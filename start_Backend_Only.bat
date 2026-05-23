@echo off
setlocal

title Kiosk Scan Backend EXE

set "ROOT_DIR=%~dp0"
set "DEPLOY_DIR=%ROOT_DIR%backend\deployment"
set "BACKEND_EXE=%DEPLOY_DIR%\WebcamScan.exe"

echo ========================================
echo   Kiosk Scan - Backend EXE
echo ========================================
echo.

if not exist "%BACKEND_EXE%" (
    echo [ERROR] Backend EXE not found:
    echo %BACKEND_EXE%
    echo.
    echo Build it first with: backend\build.bat
    pause
    exit /b 1
)

if not exist "%DEPLOY_DIR%\config.json" (
    if exist "%ROOT_DIR%config.json" (
        echo [SETUP] Copying config.json to deployment...
        copy /Y "%ROOT_DIR%config.json" "%DEPLOY_DIR%\config.json" >nul
    ) else (
        echo [ERROR] Missing config.json in project root and deployment folder.
        pause
        exit /b 1
    )
)

if not exist "%DEPLOY_DIR%\uploads" mkdir "%DEPLOY_DIR%\uploads"
if not exist "%DEPLOY_DIR%\pdfs" mkdir "%DEPLOY_DIR%\pdfs"

echo [START] Backend API: http://localhost:5000
echo [INFO] Press Ctrl+C to stop.
echo.

cd /d "%DEPLOY_DIR%"
"%BACKEND_EXE%"

echo.
echo [INFO] Backend stopped.
pause
