#!/usr/bin/env python3
"""
Build script for creating EXE with proper configuration handling
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

def check_dependencies():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
        return True
    except ImportError:
        print("❌ PyInstaller is not installed")
        print("   Install it with: pip install pyinstaller")
        return False

def prepare_build_directory():
    """Prepare build directory structure"""
    build_dir = Path("build_exe")
    
    # Clean previous build
    if build_dir.exists():
        print(f"⚠️  Removing previous build directory: {build_dir}")
        shutil.rmtree(build_dir)
    
    # Create build directory structure
    build_dir.mkdir(exist_ok=True)
    
    # Copy necessary files
    files_to_copy = [
        ("backend/main.py", "main.py"),
        ("backend/config.py", "config.py"),
        ("backend/image_processor.py", "image_processor.py"),
        ("backend/print_ticket.py", "print_ticket.py"),
        ("backend/requirements.txt", "requirements.txt"),
        ("config.json", "config.json"),
    ]
    
    for src, dst in files_to_copy:
        src_path = Path(src)
        if src_path.exists():
            shutil.copy2(src_path, build_dir / dst)
            print(f"✓ Copied {src} -> {build_dir/dst}")
        else:
            print(f"⚠️  Warning: {src} not found")
    
    # Create necessary directories
    (build_dir / "uploads").mkdir(exist_ok=True)
    (build_dir / "pdfs").mkdir(exist_ok=True)
    
    return build_dir

def create_spec_file(build_dir):
    """Create PyInstaller spec file"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['{build_dir / "main.py"}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{build_dir / "config.json"}', '.'),
        ('{build_dir / "requirements.txt"}', '.'),
    ],
    hiddenimports=[
        'image_processor',
        'print_ticket',
        'config',
        'ultralytics',
        'pytesseract',
        'rembg',
        'rembg.models',
        'onnxruntime',
        'cv2',
        'PIL',
        'numpy',
        'reportlab',
        'fastapi',
        'uvicorn',
        'pydantic',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kiosk_scan_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Optional: add icon file
)
'''
    
    spec_file = build_dir / "kiosk_scan_backend.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✓ Created spec file: {spec_file}")
    return spec_file

def build_exe(build_dir, spec_file):
    """Build EXE using PyInstaller"""
    print("\n🔨 Building EXE with PyInstaller...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onefile",
        "--name", "kiosk_scan_backend",
        "--add-data", f"{build_dir / 'config.json'};.",
        "--add-data", f"{build_dir / 'requirements.txt'};.",
        "--hidden-import", "image_processor",
        "--hidden-import", "print_ticket",
        "--hidden-import", "config",
        "--hidden-import", "ultralytics",
        "--hidden-import", "pytesseract",
        "--hidden-import", "rembg",
        "--hidden-import", "rembg.models",
        "--hidden-import", "onnxruntime",
        "--hidden-import", "cv2",
        "--hidden-import", "PIL",
        "--hidden-import", "numpy",
        "--hidden-import", "reportlab",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "pydantic",
        str(build_dir / "main.py")
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build completed successfully!")
        
        # Show output directory
        dist_dir = Path("dist")
        if dist_dir.exists():
            exe_files = list(dist_dir.glob("*.exe"))
            if exe_files:
                print(f"\n📦 EXE file created at: {exe_files[0].absolute()}")
                print(f"   Size: {exe_files[0].stat().st_size / 1024 / 1024:.2f} MB")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error code {e.returncode}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False

def create_deployment_package(build_dir):
    """Create a deployment package with EXE and configuration"""
    print("\n📦 Creating deployment package...")
    
    # Create deployment directory
    deploy_dir = Path("deployment")
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir(exist_ok=True)
    
    # Copy EXE
    dist_dir = Path("dist")
    exe_files = list(dist_dir.glob("*.exe"))
    if exe_files:
        shutil.copy2(exe_files[0], deploy_dir / "kiosk_scan_backend.exe")
        print(f"✓ Copied EXE to {deploy_dir / 'kiosk_scan_backend.exe'}")
    
    # Copy config.json
    shutil.copy2(build_dir / "config.json", deploy_dir / "config.json")
    print(f"✓ Copied config.json to {deploy_dir / 'config.json'}")
    
    # Create directories
    (deploy_dir / "uploads").mkdir(exist_ok=True)
    (deploy_dir / "pdfs").mkdir(exist_ok=True)
    
    # Create README
    readme_content = """# Kiosk Scan Backend Deployment

## Files
- `kiosk_scan_backend.exe`: Main application
- `config.json`: Configuration file
- `uploads/`: Directory for uploaded images
- `pdfs/`: Directory for generated PDFs

## Configuration
Edit `config.json` to change settings:
- `apiEndpoints.queueSystem`: Queue system API URL
- `backendSettings.host/port`: Server host and port
- Other settings as needed

## Running
1. Double-click `kiosk_scan_backend.exe`
2. Server starts on http://localhost:5000 (by default)
3. Access API at http://localhost:5000

## Notes
- First run may be slow as models download
- Check console for any errors
- Ensure firewall allows port 5000
"""
    
    with open(deploy_dir / "README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✓ Created README.txt")
    
    # Create batch file for easy start
    batch_content = """@echo off
echo Starting Kiosk Scan Backend...
echo.
echo Configuration: config.json
echo Server: http://localhost:5000
echo.
echo Press Ctrl+C to stop
echo.
kiosk_scan_backend.exe
pause
"""
    
    with open(deploy_dir / "start_server.bat", 'w', encoding='utf-8') as f:
        f.write(batch_content)
    
    print(f"✓ Created start_server.bat")
    
    # Create update config script
    update_script = """#!/usr/bin/env python3
import json
import os

print("Kiosk Scan Backend - Configuration Updater")
print("=" * 50)

config_file = "config.json"
if not os.path.exists(config_file):
    print(f"❌ {config_file} not found!")
    input("Press Enter to exit...")
    exit(1)

try:
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("Current configuration:")
    print(f"  • Queue System API: {config.get('apiEndpoints', {}).get('queueSystem', 'Not set')}")
    print(f"  • Backend Host: {config.get('backendSettings', {}).get('host', 'Not set')}")
    print(f"  • Backend Port: {config.get('backendSettings', {}).get('port', 'Not set')}")
    
    print("\\nTo update configuration:")
    print("  1. Edit config.json with a text editor")
    print("  2. Save the file")
    print("  3. Restart the backend server")
    
except Exception as e:
    print(f"❌ Error reading config.json: {e}")

input("\\nPress Enter to exit...")
"""
    
    with open(deploy_dir / "update_config.py", 'w', encoding='utf-8') as f:
        f.write(update_script)
    
    print(f"✓ Created update_config.py")
    
    print(f"\n✅ Deployment package created at: {deploy_dir.absolute()}")
    print(f"   Total size: {sum(f.stat().st_size for f in deploy_dir.rglob('*') if f.is_file()) / 1024 / 1024:.2f} MB")

def main():
    print("🚀 Kiosk Scan Backend EXE Builder")
    print("=" * 50)
    
    if not check_dependencies():
        return
    
    # Step 1: Prepare build directory
    print("\n📁 Preparing build directory...")
    build_dir = prepare_build_directory()
    
    # Step 2: Build EXE
    print("\n🔨 Building EXE...")
    if not build_exe(build_dir, None):  # We'll use command line instead of spec file
        return
    
    # Step 3: Create deployment package
    create_deployment_package(build_dir)
    
    print("\n✅ Build process completed!")
    print("\n📋 Next steps:")
    print("   1. Test the EXE in the deployment folder")
    print("   2. Update config.json if needed")
    print("   3. Distribute the deployment folder")

if __name__ == "__main__":
    main()