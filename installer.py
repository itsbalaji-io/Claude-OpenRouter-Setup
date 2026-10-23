"""Prerequisites detection and installer module for Windows.

Handles checking and installing:
- Windows version & Administrator privileges
- Python runtime (>= 3.10)
- Node.js LTS & npm
- Anthropic Claude Code CLI
"""

import os
import sys
import shutil
import ctypes
import platform
import subprocess
import winreg
from typing import Dict, Optional, Tuple, List


def is_windows() -> bool:
    """Return True if running on Windows."""
    return sys.platform == "win32"


def is_admin() -> bool:
    """Check if the current process has Administrator privileges on Windows."""
    if not is_windows():
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_windows_info() -> Dict[str, str]:
    """Return Windows OS version information."""
    return {
        "platform": platform.platform(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.architecture()[0],
    }


def get_powershell_version() -> Optional[str]:
    """Retrieve installed PowerShell version via command line."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


def get_active_and_registry_path() -> str:
    """Combine current process PATH with User and Machine registry PATHs."""
    paths = [os.environ.get("PATH", "")]
    for hkey, subkey in [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]:
        try:
            with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "Path")
                paths.append(str(val))
        except Exception:
            pass
    return ";".join(paths)


def find_executable(name: str, candidate_paths: Optional[List[str]] = None) -> Optional[str]:
    """Locate an executable searching PATH, registry PATHs, and common candidate directories."""
    combined_path = get_active_and_registry_path()
    found = shutil.which(name, path=combined_path)
    if found and os.path.exists(found):
        return os.path.abspath(found)

    if candidate_paths:
        for c in candidate_paths:
            expanded = os.path.expandvars(c)
            if os.path.isfile(expanded):
                return os.path.abspath(expanded)
    return None


def detect_python() -> Tuple[bool, str]:
    """Verify current Python version is 3.10+."""
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver.major == 3 and ver.minor >= 10:
        return True, ver_str
    return False, ver_str


def detect_nodejs() -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect Node.js executable and version.
    
    Returns:
        (is_installed, executable_path, version_string)
    """
    candidates = [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        r"%LOCALAPPDATA%\Programs\node\node.exe",
    ]
    node_exe = find_executable("node", candidates)
    if not node_exe:
        return False, None, None

    try:
        res = subprocess.run(
            [node_exe, "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if res.returncode == 0:
            return True, node_exe, res.stdout.strip()
    except Exception:
        pass
    return True, node_exe, "[Unknown version]"


def detect_npm() -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect npm executable and version.
    
    Returns:
        (is_installed, executable_path, version_string)
    """
    candidates = [
        r"C:\Program Files\nodejs\npm.cmd",
        r"C:\Program Files (x86)\nodejs\npm.cmd",
        r"%APPDATA%\npm\npm.cmd",
    ]
    npm_exe = find_executable("npm.cmd", candidates) or find_executable("npm", candidates)
    if not npm_exe:
        return False, None, None

    try:
        res = subprocess.run(
            [npm_exe, "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if res.returncode == 0:
            return True, npm_exe, res.stdout.strip()
    except Exception:
        pass
    return True, npm_exe, "[Unknown version]"


def add_directory_to_path(target_dir: str) -> bool:
    """Permanently register a directory in the Windows User PATH registry and active process PATH."""
    target_dir = os.path.abspath(os.path.expandvars(target_dir))
    if not os.path.isdir(target_dir):
        return False

    # 1. Update active process PATH
    current_path = os.environ.get("PATH", "")
    if target_dir.lower() not in [p.lower() for p in current_path.split(";") if p]:
        os.environ["PATH"] = f"{target_dir};{current_path}"

    # 2. Update User Registry PATH
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS) as k:
            try:
                val, _ = winreg.QueryValueEx(k, "Path")
            except FileNotFoundError:
                val = ""
            parts = [p.strip() for p in val.split(";") if p.strip()]
            if target_dir.lower() not in [p.lower() for p in parts]:
                parts.append(target_dir)
                winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, ";".join(parts))
    except Exception:
        pass

    # 3. If Administrator, also update Machine Registry PATH
    if is_admin():
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_ALL_ACCESS,
            ) as k:
                try:
                    val, _ = winreg.QueryValueEx(k, "Path")
                except FileNotFoundError:
                    val = ""
                parts = [p.strip() for p in val.split(";") if p.strip()]
                if target_dir.lower() not in [p.lower() for p in parts]:
                    parts.append(target_dir)
                    winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, ";".join(parts))
        except Exception:
            pass

    # 4. Broadcast setting change
    try:
        from config import broadcast_setting_change
        broadcast_setting_change()
    except Exception:
        pass
    return True


def create_global_shim(name: str, target_exe: str) -> bool:
    r"""Create a .cmd launcher shim in C:\Windows or WindowsApps so the command is globally recognized in CMD and PowerShell."""
    target_exe = os.path.abspath(os.path.expandvars(target_exe))
    if not os.path.exists(target_exe):
        return False

    cmd_content = f'@echo off\n"{target_exe}" %*\n'

    # Method 1: Try C:\Windows (guaranteed to be on PATH on all Windows systems)
    win_dir = os.environ.get("SystemRoot", r"C:\Windows")
    shim_path = os.path.join(win_dir, f"{name}.cmd")
    try:
        with open(shim_path, "w", encoding="utf-8") as f:
            f.write(cmd_content)
        return True
    except (PermissionError, OSError):
        pass

    # Method 2: Try %LOCALAPPDATA%\Microsoft\WindowsApps (in default User PATH)
    local_apps = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
    if os.path.isdir(local_apps):
        try:
            with open(os.path.join(local_apps, f"{name}.cmd"), "w", encoding="utf-8") as f:
                f.write(cmd_content)
            return True
        except Exception:
            pass

    return False


def detect_claude_code() -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect Anthropic Claude Code CLI executable and version."""
    candidates = [
        r"%USERPROFILE%\.local\bin\claude.exe",
        r"%LOCALAPPDATA%\Microsoft\WinGet\Links\claude.exe",
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\claude.exe",
        r"%APPDATA%\npm\claude.cmd",
        r"C:\Program Files\nodejs\claude.cmd",
    ]
    claude_exe = find_executable("claude.exe", candidates) or find_executable("claude", candidates)
    if not claude_exe:
        return False, None, None

    # Ensure global accessibility in CMD and PowerShell
    create_global_shim("claude", claude_exe)
    add_directory_to_path(os.path.dirname(claude_exe))

    try:
        res = subprocess.run(
            [claude_exe, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if res.returncode == 0:
            return True, claude_exe, res.stdout.strip()
    except Exception:
        pass
    return True, claude_exe, "[Installed, version check pending]"


def has_winget() -> bool:
    """Check if winget.exe is available on the system."""
    return find_executable("winget.exe") is not None


def download_file_securely(url: str, dest_path: str, timeout: int = 180) -> bool:
    """Download a file securely using curl.exe, PowerShell, or urllib with Windows Root Certs."""
    # Method 1: Try built-in curl.exe (uses Windows Schannel root certificate store natively)
    curl_exe = shutil.which("curl.exe") or shutil.which("curl")
    if curl_exe:
        try:
            res = subprocess.run(
                [curl_exe, "-fLo", dest_path, url],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if res.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000:
                return True
        except Exception:
            pass

    # Method 2: Try PowerShell (uses Windows Schannel via .NET WebClient)
    try:
        ps_cmd = (
            f"[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
            f"(New-Object Net.WebClient).DownloadFile('{url}', '{dest_path}')"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000:
            return True
    except Exception:
        pass

    # Method 3: urllib with Windows system certificates
    try:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
        except Exception:
            pass
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-OpenRouter-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000
    except Exception:
        pass

    return False


def install_nodejs() -> Tuple[bool, str]:
    """Install Node.js LTS and npm using winget or direct official portable archive."""
    # Method 1: Try winget if available
    if has_winget():
        cmd = [
            "winget", "install",
            "--id", "OpenJS.NodeJS.LTS",
            "--exact",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if res.returncode == 0:
                node_ok, node_path, node_ver = detect_nodejs()
                if node_ok and node_path:
                    create_global_shim("node", node_path)
                    add_directory_to_path(os.path.dirname(node_path))
                    npm_ok, npm_path, _ = detect_npm()
                    if npm_ok and npm_path:
                        create_global_shim("npm", npm_path)
                    return True, f"Node.js installed successfully ({node_ver}) at {node_path}."
        except Exception:
            pass

    # Method 2: Direct official Node.js Portable zip (100% reliable in Windows Sandbox)
    try:
        import zipfile
        import tempfile

        target_dir = r"C:\Program Files\nodejs"
        try:
            os.makedirs(target_dir, exist_ok=True)
            test_f = os.path.join(target_dir, ".test_write")
            with open(test_f, "w") as f:
                f.write("ok")
            os.remove(test_f)
        except (PermissionError, OSError):
            target_dir = os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs")
            os.makedirs(target_dir, exist_ok=True)

        zip_url = "https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip"
        temp_zip = os.path.join(tempfile.gettempdir(), "node-portable.zip")
        if not download_file_securely(zip_url, temp_zip, timeout=180):
            return False, "Failed to download Node.js package. Please check network connectivity."

        with zipfile.ZipFile(temp_zip, "r") as z:
            for member in z.infolist():
                parts = member.filename.split("/", 1)
                if len(parts) > 1 and parts[1]:
                    dest_file = os.path.join(target_dir, parts[1].replace("/", os.sep))
                    if member.is_dir():
                        os.makedirs(dest_file, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        with z.open(member) as src, open(dest_file, "wb") as dst:
                            dst.write(src.read())

        if os.path.exists(temp_zip):
            try:
                os.remove(temp_zip)
            except Exception:
                pass

        add_directory_to_path(target_dir)

        node_exe = os.path.join(target_dir, "node.exe")
        npm_cmd = os.path.join(target_dir, "npm.cmd")
        npx_cmd = os.path.join(target_dir, "npx.cmd")

        if os.path.exists(node_exe):
            create_global_shim("node", node_exe)
        if os.path.exists(npm_cmd):
            create_global_shim("npm", npm_cmd)
        if os.path.exists(npx_cmd):
            create_global_shim("npx", npx_cmd)

        node_ok, node_path, node_ver = detect_nodejs()
        if node_ok:
            return True, f"Node.js LTS and npm installed successfully ({node_ver}) at {node_path}."
        return True, f"Node.js installed to {target_dir}."
    except Exception as e:
        return False, f"Failed to install Node.js: {e}"


def install_claude_code() -> Tuple[bool, str]:
    """Install Claude Code using winget, npm, or native installer with global shimming."""
    # Method 1: Try WinGet first (official package Anthropic.ClaudeCode)
    if has_winget():
        cmd = [
            "winget", "install",
            "--id", "Anthropic.ClaudeCode",
            "--exact",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent",
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    create_global_shim("claude", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Claude Code installed successfully via winget ({ver}) at {path}."
        except Exception:
            pass

    # Method 2: Try native installer
    ps_cmd = 'irm https://claude.ai/install.ps1 | iex'
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if res.returncode == 0:
            ok, path, ver = detect_claude_code()
            if ok and path:
                create_global_shim("claude", path)
                add_directory_to_path(os.path.dirname(path))
                return True, f"Claude Code installed via native installer ({ver}) at {path}."
    except Exception:
        pass

    # Method 3: Try npm
    npm_ok, npm_exe, _ = detect_npm()
    if npm_ok and npm_exe:
        cmd = [npm_exe, "install", "-g", "@anthropic-ai/claude-code"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    create_global_shim("claude", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Claude Code installed successfully via npm ({ver}) at {path}."
        except Exception as e:
            return False, f"npm install failed: {e}"

    return False, "Failed to install Claude Code. Please run 'winget install Anthropic.ClaudeCode' manually."
