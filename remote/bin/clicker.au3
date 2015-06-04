#include <Array.au3>
#include <FileConstants.au3>

Global $hLogFile
Global $LOGPATH = "c:\malware\clicker-log.txt"
Global $BUTTONSSTRING = "OK|Ok|ok|YES|Yes|yes|NEXT|NEXT >|Next >|Next>|Next|&Next >|next|INSTALL|&Install|Install|install|FINISH|Finish|&Finish|finish|ACCEPT|Accept|Accept >|&Accept >|accept"
Global $BUTTONS = StringSplit($BUTTONSSTRING, "|")
_ArraySort($BUTTONS, 0, 1)
Opt("MouseCoordMode", 2)

Func HaveWindow($list, $value)
	Local $rv = False
	If _ArraySearch($list, $value) > 0 Then
		$rv = True
	EndIf
	Return $rv
EndFunc


Func GetNewWindows($listA, $listB)
	Local $newList[1]
	$newList[0] = 0

	For $i = 1 to $listB[0]
		If Not HaveWindow($listA, $listB[$i]) Then
			_ArrayAdd($newList, $listB[$i])
			$newList[0] += 1
		EndIf
	Next
	Return $newList
EndFunc


Func GetWindowsNames()
	Local $list = WinList()
	Local $newList[1]
	$newList[0] = 0

	For $i = 1 To $list[0][0]
		If $list[$i][0] <> "" And BitAND(WinGetState($list[$i][1]), 2) Then
			;ConsoleWrite("Window " & $i & ": " & $list[$i][0] & @CRLF)
			_ArrayAdd($newList, $list[$i][0])
			$newList[0] += 1
		EndIf
	Next

	Return $newList
EndFunc


Func WaitNewWindow()
	Local $wList = GetWindowsNames()
	Local $count = $wList[0]
	Local $tmpList
	Local $tmpCount = 0

	DO
		$tmpList = GetWindowsNames()
		$tmpCount = $tmpList[0]
		Sleep(1000)
	Until $tmpCount > $count

	$newList = GetNewWindows($wList, $tmpList)
	return $newList
EndFunc


Func FindClass($list, $class)
	Local $i

	For $i = UBound($list)-1 To 0 Step - 1
		If $list[$i] <> $class Then
			_ArrayDelete($list, $i)
		EndIf
	Next

	return $list
EndFunc


Func RenameClasses($buttons)
	Local $i

	For $i=0 to UBound($buttons)-1
		$buttons[$i] = $buttons[$i] & $i+1
	Next

	Return $buttons
EndFunc


Func GetControlInfo($wnd, $controls)
	Local $info[0][5]
	Local $i
	Local $handle
	Local $pos
	Local $text
	Local $controlID

	For $i = 0 to UBound($controls)-1
		$controlID = "[CLASSNN:" & $controls[$i] & "]"
		$handle = ControlGetHandle($wnd, "",  $controlID)
		$pos = ControlGetPos($wnd, "", $controlID)
		$text = ControlGetText($wnd, "", $controlID)
		Local $tmp[1][5] = [[$controlId, $handle, $text, $pos[0], $pos[1]]]
		_ArrayAdd($info, $tmp)
	Next
	return $info
EndFunc


Func FilterInvisible($wnd, $controls)
	Local $i

	For $i = UBound($controls)-1 to 0 Step - 1
		If Not ControlCommand($wnd, "", $controls[$i], "IsVisible") Then
			_ArrayDelete($controls, $i)
		EndIf
	Next

	return $controls
EndFunc


Func ClickThrough($wnd)
	Local $i = 1, $j=0
	Local $rv = 0
	Local $matched = 0

	WinActivate($wnd)

	While WinExists($wnd)
		WinWaitActive($wnd, "", 5)

		$matched = 0

		Local $classList = WinGetClassList($wnd)
		$classList = StringSplit($classList, @CRLF, 2)

		Local $buttonList = FindClass($classList, "TNewButton")
		$buttonList = RenameClasses($buttonList)
		$buttonList = FilterInvisible($wnd, $buttonList)
		Local $buttonInfo = GetControlInfo($wnd, $buttonList)
		Local $numButtons = UBound($buttonInfo)

		Local $radioButtonList = FindClass($classList, "TRadioButton")
		$radioButtonList = RenameClasses($radioButtonList)
		$radioButtonList = FilterInvisible($wnd, $radioButtonList)
		If UBound($radioButtonList) Then
			_ArrayDisplay($radioButtonList)
		EndIf

		Local $checkBoxList = FindClass($classList, "TCheckBox")
		$checkBoxList = RenameClasses($checkBoxList)
		$checkBoxList = FilterInvisible($wnd, $checkBoxList)
		If UBound($checkBoxList) Then
			_ArrayDisplay($checkBoxList)
		EndIf

		For $j=0 To $numButtons-1
			$rv = _ArrayBinarySearch($BUTTONS, $buttonInfo[$j][2], 1, $BUTTONS[0])

			FileWrite($hLogFile, "Search for: '"& $buttonInfo[$j][2] & "'...")
			ConsoleWrite("Search for: '" & $buttonInfo[$j][2] & "'" & @CRLF)

			If $rv > 0 Then
				FileWriteLine($hLogFile, "match @ " & $rv)
				MouseClick("left", $buttonInfo[$j][3], $buttonInfo[$j][4], 1, 50)
				$matched = 1
				ExitLoop
			EndIf

			FileWrite($hLogFile, @CRLF)
		Next

		Sleep(2000)

		If $matched Then
			FileWriteLine($hLogFile, "Clicked '" & $BUTTONS[$rv] & "' in " & $wnd)
			ConsoleWrite("Clicked '" & $BUTTONS[$rv] & "' in " & $wnd & @CRLF)
		ElseIf $numButtons Then
			FileWriteLine($hLogFile, "NOT FOUND")
			ConsoleWrite("NOT FOUND" & @CRLF)
		EndIf
	WEnd
EndFunc


Func main()
	If $CmdLine[0] Then
		$hLogFile = FileOpen($CmdLine[1], $FO_APPEND)
	Else
		$hLogFile = FileOpen($LOGPATH, $FO_APPEND)
	EndIf

	$newWindows = WaitNewWindow()

	For $i = 1 to $newWindows[0]
		FileWriteLine($hLogFile, "New Window " & $i & ": '" & $newWindows[$i] & "'")
		ConsoleWrite("New Window " & $i & ": " & $newWindows[$i] & @CRLF)
		ClickThrough($newWindows[$i])
		FileWriteLine($hLogFile, "-------------------------------------")
	Next
EndFunc

main()