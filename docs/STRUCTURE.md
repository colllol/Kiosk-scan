# Cấu trúc Project - Backend và Frontend

## Cấu trúc đề xuất (Rõ ràng và tách biệt)

```
webscan/
│
├── backend/                    # ================= BACKEND =================
│   ├── main.py                # FastAPI application
│   ├── requirements.txt       # Python dependencies
│   ├── README.md             # Hướng dẫn backend
│   │
│   ├── uploads/              # Thư mục lưu ảnh upload (tự tạo)
│   │   ├── *.jpg            # Các ảnh được upload từ frontend
│   │   └── *.png
│   │
│   └── pdfs/                 # Thư mục lưu listpdfs.txt (tự tạo)
│       ├── 20260310_listpdfs.txt   # File list theo ngày
│       └── 20260311_listpdfs.txt   # (CHỈ CHỨA FILE TEXT)
│
├── frontend/                  # ================= FRONTEND =================
│   ├── index.html            # Trang HTML chính
│   ├── styles.css            # CSS styles
│   │
│   ├── pdfs/                 # Thư mục lưu PDF files (tự tạo)
│   │   ├── 20260310_100811_document.pdf
│   │   ├── 20260310_100912_document.pdf
│   │   └── 20260311_080523_document.pdf  # (CHỈ CHỨA FILE PDF)
│   │
│   └── js/                   # JavaScript modules
│       ├── config.js         # Cấu hình ứng dụng
│       ├── app.js            # Main application
│       │
│       ├── models/
│       │   └── ImageModel.js # Model dữ liệu ảnh
│       │
│       └── components/
│           ├── Camera.js     # Xử lý camera
│           ├── Capture.js    # Chụp ảnh
│           ├── ImageList.js  # Quản lý danh sách ảnh
│           ├── Lightbox.js   # Xem ảnh phóng to
│           ├── Toast.js      # Thông báo
│           └── Api.js        # Gọi API backend
│
├── docs/                     # Tài liệu
│   ├── LISTPDFS.md          # Giải thích quản lý listpdfs
│   └── API.md               # API documentation
│
├── start-backend.bat        # Script chạy backend (Windows)
└── README.md                # README tổng thể
```

---

## PHÂN TÁCH RÕ RÀNG

### 📦 BACKEND (Python FastAPI)

**Địa chỉ:** `http://localhost:5000`

**Chức năng:**
- Xử lý file ảnh upload từ frontend
- Chuyển đổi ảnh thành PDF
- Quản lý file listpdfs.txt
- Lưu trữ PDF files

**Các thư mục:**
- `backend/uploads/` - Lưu ảnh tạm khi upload
- `backend/pdfs/` - Lưu file listpdfs.txt (text, không chứa PDF)

**Các file chính:**
```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
└── README.md          # Hướng dẫn backend
```

**API Endpoints:**
```
GET    /                    # Health check
POST   /api/upload         # Upload ảnh
POST   /api/export         # Export PDF
GET    /api/images         # Liệt kê ảnh
DELETE /api/clear          # Xóa tất cả ảnh
```

**Cách chạy:**
```bash
cd backend
pip install -r requirements.txt
python main.py
# hoặc
py -3 main.py
```

---

### 🎨 FRONTEND (HTML/CSS/JavaScript)

**Địa chỉ:** Serve từ bất kỳ web server (nginx, serve, hoặc mở trực tiếp file)

**Chức năng:**
- Truy cập camera
- Chụp ảnh
- Hiển thị danh sách ảnh
- Kéo thả sắp xếp
- Gọi API backend
- Download PDF

**Cấu trúc file:**
```
frontend/
├── index.html            # Cấu trúc HTML
├── styles.css            # Styles CSS
└── js/                   # JavaScript logic
    ├── config.js         # Cấu hình (API endpoints)
    ├── app.js            # Main entry point
    ├── models/           # Data models
    └── components/      # UI components
```

**Cách chạy:**
```bash
# Option 1: Sử dụng serve
cd frontend
npm install -g serve
serve .

# Option 2: Python http.server
cd frontend
python -m http.server 8080

# Option 3: Mở trực tiếp file
# Double-click index.html
```

---

