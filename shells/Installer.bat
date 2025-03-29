@echo off
:: Auto-elevate
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

echo Installing KeepAwake script...

:: Copy PS1 to a working directory
mkdir %ProgramData%\KeepAwake
copy KeepAwake.ps1 %ProgramData%\KeepAwake\KeepAwake.ps1

:: Create startup shortcut
echo Creating startup entry...
powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeepAwake.lnk');$s.TargetPath='powershell';$s.Arguments='-ExecutionPolicy Bypass -File ""%ProgramData%\KeepAwake\KeepAwake.ps1""';$s.Save()"

echo Done! KeepAwake is now running in the background.
pause
