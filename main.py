"""Claude CLI + OpenRouter Automated Windows Setup Tool

Interactive setup and configuration application for running Claude Code CLI
with OpenRouter as the API provider on Windows.
"""

import sys
import os
import getpass
import argparse
from typing import Optional

# Ensure the project root is always in sys.path (especially for embeddable Python runtimes)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config import (
    mask_key,
    clean_api_key,
    get_clipboard_text,
    validate_key_format,
    apply_openrouter_config,
    update_model,
    update_api_key,
    get_display_status,
    repair_environment,
    get_current_configuration,
    DEFAULT_MODEL,
    DEFAULT_CONTEXT_TOKENS,
)
from installer import (
    is_windows,
    is_admin,
    get_windows_info,
    get_powershell_version,
    detect_python,
    detect_nodejs,
    detect_npm,
    detect_claude_code,
    install_nodejs,
    install_claude_code,
)
from openrouter import (
    validate_api_key,
    fetch_models,
    validate_model,
    test_inference,
)
from verifier import run_full_verification, run_claude_inference_test


def print_banner():
    print("=" * 66)
    print("      Claude CLI + OpenRouter Automated Windows Setup Tool")
    print("=" * 66)


def print_system_diagnostics():
    """Display OS, Python, and prerequisites diagnostics."""
    print("\n--- System Diagnostics ---")
    if not is_windows():
        print("[!] Warning: This tool is designed specifically for Windows.")
    win = get_windows_info()
    ps_ver = get_powershell_version() or "Not detected"
    admin = is_admin()

    print(f"  OS Platform:        {win['platform']}")
    print(f"  PowerShell Version: {ps_ver}")
    print(f"  Admin Privileges:   {'Yes (Elevated)' if admin else 'No (Standard User)'}")

    py_ok, py_ver = detect_python()
    print(f"  Python Runtime:     {py_ver} ({'PASS: >=3.10' if py_ok else 'FAIL: Python 3.10+ required'})")

    node_ok, node_path, node_ver = detect_nodejs()
    if node_ok:
        print(f"  Node.js:            {node_ver} ({node_path})")
    else:
        print("  Node.js:            [Not Installed]")

    npm_ok, npm_path, npm_ver = detect_npm()
    if npm_ok:
        print(f"  npm:                {npm_ver} ({npm_path})")
    else:
        print("  npm:                [Not Installed]")

    claude_ok, claude_path, claude_ver = detect_claude_code()
    if claude_ok:
        print(f"  Claude Code CLI:    {claude_ver} ({claude_path})")
    else:
        print("  Claude Code CLI:    [Not Installed]")
    print("-" * 26)


def menu_install_or_repair_claude():
    """Option 1: Install or repair Node.js and Claude Code."""
    print("\n[+] Checking prerequisites for Claude Code...")
    node_ok, _, _ = detect_nodejs()
    if not node_ok:
        print("[-] Node.js is not installed. Installing Node.js LTS via winget...")
        success, msg = install_nodejs()
        print(f"    {msg}")
        if not success:
            print("[!] Could not automatically install Node.js. Please install manually from https://nodejs.org/")
            return
    else:
        print("[+] Node.js is already installed.")

    claude_ok, claude_path, claude_ver = detect_claude_code()
    if claude_ok:
        print(f"[+] Claude Code is already installed: {claude_ver} at {claude_path}")
        reinstall = input("    Do you want to repair/reinstall Claude Code? (y/N): ").strip().lower()
        if reinstall != "y":
            return

    print("[-] Installing/Repairing Claude Code CLI...")
    success, msg = install_claude_code()
    print(f"    {msg}")
    if success:
        print("[+] Claude Code installation completed successfully.")
        print("[i] Note: Newly opened terminal sessions will have 'claude' immediately in PATH.")


def prompt_user_api_key() -> Optional[str]:
    """Smart and reliable API key prompt supporting clipboard detection, Ctrl+V, and right-click paste."""
    # 1. Check if a valid OpenRouter key is already in the Windows Clipboard
    clip_text = get_clipboard_text()
    if clip_text:
        candidate = clean_api_key(clip_text)
        if candidate.startswith("sk-or-") and len(candidate) > 25:
            print(f"\n[+] Detected OpenRouter key in Windows Clipboard: {mask_key(candidate)}")
            use_clip = input("    Press Enter to use this key (or type 'n' to enter manually): ").strip().lower()
            if use_clip != "n":
                return candidate

    # 2. Direct visible input so pasting works with Ctrl+V or right-click
    print("\n    Please paste your OpenRouter API Key below.")
    print("    (You can use Ctrl+V or Right-Click to paste):")
    raw_key = input("    API Key (sk-or-...): ")

    cleaned = clean_api_key(raw_key)
    return cleaned if cleaned else None


