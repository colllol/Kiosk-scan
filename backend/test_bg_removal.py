import numpy as np
import cv2
from image_processor import process_single_image

# Create a test image: white background with a blue rectangle in the middle
# We'll make it 400x400, with a 200x100 blue rectangle at (100,150)
img = np.ones((400, 400, 3), dtype=np.uint8) * 255  # white background
# Draw a blue rectangle (BGR: 255,0,0)
cv2.rectangle(img, (100, 150), (300, 250), (255, 0, 0), thickness=-1)

print("Original image shape:", img.shape)
print("Original image dtype:", img.dtype)

# Process with background removal enabled
processed = process_single_image(
    img,
    mode="color",
    force_full=False,
    enable_rotation=False,
    enable_bg_removal=True,
    contour_method='canny'
)

print("Processed image shape:", processed.shape)
print("Processed image dtype:", processed.dtype)

# Save the original and processed images for inspection
cv2.imwrite("test_original.png", img)
cv2.imwrite("test_processed.png", processed)

print("Saved test_original.png and test_processed.png")
print("Check the processed image: the blue rectangle should be on a white background (if background removal worked).")