# 📋 Webcam Scan Document System - Project Structure

> **Hệ thống scan tài liệu bằng webcam** - Dành cho UBND và các cơ quan hành chính nhà nước

---

## 🏗️ Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WEBCAM SCAN DOCUMENT SYSTEM                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         FRONTEND (Port 3000)                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │
│  │  │ index.html  │  │ index1.html │  │   JavaScript Modules    │  │  │
│  │  │ Service     │  │ Scan        │  │  - ImageModel.js        │  │  │
│  │  │ Selection   │  │ Interface   │  │  - Camera.js            │  │  │
│  │  └─────────────┘  └─────────────┘  │  - Capture.js           │  │  │
│  │                                     │  - ImageList.js         │  │  │
│  │                                     │  - Lightbox.js          │  │  │
│  │                                     │  - Toast.js             │  │  │
│  │                                     │  - Api.js               │  │  │
│  │                                     └─────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    │ HTTP REST API                       │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         BACKEND (Port 5000)                       │  │
│  │  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │  │
│  │  │  main.py    │  │image_processor. │  │  print_ticket.py    │  │  │
│  │  │  FastAPI    │  │      py         │  │  Thermal Printer    │  │  │
│  │  │  Endpoints  │  │  CLAHE, OpenCV  │  │  Queue Ticket       │  │  │
│  │  └─────────────┘  └─────────────────┘  └─────────────────────┘  │  │
│  │         │                  │                      │              │  │
│  │         ▼                  ▼                      ▼              │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │              External Integrations                        │   │  │
│  │  │  QueueSystem API  │  Thermal Printer  │  PDF Storage     │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục chi tiết

```
d:\frontend-webscan\
│
├── 📄 PROJECT_STRUCTURE.md          # File này - Mô tả kiến trúc project
├── 📄 .gitignore                    # Git ignore rules
├── 📄 service.txt                   # Danh sách các phòng ban dịch vụ
├── 📄 start-backend.bat             # Script khởi động Backend
├── 📄 start-frontend.bat            # Script khởi động Frontend
├── 📄 upload ảnh.text               # Hướng dẫn upload ảnh
├── 📦 frontend.rar                  # Backup frontend (compressed)
│
├── 📂 backend/                      # Python FastAPI Server
│   ├── 📄 main.py                   # ⭐ API endpoints chính
│   ├── 📄 image_processor.py        # ⭐ Xử lý ảnh (CLAHE, sharpening)
│   ├── 📄 print_ticket.py           # ⭐ In vé số thứ tự
│   ├── 📄 requirements.txt          # Python dependencies
│   ├── 📄 build.bat                 # Build script (PyInstaller)
│   ├── 📄 README.md                 # Backend documentation
│   ├── 📂 __pycache__/              # Python bytecode cache
│   ├── 📂 build/                    # Build intermediate files
│   ├── 📂 dist/                     # Compiled EXE output
│   │   └── WebcamScan.exe           # Production executable
│   ├── 📂 uploads/                  # 📷 Ảnh tạm thời (runtime)
│   └── 📂 pdfs/                     # 📄 File tracking listpdfs.txt
│
├── 📂 frontend/                     # Static Web Application
│   ├── 📄 index.html                # 🏠 Trang chọn dịch vụ
│   ├── 📄 index1.html               # 📷 Giao diện scan chính
│   ├── 📄 styles.css                # Custom styles
│   ├── 📂 js/                       # JavaScript Modules
│   │   ├── 📄 config.js             # Cấu hình API endpoints
│   │   ├── 📄 app.js                # Main application entry
│   │   └── 📂 modules/              # ES6 Modules
│   │       ├── 📄 ImageModel.js     # Data model cho ảnh
│   │       ├── 📄 Camera.js         # Webcam access & control
│   │       ├── 📄 Capture.js        # Chụp ảnh & rotation
│   │       ├── 📄 ImageList.js      # Display & drag-sort ảnh
│   │       ├── 📄 Lightbox.js       # Full-screen preview
│   │       ├── 📄 Toast.js          # Notification system
│   │       └── 📄 Api.js            # Backend API calls
│   ├── 📂 css/                      # Stylesheets
│   ├── 📂 assets/                   # Images, icons, fonts
│   └── 📂 pdfs/                     # 📥 PDFs đã tải về (runtime)
│
├── 📂 Kiosk-scan/                   # Reserved (empty Git repo)
│
└── 📂 docs/                         # Documentation
    ├── 📄 STRUCTURE.md              # Project structure overview
    ├── 📄 DIRECTORY_STRUCTURE.md    # Folder organization
    ├── 📄 LISTPDFS.md               # PDF tracking format
    └── 📄 IMAGE_PROCESSING.md       # Image processing pipeline
```

