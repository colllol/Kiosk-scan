' KIOSK SCAN SYSTEM - Hidden Launcher
' Starts IDCheck.exe when available, then starts start_Kiosk.bat hidden.

Option Explicit

Dim shell, fso, scriptDir, batPath, idcheckPath, logPath

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptDir, "start_Kiosk.bat")
idcheckPath = "C:\Program Files\HANEL eKYC\IDCheck.exe"
logPath = fso.BuildPath(scriptDir, "kiosk-launch.log")

shell.CurrentDirectory = scriptDir

If Not fso.FileExists(batPath) Then
    WriteLog "ERROR: Missing batch file: " & batPath
    MsgBox "Missing start_Kiosk.bat at:" & vbCrLf & batPath, vbCritical, "Kiosk startup error"
    CleanupAndQuit 1
End If

If fso.FileExists(idcheckPath) Then
    WriteLog "Starting IDCheck: " & idcheckPath
    shell.Run Quote(idcheckPath), 0, False
Else
    WriteLog "WARN: IDCheck.exe not found: " & idcheckPath
End If

WriteLog "Starting kiosk batch: " & batPath
shell.Run "cmd.exe /c " & Quote(batPath), 0, False

CleanupAndQuit 0

Function Quote(value)
    Quote = """" & value & """"
End Function

Sub WriteLog(message)
    Dim logFile
    Set logFile = fso.OpenTextFile(logPath, 8, True)
    logFile.WriteLine "[" & Now & "] " & message
    logFile.Close
    Set logFile = Nothing
End Sub

Sub CleanupAndQuit(exitCode)
    Set shell = Nothing
    Set fso = Nothing
    WScript.Quit exitCode
End Sub
