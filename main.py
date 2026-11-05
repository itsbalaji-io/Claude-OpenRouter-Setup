"""Claude CLI + OpenRouter Automated Setup Tool.

Interactive terminal UI application for configuring Anthropic Claude Code CLI
with OpenRouter as the unified backend on Windows, macOS, and Linux.
"""

import sys
import os
import argparse
from typing import Optional, List, Dict, Any

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
    is_macos,
    is_linux,
    is_admin,
    get_system_info,
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
from profiles import (
    list_profiles,
    get_active_profile,
    set_active_profile,
    create_or_update_profile,
    delete_profile,
    CONTEXT_PRESETS,
)
from tracker import (
    fetch_openrouter_account_stats,
    get_local_usage_summary,
    clear_local_usage,
)
from tui import (
    Color,
    Spinner,
    print_banner,
    print_card,
    print_success,
    print_error,
    print_warn,
    print_info,
    menu_select,
    prompt_text,
    is_interactive,
)


def print_system_diagnostics():
    """Display OS, Python, and prerequisites diagnostics in a formatted card."""
    sys_info = get_system_info()
    ps_ver = get_powershell_version()
    admin = is_admin()

    py_ok, py_ver = detect_python()
    node_ok, node_path, node_ver = detect_nodejs()
    npm_ok, npm_path, npm_ver = detect_npm()
    claude_ok, claude_path, claude_ver = detect_claude_code()

    items = [
        ("Platform", f"{sys_info['system']} {sys_info['release']} ({sys_info['machine']})", "info"),
        ("Admin Privileges", "Yes (Elevated)" if admin else "No (Standard User)", "ok" if admin else "info"),
        ("Python Runtime", f"{py_ver}", "ok" if py_ok else "error"),
        ("Node.js LTS", f"{node_ver}" if node_ok else "[Not Installed]", "ok" if node_ok else "warn"),
        ("npm Package Mgr", f"{npm_ver}" if npm_ok else "[Not Installed]", "ok" if npm_ok else "warn"),
        ("Claude Code CLI", f"{claude_ver}" if claude_ok else "[Not Installed]", "ok" if claude_ok else "warn"),
    ]
    if ps_ver:
        items.insert(2, ("PowerShell", ps_ver, "info"))

    print_card("System Diagnostics", items)


def menu_install_or_repair_claude():
    """Option 1: Install or repair Node.js and Claude Code."""
    print_banner()
    print_info("Checking prerequisites for Claude Code CLI...")

    node_ok, node_path, node_ver = detect_nodejs()
    if not node_ok:
        print_warn("Node.js is not installed. Installing official Node.js LTS package...")
        with Spinner("Downloading and installing Node.js LTS..."):
            success, msg = install_nodejs()
        if success:
            print_success(msg)
        else:
            print_error(msg)
            return
    else:
        print_success(f"Node.js is available: {node_ver} ({node_path})")

    claude_ok, claude_path, claude_ver = detect_claude_code()
    if claude_ok:
        print_info(f"Claude Code is already detected: {claude_ver} at {claude_path}")
        reinstall = prompt_text("Reinstall or repair Claude Code? (y/N)", default="n").lower()
        if reinstall != "y":
            return

    print_info("Installing / repairing Anthropic Claude Code CLI...")
    with Spinner("Executing Claude Code installer..."):
        success, msg = install_claude_code()

    if success:
        print_success(msg)
        print_info("New shell sessions will recognize 'claude' immediately in PATH.")
    else:
        print_error(msg)


def prompt_user_api_key() -> Optional[str]:
    """Prompt for API key with clipboard auto-detection across OSes."""
    clip_text = get_clipboard_text()
    if clip_text:
        candidate = clean_api_key(clip_text)
        if candidate.startswith("sk-or-") and len(candidate) > 25:
            print_info(f"Detected OpenRouter API key in clipboard: {mask_key(candidate)}")
            use_clip = prompt_text("Press Enter to use clipboard key (or 'n' to enter manually)", default="y").lower()
            if use_clip != "n":
                return candidate

    print("\nPlease enter your OpenRouter API Key (sk-or-v1-...):")
    raw_key = input("  > ").strip()
    cleaned = clean_api_key(raw_key)
    return cleaned if cleaned else None


