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
    Tăng 15% độ sáng, giữ nguyên chất lượng ảnh gốc
    """
    try:
        # Step 1: Apply slight Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(image, (3, 3), 0)

        # Step 2: Apply mild unsharp masking for sharpness
        alpha = 1.0  # Mild sharpening
        sharpened = cv2.addWeighted(image, 1 + alpha, blurred, -alpha, 0)

        # Step 3: Convert to LAB color space for better processing
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Step 4: Apply mild CLAHE for slight contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        # Step 5: Merge channels back
        merged = cv2.merge((cl, a, b))

        # Step 6: Convert back to BGR
        enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        # Step 7: Tăng 15% độ sáng
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.25, beta=0)

        # Step 8: Tăng nhẹ contrast (5%)
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.15, beta=0)

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
    Tăng 15% độ sáng, giữ nguyên chất lượng ảnh gốc
    """
    try:
        # Convert to RGB if needed (keep color)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Mild sharpness for clarity
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)  # 1.2x sharpness

        # Very mild contrast (5%)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.15)  # 1.15x contrast

        # Tăng 15% độ sáng
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.3)  # 1.3x brightness

        # Mild color saturation
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)  # 1.1x color saturation

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