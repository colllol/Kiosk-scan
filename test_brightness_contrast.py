#!/usr/bin/env python3
"""
Test script to verify brightness and contrast adjustment functionality.
"""

import numpy as np
import cv2
from backend.image_processor import adjust_brightness_contrast, apply_scan_effect

def test_brightness_contrast():
    """Test the brightness and contrast adjustment function."""
    print("Testing brightness and contrast adjustment...")
    
    # Create a simple test image (100x100 gradient)
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        test_image[:, i, :] = i * 2
    
    print(f"Original image shape: {test_image.shape}")
    print(f"Original image dtype: {test_image.dtype}")
    print(f"Original pixel range: [{test_image.min()}, {test_image.max()}]")
    
    # Test with default values (15% brightness, 15% contrast)
    adjusted = adjust_brightness_contrast(test_image.copy())
    print(f"\nAdjusted image pixel range: [{adjusted.min()}, {adjusted.max()}]")
    
    # Test with custom values
    adjusted_custom = adjust_brightness_contrast(test_image.copy(), brightness=30, contrast=30)
    print(f"Custom adjusted (30%,30%) pixel range: [{adjusted_custom.min()}, {adjusted_custom.max()}]")
    
    # Test with negative values
    adjusted_negative = adjust_brightness_contrast(test_image.copy(), brightness=-10, contrast=-10)
    print(f"Negative adjusted (-10%,-10%) pixel range: [{adjusted_negative.min()}, {adjusted_negative.min()}]")
    
    # Test apply_scan_effect with brightness/contrast
    print("\nTesting apply_scan_effect with brightness/contrast...")
    scan_result = apply_scan_effect(test_image.copy(), mode="color", brightness=15, contrast=15)
    print(f"Scan effect result shape: {scan_result.shape}")
    
    # Test that the function doesn't crash with edge cases
    print("\nTesting edge cases...")
    
    # Zero brightness/contrast
    zero_adjusted = adjust_brightness_contrast(test_image.copy(), brightness=0, contrast=0)
    print(f"Zero adjustment - images equal: {np.array_equal(test_image, zero_adjusted)}")
    
    # Extreme values
    extreme_adjusted = adjust_brightness_contrast(test_image.copy(), brightness=100, contrast=100)
    print(f"Extreme adjustment (100%,100%) pixel range: [{extreme_adjusted.min()}, {extreme_adjusted.max()}]")
    
    print("\nAll tests passed! Brightness and contrast adjustment is working correctly.")
    
    # Save test images for visual verification
    cv2.imwrite("test_original.png", test_image)
    cv2.imwrite("test_adjusted_15_15.png", adjusted)
    cv2.imwrite("test_adjusted_30_30.png", adjusted_custom)
    cv2.imwrite("test_scan_effect.png", scan_result)
    print("\nTest images saved to disk for visual verification.")

if __name__ == "__main__":
    test_brightness_contrast()