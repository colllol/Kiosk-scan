# Hướng dẫn Build Backend thành EXE

## Cách 1: Sử dụng build script (Đề xuất)

```bash
# Cài đặt PyInstaller nếu chưa có
pip install pyinstaller

# Chạy build script
python build_exe.py
```

Script sẽ tự động:
1. Chuẩn bị thư mục build
2. Build EXE với tất cả dependencies
3. Tạo package deployment hoàn chỉnh

## Cách 2: Build thủ công

```bash
cd backend

# Build với PyInstaller
pyinstaller --onefile --name kiosk_scan_backend ^
  --add-data "../config.json;." ^
  --hidden-import image_processor ^
  --hidden-import print_ticket ^
  --hidden-import config ^
  --hidden-import ultralytics ^
  --hidden-import pytesseract ^
  --hidden-import rembg ^
  --hidden-import rembg.models ^
  --hidden-import onnxruntime ^
  --hidden-import cv2 ^
  --hidden-import PIL ^
  --hidden-import numpy ^
  --hidden-import reportlab ^
  --hidden-import fastapi ^
  --hidden-import uvicorn ^
  --hidden-import pydantic ^
  main.py
```

## Cấu trúc sau khi build

```
dist/
└── kiosk_scan_backend.exe    # File EXE chính

deployment/                   # Package deployment hoàn chỉnh
├── kiosk_scan_backend.exe    # File EXE
├── config.json               # File cấu hình
├── start_server.bat          # Batch file để chạy
├── update_config.py          # Script kiểm tra cấu hình
├── uploads/                  # Thư mục upload (tự tạo)
├── pdfs/                     # Thư mục PDF (tự tạo)
└── README.txt               # Hướng dẫn sử dụng
```

## Cấu hình khi chạy EXE

### Vị trí file config.json
EXE sẽ tìm `config.json` theo thứ tự:
1. **Cùng thư mục với EXE** (khuyến nghị)
2. **Thư mục `config/`** trong cùng thư mục với EXE

### Ví dụ cấu hình deployment
```
C:\Deploy\KioskScan\
├── kiosk_scan_backend.exe
├── config.json              <-- Đặt ở đây
├── uploads\
└── pdfs\
```

### Cập nhật cấu hình
1. Sửa file `config.json` trong cùng thư mục với EXE
2. Khởi động lại EXE
3. Backend sẽ tự động đọc cấu hình mới

## File config.json mẫu cho deployment

```json
{
  "apiEndpoints": {
    "backend": "http://localhost:5000",
    "queueSystem": "http://27.71.20.120:2020/api/ticket/create"
  },
  "targetUrl": "https://dichvucong.thainguyen.gov.vn/thong-tin-cong-dan",
  "backendSettings": {
    "host": "0.0.0.0",
    "port": 5000,
    "uploadDir": "uploads",
    "pdfDir": "pdfs"
  },
  "extensionSettings": {
    "autoDetect": true,
    "debugMode": false,
    "timeout": 10000
  }
}
```

## Các bước deploy

### Bước 1: Build EXE
```bash
python build_exe.py
```

### Bước 2: Copy đến máy đích
Copy toàn bộ thư mục `deployment/` đến máy cần chạy.

### Bước 3: Chỉnh sửa cấu hình
Sửa file `config.json` trong thư mục deployment:
- `queueSystem`: URL của hệ thống queue thực tế
- `host`, `port`: Cấu hình server nếu cần

### Bước 4: Chạy ứng dụng
Double-click `start_server.bat` hoặc chạy `kiosk_scan_backend.exe` trực tiếp.

## Xử lý sự cố

### EXE không tìm thấy config.json
- Đảm bảo `config.json` nằm cùng thư mục với EXE
- Kiểm tra quyền đọc file

### EXE không import được module
- Thêm `--hidden-import` cho module bị thiếu
- Kiểm tra requirements.txt đã cài đặt đủ

### EXE quá lớn
Các model AI (YOLO, rembg) có thể làm EXE lớn:
- Xem xét download model khi chạy thay vì embed
- Sử dụng `--exclude-module` cho packages không cần thiết

### Lỗi khi chạy
- Kiểm tra console output để xem lỗi
- Đảm bảo đã cài đặt Visual C++ Redistributable nếu cần
- Chạy với quyền Administrator nếu cần truy cập port

## Lưu ý quan trọng

1. **Python version**: Build với cùng version Python đang phát triển
2. **Dependencies**: Cài đặt tất cả packages trong requirements.txt trước khi build
3. **Model files**: Các file model (.pt, .onnx) cần được include nếu cần
4. **Firewall**: Mở port 5000 (hoặc port đã cấu hình) trong firewall
5. **Chrome extension**: Cập nhật `chrome-extension/config.js` sau khi thay đổi `config.json`

## Tích hợp với CI/CD

Để tự động hóa build, tạo file `build.bat`:

```batch
@echo off
echo Building Kiosk Scan Backend...
echo.

REM Cài đặt dependencies
pip install -r backend/requirements.txt
pip install pyinstaller

REM Build EXE
cd backend
pyinstaller --onefile --name kiosk_scan_backend ^
  --add-data "../config.json;." ^
  --hidden-import image_processor ^
  --hidden-import print_ticket ^
  --hidden-import config ^
  --hidden-import ultralytics ^
  --hidden-import pytesseract ^
  --hidden-import rembg ^
  --hidden-import rembg.models ^
  --hidden-import onnxruntime ^
  --hidden-import cv2 ^
  --hidden-import PIL ^
  --hidden-import numpy ^
  --hidden-import reportlab ^
  --hidden-import fastapi ^
  --hidden-import uvicorn ^
  --hidden-import pydantic ^
  main.py

echo.
echo Build completed!
echo EXE location: dist\kiosk_scan_backend.exe
pause
```