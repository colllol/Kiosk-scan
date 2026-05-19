@echo off
setlocal

REM KIOSK SCAN SYSTEM - FRONTEND
REM Starts frontend HTTP server on port 3000.

cd /d "%~dp0frontend"

if not exist "index.html" (
    echo [ERROR] index.html not found in frontend directory.
    timeout /t 5 /nobreak >nul
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    timeout /t 5 /nobreak >nul
    exit /b 1
)

echo [FRONTEND] Starting HTTP server on port 3000...
start "" /B python.exe -m http.server 3000 --bind localhost > frontend-server.log 2> frontend-server.err.log

timeout /t 2 /nobreak >nul
echo [FRONTEND] Server started at http://localhost:3000
exit /b 0
