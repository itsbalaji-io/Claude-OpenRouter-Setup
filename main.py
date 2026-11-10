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
    validate_key_format,
    apply_openrouter_config,
    update_model,
    update_api_key,
    get_display_status,
    repair_environment,
    get_current_configuration,
    DEFAULT_MODEL,
)
from installer import (
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
)
from verifier import run_full_verification
from tracker import (
    fetch_openrouter_account_stats,
    get_local_usage_summary,
    clear_local_usage,
)
from tui import (
    Color,
    Spinner,
    clear_screen,
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

# Curated Top Free Models on OpenRouter
TOP_FREE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "recursive/flint-v1.0:free",
        "name": "Recursive Flint 1.0 (Default Free)",
        "context_length": 262144,
        "desc": "Ultra-fast instruction & coding model (262k context)",
    },
    {
        "id": "deepseek/deepseek-r1:free",
        "name": "DeepSeek R1 (Free)",
        "context_length": 163840,
        "desc": "DeepSeek R1 full reasoning model (163k context)",
    },
    {
        "id": "deepseek/deepseek-chat:free",
        "name": "DeepSeek V3 (Free)",
        "context_length": 163840,
        "desc": "DeepSeek V3 general chat & coding (163k context)",
    },
    {
        "id": "google/gemini-2.0-flash-thinking-exp:free",
        "name": "Google Gemini 2.0 Flash Thinking (Free)",
        "context_length": 1000000,
        "desc": "Gemini 2.0 Flash with reasoning & 1M context",
    },
    {
        "id": "google/gemini-2.0-flash-exp:free",
        "name": "Google Gemini 2.0 Flash (Free)",
        "context_length": 1000000,
        "desc": "High-speed multimodal Gemini (1M context)",
    },
    {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Meta Llama 3.3 70B (Free)",
        "context_length": 131072,
        "desc": "Meta Llama 3.3 70B open weights instruction-tuned",
    },
    {
        "id": "qwen/qwen-2.5-coder-32b-instruct:free",
        "name": "Qwen 2.5 Coder 32B (Free)",
        "context_length": 131072,
        "desc": "Specialized coding model by Alibaba Cloud",
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B (Free)",
        "context_length": 262144,
        "desc": "Google Gemma open instruction model (262k context)",
    },
    {
        "id": "cohere/north-mini-code:free",
        "name": "Cohere North Mini Code (Free)",
        "context_length": 256000,
        "desc": "Cohere code generation model (256k context)",
    },
    {
        "id": "nvidia/nemotron-3.5-super-vl:free",
        "name": "NVIDIA Nemotron 3.5 Super VL (Free)",
        "context_length": 1000000,
        "desc": "NVIDIA Nemotron vision-language model (1M context)",
    },
]


def print_system_diagnostics():
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
    clear_screen()
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
            input("\nPress Enter to return...")
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
    input("\nPress Enter to return...")


def prompt_user_api_key() -> Optional[str]:
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
    clear_screen()
    print_banner()
    print_info("Configure OpenRouter API Key")
    print("Your key is validated live and persistently registered in user environment.\n")

    key = prompt_user_api_key()
    if not key:
        print_error("API key cannot be empty. Operation cancelled.")
        input("\nPress Enter to return...")
        return

    valid_format, fmt_msg = validate_key_format(key)
    if not valid_format:
        print_error(f"Invalid key syntax: {fmt_msg}")
        input("\nPress Enter to return...")
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
    input("\nPress Enter to return...")


