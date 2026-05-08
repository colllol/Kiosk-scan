' =====================================================
' start_kiosk.vbs — Chạy Backend + Train Worker ẩn dưới taskbar
' 
' Cách dùng:
'   - Double-click file này để chạy ngầm (không hiện console)
'   - Để dừng: mở Task Manager → kết thúc python.exe / pythonw.exe
'
' Luồng:
'   1. Train Worker — chạy bằng pythonw.exe (ẩn)
'   2. Backend FastAPI — chạy bằng pythonw.exe (ẩn)
' =====================================================

Dim shell
Set shell = CreateObject("WScript.Shell")

' Lấy đường dẫn thư mục backend
Dim scriptPath
scriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Tạo thư mục cần thiết
Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FolderExists(scriptPath & "\uploads") Then fso.CreateFolder(scriptPath & "\uploads")
If Not fso.FolderExists(scriptPath & "\pdfs") Then fso.CreateFolder(scriptPath & "\pdfs")
If Not fso.FolderExists(scriptPath & "\train_staging") Then fso.CreateFolder(scriptPath & "\train_staging")
If Not fso.FolderExists(scriptPath & "\train_dataset") Then fso.CreateFolder(scriptPath & "\train_dataset")

' Chạy Train Worker (ẩn, không hiện console)
shell.Run "pythonw.exe """ & scriptPath & "\train_worker.py""", 0, False

' Chờ 2 giây để worker khởi động
WScript.Sleep 2000

' Chạy Backend FastAPI (ẩn, không hiện console)
shell.Run "pythonw.exe """ & scriptPath & "\main.py""", 0, False

' Thông báo (tùy chọn — comment dòng dưới nếu không muốn popup)
' shell.Popup "Kiosk Scan da khoi dong ngam.", 3, "Kiosk Scan", 64
