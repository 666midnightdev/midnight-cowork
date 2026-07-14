Set WshShell = CreateObject("WScript.Shell")
DesktopPath = WshShell.SpecialFolders("Desktop")
ProjectPath = "C:\Users\ASUS\Desktop\open_interpreter_ui"

' Create Mulai Midnight Cowork Shortcut (points directly to start.bat)
Set Shortcut1 = WshShell.CreateShortcut(DesktopPath & "\Mulai Midnight Cowork.lnk")
Shortcut1.TargetPath = ProjectPath & "\start.bat"
Shortcut1.WorkingDirectory = ProjectPath
Shortcut1.Description = "Mulai Midnight Cowork di Latar Belakang"
Shortcut1.IconLocation = "shell32.dll,12"
Shortcut1.Save

' Create Matikan Midnight Cowork Shortcut (points to stop.bat)
Set Shortcut2 = WshShell.CreateShortcut(DesktopPath & "\Matikan Midnight Cowork.lnk")
Shortcut2.TargetPath = ProjectPath & "\stop.bat"
Shortcut2.WorkingDirectory = ProjectPath
Shortcut2.Description = "Matikan Server Midnight Cowork"
Shortcut2.IconLocation = "shell32.dll,131"
Shortcut2.Save
