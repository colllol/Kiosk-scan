# Chrome Extension - Auto Fill Form Dịch Vụ Công

## 📋 Mô tả

Extension Chrome tự động điền thông tin vào form dịch vụ công tỉnh Thái Nguyên từ dữ liệu API JSON.

## ✨ Tính năng

- ✅ Tự động phát hiện trang form dịch vụ công
- ✅ Lấy dữ liệu từ API (JSON) và điền vào form
- ✅ Điền thủ công từ JSON data
- ✅ Hỗ trợ cả file local (form-replica.html) và website chính thức
- ✅ Đồng bộ với các trường trong form
- ✅ Lưu dữ liệu để tự động điền
- ✅ Hỗ trợ nhiều loại field: text, select, date, checkbox, textarea

## 📁 Cấu trúc thư mục

```
chrome-extension/
├── manifest.json          # Manifest V3 configuration
├── content.js             # Content script - chạy trên trang form
├── popup.html             # Giao diện popup
├── popup.js               # Script cho popup
├── background.js          # Background service worker
├── sample-data.json       # Dữ liệu mẫu để test
├── icons/                 # Icon files
│   ├── icon16.png        
│   ├── icon48.png        
│   ├── icon128.png       
│   ├── icon.svg          
│   ├── generate-icons.html  # Tool tạo icon
│   └── generate-icons.js    # Script tạo icon
└── README.md             # File này
```

## 🚀 Cài đặt

### 1. Load extension vào Chrome

1. Mở Chrome và vào `chrome://extensions/`
2. Bật **"Developer mode"** (góc trên bên phải)
3. Click **"Load unpacked"**
4. Chọn thư mục `chrome-extension`
5. Extension sẽ được cài đặt

### 2. Cấp quyền truy cập file local (QUAN TRỌNG!)

Để extension hoạt động với file `form-replica.html`:

1. Vào `chrome://extensions/`
2. Tìm extension "Auto Fill Form - Dịch Vụ Công"
3. Click **"Details"**
4. Bật toggle **"Allow access to file URLs"** (Cho phép truy cập URL file)

⚠️ **Nếu không bật option này, extension sẽ không hoạt động với file local!**

## 📖 Hướng dẫn sử dụng

### Cách 1: Điền thủ công từ JSON (Test với form-replica.html)

1. Mở file `form-replica.html` trong Chrome (kéo file vào trình duyệt)
2. Click vào icon extension trên thanh công cụ
3. Copy nội dung từ file `sample-data.json` và dán vào ô "Dán dữ liệu JSON"
4. Click **"Điền vào form"**
5. Extension sẽ tự động điền dữ liệu vào các trường

### Cách 2: Tự động từ API

1. Mở trang form (form-replica.html hoặc dichvucong.thainguyen.gov.vn)
2. Click vào icon extension
3. Nhập URL API trả về dữ liệu JSON
4. Click **"Lấy dữ liệu và điền form"**
5. Extension sẽ fetch data từ API và tự động điền vào form

### Cách 3: Tự động điền khi load trang

1. Extension sẽ tự động kiểm tra localStorage
2. Nếu có dữ liệu đã lưu, sẽ tự động điền khi mở trang form

## 🔧 Cấu trúc dữ liệu JSON

Extension hỗ trợ các field sau trong JSON:

```json
{
  "applicant_name": "Nguyễn Văn A",
  "ten_nguoi_nop": "Nguyễn Văn A",
  "birth_date": "1990-01-15",
  "ngay_sinh": "1990-01-15",
  "id_number": "0361240112234",
  "cmnd": "0361240112234",
  "issue_date": "2020-01-16",
  "ngay_cap": "2020-01-16",
  "issue_place": "Cục Cảnh sát QLHC",
  "noi_cap": "Cục Cảnh sát QLHC",
  "phone": "0879827008",
  "so_dien_thoai": "0879827008",
  "email": "example@email.com",
  "address": "Phường Láng, Thành phố Hà Nội",
  "dia_chi": "Phường Láng, Thành phố Hà Nội",
  "address_detail": "123 Đường ABC",
  "dia_chi_chi_tiet": "123 Đường ABC",
  "commitment": true,
  "cam_ket": true
}
```

## 🎯 Mapping fields

| JSON Key | Form Field | Type |
|----------|-----------|------|
| `applicant_name` | Input tên người nộp | text |
| `ten_nguoi_nop` | Input tên người nộp | text |
| `birth_date` | Input ngày sinh | date |
| `ngay_sinh` | Input ngày sinh | date |
| `id_number` | Input CMND | text |
| `cmnd` | Input CMND | text |
| `issue_date` | Input ngày cấp | date |
| `ngay_cap` | Input ngày cấp | date |
| `issue_place` | Input nơi cấp | text |
| `noi_cap` | Input nơi cấp | text |
| `phone` | Input số điện thoại | text |
| `so_dien_thoai` | Input số điện thoại | text |
| `email` | Input email | text |
| `address` | Select địa chỉ | select |
| `dia_chi` | Select địa chỉ | select |
| `address_detail` | Input địa chỉ chi tiết | text |
| `dia_chi_chi_tiet` | Input địa chỉ chi tiết | text |
| `commitment` | Checkbox cam kết | checkbox |
| `cam_ket` | Checkbox cam kết | checkbox |

## 🐛 Troubleshooting

### ❌ Lỗi "Could not establish connection. Receiving end does not exist"

**Nguyên nhân:** Content script chưa được load trên trang hiện tại.

**Cách khắc phục:**
1. **Reload trang** (nhấn F5)
2. **Mở lại popup** extension (click icon extension)
3. Nếu dùng file local: **Bật "Allow access to file URLs"** trong chrome://extensions/
4. Đảm bảo đang mở đúng file form (form-replica.html)

### ❌ Lỗi "Not on valid form page"

**Cách khắc phục:**
- Đảm bảo đang mở file `form-replica.html` hoặc trang `dichvucong.thainguyen.gov.vn`
- Kiểm tra console (F12) để xem URL hiện tại

### ❌ Extension không điền được vào một số field

- Một số field bị `disabled` sẽ không điền được
- Kiểm tra JSON data có đúng format không
- Kiểm tra console logs để xem chi tiết

### ❌ API không trả về data

- Kiểm tra API URL có đúng không
- API phải trả về Content-Type: application/json
- API phải cho phép CORS hoặc cùng domain

## 🔒 Bảo mật

- Extension chỉ hoạt động trên các domain được chỉ định
- Không gửi dữ liệu ra ngoài
- Dữ liệu chỉ được lưu trong localStorage của extension
- API call được thực hiện trực tiếp từ content script

## 📝 Ghi chú

- Extension được thiết kế riêng cho form dịch vụ công tỉnh Thái Nguyên
- Có thể mở rộng mapping để hỗ trợ thêm fields
- Dữ liệu JSON có thể thiếu field, extension sẽ bỏ qua các field không tìm thấy
- **Quan trọng**: Bật "Allow access to file URLs" để dùng với file local

## 🔄 Version History

### v1.0.0 (2026-04-06)
- ✅ Manifest V3
- ✅ Content script
- ✅ Popup UI
- ✅ Background service worker
- ✅ Auto-fill from API
- ✅ Manual JSON input
- ✅ Auto-fill on page load
- ✅ localStorage persistence
- ✅ Hỗ trợ file local (form-replica.html)

## 📞 Support

Mọi vấn đề vui lòng kiểm tra:
1. Console logs (F12 → Console)
2. Extension logs (F12 → Background page)
3. Popup status messages

## 📄 License

MIT License
