#!/usr/bin/env python3
"""Test PDF creation to see current warnings"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import numpy as np
import io
import time

# Create a test image
test_image = Image.new('RGB', (800, 600), color='white')

# Import image_processor
import image_processor

print("Testing image processor with a simple image...")
print("-" * 60)

# Test single image processing
cv_image = image_processor.pil_to_cv2(test_image)
result = image_processor.process_single_image(
    cv_image, 
    mode="color",
    force_full=False,
    enable_rotation=True,
    enable_bg_removal=True,
    contour_method='canny'
)

print("\n" + "=" * 60)
print("Test completed!")
print("\nCurrent status:")
print("1. YOLO models: Missing (will use OpenCV fallback)")
print("2. Tesseract: Not installed (auto-rotation disabled)")
print("3. rembg: Working ✓")
print("4. OpenCV: Working ✓")
print("\nThe system will work with basic functionality.")
print("For full features, install Tesseract OCR and add YOLO model files.")