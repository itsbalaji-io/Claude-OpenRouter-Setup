"""OpenRouter API client and validator for Claude Code integration.

Interacts with OpenRouter endpoints to:
1. Validate API keys (/api/v1/auth/key)
2. List and validate free and available models (/api/v1/models)
3. Test Anthropic-compatible message completions (/api/v1/messages)
"""

import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any

OPENROUTER_AUTH_URL = "https://openrouter.ai/api/v1/auth/key"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_MESSAGES_URL = "https://openrouter.ai/api/v1/messages"


def repair_windows_sandbox_dns() -> bool:
    """Attempt to configure Google DNS (8.8.8.8, 1.1.1.1) on active network adapters.
    
    Fixes the common Windows Sandbox / Hyper-V vEthernet DNS relay bug (Errno 11001).
    """
    import subprocess
    try:
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            "Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object Status -eq 'Up' | Set-DnsClientServerAddress -ServerAddresses ('8.8.8.8','1.1.1.1') -ErrorAction SilentlyContinue; Clear-DnsClientCache"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return res.returncode == 0
    except Exception:
        return False


def _get_ssl_context():
    """Create an SSL context using Windows System Root Certificates."""
    import ssl
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except Exception:
        pass
    return ctx


def _make_request(url: str, headers: Dict[str, str], data: Optional[bytes] = None, timeout: int = 15) -> Tuple[int, Any]:
    """Helper to perform HTTP requests using standard library urllib with automatic DNS recovery and Windows TLS validation."""
    req = urllib.request.Request(url, data=data, headers=headers)
    ssl_ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return e.code, parsed
    except urllib.error.URLError as e:
        err_str = str(e.reason)
        # Check for Windows Sandbox DNS failure (11001 getaddrinfo failed)
        if "11001" in err_str or "getaddrinfo" in err_str.lower():
            # Automatically try to repair Sandbox DNS and retry once
            if repair_windows_sandbox_dns():
                try:
                    with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                        body = resp.read().decode("utf-8", errors="replace")
                        try:
                            return resp.status, json.loads(body)
                        except json.JSONDecodeError:
                            return resp.status, body
                except Exception:
                    pass
            return 0, "DNS resolution failed ([Errno 11001] getaddrinfo failed): Could not resolve openrouter.ai. In Windows Sandbox, DNS relay often fails; ensure Sandbox has internet and DNS is configured to 8.8.8.8."
        return 0, err_str
    except Exception as e:
        return 0, str(e)


def validate_api_key(api_key: str) -> Tuple[bool, Dict[str, Any], str]:
    """Validate the OpenRouter API key using /api/v1/auth/key.
    
    Returns:
        (is_valid, key_metadata, message)
    """
    clean_key = api_key.strip()
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
        "User-Agent": "Claude-OpenRouter-Setup/1.0",
    }

    status, payload = _make_request(OPENROUTER_AUTH_URL, headers)
    if status == 200 and isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        label = data.get("label", "Valid Key")
        free_reqs = data.get("free_model_daily_requests", {})
        remaining = free_reqs.get("remaining", "N/A")
        msg = f"Key verified successfully. Label: {label} | Free requests remaining today: {remaining}"
        return True, data, msg
    elif status == 401:
        return False, {}, "Authentication failed: Invalid OpenRouter API key."
    else:
        err = payload if isinstance(payload, str) else json.dumps(payload)
        return False, {}, f"OpenRouter API error (HTTP {status}): {err}"


def fetch_models(free_only: bool = True) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Fetch model catalogue from OpenRouter.
    
    Returns:
        (success, models_list, error_or_info_message)
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Claude-OpenRouter-Setup/1.0",
    }
    status, payload = _make_request(OPENROUTER_MODELS_URL, headers, timeout=20)
    if status == 200 and isinstance(payload, dict) and "data" in payload:
        models = payload["data"]
        if free_only:
            models = [
                m for m in models
                if m.get("id", "").endswith(":free") or ":free" in m.get("id", "")
            ]
        return True, models, f"Fetched {len(models)} models."
    return False, [], f"Failed to retrieve models (HTTP {status}): {payload}"


def validate_model(model_id: str, free_only: bool = True) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Check if the given model exists on OpenRouter and extract its specs.
    
    Returns:
        (is_valid, model_dict, status_message)
    """
    clean_id = model_id.strip()
    success, models, msg = fetch_models(free_only=free_only)
    if not success:
        return False, None, f"Could not verify model catalogue: {msg}"

    for m in models:
        if m.get("id") == clean_id:
            context_len = m.get("context_length", 200000)
            supports_tools = "tools" in m.get("supported_parameters", [])
            info = f"Model found: {clean_id} | Context: {context_len} tokens | Tools supported: {supports_tools}"
            return True, m, info

    # If free_only was True and not found, check if it exists in non-free catalogue
    if free_only:
        all_ok, all_models, _ = fetch_models(free_only=False)
        if all_ok:
            for m in all_models:
                if m.get("id") == clean_id:
                    return False, m, f"Model '{clean_id}' exists on OpenRouter but is NOT a free tier model."

    return False, None, f"Model '{clean_id}' not found in current OpenRouter catalogue."


def test_inference(api_key: str, model_id: str, prompt: str = "Say hello in one word") -> Tuple[bool, str, Dict[str, Any]]:
    """Perform a minimal test inference call against OpenRouter's Anthropic endpoint (/api/v1/messages).
    
    Returns:
        (success, response_text, full_response_payload)
    """
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "x-api-key": api_key.strip(),
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "User-Agent": "Claude-OpenRouter-Setup/1.0",
    }
    payload = {
        "model": model_id.strip(),
        "max_tokens": 200,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    status, res = _make_request(OPENROUTER_MESSAGES_URL, headers, data=data, timeout=30)
    if status == 200 and isinstance(res, dict):
        text = ""
        thinking = ""
        for block in res.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "thinking":
                thinking += block.get("thinking", "")
        output = text.strip() if text.strip() else (f"[Reasoning output generated: {thinking[:60]}...]" if thinking else "[Response received]")
        return True, output, res
    err_msg = res if isinstance(res, str) else json.dumps(res)
    return False, f"Inference failed (HTTP {status}): {err_msg}", res if isinstance(res, dict) else {}
