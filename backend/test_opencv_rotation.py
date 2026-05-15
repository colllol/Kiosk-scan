"""Test OpenCV rotation replacement for Tesseract OSD."""
import sys
import os

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2
from image_processor import (
    process_single_image,
    rotate_image_opencv,
    _detect_text_orientation_opencv,
)

print("=" * 60)
print("TEST: OpenCV rotation (replacement for Tesseract OSD)")
print("=" * 60)

# Test 1: Basic rotation function
print("\n[Test 1] rotate_image_opencv basic call...")
dummy = np.zeros((200, 200, 3), dtype=np.uint8)
result = rotate_image_opencv(dummy)
assert result.shape == (200, 200, 3), f"Shape mismatch: {result.shape}"
print("  PASS")

# Test 2: Orientation detection on blank image
print("\n[Test 2] Orientation detection on blank image...")
angle = _detect_text_orientation_opencv(dummy)
print(f"  Detected angle: {angle}")
assert angle == 0, f"Expected 0, got {angle}"
print("  PASS")

# Test 3: Orientation detection on image with horizontal text
print("\n[Test 3] Orientation detection on horizontal text...")
img = np.ones((400, 600, 3), dtype=np.uint8) * 255
cv2.putText(img, "Hello World This Is A Test Document", (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.putText(img, "Second Line Of Text Here For Testing", (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.putText(img, "Third Line At The Bottom Of Document", (30, 220),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
angle = _detect_text_orientation_opencv(img)
print(f"  Detected angle: {angle}")
assert angle == 0, f"Expected 0, got {angle}"
print("  PASS")

# Test 4: Orientation detection on 90-degree rotated text
print("\n[Test 4] Orientation detection on 90 CW rotated text...")
rotated_90 = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
angle = _detect_text_orientation_opencv(rotated_90)
print(f"  Detected angle: {angle}")
assert angle == 270, f"Expected 270, got {angle}"
print("  PASS")

# Test 5: Orientation detection on 180-degree rotated text
print("\n[Test 5] Orientation detection on 180 rotated text...")
rotated_180 = cv2.rotate(img, cv2.ROTATE_180)
angle = _detect_text_orientation_opencv(rotated_180)
print(f"  Detected angle: {angle}")
assert angle == 180, f"Expected 180, got {angle}"
print("  PASS")

# Test 6: Full pipeline with enable_rotation=True
print("\n[Test 6] Full pipeline with enable_rotation=True...")
result = process_single_image(img, mode="color", enable_rotation=True, force_full=True)
print(f"  Result shape: {result.shape}")
assert result is not None
print("  PASS")

# Test 7: Full pipeline with rotated input
print("\n[Test 7] Full pipeline with 90 CW rotated input...")
result = process_single_image(rotated_90, mode="color", enable_rotation=True, force_full=True)
print(f"  Result shape: {result.shape}")
assert result is not None
print("  PASS")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)
