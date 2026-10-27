"""Configuration and environment variable management for Claude Code + OpenRouter on Windows.

Manages persistent Windows User-level environment variables in HKCU\\Environment,
broadcasts WM_SETTINGCHANGE, and safeguards API keys from accidental disclosure.
"""

import os
import sys
import winreg
import ctypes
import subprocess
from typing import Dict, Optional, Tuple

ENV_REG_PATH = r"Environment"
ANTHROPIC_BASE_URL = "https://openrouter.ai/api/v1"
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
    """Mask sensitive API keys or tokens for safe display.
    
    Example: 'sk-or-v1-a844b...06ebe'
    Never returns the full key.
    """
    if not key:
        return "[Not Set]"
    k_len = len(key)
    if k_len <= 12:
        return "***"
    prefix = key[:10]
    suffix = key[-5:]
    return f"{prefix}...{suffix} (length: {k_len})"


def get_clipboard_text() -> Optional[str]:
    """Read plain text from the Windows Clipboard safely out-of-process."""
    if sys.platform != "win32":
        return None
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
        if res.returncode == 0:
            val = res.stdout.strip()
            return val if val else None
    except Exception:
        pass
    return None


def clean_api_key(key: Optional[str]) -> str:
    """Sanitize API key input by stripping quotes, whitespace, and non-printable control characters."""
    if not key:
        return ""
    clean = key.strip().strip('"').strip("'")
    clean = "".join(c for c in clean if c.isprintable()).strip()
    return clean


def validate_key_format(key: str) -> Tuple[bool, str]:
    """Validate the syntax of an OpenRouter API key without network call."""
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


def get_user_env_var(name: str) -> Optional[str]:
    """Read a single persistent user-level environment variable from HKCU\\Environment."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, name)
            return str(val)
    except (FileNotFoundError, OSError):
        return None


def set_user_env_var(name: str, value: str) -> None:
    """Write a persistent user-level environment variable to HKCU\\Environment
    and update the current process os.environ.
    """
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    os.environ[name] = value


def delete_user_env_var(name: str) -> bool:
    """Delete a user-level environment variable from HKCU\\Environment if it exists."""
    deleted = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
            deleted = True
    except (FileNotFoundError, OSError):
        pass
    os.environ.pop(name, None)
    return deleted


def broadcast_setting_change() -> None:
    """Broadcast WM_SETTINGCHANGE so Windows applications and Explorer detect environment changes."""
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_ulong()
    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def apply_openrouter_config(api_key: str, model: str, context_tokens: int = DEFAULT_CONTEXT_TOKENS) -> None:
    """Configure all required Windows user environment variables for Claude Code + OpenRouter.
    
    Maintains clean separation between credentials and model settings.
    """
    clean_key = api_key.strip()
    clean_model = model.strip()

    # 1. Credentials
    set_user_env_var("OPENROUTER_API_KEY", clean_key)
    set_user_env_var("ANTHROPIC_AUTH_TOKEN", clean_key)

    # 2. Base URL
    set_user_env_var("ANTHROPIC_BASE_URL", ANTHROPIC_BASE_URL)

    # 3. Model bindings
    set_user_env_var("OPENROUTER_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_HAIKU_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_SONNET_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_OPUS_MODEL", clean_model)

    # 4. Context tokens window
    set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(context_tokens))

    # 5. Clean up any conflicting direct ANTHROPIC_API_KEY from User environment
    delete_user_env_var("ANTHROPIC_API_KEY")

    # Broadcast changes to system
    broadcast_setting_change()


def update_model(model: str, context_tokens: Optional[int] = None) -> None:
    """Update only the model configuration without touching the API key."""
    clean_model = model.strip()
    set_user_env_var("OPENROUTER_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_HAIKU_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_SONNET_MODEL", clean_model)
    set_user_env_var("ANTHROPIC_DEFAULT_OPUS_MODEL", clean_model)
    if context_tokens:
        set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(context_tokens))
    broadcast_setting_change()


def update_api_key(api_key: str) -> None:
    """Update only the API key without changing model settings."""
    clean_key = api_key.strip()
    set_user_env_var("OPENROUTER_API_KEY", clean_key)
    set_user_env_var("ANTHROPIC_AUTH_TOKEN", clean_key)
    broadcast_setting_change()


def get_current_configuration() -> Dict[str, Optional[str]]:
    """Return current configuration values from the user environment registry."""
    cfg = {}
    for var in MANAGED_VARIABLES:
        cfg[var] = get_user_env_var(var)
    cfg["ANTHROPIC_API_KEY"] = get_user_env_var("ANTHROPIC_API_KEY")
    return cfg


def get_display_status() -> Dict[str, str]:
    """Return a dictionary of variable status formatted safely for display."""
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
    """Detect and repair inconsistent environment variables."""
    actions_taken = []
    current = get_current_configuration()

    # 1. Base URL check
    if current.get("ANTHROPIC_BASE_URL") != ANTHROPIC_BASE_URL:
        set_user_env_var("ANTHROPIC_BASE_URL", ANTHROPIC_BASE_URL)
        actions_taken.append(f"Fixed ANTHROPIC_BASE_URL -> {ANTHROPIC_BASE_URL}")

    # 2. Key sync check
    or_key = current.get("OPENROUTER_API_KEY")
    anth_token = current.get("ANTHROPIC_AUTH_TOKEN")
    if or_key and anth_token != or_key:
        set_user_env_var("ANTHROPIC_AUTH_TOKEN", or_key)
        actions_taken.append("Synchronized ANTHROPIC_AUTH_TOKEN to match OPENROUTER_API_KEY")
    elif anth_token and not or_key:
        set_user_env_var("OPENROUTER_API_KEY", anth_token)
        actions_taken.append("Restored OPENROUTER_API_KEY from ANTHROPIC_AUTH_TOKEN")

    # 3. Model sync check
    primary_model = current.get("OPENROUTER_MODEL") or current.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    for mvar in ("OPENROUTER_MODEL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL"):
        if current.get(mvar) != primary_model:
            set_user_env_var(mvar, primary_model)
            actions_taken.append(f"Standardized {mvar} -> {primary_model}")

    # 4. ANTHROPIC_API_KEY conflicting variable
    if current.get("ANTHROPIC_API_KEY") is not None:
        delete_user_env_var("ANTHROPIC_API_KEY")
        actions_taken.append("Removed conflicting ANTHROPIC_API_KEY from user environment")

    # 5. Context window
    if not current.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS"):
        set_user_env_var("CLAUDE_CODE_MAX_CONTEXT_TOKENS", str(DEFAULT_CONTEXT_TOKENS))
        actions_taken.append(f"Set CLAUDE_CODE_MAX_CONTEXT_TOKENS -> {DEFAULT_CONTEXT_TOKENS}")

    if actions_taken:
        broadcast_setting_change()

    return (len(actions_taken) > 0, actions_taken)
