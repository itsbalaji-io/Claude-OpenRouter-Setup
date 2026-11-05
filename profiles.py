"""Profiles and Session Management for Claude Code + OpenRouter.

Allows creating, saving, switching, and deleting multi-model profiles
with tailored context window presets, model IDs, and descriptions.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple

PROFILES_FILE = os.path.expanduser(os.path.join("~", ".claude_openrouter_profiles.json"))

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "flint-free": {
        "model": "recursive/flint-v1.0:free",
        "context_tokens": 262144,
        "description": "Default free fast model on OpenRouter (262k context)",
    },
    "claude-3-7-sonnet": {
        "model": "anthropic/claude-3.7-sonnet",
        "context_tokens": 200000,
        "description": "Anthropic Claude 3.7 Sonnet (Hybrid Reasoning, 200k context)",
    },
    "claude-3-5-sonnet": {
        "model": "anthropic/claude-3.5-sonnet",
        "context_tokens": 200000,
        "description": "Anthropic Claude 3.5 Sonnet (Premier coding model, 200k context)",
    },
    "deepseek-r1": {
        "model": "deepseek/deepseek-r1",
        "context_tokens": 163840,
        "description": "DeepSeek R1 full reasoning model (163k context)",
    },
    "deepseek-chat": {
        "model": "deepseek/deepseek-chat",
        "context_tokens": 163840,
        "description": "DeepSeek V3 general chat & coding (163k context)",
    },
    "deepseek-r1-free": {
        "model": "deepseek/deepseek-r1:free",
        "context_tokens": 163840,
        "description": "DeepSeek R1 Free Tier community router",
    },
    "gemini-2-flash": {
        "model": "google/gemini-2.0-flash-001",
        "context_tokens": 1000000,
        "description": "Google Gemini 2.0 Flash (Ultra fast 1M context)",
    },
    "llama-3-3-70b": {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "context_tokens": 131072,
        "description": "Meta Llama 3.3 70B Instruct open weights (131k context)",
    },
    "qwen-2-5-coder": {
        "model": "qwen/qwen-2.5-coder-32b-instruct",
        "context_tokens": 131072,
        "description": "Qwen 2.5 Coder 32B Instruct (131k context)",
    },
}

CONTEXT_PRESETS = [
    (32768, "32k (Compact / Budget)"),
    (65536, "64k (Standard CLI)"),
    (131072, "128k (Large Codebases)"),
    (163840, "163k (DeepSeek Standard)"),
    (200000, "200k (Claude 3.5/3.7 Native)"),
    (262144, "262k (Recursive Flint Default)"),
    (1000000, "1M (Gemini 2.0 Extended)"),
]


def load_profiles_data() -> Dict[str, Any]:
    """Load profile database from disk, populating default presets if missing."""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "profiles" in data:
                    return data
        except Exception:
            pass

    # Initialize with default presets
    initial_data: Dict[str, Any] = {
        "active_profile": "flint-free",
        "profiles": dict(DEFAULT_PRESETS),
    }
    save_profiles_data(initial_data)
    return initial_data


def save_profiles_data(data: Dict[str, Any]) -> None:
    """Save profile dictionary to JSON storage safely."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(PROFILES_FILE)), exist_ok=True)
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def list_profiles() -> List[Dict[str, Any]]:
    """Return an ordered list of profile items with active indicator."""
    data = load_profiles_data()
    active = data.get("active_profile", "flint-free")
    result = []
    for name, p in data.get("profiles", {}).items():
        item = dict(p)
        item["name"] = name
        item["is_active"] = (name == active)
        result.append(item)
    return result


def get_active_profile() -> Tuple[str, Dict[str, Any]]:
    """Return the name and dict of the currently active profile."""
    data = load_profiles_data()
    active_name = data.get("active_profile", "flint-free")
    profiles = data.get("profiles", {})
    if active_name not in profiles:
        active_name = next(iter(profiles.keys()), "flint-free")
        data["active_profile"] = active_name
        save_profiles_data(data)
    return active_name, profiles.get(active_name, DEFAULT_PRESETS["flint-free"])


def set_active_profile(name: str) -> Tuple[bool, str]:
    """Set the active profile and apply changes to environment variables."""
    from config import update_model, update_api_key

    data = load_profiles_data()
    profiles = data.get("profiles", {})
    if name not in profiles:
        return False, f"Profile '{name}' does not exist."

    prof = profiles[name]
    data["active_profile"] = name
    save_profiles_data(data)

    # Apply model & context tokens to user environment
    model = prof.get("model", "recursive/flint-v1.0:free")
    ctx = prof.get("context_tokens", 262144)
    update_model(model, context_tokens=ctx)

    # If profile carries a dedicated API key override, apply it
    if prof.get("api_key"):
        update_api_key(prof["api_key"])

    return True, f"Switched active profile to '{name}' ({model}, {ctx} tokens)."


def create_or_update_profile(
    name: str,
    model: str,
    context_tokens: int,
    description: str = "",
    api_key: Optional[str] = None,
    activate: bool = True,
) -> Tuple[bool, str]:
    """Create a new profile or update existing one."""
    clean_name = name.strip().lower().replace(" ", "-")
    if not clean_name:
        return False, "Profile name cannot be empty."

    data = load_profiles_data()
    prof_entry: Dict[str, Any] = {
        "model": model.strip(),
        "context_tokens": int(context_tokens),
        "description": description.strip(),
    }
    if api_key and api_key.strip():
        prof_entry["api_key"] = api_key.strip()

    data["profiles"][clean_name] = prof_entry

    if activate:
        data["active_profile"] = clean_name
        save_profiles_data(data)
        from config import update_model, update_api_key
        update_model(prof_entry["model"], context_tokens=prof_entry["context_tokens"])
        if api_key and api_key.strip():
            update_api_key(api_key.strip())
        return True, f"Profile '{clean_name}' created and activated successfully."

    save_profiles_data(data)
    return True, f"Profile '{clean_name}' saved successfully."


def delete_profile(name: str) -> Tuple[bool, str]:
    """Delete a profile if it's not the only remaining profile."""
    data = load_profiles_data()
    profiles = data.get("profiles", {})
    if name not in profiles:
        return False, f"Profile '{name}' not found."
    if len(profiles) <= 1:
        return False, "Cannot delete the last remaining profile."

    del profiles[name]
    if data.get("active_profile") == name:
        new_active = next(iter(profiles.keys()))
        data["active_profile"] = new_active
        set_active_profile(new_active)

    save_profiles_data(data)
    return True, f"Profile '{name}' removed."
