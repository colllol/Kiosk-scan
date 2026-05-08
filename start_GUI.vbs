' Kiosk Scan GUI Launcher (Hidden Console)
' Chay GUI ma khong hien cua so console

Dim shell
Set shell = CreateObject("WScript.Shell")

' Chay start_GUI.bat voi window style = 0 (hidden)
shell.Run "start_GUI.bat", 0, False

Set shell = Nothing