---

## 🎯 Chức năng chi tiết từng thành phần

### 1️⃣ FRONTEND (`frontend/`)

#### 📄 `index.html` - Trang lựa chọn dịch vụ
**Chức năng:**
- Hiển thị 6 phòng ban dịch vụ UBND:
  1. 🏭 Kinh tế - Xã hội
  2. ⚖️ Tư pháp - Hộ tịch
  3. 🏗️ Địa chính - Xây dựng
  4. 📰 Văn hóa - Thông tin
  5. 💰 Kế toán - Tài chính
  6. 🏥 Giáo dục - Y tế
- Video hướng dẫn sử dụng
- Link nhanh đến Cổng dịch vụ công quốc gia

**Luồng xử lý:**
```
User chọn phòng ban → Chuyển đến index1.html → Truyền serviceId
```

---

#### 📄 `index1.html` - Giao diện scan tài liệu
**Chức năng:**
- 📷 **Webcam Preview**: Hiển thị camera realtime (xoay -90°)
- 📸 **Capture**: Chụp ảnh độ phân giải cao (4608x3456)
- 🔄 **Image Processing**: Tự động tăng cường chất lượng (CLAHE, sharpen, +30% brightness)
- 📋 **Image List**: Hiển thị thumbnail với drag-and-drop reordering
- 🔍 **Lightbox**: Preview toàn màn hình với pinch-zoom
- 📤 **Export**: Tạo PDF từ nhiều ảnh
- 🎫 **Ticket**: Lấy số thứ tự và in vé

**Components:**
| Component | Chức năng |
|-----------|-----------|
| `Camera.js` | Khởi tạo webcam, xử lý rotation, auto-focus |
| `Capture.js` | Chụp ảnh, áp dụng image enhancement, lưu vào model |
| `ImageList.js` | Render thumbnails, drag-sort (SortableJS), delete/reorder |
| `Lightbox.js` | Full-screen preview, zoom, rotate, pan |
| `Toast.js` | Hiển thị notifications (success/error/warning) |
| `Api.js` | REST API calls (upload, export, ticket) |

---

#### 📂 JavaScript Modules

##### `models/ImageModel.js`
```javascript
// Data model quản lý danh sách ảnh
class ImageModel {
  - images: Array          // Danh sách ảnh đã chụp
  - serviceId: String      // ID phòng ban hiện tại
  + addImage()            // Thêm ảnh mới
  + removeImage()         // Xóa ảnh
  + reorderImages()       // Sắp xếp lại thứ tự
  + getImages()           // Lấy danh sách ảnh
}
```

##### `components/Camera.js`
```javascript
// Webcam access và control
class Camera {
  - videoElement: HTMLVideoElement
  - stream: MediaStream
  + init()              // Khởi tạo webcam
  + startStream()       // Bắt đầu stream
  + stopStream()        // Dừng stream
  + rotate(-90deg)      // Xoay video preview
}
```

##### `components/Capture.js`
```javascript
// Xử lý chụp ảnh
class Capture {
  - canvas: HTMLCanvasElement
  - context: CanvasRenderingContext2D
  + captureFrame()      // Chụp frame từ video
  + applyEnhancement()  // Tăng cường chất lượng ảnh
  + rotateImage()       // Xoay ảnh sau chụp
  + saveToModel()       // Lưu vào ImageModel
}
```

##### `components/ImageList.js`
```javascript
// Display và quản lý danh sách ảnh
class ImageList {
  - container: HTMLElement
  - sortable: SortableJS
  + render()            // Render thumbnails
  + enableDragSort()    // Kích hoạt drag-and-drop
  + deleteImage()       // Xóa ảnh khỏi list
  + updateOrder()       // Cập nhật thứ tự mới
}
```

##### `components/Lightbox.js`
```javascript
// Full-screen image preview
class Lightbox {
  - overlay: HTMLElement
  - imageElement: HTMLImageElement
  + open(imageSrc)      // Mở lightbox
  + close()             // Đóng lightbox
  + zoom(in/out)        // Phóng to/thu nhỏ
  + pan(x, y)           // Di chuyển ảnh
}
```

##### `components/Toast.js`
```javascript
// Notification system
class Toast {
  + showSuccess(msg)    // Hiển thị thông báo thành công
  + showError(msg)      // Hiển thị lỗi
  + showWarning(msg)    // Hiển thị cảnh báo
  + showInfo(msg)       // Hiển thị thông tin
}
```