def menu_switch_model():
    cfg = get_current_configuration()
    current_model = cfg.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    live_models: List[Dict[str, Any]] = []
    ok, fetched, _ = fetch_models(free_only=True)
    if ok and fetched:
        live_models = fetched

    known_ids = set()
    model_choices: List[Dict[str, Any]] = []

    for m in TOP_FREE_MODELS:
        m_id = m["id"]
        known_ids.add(m_id)
        for lm in live_models:
            if lm.get("id") == m_id:
                m["context_length"] = lm.get("context_length", m["context_length"])
                break
        model_choices.append(m)

    for lm in live_models:
        lm_id = lm.get("id", "")
        if lm_id and lm_id not in known_ids and ":free" in lm_id:
            known_ids.add(lm_id)
            model_choices.append({
                "id": lm_id,
                "name": lm.get("name", lm_id),
                "context_length": lm.get("context_length", 200000),
                "desc": f"Live free model ({lm.get('context_length', 200000):,} tokens)",
            })

    options: List[Dict[str, str]] = []
    for m in model_choices:
        is_curr = (m["id"] == current_model)
        marker = " [CURRENT]" if is_curr else ""
        ctx_k = f"{m.get('context_length', 200000) // 1000}k" if m.get("context_length") else "N/A"
        options.append({
            "title": f"{m['id']}{marker}",
            "desc": f"{ctx_k} context — {m.get('desc', '')}",
        })

    options.append({
        "title": "✏️  Enter Custom Free Model ID",
        "desc": "Specify any custom OpenRouter free model manually",
    })
    options.append({
        "title": "↩  Cancel",
        "desc": "Return to main menu without changing model",
    })

    choice = menu_select(
        title="🤖 Switch Model (Free Top Models)",
        subtitle=f"Current Model: {Color.CYAN}{current_model}{Color.RESET}",
        options=options,
    )

    if choice is None or choice == len(options) - 1:
        return

    if choice == len(options) - 2:
        custom_id = prompt_text("Enter OpenRouter Model ID (must end in :free)")
        if not custom_id:
            return
        clean_custom = custom_id.strip()
        ctx_input = prompt_text("Enter Context Tokens", default="262144")
        ctx_tokens = int(ctx_input) if ctx_input.isdigit() else 262144
        update_model(clean_custom, context_tokens=ctx_tokens)
        clear_screen()
        print_banner()
        print_success(f"Model updated to: {clean_custom} ({ctx_tokens} context tokens)")
        input("\nPress Enter to return...")
        return

    selected_m = model_choices[choice]
    sel_id = selected_m["id"]
    sel_ctx = selected_m.get("context_length", 262144)

    update_model(sel_id, context_tokens=sel_ctx)
    clear_screen()
    print_banner()
    print_success(f"Model successfully switched to: {Color.CYAN}{sel_id}{Color.RESET}")
    print_info(f"Context window configured: {sel_ctx:,} tokens (CLAUDE_CODE_MAX_CONTEXT_TOKENS)")
    print_info("New terminal sessions will automatically use this model for Claude Code.")
    input("\nPress Enter to return...")


def menu_token_usage_tracker():
    clear_screen()
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
    clear_screen()
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


def menu_display_status(wait: bool = True):
    clear_screen()
    print_banner()
    status = get_display_status()
    cfg = get_current_configuration()
    current_model = cfg.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    items = [
        ("Current Free Model", f"{current_model}", "active"),
        ("OPENROUTER_API_KEY", status.get("OPENROUTER_API_KEY", "[Not Set]"), "ok" if status.get("OPENROUTER_API_KEY") != "[Not Set]" else "warn"),
        ("ANTHROPIC_AUTH_TOKEN", status.get("ANTHROPIC_AUTH_TOKEN", "[Not Set]"), "ok" if status.get("ANTHROPIC_AUTH_TOKEN") != "[Not Set]" else "warn"),
        ("ANTHROPIC_BASE_URL", status.get("ANTHROPIC_BASE_URL", "[Not Set]"), "ok" if status.get("ANTHROPIC_BASE_URL") == "https://openrouter.ai/api" else "warn"),
        ("ANTHROPIC_MODEL", status.get("ANTHROPIC_MODEL", "[Not Set]"), "info"),
        ("CLAUDE_MAX_CONTEXT", status.get("CLAUDE_CODE_MAX_CONTEXT_TOKENS", "[Not Set]"), "info"),
        ("Direct ANTHROPIC_KEY", status.get("ANTHROPIC_API_KEY", "[Cleared]"), "ok"),
    ]
    print_card("Current User Environment Configuration", items)
    if wait:
        input("\nPress Enter to return to menu...")


