"""
train_yolo.py — Huấn luyện / fine-tune model YOLO phát hiện tài liệu.

Cách dùng:
  1. Chuẩn bị dataset trong thư mục dataset/ theo cấu trúc YOLO:
       dataset/
         images/
           train/
             img1.jpg
           val/
             img2.jpg
         labels/
           train/
             img1.txt
           val/
             img2.txt

  2. Chạy training:
       python train_yolo.py

  Hoặc dùng ảnh đã upload để auto-label rồi train:
       python train_yolo.py --auto-label --upload-dir uploads

Tham số:
  --model         Path to base model (mặc định: best.pt hoặc YOLO pretrained)
  --data          Path to data.yaml (mặc định: dataset/data.yaml)
  --epochs        Số epoch (mặc định: 50)
  --imgsz         Kích thước ảnh đầu vào (mặc định: 640)
  --batch         Batch size (mặc định: 8)
  --lr            Learning rate (mặc định: 0.001)
  --device        Thiết bị: cpu, 0, 1,... (mặc định: auto)
  --auto-label    Tự động gán nhãn từ contour detection rồi train
  --upload-dir    Thư mục chứa ảnh upload (dùng với --auto-label)
  --export-path   Nơi lưu model sau train (mặc định: best.pt)

Yêu cầu:
  - ultralytics (pip install ultralytics)
  - opencv-python, numpy
"""

import os
import sys
import argparse
import shutil
import glob
from datetime import datetime

import cv2
import numpy as np

# ==================== Cấu hình ====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(SCRIPT_DIR, "best.pt")
DEFAULT_DATA_YAML = os.path.join(SCRIPT_DIR, "dataset", "data.yaml")
DEFAULT_UPLOAD_DIR = os.path.join(SCRIPT_DIR, "uploads")
DEFAULT_EXPORT_PATH = os.path.join(SCRIPT_DIR, "best.pt")

