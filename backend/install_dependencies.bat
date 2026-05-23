@echo off
setlocal

title Install Kiosk Backend Dependencies

cd /d "%~dp0"

echo ========================================
echo   Install Backend Dependencies
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

python --version
echo.

if not exist "requirements.txt" (
    echo [SETUP] Creating default requirements.txt...
    (
    echo fastapi
    echo uvicorn[standard]
    echo python-multipart
    echo Pillow
    echo reportlab
    echo numpy
    echo opencv-python
    echo requests
    echo python-escpos
    echo ultralytics
    echo pytesseract
    echo rembg[cpu]
    ) > requirements.txt
)

echo [SETUP] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARN] pip upgrade failed. Continuing with existing pip.
)

echo.
echo [SETUP] Installing PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo [SETUP] Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install one or more dependencies.
    pause
    exit /b 1
)

echo.
echo [CHECK] Verifying key packages...
python -c "import fastapi, cv2, ultralytics, rembg; print('OK')"
if errorlevel 1 (
    echo [WARN] Some packages could not be imported. Check the messages above.
) else (
    echo [OK] Key packages are available.
)

echo.
echo [OK] Dependency installation complete.
pause
