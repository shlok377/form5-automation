@echo off
setlocal enabledelayedexpansion

echo =================================================================
echo    FORM-5 Medical Examination Automation System - Windows Setup
echo =================================================================
echo.

cd /d "%~dp0"

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

:: 2. Set up Virtual Environment inside core\.venv
echo.
echo [2/4] Setting up Python virtual environment (core\.venv)...
if not exist "core\.venv" (
    %PYTHON_CMD% -m venv core\.venv
)

:: 3. Install Dependencies from core\requirements.txt
echo.
echo [3/4] Installing dependencies...
call core\.venv\Scripts\pip install --upgrade pip --quiet
call core\.venv\Scripts\pip install -r core\requirements.txt --quiet

:: 4. Ensure Directory Structure & Create Desktop Shortcut
echo.
echo [4/4] Verifying directory structure...
if not exist "output" mkdir output
if not exist "core\data" mkdir core\data
if not exist "core\temp_json" mkdir core\temp_json

echo Creating Desktop shortcut for convenient access...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut([System.IO.Path]::Combine($d, 'FORM-5 Medical Automation.lnk')); $s.TargetPath = '%~dp02_START.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Launch FORM-5 Medical Examination Dashboard'; $s.Save()" >nul 2>&1

echo.
echo =================================================================
echo   Installation Complete!
echo =================================================================
echo.
echo   HOW TO USE:
echo.
echo   Option 1: Double-click "2_START.bat" in this folder.
echo   Option 2: Double-click "FORM-5 Medical Automation" on your Desktop.
echo.
echo   All generated PDFs will automatically be saved into the "output" folder.
echo =================================================================
echo.
pause
