from __future__ import annotations
from datetime import datetime
import os
import sys
import logging
from escpos.printer import Win32Raw
from PIL import Image, ImageDraw, ImageFont

# --- CẤU HÌNH LOGGING (QUAN TRỌNG) ---
# Hiển thị log chung, nhưng ẨN cảnh báo "media.width.pixel" từ escpos
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logging.getLogger('escpos').setLevel(logging.ERROR)
# -------------------------------------

# Làm sạch biến môi trường (LOẠI BỎ KHOẢNG TRẮNG THỪA)
PRINTER_NAME = os.environ.get("WEBSCAN_PRINTER_NAME", "EP802").strip()
CHARS_PER_LINE = int(os.environ.get("WEBSCAN_PRINTER_COLS", "42").strip())
PRINT_WIDTH_PX = int(os.environ.get("WEBSCAN_PRINTER_DOTS", "576").strip())
FONT_PATH = os.environ.get("WEBSCAN_TICKET_FONT",
                           r"C:\Windows\Fonts\arial.ttf").strip()
USE_RASTER = os.environ.get("WEBSCAN_TICKET_RASTER",
                            "1").strip() not in ("0", "false", "False")

logging.info(
    f"Printer: {PRINTER_NAME}, Width: {PRINT_WIDTH_PX}px, Raster: {USE_RASTER}")


def get_base_dir():
    """Get base directory - works for both EXE and Python script"""
    if getattr(sys, 'frozen', False):
        # Running from EXE - use executable directory
        base_dir = os.path.dirname(sys.executable)
        logging.info(f"[print_ticket] Running from EXE: {base_dir}")
    else:
        # Running from Python script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logging.info(f"[print_ticket] Running from Python: {base_dir}")

    return base_dir


def get_logo_path():
    """Get logo path - check multiple locations for EXE compatibility"""
    base_dir = get_base_dir()
    
    # Try paths in order:
    # 1. uploads/Logo.png relative to base dir
    logo_path = os.path.join(base_dir, "uploads", "Logo.png")
    logging.info(f"[print_ticket] Checking logo path: {logo_path}")
    
    if os.path.exists(logo_path):
        logging.info(f"[print_ticket] Logo found at: {logo_path}")
        return logo_path
    
    # 2. Try current working directory
    logo_path_cwd = os.path.join(os.getcwd(), "uploads", "Logo.png")
    logging.info(f"[print_ticket] Checking logo path (cwd): {logo_path_cwd}")
    
    if os.path.exists(logo_path_cwd):
        logging.info(f"[print_ticket] Logo found at (cwd): {logo_path_cwd}")
        return logo_path_cwd
    
    # 3. Try relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path_script = os.path.join(script_dir, "uploads", "Logo.png")
    logging.info(f"[print_ticket] Checking logo path (script): {logo_path_script}")
    
    if os.path.exists(logo_path_script):
        logging.info(f"[print_ticket] Logo found at (script): {logo_path_script}")
        return logo_path_script
    
    logging.warning(f"[print_ticket] Logo NOT found in any location")
    return None


def _two_cols(left: str, right: str, width: int) -> str:
    left = (left or "").strip()
    right = (right or "").strip()
    if not right:
        return left
    gap = max(1, width - len(left) - len(right))
    return f"{left}{' ' * gap}{right}"


def _load_font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT_PATH, size=size)
    except Exception:
        return ImageFont.load_default()


