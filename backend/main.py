"""
Backend FastAPI cho Webcam Scan Document
Chức năng:
- Nhận ảnh từ frontend
- Chuyển đổi ảnh thành PDF
- Lưu PDF với format STT_DATETIME
- Export PDF về frontend

Các model xử lý ảnh (YOLO, rembg, pytesseract, ppocr-lite) được nạp sẵn ngay khi server start.
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
import requests
from print_ticket import print_ticket
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import numpy as np
import cv2

# Import configuration
from config import QUEUE_SYSTEM_API, SERVER_HOST, SERVER_PORT, UPLOAD_DIR, PDF_DIR

# Determine script directory early (used below for STAGING_DIR)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] Running from EXE: {SCRIPT_DIR}")
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"[INFO] Running from Python script: {SCRIPT_DIR}")

# ==================== Train Worker Trigger ====================
STAGING_DIR = os.path.join(SCRIPT_DIR, "train_staging")
os.makedirs(STAGING_DIR, exist_ok=True)

def _stage_image_for_training(image_path: str):
    """Copy ảnh mới upload sang staging dir để train worker xử lý."""
    import shutil
    try:
        basename = os.path.basename(image_path)
        dst = os.path.join(STAGING_DIR, basename)
        # Tránh copy trùng
        if os.path.abspath(image_path) != os.path.abspath(dst):
            shutil.copy2(image_path, dst)
            print(f"[TRAIN-STAGE] Staged {basename} for training")
    except Exception as e:
        print(f"[TRAIN-STAGE] Failed to stage {image_path}: {e}")

# ========== TẢI NGAY MODULE XỬ LÝ ẢNH ==========
# Thay vì lazy import, import trực tiếp để các model YOLO, rembg, ... được load ngay
try:
    import image_processor
    print("[INFO] image_processor loaded successfully")
except ImportError as e:
    print(f"[ERROR] Could not import image_processor: {e}")
    raise SystemExit("Missing image_processor module. Exiting.")

# Import print_ticket module (sẽ được đóng gói cùng EXE)
try:
    import print_ticket as print_ticket_module   # đã import ở trên nhưng để rõ ràng
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

# Mount static files
app.mount("/static", StaticFiles(directory=SCRIPT_DIR), name="static")

# Sử dụng thư mục từ config
UPLOAD_DIR_ABS = os.path.join(SCRIPT_DIR, UPLOAD_DIR)
PDF_DIR_ABS = os.path.join(SCRIPT_DIR, PDF_DIR)
LISTPDF_DIR = os.path.join(SCRIPT_DIR, PDF_DIR)  # Cùng thư mục PDF
PRINT_TICKET_SCRIPT = os.path.join(SCRIPT_DIR, "print_ticket.py")

os.makedirs(UPLOAD_DIR_ABS, exist_ok=True)
os.makedirs(PDF_DIR_ABS, exist_ok=True)
os.makedirs(LISTPDF_DIR, exist_ok=True)

print(f"[INFO] Upload directory: {UPLOAD_DIR_ABS}")
print(f"[INFO] PDF directory: {PDF_DIR_ABS}")
print(f"[INFO] Queue System API: {QUEUE_SYSTEM_API}")

# Lưu trữ các ảnh đã upload (tạm thời)
uploaded_images = {}

# ========== SỰ KIỆN STARTUP – PRELOAD MODELS ==========
@app.on_event("startup")
async def preload_models():
    """
    Chạy pipeline xử lý ảnh với một ảnh dummy nhỏ để ép tất cả các model
    (YOLO, rembg, pytesseract, ppocr-lite) tải vào RAM ngay từ đầu.
    """
    try:
        # Tạo ảnh dummy 100x100 pixel màu trắng
        dummy_pil = Image.new('RGB', (100, 100), color=(255, 255, 255))
        dummy_cv = cv2.cvtColor(np.array(dummy_pil), cv2.COLOR_RGB2BGR)

        _ = image_processor.process_single_image(
            dummy_cv,
            mode="color",
            force_full=False,
            enable_rotation=True,       # bắt buộc load Tesseract
            enable_bg_removal=True,     # bắt buộc load rembg
            contour_method='canny',
            preprocess='clahe'
        )
        print("[STARTUP] ✅ All image processing models preloaded successfully.")
    except Exception as e:
        print(f"[STARTUP] ⚠️ Model preload warning (non-critical): {e}")

# ========== Models ==========
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

# ========== STT Prefix Mapping ==========
# Mỗi serviceId có dải STT riêng theo yêu cầu từ service.txt
# serviceId → prefix (STT = prefix*1000 + số thứ tự)
SERVICE_STT_PREFIX = {
    99: 1,   # 1001, 1002, 1003...
    2: 2,    # 2001, 2002, 2003...
    3: 3,    # 3001, 3002, 3003...
    4: 4,    # 4001, 4002, 4003...
    5: 5,    # 5001, 5002, 5003...
}

def get_service_stt_prefix(service_id: Optional[int]) -> int:
    """Lấy STT prefix cho serviceId. Trả về 0 nếu không có mapping."""
    if service_id is None:
        return 0
    return SERVICE_STT_PREFIX.get(service_id, 0)

def get_initial_stt_for_service(service_id: Optional[int]) -> int:
    """Lấy STT khởi đầu cho serviceId.
    Ví dụ: serviceId=2 → prefix=2 → STT=2001
    Nếu không có mapping → STT=1
    """
    prefix = get_service_stt_prefix(service_id)
    if prefix > 0:
        return prefix * 1000 + 1
    return 1

# ========== Helper Functions ==========
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

def get_next_stt(listpdfs_path, service_id: Optional[int] = None):
    """
    Lấy STT tiếp theo dựa trên serviceId.
    - Nếu serviceId có prefix (vd: 2 → 2xxx), chỉ đếm trong dải đó.
    - Nếu không có prefix, dùng STT tăng dần bắt đầu từ 1.
    """
    prefix = get_service_stt_prefix(service_id)
    initial_stt = get_initial_stt_for_service(service_id)

    if not os.path.exists(listpdfs_path):
        return initial_stt

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
                    # Nếu có prefix, chỉ xét STT trong dải của service đó
                    if prefix > 0:
                        if stt // 1000 == prefix:
                            if stt > max_stt:
                                max_stt = stt
                    else:
                        if stt > max_stt:
                            max_stt = stt
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error reading listpdfs.txt: {e}")
        return initial_stt

    if max_stt == 0:
        return initial_stt
    return max_stt + 1

def log_pdf_to_list(pdf_filename, listpdfs_path, serviceId=None, serviceName=None):
    try:
        os.makedirs(os.path.dirname(listpdfs_path), exist_ok=True)
        stt = get_next_stt(listpdfs_path, service_id=serviceId)
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
    api_url = QUEUE_SYSTEM_API
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

def cleanup_uploads_and_pdfs():
    """Xóa toàn bộ ảnh trong uploads/ và file PDF trong pdfs/ sau khi in xong.
    File *_listpdfs.txt được giữ lại để không mất lịch sử số thứ tự."""
    import glob
    cleaned = 0
    # Xóa ảnh uploads
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff"):
        for f in glob.glob(os.path.join(UPLOAD_DIR_ABS, ext)):
            try:
                os.remove(f)
                cleaned += 1
            except Exception as e:
                print(f"[CLEANUP] Failed to delete {f}: {e}")
    # Xóa PDF (giữ nguyên file *_listpdfs.txt)
    for ext in ("*.pdf",):
        for f in glob.glob(os.path.join(PDF_DIR_ABS, ext)):
            try:
                os.remove(f)
                cleaned += 1
            except Exception as e:
                print(f"[CLEANUP] Failed to delete {f}: {e}")
    print(f"[CLEANUP] Đã xóa {cleaned} file trong uploads/ và pdfs/ (giữ nguyên *_listpdfs.txt)")


def run_print_ticket(stt: int, dt: Optional[datetime], service_name: str = "HỘ TỊCH - CHỨNG THỰC"):
    if not PRINT_AVAILABLE:
        print("[PRINT] Skipping print - print_ticket module not available")
        return
    try:
        print(f"[PRINT] Calling print function with STT={stt}, serviceName={service_name}")
        print_ticket(stt, dt, service_name)
        print(f"[PRINT] Print job completed successfully")
        # --- Tự động xóa ảnh và PDF sau khi in xong ---
        cleanup_uploads_and_pdfs()
    except Exception as e:
        print(f"[PRINT] Exception: {e}")
        import traceback
        traceback.print_exc()
        # Vẫn xóa dù in lỗi
        cleanup_uploads_and_pdfs()

def get_or_create_listpdfs(pdf_filename):
    pdf_date = extract_date_from_filename(pdf_filename)
    listpdfs_filename = get_listpdfs_filename(pdf_date)
    listpdfs_path = os.path.join(LISTPDF_DIR, listpdfs_filename)
    return listpdfs_path

def create_pdf_from_images(image_paths, output_path, enable_rotation=False, enable_bg_removal=False):
    import time
    start_time = time.time()
    print(f"\n[PDF] Starting PDF creation with {len(image_paths)} image(s)...")
    try:
        # Sử dụng trực tiếp module image_processor đã import
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
        processed_images = image_processor.process_scanned_images_batch_with_crop(
            pil_images,
            mode="color",
            force_full=False,
            enable_rotation=enable_rotation,
            enable_bg_removal=enable_bg_removal,
            contour_method='canny'
        )
        print(f"[PDF] Step 2 - Batch processed images in {time.time() - step_start:.3f}s")

        # Đảm bảo không có ảnh nào None
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

# ========== API Endpoints ==========
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
        file_path = os.path.join(UPLOAD_DIR_ABS, filename)
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
        # --- Copy ảnh sang staging để train worker xử lý ---
        _stage_image_for_training(file_path)
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
        pdf_path = os.path.join(PDF_DIR_ABS, pdf_filename)

        # Mặc định bật rotation và background removal (có thể cấu hình sau)
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
    print(f"[INFO] Upload directory: {os.path.abspath(UPLOAD_DIR_ABS)}")
    print(f"[INFO] PDF directory: {os.path.abspath(PDF_DIR_ABS)}")
    print(f"[INFO] Print available: {PRINT_AVAILABLE}")
    print("=" * 60)
    if getattr(sys, 'frozen', False):
        print("[INFO] Running as EXE - Auto-starting server...")
        print("[INFO] Press Ctrl+C to stop the server")
        print("=" * 60)
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)