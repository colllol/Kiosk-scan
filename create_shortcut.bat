@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "SHORTCUT=%ROOT_DIR%start_Kiosk.lnk"
set "TARGET=%ROOT_DIR%start_Kiosk.vbs"

if not exist "%TARGET%" (
    echo [ERROR] Missing launcher: %TARGET%
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$shortcut = $shell.CreateShortcut('%SHORTCUT%'); " ^
  "$shortcut.TargetPath = 'wscript.exe'; " ^
  "$shortcut.Arguments = '""%TARGET%""'; " ^
  "$shortcut.WorkingDirectory = '%ROOT_DIR%'; " ^
  "$shortcut.WindowStyle = 7; " ^
  "$shortcut.Description = 'Kiosk Scan System'; " ^
  "$shortcut.Save()"

if errorlevel 1 (
    echo [ERROR] Failed to create shortcut.
    pause
    exit /b 1
)

echo [OK] Shortcut created: %SHORTCUT%
pause
