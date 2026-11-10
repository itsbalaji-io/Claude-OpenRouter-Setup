"""Configuration and environment variable management for Claude Code + OpenRouter.

Supports:
- Windows: Persistent User-level environment in HKCU\Environment + WM_SETTINGCHANGE
- macOS / Linux: Persistent User-level environment in ~/.bashrc, ~/.zshrc, and ~/.profile
- Strict secret redaction across all platforms
"""

import os
import sys
import shutil
import subprocess
from typing import Dict, Optional, Tuple, List

ENV_REG_PATH = r"Environment"
ANTHROPIC_BASE_URL = "https://openrouter.ai/api"
DEFAULT_MODEL = "recursive/flint-v1.0:free"
DEFAULT_CONTEXT_TOKENS = 262144

MANAGED_VARIABLES = [
    "OPENROUTER_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENROUTER_MODEL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
]


def mask_key(key: Optional[str]) -> str:
    if not key:
        return "[Not Set]"
    k_len = len(key)
    if k_len <= 12:
        return "***"
    prefix = key[:10]
    suffix = key[-5:]
    return f"{prefix}...{suffix} (length: {k_len})"


def get_clipboard_text() -> Optional[str]:
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                return val if val else None
        except Exception:
            pass
        return None

    if sys.platform == "darwin":
        pbpaste = shutil.which("pbpaste")
        if pbpaste:
            try:
                res = subprocess.run([pbpaste], capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass

    if sys.platform.startswith("linux"):
        for tool, args in [("wl-paste", []), ("xclip", ["-selection", "clipboard", "-o"])]:
            exe = shutil.which(tool)
            if exe:
                try:
                    res = subprocess.run([exe] + args, capture_output=True, text=True, timeout=3)
                    if res.returncode == 0 and res.stdout.strip():
                        return res.stdout.strip()
                except Exception:
                    pass
    return None


def clean_api_key(key: Optional[str]) -> str:
    if not key:
        return ""
    clean = key.strip().strip('"').strip("'")
    clean = "".join(c for c in clean if c.isprintable()).strip()
    return clean


def validate_key_format(key: str) -> Tuple[bool, str]:
    if not key or not isinstance(key, str):
        return False, "API key cannot be empty."
    clean = clean_api_key(key)
    if not clean:
        return False, "API key cannot be empty."
    if not clean.startswith("sk-or-"):
        preview = clean[:6] if clean else "empty"
        return False, f"OpenRouter API keys must start with 'sk-or-' (received prefix: '{preview}...')."
    if len(clean) < 30:
        return False, f"API key is too short ({len(clean)} characters). Please ensure the full key is pasted."
    return True, "Key format is valid."


def _unix_rc_files() -> List[str]:
    home = os.path.expanduser("~")
    rc_candidates = [
        os.path.join(home, ".bashrc"),
        os.path.join(home, ".zshrc"),
        os.path.join(home, ".profile"),
    ]
    return [p for p in rc_candidates if os.path.exists(p)] or [os.path.join(home, ".bashrc")]


def get_user_env_var(name: str) -> Optional[str]:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, name)
                return str(val)
        except (FileNotFoundError, OSError, ImportError):
            pass
    return os.environ.get(name)


