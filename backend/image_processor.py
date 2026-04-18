"""
Image Processing Module
Xử lý ảnh thành dạng scan tài liệu
- Giữ nguyên đa luồng & tăng sáng từ image_processor.py
- Thay thế phần cắt/phối cảnh/trim bằng pipeline từ img-anh.py
"""
import numpy as np
from PIL import Image, ImageEnhance
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

CV2_AVAILABLE = False
_clahe_cache = None

def _load_cv2():
    """Lazy load OpenCV"""
    global CV2_AVAILABLE
    if not CV2_AVAILABLE:
        try:
            global cv2
            import cv2
            CV2_AVAILABLE = True
        except ImportError:
            print("OpenCV not available, using fallback methods")
    return CV2_AVAILABLE

# ============================================================================
# FUNCTIONS TỪ img-anh.py (Đã chuẩn hóa cú pháp & thích nghi numpy/cv2)
# ============================================================================

def sap_xep_4_diem(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    tong = points.sum(axis=1)
    hieu = np.diff(points, axis=1)
    rect[0] = points[np.argmin(tong)]
    rect[1] = points[np.argmin(hieu)]
    rect[2] = points[np.argmax(tong)]
    rect[3] = points[np.argmax(hieu)]
    return rect

def smooth_1d(values: np.ndarray, window_size: int) -> np.ndarray:
    window_size = max(3, window_size | 1)
    kernel = np.ones(window_size, dtype=np.float32) / float(window_size)
    return np.convolve(values.astype(np.float32), kernel, mode="same")

def cat_sat_vung_giay_trang(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    image_area = float(h * w)
    best_rect = None
    best_score = -1.0

    for threshold_value in (220, 200, 180, 160, 140):
        mask = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8), iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < image_area * 0.2: continue
            x, y, bw, bh = cv2.boundingRect(contour)
            rect_area = float(bw * bh)
            if rect_area <= 0: continue
            fill_ratio = area / rect_area
            if fill_ratio < 0.72: continue
            area_ratio = rect_area / image_area
            if area_ratio < 0.35: continue
            score = area_ratio * 2.0 + fill_ratio
            if score > best_score:
                best_score = score
                best_rect = (x, y, x + bw - 1, y + bh - 1)

    if best_rect is None: return image
    x1, y1, x2, y2 = best_rect
    inset_x = max(3, int((x2 - x1 + 1) * 0.004))
    inset_y = max(3, int((y2 - y1 + 1) * 0.004))
    x1 = min(max(0, x1 + inset_x), w - 1)
    y1 = min(max(0, y1 + inset_y), h - 1)
    x2 = max(0, min(w - 1, x2 - inset_x))
    y2 = max(0, min(h - 1, y2 - inset_y))
    if x2 <= x1 or y2 <= y1: return image
    return image[y1 : y2 + 1, x1 : x2 + 1]

def trim_theo_mat_do_sang(image: np.ndarray, gray_threshold: int = 180, density_threshold: float = 0.45, inset_ratio: float = 0.003) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    bright = (gray >= gray_threshold).astype(np.uint8)
    row_ratio = bright.mean(axis=1)
    col_ratio = bright.mean(axis=0)
    rows = np.where(row_ratio >= density_threshold)[0]
    cols = np.where(col_ratio >= density_threshold)[0]
    if len(rows) == 0 or len(cols) == 0: return image
    y1, y2, x1, x2 = int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])
    inset_x = max(2, int(w * inset_ratio))
    inset_y = max(2, int(h * inset_ratio))
    x1 = min(max(0, x1 + inset_x), w - 1)
    y1 = min(max(0, y1 + inset_y), h - 1)
    x2 = max(0, min(w - 1, x2 - inset_x))
    y2 = max(0, min(h - 1, y2 - inset_y))
    if x2 <= x1 or y2 <= y1: return image
    return image[y1 : y2 + 1, x1 : x2 + 1]

def trim_dai_vien_toi(image: np.ndarray, min_mean: float = 150.0, min_bright_ratio: float = 0.55) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    y1 = int(h * 0.08)
    y2 = max(y1 + 1, int(h * 0.92))
    x1 = int(w * 0.08)
    x2 = max(x1 + 1, int(w * 0.92))
    center_cols = gray[y1:y2, :]
    center_rows = gray[:, x1:x2]
    col_mean = center_cols.mean(axis=0)
    row_mean = center_rows.mean(axis=1)
    col_bright_ratio = (center_cols >= 180).mean(axis=0)
    row_bright_ratio = (center_rows >= 180).mean(axis=1)

    left = 0
    while left < w - 1 and (col_mean[left] < min_mean or col_bright_ratio[left] < min_bright_ratio): left += 1
    right = w - 1
    while right > 0 and (col_mean[right] < min_mean or col_bright_ratio[right] < min_bright_ratio): right -= 1
    top = 0
    while top < h - 1 and (row_mean[top] < min_mean or row_bright_ratio[top] < min_bright_ratio): top += 1
    bottom = h - 1
    while bottom > 0 and (row_mean[bottom] < min_mean or row_bright_ratio[bottom] < min_bright_ratio): bottom -= 1

    if right <= left or bottom <= top: return image
    inset_x = max(2, int((right - left + 1) * 0.002))
    inset_y = max(2, int((bottom - top + 1) * 0.002))
    left = min(max(0, left + inset_x), w - 1)
    right = max(0, min(w - 1, right - inset_x))
    top = min(max(0, top + inset_y), h - 1)
    bottom = max(0, min(h - 1, bottom - inset_y))
    if right <= left or bottom <= top: return image
    return image[top : bottom + 1, left : right + 1]

