import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import cv2

# ================= YOLO =================
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    _yolo_seg_model = None
    try:
        _yolo_seg_model = YOLO("best-seg.pt")
        print("[YOLO] Segmentation model loaded.")
    except:
        print("[YOLO] No segmentation model found, using detection model only.")
    _yolo_det_model = None
    try:
        _yolo_det_model = YOLO("best.pt")
        print("[YOLO] Detection model loaded.")
    except:
        print("[YOLO] No detection model found, using OpenCV fallback.")
except ImportError:
    YOLO_AVAILABLE = False
    _yolo_seg_model = None
    _yolo_det_model = None
    print("[YOLO] Ultralytics not installed. Using OpenCV fallback only.")

# ================= Lazy imports for heavy modules =================
_REMBG_AVAILABLE = None
_PYTESSERACT_AVAILABLE = None

def _check_rembg():
    global _REMBG_AVAILABLE
    if _REMBG_AVAILABLE is None:
        try:
            from rembg import remove
            _REMBG_AVAILABLE = True
        except ImportError:
            _REMBG_AVAILABLE = False
            print("[REMBG] rembg not installed. Background removal disabled.")
    return _REMBG_AVAILABLE

def _check_pytesseract():
    global _PYTESSERACT_AVAILABLE
    if _PYTESSERACT_AVAILABLE is None:
        try:
            import pytesseract
            tesseract_path = os.environ.get('TESSERACT_CMD', r'.\Tesseract-OCR\tesseract.exe')
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            _PYTESSERACT_AVAILABLE = True
            print("[TESSERACT] Pytesseract loaded.")
        except ImportError:
            _PYTESSERACT_AVAILABLE = False
            print("[TESSERACT] Pytesseract not installed. Orientation detection disabled.")
    return _PYTESSERACT_AVAILABLE

# ================= Utility Functions =================
_clahe_cache = None

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (max_width, max_height))


def _alpha_to_solid(bgra_img, solid_color=(255, 255, 255)):
    """Composite BGRA image over a solid BGR color."""
    if bgra_img.shape[2] != 4:
        return bgra_img
    alpha = bgra_img[:, :, 3:] / 255.0
    bgr = bgra_img[:, :, :3]
    solid = np.full_like(bgr, solid_color, dtype=np.uint8)
    composite = (alpha * bgr + (1 - alpha) * solid).astype(np.uint8)
    return composite

# ================= YOLO Detection Functions =================
def detect_document_yolo_seg(cv_image):
    if not YOLO_AVAILABLE or _yolo_seg_model is None:
        return None
    try:
        results = _yolo_seg_model(cv_image)
        if results[0].masks is None:
            return None
        mask = results[0].masks.data[0].cpu().numpy()
        mask = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        cnt = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2).astype(np.float32)
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        return box.astype(np.float32)
    except Exception as e:
        print(f"[YOLO-SEG] Error: {e}")
        return None

def detect_document_yolo_bbox(cv_image):
    if not YOLO_AVAILABLE or _yolo_det_model is None:
        return None
    try:
        results = _yolo_det_model(cv_image)
        if len(results[0].boxes) == 0:
            return None
        box = results[0].boxes.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = box
        pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        return pts
    except Exception as e:
        print(f"[YOLO-BBOX] Error: {e}")
        return None

def refine_with_contour(cv_image, bbox_pts):
    # Sử dụng contour detection trong vùng bounding box để tinh chỉnh
    x1 = int(min(bbox_pts[:, 0]))
    y1 = int(min(bbox_pts[:, 1]))
    x2 = int(max(bbox_pts[:, 0]))
    y2 = int(max(bbox_pts[:, 1]))
    roi = cv_image[y1:y2, x1:x2]
    if roi.size == 0:
        return bbox_pts
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bbox_pts
    cnt = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(approx) == 4:
        approx[:, 0, 0] += x1
        approx[:, 0, 1] += y1
        return approx.reshape(4, 2).astype(np.float32)
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    box[:, 0] += x1
    box[:, 1] += y1
    return box.astype(np.float32)

# ================= Document Contour Detection (OpenCV) =================
def detect_document_contour_canny(image):
    """Phát hiện contour tài liệu dùng Canny edge (từ main01.py)"""
    h, w = image.shape[:2]
    scale = 800.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 75, 200)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    doc_cnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_cnt = approx
            break
    if doc_cnt is None:
        return None
    doc_cnt = (doc_cnt / scale).astype("float32")
    return doc_cnt.reshape(4, 2)

def detect_document_contour_adaptive(image):
    """Fallback: Phát hiện contour dùng adaptive threshold + morphology"""
    h, w = image.shape[:2]
    scale = 1000.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    max_area = 0
    img_area = w * h
    scaled_img_area = img_area * (scale ** 2)
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

