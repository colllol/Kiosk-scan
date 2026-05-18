@echo off
setlocal
title Kiosk Scan GUI
cd /d "%~dp0"

echo ============================================
echo   Kiosk Scan GUI - GridFlux
echo ============================================
echo.

set "GRIDFLUX_DIR=%APPDATA%\GridFlux"
set "GRIDFLUX_CONFIG=%GRIDFLUX_DIR%\config.json"
set "GUI_EXE=%~dp0GUI\build\bin\gridflux.exe"

if not exist "%GRIDFLUX_DIR%" mkdir "%GRIDFLUX_DIR%"

echo [CONFIG] Writing GridFlux kiosk layout...
(
echo {
echo   "rows": 2,
echo   "cols": 1,
echo   "gap": 0,
echo   "border_width": 0,
echo   "row_weights": [3, 7, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
echo   "col_weights": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
echo   "enable_borders": false,
echo   "auto_tile": true,
echo   "follow_focus": true,
echo   "lock_grids": false,
echo   "auto_launch_tasks": true,
echo   "workspace_count": 1,
echo.
echo   "workspace_names": [
echo     "Kiosk"
echo   ],
echo.
echo   "startup_tasks": [
echo     "http://localhost:3000/index4.html",
echo     "http://localhost:3000/index2.html"
echo   ],
echo.
echo   "startup_task_f11": [
echo     true,
echo     true
echo   ],
echo.
echo   "window_rules": [
echo   ]
echo }
) > "%GRIDFLUX_CONFIG%"

echo [BACKEND] Starting API server on port 5000...
if exist "%~dp0backend\venv\Scripts\pythonw.exe" (
    start "" /D "%~dp0backend" "%~dp0backend\venv\Scripts\pythonw.exe" "%~dp0backend\main.py"
) else (
    start "" /D "%~dp0backend" pythonw.exe "%~dp0backend\main.py"
)

echo [FRONTEND] Starting HTTP server on port 3000...
start "" /D "%~dp0frontend" /B pythonw.exe -m http.server 3000 --bind localhost

timeout /t 2 /nobreak > nul

if not exist "%GUI_EXE%" (
    echo [BUILD] gridflux.exe not found. Building GUI...
    call "%~dp0GUI\build.bat"
)

if not exist "%GUI_EXE%" (
    echo.
    echo [ERROR] Khong tim thay GUI executable:
    echo %GUI_EXE%
    pause
    exit /b 1
)

echo [GUI] Starting GridFlux...
start "" "%GUI_EXE%"
exit /b 0
