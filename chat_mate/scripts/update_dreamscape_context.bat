@echo off
REM Dreamscape Context Update - Windows Batch File
REM This script checks if a context update is due and sends it to ChatGPT

echo Checking for scheduled Dreamscape context updates...
python scripts/check_context_updates.py --config config/dreamscape_config.yaml

IF %ERRORLEVEL% NEQ 0 (
    echo Error: Context update failed with code %ERRORLEVEL%
) ELSE (
    echo Context update check completed successfully.
)

echo.
pause 