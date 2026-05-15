import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

# ================= YOLO =================
try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
    _yolo_det_model = None

    try:
        _yolo_det_model = YOLO("best.pt")
        print("[YOLO] Detection model loaded.")
    except Exception:
        print("[YOLO] No detection model found, using OpenCV fallback.")

except ImportError:
    YOLO_AVAILABLE = False
    _yolo_det_model = None
    print("[YOLO] Ultralytics not installed. Using OpenCV fallback only.")

# ================= Lazy imports for heavy modules =================
_REMBG_AVAILABLE = None
_PYTESSERACT_AVAILABLE = None
_PPOCR_LITE_AVAILABLE = None


def _check_rembg():
    global _REMBG_AVAILABLE
    if _REMBG_AVAILABLE is None:
        try:
            from rembg import remove  # noqa: F401

            _REMBG_AVAILABLE = True
        except ImportError:
            _REMBG_AVAILABLE = False
            print("[REMBG] rembg not installed. Background removal disabled.")
    return _REMBG_AVAILABLE


# ================= TESSERACT OSD (COMMENTED - replaced by OpenCV custom) =================
# def _check_pytesseract():
#     global _PYTESSERACT_AVAILABLE
#     if _PYTESSERACT_AVAILABLE is None:
#         try:
#             import pytesseract  # noqa: F401
#
#             tesseract_path = os.environ.get(
#                 "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#             )
#             if os.path.exists(tesseract_path):
#                 pytesseract.pytesseract.tesseract_cmd = tesseract_path
#             _PYTESSERACT_AVAILABLE = True
#             print("[TESSERACT] Pytesseract loaded.")
#         except ImportError:
#             _PYTESSERACT_AVAILABLE = False
#             print("[TESSERACT] Pytesseract not installed. Orientation detection disabled.")
#     return _PYTESSERACT_AVAILABLE


# ================= OpenCV custom rotation (thay thế Tesseract OSD) =================
def _detect_text_orientation_opencv(cv_image):
    """
    Phát hiện hướng xoay của văn bản bằng OpenCV (không dùng Tesseract).
    - Resize ảnh xuống nhỏ (max 300px) để tăng tốc
    - So sánh bounding box của text contours để xác định hướng

    Returns: góc cần xoay (0, 90, 180, 270)
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    if h < 50 or w < 50:
        return 0

    # Resize ảnh xuống max 1200px để giữ text rõ trong khi vẫn tăng tốc
    scale = min(1200.0 / h, 1200.0 / w, 1.0)
    if scale < 1.0:
        small = cv2.resize(gray, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)
        sh, sw = small.shape
    else:
        small = gray
        sh, sw = h, w

    # Nếu ảnh gần như đồng màu (std quá thấp) → không có text, bỏ qua
    if np.std(small) < 10:
        return 0

    # OTSU threshold
    _, binary = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Xoá nhiễu nhỏ
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # Tìm contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0

    # Lọc contour quá nhỏ (nhiễu) - giữ ngưỡng thấp để không mất text
    min_area = max(3, (sh * sw) * 0.0001)
    valid = [c for c in contours if cv2.contourArea(c) > min_area]
    if not valid:
        return 0

    # Gộp tất cả contour để lấy bounding box bao trùm toàn bộ text
    all_pts = np.vstack([c.reshape(-1, 2) for c in valid])
    x, y, bw, bh = cv2.boundingRect(all_pts)

    if bw == 0 or bh == 0:
        return 0

    # So sánh chiều rộng vs chiều cao của vùng text
    # Text nằm ngang → bbox rộng hơn cao → 0° hoặc 180°
    # Text nằm dọc → bbox cao hơn rộng → 90° hoặc 270°
    if bw >= bh:
        # Text ngang: kiểm tra 180° bằng mật độ text 1/4 trên vs 1/4 dưới
        q1 = cleaned[:sh//4, :]
        q4 = cleaned[3*sh//4:, :]
        d1 = np.sum(q1) / 255.0
        d4 = np.sum(q4) / 255.0
        if d4 > d1 * 1.5 and d4 > 10:
            return 180
        return 0
    else:
        # Text dọc: kiểm tra 90° vs 270° bằng mật độ text 1/4 trái vs 1/4 phải
        q1 = cleaned[:, :sw//4]
        q4 = cleaned[:, 3*sw//4:]
        d1 = np.sum(q1) / 255.0
        d4 = np.sum(q4) / 255.0
        if d4 > d1 * 1.5 and d4 > 10:
            return 270
        return 90


def rotate_image_opencv(cv_image):
    """
    Xoay ảnh về đúng hướng văn bản bằng OpenCV (thay thế Tesseract OSD).
    Nhanh hơn vì không cần load Tesseract engine.
    """
    angle = _detect_text_orientation_opencv(cv_image)
    if angle == 0:
        return cv_image
    if angle == 90:
        return cv2.rotate(cv_image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(cv_image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(cv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return cv_image


def _check_ppocr_lite():
    global _PPOCR_LITE_AVAILABLE
    if _PPOCR_LITE_AVAILABLE is None:
        try:
            from ppocr_lite import PPOcrLite  # noqa: F401

            _PPOCR_LITE_AVAILABLE = True
            print("[PPOCR-LITE] ppocr-lite loaded (lightweight fallback).")
        except ImportError:
            _PPOCR_LITE_AVAILABLE = False
            print("[PPOCR-LITE] ppocr-lite not installed. Skipping.")
    return _PPOCR_LITE_AVAILABLE


# ================= Utility Functions =================
_clahe_cache = None


def order_points(pts: np.ndarray) -> np.ndarray:
    """Sắp xếp 4 điểm theo thứ tự: tl, tr, br, bl."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Perspective warp: crop tài liệu theo 4 điểm, trả về ảnh đã warp sát cạnh."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width <= 1 or max_height <= 1:
        return image.copy()

    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    return warped


