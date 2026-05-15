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
    # try:
    #     _yolo_seg_model = YOLO("best-seg.pt")
    #     print("[YOLO] Segmentation model loaded.")
    # except:
    #     print("[YOLO] No segmentation model found, using detection model only.")
    # _yolo_det_model = None
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
_PPOCR_LITE_AVAILABLE = None

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

# ================= TESSERACT OSD (COMMENTED - replaced by OpenCV custom) =================
# def _check_pytesseract():
#     global _PYTESSERACT_AVAILABLE
#     if _PYTESSERACT_AVAILABLE is None:
#         try:
#             import pytesseract
#             tesseract_path = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
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
    Dùng Hough Line Transform để tìm góc của text lines.

    Returns: góc cần xoay (0, 90, 180, 270)
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    if h < 50 or w < 50:
        return 0

    # Dùng OTSU threshold để tách text khỏi nền
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Xoá nhiễu nhỏ, giữ lại các khối text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    # Tìm contours của text
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0

    # Lọc contour quá nhỏ (nhiễu) hoặc quá lớn (khối nền)
    img_area = h * w
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 10 < area < img_area * 0.3:
            valid_contours.append(cnt)

    if not valid_contours:
        return 0

    # Vẽ mask chỉ chứa text contours
    text_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(text_mask, valid_contours, -1, 255, -1)

    # Dùng HoughLinesP để tìm các đường text line
    lines = cv2.HoughLinesP(text_mask, rho=1, theta=np.pi/180,
                            threshold=30, minLineLength=max(20, w//15),
                            maxLineGap=max(5, w//30))

    if lines is not None and len(lines) > 3:
        # Phân tích góc của các đường line
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) > 0:
                angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
                angles.append(angle)

        if angles:
            # Góc trung bình của text lines
            mean_angle = np.mean(angles)
            # Nếu text lines gần ngang (góc < 30° so với ngang) → 0° hoặc 180°
            if mean_angle < 30:
                # Phân biệt 0° vs 180°: so sánh mật độ text 1/4 trên vs 1/4 dưới
                q1 = text_mask[:h//4, :]
                q4 = text_mask[3*h//4:, :]
                d1 = np.sum(q1) / 255.0
                d4 = np.sum(q4) / 255.0
                # Text thường ở phần đầu tài liệu
                if d4 > d1 * 1.5 and d4 > 50:
                    return 180
                return 0
            else:
                # Text lines gần dọc → ảnh bị xoay 90° hoặc 270°
                # So sánh mật độ text nửa trái vs nửa phải
                left_half = text_mask[:, :w//2]
                right_half = text_mask[:, w//2:]
                left_density = np.sum(left_half) / 255.0
                right_density = np.sum(right_half) / 255.0
                if left_density >= right_density:
                    return 90
                else:
                    return 270

    # Fallback: nếu HoughLines không tìm đủ line, dùng phương pháp morphology
    # Kernel ngang: nối text trên cùng một dòng
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 20), 3))
    connected_h = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_h, iterations=2)

    # Kernel dọc: nối text theo cột
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, max(15, h // 20)))
    connected_v = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_v, iterations=2)

    horizontal_pixels = np.sum(connected_h) / 255.0
    vertical_pixels = np.sum(connected_v) / 255.0

    if horizontal_pixels >= vertical_pixels:
        # Text ngang: kiểm tra 180°
        q1 = connected_h[:h//4, :]
        q4 = connected_h[3*h//4:, :]
        d1 = np.sum(q1) / (q1.shape[0] * q1.shape[1])
        d4 = np.sum(q4) / (q4.shape[0] * q4.shape[1])
        if d4 > d1 * 1.5 and d4 > 0.005:
            return 180
        return 0
    else:
        # Text dọc
        left_half = connected_v[:, :w//2]
        right_half = connected_v[:, w//2:]
        left_density = np.sum(left_half) / (left_half.shape[0] * left_half.shape[1])
        right_density = np.sum(right_half) / (right_half.shape[0] * right_half.shape[1])
        if left_density >= right_density:
            return 90
        else:
            return 270


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
            from ppocr_lite import PPOcrLite
            _PPOCR_LITE_AVAILABLE = True
            print("[PPOCR-LITE] ppocr-lite loaded (lightweight fallback).")
        except ImportError:
            _PPOCR_LITE_AVAILABLE = False
            print("[PPOCR-LITE] ppocr-lite not installed. Skipping.")
    return _PPOCR_LITE_AVAILABLE

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


def preprocess_for_contour(image, method='clahe'):
    """
    Chuẩn hóa ánh sáng để cải thiện phát hiện cạnh.
    Ảnh đầu vào có thể là BGR hoặc Gray.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    if method == 'clahe':
        global _clahe_cache
        if _clahe_cache is None:
            _clahe_cache = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        return _clahe_cache.apply(gray)
    elif method == 'gamma':
        # Gamma correction: làm sáng ảnh tối, tối ảnh sáng
        mean = np.mean(gray)
        gamma = 1.0
        if mean < 80:
            gamma = 0.6
        elif mean > 180:
            gamma = 1.5
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(gray, table)
    else:
        return gray


def is_valid_document(pts, img_shape, min_area_ratio=0.02, max_area_ratio=0.95,
                      min_aspect=0.5, max_aspect=3.0):
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

# ================= YOLO Detection Functions =================
def detect_document_yolo_seg(cv_image, conf=0.15, iou=0.7, imgsz=320):
    if not YOLO_AVAILABLE or _yolo_seg_model is None:
        return None
    try:
        results = _yolo_seg_model(cv_image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)
        if results[0].masks is None:
            return None
        mask = results[0].masks.data[0].cpu().numpy()
        mask = (mask * 255).astype(np.uint8)
        # Morphological smoothing để contour mượt hơn
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        cnt = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype(np.float32)
        else:
            rect = cv2.minAreaRect(cnt)
            pts = cv2.boxPoints(rect).astype(np.float32)
        return pts
    except Exception as e:
        print(f"[YOLO-SEG] Error: {e}")
        return None

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
    """Sử dụng contour detection trong vùng bounding box để tinh chỉnh, có tiền xử lý ánh sáng."""
    x1 = int(min(bbox_pts[:, 0]))
    y1 = int(min(bbox_pts[:, 1]))
    x2 = int(max(bbox_pts[:, 0]))
    y2 = int(max(bbox_pts[:, 1]))
    # Thêm margin nhỏ để không bị sát mép
    margin = 5
    h_img, w_img = cv_image.shape[:2]
    x1 = max(0, x1 - margin)
    y1 = max(0, y1 - margin)
    x2 = min(w_img, x2 + margin)
    y2 = min(h_img, y2 + margin)
    roi = cv_image[y1:y2, x1:x2]
    if roi.size == 0:
        return bbox_pts
    # Tiền xử lý ánh sáng
    gray = preprocess_for_contour(roi, method=preprocess)
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
def detect_document_contour_canny(image, preprocess='clahe'):
    h, w = image.shape[:2]
    scale = 800.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))

    gray = preprocess_for_contour(resized, method=preprocess)

    # 🔥 sharpen (quan trọng)
    gray = cv2.addWeighted(
        gray, 1.5,
        cv2.GaussianBlur(gray, (0,0), 3),
        -0.5, 0
    )

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 🔥 nhạy hơn
    edges = cv2.Canny(blurred, 30, 150)

    # 🔥 nối cạnh mạnh hơn
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=3)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            return (approx / scale).reshape(4, 2).astype("float32")

    return None
    # doc_cnt = (doc_cnt / scale).astype("float32")
    # return doc_cnt.reshape(4, 2)

def detect_document_contour_adaptive(image, preprocess='clahe'):
    """Fallback: Adaptive threshold + morphology (đã thêm tiền xử lý ánh sáng)"""
    h, w = image.shape[:2]
    scale = 1000.0 / max(h, w)
    resized = cv2.resize(image, (int(w * scale), int(h * scale)))
    # Tiền xử lý ánh sáng trước
    gray = preprocess_for_contour(resized, method=preprocess)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
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
    """Hàm phát hiện contour chính, ưu tiên Canny, fallback adaptive"""
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
        from ppocr_lite import PPOcrLite
        # Giả sử PPOcrLite có thể trả về polygon của vùng document.
        # Bạn có thể cần tùy chỉnh theo API thực tế của thư viện.
        ocr = PPOcrLite()
        # ppocr-lite thường dùng để phát hiện text, nhưng ta có thể sử dụng
        # tính năng phát hiện biên tài liệu của PaddleOCR nếu có.
        # Ở đây ta dùng một cách đơn giản: nhận diện contour từ ảnh đã xử lý.
        # (Thực tế ppocr-lite chưa có sẵn detect document, cần cấu hình thêm)
        # Placeholder: trả về None để không crash.
        return None
    except Exception as e:
        # print(f"[PPOCR-LITE] Error: {e}")
        return None

# ================= Rotation & Background Removal =================
# ================= TESSERACT OSD (COMMENTED - replaced by OpenCV custom) =================
# def rotate_image_with_osd(cv_image):
#     """Xoay ảnh về đúng hướng văn bản bằng Tesseract OSD"""
#     if not _check_pytesseract():
#         return cv_image
#     try:
#         import pytesseract
#         from pytesseract import Output
#         rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
#         osd = pytesseract.image_to_osd(rgb, output_type=Output.DICT)
#         angle = osd['rotate']
#         if angle == 90:
#             return cv2.rotate(cv_image, cv2.ROTATE_90_CLOCKWISE)
#         elif angle == 180:
#             return cv2.rotate(cv_image, cv2.ROTATE_180)
#         elif angle == 270:
#             return cv2.rotate(cv_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         else:
#             return cv_image
#     except Exception as e:
#         print(f"[TESSERACT] OSD failed: {e}")
#         return cv_image

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

def adjust_brightness_contrast(img, brightness=15, contrast=15):
    """
    Adjust brightness and contrast of an image.
    
    Args:
        img: Input image (BGR format)
        brightness: Brightness adjustment percentage (-100 to 100)
        contrast: Contrast adjustment percentage (-100 to 100)
    
    Returns:
        Adjusted image
    """
    # Convert percentage to factor
    brightness_factor = brightness / 100.0
    contrast_factor = contrast / 100.0
    
    # Apply brightness adjustment
    if brightness != 0:
        beta = brightness_factor * 255
        img = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)
    
    # Apply contrast adjustment
    if contrast != 0:
        alpha = 1.0 + contrast_factor
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=0)
    
    return img

def apply_scan_effect(image, mode="color", threshold_method="adaptive", brightness=15, contrast=15):
    """
    Áp dụng hiệu ứng scan.
    - mode: 'color', 'gray', 'binary'
    - threshold_method: 'adaptive', 'otsu', 'simple' (chỉ dùng khi mode='binary')
    - brightness: Brightness adjustment percentage (-100 to 100)
    - contrast: Contrast adjustment percentage (-100 to 100)
    """
    # Apply brightness and contrast adjustment first
    if brightness != 0 or contrast != 0:
        image = adjust_brightness_contrast(image, brightness, contrast)
    
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
                         contour_method='canny', preprocess='clahe',
                         conf=0.15, iou=0.7, imgsz=320,
                         brightness=15, contrast=15):
    """
    Xử lý một ảnh OpenCV BGR.
    Các bước tùy chọn:
        - Xóa nền (enable_bg_removal) - thực hiện trước khi crop để có background sạch
        - Crop tài liệu (force_full=False)
        - Xoay ảnh (enable_rotation) - thực hiện sau khi crop, tập trung vào vùng tài liệu
        - Hiệu ứng scan (mode)
    Tham số bổ sung:
        conf, iou, imgsz: dành cho YOLO
        preprocess: 'clahe' hoặc 'gamma' cho tiền xử lý contour
        contour_method: 'canny' hoặc truy cập trực tiếp adaptive
        brightness: Brightness adjustment percentage (-100 to 100)
        contrast: Contrast adjustment percentage (-100 to 100)
    """
    try:
        # Bước 1: Xóa nền (nếu cần, thực hiện trước khi crop để có background sạch)
        if enable_bg_removal:
            cv_image = remove_background(cv_image)
            if cv_image.shape[2] == 4:
                cv_image = _alpha_to_solid(cv_image, solid_color=(255, 255, 255))

        # Bước 2: Crop tài liệu
        if force_full:
            warped = cv_image
        else:
            pts = None
            # Thử YOLO nếu có
            if YOLO_AVAILABLE:
                pts = detect_document_yolo_seg(cv_image, conf=conf, iou=iou, imgsz=imgsz)
                if pts is not None and not is_valid_document(pts, cv_image.shape[:2]):
                    pts = None
                if pts is None:
                    pts = detect_document_yolo_bbox(cv_image, conf=conf, iou=iou, imgsz=imgsz)
                    if pts is not None:
                        pts = refine_with_contour(cv_image, pts, preprocess=preprocess)
                        if not is_valid_document(pts, cv_image.shape[:2]):
                            pts = None
            # Fallback về OpenCV contour detection
            if pts is None:
                pts = detect_document_contour(cv_image, method=contour_method, preprocess=preprocess)
                if pts is not None and not is_valid_document(pts, cv_image.shape[:2]):
                    pts = None
            # ppocr-lite fallback
            if pts is None:
                pts = detect_document_ppocr_lite(cv_image)  # hiện tại trả None
            # Nếu vẫn không có, dùng ảnh gốc
            if pts is not None:
                warped = four_point_transform(cv_image, pts)
            else:
                warped = cv_image
                print("[INFO] No document contour found, using original image.")

        # Bước 3: Xoay ảnh (dùng OpenCV custom thay vì Tesseract OSD)
        if enable_rotation:
            warped = rotate_image_opencv(warped)

        # Bước 4: Scan effect
        result = apply_scan_effect(warped, mode, brightness=brightness, contrast=contrast)
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
                                           contour_method='canny', preprocess='clahe',
                                           conf=0.15, iou=0.7, imgsz=320,
                                           brightness=10, contrast=10):
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
                contour_method=contour_method,
                preprocess=preprocess,
                conf=conf, iou=iou, imgsz=imgsz,
                brightness=brightness, contrast=contrast
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