@echo off
setlocal
cd /d "%~dp0"

set PYTHON_EXEC=core\.venv\Scripts\python.exe

if not exist "%PYTHON_EXEC%" (
    echo [ERROR] Python environment not found!
    echo Please run "1_SETUP.bat" first to set up the system.
    echo.
    pause
    exit /b 1
)

if "%1"=="--cli" (
    echo Starting FORM-5 Batch Generation Pipeline via CLI...
    "%PYTHON_EXEC%" core\application\pipeline.py --workers 8 %*
    pause
    exit /b 0
)

if "%1"=="--status" (
    "%PYTHON_EXEC%" core\application\pipeline.py --status
    pause
    exit /b 0
)

echo =================================================================
echo    FORM-5 Medical Examination Automation System
echo =================================================================
echo.
echo Starting Web Dashboard server at http://localhost:8080...
echo Opening your default browser...
echo.
echo (Keep this window open while using the application. Press Ctrl+C to stop.)
echo.

start http://localhost:8080
"%PYTHON_EXEC%" core\application\server.py 8080

pause
