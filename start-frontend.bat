@echo off
echo Starting Frontend Server on http://localhost:3000
echo Press Ctrl+C to stop the server
echo.
cd /d "%~dp0frontend"
python -m http.server 3000
pause
