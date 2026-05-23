# AutoCut Document Scanner

Web app quét tài liệu bằng camera, YOLO ONNX và OpenCV.js.

## Chạy web

```powershell
npm install
npm start
```

Mở URL Vite in ra, thường là `http://127.0.0.1:5173`.

Nếu chưa có model `models/document-yolo.onnx`, app vẫn chạy bằng contour fallback. Để dùng YOLO, upload file `.onnx` trên giao diện hoặc đặt file tại:

```text
models/document-yolo.onnx
```

## Huấn luyện YOLO

Chuẩn bị dataset theo cấu trúc YOLO:

```text
datasets/document/
  images/train/*.jpg
  images/val/*.jpg
  labels/train/*.txt
  labels/val/*.txt
```

Mỗi label có class `0` cho vùng tài liệu:

```text
0 x_center y_center width height
```

Cài thư viện Python:

```powershell
pip install ultralytics onnx onnxsim
```

Huấn luyện và export:

```powershell
npm run train
npm run export
```

Sau export, web sẽ tự nạp `models/document-yolo.onnx`.

## Luồng xử lý

1. Camera lấy frame trực tiếp trong trình duyệt.
2. YOLO phát hiện bounding box tài liệu.
3. Khi box ổn định đủ lâu, app tự chụp.
4. OpenCV tìm 4 góc trong vùng YOLO, perspective transform để crop và deskew.
5. Nút `Tạo PDF` đưa các ảnh đã crop vào file PDF A4.

Việc xoay hiện tại là deskew và chuẩn hóa trang dọc. Nếu cần nhận đúng chiều chữ 0/90/180/270 độ, nên bổ sung OCR orientation sau bước crop.
