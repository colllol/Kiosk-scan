@echo off
setlocal

title Kiosk Scan Backend

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

echo ========================================
echo   Kiosk Scan - Backend
echo ========================================
echo.

if not exist "%BACKEND_DIR%\main.py" (
    echo [ERROR] Missing backend file: %BACKEND_DIR%\main.py
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Missing venv Python: %PYTHON_EXE%
    pause
    exit /b 1
)

if exist "%BACKEND_DIR%\requirements.txt" (
    echo [SETUP] Installing backend dependencies...
    "%PYTHON_EXE%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
) else (
    echo [WARN] requirements.txt not found. Starting with current environment.
)

if not exist "%BACKEND_DIR%\uploads" mkdir "%BACKEND_DIR%\uploads"
if not exist "%BACKEND_DIR%\pdfs" mkdir "%BACKEND_DIR%\pdfs"

echo.
echo [START] Backend API: http://localhost:5000
echo [START] API docs:    http://localhost:5000/docs
echo [INFO] Press Ctrl+C to stop.
echo.

cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" main.py

echo.
echo [INFO] Backend stopped.
pause
