"""
Image Processing Module
Xử lý ảnh thành dạng scan tài liệu đen trắng
Hỗ trợ:
- Phát hiện góc tài liệu
- Chỉnh sửa góc nhìn (perspective correction)
- Tăng cường ảnh scan

Note: OpenCV is lazy-loaded to improve startup time
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# Lazy load OpenCV - only import when actually needed
CV2_AVAILABLE = False
_clahe_cache = None  # Cache CLAHE object to avoid recreating

def _load_cv2():
    """Lazy load OpenCV to improve startup time"""
    global CV2_AVAILABLE
    if not CV2_AVAILABLE:
        try:
            global cv2
            import cv2
            CV2_AVAILABLE = True
        except ImportError:
            print("OpenCV not available, using fallback methods")
    return CV2_AVAILABLE


def process_scanned_images_batch(image_list):
    """
    Xử lý batch nhiều ảnh song song với đa luồng
    Args:
        image_list: List các ảnh PIL
    Returns:
        List các ảnh đã xử lý (giữ nguyên chất lượng gốc, chỉ xoay nếu cần)
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    start_time = time.time()
    print(f"[IMG] Starting batch processing of {len(image_list)} image(s) with multi-threading...")

    results = [None] * len(image_list)
    
    # Sử dụng ThreadPoolExecutor để xử lý song song
    # Số worker = số CPU cores (tối ưu cho I/O bound tasks)
    import os
    max_workers = min(os.cpu_count() or 4, len(image_list))
    print(f"[IMG] Using {max_workers} worker thread(s)")

    def process_single(args):
        idx, img = args
        img_start = time.time()
        try:
            # Chỉ giữ nguyên ảnh, không xử lý tăng sáng/tương phản
            result = process_scanned_image(img)
            print(f"[IMG] Processed image {idx} in {time.time() - img_start:.3f}s")
            return idx, result
        except Exception as e:
            print(f"[IMG] Error processing image {idx}: {e}")
            # Fallback to original image to ensure no image is skipped
            return idx, img

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single, (i, img)): i
                   for i, img in enumerate(image_list)}

        for future in as_completed(futures):
            try:
                idx, processed_img = future.result()
                results[idx] = processed_img
            except Exception as e:
                print(f"[IMG] Error getting result: {e}")
                # Ensure no image is skipped - use original
                results[futures[future]] = image_list[futures[future]]

    # Verify all images were processed
    for i, result in enumerate(results):
        if result is None:
            print(f"[IMG] Warning: Image {i} was not processed, using original")
            results[i] = image_list[i]

    print(f"[IMG] Batch processing completed in {time.time() - start_time:.3f}s\n")
    return results


def process_scanned_image(image):
    """
    Xử lý ảnh thành dạng scan tài liệu đen trắng
    Sử dụng OpenCV nếu có, nếu không dùng Pillow fallback
    """
    # Lazy load OpenCV only when processing first image
    if _load_cv2():
        return process_with_opencv(image)
    else:
        return process_with_pillow(image)

def process_with_opencv(pil_image):
    """
    Xử lý ảnh dùng OpenCV - phương pháp nâng cao
    Tối ưu: Cache CLAHE, giảm split/merge, gộp operations
    """
    try:
        # Convert PIL to OpenCV format
        cv_image = pil_to_cv2(pil_image)

        # Process document
        processed = process_document(cv_image)

        # Convert back to PIL
        return cv2_to_pil(processed)

    except Exception as e:
        print(f"OpenCV processing error: {e}")
        return process_with_pillow(pil_image)


def process_document(image):
    """
    Main pipeline: Process image for PDF output
    Tăng sáng và tương phản nhẹ, giảm nhiễu, tránh over-processing
    """
    try:
        # Step 1: Apply Gaussian blur để giảm nhiễu (kernel lớn hơn)
        blurred = cv2.GaussianBlur(image, (5, 5), 0)

        # Step 2: Apply unsharp masking nhẹ hơn (alpha=0.5 thay vì 1.0)
        alpha = 0.5  # Giảm sharpening để tránh nhiễu
        sharpened = cv2.addWeighted(image, 1 + alpha, blurred, -alpha, 0)

        # Step 3: Convert to LAB color space
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)

        # Step 4: Apply CLAHE nhẹ hơn (clipLimit=1.2 thay vì 1.5)
        global _clahe_cache
        if _clahe_cache is None:
            _clahe_cache = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
        clahe = _clahe_cache

        # Xử lý trực tiếp trên kênh L (index 0)
        l_channel = lab[:, :, 0]
        l_enhanced = clahe.apply(l_channel)
        lab[:, :, 0] = l_enhanced  # Gán trực tiếp, không cần merge

        # Step 5: Convert back to BGR
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Step 6: Tăng sáng + contrast nhẹ hơn
        # Brightness: 1.15x (giảm từ 1.3x)
        # Contrast: 1.1x (giảm từ 1.15x)
        # Gộp thành: alpha = 1.15 * 1.1 = 1.265
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.265, beta=0)

        return enhanced
    except Exception as e:
        print(f"Error in process_document: {e}")
        return image
