"""Benchmark: đo tốc độ OpenCV rotation trên ảnh lớn."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2
from image_processor import _detect_text_orientation_opencv

# Ảnh scan thật ~2500x3500
h, w = 3500, 2500
print(f"Tao anh test {w}x{h} pixels...")

img = np.ones((h, w, 3), dtype=np.uint8) * 255
for i, text in enumerate([
    "UBND HUYEN ...", "CONG HOA XA HOI CHU NGHIA VIET NAM",
    "DON DE NGHI CAP GIAY CHUNG THUC", "Kin gui: UBND xa ...",
    "Toi ten: NGUYEN VAN A", "CMND/CCCD: 123456789",
    "Dia chi: Thon 1, xa ..., huyen ..."
]):
    cv2.putText(img, text, (50, 100 + i*80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,0), 3)

img_90 = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
img_180 = cv2.rotate(img, cv2.ROTATE_180)

N = 5
print(f"Benchmark: {N} lan cho moi truong hop...\n")

for name, test_img in [("0° (dung huong)", img), ("90° CW", img_90), ("180°", img_180)]:
    times = []
    for _ in range(N):
        t0 = time.perf_counter()
        angle = _detect_text_orientation_opencv(test_img)
        dt = time.perf_counter() - t0
        times.append(dt)
    avg_ms = sum(times) / N * 1000
    print(f"  {name:20s} -> phat hien {angle:>3}° | {avg_ms:7.2f}ms (TB {N} lan)")

print(f"\n=> OpenCV rotation: ~{sum(times)/N*1000:.1f}ms cho anh {w}x{h}")
print("✅ Hoan toan khong can Tesseract engine!")