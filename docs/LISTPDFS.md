# Quản lý File PDF và ListPDFs

## Cấu trúc Thư mục

```
frontend-webscan/
├── backend/
│   └── uploads/           # Thư mục lưu ảnh upload
└── pdfs/                   # Thư mục lưu PDF (frontend)
    ├── 20260310_listpdfs.txt  # File danh sách ngày 10/03/2026
    ├── 20260311_listpdfs.txt  # File danh sách ngày 11/03/2026
    ├── 20260310_100811_document.pdf
    └── 20260310_100912_document.pdf
```

## Cách hoạt động

### 1. Lưu file PDF
- PDF được lưu trực tiếp vào thư mục `frontend/pdfs/`
- Format filename: `YYYYMMDD_HHMMSS_document.pdf`
  - Ví dụ: `20260310_100811_document.pdf`

### 2. Quản lý ListPDFs.txt

#### File ListPDFs.txt được tạo theo ngày
- Format filename: `YYYYMMDD_listpdfs.txt`
- Ví dụ: `20260310_listpdfs.txt` cho ngày 10/03/2026

#### Cấu trúc file
```
STT   | Ten File
--------------------------------------------------
1     | 20260310_100811_document.pdf
2     | 20260310_100912_document.pdf
3     | 20260310_103015_document.pdf
```

### 3. Flow hoạt động

```
1. Frontend upload ảnh lên backend
         ↓
2. Backend tạo PDF với tên: YYYYMMDD_HHMMSS_document.pdf
         ↓
3. Trích xuất ngày từ tên PDF: YYYYMMDD
         ↓
4. Tìm file listpdfs.txt: YYYYMMDD_listpdfs.txt
         ↓
5a. Nếu file tồn tại → Đọc STT cuối cùng + 1
5b. Nếu file không tồn tại → Tạo file mới, STT = 1
         ↓
6. Ghi vào file listpdfs.txt
         ↓
7. Lưu PDF vào frontend/pdfs/
```

### 4. Xử lý ngày mới

Khi ngày thay đổi, hệ thống sẽ tự động:
- So sánh ngày trong filename PDF với ngày hiện tại
- Nếu khác → Tạo file listpdfs.txt mới cho ngày đó
- STT sẽ bắt đầu từ 1 trong file mới

### 5. Ví dụ minh họa

#### Ngày 10/03/2026 - 09:00
```
Tạo PDF: 20260310_090012_document.pdf
→ File: 20260310_listpdfs.txt
→ Nội dung:
  STT   | Ten File
  1     | 20260310_090012_document.pdf
```

#### Ngày 10/03/2026 - 10:30
```
Tạo PDF: 20260310_103015_document.pdf
→ File: 20260310_listpdfs.txt (tồn tại)
→ Nội dung:
  STT   | Ten File
  1     | 20260310_090012_document.pdf
  2     | 20260310_103015_document.pdf
```

#### Ngày 11/03/2026 - 08:45 (Ngày mới)
```
Tạo PDF: 20260311_084523_document.pdf
→ File: 20260311_listpdfs.txt (file mới)
→ Nội dung:
  STT   | Ten File
  1     | 20260311_084523_document.pdf
```

## Các hàm trong Backend

### `extract_date_from_filename(filename)`
Trích xuất ngày tháng từ tên file PDF
- Input: `20260310_100811_document.pdf`
- Output: `20260310`

### `get_listpdfs_filename(date_str=None)`
Lấy tên file listpdfs.txt theo ngày
- Input: `None` → dùng ngày hiện tại
- Input: `"20260310"` → dùng ngày đó
- Output: `20260310_listpdfs.txt`

### `get_next_stt(listpdfs_path)`
Lấy STT tiếp theo từ file listpdfs.txt
- Nếu file không tồn tại → trả về 1
- Nếu file tồn tại → đếm số dòng, trả về STT tiếp theo

### `log_pdf_to_list(pdf_filename, listpdfs_path)`
Ghi thông tin PDF vào file listpdfs.txt
- Đọc file hiện tại
- Lấy STT tiếp theo
- Thêm bản ghi mới
- Ghi lại file

### `get_or_create_listpdfs(pdf_filename)`
Lấy hoặc tạo file listpdfs.txt tương ứng với ngày của PDF
- Trích xuất ngày từ filename PDF
- Lấy path của file listpdfs.txt
- Đảm bảo thư mục tồn tại

## Lưu ý

- STT tự động tăng theo từng PDF trong ngày
- File listpdfs.txt được tạo tự động
- Nếu ngày trong filename khác ngày hiện tại → dùng ngày đó để tạo listpdfs.txt
- Hỗ trợ UTF-8 cho tên file tiếng Việt
