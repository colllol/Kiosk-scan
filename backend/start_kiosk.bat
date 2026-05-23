@echo off
setlocal

title Kiosk Backend and Train Worker

set "BACKEND_DIR=%~dp0"
set "PYTHON_EXE=%BACKEND_DIR%venv\Scripts\python.exe"
set "PYTHONW_EXE=%BACKEND_DIR%venv\Scripts\pythonw.exe"

cd /d "%BACKEND_DIR%"

echo ========================================
echo   Kiosk Backend + Train Worker
echo ========================================
echo.

if not exist "main.py" (
    echo [ERROR] Missing main.py in %BACKEND_DIR%
    pause
    exit /b 1
)

if not exist "train_worker.py" (
    echo [ERROR] Missing train_worker.py in %BACKEND_DIR%
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
    set "PYTHONW_EXE=pythonw.exe"
)

if not exist "uploads" mkdir uploads
if not exist "pdfs" mkdir pdfs
if not exist "train_staging" mkdir train_staging
if not exist "train_dataset" mkdir train_dataset

echo [TRAIN] Starting worker in background...
start "Kiosk Train Worker" /min "%PYTHONW_EXE%" train_worker.py

echo [BACKEND] Starting API server on http://localhost:5000
echo [INFO] Press Ctrl+C to stop backend.
echo.
"%PYTHON_EXE%" main.py

echo.
echo [INFO] Backend stopped.
pause
