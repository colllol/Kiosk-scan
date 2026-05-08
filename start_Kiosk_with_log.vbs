' KIOSK SCAN SYSTEM - Hidden Launcher with logging
' This script launches start_Kiosk.bat and logs any errors

Dim shell, fso, scriptPath, batPath, wshShell, objExec, strOutput, strError

Set fso = CreateObject("Scripting.FileSystemObject")
Set wshShell = CreateObject("WScript.Shell")

' Get the actual script location
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptPath, "start_Kiosk.bat")

' Change to script directory
wshShell.CurrentDirectory = scriptPath

' Create a log file
logPath = fso.BuildPath(scriptPath, "vbs_launch.log")
Set logFile = fso.CreateTextFile(logPath, True)
logFile.WriteLine "[" & Now & "] Starting Kiosk launch..."
logFile.WriteLine "Script path: " & scriptPath
logFile.WriteLine "Batch path: " & batPath

' Check if batch file exists
If Not fso.FileExists(batPath) Then
    logFile.WriteLine "ERROR: Batch file not found!"
    logFile.Close
    WScript.Quit 1
End If

Set shell = CreateObject("WScript.Shell")

' Run the batch file and capture output
logFile.WriteLine "[" & Now & "] Executing batch file..."
Set objExec = shell.Exec("cmd.exe /c """ & batPath & """ 2>&1")

' Wait for completion with timeout
Do While objExec.Status = 0
    WScript.Sleep 100
Loop

' Read output
strOutput = objExec.StdOut.ReadAll
strError = objExec.StdErr.ReadAll

logFile.WriteLine "[" & Now & "] Batch execution completed."
logFile.WriteLine "Exit code: " & objExec.ExitCode
logFile.WriteLine "Output: " & strOutput
If strError <> "" Then logFile.WriteLine "Errors: " & strError

logFile.Close

' If there were errors, show a message
If objExec.ExitCode <> 0 Then
    MsgBox "Failed to start Kiosk. Check vbs_launch.log for details.", vbCritical, "Kiosk Error"
End If

Set objExec = Nothing
Set shell = Nothing
Set fso = Nothing
Set wshShell = Nothing