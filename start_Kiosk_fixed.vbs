' KIOSK SCAN SYSTEM - Hidden Launcher (FIXED VERSION)
' This script launches start_Kiosk.bat with NO console window at all.
' All child processes (backend EXE, frontend Python) are also hidden.

Dim shell, fso, scriptPath, batPath, wshShell

Set fso = CreateObject("Scripting.FileSystemObject")
Set wshShell = CreateObject("WScript.Shell")

' Get the actual script location (more reliable method)
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptPath, "start_Kiosk.bat")

' Change to script directory to ensure relative paths work
wshShell.CurrentDirectory = scriptPath

Set shell = CreateObject("WScript.Shell")

' Run the batch file completely hidden (0 = hide window)
' Use True to wait for the batch file to complete (keeps VBS alive)
shell.Run "cmd.exe /c """ & batPath & """", 0, True

Set shell = Nothing
Set fso = Nothing
Set wshShell = Nothing