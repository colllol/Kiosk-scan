"""Debug orientation detection."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from image_processor import _detect_text_orientation_opencv

# Tao anh giong test
img = np.ones((400, 600, 3), dtype=np.uint8) * 255
cv2.putText(img, 'Hello World This Is A Test Document', (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.putText(img, 'Second Line Of Text Here For Testing', (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.putText(img, 'Third Line At The Bottom Of Document', (30, 220),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

# Debug: check bounding box
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape
scale = min(500.0 / h, 500.0 / w, 1.0)
small = cv2.resize(gray, (int(w*scale), int(h*scale)))
sh, sw = small.shape
print(f"Original: {w}x{h}, Resized: {sw}x{sh}, scale={scale:.3f}")

_, binary = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
pixel_ratio = np.sum(binary > 0) / (sh * sw)
print(f"Text pixel ratio: {pixel_ratio:.4f}")

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"Total contours: {len(contours)}")

min_area = max(5, (sh * sw) * 0.0005)
valid = [c for c in contours if cv2.contourArea(c) > min_area]
print(f"Valid contours (>={min_area:.0f}px): {len(valid)}")

if valid:
    all_pts = np.vstack([c.reshape(-1, 2) for c in valid])
    x, y, bw, bh = cv2.boundingRect(all_pts)
    print(f"Bounding box: x={x}, y={y}, w={bw}, h={bh}, bw>=bh? {bw >= bh}")

angle = _detect_text_orientation_opencv(img)
print(f"Detected angle: {angle}")

# Now test rotated
img90 = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
gray90 = cv2.cvtColor(img90, cv2.COLOR_BGR2GRAY)
h90, w90 = gray90.shape
scale90 = min(500.0 / h90, 500.0 / w90, 1.0)
small90 = cv2.resize(gray90, (int(w90*scale90), int(h90*scale90)))
sh90, sw90 = small90.shape
print(f"\nRotated 90: Original {w90}x{h90}, Resized {sw90}x{sh90}")

_, binary90 = cv2.threshold(small90, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
cleaned90 = cv2.morphologyEx(binary90, cv2.MORPH_OPEN, kernel, iterations=1)
contours90, _ = cv2.findContours(cleaned90, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
valid90 = [c for c in contours90 if cv2.contourArea(c) > min_area]
print(f"Valid contours: {len(valid90)}")
if valid90:
    all_pts90 = np.vstack([c.reshape(-1, 2) for c in valid90])
    x90, y90, bw90, bh90 = cv2.boundingRect(all_pts90)
    print(f"Bounding box: x={x90}, y={y90}, w={bw90}, h={bh90}, bw>=bh? {bw90 >= bh90}")

angle90 = _detect_text_orientation_opencv(img90)
print(f"Detected angle: {angle90}")