def menu_configure_api_key():
    """Option 2: Configure OpenRouter API key securely."""
    print("\n[+] Configure OpenRouter API Key")
    print("    Your key will be validated against OpenRouter and stored as a persistent")
    print("    Windows User environment variable (HKCU\\Environment).")

    key = prompt_user_api_key()
    if not key:
        print("[-] API key cannot be empty. Aborted.")
        return

    valid_format, fmt_msg = validate_key_format(key)
    if not valid_format:
        print(f"[-] Invalid format: {fmt_msg}")
        return

    print(f"\n[-] Validating API key: {mask_key(key)}...")
    is_valid, meta, msg = validate_api_key(key)
    if not is_valid:
        print(f"[-] Validation failed: {msg}")
        override = input("    Save key anyway? (y/N): ").strip().lower()
        if override != "y":
            return
    else:
        print(f"[+] {msg}")

    update_api_key(key)
    print(f"[+] API key saved successfully: {mask_key(key)}")
    print("[i] Configured in persistent user variables: OPENROUTER_API_KEY & ANTHROPIC_AUTH_TOKEN.")


def menu_change_model():
    """Option 3: Change the configured OpenRouter model."""
    print("\n[+] Change OpenRouter Model")
    cfg = get_current_configuration()
    current_model = cfg.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    print(f"    Currently configured model: {current_model}")

    print("\n[-] Fetching available free models from OpenRouter...")
    ok, models, _ = fetch_models(free_only=True)
    if ok and models:
        print("\n    Available Free Models on OpenRouter:")
        for idx, m in enumerate(models[:12], 1):
            m_id = m.get("id")
            c_len = m.get("context_length", "N/A")
            marker = " (CURRENT)" if m_id == current_model else ""
            print(f"      {idx}. {m_id} [Context: {c_len}]{marker}")
    else:
        print("    [!] Could not fetch live models catalog. You can still enter a model identifier manually.")

    choice = input(f"\n    Enter model number (1-{min(len(models), 12) if ok and models else 0}) or full model ID [default: {DEFAULT_MODEL}]: ").strip()

    selected_model = DEFAULT_MODEL
    context_tokens = DEFAULT_CONTEXT_TOKENS

    if choice.isdigit() and ok and models and 1 <= int(choice) <= len(models):
        selected_m = models[int(choice) - 1]
        selected_model = selected_m.get("id")
        context_tokens = selected_m.get("context_length", DEFAULT_CONTEXT_TOKENS)
    elif choice:
        selected_model = choice
        # Try validating
        v_ok, v_meta, v_msg = validate_model(selected_model, free_only=False)
        if v_ok and v_meta:
            print(f"[+] {v_msg}")
            context_tokens = v_meta.get("context_length", DEFAULT_CONTEXT_TOKENS)
        else:
            print(f"[!] Warning: {v_msg}")
            cont = input("    Proceed with this model anyway? (Y/n): ").strip().lower()
            if cont == "n":
                return
    else:
        selected_model = current_model or DEFAULT_MODEL

    update_model(selected_model, context_tokens)
    print(f"[+] Model updated to: {selected_model}")
    print(f"[+] Context window set to: {context_tokens} tokens (CLAUDE_CODE_MAX_CONTEXT_TOKENS)")


def menu_test_connection():
    """Option 4: Test OpenRouter connection and Claude CLI execution."""
    print("\n[+] Running Connection & Verification Suite...")
    report = run_full_verification()

    print("\n--- Test Report ---")
    print(f"  1. Claude Code CLI:       {'PASS' if report['claude_installed'] else 'FAIL'} ({report['claude_version']})")
    print(f"  2. Environment Config:    {'PASS' if report['env_configured'] else 'FAIL'}")
    print(f"  3. OpenRouter Key Auth:   {'PASS' if report['api_key_valid'] else 'FAIL'} ({report['api_key_label']})")
    print(f"  4. Direct Inference Test: {'PASS' if report['openrouter_direct_test'] else 'FAIL'} -> \"{report['openrouter_direct_response']}\"")
    print(f"  5. Claude CLI Integration:{'PASS' if report['claude_cli_test'] else 'FAIL'} -> \"{report['claude_cli_response']}\"")
    print("-" * 19)

    if report["overall_success"]:
        print("\n[SUCCESS] Claude Code is fully configured and operational with OpenRouter!")
    else:
        print("\n[FAILED] One or more verification checks failed.")
        if report["troubleshooting"]:
            print("\nTroubleshooting Suggestions:")
            for item in report["troubleshooting"]:
                print(f"  - {item}")


def menu_display_status():
    """Option 5: Display configuration status (secrets redacted)."""
    print("\n--- Current Configuration Status ---")
    status = get_display_status()
    for k, v in status.items():
        print(f"  {k:<32}: {v}")
    print("-" * 36)
    print("[i] Secret keys are masked for security and never displayed in full.")
    print("[i] Open a fresh PowerShell terminal for changes to be active in your interactive shell.")