def menu_configure_api_key():
    """Option 2: Configure OpenRouter API key securely."""
    print_banner()
    print_info("Configure OpenRouter API Key")
    print("Your key is validated live and persistently registered in user environment.\n")

    key = prompt_user_api_key()
    if not key:
        print_error("API key cannot be empty. Operation cancelled.")
        return

    valid_format, fmt_msg = validate_key_format(key)
    if not valid_format:
        print_error(f"Invalid key syntax: {fmt_msg}")
        return

    with Spinner(f"Validating key against OpenRouter auth endpoint ({mask_key(key)})..."):
        is_valid, meta, msg = validate_api_key(key)

    if not is_valid:
        print_error(f"Validation failed: {msg}")
        override = prompt_text("Save key anyway? (y/N)", default="n").lower()
        if override != "y":
            return
    else:
        print_success(msg)

    update_api_key(key)
    print_success(f"Configured API key: {mask_key(key)}")
    print_info("Variables updated: OPENROUTER_API_KEY & ANTHROPIC_AUTH_TOKEN.")


def menu_profiles_and_models():
    """Option 3: Multi-model profile management and context presets."""
    while True:
        print_banner()
        active_name, active_prof = get_active_profile()
        profs = list_profiles()

        opts = []
        for p in profs:
            marker = " [ACTIVE]" if p.get("is_active") else ""
            opts.append({
                "title": f"{p['name']}{marker}",
                "desc": f"{p.get('model')} ({p.get('context_tokens', 200000)} tokens) - {p.get('description', '')}",
            })

        opts.append({"title": "➕ Create New Profile", "desc": "Define custom model, context window, and description"})
        opts.append({"title": "🗑️  Delete a Profile", "desc": "Remove an unwanted profile"})
        opts.append({"title": "↩  Back to Main Menu", "desc": "Return to the main setup menu"})

        choice = menu_select(
            title="🎭 Model Profiles & Context Presets",
            subtitle=f"Active Profile: {Color.CYAN}{active_name}{Color.RESET} ({active_prof.get('model')})",
            options=opts,
        )

        if choice is None or choice == len(opts) - 1:
            break

        # Delete profile
        if choice == len(opts) - 2:
            del_opts = [{"title": p["name"], "desc": p.get("model")} for p in profs if p["name"] != active_name]
            if not del_opts:
                print_warn("Cannot delete the active or sole profile.")
                input("\nPress Enter to continue...")
                continue
            del_opts.append({"title": "Cancel", "desc": ""})
            del_choice = menu_select("Select Profile to Delete", del_opts)
            if del_choice is not None and del_choice < len(del_opts) - 1:
                target = del_opts[del_choice]["title"]
                ok, msg = delete_profile(target)
                if ok:
                    print_success(msg)
                else:
                    print_error(msg)
                input("\nPress Enter to continue...")
            continue

        # Create new profile
        if choice == len(opts) - 3:
            name = prompt_text("Enter Profile Name (e.g. my-custom-model)")
            if not name:
                continue
            model_id = prompt_text("Enter OpenRouter Model ID (e.g. anthropic/claude-3.7-sonnet)")
            if not model_id:
                continue

            # Context preset select
            ctx_opts = [{"title": str(c[0]), "desc": c[1]} for c in CONTEXT_PRESETS]
            ctx_opts.append({"title": "Custom", "desc": "Enter token count manually"})
            ctx_choice = menu_select("Select Context Window Preset", ctx_opts)
            if ctx_choice is None:
                ctx_tokens = 200000
            elif ctx_choice == len(ctx_opts) - 1:
                raw_c = prompt_text("Enter Context Tokens", default="200000")
                ctx_tokens = int(raw_c) if raw_c.isdigit() else 200000
            else:
                ctx_tokens = CONTEXT_PRESETS[ctx_choice][0]

            desc = prompt_text("Profile Description", default=f"{model_id} profile")
            ok, msg = create_or_update_profile(name, model_id, ctx_tokens, description=desc, activate=True)
            if ok:
                print_success(msg)
            else:
                print_error(msg)
            input("\nPress Enter to continue...")
            continue

        # Switch to selected profile
        selected_prof_name = profs[choice]["name"]
        ok, msg = set_active_profile(selected_prof_name)
        if ok:
            print_success(msg)
        else:
            print_error(msg)
        input("\nPress Enter to continue...")