def menu_repair_environment():
    clear_screen()
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
    clear_screen()
    print_banner()
    print_info("Starting Full Guided Setup for Claude Code + OpenRouter...")
    print_system_diagnostics()

    claude_ok, _, _ = detect_claude_code()
    if not claude_ok:
        menu_install_or_repair_claude()
    else:
        print_success("Claude Code CLI is installed.")

    cfg = get_current_configuration()
    if not cfg.get("OPENROUTER_API_KEY"):
        menu_configure_api_key()
    else:
        print_success(f"OpenRouter API key is already configured: {mask_key(cfg.get('OPENROUTER_API_KEY'))}")

    menu_switch_model()
    menu_test_connection()


def main():
    parser = argparse.ArgumentParser(description="Claude CLI + OpenRouter Setup Tool")
    parser.add_argument("--status", action="store_true", help="Print configuration status and exit")
    parser.add_argument("--verify", action="store_true", help="Run verification suite and exit")
    parser.add_argument("--list-models", action="store_true", help="List all available top free models and exit")
    parser.add_argument("--model", type=str, help="Switch active free model by ID")
    parser.add_argument("--usage", action="store_true", help="Print token usage summary and exit")
    parser.add_argument("--no-tui", action="store_true", help="Force classic CLI prompt mode")
    args = parser.parse_args()

    if args.status:
        menu_display_status(wait=False)
        return

    if args.verify:
        rep = run_full_verification()
        sys.exit(0 if rep["overall_success"] else 1)

    if args.list_models:
        for m in TOP_FREE_MODELS:
            print(f"- {m['id']}: {m.get('context_length', 200000)} tokens - {m.get('desc', '')}")
        return

    if args.model:
        update_model(args.model)
        print(f"Model updated to: {args.model}")
        sys.exit(0)

    if args.usage:
        s = get_local_usage_summary()
        print(f"Total requests: {s['total_requests']}, Total tokens: {s['total_tokens']}")
        return

    while True:
        cfg = get_current_configuration()
        key_masked = mask_key(cfg.get("OPENROUTER_API_KEY"))
        current_model = cfg.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

        options = [
            {"title": "🚀 Run Full Guided Setup", "desc": "Step-by-step setup (Prerequisites, Key, Model, Test)"},
            {"title": "📦 Install / Repair Claude Code", "desc": "Install Node.js LTS, npm, and Claude Code CLI"},
            {"title": "🔑 Configure OpenRouter API Key", "desc": f"Manage and validate secret API key (Current: {key_masked})"},
            {"title": "🤖 Switch Model", "desc": f"Select from all top available free models (Current: {current_model})"},
            {"title": "📊 Token Usage & Account Analytics", "desc": "Inspect OpenRouter credit balance and local session tokens"},
            {"title": "🧪 Test Connection & Dual Inference", "desc": "Execute live verification (Direct API + Claude CLI)"},
            {"title": "📋 View Configuration Status", "desc": "Display all managed environment variables safely"},
            {"title": "🔧 Repair Environment Variables", "desc": "Fix URL drift, missing tokens, and conflicts"},
            {"title": "🚪 Exit", "desc": "Quit setup tool"},
        ]

        choice = menu_select(
            title="Main Menu",
            subtitle=f"Active Free Model: {Color.CYAN}{current_model}{Color.RESET}",
            options=options,
        )

        if choice is None or choice == 8:
            clear_screen()
            print_banner()
            print(f"{Color.CYAN}Goodbye! Enjoy using Claude Code with OpenRouter.{Color.RESET}\n")
            break
        elif choice == 0:
            run_guided_setup()
        elif choice == 1:
            menu_install_or_repair_claude()
        elif choice == 2:
            menu_configure_api_key()
        elif choice == 3:
            menu_switch_model()
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