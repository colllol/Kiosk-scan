@echo off
setlocal

title Kiosk Scan Services

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_BAT=%ROOT_DIR%start-frontend.bat"
set "BACKEND_MAIN=%BACKEND_DIR%\main.py"
set "TRAIN_WORKER=%BACKEND_DIR%\train_worker.py"
set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"

echo ========================================
echo   Kiosk Scan - Services
echo ========================================
echo.

if not exist "%BACKEND_MAIN%" (
    echo [ERROR] Missing backend file: %BACKEND_MAIN%
    pause
    exit /b 1
)

if not exist "%TRAIN_WORKER%" (
    echo [ERROR] Missing train worker file: %TRAIN_WORKER%
    pause
    exit /b 1
)

if not exist "%FRONTEND_BAT%" (
    echo [ERROR] Missing frontend starter: %FRONTEND_BAT%
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python.exe"
)

if not exist "%BACKEND_DIR%\uploads" mkdir "%BACKEND_DIR%\uploads"
if not exist "%BACKEND_DIR%\pdfs" mkdir "%BACKEND_DIR%\pdfs"
if not exist "%BACKEND_DIR%\train_staging" mkdir "%BACKEND_DIR%\train_staging"
if not exist "%BACKEND_DIR%\train_dataset" mkdir "%BACKEND_DIR%\train_dataset"

echo [BACKEND] Starting API server on port 5000...
start "Kiosk Backend" /D "%BACKEND_DIR%" /B "%PYTHON_EXE%" "%BACKEND_MAIN%" > "%ROOT_DIR%backend-live.out.log" 2> "%ROOT_DIR%backend-live.err.log"

timeout /t 5 /nobreak >nul

echo [TRAIN] Starting training worker...
start "Kiosk Train Worker" /D "%BACKEND_DIR%" /B "%PYTHON_EXE%" "%TRAIN_WORKER%" > "%ROOT_DIR%train-worker.out.log" 2> "%ROOT_DIR%train-worker.err.log"

echo [FRONTEND] Starting frontend on port 3000...
call "%FRONTEND_BAT%"
if errorlevel 1 (
    echo [ERROR] Frontend failed to start.
    pause
    exit /b 1
)

echo.
echo [OK] Services started.
echo [INFO] Frontend: http://localhost:3000
echo [INFO] Backend:  http://localhost:5000/docs
timeout /t 3 /nobreak >nul
exit /b 0
