@echo off
echo Starting Stoxalotl...

:: Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found in PATH. Checking for specific Python locations...
    
    :: Try Python from virtual environment
    if exist ".venv\Scripts\python.exe" (
        echo Using Python from virtual environment...
        .venv\Scripts\python.exe run_stoxalotl.py
        goto :end
    )
    
    :: Try system Python locations
    if exist "C:\Python310\python.exe" (
        echo Using Python 3.10...
        C:\Python310\python.exe run_stoxalotl.py
        goto :end
    )
    
    echo Python not found! Please install Python 3.8 or newer.
    pause
    exit /b 1
) else (
    :: Use Python from PATH
    python run_stoxalotl.py
)

:end
if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%
    echo See logs folder for details.
    pause
)
