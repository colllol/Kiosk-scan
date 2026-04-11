"""
Backend FastAPI cho Webcam Scan Document
Chức năng:
- Nhận ảnh từ frontend
- Chuyển đổi ảnh thành PDF
- Lưu PDF với format STT_DATETIME
- Export PDF về frontend

Note: Heavy modules are lazy-loaded to improve startup time
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
import io
import sys
import subprocess
import requests
from print_ticket import print_ticket
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import numpy as np

# Lazy import image processing module
import importlib
image_processor = None

def get_image_processor():
    """Lazy load image_processor module"""
    global image_processor
    if image_processor is None:
        image_processor = importlib.import_module('image_processor')
    return image_processor

# Import print_ticket module (will be bundled with EXE)
try:
    import print_ticket
    PRINT_AVAILABLE = True
    print("[INFO] print_ticket module loaded successfully")
except Exception as e:
    PRINT_AVAILABLE = False
    print(f"[WARNING] Could not load print_ticket module: {e}")

app = FastAPI(title="Webcam Scan Document API")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thư mục lưu trữ
# Khi chạy từ EXE, dùng thư mục chứa file EXE
# Khi chạy từ Python script, dùng thư mục chứa file .py
if getattr(sys, 'frozen', False):
    # Đang chạy từ file EXE
    SCRIPT_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] Running from EXE: {SCRIPT_DIR}")
else:
    # Đang chạy từ Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"[INFO] Running from Python script: {SCRIPT_DIR}")

# Mount static files để phục vụ ảnh background và các file tĩnh khác
app.mount("/static", StaticFiles(directory=SCRIPT_DIR), name="static")

UPLOAD_DIR = os.path.join(SCRIPT_DIR, "uploads")
PDF_DIR = os.path.join(SCRIPT_DIR, "pdfs")
LISTPDF_DIR = os.path.join(SCRIPT_DIR, "pdfs")
PRINT_TICKET_SCRIPT = os.path.join(SCRIPT_DIR, "print_ticket.py")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(LISTPDF_DIR, exist_ok=True)

print(f"[INFO] Upload directory: {UPLOAD_DIR}")
print(f"[INFO] PDF directory: {PDF_DIR}")
print(f"[INFO] Logo path would be: {os.path.join(UPLOAD_DIR, 'Logo.png')}")
print(f"[INFO] Logo exists: {os.path.exists(os.path.join(UPLOAD_DIR, 'Logo.png'))}")

# Lưu trữ các ảnh đã upload (temp)
uploaded_images = {}

# Model cho request
class ExportRequest(BaseModel):
    ids: List[str]
    filename: Optional[str] = None
    serviceId: Optional[int] = None
    serviceName: Optional[str] = None


class TicketRequest(BaseModel):
    serviceId: int
    serviceName: Optional[str] = None


class PrintTicketRequest(BaseModel):
    stt: int
    filename: Optional[str] = None
    serviceName: Optional[str] = None


def generate_pdf_filename():
    """Generate filename với format STT_DATETIME"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_document.pdf"


def extract_date_from_filename(filename):
    """Trích xuất ngày tháng từ tên file PDF (YYYYMMDD_HHMMSS_document.pdf)"""
    try:
        parts = filename.split('_')
        if len(parts) >= 1:
            return parts[0]
    except:
        pass
    return datetime.now().strftime("%Y%m%d")


