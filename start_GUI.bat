@echo off
setlocal

title Kiosk Scan GUI

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "GRIDFLUX_DIR=%APPDATA%\GridFlux"
set "GRIDFLUX_CONFIG=%GRIDFLUX_DIR%\config.json"
set "GUI_EXE=%ROOT_DIR%GUI\build\bin\gridflux.exe"
set "PYTHONW_EXE=%BACKEND_DIR%\venv\Scripts\pythonw.exe"

echo ========================================
echo   Kiosk Scan GUI - GridFlux
echo ========================================
echo.

if not exist "%GRIDFLUX_DIR%" mkdir "%GRIDFLUX_DIR%"

echo [CONFIG] Writing GridFlux layout...
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
echo   "workspace_names": ["Kiosk"],
echo   "startup_tasks": [
echo     "http://localhost:3000/index4.html",
echo     "http://localhost:3000/index2.html"
echo   ],
echo   "startup_task_f11": [true, true],
echo   "window_rules": []
echo }
) > "%GRIDFLUX_CONFIG%"

if not exist "%BACKEND_DIR%\main.py" (
    echo [ERROR] Missing backend file: %BACKEND_DIR%\main.py
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\index.html" (
    echo [ERROR] Missing frontend file: %FRONTEND_DIR%\index.html
    pause
    exit /b 1
)

echo [BACKEND] Starting API server on port 5000...
if exist "%PYTHONW_EXE%" (
    start "Kiosk Backend" /D "%BACKEND_DIR%" "%PYTHONW_EXE%" "%BACKEND_DIR%\main.py"
) else (
    where pythonw >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] pythonw.exe not found. Install Python or create backend venv first.
        pause
        exit /b 1
    )
    start "Kiosk Backend" /D "%BACKEND_DIR%" pythonw.exe "%BACKEND_DIR%\main.py"
)

echo [FRONTEND] Starting HTTP server on port 3000...
start "Kiosk Frontend" /D "%FRONTEND_DIR%" /B pythonw.exe -m http.server 3000 --bind localhost > "%FRONTEND_DIR%\frontend-server.log" 2> "%FRONTEND_DIR%\frontend-server.err.log"

timeout /t 2 /nobreak >nul

if not exist "%GUI_EXE%" (
    echo [BUILD] gridflux.exe not found. Building GUI...
    call "%ROOT_DIR%GUI\build.bat"
)

if not exist "%GUI_EXE%" (
    echo [ERROR] GUI executable not found:
    echo %GUI_EXE%
    pause
    exit /b 1
)

echo [GUI] Starting GridFlux...
start "GridFlux" "%GUI_EXE%"
exit /b 0
