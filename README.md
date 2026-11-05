# Claude CLI + OpenRouter Automated Setup Tool

An automated, cross-platform application that installs, configures, and tests Anthropic's **Claude Code CLI** to route through **OpenRouter** as the unified API provider on **Windows**, **macOS**, and **Linux**.

---

## Overview

Claude Code CLI uses the Anthropic Messages API. By configuring custom environment variables (`ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`), Claude Code routes requests to OpenRouter's Anthropic-compatible gateway (`https://openrouter.ai/api/v1/messages`), enabling you to use OpenRouter's diverse model catalogue, including free models like `recursive/flint-v1.0:free`, `deepseek/deepseek-r1:free`, or flagship models like `anthropic/claude-3.7-sonnet` and `deepseek/deepseek-chat`.

This setup tool automates prerequisite detection (Node.js LTS, Claude Code CLI), credential management, profile management, live credit tracking, and dual-layer inference verification without exposing secrets.

---

## Key Features

- **Interactive Terminal UI (TUI)**:
  - Arrow key navigation (`↑`/`↓`/`Enter`/`Esc`) with ANSI styling and responsive cursor rendering.
  - Real-time animated background spinners for network queries and package installations.
  - Formatted status cards, tables, and diagnostic report badges.
  - Automatic fallback to numeric prompt mode for non-interactive shells or piped inputs.
- **Cross-Platform Support (Windows, macOS, Linux)**:
  - **Windows**: Persists variables in `HKCU\Environment` registry and broadcasts `WM_SETTINGCHANGE`.
  - **macOS & Linux**: Persists variables across `~/.bashrc`, `~/.zshrc`, and `~/.profile`.
  - Global executable shims and symlinks (`.cmd` on Windows, symlinks in `~/.local/bin` or `/usr/local/bin` on Unix).
  - Cross-platform clipboard auto-detection for API key pasting (Windows PowerShell, macOS `pbpaste`, Linux `xclip` / `wl-paste`).
- **Multi-Model Profiles & Presets**:
  - Switch between curated model configurations in 1 keypress:
    - `flint-free` (`recursive/flint-v1.0:free`, 262k context)
    - `claude-3-7-sonnet` (`anthropic/claude-3.7-sonnet`, 200k context)
    - `claude-3-5-sonnet` (`anthropic/claude-3.5-sonnet`, 200k context)
    - `deepseek-r1` (`deepseek/deepseek-r1`, 163k context)
    - `deepseek-chat` (`deepseek/deepseek-chat`, 163k context)
    - `deepseek-r1-free` (`deepseek/deepseek-r1:free`, 163k context)
    - `gemini-2-flash` (`google/gemini-2.0-flash-001`, 1M context)
    - `llama-3-3-70b` (`meta-llama/llama-3.3-70b-instruct`, 131k context)
    - `qwen-2-5-coder` (`qwen/qwen-2.5-coder-32b-instruct`, 131k context)
  - Create, clone, or delete custom profiles stored in `~/.claude_openrouter_profiles.json`.
- **Token Usage & Credit Tracker**:
  - Live account telemetry from OpenRouter `/api/v1/auth/key` (usage, credit balance, rate limits, tier).
  - Local inference session tracking in `~/.claude_openrouter_usage.json` (prompt/completion tokens, latency, request count).
- **Strict Secret Protection**:
  - Prompts with hidden or masked input.
  - Redacts keys across CLI outputs, logs, and status checks (e.g., `sk-or-v1-a84...06ebe`).
  - Never commits plaintext keys or secrets to disk or git.
- **Dual Inference Verification**:
  - Tests direct OpenRouter HTTP inference and actual non-interactive Claude Code CLI execution (`claude -p`).

---

## Project Structure

```text
Claude-OpenRouter-Setup/
├── setup.bat           # 1-Click Windows batch launcher
├── setup.sh            # 1-Click macOS & Linux bash launcher
├── main.py             # Main entry point & interactive TUI engine
├── tui.py              # Zero-dependency terminal UI, arrows, spinners & formatting
├── profiles.py         # Multi-model profiles & context window presets
├── tracker.py          # OpenRouter live credit & local token usage telemetry
├── config.py           # Cross-platform environment variable manager
├── installer.py        # System diagnostics and installer (winget / brew / apt / npm)
├── openrouter.py       # OpenRouter REST API client & model validator
├── verifier.py         # End-to-end integration verification suite
├── test_setup.py       # Unit test suite (12 tests)
├── requirements.txt    # Optional dependencies
├── .env.example        # Safe placeholder template
├── .gitignore          # Version control ignore rules
├── CHANGE_MODEL.md     # Quick guide for profiles and switching
├── LICENSE             # MIT License
└── README.md           # Documentation
```

---

## Quickstart

### On Windows
Run `setup.bat`:
```cmd
setup.bat
```
- Auto-detects Python. If missing, it downloads official portable Python 3.12.
- Launches the interactive TUI menu.

### On macOS / Linux
Run `setup.sh`:
```bash
chmod +x setup.sh
./setup.sh
```
- Auto-detects Python 3.10+ (or installs via `brew`, `apt`, `dnf`, or `pacman`).
- Launches the interactive TUI menu.

### Manual Python Launch
```bash
python main.py
```

---

## CLI Options

You can automate or inspect the setup without the interactive menu:

```bash
python main.py --status           # Display current environment configuration (masked)
python main.py --verify           # Run automated end-to-end verification suite
python main.py --list-profiles    # List all available model profiles
python main.py --profile <name>   # Switch active profile directly (e.g. --profile deepseek-r1)
python main.py --usage            # Output local token usage summary
python main.py --no-tui           # Run in plain numerical menu mode
```

---

## Environment Variables Configured

| Variable Name | Purpose |
| :--- | :--- |
| `OPENROUTER_API_KEY` | Your OpenRouter API secret key (`sk-or-v1-...`) |
| `ANTHROPIC_AUTH_TOKEN` | Mirrored OpenRouter API key so Claude Code's Anthropic client authenticates properly |
| `ANTHROPIC_BASE_URL` | Set to `https://openrouter.ai/api` (Routes Claude Code requests to OpenRouter gateway) |
| `OPENROUTER_MODEL` | Currently active model identifier |
| `ANTHROPIC_MODEL` | Default model override for all Claude Code sessions |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Pinned to active model |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Pinned to active model |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Pinned to active model |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS`| Context window size in tokens (e.g. `200000`, `262144`) |
| `ANTHROPIC_API_KEY` | Explicitly cleared/deleted to prevent unintentional direct Anthropic calls |

---

## Unit Testing

Run the included unit test suite:
```bash
python test_setup.py
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