# def crop_by_text_region(image):
#     """
#     Cắt ảnh dựa trên vùng chữ (dùng threshold, dilation, contour lớn nhất)
#     Trả về ảnh đã cắt (vẫn giữ màu)
#     """
#     # Chuyển sang grayscale
#     if len(image.shape) == 3:
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     else:
#         gray = image

#     # Làm mờ
#     blurred = cv2.GaussianBlur(gray, (5,5), 0)

#     # Threshold nhị phân (chữ trắng trên nền đen)
#     _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

#     # Giãn nở để nối các vùng chữ
#     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
#     dilated = cv2.dilate(thresh, kernel, iterations=2)

#     # Tìm contour
#     contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     if not contours:
#         return image  # Không tìm thấy contour nào

#     # Lấy contour lớn nhất
#     largest_contour = max(contours, key=cv2.contourArea)
#     x, y, w, h = cv2.boundingRect(largest_contour)

#     # Cắt ảnh gốc (màu)
#     cropped = image[y:y+h, x:x+w]
#     return cropped

def order_points(pts):
    """
    Orders coordinates: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left: smallest sum, bottom-right: largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Top-right: smallest difference, bottom-left: largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


# def detect_document_corners(image):
#     """
#     Detects the 4 corners of the document in the image.
#     """
#     
#     # Convert to grayscale for edge detection only
#     if len(image.shape) == 3:
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     else:
#         gray = image
#     
#     # Edge detection
#     edged = cv2.Canny(gray, 50, 150)
#     
#     # 3. Find contours
#     contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
#     contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
#     
#     document_contour = None
#     
#     for c in contours:
#         peri = cv2.arcLength(c, True)
#         approx = cv2.approxPolyDP(c, 0.02 * peri, True)
#         
#         if len(approx) == 4:
#             document_contour = approx
#             break
            
#     if document_contour is None:
#         raise ValueError("Could not find document contours")
        
#     pts = document_contour.reshape(4, 2)
#     return order_points(pts)


# def correct_perspective(image, pts):
#     """
#     Applies a perspective warp to flatten the document.
#     """
#     (tl, tr, br, bl) = pts
#     
#     # Compute width
#     widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
#     widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
#     maxWidth = max(int(widthA), int(widthB))
#     
#     # Compute height
#     heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
#     heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
#     maxHeight = max(int(heightA), int(heightB))
#     
#     # Destination points
#     dst = np.array([
#         [0, 0],
#         [maxWidth - 1, 0],
#         [maxWidth - 1, maxHeight - 1],
#         [0, maxHeight - 1]
#     ], dtype="float32")
#     
#     # Perspective transform
#     M = cv2.getPerspectiveTransform(pts, dst)
#     warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
#     
#     return warped


def enhance_document(image):
    """
    Enhances the document image using adaptive thresholding.
    Handles uneven lighting better than simple threshold.
    """
    # Return original color image (skip B&W conversion)
    # if len(image.shape) == 3:
    #     return cv2.cvtColor(image, cv2.COLOR_BGR)
    # else:
    return image
    
    # # Original B&W conversion code (commented)
    # if len(image.shape) == 3:
    #     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # else:
    #     gray = image
    # 
    # # Adaptive thresholding
    # enhanced = cv2.adaptiveThreshold(
    #     gray, 255, 
    #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    #     cv2.THRESH_BINARY, 
    #     21, 10
    # )
    # 
    # return enhanced


def process_with_pillow(image):
    """
    Fallback: Xử lý ảnh dùng Pillow
    Tăng sáng và tương phản nhẹ, giảm nhiễu
    """
    try:
        # Convert to RGB if needed (keep color)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Nhẹ nhàng sharpening (giảm từ 1.2x xuống 1.1x)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)

        # Nhẹ nhàng contrast (giảm từ 1.15x xuống 1.08x)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.08)

        # Tăng sáng nhẹ (giảm từ 1.3x xuống 1.15x)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.15)

        # Nhẹ nhàng color saturation (giảm từ 1.1x xuống 1.05x)
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.05)

        return image

    except Exception as e:
        print(f"Pillow processing error: {e}")
        # Return original image if processing fails
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image


# === Utility Functions ===

def pil_to_cv2(pil_image):
    """Convert PIL Image to OpenCV format"""
    if pil_image.mode == 'L':
        return np.array(pil_image)
    elif pil_image.mode == 'RGBA':
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)
    else:
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv_image):
    """Convert OpenCV image to PIL format"""
    if len(cv_image.shape) == 2:
        # Grayscale
        return Image.fromarray(cv_image, mode='L')
    else:
        # Color
        return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))


def resize_to_a4(image, max_width=1700):
    """Resize ảnh với kích thước phù hợp cho A4"""
    width, height = image.size
    
    if width > max_width:
        ratio = max_width / width
        new_width = max_width
        new_height = int(height * ratio)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return image


def convert_to_grayscale(image):
    """Chuyển ảnh sang grayscale"""
    if image.mode != 'L':
        return image.convert('L')
    return image


def apply_contrast(image, factor=1.5):
    """Tăng contrast của ảnh"""
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)


def apply_brightness(image, factor=1.1):
    """Tăng brightness của ảnh"""
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)