## 🔄 GIAO TIẾP FRONTEND - BACKEND

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                         │
│  ┌──────────┐    ┌──────────┐    ┌─────────────┐   │
│  │ Camera   │ -> │ Capture  │ -> │  ImageList  │   │
│  └──────────┘    └──────────┘    └─────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  API Component (Api.js)                     │  │
│  │  - /api/upload (POST)                       │  │
│  │  - /api/export (POST)                       │  │
│  └────────────┬─────────────────────────────────┘  │
│               │                                   │
└───────────────┼───────────────────────────────────┘
                │
                │ HTTP/JSON
                │
┌───────────────▼───────────────────────────────────┐
│                   BACKEND                         │
│  ┌─────────────────────────────────────────────┐ │
│  │  FastAPI (main.py)                         │ │
│  │  - /api/upload: Receive images             │ │
│  │  - /api/export: Create & return PDF        │ │
│  └────────────┬────────────────────────────────┘ │
│               │                                   │
│  ┌────────────▼────────────────────────────────┐ │
│  │  File Storage                              │ │
│  │  backend/uploads/ (images)                  │ │
│  │  backend/pdfs/ (PDF files + listpdfs.txt)   │ │
│  └─────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

---

## 📝 FLOW DATA

### 1. Upload Ảnh
```
Frontend (Capture)
  ↓ [POST /api/upload]
  ↓ FormData with blob
Backend
  ↓ Save to backend/uploads/{uuid}.jpg
  ↓ Return { id: "uuid", preview: "..." }
Frontend (Store ID)
```

### 2. Tạo PDF
```
Frontend (Click "Tạo PDF")
  ↓ Loop all images
  ↓ [POST /api/upload] cho từng ảnh
Backend
  ↓ Save ảnh và trả về IDs
Frontend (Tạo mảng IDs)
  ↓ [POST /api/export] với { ids: [...] }
Backend
  ↓ Đọc ảnh từ backend/uploads/
  ↓ Tạo PDF: YYYYMMDD_HHMMSS_document.pdf
  ↓ Ghi vào backend/pdfs/YYYYMMDD_listpdfs.txt
  ↓ Save PDF to backend/pdfs/
  ↓ Return FileResponse (PDF blob)
Frontend (Download PDF)
  ↓ Browser save to Downloads/
```

---

## 🔧 CẤU HÌNH

### Frontend Config (`frontend/js/config.js`)
```javascript
const CONFIG = {
    API_UPLOAD: 'http://localhost:5000/api/upload',
    API_EXPORT: 'http://localhost:5000/api/export',
    // ...
};
```

### Backend Port (`backend/main.py`)
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

---

## 📋 CHECKLIST

### Backend
- [x] FastAPI server
- [x] /api/upload endpoint
- [x] /api/export endpoint
- [x] Thư mục backend/uploads/
- [x] Thư mục backend/pdfs/
- [x] File listpdfs.txt theo ngày
- [x] CORS configuration

### Frontend
- [x] index.html
- [x] styles.css
- [x] js/config.js
- [x] js/app.js
- [x] js/components/*.js
- [x] Camera access
- [x] Image capture
- [x] PDF download

---

## 🚀 CHẠY ỨNG DỤNG

### Bước 1: Chạy Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Server chạy tại http://localhost:5000
```

### Bước 2: Chạy Frontend
```bash
cd frontend
serve .
# Frontend chạy tại http://localhost:3000 (hoặc port khác)
```

### Bước 3: Truy cập
Mở browser → http://localhost:3000

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **Backend và Frontend tách biệt:**
   - Backend: Python FastAPI (port 5000)
   - Frontend: Static files (port khác)

2. **CORS:**
   - Backend đã cấu hình `allow_origins=["*"]`
   - Cho phép frontend gọi API từ bất kỳ domain

3. **Thư mục lưu trữ:**
   - `backend/uploads/` - Lưu ảnh upload (tạm thời)
   - `backend/pdfs/` - Lưu PDF files (dài hạn)

4. **File listpdfs.txt:**
   - Được tạo theo ngày trong backend/pdfs/
   - Format: `YYYYMMDD_listpdfs.txt`
   - Tự động cập nhật khi export PDF

5. **Tên file PDF:**
   - Format: `YYYYMMDD_HHMMSS_document.pdf`
   - Ngày được lấy khi tạo PDF
   - STT tăng dần trong file listpdfs.txt
