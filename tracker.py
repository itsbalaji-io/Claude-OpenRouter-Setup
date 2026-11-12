"""Token Usage & Credit Tracker for Claude Code + OpenRouter.

Provides:
1. Live OpenRouter account balance, credit usage, and rate limits via /api/v1/auth/key
2. Local session inference event logging and token usage telemetry
3. Aggregate statistics and budget inspection
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

from openrouter import _make_request, OPENROUTER_AUTH_URL

USAGE_FILE = os.path.expanduser(os.path.join("~", ".claude_openrouter_usage.json"))


def fetch_openrouter_account_stats(api_key: str) -> Tuple[bool, Dict[str, Any], str]:
    """Query OpenRouter auth endpoint to retrieve live credit limit and usage details.
    
    Returns:
        (success, stats_dict, message)
    """
    clean_key = api_key.strip()
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
        "User-Agent": "Claude-OpenRouter-Setup/2.0",
    }
    status, payload = _make_request(OPENROUTER_AUTH_URL, headers, timeout=12)

    if status == 200 and isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        stats = {
            "label": data.get("label", "Default Key"),
            "usage": float(data.get("usage", 0.0)),
            "limit": float(data.get("limit", 0.0)) if data.get("limit") is not None else None,
            "is_free_tier": bool(data.get("is_free_tier", False)),
            "rate_limit_requests": data.get("rate_limit", {}).get("requests") if isinstance(data.get("rate_limit"), dict) else None,
            "rate_limit_interval": data.get("rate_limit", {}).get("interval") if isinstance(data.get("rate_limit"), dict) else None,
        }
        return True, stats, "Successfully retrieved OpenRouter account stats."

    err_msg = "Failed to query OpenRouter account endpoint."
    if isinstance(payload, dict) and "error" in payload:
        err = payload["error"]
        err_msg = err.get("message", err_msg) if isinstance(err, dict) else str(err)
    elif isinstance(payload, str) and payload:
        err_msg = payload
    return False, {}, err_msg


def load_local_usage_log() -> Dict[str, Any]:
    """Load local usage tracking file from disk."""
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "events" in data:
                    return data
        except Exception:
            pass

    return {
        "total_requests": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "events": [],
    }


def record_usage_event(
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost: float = 0.0,
    latency_ms: int = 0,
    success: bool = True,
) -> None:
    """Log an inference event locally with timestamp and token metrics."""
    data = load_local_usage_log()
    data["total_requests"] = data.get("total_requests", 0) + 1
    data["total_prompt_tokens"] = data.get("total_prompt_tokens", 0) + prompt_tokens
    data["total_completion_tokens"] = data.get("total_completion_tokens", 0) + completion_tokens

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": cost,
        "latency_ms": latency_ms,
        "success": success,
    }

    events: List[Dict[str, Any]] = data.get("events", [])
    events.append(event)
    # Keep only the last 500 events to prevent file bloating
    if len(events) > 500:
        events = events[-500:]
    data["events"] = events

    try:
        os.makedirs(os.path.dirname(os.path.abspath(USAGE_FILE)), exist_ok=True)
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_local_usage_summary() -> Dict[str, Any]:
    """Aggregate local usage metrics into a clean summary dictionary."""
    data = load_local_usage_log()
    events = data.get("events", [])
    total_tokens = data.get("total_prompt_tokens", 0) + data.get("total_completion_tokens", 0)

    model_counts: Dict[str, int] = {}
    for ev in events:
        m = ev.get("model", "unknown")
        model_counts[m] = model_counts.get(m, 0) + 1

    return {
        "total_requests": data.get("total_requests", 0),
        "total_prompt_tokens": data.get("total_prompt_tokens", 0),
        "total_completion_tokens": data.get("total_completion_tokens", 0),
        "total_tokens": total_tokens,
        "recent_event_count": len(events),
        "model_breakdown": model_counts,
    }


def clear_local_usage() -> None:
    """Reset the local usage log."""
    empty = {
        "total_requests": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "events": [],
    }
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(empty, f, indent=2)
    except Exception:
        pass
