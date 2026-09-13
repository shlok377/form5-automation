@echo off
setlocal enabledelayedexpansion

echo =================================================================
echo    FORM-5 Medical Examination Automation System - Windows Setup
echo =================================================================
echo.

:: 1. Check if Python is installed
echo [1/4] Checking Python installation...
set PYTHON_CMD=
where python >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo Python was not detected on this machine.
    echo Attempting automated installation of Python 3.11...
    echo.
    where winget >nul 2>nul
    if !errorlevel! equ 0 (
        echo Installing Python via Windows Package Manager (winget)...
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    ) else (
        echo Downloading Python installer from python.org via PowerShell...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
        echo Installing Python silently (adding to PATH)...
        start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1
        del python_installer.exe
    )

    :: Refresh PATH in current cmd session
    for /f "tokens=*" %%a in ('powershell -Command "[Environment]::GetEnvironmentVariable('Path', [EnvironmentVariableTarget]::User) + ';' + [Environment]::GetEnvironmentVariable('Path', [EnvironmentVariableTarget]::Machine)"') do set "PATH=%%a"
    
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set PYTHON_CMD=python
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            set PYTHON_CMD=py
        ) else (
            set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
        )
    )
)

echo Using Python: %PYTHON_CMD%

:: 2. Set up Virtual Environment
echo.
echo [2/4] Creating Python virtual environment (.venv)...
if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv
)

:: 3. Install Dependencies
echo.
echo [3/4] Installing dependencies...
call .venv\Scripts\pip install --upgrade pip --quiet
call .venv\Scripts\pip install -r requirements.txt --quiet

:: 4. Ensure Directory Structure
echo.
echo [4/4] Verifying directory structure...
if not exist "data" mkdir data
if not exist "temp_json" mkdir temp_json
if not exist "output" mkdir output

echo.
echo =================================================================
echo    Setup completed successfully!
echo.
echo    To launch the Web Dashboard:
echo    Double-click on "run.bat"
echo =================================================================
echo.
pause