def menu_token_usage_tracker():
    """Option 4: View live OpenRouter credit usage and local session telemetry."""
    print_banner()
    cfg = get_current_configuration()
    key = cfg.get("OPENROUTER_API_KEY")

    live_stats = None
    if key:
        with Spinner("Querying OpenRouter account API for live credit and rate stats..."):
            ok, live_stats, msg = fetch_openrouter_account_stats(key)
        if not ok:
            print_warn(f"Could not fetch account telemetry: {msg}")

    summary = get_local_usage_summary()

    # OpenRouter Account Card
    if live_stats:
        limit_str = f"${live_stats['limit']:.2f}" if live_stats["limit"] is not None else "Unlimited / Post-paid"
        items = [
            ("Key Label", str(live_stats["label"]), "info"),
            ("Account Usage", f"${live_stats['usage']:.4f}", "info"),
            ("Credit Limit", limit_str, "info"),
            ("Tier", "Free Tier Router" if live_stats["is_free_tier"] else "Paid / Developer Tier", "ok"),
        ]
        if live_stats.get("rate_limit_requests"):
            items.append(("Rate Limit", f"{live_stats['rate_limit_requests']} req / {live_stats.get('rate_limit_interval', 'min')}", "info"))
        print_card("OpenRouter Live Account Status", items)
    else:
        print_card("OpenRouter Live Account Status", [("Status", "API key missing or endpoint unreachable", "warn")])

    # Local telemetry card
    loc_items = [
        ("Total Local Tests", str(summary["total_requests"]), "info"),
        ("Total Tokens Estimated", f"{summary['total_tokens']:,}", "ok" if summary["total_tokens"] > 0 else "info"),
        ("Prompt Tokens", f"{summary['total_prompt_tokens']:,}", "info"),
        ("Completion Tokens", f"{summary['total_completion_tokens']:,}", "info"),
        ("Recorded Events", str(summary["recent_event_count"]), "info"),
    ]
    print_card("Local Session & Inference Telemetry", loc_items)

    print("\nActions:")
    print("  c. Clear local telemetry log")
    print("  Enter. Return to main menu")
    sub = prompt_text("Select action", default="").lower()
    if sub == "c":
        clear_local_usage()
        print_success("Local telemetry cleared.")
        input("\nPress Enter to return...")


def menu_test_connection():
    """Option 5: Test OpenRouter connection and Claude CLI execution."""
    print_banner()
    print_info("Running dual inference verification suite...")

    with Spinner("Testing OpenRouter credentials, model routing, and Claude CLI execution..."):
        report = run_full_verification()

    items = [
        ("Claude Code CLI", f"{report['claude_version'] or 'Not Detected'}", "ok" if report["claude_installed"] else "error"),
        ("Environment Config", "Complete & Valid" if report["env_configured"] else "Incomplete", "ok" if report["env_configured"] else "error"),
        ("OpenRouter Key Auth", f"{report['api_key_label'] or 'Valid'}", "ok" if report["api_key_valid"] else "error"),
        ("Direct API Inference", f"{str(report['openrouter_direct_response'])[:36]}...", "ok" if report["openrouter_direct_test"] else "error"),
        ("Claude CLI Test (-p)", f"{str(report['claude_cli_response'])[:36]}...", "ok" if report["claude_cli_test"] else "warn"),
    ]
    print_card("Integration Verification Report", items)

    if report["overall_success"]:
        print_success("Claude Code is fully configured and operational with OpenRouter!")
    else:
        print_error("One or more verification checks failed.")
        if report["troubleshooting"]:
            print(f"\n{Color.YELLOW}Troubleshooting Guidance:{Color.RESET}")
            for item in report["troubleshooting"]:
                print(f"  • {item}")

    input("\nPress Enter to return to menu...")


