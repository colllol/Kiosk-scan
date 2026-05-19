@echo off
setlocal

REM KIOSK SCAN SYSTEM - AUTO START
REM Starts backend, training worker, and frontend server without opening a browser.

cd /d "%~dp0"

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_BAT=%ROOT_DIR%start-frontend.bat"
set "BACKEND_MAIN=%BACKEND_DIR%\main.py"
set "TRAIN_WORKER=%BACKEND_DIR%\train_worker.py"

echo [KIOSK] Starting kiosk services...

if not exist "%BACKEND_MAIN%" (
    echo [ERROR] Missing backend file: %BACKEND_MAIN%
    timeout /t 5 /nobreak >nul
    exit /b 1
)

if not exist "%TRAIN_WORKER%" (
    echo [ERROR] Missing train worker file: %TRAIN_WORKER%
    timeout /t 5 /nobreak >nul
    exit /b 1
)

if not exist "%FRONTEND_BAT%" (
    echo [ERROR] Missing frontend starter: %FRONTEND_BAT%
    timeout /t 5 /nobreak >nul
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    timeout /t 5 /nobreak >nul
    exit /b 1
)

if not exist "%BACKEND_DIR%\uploads" mkdir "%BACKEND_DIR%\uploads"
if not exist "%BACKEND_DIR%\pdfs" mkdir "%BACKEND_DIR%\pdfs"
if not exist "%BACKEND_DIR%\train_staging" mkdir "%BACKEND_DIR%\train_staging"
if not exist "%BACKEND_DIR%\train_dataset" mkdir "%BACKEND_DIR%\train_dataset"

echo [KIOSK] Starting backend on port 5000...
pushd "%BACKEND_DIR%"
start "Kiosk Backend" /B python.exe "%BACKEND_MAIN%"

timeout /t 5 /nobreak >nul

echo [KIOSK] Starting training worker...
start "Kiosk Train Worker" /B python.exe "%TRAIN_WORKER%"
popd

echo [KIOSK] Starting frontend on port 3000...
call "%FRONTEND_BAT%"
if errorlevel 1 (
    echo [ERROR] Frontend failed to start.
    timeout /t 5 /nobreak >nul
    exit /b 1
)

timeout /t 2 /nobreak >nul
exit /b 0
