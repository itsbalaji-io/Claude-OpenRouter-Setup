@echo off
setlocal EnableDelayedExpansion

title Claude Code + OpenRouter 1-Click Installer
echo ==================================================================
echo       Claude CLI + OpenRouter Automated 1-Click Installer
echo ==================================================================
echo.

set "TARGET_DIR=%USERPROFILE%\.claude-openrouter-setup"
set "REPO_URL=https://github.com/itsbalaji-io/Claude-OpenRouter-Setup.git"
set "ZIP_URL=https://github.com/itsbalaji-io/Claude-OpenRouter-Setup/archive/refs/heads/main.zip"

:: 1. Check if git is available
where git >nul 2>&1
if !ERRORLEVEL! equ 0 (
    if exist "!TARGET_DIR!\.git" (
        echo [+] Updating existing installation at !TARGET_DIR!...
        git -C "!TARGET_DIR!" fetch origin main >nul 2>&1
        git -C "!TARGET_DIR!" reset --hard origin/main >nul 2>&1
    ) else (
        echo [+] Cloning repository to !TARGET_DIR!...
        if exist "!TARGET_DIR!" rmdir /s /q "!TARGET_DIR!" >nul 2>&1
        git clone --depth 1 "!REPO_URL!" "!TARGET_DIR!"
    )
) else (
    echo [i] Git not detected. Downloading package zip from GitHub...
    set "TEMP_ZIP=%TEMP%\claude-openrouter-setup.zip"
    set "EXTRACT_DIR=%TEMP%\claude-openrouter-extract"

    if exist "!TEMP_ZIP!" del /f /q "!TEMP_ZIP!" >nul 2>&1
    if exist "!EXTRACT_DIR!" rmdir /s /q "!EXTRACT_DIR!" >nul 2>&1

    where curl >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        curl -fLso "!TEMP_ZIP!" "!ZIP_URL!"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13; (New-Object Net.WebClient).DownloadFile('!ZIP_URL!', '!TEMP_ZIP!')"
    )

    if not exist "!TEMP_ZIP!" (
        echo [ERROR] Failed to download Claude-OpenRouter-Setup package.
        pause
        exit /b 1
    )

    echo [+] Extracting setup files...
    where tar >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        mkdir "!EXTRACT_DIR!" >nul 2>&1
        tar -xf "!TEMP_ZIP!" -C "!EXTRACT_DIR!"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '!TEMP_ZIP!' -DestinationPath '!EXTRACT_DIR!' -Force"
    )

    del /f /q "!TEMP_ZIP!" >nul 2>&1

    if exist "!TARGET_DIR!" rmdir /s /q "!TARGET_DIR!" >nul 2>&1
    mkdir "!TARGET_DIR!" >nul 2>&1

    xcopy /e /y /q "!EXTRACT_DIR!\Claude-OpenRouter-Setup-main\*" "!TARGET_DIR!\" >nul 2>&1
    rmdir /s /q "!EXTRACT_DIR!" >nul 2>&1
)

if not exist "!TARGET_DIR!\setup.bat" (
    echo [ERROR] Setup bundle could not be found at !TARGET_DIR!.
    pause
    exit /b 1
)

:: 2. Register global 'claude-setup' command in WindowsApps or User PATH
set "SHIM_DIR=%LOCALAPPDATA%\Microsoft\WindowsApps"
if exist "!SHIM_DIR!" (
    (
        echo @echo off
        echo call "%TARGET_DIR%\setup.bat" %%*
    ) > "!SHIM_DIR!\claude-setup.cmd"
    echo [+] Created global command: claude-setup
)

:: 3. Launch setup
echo [+] Starting setup application...
echo.
cd /d "!TARGET_DIR!"
call setup.bat %*
