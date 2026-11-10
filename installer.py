"""Prerequisites detection and cross-platform installer module.

Handles checking and installing across Windows, macOS, and Linux:
- OS version & Administrator / sudo privileges
- Python runtime (>= 3.10)
- Node.js LTS & npm
- Anthropic Claude Code CLI
"""

import os
import sys
import shutil
import platform
import subprocess
import tempfile
import zipfile
import ssl
from typing import Dict, Optional, Tuple, List


def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_admin() -> bool:
    if is_windows():
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except Exception:
            return False


def get_system_info() -> Dict[str, str]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
    }


def get_powershell_version() -> Optional[str]:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        return None
    try:
        res = subprocess.run(
            [exe, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _get_search_paths() -> str:
    """Combine current process PATH with system paths."""
    paths = [os.environ.get("PATH", "")]
    if is_windows():
        try:
            import winreg
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
        except ImportError:
            pass
    else:
        home = os.path.expanduser("~")
        paths.extend([
            os.path.join(home, ".local", "bin"),
            "/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin",
        ])
    return os.pathsep.join(paths)


def find_executable(name: str, candidate_paths: Optional[List[str]] = None) -> Optional[str]:
    combined_path = _get_search_paths()
    found = shutil.which(name, path=combined_path)
    if found and os.path.exists(found):
        return os.path.abspath(found)

    if candidate_paths:
        for c in candidate_paths:
            expanded = os.path.expanduser(os.path.expandvars(c))
            if os.path.isfile(expanded):
                return os.path.abspath(expanded)
    return None


def detect_python() -> Tuple[bool, str]:
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if ver.major == 3 and ver.minor >= 10:
        return True, ver_str
    return False, ver_str


def detect_nodejs() -> Tuple[bool, Optional[str], Optional[str]]:
    candidates = (
        [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe",
         r"%LOCALAPPDATA%\Programs\node\node.exe", r"%LOCALAPPDATA%\Programs\nodejs\node.exe"]
        if is_windows() else
        ["/usr/local/bin/node", "/opt/homebrew/bin/node", "/usr/bin/node",
         os.path.expanduser("~/.nvm/versions/node/*/bin/node")]
    )
    node_exe = find_executable("node", candidates)
    if not node_exe:
        return False, None, None
    try:
        res = subprocess.run([node_exe, "-v"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=10)
        if res.returncode == 0:
            return True, node_exe, res.stdout.strip()
    except Exception:
        pass
    return True, node_exe, "[Unknown version]"


def detect_npm() -> Tuple[bool, Optional[str], Optional[str]]:
    candidates = (
        [r"C:\Program Files\nodejs\npm.cmd", r"C:\Program Files (x86)\nodejs\npm.cmd",
         r"%APPDATA%\npm\npm.cmd", r"%LOCALAPPDATA%\Programs\nodejs\npm.cmd"]
        if is_windows() else
        ["/usr/local/bin/npm", "/opt/homebrew/bin/npm", "/usr/bin/npm"]
    )
    npm_exe = find_executable("npm.cmd", candidates) or find_executable("npm", candidates)
    if not npm_exe:
        return False, None, None
    try:
        res = subprocess.run([npm_exe, "-v"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=10)
        if res.returncode == 0:
            return True, npm_exe, res.stdout.strip()
    except Exception:
        pass
    return True, npm_exe, "[Unknown version]"


def add_directory_to_path(target_dir: str) -> bool:
    target_dir = os.path.abspath(os.path.expanduser(os.path.expandvars(target_dir)))
    if not os.path.isdir(target_dir):
        return False

    current_path = os.environ.get("PATH", "")
    sep = ";" if is_windows() else ":"
    parts = [p for p in current_path.split(sep) if p]
    if target_dir not in parts:
        os.environ["PATH"] = f"{target_dir}{sep}{current_path}"

    if is_windows():
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS) as k:
                try:
                    val, _ = winreg.QueryValueEx(k, "Path")
                except FileNotFoundError:
                    val = ""
                win_parts = [p.strip() for p in val.split(";") if p.strip()]
                if target_dir.lower() not in [p.lower() for p in win_parts]:
                    win_parts.append(target_dir)
                    winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, ";".join(win_parts))
            from config import broadcast_setting_change
            broadcast_setting_change()
            return True
        except Exception:
            return False

    home = os.path.expanduser("~")
    export_line = f'export PATH="{target_dir}:$PATH"\n'
    for rc in [os.path.join(home, ".bashrc"), os.path.join(home, ".zshrc"), os.path.join(home, ".profile")]:
        if os.path.exists(rc):
            try:
                with open(rc, "r", encoding="utf-8") as f:
                    content = f.read()
                if target_dir not in content:
                    with open(rc, "a", encoding="utf-8") as f:
                        f.write(f"\n{export_line}")
            except Exception:
                pass
    return True


def create_global_shim(name: str, target_exe: str) -> bool:
    target_exe = os.path.abspath(os.path.expanduser(os.path.expandvars(target_exe)))
    if not os.path.exists(target_exe):
        return False

    if is_windows():
        cmd_content = f'@echo off\n"{target_exe}" %*\n'
        win_dir = os.environ.get("SystemRoot", r"C:\Windows")
        shim_path = os.path.join(win_dir, f"{name}.cmd")
        try:
            with open(shim_path, "w", encoding="utf-8") as f:
                f.write(cmd_content)
            return True
        except (PermissionError, OSError):
            pass

        local_apps = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
        if os.path.isdir(local_apps):
            try:
                with open(os.path.join(local_apps, f"{name}.cmd"), "w", encoding="utf-8") as f:
                    f.write(cmd_content)
                return True
            except Exception:
                pass
        return False
    else:
        for bin_dir in [os.path.expanduser("~/.local/bin"), "/usr/local/bin"]:
            if os.path.isdir(bin_dir) and os.access(bin_dir, os.W_OK):
                link_path = os.path.join(bin_dir, name)
                try:
                    if os.path.exists(link_path) or os.path.islink(link_path):
                        os.remove(link_path)
                    os.symlink(target_exe, link_path)
                    return True
                except Exception:
                    pass
        return False


def detect_claude_code() -> Tuple[bool, Optional[str], Optional[str]]:
    candidates = (
        [r"%USERPROFILE%\.local\bin\claude.exe",
         r"%LOCALAPPDATA%\Microsoft\WinGet\Links\claude.exe",
         r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\claude.exe",
         r"%APPDATA%\npm\claude.cmd", r"C:\Program Files\nodejs\claude.cmd",
         r"%LOCALAPPDATA%\Programs\nodejs\claude.cmd"]
        if is_windows() else
        [os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/bin/claude"),
         "/usr/local/bin/claude", "/opt/homebrew/bin/claude"]
    )
    claude_exe = find_executable("claude.exe", candidates) or find_executable("claude", candidates)
    if not claude_exe:
        return False, None, None

    create_global_shim("claude", claude_exe)
    add_directory_to_path(os.path.dirname(claude_exe))

    try:
        res = subprocess.run(
            [claude_exe, "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15
        )
        if res.returncode == 0:
            return True, claude_exe, res.stdout.strip()
    except Exception:
        pass
    return True, claude_exe, "[Installed, version pending]"


def _has_winget() -> bool:
    return is_windows() and find_executable("winget.exe") is not None


def _has_brew() -> bool:
    return find_executable("brew") is not None


def _download_file(url: str, dest_path: str, timeout: int = 180) -> bool:
    curl_exe = shutil.which("curl.exe") or shutil.which("curl")
    if curl_exe:
        try:
            res = subprocess.run([curl_exe, "-fLo", dest_path, url], capture_output=True, timeout=timeout)
            if res.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000:
                return True
        except Exception:
            pass

    try:
        import urllib.request
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
        except Exception:
            pass
        req = urllib.request.Request(url, headers={"User-Agent": "Claude-OpenRouter-Setup/2.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000
    except Exception:
        pass
    return False


def install_nodejs() -> Tuple[bool, str]:
    if _has_winget():
        cmd = ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "--exact",
               "--accept-source-agreements", "--accept-package-agreements", "--silent"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                ok, path, ver = detect_nodejs()
                if ok and path:
                    create_global_shim("node", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Node.js installed successfully via winget ({ver})."
        except Exception:
            pass

    if is_macos() and _has_brew():
        try:
            res = subprocess.run(["brew", "install", "node"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                ok, path, ver = detect_nodejs()
                if ok:
                    return True, f"Node.js installed successfully via Homebrew ({ver})."
        except Exception:
            pass

    if is_linux():
        for pm, pm_args in [
            ("apt", ["sudo", "apt", "update", "-y", "&&", "sudo", "apt", "install", "-y", "nodejs", "npm"]),
            ("dnf", ["sudo", "dnf", "install", "-y", "nodejs", "npm"]),
            ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "nodejs", "npm"]),
        ]:
            if shutil.which(pm):
                try:
                    res = subprocess.run(" ".join(pm_args), shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
                    if res.returncode == 0:
                        ok, path, ver = detect_nodejs()
                        if ok:
                            return True, f"Node.js installed successfully via {pm} ({ver})."
                except Exception:
                    pass

    if is_windows():
        try:
            target_dir = os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs")
            os.makedirs(target_dir, exist_ok=True)
            zip_url = "https://nodejs.org/dist/v26.13.0/node-v26.13.0-win-x64.zip"
            temp_zip = os.path.join(tempfile.gettempdir(), "node-portable.zip")
            if _download_file(zip_url, temp_zip, timeout=180):
                with zipfile.ZipFile(temp_zip, "r") as z:
                    for member in z.infolist():
                        parts = member.filename.split("/", 1)
                        if len(parts) > 1 and parts[1]:
                            dest = os.path.join(target_dir, parts[1].replace("/", os.sep))
                            if member.is_dir():
                                os.makedirs(dest, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(dest), exist_ok=True)
                                with z.open(member) as src, open(dest, "wb") as dst:
                                    dst.write(src.read())
                if os.path.exists(temp_zip):
                    try:
                        os.remove(temp_zip)
                    except Exception:
                        pass
                add_directory_to_path(target_dir)
                ok, path, ver = detect_nodejs()
                if ok:
                    return True, f"Node.js portable installed successfully ({ver}) at {target_dir}."
        except Exception as e:
            return False, f"Failed portable Node.js installation: {e}"

    return False, "Could not install Node.js automatically. Please install Node.js LTS from https://nodejs.org."


def install_claude_code() -> Tuple[bool, str]:
    if is_windows():
        ps_cmd = 'irm https://claude.ai/install.ps1 | iex'
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
            )
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    create_global_shim("claude", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Claude Code installed via native installer ({ver}) at {path}."
        except Exception:
            pass
    else:
        sh_cmd = "curl -fsSL https://claude.ai/install.sh | bash"
        try:
            res = subprocess.run(sh_cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    return True, f"Claude Code installed via native script ({ver}) at {path}."
        except Exception:
            pass

    if _has_winget():
        cmd = ["winget", "install", "--id", "Anthropic.ClaudeCode", "--exact",
               "--accept-source-agreements", "--accept-package-agreements", "--silent"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    create_global_shim("claude", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Claude Code installed successfully via winget ({ver})."
        except Exception:
            pass

    npm_ok, npm_exe, _ = detect_npm()
    if npm_ok and npm_exe:
        cmd = [npm_exe, "install", "-g", "@anthropic-ai/claude-code"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                ok, path, ver = detect_claude_code()
                if ok and path:
                    create_global_shim("claude", path)
                    add_directory_to_path(os.path.dirname(path))
                    return True, f"Claude Code installed successfully via npm ({ver})."
        except Exception as e:
            return False, f"npm install failed: {e}"

    return False, "Failed to install Claude Code. Please run 'npm install -g @anthropic-ai/claude-code'."