def _render_ticket_image(number: int, now: datetime, service_name: str = "HỘ TỊCH - CHỨNG THỰC") -> Image.Image:
    w = PRINT_WIDTH_PX
    pad = 16

    f_header1 = _load_font(26)
    f_header2 = _load_font(22)
    f_title = _load_font(34)
    f_number = _load_font(160)
    f_note = _load_font(22)
    f_footer = _load_font(20)

    # Use new get_logo_path() that checks multiple locations
    logo_path = get_logo_path()
    logo = None
    logo_w = 0
    header_block_h = 0
    header_lines_prose = [
        ("       UBND XÃ ABC", f_header1),
        ("BỘ PHẬN TIẾP NHẬN VÀ TRẢ KẾT QUẢ", f_header2),
    ]

    try:
        tmp_draw = ImageDraw.Draw(Image.new("L", (1, 1), 255))
        text_block_h = 0
        for text, font in header_lines_prose:
            bbox = tmp_draw.textbbox((0, 0), text, font=font)
            text_block_h += (bbox[3] - bbox[1]) + 10
        text_block_h -= 10

        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                logo_h = text_block_h
                ratio = logo_h / logo_img.height
                logo_w = int(logo_img.width * ratio)
                logo = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                logging.info(f"[print_ticket] Logo loaded successfully: {logo_w}x{logo_h}")
            except Exception as img_err:
                logging.error(f"[print_ticket] Error loading logo image: {img_err}")
                logo = None
        else:
            logging.warning(f"[print_ticket] Logo file does not exist at: {logo_path}")

        header_block_h = text_block_h
    except Exception as e:
        logging.warning(f"Could not load logo: {e}")
        logo = None

    lines = [
        (" ", f_footer),
        (service_name, f_title),
        (" ", f_footer),
        (f"{number:04d}", f_number),
        (" ", f_footer),
        (" ", f_footer),
        (" ", f_footer),
        ("Quý khách vui lòng chờ đến số thứ tự này. Cảm ơn!", f_note),
    ]

    tmp = Image.new("L", (w, 10), 255)
    dtmp = ImageDraw.Draw(tmp)
    y = pad

    if logo:
        y += header_block_h + 10
    else:
        lines = header_lines_prose + lines

    for text, font in lines:
        if not text:
            y += 14
            continue
        bbox = dtmp.textbbox((0, 0), text, font=font)
        y += (bbox[3] - bbox[1]) + 10

    footer_h = 36
    total_h = y + footer_h + pad

    img = Image.new("L", (w, total_h), 255)
    draw = ImageDraw.Draw(img)

    cy = pad
    if logo:
        mask = logo.convert("RGBA").split(
        )[-1] if logo.mode in ("RGBA", "LA") else None
        img.paste(logo, (pad, cy), mask)

        text_x = pad + logo_w + 10
        text_y = cy
        for text, font in header_lines_prose:
            draw.text((text_x, text_y), text, font=font, fill=0)
            bbox = dtmp.textbbox((0, 0), text, font=font)
            text_y += (bbox[3] - bbox[1]) + 10

        cy += header_block_h + 10

    for text, font in lines:
        if not text:
            cy += 14
            continue
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2
        draw.text((x, cy), text, font=font, fill=0)
        cy += th + 10

    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d/%m/%Y")
    left = f"Giờ In Phiếu: {time_str}"
    right = f"Ngày: {date_str}"

    fb = draw.textbbox((0, 0), left, font=f_footer)
    draw.text(
        (pad, total_h - pad - (fb[3] - fb[1]) - 2), left, font=f_footer, fill=0)

    rb = draw.textbbox((0, 0), right, font=f_footer)
    draw.text((w - pad - (rb[2] - rb[0]), total_h - pad -
              (rb[3] - rb[1]) - 2), right, font=f_footer, fill=0)

    return img.convert("1")


def print_ticket(number: int, dt: datetime | None = None, service_name: str = "HỘ TỊCH - CHỨNG THỰC"):
    now = dt or datetime.now()

    logging.info(f"Connecting to printer: '{PRINTER_NAME}'")

    try:
        p = Win32Raw(PRINTER_NAME)

        # QUAN TRỌNG: Gửi lệnh khởi tạo máy in (ESC @) để reset bộ đệm
        p._raw(b'\x1b\x40')

        if USE_RASTER:
            ticket_img = _render_ticket_image(number, now, service_name)
            logging.info(f"Image size: {ticket_img.size}")
            p.image(ticket_img)
            p.cut()
        else:
            p.set(align="center", bold=True)
            p.text("UBND XÃ HOÀI MỸ\n")
            p.set(align="center", bold=False)
            p.text("BỘ PHẬN TIẾP NHẬN VÀ TRẢ KẾT QUẢ\n\n")
            p.set(align="center", bold=True, width=2, height=2)
            p.text(f"{service_name}\n\n")
            p.set(align="center", bold=True, width=10, height=10)
            p.text(f"{number:04d}\n\n")
            p.set(align="center", bold=False, width=1, height=1)
            p.text("Quý khách vui lòng chờ đến số thứ tự này. Cảm ơn!\n\n")

            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%d/%m/%Y")
            footer = _two_cols(
                f"Giờ in phiếu: {time_str}", f"Ngày: {date_str}", CHARS_PER_LINE)
            p.set(align="left", bold=False)
            p.text(footer + "\n")
            p.cut()

        p.close()
        logging.info("Print job completed successfully")

    except Exception as e:
        logging.error(f"Print exception: {e}")
        raise

if __name__ == '__main__':
    stt = int(sys.argv[1]) if len(sys.argv) >= 2 else 123
    dt = None
    if len(sys.argv) >= 3 and sys.argv[2].strip():
        try:
            dt = datetime.strptime(sys.argv[2].strip(), "%d/%m/%Y %H:%M:%S")
        except Exception:
            dt = None
    print_ticket(stt, dt)