def tim_bien_trang_theo_profile(image: np.ndarray):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    y1_scan = int(h * 0.30)
    y2_scan = int(h * 0.90)
    col_profile = gray[y1_scan:y2_scan, :].mean(axis=0)
    col_smooth = smooth_1d(col_profile, max(31, w // 45))
    col_grad = np.diff(col_smooth)
    left_search = slice(int(w * 0.05), int(w * 0.45))
    right_search = slice(int(w * 0.55), int(w * 0.95))
    left = left_search.start + int(np.argmax(col_grad[left_search]))
    right = right_search.start + int(np.argmin(col_grad[right_search]))
    if right - left < int(w * 0.35): return None

    x1_scan = int(left + (right - left) * 0.12)
    x2_scan = int(right - (right - left) * 0.12)
    row_profile = gray[:, x1_scan:x2_scan].mean(axis=1)
    row_smooth = smooth_1d(row_profile, max(31, h // 45))
    row_grad = np.diff(row_smooth)
    top_search = slice(int(h * 0.12), int(h * 0.50))
    bottom_search = slice(int(h * 0.55), int(h * 0.98))
    top = top_search.start + int(np.argmax(row_grad[top_search]))
    bottom = bottom_search.start + int(np.argmin(row_grad[bottom_search]))
    if bottom - top < int(h * 0.35): return None

    inset_x = max(4, int((right - left) * 0.01))
    inset_top = max(4, int((bottom - top) * 0.006))
    inset_bottom = max(8, int((bottom - top) * 0.01))
    left = max(0, left + inset_x)
    right = min(w - 1, right - inset_x)
    top = max(0, top + inset_top)
    bottom = min(h - 1, bottom - inset_bottom)
    if right <= left or bottom <= top: return None
    return left, top, right, bottom

def uoc_luong_khung_tu_vung_chu(image: np.ndarray):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    image_area = float(h * w)
    text_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15)
    text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
    boxes = []
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats[i]
        area_ratio = area / image_area
        if area_ratio < 0.00001 or area_ratio > 0.02: continue
        if bw < 2 or bh < 4: continue
        if bw > w * 0.4 or bh > h * 0.15: continue
        if area / float(max(bw * bh, 1)) < 0.08: continue
        boxes.append((x, y, x + bw - 1, y + bh - 1))
    if not boxes: return None
    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[2] for box in boxes)
    y2 = max(box[3] for box in boxes)
    x1 = max(0, x1 - int((x2 - x1 + 1) * 0.45))
    y1 = max(0, y1 - int((y2 - y1 + 1) * 0.60))
    x2 = min(w - 1, x2 + int((x2 - x1 + 1) * 0.45))
    y2 = min(h - 1, y2 + int((y2 - y1 + 1) * 0.60))
    quad_area_ratio = ((x2 - x1 + 1) * (y2 - y1 + 1)) / image_area
    if quad_area_ratio < 0.2: return None
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype="float32")

def tim_khung_tai_lieu(image: np.ndarray):
    text_quad = uoc_luong_khung_tu_vung_chu(image)
    if text_quad is not None: return text_quad
    
    image_area = float(image.shape[0] * image.shape[1])
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    white_mask = cv2.inRange(hsv, (0, 0, 100), (180, 90, 255))
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8), iterations=2)

    best_quad = None
    best_score = -1.0
    for mask in (white_mask, edges, binary):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            area_ratio = area / image_area
            if area_ratio < 0.15 or area_ratio > 0.98: continue
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approx) == 4:
                quad = approx.reshape(4, 2).astype("float32")
            else:
                rect = cv2.minAreaRect(contour)
                quad = cv2.boxPoints(rect).astype("float32")
            ordered = sap_xep_4_diem(quad)
            width = max(np.linalg.norm(ordered[2] - ordered[3]), np.linalg.norm(ordered[1] - ordered[0]))
            height = max(np.linalg.norm(ordered[1] - ordered[2]), np.linalg.norm(ordered[0] - ordered[3]))
            if min(width, height) < 50: continue
            aspect = max(width, height) / max(min(width, height), 1.0)
            if aspect > 2.5: continue
            score = area_ratio - abs(aspect - 1.41) * 0.08
            if score > best_score:
                best_score = score
                best_quad = quad
    return best_quad  # Trả về None thay vì raise lỗi để pipeline fallback an toàn