# ==================== Auto-label bằng contour ====================


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
    """
    Dùng contour detection để tìm bounding box của tài liệu.
    Trả về (x1, y1, x2, y2) ở tọa độ ảnh gốc, hoặc None.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]

    # Scale ảnh về tối đa 1000px để tăng tốc
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
                # Scale về tọa độ gốc
                x = int(x / scale)
                y = int(y / scale)
                bw = int(bw / scale)
                bh = int(bh / scale)
                best_box = (x, y, x + bw, y + bh)
                best_area = box_area

    if best_box is None:
        # Fallback: dùng minAreaRect trên contour lớn nhất
        if contours:
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
    """Chuyển (x1,y1,x2,y2) → YOLO format (class x_center y_center width height)."""
    x1, y1, x2, y2 = bbox
    x_center = ((x1 + x2) / 2) / img_w
    y_center = ((y1 + y2) / 2) / img_h
    width = (x2 - x1) / img_w
    height = (y2 - y1) / img_h
    # Class 0 = document
    return f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"


def auto_label_dataset(upload_dir: str, output_dir: str, val_split: float = 0.15):
    """
    Tự động gán nhãn cho ảnh từ upload_dir bằng contour detection.
    Tạo cấu trúc dataset YOLO tại output_dir.
    """
    image_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
    image_paths = []
    for ext in image_exts:
        image_paths.extend(glob.glob(os.path.join(upload_dir, f"*{ext}")))
        image_paths.extend(glob.glob(os.path.join(upload_dir, f"*{ext.upper()}")))

    if not image_paths:
        print(f"[TRAIN] Không tìm thấy ảnh nào trong {upload_dir}")
        return False

    print(f"[TRAIN] Tìm thấy {len(image_paths)} ảnh trong {upload_dir}")
    print(f"[TRAIN] Đang auto-label bằng contour detection...")

    # Tạo cấu trúc thư mục
    train_img_dir = os.path.join(output_dir, "images", "train")
    val_img_dir = os.path.join(output_dir, "images", "val")
    train_lbl_dir = os.path.join(output_dir, "labels", "train")
    val_lbl_dir = os.path.join(output_dir, "labels", "val")

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        os.makedirs(d, exist_ok=True)

    # Xáo trộn và split
    import random
    random.shuffle(image_paths)
    split_idx = max(1, int(len(image_paths) * (1 - val_split)))
    train_paths = image_paths[:split_idx]
    val_paths = image_paths[split_idx:]

    labeled_count = 0
    failed = []

    def process_one(src_path, img_dir, lbl_dir):
        nonlocal labeled_count
        img = cv2.imread(src_path)
        if img is None:
            failed.append(src_path)
            return
        h, w = img.shape[:2]

        bbox = _find_document_bbox(src_path)
        if bbox is None:
            failed.append(src_path)
            return

        # Copy ảnh
        basename = os.path.splitext(os.path.basename(src_path))[0]
        dst_img = os.path.join(img_dir, basename + ".jpg")
        cv2.imwrite(dst_img, img)

        # Ghi label
        dst_lbl = os.path.join(lbl_dir, basename + ".txt")
        with open(dst_lbl, "w") as f:
            f.write(_bbox_to_yolo(bbox, w, h))

        labeled_count += 1

    for p in train_paths:
        process_one(p, train_img_dir, train_lbl_dir)
    for p in val_paths:
        process_one(p, val_img_dir, val_lbl_dir)

    print(f"[TRAIN] Đã gán nhãn: {labeled_count} ảnh")
    if failed:
        print(f"[TRAIN] Không thể gán nhãn: {len(failed)} ảnh")
        for f in failed[:5]:
            print(f"  - {f}")
        if len(failed) > 5:
            print(f"  ... và {len(failed) - 5} ảnh khác")

    # Tạo data.yaml
    data_yaml_path = os.path.join(output_dir, "data.yaml")
    with open(data_yaml_path, "w", encoding="utf-8") as f:
        f.write(f"# Dataset auto-generated by train_yolo.py ({datetime.now()})\n")
        f.write(f"train: {os.path.abspath(train_img_dir)}\n")
        f.write(f"val: {os.path.abspath(val_img_dir)}\n")
        f.write(f"nc: 1\n")
        f.write(f"names: ['document']\n")

    print(f"[TRAIN] Dataset created at: {output_dir}")
    print(f"[TRAIN] Train: {len(train_paths)} ảnh, Val: {len(val_paths)} ảnh")
    return True


# ==================== Training ====================


def _get_next_version(base_path: str) -> int:
    """Đọc version hiện tại từ các file best_v*.pt, trả về version tiếp theo."""
    import glob
    pattern = base_path.replace(".pt", "_v*.pt")
    existing = glob.glob(pattern)
    if not existing:
        return 1
    versions = []
    for f in existing:
        try:
            v = int(f.split("_v")[-1].replace(".pt", ""))
            versions.append(v)
        except ValueError:
            pass
    return max(versions) + 1 if versions else 1


def train_yolo(
    model_path: str,
    data_yaml: str,
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 8,
    lr: float = 0.001,
    device: str = "auto",
    export_path: str = DEFAULT_EXPORT_PATH,
    incremental: bool = False,  # Mặc định: UPDATE TRỰC TIẾP best.pt
):
    """
    Fine-tune YOLO model với dataset.
    Nếu incremental=False: UPDATE TRỰC TIẾP best.pt (ghi đè)
    Nếu incremental=True: lưu thành best_vN.pt (giữ file cũ)
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[TRAIN] LỖI: ultralytics chưa được cài đặt.")
        print("  pip install ultralytics")
        return False

    if not os.path.exists(data_yaml):
        print(f"[TRAIN] LỖI: Không tìm thấy data.yaml tại: {data_yaml}")
        return False

    # Load model
    if os.path.exists(model_path):
        print(f"[TRAIN] Load model từ: {model_path}")
        model = YOLO(model_path)
    else:
        print(f"[TRAIN] Không tìm thấy {model_path}, dùng YOLO pretrained (yolo11n.pt)")
        model = YOLO("yolo11n.pt")

    print(f"[TRAIN] Bắt đầu training{' (incremental - keep old model)' if incremental else ' (direct update - overwrite best.pt)'}...")
    print(f"  Epochs: {epochs}")
    print(f"  Img size: {imgsz}")
    print(f"  Batch: {batch}")
    print(f"  Learning rate: {lr}")
    print(f"  Device: {device}")
    print(f"  Data: {data_yaml}")

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        lr0=lr,
        device=device,
        patience=20,
        save=True,
        project=os.path.dirname(export_path),
        name="train_yolo",
        exist_ok=True,
    )

    # Export model
    export_dir = os.path.dirname(export_path) or "."
    last_pt = os.path.join(export_dir, "train_yolo", "weights", "last.pt")
    best_pt = os.path.join(export_dir, "train_yolo", "weights", "best.pt")

    if incremental:
        # Incremental: lưu thành best_vN.pt, KHÔNG ghi đè best.pt
        version = _get_next_version(export_path)
        new_path = export_path.replace(".pt", f"_v{version}.pt")
        if os.path.exists(best_pt):
            shutil.copy2(best_pt, new_path)
            print(f"[TRAIN] ✅ Incremental model saved: {new_path}")
            print(f"[TRAIN] best.pt vẫn được giữ nguyên, model mới: best_v{version}.pt")
        elif os.path.exists(last_pt):
            shutil.copy2(last_pt, new_path)
            print(f"[TRAIN] ⚠️ Chỉ có last.pt, đã lưu: {new_path}")
        else:
            print(f"[TRAIN] ❌ Không tìm thấy weights sau training!")
            return False
    else:
        # UPDATE TRỰC TIẾP best.pt (ghi đè file cũ)
        if os.path.exists(best_pt):
            shutil.copy2(best_pt, export_path)
            print(f"[TRAIN] ✅ Model UPDATED DIRECTLY: {export_path}")
        elif os.path.exists(last_pt):
            shutil.copy2(last_pt, export_path)
            print(f"[TRAIN] ⚠️ Chỉ có last.pt, đã update: {export_path}")
        else:
            print(f"[TRAIN] ❌ Không tìm thấy weights sau training!")
            return False

    # Cleanup thư mục train tạm
    train_dir = os.path.join(export_dir, "train_yolo")
    if os.path.exists(train_dir):
        import shutil
        shutil.rmtree(train_dir, ignore_errors=True)
        print(f"[TRAIN] Đã dọn thư mục tạm: {train_dir}")

    print(f"[TRAIN] ✅ Training hoàn tất!")
    return True