def menu_display_status():
    """Option 6: Display current configuration status."""
    print_banner()
    status = get_display_status()
    active_name, active_prof = get_active_profile()

    items = [
        ("Active Profile", f"{active_name} ({active_prof.get('model')})", "active"),
        ("OPENROUTER_API_KEY", status.get("OPENROUTER_API_KEY", "[Not Set]"), "ok" if status.get("OPENROUTER_API_KEY") != "[Not Set]" else "warn"),
        ("ANTHROPIC_AUTH_TOKEN", status.get("ANTHROPIC_AUTH_TOKEN", "[Not Set]"), "ok" if status.get("ANTHROPIC_AUTH_TOKEN") != "[Not Set]" else "warn"),
        ("ANTHROPIC_BASE_URL", status.get("ANTHROPIC_BASE_URL", "[Not Set]"), "ok" if status.get("ANTHROPIC_BASE_URL") == "https://openrouter.ai/api" else "warn"),
        ("ANTHROPIC_MODEL", status.get("ANTHROPIC_MODEL", "[Not Set]"), "info"),
        ("CLAUDE_MAX_CONTEXT", status.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS", "[Not Set]"), "info"),
        ("Direct ANTHROPIC_KEY", status.get("ANTHROPIC_API_KEY", "[Cleared]"), "ok"),
    ]
    print_card("Current User Environment Configuration", items)
    input("\nPress Enter to return to menu...")


def menu_repair_environment():
    """Option 7: Audit and repair inconsistent environment variables."""
    print_banner()
    print_info("Auditing environment variables for drift or conflicts...")
    repaired, actions = repair_environment()
    if repaired:
        print_success(f"Repaired {len(actions)} configuration items:")
        for a in actions:
            print(f"  ✔ {a}")
    else:
        print_success("Environment is fully consistent and standard. No repair needed.")
    input("\nPress Enter to return to menu...")


def run_guided_setup():
    """Option 0: Full step-by-step guided setup."""
    print_banner()
    print_info("Starting Full Guided Setup for Claude Code + OpenRouter...")
    print_system_diagnostics()

    # Step 1: Check / Install Claude Code
    claude_ok, _, _ = detect_claude_code()
    if not claude_ok:
        menu_install_or_repair_claude()
    else:
        print_success("Claude Code CLI is installed.")

    # Step 2: Configure API Key
    cfg = get_current_configuration()
    if not cfg.get("OPENROUTER_API_KEY"):
        menu_configure_api_key()
    else:
        print_success(f"OpenRouter API key is already configured: {mask_key(cfg.get('OPENROUTER_API_KEY'))}")

    # Step 3: Choose Profile / Model
    menu_profiles_and_models()

    # Step 4: Verification test
    menu_test_connection()


def main():
    parser = argparse.ArgumentParser(description="Claude CLI + OpenRouter Setup Tool")
    parser.add_argument("--status", action="store_true", help="Print configuration status and exit")
    parser.add_argument("--verify", action="store_true", help="Run verification suite and exit")
    parser.add_argument("--list-profiles", action="store_true", help="List all saved profiles and exit")
    parser.add_argument("--profile", type=str, help="Switch active profile by name")
    parser.add_argument("--usage", action="store_true", help="Print token usage summary and exit")
    parser.add_argument("--no-tui", action="store_true", help="Force classic CLI prompt mode")
    args = parser.parse_args()

    # CLI flag operations
    if args.status:
        menu_display_status()
        return

    if args.verify:
        rep = run_full_verification()
        sys.exit(0 if rep["overall_success"] else 1)

    if args.list_profiles:
        for p in list_profiles():
            mark = " [ACTIVE]" if p.get("is_active") else ""
            print(f"- {p['name']}{mark}: {p.get('model')} ({p.get('context_tokens')} tokens)")
        return

    if args.profile:
        ok, msg = set_active_profile(args.profile)
        print(msg)
        sys.exit(0 if ok else 1)

    if args.usage:
        s = get_local_usage_summary()
        print(f"Total requests: {s['total_requests']}, Total tokens: {s['total_tokens']}")
        return

    # Interactive Main Loop
    while True:
        active_name, active_prof = get_active_profile()
        cfg = get_current_configuration()
        key_masked = mask_key(cfg.get("OPENROUTER_API_KEY"))

        options = [
            {"title": "🚀 Run Full Guided Setup", "desc": "Step-by-step setup (Prerequisites, Key, Model, Test)"},
            {"title": "📦 Install / Repair Claude Code", "desc": "Install Node.js LTS, npm, and Claude Code CLI"},
            {"title": "🔑 Configure OpenRouter API Key", "desc": f"Manage and validate secret API key (Current: {key_masked})"},
            {"title": "🎭 Profiles & Model Presets", "desc": f"Switch model & context presets (Active: {active_name})"},
            {"title": "📊 Token Usage & Account Analytics", "desc": "Inspect OpenRouter credit balance and local session tokens"},
            {"title": "🧪 Test Connection & Dual Inference", "desc": "Execute live verification (Direct API + Claude CLI)"},
            {"title": "📋 View Configuration Status", "desc": "Display all managed environment variables safely"},
            {"title": "🔧 Repair Environment Variables", "desc": "Fix URL drift, missing tokens, and conflicts"},
            {"title": "🚪 Exit", "desc": "Quit setup tool"},
        ]

        print_banner()
        choice = menu_select(
            title="Main Menu",
            subtitle=f"Active Profile: {Color.CYAN}{active_name}{Color.RESET} | Model: {Color.WHITE}{active_prof.get('model')}{Color.RESET}",
            options=options,
        )

        if choice is None or choice == 8:
            print(f"\n{Color.CYAN}Goodbye! Enjoy using Claude Code with OpenRouter.{Color.RESET}\n")
            break
        elif choice == 0:
            run_guided_setup()
        elif choice == 1:
            menu_install_or_repair_claude()
        elif choice == 2:
            menu_configure_api_key()
        elif choice == 3:
            menu_profiles_and_models()
        elif choice == 4:
            menu_token_usage_tracker()
        elif choice == 5:
            menu_test_connection()
        elif choice == 6:
            menu_display_status()
        elif choice == 7:
            menu_repair_environment()


if __name__ == "__main__":
    main()
