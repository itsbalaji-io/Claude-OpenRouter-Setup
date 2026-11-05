# Claude Code + OpenRouter 1-Click PowerShell Installer
# Usage: irm https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "      Claude CLI + OpenRouter Automated 1-Click Installer         " -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$TargetDir = Join-Path $HOME ".claude-openrouter-setup"
$RepoUrl = "https://github.com/itsbalaji-io/Claude-OpenRouter-Setup.git"
$ZipUrl = "https://github.com/itsbalaji-io/Claude-OpenRouter-Setup/archive/refs/heads/main.zip"

if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path (Join-Path $TargetDir ".git")) {
        Write-Host "[+] Updating existing installation at $TargetDir..." -ForegroundColor Green
        git -C $TargetDir fetch origin main 2>$null
        git -C $TargetDir reset --hard origin/main 2>$null
    } else {
        Write-Host "[+] Cloning repository to $TargetDir..." -ForegroundColor Green
        if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
        git clone --depth 1 $RepoUrl $TargetDir
    }
} else {
    Write-Host "[i] Git not detected. Downloading package archive from GitHub..." -ForegroundColor Yellow
    $TempZip = Join-Path $env:TEMP "claude-openrouter-setup.zip"
    $ExtractDir = Join-Path $env:TEMP "claude-openrouter-extract"

    if (Test-Path $TempZip) { Remove-Item -Force $TempZip }
    if (Test-Path $ExtractDir) { Remove-Item -Recurse -Force $ExtractDir }

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
    (New-Object Net.WebClient).DownloadFile($ZipUrl, $TempZip)

    Write-Host "[+] Extracting setup files..." -ForegroundColor Green
    Expand-Archive -Path $TempZip -DestinationPath $ExtractDir -Force
    Remove-Item -Force $TempZip

    if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    Copy-Item -Path "$ExtractDir\Claude-OpenRouter-Setup-main\*" -Destination $TargetDir -Recurse -Force
    Remove-Item -Recurse -Force $ExtractDir
}

# Register global claude-setup command shim
$ShimDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
if (Test-Path $ShimDir) {
    $ShimContent = "@echo off`ncall `"$TargetDir\setup.bat`" %*"
    Set-Content -Path (Join-Path $ShimDir "claude-setup.cmd") -Value $ShimContent -Encoding Ascii
    Write-Host "[+] Registered global command: claude-setup" -ForegroundColor Green
}

# Run setup
Set-Location $TargetDir
& ".\setup.bat"