def menu_repair_env():
    """Option 6: Repair environment variables and network DNS."""
    print("\n[+] Checking and repairing environment configuration...")
    repaired, actions = repair_environment()
    if repaired:
        print("[+] Completed the following repairs:")
        for a in actions:
            print(f"    - {a}")
    else:
        print("[+] All environment variables are consistent.")

    # Network / DNS check
    print("\n[-] Checking internet connectivity & DNS resolution (openrouter.ai)...")
    import socket
    try:
        ip = socket.gethostbyname("openrouter.ai")
        print(f"[+] DNS check passed: openrouter.ai -> {ip}")
    except socket.gaierror:
        print("[-] DNS resolution failed for openrouter.ai ([Errno 11001]).")
        print("[-] Attempting automatic DNS repair for Windows Sandbox / Hyper-V...")
        from openrouter import repair_windows_sandbox_dns
        if repair_windows_sandbox_dns():
            try:
                ip = socket.gethostbyname("openrouter.ai")
                print(f"[+] DNS repaired successfully: openrouter.ai -> {ip}")
            except Exception:
                print("[!] DNS repair attempted, but openrouter.ai is still unreachable. Check host internet or VPN.")
        else:
            print("[!] Could not auto-configure DNS. Run in Sandbox PowerShell as Administrator:")
            print("    Get-NetAdapter | Where-Object Status -eq 'Up' | Set-DnsClientServerAddress -ServerAddresses ('8.8.8.8','1.1.1.1')")


def run_full_guided_setup():
    """Option 0: Full guided initial setup."""
    print_banner()
    print_system_diagnostics()

    # Step 1: Install prerequisites
    print("\n[Step 1/5] Checking and Installing Prerequisites...")
    node_ok, node_p, node_v = detect_nodejs()
    if not node_ok:
        print("  Installing Node.js LTS and npm...")
        ok, msg = install_nodejs()
        print(f"  {msg}")
    else:
        print(f"  Node.js: {node_v} ({node_p})")

    claude_ok, claude_p, claude_v = detect_claude_code()
    if not claude_ok:
        print("  Installing Claude Code CLI...")
        ok, msg = install_claude_code()
        print(f"  {msg}")
    else:
        print(f"  Claude Code CLI: {claude_v} ({claude_p})")

    # Step 2: Configure API Key
    print("\n[Step 2/5] OpenRouter API Key Configuration...")
    cfg = get_current_configuration()
    existing_key = cfg.get("OPENROUTER_API_KEY")
    if existing_key:
        print(f"  Found existing API key: {mask_key(existing_key)}")
        change = input("  Do you want to use a different key? (y/N): ").strip().lower()
        if change == "y":
            menu_configure_api_key()
    else:
        menu_configure_api_key()

    # Step 3: Select Model
    print("\n[Step 3/5] OpenRouter Model Selection...")
    menu_change_model()

    # Step 4: Repair / Ensure env consistency
    print("\n[Step 4/5] Standardizing Environment Variables...")
    repair_environment()

    # Step 5: Verify
    print("\n[Step 5/5] End-to-End Verification...")
    menu_test_connection()


def interactive_menu():
    """Interactive console menu loop."""
    while True:
        print_banner()
        print("  0. Run Full Guided Setup (Recommended for first-time setup)")
        print("  1. Install or repair Claude Code")
        print("  2. Configure OpenRouter API key")
        print("  3. Change the model")
        print("  4. Test OpenRouter connection & inference")
        print("  5. Display configuration status (never reveals key)")
        print("  6. Repair environment variables")
        print("  7. Exit")
        print("=" * 66)

        choice = input("Select an option (0-7): ").strip()
        if choice == "0":
            run_full_guided_setup()
        elif choice == "1":
            menu_install_or_repair_claude()
        elif choice == "2":
            menu_configure_api_key()
        elif choice == "3":
            menu_change_model()
        elif choice == "4":
            menu_test_connection()
        elif choice == "5":
            menu_display_status()
        elif choice == "6":
            menu_repair_env()
        elif choice in ("7", "q", "exit"):
            print("\nExiting. Thank you!")
            break
        else:
            print("\n[-] Invalid selection. Please enter a number from 0 to 7.")

        input("\nPress Enter to return to the menu...")


def ensure_dns_connectivity():
    """Verify and auto-fix DNS for Windows Sandbox / Hyper-V environments."""
    import socket
    try:
        socket.gethostbyname("openrouter.ai")
    except Exception:
        from openrouter import repair_windows_sandbox_dns
        repair_windows_sandbox_dns()


def main():
    parser = argparse.ArgumentParser(description="Claude CLI + OpenRouter Automated Windows Setup Tool")
    parser.add_argument("--full-setup", action="store_true", help="Run the full guided setup non-interactively where possible")
    parser.add_argument("--test", action="store_true", help="Run the verification suite and exit")
    parser.add_argument("--status", action="store_true", help="Display current configuration status and exit")
    args = parser.parse_args()

    # Automatically ensure DNS is functional (especially inside Windows Sandbox)
    ensure_dns_connectivity()

    if args.status:
        menu_display_status()
    elif args.test:
        menu_test_connection()
    elif args.full_setup:
        run_full_guided_setup()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
