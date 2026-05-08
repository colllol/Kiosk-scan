# Cấu trúc Thư mục Tối ưu - Backend và Frontend Tách Biệt

## 📁 CẤU TRÚC TỐI ƯU

```
d:/frontend-webscan/
│
├── backend/                      # ══════════════════════════
│   ├── main.py                  # FastAPI application
│   ├── requirements.txt         # Python dependencies
│   ├── README.md                # Hướng dẫn backend
│   │
│   ├── uploads/                 # Lưu ảnh upload
│   │   ├── *.jpg
│   │   └── *.png
│   │
│   └── pdfs/                    # Lưu listpdfs.txt (TEXT ONLY)
│       ├── 20260310_listpdfs.txt
│       └── 20260311_listpdfs.txt
│
├── frontend/                     # ══════════════════════════
│   ├── index.html               # Trang HTML chính
│   ├── styles.css               # CSS styles
│   │
│   ├── pdfs/                    # Lưu file PDF (PDF ONLY)
│   │   ├── 20260310_100811_document.pdf
│   │   ├── 20260310_100912_document.pdf
│   │   └── 20260311_080523_document.pdf
│   │
│   └── js/                      # JavaScript modules
│       ├── config.js           # Cấu hình API endpoints
│       ├── app.js              # Main application entry
│       │
│       ├── models/
│       │   └── ImageModel.js   # Model dữ liệu ảnh
│       │
│       └── components/
│           ├── Camera.js       # Xử lý camera
│           ├── Capture.js      # Chụp ảnh
│           ├── ImageList.js    # Quản lý danh sách ảnh
│           ├── Lightbox.js     # Xem ảnh phóng to
│           ├── Toast.js        # Thông báo
│           └── Api.js          # Gọi API backend
│
├── docs/                        # Tài liệu project
│   ├── STRUCTURE.md            # Tài liệu cấu trúc
│   ├── LISTPDFS.md             # Giải thích listpdfs.txt
│   └── README.md               # README tổng thể
│
└── start-backend.bat            # Script chạy backend (Windows)
```

---

## 🔍 PHÂN TÁCH RÕ RÀNG

### 📦 BACKEND (Python FastAPI - Port 5000)

**Thư mục:** `backend/`

**Chức năng:**
- Nhận và lưu file ảnh upload
- Chuyển đổi ảnh thành PDF
- Quản lý file listpdfs.txt (theo ngày)
- Trả về file PDF cho frontend

**Cấu trúc thư mục:**
```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── README.md            # Hướng dẫn backend
│
├── uploads/            # Lưu ảnh upload (tạm thời)
│   └── {uuid}.jpg      # Các ảnh được upload
│
└── pdfs/               # Lưu listpdfs.txt (TEXT ONLY)
    ├── 20260310_listpdfs.txt
    └── 20260311_listpdfs.txt
```

**Lưu ý quan trọng:**
- `backend/pdfs/` → **CHỈ CHỨA FILE TEXT** (listpdfs.txt)
- `backend/pdfs/` → **KHÔNG CHỨA FILE PDF**

---

### 🎨 FRONTEND (HTML/CSS/JavaScript - Port khác)

**Thư mục:** `frontend/`

**Chức năng:**
- Truy cập webcam
- Chụp và hiển thị ảnh
- Gọi API backend
- Download file PDF

**Cấu trúc thư mục:**
```
frontend/
├── index.html         # Trang HTML chính
├── styles.css         # CSS styles
│
├── pdfs/              # Lưu file PDF (PDF ONLY)
│   ├── 20260310_100811_document.pdf
│   ├── 20260310_100912_document.pdf
│   └── 20260311_080523_document.pdf
│
└── js/                # JavaScript modules
    ├── config.js     # Cấu hình API
    ├── app.js        # Main app
    ├── models/       # Data models
    └── components/   # UI components
```

**Lưu ý quan trọng:**
- `frontend/pdfs/` → **CHỈ CHỨA FILE PDF**
- `frontend/pdfs/` → **KHÔNG CHỨA FILE TEXT**

---

## 🔄 FLOW DỮ LIỆU

### Export PDF

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND                           │
│  Chụp ảnh → Upload → Nhấn "Tạo PDF"                  │
└───────────────┬──────────────────────────────────────┘
                │
                │ [POST /api/export] với IDs
                │
                ▼
┌─────────────────────────────────────────────────────┐
│                   BACKEND                           │
│                                                     │
│  1. Đọc ảnh từ backend/uploads/                     │
│  2. Tạo PDF: YYYYMMDD_HHMMSS_document.pdf          │
│  3. Lưu PDF → frontend/pdfs/                         │
│  4. Ghi vào backend/pdfs/YYYYMMDD_listpdfs.txt      │
│  5. Trả file PDF về frontend                       │
│  6. Frontend download PDF                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 File ListPDFs.txt

### Vị trí
- **backend/pdfs/YYYYMMDD_listpdfs.txt**

### Cấu trúc
```
STT   | Ten File
--------------------------------------------------
1     | 20260310_100811_document.pdf
2     | 20260310_100912_document.pdf
3     | 20260310_103015_document.pdf
```

### Lưu ý
- 1 file listpdfs.txt cho mỗi ngày
- Chứa trong `backend/pdfs/` (không phải frontend/pdfs)
- Chỉ chứa text (STT và tên file)
- STT tự động tăng khi có PDF mới

---

## 🚀 CÁCH CHẠY

### Bước 1: Chạy Backend
```bash
cd backend
py -3 main.py
# Server: http://localhost:5000
```

### Bước 2: Chạy Frontend
```bash
cd frontend
serve .
# Frontend: http://localhost:3000
```

### Bước 3: Truy cập
Mở browser → http://localhost:3000

---

## ✅ KIỂM TRA CẤU TRÚC

### Backend
- [x] `backend/main.py`
- [x] `backend/requirements.txt`
- [x] `backend/uploads/` (ảnh)
- [x] `backend/pdfs/` (chỉ text: listpdfs.txt)

### Frontend
- [x] `frontend/index.html`
- [x] `frontend/styles.css`
- [x] `frontend/js/config.js`
- [x] `frontend/js/app.js`
- [x] `frontend/pdfs/` (chỉ PDF files)

---

## ⚠️ QUAN TRỌNG

### Frontend và Backend KHÔNG ở cùng thư mục
- Khi deploy, frontend và backend có thể ở server khác nhau
- Frontend truy cập backend qua HTTP API
- Cấu hình CORS trong backend cho phép cross-origin requests

### Thư mục pdfs riêng biệt
1. **frontend/pdfs/** → Chỉ chứa file PDF (download về máy người dùng)
2. **backend/pdfs/** → Chỉ chứa file listpdfs.txt (quản lý tracking)

### File listpdfs.txt
- Được backend tự động tạo
- Chứa trong backend/pdfs/
- Mỗi ngày một file
- Không cần frontend can thiệp
