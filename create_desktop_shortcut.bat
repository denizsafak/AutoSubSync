@echo off
setlocal
set "target=%~dp0run.bat"
set "icon=%~dp0main\icon.ico"
set "shortcut=%USERPROFILE%\Desktop\AutoSubSync.lnk"

echo Creating desktop shortcut...
:: Try PowerShell method
powershell -NoProfile -Command ^
    "$s = New-Object -ComObject WScript.Shell; " ^
    "$sc = $s.CreateShortcut('%shortcut%'); " ^
    "$sc.TargetPath = '%target%'; " ^
    "$sc.IconLocation = '%icon%'; " ^
    "$sc.Save()" 
if errorlevel 1 (
    echo PowerShell method failed. Trying another method...
    goto vbscript
) else (
    echo Shortcut created successfully.
    goto end
)
:vbscript
echo Creating desktop shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%temp%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut("%shortcut%") >> "%temp%\create_shortcut.vbs"
echo oLink.TargetPath = "%target%" >> "%temp%\create_shortcut.vbs"
echo oLink.IconLocation = "%icon%" >> "%temp%\create_shortcut.vbs"
echo oLink.Save >> "%temp%\create_shortcut.vbs"
cscript //nologo "%temp%\create_shortcut.vbs"
del "%temp%\create_shortcut.vbs"

if exist "%shortcut%" (
    echo Shortcut created successfully.
) else (
    echo Failed to create shortcut.
)
:end
echo.
echo Press any key to exit...
pause >nul
endlocal