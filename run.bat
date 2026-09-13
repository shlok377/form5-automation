@echo off
setlocal

cd /d "%~dp0"

set PYTHON_EXEC=.venv\Scripts\python.exe

if not exist "%PYTHON_EXEC%" (
    echo Python environment not found!
    echo Please run install.bat first to set up the system.
    echo.
    pause
    exit /b 1
)

if "%1"=="--cli" (
    echo Starting FORM-5 Batch Generation Pipeline via CLI...
    "%PYTHON_EXEC%" application\pipeline.py --workers 8 %*
    pause
    exit /b 0
)

if "%1"=="--status" (
    "%PYTHON_EXEC%" application\pipeline.py --status
    pause
    exit /b 0
)

echo Starting FORM-5 Medical Examination Dashboard...
echo Server running at http://localhost:8080
echo Opening web browser...
echo.
echo Press Ctrl+C in this window to stop the server.

start http://localhost:8080
"%PYTHON_EXEC%" application\server.py 8080

pause
