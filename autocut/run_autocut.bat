@echo off
setlocal

title AutoCut

set "APP_DIR=%~dp0"
set "URL=http://127.0.0.1:5173"

cd /d "%APP_DIR%"

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js before running AutoCut.
    pause
    exit /b 1
)

if not exist "package.json" (
    echo [ERROR] Missing package.json in %APP_DIR%
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [SETUP] Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo [START] AutoCut: %URL%
start "Open AutoCut" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"
call npm start

echo.
echo [INFO] AutoCut stopped.
pause
