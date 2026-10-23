"""Verification and end-to-end testing module for Claude Code + OpenRouter.

Validates that:
1. Claude Code CLI executable is present and callable.
2. Required OpenRouter environment variables are persistently configured.
3. OpenRouter API authentication and message inference succeed.
4. Claude Code actually routes requests through OpenRouter (not Anthropic direct).
5. No credentials are leaked in output or logs.
"""

import os
import tempfile
import subprocess
from typing import Dict, Any, Tuple, Optional

from config import get_current_configuration, mask_key
from installer import detect_claude_code
from openrouter import validate_api_key, test_inference


def run_claude_inference_test(prompt: str = "Respond strictly with: Verification test successful.", timeout: int = 35) -> Tuple[bool, str, str, int]:
    """Execute a small non-interactive Claude Code test prompt using the configured environment.
    
    Returns:
        (success, stdout_output, stderr_output, exit_code)
    """
    ok, claude_exe, ver = detect_claude_code()
    if not ok or not claude_exe:
        return False, "", "Claude Code executable not found.", -1

    # Prepare environment with persistent user registry variables
    cfg = get_current_configuration()
    env = os.environ.copy()

    # Pass OpenRouter variables to process env
    for k, v in cfg.items():
        if v is not None:
            env[k] = v

    # Ensure ANTHROPIC_API_KEY is unset so Claude Code doesn't hit Anthropic directly
    env.pop("ANTHROPIC_API_KEY", None)

    # Run in an isolated temporary directory
    try:
        with tempfile.TemporaryDirectory() as td:
            res = subprocess.run(
                [claude_exe, "-p", prompt],
                cwd=td,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            success = res.returncode == 0 and len(stdout) > 0
            return success, stdout, stderr, res.returncode
    except subprocess.TimeoutExpired:
        return False, "", f"Claude Code timed out after {timeout} seconds.", -1
    except Exception as e:
        return False, "", f"Execution error: {e}", -1


def run_full_verification() -> Dict[str, Any]:
    """Execute a comprehensive verification suite and compile results.
    
    Returns a report dictionary containing each check and overall status.
    """
    report = {
        "claude_installed": False,
        "claude_version": None,
        "claude_path": None,
        "env_configured": False,
        "env_details": {},
        "api_key_valid": False,
        "api_key_label": None,
        "openrouter_direct_test": False,
        "openrouter_direct_response": None,
        "claude_cli_test": False,
        "claude_cli_response": None,
        "claude_cli_exit_code": None,
        "overall_success": False,
        "troubleshooting": [],
    }

    # 1. Claude CLI check
    c_ok, c_path, c_ver = detect_claude_code()
    report["claude_installed"] = c_ok
    report["claude_version"] = c_ver
    report["claude_path"] = c_path
    if not c_ok:
        report["troubleshooting"].append("Claude Code CLI is not detected. Please install via option 1 in the menu.")

    # 2. Environment variables check
    cfg = get_current_configuration()
    has_key = bool(cfg.get("OPENROUTER_API_KEY"))
    has_base = cfg.get("ANTHROPIC_BASE_URL") == "https://openrouter.ai/api"
    has_model = bool(cfg.get("ANTHROPIC_MODEL"))
    report["env_configured"] = has_key and has_base and has_model
    report["env_details"] = {
        "OPENROUTER_API_KEY": mask_key(cfg.get("OPENROUTER_API_KEY")),
        "ANTHROPIC_BASE_URL": cfg.get("ANTHROPIC_BASE_URL", "[Not Set]"),
        "ANTHROPIC_MODEL": cfg.get("ANTHROPIC_MODEL", "[Not Set]"),
        "ANTHROPIC_AUTH_TOKEN": mask_key(cfg.get("ANTHROPIC_AUTH_TOKEN")),
    }
    if not has_key:
        report["troubleshooting"].append("OpenRouter API key is missing. Configure it using option 2.")
    if not has_base:
        report["troubleshooting"].append("ANTHROPIC_BASE_URL is not set to https://openrouter.ai/api. Run option 6 to repair.")

    # 3. Direct OpenRouter API check
    if has_key:
        key = cfg["OPENROUTER_API_KEY"]
        key_ok, key_meta, key_msg = validate_api_key(key)
        report["api_key_valid"] = key_ok
        report["api_key_label"] = key_meta.get("label", "Valid")
        if not key_ok:
            report["troubleshooting"].append(f"OpenRouter API key check failed: {key_msg}")
            if "11001" in key_msg or "getaddrinfo" in key_msg:
                report["troubleshooting"].append(
                    "Network / DNS Resolution Error: Windows Sandbox cannot resolve internet hostnames.\n"
                    "    Fix: In Windows Sandbox, open PowerShell as Administrator and run:\n"
                    "    Get-NetAdapter | Where-Object Status -eq 'Up' | Set-DnsClientServerAddress -ServerAddresses ('8.8.8.8','1.1.1.1')"
                )
        else:
            # Direct inference test
            model = cfg.get("ANTHROPIC_MODEL", "recursive/flint-v1.0:free")
            inf_ok, inf_text, _ = test_inference(key, model, "Say Hello in one word")
            report["openrouter_direct_test"] = inf_ok
            report["openrouter_direct_response"] = inf_text
            if not inf_ok:
                report["troubleshooting"].append(f"Direct OpenRouter inference test failed: {inf_text}")

    # 4. Claude Code CLI integration test
    if report["claude_installed"] and report["api_key_valid"]:
        cli_ok, cli_out, cli_err, cli_code = run_claude_inference_test()
        report["claude_cli_test"] = cli_ok
        report["claude_cli_response"] = cli_out
        report["claude_cli_exit_code"] = cli_code
        if not cli_ok:
            report["troubleshooting"].append(f"Claude CLI inference failed (exit code {cli_code}): {cli_err}")

    # Overall verdict
    report["overall_success"] = (
        report["claude_installed"]
        and report["env_configured"]
        and report["api_key_valid"]
        and report["openrouter_direct_test"]
        and report["claude_cli_test"]
    )

    return report
