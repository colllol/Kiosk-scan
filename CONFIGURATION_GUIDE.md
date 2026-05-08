# Hướng dẫn Cấu hình Hệ thống Kiosk Scan

## Tổng quan

Hệ thống hiện sử dụng file cấu hình tập trung `config.json` ở thư mục gốc để quản lý tất cả các cài đặt cho cả backend và chrome-extension.

## Cấu trúc File

```
Kiosk-scan/
├── config.json                    # File cấu hình chính
├── update_config.py              # Script đồng bộ cấu hình
├── CONFIGURATION_GUIDE.md        # Hướng dẫn này
├── backend/
│   ├── config.py                # Module đọc cấu hình cho backend
│   └── main.py                  # Backend chính (đã cập nhật)
└── chrome-extension/
    ├── config.js                # File cấu hình cho extension
    └── background.js            # Extension background (đã cập nhật)
```

## File config.json

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

### Giải thích các tham số:

1. **apiEndpoints**
   - `backend`: URL của backend server (mặc định: http://localhost:5000)
   - `queueSystem`: URL của hệ thống queue để gửi ticket

2. **targetUrl**: URL mục tiêu để chrome-extension theo dõi

3. **backendSettings**
   - `host`: Host để bind backend server (0.0.0.0 = tất cả interfaces)
   - `port`: Port của backend server
   - `uploadDir`: Thư mục lưu ảnh upload
   - `pdfDir`: Thư mục lưu file PDF

4. **extensionSettings**
   - `autoDetect`: Tự động phát hiện URL mục tiêu
   - `debugMode`: Chế độ debug (hiển thị log chi tiết)
   - `timeout`: Timeout cho các request (ms)

## Cách sử dụng

### 1. Thay đổi cấu hình

Chỉ cần sửa file `config.json` ở thư mục gốc, sau đó chạy script đồng bộ:

```bash
python update_config.py
```

Script sẽ tự động cập nhật:
- `chrome-extension/config.js` từ cấu hình mới
- Backend sẽ tự động đọc từ `config.json` khi khởi động

### 2. Build/Deploy

Khi build hoặc deploy sang môi trường khác:

1. Chỉnh sửa `config.json` với các giá trị phù hợp
2. Chạy `python update_config.py` để đồng bộ
3. Reload chrome extension (vào `chrome://extensions/`)
4. Khởi động lại backend server

### 3. Cập nhật thủ công

Nếu không muốn dùng script, có thể sửa trực tiếp:
- `config.json`: Cấu hình chính
- `chrome-extension/config.js`: Cấu hình extension
- `backend/config.py`: Có thể chỉnh sửa DEFAULT_CONFIG nếu cần

## Ví dụ thay đổi API endpoint

Giả sử cần thay đổi Queue System API từ `27.71.20.120:2020` sang `192.168.1.100:8080`:

1. Sửa `config.json`:
```json
{
  "apiEndpoints": {
    "backend": "http://localhost:5000",
    "queueSystem": "http://192.168.1.100:8080/api/ticket/create"
  },
  ...
}
```

2. Chạy đồng bộ:
```bash
python update_config.py
```

3. Reload extension và restart backend.

## Lưu ý

1. **Chrome Extension**: Không thể đọc trực tiếp file local, nên cần file `config.js` riêng
2. **Backend**: Tự động đọc `config.json` khi import `config.py`
3. **Script đồng bộ**: Tạo comment "DO NOT EDIT MANUALLY" trong `config.js` để tránh chỉnh sửa nhầm
4. **Backward Compatibility**: Hệ thống vẫn hoạt động nếu `config.json` không tồn tại (dùng giá trị mặc định)

## Build thành EXE

Khi build backend thành EXE, hệ thống vẫn hỗ trợ cấu hình động:

### Cách 1: Sử dụng build script
```bash
python build_exe.py
```

Script sẽ:
1. Tạo thư mục build với tất cả file cần thiết
2. Build EXE bằng PyInstaller
3. Tạo package deployment với EXE và config.json

### Cách 2: Build thủ công với PyInstaller
```bash
cd backend
pyinstaller --onefile --name kiosk_scan_backend ^
  --add-data "../config.json;." ^
  --hidden-import image_processor ^
  --hidden-import config ^
  --hidden-import ultralytics ^
  main.py
```

### Cấu hình khi chạy EXE

Khi chạy EXE, hệ thống tìm `config.json` theo thứ tự:
1. Cùng thư mục với EXE
2. Thư mục `config` trong cùng thư mục với EXE

**Ví dụ cấu trúc deployment:**
```
deployment/
├── kiosk_scan_backend.exe    # File EXE
├── config.json               # File cấu hình (cùng thư mục)
├── uploads/                  # Thư mục upload
├── pdfs/                     # Thư mục PDF
└── README.txt               # Hướng dẫn
```

### Cập nhật cấu hình sau khi build
1. Chỉ cần sửa file `config.json` trong cùng thư mục với EXE
2. Khởi động lại EXE
3. Backend sẽ tự động đọc cấu hình mới

## Xử lý lỗi

Nếu gặp lỗi:
1. Kiểm tra file `config.json` có đúng định dạng JSON không
2. Chạy `python update_config.py` để xem thông báo lỗi
3. Kiểm tra console log của backend khi khởi động
4. Kiểm tra console của chrome extension (F12 > Console)

### Lỗi thường gặp khi build EXE:
1. **Missing modules**: Thêm `--hidden-import` cho module bị thiếu
2. **Config not found**: Đảm bảo `config.json` được copy vào cùng thư mục EXE
3. **Large EXE size**: Các model AI có thể làm EXE lớn, xem xét download khi chạy

## Ưu điểm của hệ thống mới

1. **Tập trung**: Tất cả cấu hình trong 1 file
2. **Dễ bảo trì**: Chỉ sửa 1 chỗ, tự động đồng bộ
3. **An toàn**: Không hard-code trong source code
4. **Linh hoạt**: Dễ dàng thay đổi khi deploy sang môi trường khác
5. **Tương thích ngược**: Vẫn hoạt động nếu config.json không tồn tại
6. **EXE-friendly**: Hoạt động tốt cả ở chế độ script và EXE
7. **Deployment-ready**: Dễ dàng phân phối và cấu hình