# ==================== CLI ====================


def main():
    parser = argparse.ArgumentParser(
        description="Train / fine-tune YOLO document detection model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Base model path")
    parser.add_argument("--data", default=DEFAULT_DATA_YAML, help="data.yaml path")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--device", default="auto", help="Device: cpu, 0, 1,...")
    parser.add_argument(
        "--auto-label",
        action="store_true",
        help="Auto-label images from upload-dir using contour detection",
    )
    parser.add_argument(
        "--upload-dir",
        default=DEFAULT_UPLOAD_DIR,
        help="Directory containing uploaded images (used with --auto-label)",
    )
    parser.add_argument(
        "--export-path",
        default=DEFAULT_EXPORT_PATH,
        help="Where to save the trained model",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental mode (create best_vN.pt instead of overwriting best.pt)",
    )

    args = parser.parse_args()

    # Nếu không có đối số nào, in help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # Auto-label nếu cần
    if args.auto_label:
        dataset_dir = os.path.join(SCRIPT_DIR, "dataset")
        success = auto_label_dataset(args.upload_dir, dataset_dir)
        if not success:
            print("[TRAIN] ❌ Auto-label thất bại, không thể training.")
            return
        args.data = os.path.join(dataset_dir, "data.yaml")

    # Train
    train_yolo(
        model_path=args.model,
        data_yaml=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        lr=args.lr,
        device=args.device,
        export_path=args.export_path,
        incremental=args.incremental,
    )


if __name__ == "__main__":
    main()
