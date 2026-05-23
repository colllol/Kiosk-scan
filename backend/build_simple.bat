@echo off
setlocal

title Build Kiosk Backend EXE - Simple

cd /d "%~dp0"

echo ========================================
echo   Simple Backend Build
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] Missing main.py in %cd%
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "WebcamScan.spec" del /q "WebcamScan.spec"

echo [BUILD] Running PyInstaller...
python -m PyInstaller --onedir ^
  --name "WebcamScan" ^
  --add-data "..\config.json;." ^
  --hidden-import=image_processor ^
  --hidden-import=print_ticket ^
  --hidden-import=config ^
  --hidden-import=ultralytics ^
  --hidden-import=pytesseract ^
  --hidden-import=rembg ^
  --hidden-import=onnxruntime ^
  --hidden-import=cv2 ^
  --hidden-import=uvicorn ^
  --hidden-import=fastapi ^
  --hidden-import=pydantic ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [OK] Build complete: %cd%\dist\WebcamScan\WebcamScan.exe
pause
