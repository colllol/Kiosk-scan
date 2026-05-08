@echo off
chcp 65001 >nul
echo ========================================
echo  Webcam Scan Document - Backend
echo ========================================
echo.
echo  Đang khởi động FastAPI server...
echo.

cd backend

:: Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Không tìm thấy Python. Vui lòng cài đặt Python trước.
    pause
    exit /b 1
)

:: Kiểm tra và cài đặt dependencies
echo [1/2] Kiểm tra dependencies...
if not exist "venv" (
    echo [INFO] Tạo virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install requirements
pip install -r requirements.txt -q

:: Chạy server
echo [2/2] Khởi động server trên http://localhost:5000
echo.
echo ========================================
echo  Server đang chạy...
echo  API: http://localhost:5000/docs
echo  Press Ctrl+C để dừng
echo ========================================
echo.

python main.py

pause
