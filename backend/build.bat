@echo off
setlocal

title Build Kiosk Backend EXE

set "BACKEND_DIR=%~dp0"
set "ROOT_DIR=%BACKEND_DIR%.."
set "APP_NAME=WebcamScan"
set "CONFIG_FILE=%BACKEND_DIR%config.json"

cd /d "%BACKEND_DIR%"

echo ========================================
echo   Build Backend EXE
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] Missing main.py in %BACKEND_DIR%
    pause
    exit /b 1
)

if exist "%ROOT_DIR%\config.json" (
    copy /Y "%ROOT_DIR%\config.json" "%CONFIG_FILE%" >nul
) else if not exist "%CONFIG_FILE%" (
    echo [ERROR] Missing config.json in project root.
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

echo [CLEAN] Removing previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"

echo [BUILD] Running PyInstaller...
python -m PyInstaller --onedir ^
  --clean ^
  --name "%APP_NAME%" ^
  --optimize=1 ^
  --noconfirm ^
  --noupx ^
  --collect-all numpy ^
  --collect-all PIL ^
  --collect-all escpos ^
  --collect-all reportlab ^
  --add-data "config.json;." ^
  --add-data "print_ticket.py;." ^
  --add-data "image_processor.py;." ^
  --hidden-import=cv2 ^
  --hidden-import=uvicorn ^
  --hidden-import=fastapi ^
  --hidden-import=uvicorn.logging ^
  --hidden-import=uvicorn.loops ^
  --hidden-import=uvicorn.protocols ^
  --hidden-import=fastapi.staticfiles ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageDraw ^
  --hidden-import=PIL.ImageFont ^
  --hidden-import=escpos.printer ^
  --hidden-import=reportlab.pdfgen ^
  --hidden-import=reportlab.lib.pagesizes ^
  --hidden-import=reportlab.lib.units ^
  --hidden-import=reportlab.lib.utils ^
  --hidden-import=print_ticket ^
  --hidden-import=image_processor ^
  --hidden-import=config ^
  --hidden-import=ultralytics ^
  --hidden-import=pytesseract ^
  --hidden-import=rembg ^
  --hidden-import=rembg.models ^
  --hidden-import=onnxruntime ^
  --hidden-import=pydantic ^
  --hidden-import=multipart ^
  --hidden-import=typing_extensions ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    echo [ERROR] Build finished but EXE was not found.
    pause
    exit /b 1
)

echo [PACKAGE] Creating deployment folder...
if exist "deployment" rmdir /s /q "deployment"
mkdir "deployment"
xcopy "dist\%APP_NAME%\*" "deployment\" /E /I /H /Y >nul
if exist "%ROOT_DIR%\config.json" copy /Y "%ROOT_DIR%\config.json" "deployment\config.json" >nul

echo.
echo [OK] Build complete.
echo [OK] EXE: %BACKEND_DIR%deployment\%APP_NAME%.exe
pause
