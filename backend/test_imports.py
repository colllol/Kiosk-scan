#!/usr/bin/env python3
"""Test imports and check for missing dependencies"""

import sys
import os

print("Testing imports...")

# Test ultralytics
try:
    from ultralytics import YOLO
    print("✓ ultralytics imported successfully")
    
    # Check for model files
    model_files = ["best.pt", "best-seg.pt"]
    for model_file in model_files:
        if os.path.exists(model_file):
            print(f"✓ Found {model_file}")
        else:
            print(f"✗ Missing {model_file}")
except ImportError as e:
    print(f"✗ ultralytics import failed: {e}")

# Test pytesseract
try:
    import pytesseract
    print("✓ pytesseract imported successfully")
    
    # Check if tesseract executable exists
    try:
        pytesseract.get_tesseract_version()
        print("✓ Tesseract OCR engine found")
    except Exception as e:
        print(f"✗ Tesseract OCR engine not found: {e}")
except ImportError as e:
    print(f"✗ pytesseract import failed: {e}")

# Test rembg
try:
    from rembg import remove
    print("✓ rembg imported successfully")
except ImportError as e:
    print(f"✗ rembg import failed: {e}")

# Test OpenCV
try:
    import cv2
    print(f"✓ OpenCV imported successfully (version {cv2.__version__})")
except ImportError as e:
    print(f"✗ OpenCV import failed: {e}")

print("\nSummary:")
print("-" * 40)
print("The system will work without Tesseract and YOLO models,")
print("but with reduced functionality (no auto-rotation, basic contour detection).")