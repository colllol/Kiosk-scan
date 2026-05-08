#!/usr/bin/env python3
"""Test config in EXE mode"""

import sys
import os

# Simulate EXE mode
sys.frozen = True
sys.executable = os.path.join(os.path.dirname(__file__), "test.exe")

print(f"Simulating EXE mode:")
print(f"  frozen: {getattr(sys, 'frozen', False)}")
print(f"  executable: {sys.executable}")

# Import config
import config

print(f"\nConfig loaded successfully:")
print(f"  Queue API: {config.QUEUE_SYSTEM_API}")
print(f"  Host: {config.SERVER_HOST}")
print(f"  Port: {config.SERVER_PORT}")
print(f"  Upload Dir: {config.UPLOAD_DIR}")
print(f"  PDF Dir: {config.PDF_DIR}")

print(f"\nConfig paths that would be searched:")
for i, path in enumerate(config.get_config_paths(), 1):
    exists = "✓" if os.path.exists(path) else "✗"
    print(f"  {i}. {exists} {path}")