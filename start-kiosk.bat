@echo off
setlocal

cd /d "%~dp0"
call "%~dp0start_Kiosk.bat"
exit /b %ERRORLEVEL%