def get_listpdfs_filename(date_str=None):
    """
    Get tên file listpdfs.txt theo ngày
    Format: YYYYMMDD_listpdfs.txt
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    return f"{date_str}_listpdfs.txt"


def get_next_stt(listpdfs_path):
    """
    Lấy STT tiếp theo từ file listpdfs.txt
    Nếu file không tồn tại, trả về 1
    Format: 0001, 0002, 0003...
    """
    if not os.path.exists(listpdfs_path):
        return 1

    max_stt = 0
    try:
        with open(listpdfs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Tìm STT lớn nhất
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('STT') or line.startswith('-'):
                    continue
                if '|' not in line:
                    continue
                stt_str = line.split('|')[0].strip()
                try:
                    stt = int(stt_str)
                    if stt > max_stt:
                        max_stt = stt
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error reading listpdfs.txt: {e}")
        return 1

    return max_stt + 1


def log_pdf_to_list(pdf_filename, listpdfs_path, serviceId=None, serviceName=None):
    """
    Ghi thông tin PDF vào file listpdfs.txt
    Format:
    STT | Ten File | ServiceId | ServiceName
    0001| 20260310_100811_document.pdf | 1 | Kinh tế - Xã hội
    0002| 20260310_100912_document.pdf | 2 | Tư pháp - Hộ tịch
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(listpdfs_path), exist_ok=True)

        # Lấy STT tiếp theo (format 4 chữ số)
        stt = get_next_stt(listpdfs_path)

        # Mở file để đọc/ghi
        lines = []
        file_exists = os.path.exists(listpdfs_path)

        if file_exists:
            with open(listpdfs_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        # Nếu file mới, thêm header
        if not file_exists or not lines:
            lines.append("STT   | Ten File                              | ServiceId | ServiceName\n")
            lines.append("-" * 70 + "\n")

        # Thêm bản ghi mới với STT format 4 chữ số (0001, 0002, ...)
        service_info = f" | {serviceId} | {serviceName}" if serviceId else ""
        lines.append(f"{stt:04d}| {pdf_filename}{service_info}\n")

        # Ghi lại file
        with open(listpdfs_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"Logged PDF to listpdfs: {pdf_filename} (STT: {stt:04d}, ServiceId: {serviceId})")
        return stt

    except Exception as e:
        print(f"Error logging PDF to listpdfs: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_datetime_from_pdf_filename(pdf_filename: str) -> Optional[datetime]:
    """
    Parse datetime from filename:
    - YYYYMMDD_HHMMSS_document.pdf
    """
    try:
        parts = pdf_filename.split('_')
        if len(parts) < 3:
            return None
        date_part = parts[0]
        time_part = parts[1]
        return datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
    except Exception:
        return None


def get_latest_ticket_from_list(listpdfs_path: str):
    """
    Lấy bản ghi mới nhất (STT lớn nhất) trong listpdfs.
    Return: (stt:int|None, pdf_filename:str|None, serviceId:int|None, serviceName:str|None)
    """
    if not os.path.exists(listpdfs_path):
        return None, None, None, None

    best_stt = None
    best_filename = None
    best_service_id = None
    best_service_name = None
    try:
        with open(listpdfs_path, "r", encoding="utf-8") as f:
            for raw in f.readlines():
                line = raw.strip()
                if not line or line.startswith("STT") or line.startswith("-"):
                    continue
                if "|" not in line:
                    continue
                parts = line.split("|")
                
                # Parse STT (phần 1)
                stt_str = parts[0].strip()
                try:
                    stt = int(stt_str)
                except Exception:
                    continue
                
                # Parse filename (phần 2)
                filename = parts[1].strip() if len(parts) > 1 else None
                
                # Parse serviceId (phần 3)
                service_id = None
                if len(parts) > 2:
                    sid_str = parts[2].strip()
                    try:
                        service_id = int(sid_str)
                    except ValueError:
                        pass
                
                # Parse serviceName (phần 4)
                service_name = None
                if len(parts) > 3:
                    service_name = parts[3].strip()
                
                # Cập nhật nếu STT lớn hơn
                if best_stt is None or stt > best_stt:
                    best_stt = stt
                    best_filename = filename
                    best_service_id = service_id
                    best_service_name = service_name
    except Exception as e:
        print(f"Error parsing listpdfs: {e}")
        return None, None, None, None

    return best_stt, best_filename, best_service_id, best_service_name


def send_ticket_to_api(stt: int, serviceId: int = 1, counterId: int = 1, pdf_filename: str = "", ticket_only: bool = False):
    """
    Gửi số thứ tự lên API QueueSystem
    API: http://192.168.100.238/QueueSystemAdmin/api/ticket/create
    
    Args:
        ticket_only: Nếu True, filePdf sẽ là khoảng trắng (cho chức năng lấy số từ index.html)
                     Nếu False, filePdf sẽ là tên file PDF (cho chức năng quét từ index1.html)
    """
    api_url = "http://192.168.100.238/QueueSystemAdmin/api/ticket/create"

    try:
        # Format số thứ tự thành 4 chữ số (0001, 0002, ...)
        formatted_stt = f"{stt:04d}"

        # Nếu ticket_only=True, filePdf sẽ là khoảng trắng
        file_pdf_value = " " if ticket_only else pdf_filename

        # Gửi request lên API
        print(f"[API] Sending to {api_url}: ticketNumber={formatted_stt}, serviceId={serviceId}, counterId={counterId}, filePdf={file_pdf_value}")

        response = requests.post(
            api_url,
            json={
                "ticketNumber": formatted_stt,
                "serviceId": serviceId,
                "counterId": counterId,
                "filePdf": file_pdf_value
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"[API] Response status: {response.status_code}")
        print(f"[API] Response body: {response.text}")

        if response.status_code in [200, 201]:
            print(f"[API] Successfully sent ticket {formatted_stt} to QueueSystem")
        else:
            print(f"[API] Failed to send ticket: HTTP {response.status_code} - {response.text}")

        return response.status_code in [200, 201]

    except requests.exceptions.RequestException as e:
        print(f"[API] Error sending ticket to QueueSystem: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_print_ticket(stt: int, dt: Optional[datetime], service_name: str = "HỘ TỊCH - CHỨNG THỰC"):
    """
    Call print_ticket function directly (no subprocess needed for EXE).
    Import lazily to avoid startup errors.
    """
    if not PRINT_AVAILABLE:
        print("[PRINT] Skipping print - print_ticket module not available")
        return

    try:
        print(f"[PRINT] Calling print function with STT={stt}, serviceName={service_name}")
        # Use the imported module directly
        print_ticket.print_ticket(stt, dt, service_name)
        print(f"[PRINT] Print job completed successfully")
    except Exception as e:
        print(f"[PRINT] Exception: {e}")
        import traceback
        traceback.print_exc()


def get_or_create_listpdfs(pdf_filename):
    """
    Lấy hoặc tạo file listpdfs.txt tương ứng với ngày của PDF
    Lưu vào backend/pdfs/ (chứa text, không chứa PDF)
    """
    # Trích xuất ngày từ tên file PDF
    pdf_date = extract_date_from_filename(pdf_filename)

    # Lấy ngày hiện tại
    current_date = datetime.now().strftime("%Y%m%d")

    # So sánh ngày
    # Nếu ngày của PDF khác ngày hiện tại, dùng ngày của PDF
    # Lý do: khi export PDF, ngày đã được định trong filename
    # Chúng ta muốn ghi vào file listpdfs của ngày đó

    listpdfs_filename = get_listpdfs_filename(pdf_date)
    listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)

    return listpdfs_path


def convert_image_to_pdf(image_path, output_path):
    """Chuyển đổi ảnh thành PDF với chất lượng cao nhất

    Tăng 15% độ sáng, dùng JPEG 90% để giữ chất lượng tốt và tốc độ nhanh
    """
    try:
        # Mở ảnh gốc
        img = Image.open(image_path)

        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img_width, img_height = img.size

        # Tạo PDF với kích thước theo ảnh gốc
        c = canvas.Canvas(output_path, pagesize=(img_width, img_height))

        # Convert ảnh sang format phù hợp cho reportlab
        # Sử dụng JPEG chất lượng 98% (tối đa, giảm nhiễu nén)
        temp_jpg = io.BytesIO()
        img.save(temp_jpg, format='JPEG', quality=98, optimize=True)
        temp_jpg.seek(0)

        # Draw ảnh vào PDF (không resize, không crop)
        img_reader = ImageReader(temp_jpg)
        c.drawImage(
            img_reader,
            0, 0,
            width=img_width,
            height=img_height,
            preserveAspectRatio=False
        )

        c.save()
        return True
    except Exception as e:
        print(f"Error converting image to PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_pdf_from_images(image_paths, output_path):
    """Tạo PDF từ danh sách ảnh - Xử lý tăng sáng/tương phản ở backend, đa luồng

    Backend xử lý: tăng sáng, tương phản, sharpening (chuyển từ frontend xuống)
    Giữ nguyên độ phân giải và tỉ lệ 1:1
    Tối ưu: Multi-threading batch processing
    """
    import time
    start_time = time.time()
    print(f"\n[PDF] Starting PDF creation with {len(image_paths)} image(s)...")

    try:
        # Lazy load image processor
        img_processor = get_image_processor()

        step_start = time.time()
        # Mở tất cả ảnh trước (mở 1 lần, dùng nhiều lần)
        pil_images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                pil_images.append(img)
            except Exception as e:
                print(f"[PDF] Warning: Could not open image {path}: {e}")
                # Skip invalid images but continue processing
        
        if not pil_images:
            print("[PDF] Error: No valid images to process")
            return False
            
        print(f"[PDF] Step 1 - Opened {len(pil_images)} images in {time.time() - step_start:.3f}s")

        step_start = time.time()
        # Xử lý batch song song với đa luồng
        processed_images = img_processor.process_scanned_images_batch(pil_images)
        print(f"[PDF] Step 2 - Batch processed images in {time.time() - step_start:.3f}s")

        # Verify all images were processed
        if len(processed_images) != len(pil_images):
            print(f"[PDF] Warning: Expected {len(pil_images)} images, got {len(processed_images)}")
            # Fill in any missing images with originals
            for i in range(len(pil_images)):
                if i >= len(processed_images) or processed_images[i] is None:
                    print(f"[PDF] Filling missing image {i} with original")
                    if i < len(processed_images):
                        processed_images[i] = pil_images[i]
                    else:
                        processed_images.append(pil_images[i])

        # Lấy kích thước từ ảnh đầu tiên
        processed_first = processed_images[0]
        if processed_first.mode != 'RGB':
            processed_first = processed_first.convert('RGB')

        pdf_width, pdf_height = processed_first.size

        # Create canvas with first image dimensions
        c = canvas.Canvas(output_path, pagesize=(pdf_width, pdf_height))

        step_start = time.time()
        for idx, processed_img in enumerate(processed_images):
            # Convert to RGB if needed
            if processed_img.mode != 'RGB':
                processed_img = processed_img.convert('RGB')

            img_width, img_height = processed_img.size

            # Save to BytesIO với JPEG chất lượng 98% (tối đa, giảm nhiễu nén)
            temp_jpg = io.BytesIO()
            processed_img.save(temp_jpg, format='JPEG', quality=98, optimize=True)
            temp_jpg.seek(0)

            # Draw ảnh (không resize, không crop, giữ nguyên kích thước gốc)
            img_reader = ImageReader(temp_jpg)
            c.drawImage(
                img_reader,
                0, 0,
                width=img_width,
                height=img_height,
                preserveAspectRatio=False
            )

            # Add trang mới nếu không phải ảnh cuối
            if idx < len(processed_images) - 1:
                # Update page size for next page if different
                next_img = processed_images[idx + 1]
                if next_img.mode != 'RGB':
                    next_img = next_img.convert('RGB')
                c.setPageSize((next_img.size[0], next_img.size[1]))
                c.showPage()

        c.save()
        total_time = time.time() - start_time
        print(f"[PDF] Step 3 - Created PDF in {time.time() - step_start:.3f}s")
        print(f"[PDF] ✅ PDF creation completed in {total_time:.3f}s - Saved to: {output_path}\n")
        return True
    except Exception as e:
        print(f"Error creating PDF from images: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.get("/")
async def root():
    """Serve trang HTML chính"""
    return {"message": "Webcam Scan Document API is running"}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload ảnh và xử lý
    Nhận file ảnh, lưu tạm, trả về ID và preview
    """
    try:
        # Generate unique ID
        image_id = str(uuid.uuid4())

        # Lưu file ảnh
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png']:
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JPG, JPEG, PNG")

        filename = f"{image_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Lưu thông tin
        uploaded_images[image_id] = {
            "id": image_id,
            "filename": filename,
            "path": file_path,
            "original_name": file.filename,
            "timestamp": datetime.now().isoformat()
        }

        # Generate preview base64 (nếu cần)
        with open(file_path, "rb") as f:
            import base64
            preview = base64.b64encode(f.read()).decode('utf-8')

        return {
            "id": image_id,
            "message": "Upload thành công",
            "preview": f"data:image/{file_extension};base64,{preview}"
        }

    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi upload: {str(e)}")


@app.post("/api/export")
async def export_pdf(request: ExportRequest, background_tasks: BackgroundTasks):
    """
    Export ảnh đã upload thành PDF
    Nhận danh sách ID ảnh, tạo PDF, lưu file, và trả về file PDF
    """
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="Không có ID nào được cung cấp")

        # Lấy danh sách path ảnh
        image_paths = []
        missing_ids = []

        for img_id in request.ids:
            if img_id not in uploaded_images:
                missing_ids.append(img_id)
                continue

            image_paths.append(uploaded_images[img_id]["path"])

        if missing_ids:
            print(f"Warning: Missing IDs: {missing_ids}")

        if not image_paths:
            raise HTTPException(status_code=404, detail="Không tìm thấy ảnh nào")

        # Generate filename với format STT_DATETIME
        pdf_filename = generate_pdf_filename()
        pdf_path = os.path.join(PDF_DIR, pdf_filename)

        # Tạo PDF từ ảnh
        success = create_pdf_from_images(image_paths, pdf_path)

        if not success:
            raise HTTPException(status_code=500, detail="Lỗi khi tạo PDF")

        print(f"PDF created: {pdf_path}")

        # Ghi thông tin PDF vào file listpdfs.txt tương ứng
        listpdfs_path = get_or_create_listpdfs(pdf_filename)
        latest_stt = log_pdf_to_list(pdf_filename, listpdfs_path, request.serviceId, request.serviceName)

        # NOTE: API QueueSystem và in ticket sẽ được xử lý bởi extension
        # khi detect URL /thong-tin-cong-dan

        # Trả về file PDF
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=pdf_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi export: {str(e)}")


@app.get("/api/latest-ticket")
async def get_latest_ticket():
    """
    Lấy thông tin ticket mới nhất từ listpdfs.txt
    Trả về TẤT CẢ thông tin: stt, filename, serviceId, serviceName
    Extension sẽ dùng thông tin này để gọi API QueueSystem và in ticket
    """
    try:
        # Lấy file listpdfs của ngày hiện tại
        current_date = datetime.now().strftime("%Y%m%d")
        listpdfs_filename = f"{current_date}_listpdfs.txt"
        listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)

        if not os.path.exists(listpdfs_path):
            raise HTTPException(status_code=404, detail="Không có ticket nào trong ngày hôm nay")

        # Đọc ticket mới nhất - TẤT CẢ thông tin từ listpdfs
        latest_stt, latest_filename, latest_service_id, latest_service_name = get_latest_ticket_from_list(listpdfs_path)

        if latest_stt is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy ticket nào")

        return {
            "stt": latest_stt,
            "formattedStt": f"{latest_stt:04d}",
            "filename": latest_filename,
            "serviceId": latest_service_id,
            "serviceName": latest_service_name
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting latest ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")


@app.post("/api/print-ticket")
async def print_ticket_endpoint(request: PrintTicketRequest):
    """
    In ticket theo yêu cầu từ extension
    Nhận stt và serviceName, gọi hàm in ticket
    """
    try:
        print(f"[PRINT API] Received print request: stt={request.stt}, serviceName={request.serviceName}")
        
        # Parse datetime từ filename nếu có
        dt = None
        if request.filename:
            dt = parse_datetime_from_pdf_filename(request.filename)
        
        # Gọi hàm in ticket
        run_print_ticket(request.stt, dt, request.serviceName or "HỘ TỊCH - CHỨNG THỰC")
        
        return {
            "success": True,
            "message": f"Đã gửi lệnh in ticket #{request.stt:04d}"
        }

    except Exception as e:
        print(f"[PRINT API] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi in ticket: {str(e)}")


@app.get("/api/images")
async def list_images():
    """Lấy danh sách ảnh đã upload"""
    return {
        "count": len(uploaded_images),
        "images": list(uploaded_images.values())
    }


@app.delete("/api/clear")
async def clear_images():
    """Xóa tất cả ảnh đã upload"""
    try:
        # Xóa files
        for img_id, img_data in uploaded_images.items():
            if os.path.exists(img_data["path"]):
                os.remove(img_data["path"])

        # Xóa dictionary
        uploaded_images.clear()

        return {"message": "Đã xóa tất cả ảnh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa: {str(e)}")


@app.post("/api/ticket")
async def create_ticket(request: TicketRequest, background_tasks: BackgroundTasks):
    """
    Tạo số thứ tự mới và in phiếu (không tạo PDF)
    Nhận serviceId, tạo STT mới trong listpdfs.txt, gửi lên API QueueSystem và in phiếu
    """
    try:
        # Generate filename với format STT_DATETIME (không cần lưu PDF thật)
        pdf_filename = generate_pdf_filename()

        # Lấy file listpdfs.txt cho ngày hiện tại
        current_date = datetime.now().strftime("%Y%m%d")
        listpdfs_filename = get_listpdfs_filename(current_date)
        listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)

        # Ghi STT mới vào listpdfs.txt (không có file PDF thật)
        latest_stt = log_pdf_to_list(pdf_filename, listpdfs_path, request.serviceId, request.serviceName)

        if latest_stt is None:
            raise HTTPException(status_code=500, detail="Không thể tạo số thứ tự")

        # Gửi số thứ tự lên API QueueSystem với serviceId và filePdf = " " (ticket_only=True)
        if latest_stt is not None:
            success = send_ticket_to_api(latest_stt, serviceId=request.serviceId, pdf_filename=pdf_filename, ticket_only=True)
            if not success:
                print(f"[WARNING] Failed to send ticket to QueueSystem")

        # In phiếu với STT mới
        dt = parse_datetime_from_pdf_filename(pdf_filename)
        if latest_stt is not None:
            run_print_ticket(latest_stt, dt, request.serviceName or "HỘ TỊCH - CHỨNG THỰC")

        # Format số thứ tự thành 4 chữ số
        formatted_stt = f"{latest_stt:04d}"

        return {
            "ticketNumber": formatted_stt,
            "serviceId": request.serviceId,
            "serviceName": request.serviceName or f"Dịch vụ {request.serviceId}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Ticket error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tạo số: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting Webcam Scan Document API...")
    print(f"[INFO] Frozen: {getattr(sys, 'frozen', False)}")
    print(f"[INFO] Upload directory: {os.path.abspath(UPLOAD_DIR)}")
    print(f"[INFO] PDF directory: {os.path.abspath(PDF_DIR)}")
    print(f"[INFO] Print available: {PRINT_AVAILABLE}")
    print("=" * 60)
    
    # Auto-start server when running as EXE
    if getattr(sys, 'frozen', False):
        print("[INFO] Running as EXE - Auto-starting server...")
        print("[INFO] Server will run until you close the window")
        print("[INFO] Press Ctrl+C to stop the server")
        print("=" * 60)
    
    # Run the server (this will block until stopped)
    uvicorn.run(app, host="0.0.0.0", port=5000)