# Kiến trúc Frontend - Webcam Scan Document Kiosk

> **Mô tả toàn bộ cấu trúc, luồng hoạt động và tương tác giao diện của frontend**
> Hệ thống scan tài liệu bằng webcam dành cho UBND và cơ quan hành chính nhà nước

---

## Mục lục

1. [Cấu trúc thư mục](#1-cấu-trúc-thư-mục)
2. [Luồng điều hướng (Flow)](#2-luồng-điều-hướng-flow)
3. [Mô tả từng trang & component](#3-mô-tả-từng-trang--component)
4. [Hệ thống Overlay & Popup](#4-hệ-thống-overlay--popup)
5. [Luồng dịch vụ hành chính công (External)](#5-luồng-dịch-vụ-hành-chính-công-external)
6. [Luồng dữ liệu chi tiết](#6-luồng-dữ-liệu-chi-tiết)
7. [Sơ đồ lớp & module](#7-sơ-đồ-lớp--module)
8. [API Endpoints](#8-api-endpoints)
9. [Ghi chú kỹ thuật](#9-ghi-chú-kỹ-thuật)

---

## 1. Cấu trúc thư mục

```
frontend/
│
├── index.html              # 🏠 Trang chủ - Chọn dịch vụ
├── index2.html             # 💳 Trang hướng dẫn cắm thẻ căn cước
├── index3.html             # 📷 Giao diện scan tài liệu chính (SPA)
├── styles.css              # 🎨 Custom styles (toast, lightbox, image items...)
│
├── js/
│   ├── config.js           # ⚙️ Cấu hình & State toàn cục
│   ├── app.js              # 🚀 App entry point - Khởi tạo toàn bộ components
│   │
│   ├── models/
│   │   └── ImageModel.js   # 📦 Data model: ImageModel + ImageStore
│   │
│   ├── components/
│   │   ├── Camera.js       # 📸 Webcam initialization & control
│   │   ├── Capture.js      # 📥 Chụp ảnh từ video stream
│   │   ├── ImageList.js    # 🖼️ Render ảnh thumbnail + drag-sort
│   │   ├── Lightbox.js     # 🔍 Full-screen preview + zoom
│   │   ├── Toast.js        # 🔔 Notification system
│   │   ├── Api.js          # 🌐 REST API calls (upload, export, certify)
│   │   └── imageProcessing.js  # 🧠 Xử lý ảnh client-side (Canny edge, auto-crop)
│   │
│   └── video/
│       └── guide.mp4       # 🎬 Video hướng dẫn sử dụng
```

---

## 2. Luồng điều hướng (Flow)

```
┌──────────────────────────────────────────────────────────────────┐
│                      LUỒNG ĐIỀU HƯỚNG TỔNG THỂ                    │
└──────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │  index.html  │  🏠 Trang chọn dịch vụ
  │              │
  │  ┌────────┐  │  Nhấn vào 1 trong 6 dịch vụ:
  │  │ Card 1 │──│──── POST /api/ticket → alert(số thứ tự)
  │  │  ...   │  │
  │  │ Card 6 │  │
  │  ├────────┤  │
  │  │ "Dịch  │  │
  │  │  vụ    │──│───► index2.html  (Cắm thẻ căn cước)
  │  │ chứng  │  │
  │  │ thực"  │  │
  │  ├────────┤  │
  │  │ "Dịch  │  │
  │  │  vụ    │──│───► https://dichvucong.gov.vn/  (external)
  │  │ công"  │  │
  │  └────────┘  │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ index2.html  │  💳 Hướng dẫn cắm thẻ căn cước
  │              │
  │   3 bước:    │
  │  1. Cắm thẻ  │
  │  2. Đợi đọc  │
  │  3. Nhấn nút │
  │              │
  │  [Tiếp tục]──│───► index3.html
  └──────────────┘
         │
         ▼
  ┌──────────────────────────────────────────┐
  │  index3.html   📷 GIAO DIỆN SCAN CHÍNH    │
  │                                            │
  │ ┌───────────────────────┬──────────────┐  │
  │ │                       │  🖼️ DANH SÁCH │  │
  │ │  📹 CAMERA VIEWPORT   │    ẢNH ĐÃ CHỤP │  │
  │ │   (80% × 80%)         │   (20% × 80%) │  │
  │ │                       │               │  │
  │ │   [Video preview]     │  [thumb 1]    │  │
  │ │                       │  [thumb 2]    │  │
  │ │                       │  [thumb 3]    │  │
  │ │                       │     ...       │  │
  │ └───────────────────────┴──────────────┘  │
  │                                            │
  │ ┌──────────────────────────────────────┐  │
  │ │  🔘 CONTROL BAR (100% × 20%)        │  │
  │ │  [📷 Chụp ảnh] [🗑️ Xóa tất cả]      │  │
  │ │  [📄 Lấy số thứ tự] [🏷️ Chứng thực]  │  │
  │ │  [▼ Chọn dịch vụ (dropdown)]        │  │
  │ └──────────────────────────────────────┘  │
  └──────────────────────────────────────────┘
         │
         ├── [Chụp ảnh]    ───► Camera capture → Thêm vào danh sách
         │
         ├── [Lấy số thứ tự] ──► Upload ảnh → Backend tạo PDF → In vé
         │                        → Hiển thị PDF Modal với 2 nút:
         │                          [Chứng thực tài liệu] → dichvucong.thainguyen.gov.vn
         │                          [Chứng thực chữ ký]   → dichvucong.thainguyen.gov.vn
         │                        → Redirect về index.html
         │
         ├── [Chứng thực] ───► Fetch fullName từ localhost:5431
         │                        → Upload ảnh với serviceId=99
         │                        → Backend tạo PDF
         │                        → Hiển thị PDF Modal
         │
         └── [Xóa tất cả] ───► Clear danh sách ảnh
```

---

## 3. Mô tả từng trang & component

### 3.1 `index.html` — Trang chọn dịch vụ

**Mục đích:** Màn hình chính của kiosk, cho phép người dùng chọn dịch vụ hành chính.

**Bố cục:**
- **Video section (30% chiều cao):** Phát video `video/guide.mp4` hướng dẫn sử dụng
- **Features section (70% chiều cao):** Grid 8 thẻ chức năng (6 dịch vụ + 2 liên kết)

**8 thẻ chức năng:**

| Thẻ | Dịch vụ | Hành động |
|-----|---------|-----------|
| 1 | Kinh tế - Xã hội | POST `/api/ticket` → in vé |
| 2 | Tư pháp - Hộ tịch | POST `/api/ticket` → in vé |
| 3 | Địa chính - Xây dựng | POST `/api/ticket` → in vé |
| 4 | Văn hóa - Thông tin | POST `/api/ticket` → in vé |
| 5 | Kế toán - Tài chính | POST `/api/ticket` → in vé |
| 6 | Giáo dục - Y tế | POST `/api/ticket` → in vé |
| 7 | **Dịch vụ chứng thực** | Điều hướng → `index2.html` |
| 8 | **Dịch vụ công** (external) | Mở `https://dichvucong.gov.vn/` |

**Luồng API Ticket:**
```
Click thẻ dịch vụ (1-6)
  → fetch POST http://localhost:5000/api/ticket
    body: { serviceId, serviceName }
  → Response: { ticketNumber }
  → alert() hiển thị số thứ tự + lệnh in
```

---

### 3.2 `index2.html` — Hướng dẫn cắm thẻ căn cước

**Mục đích:** Trung gian hướng dẫn người dùng cắm thẻ căn cước công dân (CCCD) trước khi vào giao diện scan.

**Bố cục:**
- Icon thẻ căn cước (SVG animated pulse)
- Tiêu đề: "📋 Yêu cầu cắm thẻ căn cước"
- 3 bước hướng dẫn:
  1. Cắm thẻ căn cước vào đầu đọc thẻ
  2. Đợi hệ thống đọc thông tin từ thẻ
  3. Nhấn nút "Tiếp tục"
- Nút **🚀 Tiếp tục** → `window.location.href = "index3.html"`
- Hỗ trợ phím **Enter** để tiếp tục

---

### 3.3 `index3.html` — Giao diện scan tài liệu (SPA)

**Mục đích:** Trang web scan chính, xử lý toàn bộ quy trình chụp ảnh, upload, tạo PDF.

**Layout CSS Grid:**
```
grid-template-columns: 80% 20%
grid-template-rows: 80% 20%
```

#### Card 1 — Camera Viewport (80% × 80%)

| Element | Mô tả |
|---------|-------|
| `<video id="video">` | Webcam stream, xoay -90°, scale 0.5 |
| `<div id="flash">` | Hiệu ứng flash khi chụp |
| `<div id="camera-error">` | Message khi không có camera |

**Camera.js — Xử lý camera:**
```
Camera.init()
  → getUserMedia({ video: { facingMode: 'environment', width: 3840, height: 2160 } })
  → video.srcObject = stream
  → onloadedmetadata → tính aspect ratio xoay -90°, scale 0.5
  → video.play()
  → checkCameraCapabilities() (focus mode, focus distance)
```

#### Card 2 — Image List (20% × 80%)

| Element | Mô tả |
|---------|-------|
| `<div id="image-list">` | Container ảnh thumbnail |
| `<span id="image-count">` | Đếm số ảnh |
| `<div id="empty-message">` | Hiển thị khi chưa có ảnh |

**ImageList.js — Quản lý danh sách ảnh:**
```
ImageList.init()
  → setupSortable() (SortableJS cho drag-and-drop)

render(imageModel, index)
  → Tạo div.image-item với:
    - <img> thumbnail
    - <button.delete-btn> (Xóa từng ảnh)
    - <span.image-number> (Số thứ tự)
  → Click → mở Lightbox
  → Drag → reorder → cập nhật ImageStore

delete(id) → Xóa ảnh khỏi store + DOM
clear() → Xóa tất cả ảnh
```

#### Card 3 — Control Bar (100% × 20%)

| Button | ID | Chức năng |
|--------|----|-----------|
| 📷 **Chụp ảnh** | `capture-btn` | Chụp frame từ camera |
| 🗑️ **Xóa tất cả** | `reset-btn` | Xóa toàn bộ ảnh đã chụp |
| 📄 **Lấy số thứ tự** | `pdf-btn` | Upload ảnh + tạo PDF + in vé |
| 🏷️ **Chứng thực tài liệu** | `certify-btn` | Fetch identity từ localhost:5431 → upload → tạo PDF |
| ▼ **Chọn dịch vụ** | `service-select` | Dropdown 6 dịch vụ (ẩn mặc định) |

---

### 3.4 Các Component JavaScript

#### `config.js` — Cấu hình & State toàn cục

```javascript
CONFIG = {
  MAX_WIDTH: 3840,
  MAX_HEIGHT: 2160,
  JPEG_QUALITY: 0.95,
  API_UPLOAD: 'http://localhost:5000/api/upload',
  API_EXPORT: 'http://localhost:5000/api/export',
  MAX_PARALLEL_UPLOADS: 5,     // class Api override = 10
  PREVIEW_BRIGHTNESS: 20,
  PREVIEW_CONTRAST: 1.3
}

state = {
  images: [],             // ImageModel[]
  documentIds: [],        // server-side IDs
  stream: null,           // MediaStream
  sortable: null,         // SortableJS instance
  currentLightboxIndex: 0,
  isLoading: false,
  pinchStartDistance: 0,
  currentScale: 1
}
```

#### `app.js` — Application Entry Point

**App class — Khởi tạo toàn bộ hệ thống:**
```
App.init()
  ├── new Toast(container)
  ├── new Camera(elements)
  ├── new Capture(elements, imageStore)
  ├── new ImageList(elements, imageStore)
  ├── new Lightbox(elements, imageStore)
  ├── new Api(imageStore, elements)
  ├── setupEventListeners()
  ├── imageList.init()
  ├── lightbox.init()
  ├── camera.init()
  ├── loadImages()     # từ localStorage (chỉ cleanup, không restore)
  └── setupCleanup()   # beforeunload → stop camera + revoke URLs
```

#### `Camera.js` — Webcam Access & Control

| Method | Mô tả |
|--------|-------|
| `init()` | getUserMedia → gán stream vào video element |
| `stop()` | Dừng tất cả tracks |
| `setFocus(mode, distance)` | Điều chỉnh focus (continuous/manual) |
| `triggerFocus()` | Bật continuous autofocus |

**Xử lý rotation:**
- Camera vật lý đặt ngang → xoay video preview -90°
- Scale 0.5 để vừa viewport
- Aspect ratio tự động tính: `rotatedAspectRatio = videoHeight / videoWidth`

#### `Capture.js` — Chụp ảnh từ Webcam

| Method | Mô tả |
|--------|-------|
| `capture()` | Chụp canvas từ video frame + flash effect |
| `saveImage(w, h)` | Canvas → Blob (PNG lossless) → ImageModel → ImageStore |

**Xử lý rotation khi capture:**
```
Canvas: swap width/height (videoHeight × videoWidth)
  → ctx.translate(center)
  → ctx.rotate(-π/2)
  → ctx.drawImage(video, -videoWidth/2, -videoHeight/2, ...)
  → canvas.toBlob('image/png')
```

#### `ImageList.js` — Thumbnail & Drag-Sort

| Method | Mô tả |
|--------|-------|
| `init()` | Khởi tạo SortableJS drag-and-drop |
| `render(model, index)` | Render thumbnail mới + batched queue |
| `delete(id)` | Xóa ảnh theo ID |
| `clear()` | Xóa toàn bộ danh sách |
| `onReorder(evt)` | Cập nhật thứ tự sau khi kéo thả |

**SortableJS config:**
```javascript
new Sortable(element, {
  animation: 100,
  ghostClass: 'sortable-ghost',
  chosenClass: 'sortable-chosen',
  handle: '.image-item',
  delay: 30,
  delayOnTouchOnly: true,
  onEnd: this.onReorder
})
```

#### `Lightbox.js` — Full-screen Preview

| Method | Mô tả |
|--------|-------|
| `open(index)` | Mở lightbox tại ảnh thứ index |
| `close()` | Đóng lightbox |
| `navigate(direction)` | Chuyển ảnh (+1 / -1) |
| `resetZoom()` | Reset scale về 1 |

**Tương tác:**
- **Click outside** → Close
- **Bàn phím**: Escape (close), ← → (navigate)
- **Touch**: Swipe lên/xuống (close), Pinch (zoom 1x–4x)
- **Mouse wheel**: Zoom in/out
- **Image filter**: `brightness(1.3) contrast(1.4) saturate(1.2)`

#### `Toast.js` — Notification System

| Method | Mô tả |
|--------|-------|
| `show(message, type)` | Hiển thị toast (success/error/info) trong 3s |

Toast tự động biến mất sau 3 giây với animation slideOut.

#### `imageProcessing.js` — Xử lý ảnh Client-Side

**Pipeline auto-crop (Canny edge detection + perspective warp):**

```
Input Canvas
  │
  ├─► toGrayscale()        — Chuyển sang grayscale
  ├─► gaussianBlur()       — Làm mờ (kernel 5×5)
  ├─► cannyEdge()          — Phát hiện cạnh (Sobel + hysteresis)
  ├─► findDocumentCorners()— Tìm 4 góc của tài liệu:
  │   ├─ convexHull()
  │   ├─ approximateQuadrilateral()
  │   └─ orderCorners()    — Sắp xếp: TL, TR, BR, BL
  └─► perspectiveWarp()    — Biến đổi phối cảnh → ảnh phẳng
```

> **Note:** Module này được export nhưng chưa được import trong app.js. Backend (Python) xử lý auto-crop bằng OpenCV CLAHE.

#### `Api.js` — REST API Communication

| Method | Mô tả |
|--------|-------|
| `uploadImage(model)` | POST 1 ảnh lên `/api/upload` (FormData PNG) |
| `uploadAllImages()` | Upload song song max 10 ảnh, trả về IDs |
| `createPDF()` | Upload ảnh + POST `/api/export` → tạo PDF + in vé |
| `certifyDocuments()` | Fetch identity → upload ảnh → tạo PDF (serviceId=99) |
| `showPdfModal(pdfUrl)` | Hiển thị PDF với 2 nút chứng thực |

**createPDF() — Validation logic:**
```
if (hasImages && hasService)    → Upload + Export
if (hasImages && !hasService)   → Error: "xin vui lòng chọn dịch vụ"
if (!hasImages && hasService)   → Error: "xin vui lòng tải ảnh lên"
if (!hasImages && !hasService)  → Error: "xin vui lòng tải ảnh lên và chọn dịch vụ"
```

**certifyDocuments() — Luồng xử lý:**
```
1. Kiểm tra có ảnh?
2. Fetch GET http://localhost:5431/ → lấy fullName từ cardObj
3. Upload tất cả ảnh (parallel)
4. POST /api/export với { serviceId: 99, serviceName: fullName }
5. Nhận PDF → showPdfModal(pdfUrl)
```

**PDF Modal — 3 buttons footer:**
| Nút | Hành động |
|-----|-----------|
| ❌ **Đóng** | Close modal + revoke blob URL |
| 🏷️ **Chứng thực tài liệu** | Open dichvucong URL + redirect index.html |
| ✍️ **Chứng thực chữ ký** | Open dichvucong URL + redirect index.html |

---

### 3.5 `index3.html` — Overlay Elements (Loading & Lightbox)

Ngoài layout chính, `index3.html` định nghĩa sẵn 2 overlay quan trọng:

| Element ID | Loại | Mô tả |
|------------|------|-------|
| `#loading-overlay` | Full-screen overlay | Loading spinner + message "Đang tạo PDF..." |
| `#lightbox` | Full-screen overlay | Xem ảnh toàn màn hình (zoom, swipe, navigate) |
| `#toast-container` | Fixed top-right | Container chứa các toast notification |

Xem chi tiết overlay hoạt động tại **[Mục 4 — Hệ thống Overlay & Popup](#4-hệ-thống-overlay--popup)**.

---

### 3.6 `ImageModel.js` — Data Model

```
ImageModel (1 ảnh)
  ├── id: Date.now()
  ├── blob: Blob (PNG lossless)
  ├── url: URL.createObjectURL(blob)
  ├── width / height
  ├── timestamp: ISO string
  └── methods: revokeUrl(), rotate(), loadImage(), toJSON()

ImageStore (quản lý collection)
  ├── images: ImageModel[]
  ├── add(model)
  ├── remove(id)
  ├── get(id) / getByIndex(idx) / findIndex(id)
  ├── clear()
  ├── reorder(newOrder)
  ├── count (getter)
  └── getAll()
```

---

## 4. Hệ thống Overlay & Popup

> **3 cơ chế overlay độc lập**: Loading overlay (toàn màn hình), PDF Modal (full-screen), và Toast (fixed top-right).

### 4.1 Loading Overlay — `#loading-overlay`

**Kích hoạt bởi:** `Api.setLoading(true)` — khi bắt đầu upload ảnh hoặc tạo PDF.

**Cấu trúc HTML (có sẵn trong index3.html):**
```html
<div id="loading-overlay" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center">
  <div class="bg-gray-800 rounded-2xl p-8 text-center shadow-2xl">
    <div class="relative w-20 h-20 mx-auto mb-4">
      <div class="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
      <div class="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
    <p class="text-white text-lg font-medium">Đang tạo PDF...</p>
    <p class="text-gray-400 text-sm mt-2">Vui lòng chờ trong giây lát</p>
  </div>
</div>
```

**Trạng thái:**
- `hidden` class: overlay ẩn (mặc định)
- Không có `hidden`: overlay hiện + backdrop blur

**Luồng hoạt động:**
```
Api.setLoading(true)
  → #loading-overlay.classList.remove('hidden')
  → Vô hiệu hóa các nút: pdfBtn.disabled = true, captureBtn.disabled = true
  → Chặn tương tác người dùng với toàn bộ trang (inset + z-50)

... (upload / export hoàn tất)

Api.setLoading(false)
  → #loading-overlay.classList.add('hidden')
  → Kích hoạt lại các nút: pdfBtn.disabled = false, captureBtn.disabled = false
```

**Z-index:** `z-50` (cao hơn lightbox `z-50` — cùng cấp, nhưng loading overlay xuất hiện trước/hết sau).

---

### 4.2 PDF Modal — `showPdfModal(pdfUrl)` (Pop-up động)

**Kích hoạt bởi:** `Api.createPDF()` hoặc `Api.certifyDocuments()` sau khi nhận được PDF blob từ backend.

**Không có sẵn trong HTML — được tạo động bằng JavaScript trong `Api.showPdfModal()`.**

**Cấu trúc HTML động (tạo bằng JS):**

```html
<div id="pdf-modal" class="fixed inset-0 bg-black z-[100] flex flex-col">
  <!-- Header -->
  <div class="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
    <h3 class="text-xl font-semibold text-white">
      <i class="fas fa-file-pdf mr-2"></i>PDF đã tạo
    </h3>
    <button id="pdf-modal-close" class="text-gray-400 hover:text-white text-2xl">
      <i class="fas fa-times"></i>
    </button>
  </div>

  <!-- PDF Viewer - full remaining space -->
  <div class="flex-1 overflow-hidden">
    <iframe src="[pdfUrl]" class="w-full h-full border-0" title="PDF Viewer"></iframe>
  </div>

  <!-- Footer with 3 buttons -->
  <div class="flex justify-between p-4 border-t border-gray-700 bg-gray-800">
    <button id="pdf-modal-close-btn" class="bg-gray-600 hover:bg-gray-700 ...">
      ❌ Đóng
    </button>
    <div class="flex gap-3">
      <button id="pdf-modal-certify-doc" class="bg-blue-500 ...">
        🏷️ Chứng thực tài liệu
      </button>
      <button id="pdf-modal-certify-sign" class="bg-green-500 ...">
        ✍️ Chứng thực chữ ký
      </button>
    </div>
  </div>
</div>
```

**Sơ đồ luồng hiển thị PDF Modal:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PDF MODAL — FULL SCREEN POPUP                      │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  HEADER      [📄 PDF đã tạo]                          [❌]   │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │                                                         │  │  │
│  │  │              IFRAME PDF VIEWER                          │  │  │
│  │  │       (full remaining height, chiếm toàn bộ             │  │  │
│  │  │        khoảng trống giữa header và footer)              │  │  │
│  │  │                                                         │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  FOOTER     [❌ Đóng]            [🏷️ C.tác tài liệu] [✍️ C.tác chữ ký] │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Z-index: z-[100] (cao nhất, phủ lên tất cả)                          │
│  Background: bg-black (che hoàn toàn index3.html)                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Luồng tương tác trong PDF Modal:**

```
PDF Modal xuất hiện (sau khi tạo PDF thành công)
  │
  ├── User xem PDF trong iframe (có thể cuộn, phóng to)
  │
  ├── [❌ Đóng]
  │     ├─► modal.remove() — Xóa khỏi DOM
  │     ├─► URL.revokeObjectURL(pdfUrl) — Giải phóng bộ nhớ
  │     └─► Quay lại giao diện scan (index3.html)
  │
  ├── [🏷️ Chứng thực tài liệu]
  │     ├─► window.open('https://dichvucong.thainguyen.gov.vn/...', '_blank')
  │     ├─► modal.remove() + revoke blob URL
  │     └─► setTimeout → redirect window.location.href = 'index.html'
  │
  ├── [✍️ Chứng thực chữ ký]
  │     ├─► window.open('https://dichvucong.thainguyen.gov.vn/...', '_blank')
  │     ├─► modal.remove() + revoke blob URL
  │     └─► setTimeout → redirect window.location.href = 'index.html'
  │
  └── [ESC key]
        └─► Giống nút Đóng: modal.remove() + revoke blob URL
```

**Chi tiết các hành động khi click nút chứng thực:**
```
1. Mở tab mới → Cổng dịch vụ công Thái Nguyên (xem Mục 5)
2. Đóng modal + dọn dẹp blob URL
3. Chờ 100ms → redirect về index.html (trang chọn dịch vụ)
   → User đã có PDF trong tab mới, sẵn sàng nộp hồ sơ trên dichvucong
```

---

### 4.3 Lightbox Overlay — `#lightbox`

**Kích hoạt bởi:** Click vào thumbnail ảnh trong ImageList.

**Z-index:** `z-50` (ngang với loading overlay, nhưng thấp hơn PDF Modal `z-[100]`).

**Chi tiết:** Xem tại [Lightbox.js — Full-screen Preview](#lightboxjs--full-screen-preview).

---

### 4.4 Toast Container — `#toast-container`

**Vị trí:** Fixed top-right, `z-[60]` (giữa lightbox/z-50 và PDF modal/z-[100]).

**Cấu trúc:**
```html
<div id="toast-container" class="fixed top-4 right-4 z-[60] space-y-2"></div>
```

**Các Toast tự động biến mất sau 3 giây với animation.**

**Bảng tổng hợp overlay theo Z-index:**

| Component | Z-index | Loại | Nền |
|-----------|---------|------|-----|
| `#toast-container` | `z-[60]` | Fixed | Trong suốt |
| `#lightbox` | `z-50` | Fixed | `bg-black/95` |
| `#loading-overlay` | `z-50` | Fixed | `bg-black/70 backdrop-blur-sm` |
| `#pdf-modal` | `z-[100]` | Fixed | `bg-black` |

---

## 5. Luồng dịch vụ hành chính công (External)

> **Kết nối với Cổng dịch vụ công Thái Nguyên** để thực hiện nộp hồ sơ chứng thực trực tuyến.
> Frontend không xử lý các form này — chỉ mở URL sang hệ thống bên ngoài.

### 5.1 Các liên kết đến Cổng dịch vụ công

Có **3 điểm chạm** với hệ thống dịch vụ công trong frontend:

#### 🔗 index.html — Thẻ "Dịch vụ công"

```
[index.html]
  └── Thẻ số 8: "🌐 Dịch vụ công"
       └── <a href="https://dichvucong.gov.vn/" target="_blank" rel="noopener noreferrer">
            └── Mở tab mới → Cổng DVC quốc gia (dichvucong.gov.vn)
```

#### 🔗 PDF Modal — Nút "Chứng thực tài liệu"

```
[PDF Modal] → [🏷️ Chứng thực tài liệu]
  └── window.open('https://dichvucong.thainguyen.gov.vn/nop-ho-so'
                   + '?MaTTHCDP=2.000815.000.00.00.H55'
                   + '&MaCoQuanThucHien=H55.242'
                   + '&vnconnect=1'
                   + '&MaDVC=2.000815.000.00.00.H55.02'
                   + '&MDT=MzQ1ZTQwMDctY2ZlMS00YmQ4LTgxNjctN2MxZTYzYjUzNjU3',
                   '_blank')
  → Mở form: "Chứng thực bản sao điện tử từ bản chính" (dịch vụ công Thái Nguyên)
  → User có thể upload file PDF đã tạo từ kiosk lên form này
```

#### 🔗 PDF Modal — Nút "Chứng thực chữ ký"

```
[PDF Modal] → [✍️ Chứng thực chữ ký]
  └── window.open('https://dichvucong.thainguyen.gov.vn/nop-ho-so'
                   + '?MaTTHCDP=2.000884.000.00.00.H55'
                   + '&MaCoQuanThucHien=H55.242'
                   + '&vnconnect=1'
                   + '&MaDVC=2.000884.000.00.00.H55.01'
                   + '&MDT=MzQ1ZTQwMDctY2ZlMS00YmQ4LTgxNjctN2MxZTYzYjUzNjU3',
                   '_blank')
  → Mở form: "Chứng thực chữ ký người dịch" (dịch vụ công Thái Nguyên)
  → User có thể upload file PDF + thực hiện chứng thực chữ ký
```

### 5.2 Phân tích tham số URL

```
https://dichvucong.thainguyen.gov.vn/nop-ho-so
  ?MaTTHCDP=...                      # Mã thủ tục hành chính
  &MaCoQuanThucHien=H55.242          # Mã cơ quan thực hiện (UBND tỉnh Thái Nguyên)
  &vnconnect=1                       # Kết nối VNeID/định danh
  &MaDVC=...                         # Mã dịch vụ công (phiên bản cụ thể)
  &MDT=MzQ1ZTQwMDctY2ZlMS00YmQ4...   # Mã định danh giao dịch (base64)
```

| Tham số | Chứng thực tài liệu | Chứng thực chữ ký |
|---------|---------------------|-------------------|
| MaTTHCDP | `2.000815.000.00.00.H55` | `2.000884.000.00.00.H55` |
| MaDVC | `2.000815.000.00.00.H55.02` | `2.000884.000.00.00.H55.01` |
| Mô tả | Chứng thực bản sao điện tử từ bản chính | Chứng thực chữ ký người dịch |
| Cơ quan | UBND tỉnh Thái Nguyên (H55.242) | UBND tỉnh Thái Nguyên (H55.242) |

### 5.3 Luồng nghiệp vụ hoàn chỉnh (từ kiosk → nộp hồ sơ)

```
┌─────────────────────────────────────────────────────────────────────────┐
│           LUỒNG NGHIỆP VỤ: KIOSK → CỔNG DỊCH VỤ CÔNG                    │
│                                                                          │
│  Bước 1: User scan tài liệu tại kiosk                                    │
│    ├── Chụp ảnh tài liệu qua webcam                                     │
│    ├── Sắp xếp thứ tự (drag-and-drop)                                    │
│    └── Click [📄 Lấy số thứ tự] hoặc [🏷️ Chứng thực]                     │
│                                                                          │
│  Bước 2: Hệ thống tạo PDF                                                │
│    ├── Upload ảnh → Backend xử lý (CLAHE, sharpen)                      │
│    ├── Backend tạo file PDF                                              │
│    └── Trả PDF blob về frontend                                          │
│                                                                          │
│  Bước 3: Hiển thị PDF Modal                                              │
│    ├── User xem lại PDF trong iframe                                     │
│    └── Chọn 1 trong 2 hướng:                                            │
│                                                                          │
│    ┌─ A. [🏷️ Chứng thực tài liệu] ─────────────────────────────────┐   │
│    │  ├── Mở tab mới → Form chứng thực bản sao điện tử                │   │
│    │  ├── User tải PDF từ máy (đã lưu từ kiosk) lên form              │   │
│    │  ├── Điền thông tin bổ sung (nếu cần)                            │   │
│    │  └── Nộp hồ sơ → Chờ xử lý → Nhận kết quả chứng thực            │   │
│    └───────────────────────────────────────────────────────────────┘   │
│                                                                          │
│    ┌─ B. [✍️ Chứng thực chữ ký] ──────────────────────────────────┐   │
│    │  ├── Mở tab mới → Form chứng thực chữ ký người dịch            │   │
│    │  ├── User tải PDF + thực hiện chứng thực chữ ký                 │   │
│    │  ├── Điền thông tin bổ sung (nếu cần)                           │   │
│    │  └── Nộp hồ sơ → Chờ xử lý → Nhận kết quả chứng thực           │   │
│    └───────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Bước 4: Sau khi click nút chứng thực                                   │
│    ├── PDF Modal tự động đóng                                           │
│    ├── Trang kiosk redirect về index.html (trang chủ)                   │
│    └── User thao tác trên tab dichvucong đã mở                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Mối quan hệ giữa "Chứng thực tài liệu" và "Dịch vụ chứng thực"

Trong frontend có **2 đường dẫn khác nhau** dẫn đến chức năng chứng thực:

| Đường dẫn | Xuất phát | Hành động |
|-----------|-----------|-----------|
| **A — Qua scan** | `index3.html` → [🏷️ Chứng thực tài liệu] | Upload ảnh + tạo PDF + redirect đến dichvucong |
| **B — Qua thẻ CCCD** | `index.html` → "Dịch vụ chứng thực" → `index2.html` → `index3.html` | Cắm thẻ → vào scan → [📄 Lấy số thứ tự] hoặc [🏷️ Chứng thực] |

Cả 2 đường dẫn đều kết thúc tại `index3.html` và sử dụng cùng cơ chế PDF Modal để chuyển tiếp sang dichvucong.

---

### 6.1 Luồng "Lấy số thứ tự" (PDF + Ticket)

```
User chụp ảnh xong
  → Chọn dịch vụ từ dropdown
  → Click [📄 Lấy số thứ tự]
     │
     ├─► Validation (ảnh + service)
     │
     ├─► uploadAllImages() — Parallel upload (max 10)
     │   └─► POST /api/upload { file: PNG } → { id: string }
     │
     ├─► POST /api/export { ids, serviceId, serviceName }
     │   └─► Backend: đọc ảnh → CLAHE enhance → tạo PDF → lưu + log
     │   └─► Response: PDF blob
     │
     ├─► Hiển thị PDF Modal
     │   └─► [Chứng thực tài liệu] → Open dichvucong → redirect index.html
     │   └─► [Chứng thực chữ ký]   → Open dichvucong → redirect index.html
     │
     └─► clearAllImages()
```

### 6.2 Luồng "Chứng thực tài liệu" (Certify)

```
User chụp ảnh xong
  → Click [🏷️ Chứng thực tài liệu]
     │
     ├─► GET http://localhost:5431/  (lấy thông tin CCCD)
     │   └─► Response: { data: { cardObj: { fullName: "Nguyễn Văn A" } } }
     │
     ├─► uploadAllImages() — Parallel upload
     │
     ├─► POST /api/export { ids, serviceId: 99, serviceName: fullName }
     │
     ├─► PDF Modal hiển thị
     │
     └─► clearAllImages()
```

### 6.3 Luồng tương tác người dùng trên index3.html

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERACTION MAP                      │
│                                                               │
│  [Trang load]                                                 │
│      │                                                        │
│      ├─► Camera.init() → Webcam stream                        │
│      ├─► ImageList.init() → SortableJS ready                  │
│      └─► Lưu state trong memory (không persist blob)          │
│                                                               │
│  [User chụp ảnh]                                              │
│      │                                                        │
│      ├─► Flash hiệu ứng                                      │
│      ├─► Canvas capture (rotate -90°)                         │
│      ├─► ImageModel tạo mới → ImageStore.add()                │
│      ├─► ImageList.render() → Thumbnail xuất hiện             │
│      ├─► Toast: "Đã chụp ảnh"                                 │
│      └─► saveImages() → localStorage (metadata chỉ để cleanup)│
│                                                               │
│  [User click thumbnail]                                       │
│      └─► Lightbox.open(index) → fullscreen preview            │
│          ├─► Swipe/Arrows → navigate                          │
│          ├─► Pinch/Scroll → zoom                              │
│          └─► Click outside/Escape → close                     │
│                                                               │
│  [User drag thumbnail]                                        │
│      └─► SortableJS onEnd → ImageStore.reorder()              │
│          └─► Cập nhật số thứ tự trên mỗi thumbnail            │
│                                                               │
│  [User hover thumbnail]                                       │
│      └─► Delete button hiện ra (opacity 0→1)                  │
│          └─► Click × → Xóa ảnh                                │
│                                                               │
│  [User click 🗑️ Xóa tất cả]                                   │
│      └─► ImageStore.clear() + ImageList.clear()               │
│          └─► localStorage.removeItem('webscan_images')        │
│          └─► Toast: "Đã xóa tất cả ảnh"                       │
│                                                               │
│  [User click 📄 Lấy số thứ tự]                                │
│      └─► (Xem 4.1 Luồng PDF + Ticket)                         │
│                                                               │
│  [User click 🏷️ Chứng thực]                                   │
│      └─► (Xem 4.2 Luồng Certify)                              │
│                                                               │
│  [User rời trang]                                             │
│      └─► beforeunload → stop camera + revoke all blob URLs    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Sơ đồ lớp & module

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MODULE DEPENDENCY TREE                           │
│                                                                          │
│  index3.html (entry)                                                     │
│      │                                                                   │
│      └── type="module" script import:                                    │
│            │                                                             │
│            ├── config.js  ←──── state (global singleton)                 │
│            │       │                                                     │
│            │       └── CONFIG: API endpoints, quality settings           │
│            │       └── state: images[], documentIds[], stream, ...       │
│            │                                                             │
│            ├── models/ImageModel.js                                      │
│            │       ├── class ImageModel (id, blob, url, w, h, ts)        │
│            │       └── class ImageStore (add, remove, get, clear, count) │
│            │                                                             │
│            ├── components/                                               │
│            │       ├── Camera.js ──── depends on: state                  │
│            │       ├── Capture.js ─── depends on: ImageModel, state      │
│            │       ├── ImageList.js ─ depends on: imageStore, state      │
│            │       ├── Lightbox.js ─── depends on: imageStore, state     │
│            │       ├── Toast.js ────── depends on: nothing               │
│            │       └── Api.js ──────── depends on: CONFIG, state         │
│            │                                                             │
│            └── app.js ─────── main coordinator                           │
│                  ├── class App                                           │
│                  │     ├── constructor: khởi tạo elements + imageStore   │
│                  │     ├── init(): khởi tạo tất cả components            │
│                  │     ├── updateUI(): cập nhật counter + empty message  │
│                  │     ├── resetImages(): xóa toàn bộ                    │
│                  │     ├── saveImages(): lưu metadata (cleanup)          │
│                  │     └── loadImages(): load từ localStorage (cleanup)  │
│                  │                                                       │
│                  └── window.App singleton                                │
│                                                                          │
│  imageProcessing.js (độc lập, chưa được import)                          │
│      ├── toGrayscale()                                                   │
│      ├── gaussianBlur()                                                  │
│      ├── cannyEdge()                                                     │
│      ├── findDocumentCorners()                                           │
│      ├── perspectiveWarp()                                               │
│      └── autoCropCanvas()                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. API Endpoints

| Endpoint | Method | Module | Mô tả |
|----------|--------|--------|-------|
| `http://localhost:5000/api/upload` | POST | `Api.uploadImage()` | Upload 1 file PNG → trả về ID |
| `http://localhost:5000/api/export` | POST | `Api.createPDF()`, `Api.certifyDocuments()` | Tạo PDF từ danh sách IDs + service info |
| `http://localhost:5000/api/ticket` | POST | `index.html` (inline JS) | Tạo số thứ tự + in vé nhiệt |
| `http://localhost:5431/` | GET | `Api.certifyDocuments()` | Lấy thông tin CCCD (fullName) từ reader |

**Cấu trúc API Export:**
```
POST /api/export
Content-Type: application/json

{
  "ids": ["uuid1", "uuid2", ...],
  "serviceId": 1-6 | 99,
  "serviceName": "Tên dịch vụ" | "Họ tên công dân"
}

Response: binary PDF blob
```

---

## 9. Ghi chú kỹ thuật

### 9.1 Camera Rotation
- Camera đặt ngang (landscape) nhưng kiosk màn hình dọc (portrait)
- **Preview**: xoay video -90°, scale 0.5
- **Capture**: canvas `width=videoHeight, height=videoWidth`, rotate -90°, drawImage
- Output: ảnh PNG lossless, chiều dọc

### 9.2 Upload Strategy
- **Parallel upload**: tối đa 10 luồng đồng thời
- **Queue-based**: dùng đệ quy uploadNext() — khi 1 luồng hoàn thành, lấy ảnh tiếp theo
- **Format**: PNG lossless (giữ chất lượng tối đa cho backend xử lý)

### 9.3 CSS Grid Layout (index3.html)
```
#app {
  display: grid;
  grid-template-columns: 80% 20%;
  grid-template-rows: 80% 20%;
}
```
- **Responsive**: ≤768px chuyển thành 1 cột (50% / 30% / 20%)

### 9.4 Image Processing Pipeline
- **Client-side** (`imageProcessing.js`): Vanilla JS implementation của Canny edge detection + perspective warp. Hiện tại chưa được tích hợp.
- **Server-side** (Python backend): OpenCV CLAHE + sharpen + brightness adjustment. Đây là pipeline chính đang hoạt động.

### 9.5 Key Technical Decisions

| Quyết định | Lý do |
|------------|-------|
| **Vanilla JS (no framework)** | Giảm phụ thuộc, kiểm soát hoàn toàn, không cần build step |
| **PNG lossless** | Giữ chất lượng gốc trước khi backend xử lý |
| **Parallel upload (10x)** | Tận dụng bandwidth, tăng tốc độ |
| **SortableJS** | Nhẹ (8KB), hỗ trợ touch đầy đủ |
| **Tailwind CSS CDN** | Tạo mẫu nhanh, không cần build |
| **localStorage chỉ để cleanup** | Blob URL không serializable → chỉ lưu metadata để dọn dẹp |

---

*Tài liệu được tạo ngày 01/05/2026*
*Dựa trên mã nguồn frontend tại `c:\Users\Admin\Documents\GitHub\Kiosk-scan\frontend\`*
