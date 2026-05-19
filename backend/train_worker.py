"""
train_worker.py — Tiến trình train YOLO chạy song song với backend.

Cơ chế:
  - Chạy như một tiến trình riêng biệt (multiprocessing.Process)
  - Nhận ảnh mới qua thư mục staging (train_staging/)
  - Auto-label bằng contour detection
  - Incremental training: load best.pt → train thêm → lưu best_vN.pt
  - Không block backend, không chia sẻ RAM với backend
  - Tự động dọn staging sau khi train xong
"""

import os
import sys
import time
import glob
import shutil
import random
import threading
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# ==================== Cấu hình ====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BEST_PT = os.path.join(SCRIPT_DIR, "best.pt")
STAGING_DIR = os.path.join(SCRIPT_DIR, "train_staging")
DATASET_DIR = os.path.join(SCRIPT_DIR, "train_dataset")
VERSION_FILE = os.path.join(SCRIPT_DIR, ".train_version")

# Ngưỡng tối thiểu để bắt đầu train
MIN_IMAGES_TO_TRAIN = 5
# Số epoch mỗi lần train
EPOCHS_PER_BATCH = 10
# Thời gian chờ giữa các lần check staging (giây)
POLL_INTERVAL = 5
# Batch size
BATCH_SIZE = 4
# Image size
IMGSZ = 320
# Learning rate
LR = 0.001


def get_next_version() -> int:
    """Đọc version hiện tại từ file, trả về version tiếp theo."""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as f:
                return int(f.read().strip()) + 1
        except (ValueError, IOError):
            pass
    return 1


def save_version(version: int):
    """Lưu version hiện tại."""
    with open(VERSION_FILE, "w") as f:
        f.write(str(version))


