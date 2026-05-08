@echo off
REM =====================================================
REM start_kiosk.bat — Khởi động Backend + Train Worker
REM 
REM Cách dùng:
REM   - Chạy trực tiếp: double-click file này
REM   - Chạy ngầm (ẩn console): dùng start_kiosk.vbs
REM
REM Luồng:
REM   1. Backend FastAPI (cổng 5000) — xử lý scan, PDF, print
REM   2. Train Worker — poll train_staging/, auto-label, incremental train
REM =====================================================

cd /d "%~dp0"

echo ============================================================
echo   Kiosk Scan — Starting Backend + Train Worker
echo ============================================================
echo.

REM --- Kiểm tra Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay Python. Cai dat Python 3.10+ truoc.
    pause
    exit /b 1
)

REM --- Kiểm tra thư mục cần thiết ---
if not exist "uploads" mkdir uploads
if not exist "pdfs" mkdir pdfs
if not exist "train_staging" mkdir train_staging
if not exist "train_dataset" mkdir train_dataset

echo [INFO] Starting Backend on port 5000...
echo [INFO] Starting Train Worker (background)...
echo.

REM --- Chạy Train Worker ở background ---
start "Kiosk-TrainWorker" /min pythonw.exe train_worker.py

REM --- Chạy Backend (foreground) ---
python main.py

echo.
echo [INFO] Backend stopped.
pause
