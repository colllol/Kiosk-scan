@echo off
echo ============================================
echo KIOSK BACKEND - AUTO START
echo ============================================
echo.
echo This script will start the backend EXE only.
echo Frontend should be accessed separately.
echo.

REM Set working directory to script location
cd /d "%~dp0"
echo Working directory: %cd%
echo.

REM Check if backend EXE exists
if not exist "backend\deployment\WebcamScan.exe" (
    echo ❌ Backend EXE not found at backend\deployment\WebcamScan.exe!
    echo Please build the backend first.
    echo.
    pause
    exit /b 1
)

REM Check if config.json exists in backend EXE directory
if not exist "backend\deployment\config.json" (
    echo ⚠️  config.json not found in EXE directory
    echo Copying config.json from project root...
    if exist "config.json" (
        copy "config.json" "backend\deployment\config.json" > nul
        echo ✓ Copied config.json
    ) else (
        echo ❌ config.json not found in project root!
        pause
        exit /b 1
    )
)

echo ============================================
echo STARTING BACKEND SERVER...
echo ============================================
echo.

REM Create necessary directories
if not exist "backend\deployment\uploads" mkdir "backend\deployment\uploads"
if not exist "backend\deployment\pdfs" mkdir "backend\deployment\pdfs"
echo ✓ Created uploads and pdfs directories
echo.

REM Start backend EXE
echo Starting backend server on port 5000...
echo.
echo ============================================
echo BACKEND SERVER LOGS
echo ============================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run backend EXE in foreground (shows logs)
"backend\deployment\WebcamScan.exe"

echo.
echo ============================================
echo BACKEND SERVER STOPPED
echo ============================================
echo.
pause