##### `components/Api.js`
```javascript
// Backend API communication
class Api {
  - baseURL: 'http://localhost:5000'
  + uploadImage(file)        // POST /api/upload
  + exportPdf(images, svc)   // POST /api/export
  + getTicket(service)       // POST /api/ticket
  + listImages()             // GET /api/images
  + clearAll()               // DELETE /api/clear
}
```

---

### 2️⃣ BACKEND (`backend/`)

#### 📄 `main.py` - FastAPI Application
**Chức năng:** API endpoints chính

| Endpoint | Method | Chức năng |
|----------|--------|-----------|
| `/api/upload` | POST | Upload ảnh từ frontend |
| `/api/export` | POST | Tạo PDF từ danh sách ảnh |
| `/api/ticket` | POST | Tạo số thứ tự và in vé |
| `/api/images` | GET | Liệt kê ảnh đã upload |
| `/api/clear` | DELETE | Xóa tất cả ảnh tạm |

**Luồng xử lý `/api/export`:**
```
1. Nhận danh sách image IDs + service info
2. Đọc ảnh từ backend/uploads/
3. Xử lý ảnh qua ImageProcessor (CLAHE, sharpen, brightness)
4. Tạo PDF: YYYYMMDD_HHMMSS_document.pdf
5. Ghi log vào backend/pdfs/YYYYMMDD_listpdfs.txt
6. Trigger ticket creation (background task)
7. Return PDF URL cho frontend download
```

**Luồng xử lý `/api/ticket`:**
```
1. Nhận service info
2. Đọc số thứ tự cuối cùng từ listpdfs.txt
3. Tăng số thứ tự (+1)
4. Gọi QueueSystem API (http://192.168.100.238/QueueSystemAdmin/api/ticket/create)
5. In vé qua thermal printer (background task)
6. Return ticket number
```

---

#### 📄 `image_processor.py` - Xử lý ảnh
**Chức năng:** Tăng cường chất lượng ảnh scan

**Pipeline xử lý:**
```
Input Image
    │
    ├─► Convert to LAB color space
    │
    ├─► Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    │   - Kernel size: 8x8
    │   - Clip limit: 2.0
    │
    ├─► Sharpening filter
    │   - Kernel: [[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]
    │
    ├─► Increase brightness (+30%)
    │
    └─► Convert back to RGB
        │
        ▼
Output Enhanced Image
```

**Code structure:**
```python
class ImageProcessor:
    + enhance_document(image) -> PIL.Image
        - apply_clahe()
        - apply_sharpening()
        - adjust_brightness(1.3)
    
    + lazy_load_opencv()
        # Chỉ load OpenCV khi cần thiết
```

---

#### 📄 `print_ticket.py` - In vé số thứ tự
**Chức năng:** In vé qua máy in nhiệt EP802

**Ticket format:**
```
┌────────────────────────┐
│   🏛️ UBND QUẬN/PHƯỜNG   │
│   📋 PHIẾU XẾP HÀNG     │
│                        │
│   Số thứ tự: 0042      │
│   Phòng ban:           │
│   Tư pháp - Hộ tịch    │
│                        │
│   Ngày: 27/03/2026     │
│   Giờ: 14:30:25        │
│                        │
│   Xin cảm ơn!          │
└────────────────────────┘
```

**Integration:**
- Sử dụng thư viện `python-escpos`
- Kết nối qua Windows printer driver
- Hỗ trợ custom logo và QR code

---

### 3️⃂ Data Flow - Luồng dữ liệu hoàn chỉnh

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER WORKFLOW                                 │
│                                                                      │
│  1. Chọn phòng ban (index.html)                                     │
│         │                                                            │
│         ▼                                                            │
│  2. Mở giao diện scan (index1.html)                                 │
│         │                                                            │
│         ▼                                                            │
│  3. Chụp ảnh tài liệu qua webcam                                    │
│         │                                                            │
│         ▼                                                            │
│  4. Review, reorder, delete ảnh (optional)                          │
│         │                                                            │
│         ▼                                                            │
│  5. Click "Lấy số thứ tự"                                           │
│         │                                                            │
│         ▼                                                            │
│  6. Download PDF + Nhận vé in                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW                                     │
│                                                                      │
│  Frontend                    Backend                  External      │
│                                                                      │
│  📸 Capture ảnh                                                      │
│       │                                                              │
│       ├─► POST /api/upload ──► Lưu vào uploads/                     │
│       │                                                              │
│  📤 Export PDF                                                       │
│       ├─► POST /api/export ──► Đọc ảnh từ uploads/                  │
│       │                      ├─► ImageProcessor.enhance()           │
│       │                      ├─► Tạo PDF (ReportLab)                │
│       │                      ├─► Ghi log listpdfs.txt               │
│       │                      │                                      │
│       │                      ├─► Background Task:                   │
│       │                      │    ├─► QueueSystem API               │
│       │                      │    └─► Thermal Printer               │
│       │                      │                                      │
│       ◄─── PDF URL ──────────┘                                      │
│       │                                                              │
│  📥 Download PDF                                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Database & File Tracking

