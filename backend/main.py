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
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] Running from EXE: {SCRIPT_DIR}")
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"[INFO] Running from Python script: {SCRIPT_DIR}")

# Mount static files
app.mount("/static", StaticFiles(directory=SCRIPT_DIR), name="static")

UPLOAD_DIR = os.path.join(SCRIPT_DIR, "uploads")
PDF_DIR = os.path.join(SCRIPT_DIR, "pdfs")
LISTPDF_DIR = os.path.join(SCRIPT_DIR, "pdfs")
PRINT_TICKET_SCRIPT = os.path.join(SCRIPT_DIR, "print_ticket.py")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(LISTPDF_DIR, exist_ok=True)

print(f"[INFO] Upload directory: {UPLOAD_DIR}")
print(f"[INFO] PDF directory: {PDF_DIR}")

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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_document.pdf"

def extract_date_from_filename(filename):
    try:
        parts = filename.split('_')
        if len(parts) >= 1:
            return parts[0]
    except:
        pass
    return datetime.now().strftime("%Y%m%d")

def get_listpdfs_filename(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    return f"{date_str}_listpdfs.txt"

def get_next_stt(listpdfs_path):
    if not os.path.exists(listpdfs_path):
        return 1
    max_stt = 0
    try:
        with open(listpdfs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith('STT') or line.startswith('-') or '|' not in line:
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
    try:
        os.makedirs(os.path.dirname(listpdfs_path), exist_ok=True)
        stt = get_next_stt(listpdfs_path)
        lines = []
        file_exists = os.path.exists(listpdfs_path)
        if file_exists:
            with open(listpdfs_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        if not file_exists or not lines:
            lines.append("STT   | Ten File                              | ServiceId | ServiceName\n")
            lines.append("-" * 70 + "\n")
        service_info = f" | {serviceId} | {serviceName}" if serviceId else ""
        lines.append(f"{stt:04d}| {pdf_filename}{service_info}\n")
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
                if not line or line.startswith("STT") or line.startswith("-") or "|" not in line:
                    continue
                parts = line.split("|")
                stt_str = parts[0].strip()
                try:
                    stt = int(stt_str)
                except Exception:
                    continue
                filename = parts[1].strip() if len(parts) > 1 else None
                service_id = None
                if len(parts) > 2:
                    sid_str = parts[2].strip()
                    try:
                        service_id = int(sid_str)
                    except ValueError:
                        pass
                service_name = None
                if len(parts) > 3:
                    service_name = parts[3].strip()
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
    api_url = "http://192.168.100.238/QueueSystemAdmin/api/ticket/create"
    try:
        formatted_stt = f"{stt:04d}"
        file_pdf_value = " " if ticket_only else pdf_filename
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
        return response.status_code in [200, 201]
    except requests.exceptions.RequestException as e:
        print(f"[API] Error sending ticket to QueueSystem: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_print_ticket(stt: int, dt: Optional[datetime], service_name: str = "HỘ TỊCH - CHỨNG THỰC"):
    if not PRINT_AVAILABLE:
        print("[PRINT] Skipping print - print_ticket module not available")
        return
    try:
        print(f"[PRINT] Calling print function with STT={stt}, serviceName={service_name}")
        print_ticket.print_ticket(stt, dt, service_name)
        print(f"[PRINT] Print job completed successfully")
    except Exception as e:
        print(f"[PRINT] Exception: {e}")
        import traceback
        traceback.print_exc()

def get_or_create_listpdfs(pdf_filename):
    pdf_date = extract_date_from_filename(pdf_filename)
    listpdfs_filename = get_listpdfs_filename(pdf_date)
    listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)
    return listpdfs_path

def convert_image_to_pdf(image_path, output_path):
    try:
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img_width, img_height = img.size
        c = canvas.Canvas(output_path, pagesize=(img_width, img_height))
        temp_jpg = io.BytesIO()
        img.save(temp_jpg, format='JPEG', quality=98, optimize=True)
        temp_jpg.seek(0)
        img_reader = ImageReader(temp_jpg)
        c.drawImage(img_reader, 0, 0, width=img_width, height=img_height, preserveAspectRatio=False)
        c.save()
        return True
    except Exception as e:
        print(f"Error converting image to PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_pdf_from_images(image_paths, output_path, enable_rotation=False, enable_bg_removal=False):
    import time
    start_time = time.time()
    print(f"\n[PDF] Starting PDF creation with {len(image_paths)} image(s)...")
    try:
        img_processor = get_image_processor()
        step_start = time.time()
        pil_images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                pil_images.append(img)
            except Exception as e:
                print(f"[PDF] Warning: Could not open image {path}: {e}")
        if not pil_images:
            print("[PDF] Error: No valid images to process")
            return False
        print(f"[PDF] Step 1 - Opened {len(pil_images)} images in {time.time() - step_start:.3f}s")
        step_start = time.time()
        processed_images = img_processor.process_scanned_images_batch_with_crop(
            pil_images,
            mode="color",
            force_full=False,
            enable_rotation=enable_rotation,
            enable_bg_removal=enable_bg_removal,
            contour_method='canny'
        )
        print(f"[PDF] Step 2 - Batch processed images in {time.time() - step_start:.3f}s")
        # Verify
        if len(processed_images) != len(pil_images):
            print(f"[PDF] Warning: Expected {len(pil_images)} images, got {len(processed_images)}")
            for i in range(len(pil_images)):
                if i >= len(processed_images) or processed_images[i] is None:
                    processed_images.append(pil_images[i])
        processed_first = processed_images[0]
        if processed_first.mode != 'RGB':
            processed_first = processed_first.convert('RGB')
        pdf_width, pdf_height = processed_first.size
        c = canvas.Canvas(output_path, pagesize=(pdf_width, pdf_height))
        step_start = time.time()
        for idx, processed_img in enumerate(processed_images):
            if processed_img.mode != 'RGB':
                processed_img = processed_img.convert('RGB')
            img_width, img_height = processed_img.size
            temp_jpg = io.BytesIO()
            processed_img.save(temp_jpg, format='JPEG', quality=98, optimize=True)
            temp_jpg.seek(0)
            img_reader = ImageReader(temp_jpg)
            c.drawImage(img_reader, 0, 0, width=img_width, height=img_height, preserveAspectRatio=False)
            if idx < len(processed_images) - 1:
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
    return {"message": "Webcam Scan Document API is running"}

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        image_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png']:
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JPG, JPEG, PNG")
        filename = f"{image_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        uploaded_images[image_id] = {
            "id": image_id,
            "filename": filename,
            "path": file_path,
            "original_name": file.filename,
            "timestamp": datetime.now().isoformat()
        }
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
    try:
        if not request.ids:
            raise HTTPException(status_code=400, detail="Không có ID nào được cung cấp")
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
        pdf_filename = generate_pdf_filename()
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        # Mặc định bật rotation và background removal có thể được cấu hình qua request sau này
        success = create_pdf_from_images(image_paths, pdf_path, enable_rotation=True, enable_bg_removal=True)
        if not success:
            raise HTTPException(status_code=500, detail="Lỗi khi tạo PDF")
        print(f"PDF created: {pdf_path}")
        listpdfs_path = get_or_create_listpdfs(pdf_filename)
        latest_stt = log_pdf_to_list(pdf_filename, listpdfs_path, request.serviceId, request.serviceName)
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
    try:
        current_date = datetime.now().strftime("%Y%m%d")
        listpdfs_filename = f"{current_date}_listpdfs.txt"
        listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)
        if not os.path.exists(listpdfs_path):
            raise HTTPException(status_code=404, detail="Không có ticket nào trong ngày hôm nay")
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
    try:
        print(f"[PRINT API] Received print request: stt={request.stt}, serviceName={request.serviceName}")
        dt = None
        if request.filename:
            dt = parse_datetime_from_pdf_filename(request.filename)
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
    return {
        "count": len(uploaded_images),
        "images": list(uploaded_images.values())
    }

@app.delete("/api/clear")
async def clear_images():
    try:
        for img_id, img_data in uploaded_images.items():
            if os.path.exists(img_data["path"]):
                os.remove(img_data["path"])
        uploaded_images.clear()
        return {"message": "Đã xóa tất cả ảnh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa: {str(e)}")

@app.post("/api/ticket")
async def create_ticket(request: TicketRequest, background_tasks: BackgroundTasks):
    try:
        pdf_filename = generate_pdf_filename()
        current_date = datetime.now().strftime("%Y%m%d")
        listpdfs_filename = get_listpdfs_filename(current_date)
        listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)
        latest_stt = log_pdf_to_list(pdf_filename, listpdfs_path, request.serviceId, request.serviceName)
        if latest_stt is None:
            raise HTTPException(status_code=500, detail="Không thể tạo số thứ tự")
        success = send_ticket_to_api(latest_stt, serviceId=request.serviceId, pdf_filename=pdf_filename, ticket_only=True)
        if not success:
            print(f"[WARNING] Failed to send ticket to QueueSystem")
        dt = parse_datetime_from_pdf_filename(pdf_filename)
        run_print_ticket(latest_stt, dt, request.serviceName or "HỘ TỊCH - CHỨNG THỰC")
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
    if getattr(sys, 'frozen', False):
        print("[INFO] Running as EXE - Auto-starting server...")
        print("[INFO] Press Ctrl+C to stop the server")
        print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=5000)