def cat_va_nan_phoi_canh(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    rect = sap_xep_4_diem(quad)
    tl, tr, br, bl = rect
    max_width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    max_height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]], dtype="float32"
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))

# ============================================================================
# PIPELINE KẾT HỢP (img-anh crop/trim + brightness enhancement)
# ============================================================================

def apply_brightness_enhancement(cv_image: np.ndarray) -> np.ndarray:
    """Giữ nguyên logic tăng sáng/tương phản/CLAHE từ image_processor.py"""
    try:
        blurred = cv2.GaussianBlur(cv_image, (5, 5), 0)
        alpha = 0.5
        sharpened = cv2.addWeighted(cv_image, 1 + alpha, blurred, -alpha, 0)
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        
        global _clahe_cache
        if _clahe_cache is None:
            _clahe_cache = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
            
        l_channel = lab[:, :, 0]
        l_enhanced = _clahe_cache.apply(l_channel)
        lab[:, :, 0] = l_enhanced
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return cv2.convertScaleAbs(enhanced, alpha=1.44, beta=10)
    except Exception as e:
        print(f"[ENHANCE] Error: {e}")
        return cv_image

def process_single_cv_image(cv_image: np.ndarray) -> np.ndarray:
    """Chạy pipeline chính: img-anh crop/trim -> tăng sáng"""
    try:
        # 1. Cắt/phối cảnh/trim (từ img-anh.py)
        white_rect = tim_bien_trang_theo_profile(cv_image)
        if white_rect is not None:
            x1, y1, x2, y2 = white_rect
            processed = cv_image[y1:y2+1, x1:x2+1]
        else:
            quad = tim_khung_tai_lieu(cv_image)
            if quad is not None:
                processed = cat_va_nan_phoi_canh(cv_image, quad)
            else:
                processed = cv_image.copy()
                
        processed = cat_sat_vung_giay_trang(processed)
        processed = trim_theo_mat_do_sang(processed)
        processed = trim_dai_vien_toi(processed)
        
        # 2. Tăng sáng/tương phản (từ image_processor.py)
        processed = apply_brightness_enhancement(processed)
        return processed
    except Exception as e:
        print(f"[PIPELINE] Fallback to original due to error: {e}")
        return cv_image.copy()

# ============================================================================
# UTILITIES & MULTI-THREADING BATCH PROCESSING
# ============================================================================

def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    if pil_image.mode == 'L': return np.array(pil_image)
    if pil_image.mode == 'RGBA': return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def cv2_to_pil(cv_image: np.ndarray) -> Image.Image:
    if len(cv_image.shape) == 2:
        return Image.fromarray(cv_image, mode='L')
    return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

def process_with_pillow(image: Image.Image) -> Image.Image:
    """Fallback khi không có OpenCV"""
    try:
        if image.mode != 'RGB': image = image.convert('RGB')
        image = ImageEnhance.Sharpness(image).enhance(1.2)
        image = ImageEnhance.Contrast(image).enhance(1.15)
        image = ImageEnhance.Brightness(image).enhance(1.25)
        return image
    except:
        return image

def process_scanned_images_batch_with_crop(image_list: list) -> list:
    """
    Xử lý batch đa luồng. Giữ nguyên cấu trúc từ image_processor.py.
    """
    if not image_list: return []
    
    start_time = time.time()
    print(f"[IMG] Starting batch processing with auto-crop & enhance of {len(image_list)} image(s)...")
    results = [None] * len(image_list)
    max_workers = min(os.cpu_count() or 4, len(image_list))
    print(f"[IMG] Using {max_workers} worker thread(s)")

    def process_single(args):
        idx, pil_img = args
        try:
            if _load_cv2():
                cv_img = pil_to_cv2(pil_img)
                processed_cv = process_single_cv_image(cv_img)
                return idx, cv2_to_pil(processed_cv)
            else:
                return idx, process_with_pillow(pil_img)
        except Exception as e:
            print(f"[IMG] Error processing image {idx}: {e}")
            return idx, pil_img

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single, (i, img)): i for i, img in enumerate(image_list)}
        for future in as_completed(futures):
            try:
                idx, res = future.result()
                results[idx] = res
            except Exception as e:
                print(f"[IMG] Thread error: {e}")
                results[futures[future]] = image_list[futures[future]]

    for i, res in enumerate(results):
        if res is None:
            results[i] = image_list[i]

    print(f"[IMG] Batch processing completed in {time.time() - start_time:.3f}s\n")
    return results