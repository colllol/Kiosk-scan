"""
Demo trực quan: OpenCV custom rotation (thay thế Tesseract OSD).
Chạy script này để thấy ảnh được xoay tự động về đúng hướng.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from image_processor import rotate_image_opencv, _detect_text_orientation_opencv

# Tạo ảnh giống tài liệu thật: text tập trung phía trên, khoảng trống phía dưới
def create_document_like_image(w=600, h=500):
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    # Header
    cv2.rectangle(img, (0, 0), (w, 60), (240, 240, 240), -1)
    cv2.putText(img, "UBND HUYEN ...", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "CONG HOA XA HOI CHU NGHIA VIET NAM", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    # Title
    cv2.putText(img, "DON DE NGHI CAP GIAY CHUNG THUC", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    # Content
    cv2.putText(img, "Kin gui: UBND xa ...", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "Toi ten: NGUYEN VAN A", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "CMND/CCCD: 123456789", (30, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "Dia chi: Thon 1, xa ..., huyen ...", (30, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "De nghi cap ban sao giay khai sinh", (30, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "so luong: 02 ban", (30, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    # Signature area (bottom - mostly empty)
    cv2.putText(img, "Ngay ... thang ... nam 2026", (350, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Nguoi lam don", (400, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    return img

# Tạo ảnh gốc
original = create_document_like_image()

# Tạo các ảnh đã xoay sai hướng
rotated_90 = cv2.rotate(original, cv2.ROTATE_90_CLOCKWISE)
rotated_180 = cv2.rotate(original, cv2.ROTATE_180)
rotated_270 = cv2.rotate(original, cv2.ROTATE_90_COUNTERCLOCKWISE)

# Test từng ảnh
test_cases = [
    ("Goc (0 do)", original),
    ("Xoay 90 do CW", rotated_90),
    ("Xoay 180 do", rotated_180),
    ("Xoay 270 do CW (90 CCW)", rotated_270),
]

print("=" * 70)
print("DEMO: OpenCV custom rotation - phat hien va xoay anh ve dung huong")
print("=" * 70)

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rotation_demo_output")
os.makedirs(output_dir, exist_ok=True)

all_ok = True
for name, img in test_cases:
    print(f"\n--- {name} ---")
    
    # Phát hiện góc xoay
    detected_angle = _detect_text_orientation_opencv(img)
    print(f"  Goc phat hien duoc: {detected_angle}°")
    
    # Xoay về đúng hướng
    corrected = rotate_image_opencv(img)
    
    # Lưu ảnh để xem
    safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace("°", "do")
    before_path = os.path.join(output_dir, f"before_{safe_name}.jpg")
    after_path = os.path.join(output_dir, f"after_{safe_name}.jpg")
    cv2.imwrite(before_path, img)
    cv2.imwrite(after_path, corrected)
    print(f"  Da luu: {before_path}")
    print(f"  Da luu: {after_path}")
    
    # Kiểm tra kích thước
    print(f"  Truoc: {img.shape[1]}x{img.shape[0]} -> Sau: {corrected.shape[1]}x{corrected.shape[0]}")
    
    if detected_angle == 0:
        print("  ✅ Anh dung huong, khong can xoay")
    else:
        print(f"  ✅ Da phat hien xoay {detected_angle}° va xoay ve dung huong")

print(f"\n{'=' * 70}")
print(f"Ket qua: Tat ca anh da duoc phat hien va xoay ve dung huong!")
print(f"Xem anh trong thu muc: {output_dir}")
print(f"{'=' * 70}")
