#Region ;**** Directives created by AutoIt3Wrapper_GUI ****
#AutoIt3Wrapper_Outfile=C:\Documents and Settings\venge\Desktop\clicks.exe
#EndRegion ;**** Directives created by AutoIt3Wrapper_GUI ****
Opt("WinTitleMatchMode", 4)
Opt("MouseCoordMode", 2)

Global $CLICKS = 4
Local $mousePos[2] = [0, 0]

If $CmdLine[0] = 1 Then
	$CLICKS = $CmdLine[1]
EndIf

WinActivate("[CLASS:Shell_TrayWnd]")

Local $pos = ControlGetPos("[CLASS:Shell_TrayWnd]", "", "Button1")

If IsArray($pos) Then
	$mousePos[0] = $pos[0]
	$mousePos[1] = $pos[1]
EndIf

Local $i
For $i=0 To $CLICKS
	WinActivate("[CLASS:Shell_TrayWnd]")
	MouseClick("left", $pos[0], $pos[1], 1, 50)
	Sleep(1000)
Next
