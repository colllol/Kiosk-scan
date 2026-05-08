# Hướng dẫn Khởi động Hệ thống Kiosk Scan

## Các Script Khởi động

### 1. `start_Kiosk.bat` - Khởi động toàn bộ hệ thống
```bash
start_Kiosk.bat
```
**Chức năng:**
- Khởi động backend EXE (port 5000)
- Khởi động frontend server (port 3000) nếu có Node.js
- Tự động mở trình duyệt đến frontend
- Kiểm tra trạng thái các service
- Dừng tất cả service khi nhấn phím

**Yêu cầu:**
- Backend đã được build thành EXE
- Frontend đã setup (có `package.json`)
- Node.js/npm (cho frontend)

### 2. `start_Backend_Only.bat` - Chỉ khởi động backend
```bash
start_Backend_Only.bat
```
**Chức năng:**
- Chỉ khởi động backend EXE
- Hiển thị log trực tiếp trong console
- Tự động tạo thư mục uploads/pdfs
- Kiểm tra và tạo config.json nếu cần

**Yêu cầu:**
- Backend đã được build thành EXE

## Các bước Triển khai

### Bước 1: Build Backend EXE
```bash
cd backend
build.bat
```
hoặc
```bash
cd backend
build_simple.bat
```

### Bước 2: Cấu hình
1. Sửa file `config.json` ở thư mục gốc nếu cần
2. EXE sẽ tự động tìm `config.json` trong cùng thư mục

### Bước 3: Khởi động
- **Có frontend**: Chạy `start_Kiosk.bat`
- **Chỉ backend**: Chạy `start_Backend_Only.bat`

## Cấu trúc Thư mục Sau khi Build

```
Kiosk-scan/
├── backend/
│   ├── dist/
│   │   └── WebcamScan/          # Thư mục EXE sau build
│   │       ├── WebcamScan.exe   # File EXE chính
│   │       ├── config.json      # File cấu hình (copy từ gốc)
│   │       ├── uploads/         # Thư mục upload ảnh
│   │       └── pdfs/            # Thư mục lưu PDF
│   ├── build.bat               # Script build đầy đủ
│   └── build_simple.bat        # Script build đơn giản
├── frontend/                   # Frontend React/Vue (nếu có)
├── config.json                 # File cấu hình chính
├── start_Kiosk.bat            # Script khởi động toàn hệ thống
├── start_Backend_Only.bat     # Script chỉ khởi động backend
└── STARTUP_GUIDE.md           # Hướng dẫn này
```

## URL Truy cập

Sau khi khởi động thành công:

### Backend API
- **API Server**: http://localhost:5000
- **API Documentation**: http://localhost:5000/docs
- **Health Check**: http://localhost:5000/

### Frontend (nếu có)
- **Frontend**: http://localhost:3000

## Kiểm tra Trạng thái

### Kiểm tra backend đang chạy
```bash
curl http://localhost:5000
```
Kết quả mong đợi:
```json
{"message": "Webcam Scan Document API is running"}
```

### Kiểm tra frontend đang chạy
```bash
curl http://localhost:3000
```

## Xử lý Sự cố

### 1. Backend không khởi động
- Kiểm tra port 5000 đã bị chiếm chưa: `netstat -ano | findstr :5000`
- Kiểm tra file `config.json` có trong cùng thư mục EXE không
- Kiểm tra log console để xem lỗi

### 2. Frontend không khởi động
- Kiểm tra Node.js đã cài: `node --version`
- Kiểm tra frontend dependencies: `cd frontend && npm install`
- Kiểm tra port 3000 đã bị chiếm chưa

### 3. Browser không mở được
- Mở thủ công: http://localhost:3000 hoặc http://localhost:5000
- Kiểm tra firewall cho phép truy cập localhost

### 4. EXE không tìm thấy config.json
- Copy `config.json` từ thư mục gốc vào cùng thư mục với EXE
- Hoặc đặt trong thư mục `config\` cùng cấp với EXE

## Tự động khởi động với Windows

### Tạo shortcut tự động
1. Tạo shortcut của `start_Kiosk.bat`
2. Đặt shortcut vào Startup folder:
   - `Win + R` → `shell:startup`
   - Copy shortcut vào thư mục này

### Tạo Windows Service (Nâng cao)
Sử dụng NSSM (Non-Sucking Service Manager):
```bash
nssm install KioskBackend "C:\Path\To\WebcamScan.exe"
nssm set KioskBackend AppDirectory "C:\Path\To\WebcamScan"
nssm start KioskBackend
```

## Dừng Dịch vụ

### Tự động (qua script)
- Nhấn phím bất kỳ trong console đang chạy script
- Script sẽ tự động dừng tất cả service

### Thủ công
```bash
# Dừng backend
taskkill /F /IM "WebcamScan.exe"

# Dừng frontend (Node.js)
taskkill /F /IM "node.exe"
```

## Lưu ý Quan trọng

1. **Lần đầu chạy**: Có thể chậm do download AI models
2. **Firewall**: Cho phép truy cập port 5000 và 3000
3. **Quyền Administrator**: Cần cho việc truy cập webcam và in ấn
4. **Chrome Extension**: Cần reload sau khi thay đổi config.json
5. **Dữ liệu**: File upload và PDF lưu trong thư mục `uploads/` và `pdfs/`

## Tối ưu hóa

### Giảm bộ nhớ
- Build với `--onedir` thay vì `--onefile` để khởi động nhanh hơn
- Sử dụng `--noupx` để giảm thời gian unpack

### Tự động khôi phục
Tạo file `auto_restart.bat` để tự động khởi động lại nếu crash:
```batch
@echo off
:restart
echo Starting Kiosk System...
call start_Backend_Only.bat
echo System crashed, restarting in 5 seconds...
timeout /t 5
goto restart
```