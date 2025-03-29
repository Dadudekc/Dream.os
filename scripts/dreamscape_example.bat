@echo off
REM Dreamscape Content Generator - Example batch file
REM Adjust paths as needed for your environment

echo Running Dreamscape Content Generator...
python scripts/run_dreamscape.py --config config/dreamscape_config.yaml

echo.
echo Done! Check the outputs/dreamscape directory for results.
echo.
pause 