def _alpha_to_solid(bgra_img: np.ndarray, solid_color=(255, 255, 255)) -> np.ndarray:
    """Composite BGRA image over a solid BGR color."""
    if bgra_img.shape[2] != 4:
        return bgra_img
    alpha = bgra_img[:, :, 3:] / 255.0
    bgr = bgra_img[:, :, :3]
    solid = np.full_like(bgr, solid_color, dtype=np.uint8)
    composite = (alpha * bgr + (1 - alpha) * solid).astype(np.uint8)
    return composite


# ================= Enhanced Preprocessing for Contour =================

def preprocess_for_contour(image: np.ndarray, method: str = "clahe") -> np.ndarray:
    """
    Chuẩn hóa ánh sáng để cải thiện phát hiện cạnh.
    Ảnh đầu vào có thể là BGR hoặc Gray.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    if method == "clahe":
        global _clahe_cache
        if _clahe_cache is None:
            _clahe_cache = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return _clahe_cache.apply(gray)

    if method == "gamma":
        mean = float(np.mean(gray))
        gamma = 1.0
        if mean < 80:
            gamma = 0.6
        elif mean > 180:
            gamma = 1.5
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(gray, table)

    return gray


def is_valid_document(
    pts: Optional[np.ndarray],
    img_shape: Tuple[int, int],
    min_area_ratio: float = 0.02,
    max_area_ratio: float = 0.95,
    min_aspect: float = 0.5,
    max_aspect: float = 3.0,
) -> bool:
    """
    Kiểm tra xem 4 điểm có tạo thành một tứ giác giống tài liệu không.
    - Diện tích bao phải nằm trong khoảng [min_area_ratio, max_area_ratio] so với ảnh gốc.
    - Tỉ lệ dài/rộng (aspect ratio) phải nằm trong khoảng [min_aspect, max_aspect].
    """
    if pts is None or len(pts) != 4:
        return False

    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_width = max(width_a, width_b)
    max_height = max(height_a, height_b)

    if max_width == 0 or max_height == 0:
        return False

    area = max_width * max_height
    img_area = img_shape[0] * img_shape[1]
    if not (min_area_ratio < area / img_area < max_area_ratio):
        return False

    aspect = max_width / max_height if max_height != 0 else 1
    if not (min_aspect < aspect < max_aspect):
        return False

    return True


def canny_with_auto_threshold(gray: np.ndarray) -> np.ndarray:
    """
    Canny với ngưỡng tự động dựa trên median của ảnh.
    Cho kết quả ổn định hơn trên nhiều điều kiện ánh sáng.
    """
    median = np.median(gray)
    low = int(max(0, (1.0 - 0.33) * median))
    high = int(min(255, (1.0 + 0.33) * median))
    return cv2.Canny(gray, low, high)


# ================= Local Enhancement =================

def adjust_brightness_contrast(img: np.ndarray, brightness: int = 10, contrast: int = 10) -> np.ndarray:
    """
    Tăng sáng/tương phản đều toàn ảnh.
    brightness, contrast: phần trăm (-100 đến 100)
    """
    out = img.copy()

    if brightness != 0:
        beta = (brightness / 100.0) * 255.0
        out = cv2.convertScaleAbs(out, alpha=1.0, beta=beta)

    if contrast != 0:
        alpha = 1.0 + (contrast / 100.0)
        out = cv2.convertScaleAbs(out, alpha=alpha, beta=0)

    return out


# ================= Content-Aware Auto Crop =================

def auto_crop_content(image: np.ndarray, border: int = 2) -> np.ndarray:
    """
    Tự động crop sát viền nội dung thực tế của tài liệu sau warp.
    Loại bỏ hoàn toàn nền trắng/xám thừa xung quanh.

    Args:
        image: Ảnh BGR (hoặc BGRA) đã warp
        border: Pixel đệm thêm vào viền để không cắt mất nội dung

    Returns:
        Ảnh đã crop sát nội dung
    """
    h, w = image.shape[:2]

    # Xử lý ảnh 4 kênh (BGRA) và 3 kênh (BGR)
    if len(image.shape) == 3 and image.shape[2] == 4:
        gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    elif len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Xác định màu nền từ 4 góc ảnh
    margin = max(5, int(min(h, w) * 0.02))
    corners = np.concatenate([
        gray[:margin, :margin].ravel(),
        gray[:margin, -margin:].ravel(),
        gray[-margin:, :margin].ravel(),
        gray[-margin:, -margin:].ravel(),
    ])
    bg_color = float(np.median(corners))

    # Threshold: mọi pixel khác xa màu nền là nội dung
    diff = cv2.absdiff(gray, bg_color)
    _, fg_mask = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)

    # Morphology để kết nối các vùng nội dung gần nhau
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Tìm contour lớn nhất (nội dung chính)
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    # Gộp tất cả contour để lấy bounding box bao trùm toàn bộ nội dung
    all_pts = np.vstack([c.reshape(-1, 2) for c in contours])
    x, y, bw, bh = cv2.boundingRect(all_pts)

    # Thêm đệm nhỏ để không cắt mất nội dung sát viền
    x = max(0, x - border)
    y = max(0, y - border)
    bw = min(w - x, bw + border * 2)
    bh = min(h - y, bh + border * 2)

    return image[y:y+bh, x:x+bw]


# ================= YOLO Detection Functions =================

def detect_document_yolo_bbox(cv_image, conf=0.15, iou=0.7, imgsz=320):
    if not YOLO_AVAILABLE or _yolo_det_model is None:
        return None
    try:
        results = _yolo_det_model(cv_image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)
        if len(results[0].boxes) == 0:
            return None
        box = results[0].boxes.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = box
        pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        return pts
    except Exception as e:
        print(f"[YOLO-BBOX] Error: {e}")
        return None


def refine_with_contour(cv_image, bbox_pts, preprocess='clahe'):
    """
    Tinh chỉnh 4 góc tài liệu bằng contour detection trong vùng bounding box.
    Dùng multiple Canny thresholds + morphology để bám sát cạnh thật.
    """
    x1 = int(min(bbox_pts[:, 0]))
    y1 = int(min(bbox_pts[:, 1]))
    x2 = int(max(bbox_pts[:, 0]))
    y2 = int(max(bbox_pts[:, 1]))

    margin = 3  # margin nhỏ hơn để bám sát hơn
    h_img, w_img = cv_image.shape[:2]
    x1 = max(0, x1 - margin)
    y1 = max(0, y1 - margin)
    x2 = min(w_img, x2 + margin)
    y2 = min(h_img, y2 + margin)

    roi = cv_image[y1:y2, x1:x2]
    if roi.size == 0:
        return bbox_pts

    gray = preprocess_for_contour(roi, method=preprocess)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)  # kernel nhỏ hơn để giữ chi tiết cạnh

    # Thử nhiều threshold Canny khác nhau
    edges_list = []
    for low, high in [(30, 90), (50, 120), (70, 150), (20, 80)]:
        e = cv2.Canny(blurred, low, high)
        edges_list.append(e)

    # Kết hợp các edges lại: pixel nào xuất hiện >= 2 lần thì giữ
    combined = np.zeros_like(edges_list[0], dtype=np.uint8)
    for e in edges_list:
        combined = cv2.add(combined, e // 255)
    combined = (combined >= 2).astype(np.uint8) * 255

    # Đóng khoảng trống nhỏ giữa các cạnh
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
    dilated = cv2.dilate(closed, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return bbox_pts

    # Lọc contour quá nhỏ
    min_contour_area = max(500, roi.shape[0] * roi.shape[1] * 0.01)
    large_contours = [c for c in contours if cv2.contourArea(c) > min_contour_area]
    if not large_contours:
        return bbox_pts

    cnt = max(large_contours, key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)

    # Thử nhiều epsilon để tìm tứ giác phù hợp
    best_approx = None
    for eps_factor in [0.01, 0.015, 0.02, 0.025, 0.03]:
        approx = cv2.approxPolyDP(cnt, eps_factor * peri, True)
        if len(approx) == 4:
            best_approx = approx
            break

    if best_approx is not None:
        best_approx[:, 0, 0] += x1
        best_approx[:, 0, 1] += y1
        return best_approx.reshape(4, 2).astype(np.float32)

    # Fallback: minAreaRect
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    box[:, 0] += x1
    box[:, 1] += y1
    return box.astype(np.float32)


# ================= Document Contour Detection (OpenCV) =================

def detect_document_contour_canny(image, preprocess='clahe'):
    h, w = image.shape[:2]
    scale = 800.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))

    gray = preprocess_for_contour(resized, method=preprocess)

    # Sharpen nhẹ để biên rõ hơn
    gray = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 3), -0.5, 0)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = canny_with_auto_threshold(blurred)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for c in contours:
        peri = cv2.arcLength(c, True)
        for eps in [0.01, 0.015, 0.02]:
            approx = cv2.approxPolyDP(c, eps * peri, True)
            if len(approx) == 4:
                return (approx / scale).reshape(4, 2).astype("float32")

    return None


def detect_document_contour_adaptive(image, preprocess='clahe'):
    """Fallback: Adaptive threshold + morphology."""
    h, w = image.shape[:2]
    scale = 1000.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))

    gray = preprocess_for_contour(resized, method=preprocess)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    max_area = 0
    scaled_img_area = (w * scale) * (h * scale)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10000 or area > 0.9 * scaled_img_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            if area > max_area:
                best = approx
                max_area = area
        else:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            if area > max_area:
                best = box.reshape(-1, 1, 2)
                max_area = area

    if best is None:
        return None

    pts = (best / scale).astype("float32").reshape(4, 2)
    pts = order_points(pts)
    return pts


def detect_document_contour(image, method='canny', preprocess='clahe'):
    """Hàm phát hiện contour chính, ưu tiên Canny, fallback adaptive."""
    if method == 'canny':
        pts = detect_document_contour_canny(image, preprocess=preprocess)
        if pts is not None:
            return pts
        print("[INFO] Canny contour detection failed, trying adaptive...")
    return detect_document_contour_adaptive(image, preprocess=preprocess)


# ================= ppocr-lite fallback (optional) =================

def detect_document_ppocr_lite(cv_image):
    if not _check_ppocr_lite():
        return None
    try:
        from ppocr_lite import PPOcrLite  # noqa: F401
        _ = PPOcrLite()
        return None
    except Exception:
        return None


# ================= Rotation & Background Removal =================

# ================= TESSERACT OSD (COMMENTED - replaced by OpenCV custom) =================
# def rotate_image_with_osd(cv_image):
#     """Xoay ảnh về đúng hướng văn bản bằng Tesseract OSD."""
#     if not _check_pytesseract():
#         return cv_image
#     try:
#         import pytesseract
#         from pytesseract import Output
#
#         rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
#         osd = pytesseract.image_to_osd(rgb, output_type=Output.DICT)
#         angle = osd['rotate']
#         if angle == 90:
#             return cv2.rotate(cv_image, cv2.ROTATE_90_CLOCKWISE)
#         if angle == 180:
#             return cv2.rotate(cv_image, cv2.ROTATE_180)
#         if angle == 270:
#             return cv2.rotate(cv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         return cv_image
#     except Exception as e:
#         print(f"[TESSERACT] OSD failed: {e}")
#         return cv_image


def remove_background(cv_image):
    """Loại bỏ nền bằng rembg, trả về ảnh BGR (hoặc BGRA nếu có alpha)."""
    if not _check_rembg():
        return cv_image
    try:
        from rembg import remove

        pil_img = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        output = remove(pil_img)
        if output.mode == 'RGBA':
            return cv2.cvtColor(np.array(output), cv2.COLOR_RGBA2BGRA)
        return cv2.cvtColor(np.array(output), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[REMBG] Background removal failed: {e}")
        return cv_image


def bgra_to_bgr(cv_image: np.ndarray) -> np.ndarray:
    """Chuyển BGRA (4 kênh) về BGR (3 kênh) bằng cách composite lên nền trắng."""
    if cv_image.shape[2] != 4:
        return cv_image
    alpha = cv_image[:, :, 3:] / 255.0
    bgr = cv_image[:, :, :3]
    white = np.full_like(bgr, 255, dtype=np.uint8)
    composite = (alpha * bgr.astype(np.float32) + (1 - alpha) * white.astype(np.float32)).astype(np.uint8)
    return composite


# ================= Scan Effect =================

def apply_brightness_enhancement(img):
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    sharpened = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
    lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
    global _clahe_cache
    if _clahe_cache is None:
        _clahe_cache = cv2.createCLAHE(1.2, (8, 8))
    lab[:, :, 0] = _clahe_cache.apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return cv2.convertScaleAbs(enhanced, alpha=1.3, beta=10)


def apply_scan_effect(
    image,
    mode="color",
    threshold_method="adaptive",
    brightness=15,
    contrast=15,
):
    """
    Áp dụng hiệu ứng scan.
    - mode: 'color', 'gray', 'binary'
    - threshold_method: 'adaptive', 'otsu', 'simple' (chỉ dùng khi mode='binary')
    - brightness: Brightness adjustment percentage (-100 to 100)
    - contrast: Contrast adjustment percentage (-100 to 100)
    """
    if brightness != 0 or contrast != 0:
        image = adjust_brightness_contrast(image, brightness, contrast)

    if mode == "color":
        return apply_brightness_enhancement(image)

    if mode == "gray":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    if mode == "binary":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if threshold_method == "adaptive":
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 10
            )
        elif threshold_method == "otsu":
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(
                blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    return image


# ================= Core Processing Pipeline =================

def process_single_image(
    cv_image,
    mode="color",
    force_full=False,
    enable_rotation=False,
    enable_bg_removal=False,
    enable_auto_crop=True,
    contour_method='canny',
    preprocess='clahe',
    conf=0.15,
    iou=0.7,
    imgsz=320,
    brightness=15,
    contrast=15,
    edge_brightness=35,
    edge_contrast=20,
):
    """
    Xử lý một ảnh OpenCV BGR.

    Luồng cải tiến:
      1) Tùy chọn xóa nền
      2) Phát hiện tài liệu (YOLO → refine contour → OpenCV contour)
      3) Nếu phát hiện được: perspective warp crop sát tài liệu
      4) Auto-crop nội dung thực tế (loại bỏ nền trắng/xám thừa)
      5) Tùy chọn xoay
      6) Áp dụng scan effect
    """
    try:
        # --- Bước 1: Xóa nền (giữ nguyên BGRA để dùng alpha channel crop) ---
        has_alpha = False
        if enable_bg_removal:
            cv_image = remove_background(cv_image)
            if cv_image.ndim == 3 and cv_image.shape[2] == 4:
                has_alpha = True

        # --- Bước 2: Phát hiện tài liệu ---
        pts = None
        detect_img = cv_image[:, :, :3] if has_alpha else cv_image  # BGR cho YOLO

        if not force_full:
            if YOLO_AVAILABLE:
                pts = detect_document_yolo_bbox(detect_img, conf=conf, iou=iou, imgsz=imgsz)
                if pts is not None:
                    pts = refine_with_contour(detect_img, pts, preprocess=preprocess)
                    if not is_valid_document(pts, detect_img.shape[:2]):
                        pts = None

            if pts is None:
                pts = detect_document_contour(detect_img, method=contour_method, preprocess=preprocess)
                if pts is not None and not is_valid_document(pts, detect_img.shape[:2]):
                    pts = None

            if pts is None:
                pts = detect_document_ppocr_lite(detect_img)

        # --- Bước 3: Warp / Crop ---
        if pts is not None and not force_full:
            # Warp trên ảnh gốc (giữ alpha nếu có)
            warped = four_point_transform(cv_image, pts)

            # Crop sát nội dung bằng alpha channel (nếu có)
            if enable_auto_crop:
                if has_alpha and warped.shape[2] == 4:
                    # Dùng alpha channel để crop chính xác
                    alpha = warped[:, :, 3]
                    contours, _ = cv2.findContours(alpha, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        all_pts = np.vstack([c.reshape(-1, 2) for c in contours])
                        x, y, bw, bh = cv2.boundingRect(all_pts)
                        warped = warped[y:y+bh, x:x+bw]
                else:
                    # Fallback: crop theo nội dung
                    warped = auto_crop_content(warped, border=0)

            # Chuyển về BGR nếu còn alpha
            if warped.shape[2] == 4:
                warped = warped[:, :, :3]
        else:
            if force_full:
                warped = cv_image[:, :, :3] if has_alpha else cv_image.copy()
            else:
                warped = adjust_brightness_contrast(detect_img, brightness=10, contrast=10)

        # --- Bước 4: Xoay (dùng OpenCV custom thay vì Tesseract OSD) ---
        if enable_rotation:
            warped = rotate_image_opencv(warped)

        # --- Bước 5: Scan effect ---
        result = apply_scan_effect(
            warped,
            mode,
            brightness=brightness,
            contrast=contrast,
        )

        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result

    except Exception as e:
        print("[PIPELINE ERROR]", e)
        return cv_image.copy()


# ================= Conversion Helpers =================

def pil_to_cv2(pil_img):
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv_img):
    if cv_img.ndim == 2:
        return Image.fromarray(cv_img)
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


# ================= Batch Processing =================

def process_scanned_images_batch_with_crop(
    image_list,
    mode="color",
    force_full=False,
    enable_rotation=False,
    enable_bg_removal=False,
    enable_auto_crop=True,
    contour_method='canny',
    preprocess='clahe',
    conf=0.15,
    iou=0.7,
    imgsz=320,
    brightness=10,
    contrast=10,
    edge_brightness=35,
    edge_contrast=20,
):
    if not image_list:
        return []

    results = [None] * len(image_list)
    max_workers = min(os.cpu_count() or 4, len(image_list))

    def process_single(args):
        idx, pil_img = args
        try:
            cv_img = pil_to_cv2(pil_img)
            res = process_single_image(
                cv_img,
                mode=mode,
                force_full=force_full,
                enable_rotation=enable_rotation,
                enable_bg_removal=enable_bg_removal,
                enable_auto_crop=enable_auto_crop,
                contour_method=contour_method,
                preprocess=preprocess,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                brightness=brightness,
                contrast=contrast,
                edge_brightness=edge_brightness,
                edge_contrast=edge_contrast,
            )
            return idx, cv2_to_pil(res)
        except Exception as e:
            print(f"[BATCH ERROR] idx {idx}: {e}")
            return idx, pil_img

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single, (i, img)): i for i, img in enumerate(image_list)}
        for f in as_completed(futures):
            idx, res = f.result()
            results[idx] = res

    return results
