@echo on
echo Starting Dream.OS debug session...
echo.

echo Checking Python version:
python -V
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call .\venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Python path after activation:
where python
echo.

echo Checking PyQt5 installation:
python -c "import PyQt5; print('PyQt5 version:', PyQt5.QtCore.QT_VERSION_STR)"
if %ERRORLEVEL% neq 0 (
    echo Error: PyQt5 not properly installed
    echo Installing PyQt5...
    pip install PyQt5
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install PyQt5
        pause
        exit /b 1
    )
)

echo.
echo PYTHONPATH:
python -c "import sys; print('\n'.join(sys.path))"
echo.

echo Starting Dream.OS...
python -v -m interfaces.pyqt

echo.
if %ERRORLEVEL% neq 0 (
    echo Application exited with error code %ERRORLEVEL%
) else (
    echo Application exited successfully
)

pause 