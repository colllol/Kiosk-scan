' Debug version of start_Kiosk.vbs
Dim shell, fso, scriptPath, batPath, wshShell

Set fso = CreateObject("Scripting.FileSystemObject")
Set wshShell = CreateObject("WScript.Shell")

' Get the actual script location
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
WScript.Echo "Script path: " & scriptPath

batPath = fso.BuildPath(scriptPath, "start_Kiosk.bat")
WScript.Echo "Batch file path: " & batPath

' Check if batch file exists
If Not fso.FileExists(batPath) Then
    WScript.Echo "ERROR: Batch file not found!"
    WScript.Quit 1
End If

' Change to script directory
wshShell.CurrentDirectory = scriptPath
WScript.Echo "Current directory set to: " & scriptPath

' Test running the batch file with window visible for debugging
WScript.Echo "Running batch file..."
Set shell = CreateObject("WScript.Shell")

' Run with window visible (1 = normal window) and wait for completion
shell.Run "cmd.exe /c """ & batPath & """", 1, True

WScript.Echo "Batch file execution completed."

Set shell = Nothing
Set fso = Nothing
Set wshShell = Nothing