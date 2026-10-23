@echo off
setlocal EnableDelayedExpansion

title Claude CLI + OpenRouter Setup Launcher
echo ==================================================================
echo       Claude CLI + OpenRouter Windows Setup Launcher
echo ==================================================================
echo.

:: --------------------------------------------------------------------
:: 0. Windows Sandbox / Hyper-V DNS & PATH auto-configuration
:: --------------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object Status -eq 'Up' | Set-DnsClientServerAddress -ServerAddresses ('8.8.8.8','1.1.1.1') -ErrorAction SilentlyContinue; Clear-DnsClientCache" >nul 2>&1

if exist "%USERPROFILE%\.local\bin" set "PATH=%USERPROFILE%\.local\bin;!PATH!"
if exist "C:\Program Files\nodejs" set "PATH=C:\Program Files\nodejs;!PATH!"
if exist "%LOCALAPPDATA%\Programs\nodejs" set "PATH=%LOCALAPPDATA%\Programs\nodejs;!PATH!"

:: --------------------------------------------------------------------
:: 1. Check if Python is already available and actually functional
::    (Filters out the Windows 10/11 Microsoft Store dummy app alias)
:: --------------------------------------------------------------------
set "PYTHON_CMD="

where py >nul 2>&1
if not errorlevel 1 (
    py -V >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -V >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

:: Check standard local and portable Python installation paths
if not defined PYTHON_CMD (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%USERPROFILE%\Python312\python.exe" (
        set "PYTHON_CMD=%USERPROFILE%\Python312\python.exe"
    ) else if exist "%~dp0python\python.exe" (
        set "PYTHON_CMD=%~dp0python\python.exe"
    ) else if exist "C:\Program Files\Python312\python.exe" (
        set "PYTHON_CMD=C:\Program Files\Python312\python.exe"
    )
)

:: --------------------------------------------------------------------
:: 2. If Python is still missing, set up portable Python 3.12
:: --------------------------------------------------------------------
if not defined PYTHON_CMD (
    echo [-] Python runtime was not detected or only Microsoft Store alias is present.
    echo [i] Setting up official portable Python 3.12 runtime...

    set "PY_TARGET_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
    if not exist "%LOCALAPPDATA%" set "PY_TARGET_DIR=%USERPROFILE%\Python312"
    if not exist "!PY_TARGET_DIR!" mkdir "!PY_TARGET_DIR!" >nul 2>&1

    set "PY_ZIP=%TEMP%\python-3.12.8-embed.zip"
    set "PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"

    echo [+] Downloading Python 3.12 package from python.org...
    where curl >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        curl -fLo "!PY_ZIP!" "!PY_URL!"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('!PY_URL!', '!PY_ZIP!')"
    )

    if not exist "!PY_ZIP!" (
        echo [ERROR] Failed to download Python package.
        echo Please check your internet connection or install Python manually.
        pause
        exit /b 1
    )

    echo [+] Extracting portable runtime into !PY_TARGET_DIR!...
    where tar >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        tar -xf "!PY_ZIP!" -C "!PY_TARGET_DIR!"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '!PY_ZIP!' -DestinationPath '!PY_TARGET_DIR!' -Force"
    )

    del /f /q "!PY_ZIP!" >nul 2>&1

    if exist "!PY_TARGET_DIR!\python.exe" (
        set "PYTHON_CMD=!PY_TARGET_DIR!\python.exe"
        echo [+] Python runtime ready at !PYTHON_CMD!
        
        :: Register Python directory in User PATH for future sessions
        powershell -NoProfile -Command "[System.Environment]::SetEnvironmentVariable('Path', [System.Environment]::GetEnvironmentVariable('Path','User') + ';!PY_TARGET_DIR!', 'User')" >nul 2>&1
        set "PATH=!PY_TARGET_DIR!;!PATH!"
    ) else (
        echo [ERROR] Python extraction failed.
        pause
        exit /b 1
    )
)

:: --------------------------------------------------------------------
:: 3. Verify Python version
:: --------------------------------------------------------------------
echo [+] Using Python: %PYTHON_CMD%
"%PYTHON_CMD%" -c "import sys; print('    Runtime: Python ' + sys.version.split()[0])"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to execute Python.
    pause
    exit /b 1
)

:: --------------------------------------------------------------------
:: 4. Navigate to script directory and launch main.py
:: --------------------------------------------------------------------
cd /d "%~dp0"

echo.
echo [+] Starting Claude CLI + OpenRouter setup application...
echo.
"%PYTHON_CMD%" main.py %*

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% neq 0 (
    echo.
    echo [-] Application terminated with exit code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