def set_user_env_var(name: str, value: str) -> None:
    os.environ[name] = value

    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            return
        except Exception:
            pass

    export_marker = f"export {name}="
    export_line = f'export {name}="{value}"\n'
    for rc in _unix_rc_files():
        lines = []
        if os.path.exists(rc):
            try:
                with open(rc, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                pass

        replaced = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(export_marker):
                new_lines.append(export_line)
                replaced = True
            else:
                new_lines.append(line)

        if not replaced:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(export_line)

        try:
            with open(rc, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            pass


def delete_user_env_var(name: str) -> bool:
    deleted = False
    os.environ.pop(name, None)

    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
                deleted = True
        except (FileNotFoundError, OSError, ImportError):
            pass
        return deleted

    export_marker = f"export {name}="
    for rc in _unix_rc_files():
        if not os.path.exists(rc):
            continue
        try:
            with open(rc, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = [l for l in lines if not l.strip().startswith(export_marker)]
            if len(new_lines) != len(lines):
                with open(rc, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                deleted = True
        except Exception:
            pass
    return deleted


def broadcast_setting_change() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
            SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
        )
    except Exception:
        pass


def apply_openrouter_config(api_key: str, model: str, context_tokens: int = DEFAULT_CONTEXT_TOKENS) -> None:
    clean_key = api_key.strip()
    clean_model = model.strip()

    set_user_env_var("OPENROUTER_API_KEY", clean_key)
    set_user_env_var("ANTHROPIC_AUTH_TOKEN", clean_key)
    set_user_env_var("ANTHROPIC_BASE_URL", ANTHROPIC_BASE_URL)
    set_user_env_var("OPENROUTER_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_HAIKU_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_SONNET_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_OPUS_MODEL", clean_model)
    set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(context_tokens))
    delete_user_env_var("ANTHROPIC_API_KEY")
    broadcast_setting_change()


def update_model(model: str, context_tokens: Optional[int] = None) -> None:
    clean_model = model.strip()
    for var in ("OPENROUTER_MODEL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"):
        set_user_env_var(var, clean_model)
    if context_tokens:
        set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(context_tokens))
    broadcast_setting_change()


def update_api_key(api_key: str) -> None:
    clean_key = api_key.strip()
    set_user_env_var("OPENROUTER_API_KEY", clean_key)
    set_user_env_var("ANTHROPIC_AUTH_TOKEN", clean_key)
    broadcast_setting_change()


def get_current_configuration() -> Dict[str, Optional[str]]:
    cfg = {}
    for var in MANAGED_VARIABLES:
        cfg[var] = get_user_env_var(var)
    cfg["ANTHROPIC_API_KEY"] = get_user_env_var("ANTHROPIC_API_KEY")
    return cfg


def get_display_status() -> Dict[str, str]:
    raw = get_current_configuration()
    display = {}
    for k, v in raw.items():
        if k in ("OPENROUTER_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            display[k] = mask_key(v)
        elif k == "ANTHROPIC_API_KEY":
            display[k] = "[Cleared / Not Present] (Correct for OpenRouter routing)" if v is None else f"[Warning: Present = {v[:4]}... Should be cleared!]"
        else:
            display[k] = v if v is not None else "[Not Set]"
    return display


def repair_environment() -> Tuple[bool, list]:
    actions_taken = []
    current = get_current_configuration()

    if current.get("ANTHROPIC_BASE_URL") != ANTHROPIC_BASE_URL:
        set_user_env_var("ANTHROPIC_BASE_URL", ANTHROPIC_BASE_URL)
        actions_taken.append(f"Fixed ANTHROPIC_BASE_URL -> {ANTHROPIC_BASE_URL}")

    or_key = current.get("OPENROUTER_API_KEY")
    anth_token = current.get("ANTHROPIC_AUTH_TOKEN")
    if or_key and anth_token != or_key:
        set_user_env_var("ANTHROPIC_AUTH_TOKEN", or_key)
        actions_taken.append("Synchronized ANTHROPIC_AUTH_TOKEN to match OPENROUTER_API_KEY")
    elif anth_token and not or_key:
        set_user_env_var("OPENROUTER_API_KEY", anth_token)
        actions_taken.append("Restored OPENROUTER_API_KEY from ANTHROPIC_AUTH_TOKEN")

    primary_model = current.get("OPENROUTER_MODEL") or current.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    model_vars = ("OPENROUTER_MODEL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                  "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL")
    for mvar in model_vars:
        if current.get(mvar) != primary_model:
            set_user_env_var(mvar, primary_model)
            actions_taken.append(f"Standardized {mvar} -> {primary_model}")

    if current.get("ANTHROPIC_API_KEY") is not None:
        delete_user_env_var("ANTHROPIC_API_KEY")
        actions_taken.append("Removed conflicting ANTHROPIC_API_KEY from user environment")

    if not current.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS"):
        set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(DEFAULT_CONTEXT_TOKENS))
        actions_taken.append(f"Set CLAUDE_CODE_MAX_CONTEXT_TOKENS -> {DEFAULT_CONTEXT_TOKENS}")

    if actions_taken:
        broadcast_setting_change()

    return (len(actions_taken) > 0, actions_taken)