def detect_document_contour(image, method='canny'):
    """Hàm phát hiện contour chính, ưu tiên Canny, fallback adaptive"""
    if method == 'canny':
        pts = detect_document_contour_canny(image)
        if pts is not None:
            return pts
        print("[INFO] Canny contour detection failed, trying adaptive...")
    return detect_document_contour_adaptive(image)

# ================= Rotation & Background Removal =================
def rotate_image_with_osd(cv_image):
    """Xoay ảnh về đúng hướng văn bản bằng Tesseract OSD"""
    if not _check_pytesseract():
        return cv_image
    try:
        import pytesseract
        from pytesseract import Output
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        osd = pytesseract.image_to_osd(rgb, output_type=Output.DICT)
        angle = osd['rotate']
        if angle == 90:
            return cv2.rotate(cv_image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(cv_image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(cv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return cv_image
    except Exception as e:
        print(f"[TESSERACT] OSD failed: {e}")
        return cv_image

def remove_background(cv_image):
    """Loại bỏ nền bằng rembg, trả về ảnh BGR (hoặc BGRA nếu có alpha)"""
    if not _check_rembg():
        return cv_image
    try:
        from rembg import remove
        pil_img = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        output = remove(pil_img)
        if output.mode == 'RGBA':
            return cv2.cvtColor(np.array(output), cv2.COLOR_RGBA2BGRA)
        else:
            return cv2.cvtColor(np.array(output), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[REMBG] Background removal failed: {e}")
        return cv_image

# ================= Scan Effect =================
def apply_brightness_enhancement(img):
    global _clahe_cache
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    sharpened = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
    lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
    if _clahe_cache is None:
        _clahe_cache = cv2.createCLAHE(1.2, (8, 8))
    lab[:, :, 0] = _clahe_cache.apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return cv2.convertScaleAbs(enhanced, alpha=1.3, beta=10)

def apply_scan_effect(image, mode="color", threshold_method="adaptive"):
    """
    Áp dụng hiệu ứng scan.
    - mode: 'color', 'gray', 'binary'
    - threshold_method: 'adaptive', 'otsu', 'simple' (chỉ dùng khi mode='binary')
    """
    if mode == "color":
        return apply_brightness_enhancement(image)
    elif mode == "gray":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif mode == "binary":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if threshold_method == "adaptive":
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 10
            )
        elif threshold_method == "otsu":
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(
                blurred, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:  # simple
            _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        return binary
    else:
        return image

# ================= Core Processing Pipeline =================
def process_single_image(cv_image, mode="color", force_full=False,
                         enable_rotation=False, enable_bg_removal=False,
                         contour_method='canny'):
    """
    Xử lý một ảnh OpenCV BGR.
    Các bước tùy chọn:
        - Xoay ảnh (enable_rotation)
        - Xóa nền (enable_bg_removal)
        - Crop tài liệu (force_full=False)
        - Hiệu ứng scan (mode)
    """
    try:
        # Bước 1: Xoay ảnh
        if enable_rotation:
            cv_image = rotate_image_with_osd(cv_image)

        # Bước 2: Xóa nền
        if enable_bg_removal:
            cv_image = remove_background(cv_image)
            if cv_image.shape[2] == 4:
                cv_image = _alpha_to_solid(cv_image, solid_color=(255, 255, 255))

        # Bước 3: Crop tài liệu
        if force_full:
            warped = cv_image
        else:
            pts = None
            # Thử YOLO nếu có
            if YOLO_AVAILABLE:
                pts = detect_document_yolo_seg(cv_image)
                if pts is None:
                    pts = detect_document_yolo_bbox(cv_image)
                    if pts is not None:
                        pts = refine_with_contour(cv_image, pts)
            # Fallback về OpenCV contour detection
            if pts is None:
                pts = detect_document_contour(cv_image, method=contour_method)
            if pts is None:
                warped = cv_image
                print("[INFO] No document contour found, using original image.")
            else:
                warped = four_point_transform(cv_image, pts)

        # Bước 4: Scan effect
        result = apply_scan_effect(warped, mode)
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
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

# ================= Batch Processing =================
def process_scanned_images_batch_with_crop(image_list, mode="color", force_full=False,
                                           enable_rotation=False, enable_bg_removal=False,
                                           contour_method='canny'):
    if not image_list:
        return []
    results = [None] * len(image_list)
    max_workers = min(os.cpu_count() or 4, len(image_list))

    def process_single(args):
        idx, pil_img = args
        try:
            cv_img = pil_to_cv2(pil_img)
            res = process_single_image(
                cv_img, mode=mode, force_full=force_full,
                enable_rotation=enable_rotation,
                enable_bg_removal=enable_bg_removal,
                contour_method=contour_method
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