# Image Processing Module - Tài liệu

## Cấu trúc Module

```
backend/
├── main.py              # FastAPI app
└── image_processor.py   # Xử lý ảnh
```

## Tính năng

### 1. Phát hiện góc tài liệu (Document Corner Detection)
```python
corners = detect_document_corners(image)
```
- Chuyển ảnh sang grayscale
- Làm mờ Gaussian
- Phát hiện cạnh bằng Canny
- Tìm contour có 4 điểm (góc tài liệu)

### 2. Chỉnh sửa góc nhìn (Perspective Correction)
```python
warped = correct_perspective(image, corners)
```
- Tính toán kích thước mới
- Áp dụng perspective transform
- Làm phẳng tài liệu

### 3. Tăng cường ảnh scan (Document Enhancement)
```python
enhanced = enhance_document(warped)
```
- Adaptive thresholding
- Xử lý ánh sáng không đều
- Tạo ảnh đen trắng rõ nét

## Pipeline xử lý

```
Ảnh gốc (PIL)
    ↓
Convert to OpenCV format
    ↓
Detect document corners
    ↓ (nếu tìm thấy)
Correct perspective
    ↓
Adaptive thresholding
    ↓
Convert back to PIL
    ↓
Ảnh scan đen trắng
```

## Thư viện sử dụng

| Thư viện | Chức năng |
|----------|-----------|
| OpenCV (cv2) | Xử lý ảnh nâng cao |
| NumPy | Mảng số |
| Pillow | Đọc/ghi ảnh |
| SciPy | Fallback methods |

## Cài đặt

```bash
pip install opencv-python numpy scipy Pillow
# Hoặc:
pip install -r requirements.txt
```

## Fallback

Nếu không có OpenCV, module sẽ tự động dùng phương pháp Pillow + SciPy đơn giản hơn.

## API

### `process_scanned_image(image)`
Xử lý ảnh thành dạng scan đen trắng.

**Input:** PIL Image
**Output:** PIL Image (RGB)

### `detect_document_corners(image)`
Phát hiện 4 góc của tài liệu.

**Input:** OpenCV image (BGR)
**Output:** 4 điểm góc (numpy array)

### `correct_perspective(image, pts)`
Chỉnh sửa góc nhìn.

**Input:** 
- OpenCV image
- 4 điểm góc

**Output:** OpenCV image đã chỉnh

### `enhance_document(image)`
Tăng cường ảnh scan.

**Input:** OpenCV image
**Output:** OpenCV image (grayscale, binary)

## Lưu ý

- Adaptive thresholding với block_size=21, C=10
- Gaussian blur (5x5) trước khi detect edges
- Canny edge detection: 75-200 threshold
- Contour approximation: 2% perimeter