def _preprocess_gray(image: np.ndarray) -> np.ndarray:
    """CLAHE + sharpen để contour rõ hơn."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 3), -0.5, 0)
    return gray


def _find_document_bbox(image_path: str) -> tuple | None:
    """Dùng contour detection để tìm bounding box của tài liệu."""
    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]

    scale = min(1000.0 / max(h, w), 1.0)
    if scale < 1.0:
        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
    else:
        resized = img.copy()

    gray = _preprocess_gray(resized)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    best_box = None
    best_area = 0
    img_area = resized.shape[0] * resized.shape[1]

    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.01 * img_area or area > 0.95 * img_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, bw, bh = cv2.boundingRect(approx)
            box_area = bw * bh
            if box_area > best_area:
                x = int(x / scale)
                y = int(y / scale)
                bw = int(bw / scale)
                bh = int(bh / scale)
                best_box = (x, y, x + bw, y + bh)
                best_area = box_area

    if best_box is None and contours:
        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        x, y, bw, bh = cv2.boundingRect(box)
        x = int(x / scale)
        y = int(y / scale)
        bw = int(bw / scale)
        bh = int(bh / scale)
        best_box = (x, y, x + bw, y + bh)

    return best_box


def _bbox_to_yolo(bbox, img_w, img_h):
    """Chuyển (x1,y1,x2,y2) → YOLO format."""
    x1, y1, x2, y2 = bbox
    x_center = ((x1 + x2) / 2) / img_w
    y_center = ((y1 + y2) / 2) / img_h
    width = (x2 - x1) / img_w
    height = (y2 - y1) / img_h
    return f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"


def collect_staging_images() -> list[str]:
    """Lấy tất cả ảnh từ staging dir, trả về list paths."""
    image_paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff"):
        image_paths.extend(glob.glob(os.path.join(STAGING_DIR, ext)))
        image_paths.extend(glob.glob(os.path.join(STAGING_DIR, ext.upper())))
    return image_paths


def build_dataset_from_staging(staging_images: list[str]) -> str | None:
    """
    Tạo dataset YOLO từ staging images.
    ĐÃ FIX:
      - Luôn copy ảnh kể cả khi không detect được bbox
      - Fallback bbox = full image
      - Đảm bảo val không rỗng
    """
    if len(staging_images) < MIN_IMAGES_TO_TRAIN:
        print(f"[TRAIN-WORKER] Chỉ có {len(staging_images)} ảnh, cần tối thiểu {MIN_IMAGES_TO_TRAIN}")
        return None

    print(f"[TRAIN-WORKER] Building dataset from {len(staging_images)} staging images...")

    train_img_dir = os.path.join(DATASET_DIR, "images", "train")
    val_img_dir = os.path.join(DATASET_DIR, "images", "val")
    train_lbl_dir = os.path.join(DATASET_DIR, "labels", "train")
    val_lbl_dir = os.path.join(DATASET_DIR, "labels", "val")

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)

    # Xóa dataset cũ
    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        for f in glob.glob(os.path.join(d, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

    random.shuffle(staging_images)

    # 👉 tăng train lên 90% cho dataset nhỏ
    split_idx = max(1, int(len(staging_images) * 0.9))
    train_paths = staging_images[:split_idx]
    val_paths = staging_images[split_idx:]

    # 👉 đảm bảo val không rỗng
    if len(val_paths) == 0:
        val_paths = train_paths[:1]

    labeled = 0
    failed_bbox = 0

    def process_one(src_path, img_dir, lbl_dir):
        nonlocal labeled, failed_bbox

        img = cv2.imread(src_path)
        if img is None:
            return

        h, w = img.shape[:2]
        basename = os.path.splitext(os.path.basename(src_path))[0]

        # ✅ LUÔN copy ảnh
        dst_img = os.path.join(img_dir, basename + ".jpg")
        cv2.imwrite(dst_img, img)

        # detect bbox
        bbox = _find_document_bbox(src_path)

        # ✅ fallback nếu fail
        if bbox is None:
            bbox = (0, 0, w, h)
            failed_bbox += 1

        # ghi label
        dst_lbl = os.path.join(lbl_dir, basename + ".txt")
        with open(dst_lbl, "w") as f:
            f.write(_bbox_to_yolo(bbox, w, h))

        labeled += 1

    # xử lý train
    for p in train_paths:
        process_one(p, train_img_dir, train_lbl_dir)

    # xử lý val
    for p in val_paths:
        process_one(p, val_img_dir, val_lbl_dir)

    # 👉 nếu val vẫn rỗng (trường hợp cực hiếm)
    if len(os.listdir(val_img_dir)) == 0:
        print("[TRAIN-WORKER] ⚠️ val empty → fallback copy from train")
        for f in os.listdir(train_img_dir)[:2]:
            shutil.copy2(os.path.join(train_img_dir, f), val_img_dir)
        for f in os.listdir(train_lbl_dir)[:2]:
            shutil.copy2(os.path.join(train_lbl_dir, f), val_lbl_dir)

    if labeled < MIN_IMAGES_TO_TRAIN:
        print(f"[TRAIN-WORKER] Chỉ gán nhãn được {labeled} ảnh, không đủ để train")
        return None

    data_yaml = os.path.join(DATASET_DIR, "data.yaml")
    with open(data_yaml, "w", encoding="utf-8") as f:
        f.write(f"# Auto-generated {datetime.now()}\n")
        f.write(f"train: {os.path.abspath(train_img_dir)}\n")
        f.write(f"val: {os.path.abspath(val_img_dir)}\n")
        f.write(f"nc: 1\n")
        f.write(f"names: ['document']\n")

    print(f"[TRAIN-WORKER] Dataset ready: {labeled} labeled images")
    print(f"  Train: {len(os.listdir(train_img_dir))}")
    print(f"  Val: {len(os.listdir(val_img_dir))}")
    print(f"  Fallback bbox: {failed_bbox}")

    return data_yaml


def incremental_train(data_yaml: str) -> bool:
    """
    Incremental training: load best.pt → train thêm → UPDATE TRỰC TIẾP best.pt
    Trả về True nếu thành công, False nếu thất bại.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[TRAIN-WORKER] ultralytics not installed, skipping train")
        return False

    if not os.path.exists(BEST_PT):
        print(f"[TRAIN-WORKER] {BEST_PT} not found, using pretrained yolo11n.pt")
        model = YOLO("yolo11n.pt")
        # Save initial model as best.pt
        model.save(BEST_PT)
        print(f"[TRAIN-WORKER] Created initial {BEST_PT} from yolo11n.pt")
    else:
        print(f"[TRAIN-WORKER] Loading {BEST_PT} for incremental training")
        model = YOLO(BEST_PT)

    version = get_next_version()
    project_dir = os.path.join(SCRIPT_DIR, "train_runs")
    run_name = f"train_v{version}"

    print(f"[TRAIN-WORKER] Starting incremental training (v{version})...")
    print(f"  Epochs: {EPOCHS_PER_BATCH}")
    print(f"  Img size: {IMGSZ}")
    print(f"  Batch: {BATCH_SIZE}")
    print(f"  LR: {LR}")
    print(f"  Data: {data_yaml}")

    try:
        results = model.train(
            data=data_yaml,
            epochs=EPOCHS_PER_BATCH,
            imgsz=IMGSZ,
            batch=BATCH_SIZE,
            lr0=LR,
            device="cpu",
            patience=5,
            save=True,
            project=project_dir,
            name=run_name,
            exist_ok=True,
            verbose=False,
        )

        # UPDATE TRỰC TIẾP best.pt (ghi đè file cũ)
        best_weights = os.path.join(project_dir, run_name, "weights", "best.pt")
        
        if os.path.exists(best_weights):
            # Copy weights mới ghi đè lên best.pt
            tmp_best = BEST_PT + ".tmp"
            shutil.copy2(best_weights, tmp_best)
            os.replace(tmp_best, BEST_PT)
            save_version(version)
            print(f"[TRAIN-WORKER] ✅ Model UPDATED DIRECTLY: {BEST_PT} (v{version})")

            # Cleanup thư mục train tạm
            try:
                shutil.rmtree(os.path.join(project_dir, run_name), ignore_errors=True)
            except Exception:
                pass

            return True
        else:
            print(f"[TRAIN-WORKER] ❌ No weights found after training")
            return False

    except Exception as e:
        print(f"[TRAIN-WORKER] Training error: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_staging():
    """Xóa toàn bộ ảnh trong staging sau khi train xong."""
    for f in glob.glob(os.path.join(STAGING_DIR, "*")):
        try:
            os.remove(f)
        except Exception:
            pass
    print(f"[TRAIN-WORKER] Staging cleaned")


def train_worker_loop():
    """
    Vòng lặp chính của train worker.
    - Poll staging dir mỗi POLL_INTERVAL giây
    - Khi có đủ ảnh → build dataset → train → cleanup
    """
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)

    print(f"[TRAIN-WORKER] Started. Polling: {STAGING_DIR}")
    print(f"[TRAIN-WORKER] Min images: {MIN_IMAGES_TO_TRAIN}, Poll interval: {POLL_INTERVAL}s")
    print(f"[TRAIN-WORKER] Best model: {BEST_PT}")

    while True:
        try:
            staging_images = collect_staging_images()
            if len(staging_images) >= MIN_IMAGES_TO_TRAIN:
                print(f"[TRAIN-WORKER] Found {len(staging_images)} images in staging, starting training...")

                data_yaml = build_dataset_from_staging(staging_images)
                if data_yaml:
                    success = incremental_train(data_yaml)
                    if success:
                        print(f"[TRAIN-WORKER] ✅ Training complete, {BEST_PT} updated")
                        
                        # XÓA ẢNH ĐÃ TRAIN KHỎI STAGING
                        print(f"[TRAIN-WORKER] Deleting {len(staging_images)} trained images from staging...")
                        deleted_count = 0
                        for img_path in staging_images:
                            try:
                                os.remove(img_path)
                                deleted_count += 1
                            except Exception as e:
                                print(f"[TRAIN-WORKER] Failed to delete {img_path}: {e}")
                        
                        print(f"[TRAIN-WORKER] Deleted {deleted_count}/{len(staging_images)} images")
                    else:
                        print(f"[TRAIN-WORKER] ❌ Training failed, keeping images for retry")
                else:
                    print(f"[TRAIN-WORKER] ❌ Dataset creation failed, keeping images")
            else:
                # Không có đủ ảnh, chờ tiếp
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("[TRAIN-WORKER] Interrupted, shutting down...")
            break
        except Exception as e:
            print(f"[TRAIN-WORKER] Error in loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)

    print("[TRAIN-WORKER] Stopped.")


# ==================== Entry point ====================

if __name__ == "__main__":
    train_worker_loop()
