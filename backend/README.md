# Backend FastAPI - Webcam Scan Document

## Cài đặt

### 1. Cài đặt dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Chạy backend server
```bash
python main.py
```

Hoặc sử dụng uvicorn trực tiếp:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

## API Endpoints

### GET `/`
Root endpoint
- Trả về thông tin API đang chạy

### POST `/api/upload`
Upload ảnh lên server

**Request:**
- `file`: File ảnh (multipart/form-data)

**Response:**
```json
{
  "id": "uuid-here",
  "message": "Upload thành công",
  "preview": "data:image/jpeg;base64,..."
}
```

### POST `/api/export`
Export ảnh đã upload thành PDF

**Request:**
```json
{
  "ids": ["uuid-1", "uuid-2"],
  "filename": "tùy_chọn.pdf"
}
```

**Response:**
- File PDF được tải về
- Filename format: `YYYYMMDD_HHMMSS_document.pdf`

### GET `/api/images`
Lấy danh sách ảnh đã upload

**Response:**
```json
{
  "count": 2,
  "images": [...]
}
```

### DELETE `/api/clear`
Xóa tất cả ảnh đã upload

## Cấu trúc thư mục

```
backend/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies
├── uploads/             # Thư mục lưu ảnh upload (auto-created)
└── pdfs/                # Thư mục lưu PDF files (auto-created)
```

## Flow hoạt động

1. **Frontend chụp ảnh** → Lưu tạm ở browser (blob)
2. **Nhấn "Tạo PDF"** → Frontend upload từng ảnh lên `/api/upload`
3. **Backend lưu ảnh** → Vào thư mục `uploads/` với unique ID
4. **Backend trả về ID** → Frontend lưu danh sách IDs
5. **Frontend gọi export** → Gửi IDs lên `/api/export`
6. **Backend tạo PDF** → Dùng ReportLab, resize ảnh theo A4, tạo multi-page PDF
7. **Backend lưu PDF** → Vào thư mục `pdfs/` với format `YYYYMMDD_HHMMSS_document.pdf`
8. **Backend trả file** → Frontend download về máy người dùng

## Đặc tính

- **PDF Format:** A4 size, tự động center ảnh
- **Filename:** Format STT_DATETIME (YYYYMMDD_HHMMSS)
- **Support formats:** JPG, JPEG, PNG
- **Multi-page PDF:** Hỗ trợ nhiều trang
- **CORS:** Đã cấu hình cho cross-origin requests

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- Pillow - Xử lý ảnh
- ReportLab - Tạo PDF
