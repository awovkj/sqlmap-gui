Set shell = CreateObject("WScript.Shell")
Set filesystem = CreateObject("Scripting.FileSystemObject")

scriptDir = filesystem.GetParentFolderName(WScript.ScriptFullName)
command = "cmd /c set SQLMAP_GUI_NO_PAUSE=1&& cd /d " & Chr(34) & scriptDir & Chr(34) & " && call " & Chr(34) & scriptDir & "\start.bat" & Chr(34)

shell.Run command, 0, False
