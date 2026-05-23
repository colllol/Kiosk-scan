@echo off
setlocal

title Kiosk Scan Frontend

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "PORT=3000"

if not exist "%FRONTEND_DIR%\index.html" (
    echo [ERROR] Missing frontend file: %FRONTEND_DIR%\index.html
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    exit /b 1
)

echo [FRONTEND] Starting HTTP server on http://localhost:%PORT%
echo [FRONTEND] Logs: %FRONTEND_DIR%\frontend-server.log

cd /d "%FRONTEND_DIR%"
start "Kiosk Frontend" /B python.exe -m http.server %PORT% --bind localhost > "%FRONTEND_DIR%\frontend-server.log" 2> "%FRONTEND_DIR%\frontend-server.err.log"

timeout /t 2 /nobreak >nul
exit /b 0
