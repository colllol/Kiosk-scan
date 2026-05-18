@echo off
REM ============================================
REM KIOSK SCAN SYSTEM - FRONTEND
REM ============================================
REM Start frontend HTTP server on port 3000
REM Chạy ẩn (không hiện console) khi được gọi từ start_Kiosk.bat
REM ============================================

cd /d "%~dp0frontend"

REM Check if frontend directory exists
if not exist "index.html" (
    echo ❌ index.html not found in frontend directory!
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

echo [FRONTEND] Starting HTTP server on port 3000...

REM Start Python HTTP server hidden (no console window)
start "" /B pythonw.exe -m http.server 3000 --bind localhost > nul 2>&1

timeout /t 2 /nobreak > nul
echo [FRONTEND] Server started at http://localhost:3000
