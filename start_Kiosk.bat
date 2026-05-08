@echo off
REM ============================================
REM KIOSK SCAN SYSTEM - AUTO START
REM ============================================
REM Chạy Backend (main.py) + Frontend (start-frontend.bat)
REM Được launch bởi start_Kiosk.vbs (ẩn cửa sổ).
REM ============================================

REM Set working directory to script location (luôn đúng dù gọi từ đâu)
cd /d "%~dp0"

REM --- BACKEND SETUP ---
set "BACKEND_DIR=backend"
set "MAIN_PY=backend\main.py"

REM Check if main.py exists
if not exist "%MAIN_PY%" (
    echo ❌ main.py not found at %MAIN_PY%!
    echo Please ensure backend files are in place.
    timeout /t 5 /nobreak > nul
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.10+.
    timeout /t 5 /nobreak > nul
    exit /b 1
)

REM Create required directories
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\pdfs" mkdir backend\pdfs
if not exist "backend\train_staging" mkdir backend\train_staging
if not exist "backend\train_dataset" mkdir backend\train_dataset

echo [KIOSK] Starting Backend (main.py) on port 5000...

REM Start backend (main.py) - hidden (dùng pythonw.exe để không hiện cửa sổ console)
start "" /B pythonw.exe "%~dp0%MAIN_PY%" > nul 2>&1

REM Wait for backend to initialize
timeout /t 5 /nobreak > nul

echo [KIOSK] Starting YOLO Training Worker...

REM Start YOLO training worker (chạy background, tự động train từ ảnh upload)
start "" /B pythonw.exe "%~dp0backend\train_worker.py" > nul 2>&1

echo [KIOSK] Starting Frontend on port 3000...

REM --- FRONTEND ---
if exist "start-frontend.bat" (
    call "start-frontend.bat"
) else (
    echo ❌ start-frontend.bat not found!
    timeout /t 5 /nobreak > nul
    exit /b 1
)

timeout /t 3 /nobreak > nul

REM Open browser to frontend
start "" "http://localhost:3000"

REM Keep script alive briefly to allow services to start, then exit silently
timeout /t 2 /nobreak > nul
exit