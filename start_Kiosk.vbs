' KIOSK SCAN SYSTEM - Hidden Launcher (FIXED)

Dim shell, fso, scriptDir, batPath, idcheckPath

Set fso = CreateObject("Scripting.FileSystemObject")

' Lấy thư mục chứa file .vbs
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(scriptDir, "start_Kiosk.bat")

' Kiểm tra file batch
If Not fso.FileExists(batPath) Then
    MsgBox "Không tìm thấy start_Kiosk.bat tại:" & vbCrLf & batPath, vbCritical, "Lỗi khởi động Kiosk"
    WScript.Quit 1
End If

Set shell = CreateObject("WScript.Shell")

' ====== RUN IDCheck.exe ======
idcheckPath = "C:\Program Files\HANEL eKYC\IDCheck.exe"

If fso.FileExists(idcheckPath) Then
    shell.Run """" & idcheckPath & """", 0, False
Else
    MsgBox "Không tìm thấy IDCheck.exe tại:" & vbCrLf & idcheckPath, vbCritical, "Lỗi eKYC"
End If

' ====== RUN BACKEND ======
shell.Run "cmd.exe /c """ & batPath & """", 0, False

Set shell = Nothing
Set fso = Nothing