@echo off
REM ============================================
REM Create shortcut to start_Kiosk.vbs
REM ============================================
powershell -Command ^
    $WSH = New-Object -ComObject WScript.Shell; ^
    $SC = $WSH.CreateShortcut('%~dp0start_Kiosk.lnk'); ^
    $SC.TargetPath = 'wscript.exe'; ^
    $SC.Arguments = '"%~dp0start_Kiosk.vbs"'; ^
    $SC.WorkingDirectory = '%~dp0'; ^
    $SC.WindowStyle = 7; ^
    $SC.Description = 'KIOSK Scan System - Hidden Launcher'; ^
    $SC.Save(); ^
    Write-Host 'Shortcut created: %~dp0start_Kiosk.lnk'
pause