### 📄 File `listpdfs.txt` format

**Location:** `backend/pdfs/YYYYMMDD_listpdfs.txt`

**Format:**
```
STT   | Ten File                              | ServiceId | ServiceName
----------------------------------------------------------------------
0001  | 20260310_100811_document.pdf          | 1         | Kinh tế - Xã hội
0002  | 20260310_100912_document.pdf          | 2         | Tư pháp - Hộ tịch
0003  | 20260310_101523_document.pdf          | 3         | Địa chính - Xây dựng
```

**Purpose:**
- Theo dõi số thứ tự (STT) tự động tăng
- Lưu tên file PDF đã tạo
- Ghi nhận phòng ban dịch vụ
- Reset hàng ngày (tạo file mới mỗi ngày)

---

## 🔧 Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Language runtime |
| **FastAPI** | Latest | Web framework |
| **Uvicorn** | Latest | ASGI server |
| **Pillow** | Latest | Image processing |
| **OpenCV** | Latest | Advanced image enhancement |
| **ReportLab** | Latest | PDF generation |
| **NumPy** | Latest | Array manipulation |
| **SciPy** | Latest | Image filters |
| **python-escpos** | Latest | Thermal printer control |
| **Requests** | Latest | HTTP client |
| **PyInstaller** | Latest | EXE bundling |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Vanilla JavaScript** | No framework - modular ES6 modules |
| **Tailwind CSS (CDN)** | Utility-first styling |
| **SortableJS** | Drag-and-drop reordering |
| **Font Awesome** | Icons |
| **OpenCV.js** | Optional client-side processing |

---

## 🚀 Deployment

### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Server running at http://localhost:5000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
python -m http.server 3000
# Server running at http://localhost:3000
```

### Production (Standalone EXE)

```bash
cd backend
build.bat
# Output: dist/WebcamScan.exe
# Run: dist\WebcamScan.exe
```

**PyInstaller config (build.spec):**
- `--onedir` mode for faster startup
- Bundles all dependencies
- Includes image assets
- Windows-only executable

---

## 🔗 External Integrations

| System | URL | Purpose |
|--------|-----|---------|
| **QueueSystem API** | `http://192.168.100.238/QueueSystemAdmin/api/ticket/create` | Tạo số thứ tự |
| **Dich Vu Cong** | `https://dichvucong.gov.vn/` | Link đến cổng dịch vụ công |
| **Thermal Printer** | EP802 (Windows driver) | In vé số thứ tự |

---

## 📝 Service Departments (6 phòng ban)

| ID | Name | Description |
|----|------|-------------|
| 1 | Kinh tế - Xã hội | Quản lý kinh tế địa phương, an sinh xã hội |
| 2 | Tư pháp - Hộ tịch | Đăng ký khai sinh, kết hôn, tư pháp |
| 3 | Địa chính - Xây dựng | Đất đai, giấy phép xây dựng |
| 4 | Văn hóa - Thông tin | Văn hóa, thể thao, truyền thông |
| 5 | Kế toán - Tài chính | Ngân sách, kế toán, tài chính |
| 6 | Giáo dục - Y tế | Trường học, trạm y tế |

---

## 🎨 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Vanilla JS** | Minimal dependencies, full control, no build step |
| **Lazy Loading OpenCV** | Faster startup (~2s vs ~10s) |
| **PNG Lossless** | Preserve quality before backend processing |
| **Parallel Uploads** | Up to 10 concurrent requests for speed |
| **Date-based Tracking** | Separate listpdfs.txt per day for organization |
| **Background Tasks** | API calls & printing don't block response |
| **EXE Distribution** | Easy deployment for non-technical users |
| **Tailwind CDN** | Rapid prototyping without build tools |

---

## 📖 Related Documentation

- `docs/STRUCTURE.md` - High-level project overview
- `docs/DIRECTORY_STRUCTURE.md` - Detailed folder organization
- `docs/LISTPDFS.md` - PDF tracking file specification
- `docs/IMAGE_PROCESSING.md` - Image enhancement algorithms
- `backend/README.md` - Backend API documentation

---

## 👥 Development Team Notes

**Project Type:** Government Document Scanning Kiosk  
**Target Users:** UBND staff, citizens  
**Deployment Environment:** Windows 10/11, touchscreen kiosk  
**Primary Use Case:** Scan documents, generate PDFs, print queue tickets  

---

*Generated: 27/03/2026*  
*Version: 1.0*
