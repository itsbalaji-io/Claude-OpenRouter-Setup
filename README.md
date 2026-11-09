# Claude CLI + OpenRouter Automated Setup Tool

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com/itsbalaji-io/Claude-OpenRouter-Setup)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Compatible-purple.svg)](https://openrouter.ai/)

An automated, cross-platform terminal application that installs, configures, and tests Anthropic's **Claude Code CLI** to route through **OpenRouter** as the unified API provider on **Windows**, **macOS**, and **Linux**.

---

## ⚡ 1-Line Quick Install

Install and launch everything with a single command — no manual git cloning or manual Python setup needed:

### Windows (Command Prompt / CMD)
```cmd
curl -fsSL https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.ps1 | iex
```

### macOS & Linux (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.sh | bash
```

> **Instant Access**: The installer registers a global `claude-setup` command in your PATH. You can reopen this setup dashboard anytime from any directory by typing:
> ```bash
> claude-setup
> ```

---

## Overview

Claude Code CLI uses the Anthropic Messages API. By configuring custom environment variables (`ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`), Claude Code routes requests to OpenRouter's Anthropic-compatible gateway (`https://openrouter.ai/api/messages`), enabling you to use OpenRouter's diverse model catalogue, including free models like `recursive/flint-v1.0:free`, `deepseek/deepseek-r1:free`, or flagship models like `anthropic/claude-3.7-sonnet` and `deepseek/deepseek-chat`.

This tool automates:
1. **Prerequisite detection & installation** (Node.js LTS, npm, and Claude Code CLI).
2. **Credential management** (masked input, validation against OpenRouter's `/api/v1/auth/key`).
3. **Multi-model profile switching** and context window token tuning.
4. **Live credit balance & local token usage telemetry**.
5. **Dual inference verification** (direct API call + real non-interactive `claude -p` execution).

---

## Interactive Terminal UI (TUI) Preview

```text
════════════════════════════════════════════════════════════════════
            Claude CLI + OpenRouter Setup  [v2.0]            
              Unified Model Gateway & Environment Manager            
════════════════════════════════════════════════════════════════════

Main Menu
Active Free Model: recursive/flint-v1.0:free
Use ↑/↓ or j/k to navigate, Enter to select, Esc/q to exit.

❯ 🚀 Run Full Guided Setup — Step-by-step setup (Prerequisites, Key, Model, Test)
  📦 Install / Repair Claude Code — Install Node.js LTS, npm, and Claude Code CLI
  🔑 Configure OpenRouter API Key — Manage and validate secret API key (Current: sk-or-v1-a84...06ebe)
  🤖 Switch Model — Select from all top available free models (Current: recursive/flint-v1.0:free)
  📊 Token Usage & Account Analytics — Inspect OpenRouter credit balance and local session tokens
  🧪 Test Connection & Dual Inference — Execute live verification (Direct API + Claude CLI)
  📋 View Configuration Status — Display all managed environment variables safely
  🔧 Repair Environment Variables — Fix URL drift, missing tokens, and conflicts
  🚪 Exit — Quit setup tool
```

---

## Key Features

- **Interactive Terminal UI (TUI)**:
  - Arrow navigation (`↑`/`↓`/`Enter`/`Esc` or `k`/`j`) with clean ANSI redrawing (zero vertical spacing drift).
  - Real-time animated background spinners (`⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏`) for network requests and installs.
  - Structured status cards, tables, and color-coded result badges (`PASS`, `WARN`, `FAIL`).
  - Automatic fallback to numeric prompt mode for non-interactive shells or piped inputs.
- **Cross-Platform System Persistence**:
  - **Windows**: Persists variables in `HKCU\Environment` registry and broadcasts `WM_SETTINGCHANGE`.
  - **macOS & Linux**: Persists variables across `~/.bashrc`, `~/.zshrc`, and `~/.profile`.
  - Clipboard auto-detection on all OSes (`powershell Get-Clipboard`, `pbpaste`, `xclip`/`wl-paste`).
- **Top Free Models Switcher**:
  - Switch between all top available free models in 1 keypress:
    - `recursive/flint-v1.0:free` (Default, 262k context — fast coding & instructions)
    - `deepseek/deepseek-r1:free` (DeepSeek R1 full reasoning)
    - `deepseek/deepseek-chat:free` (DeepSeek V3 chat & coding)
    - `google/gemini-2.0-flash-thinking-exp:free` (Gemini 2.0 Thinking with 1M context)
    - `google/gemini-2.0-flash-exp:free` (Gemini 2.0 Flash with 1M context)
    - `meta-llama/llama-3.3-70b-instruct:free` (Meta Llama 3.3 70B open weights)
    - `qwen/qwen-2.5-coder-32b-instruct:free` (Qwen 2.5 Coder 32B by Alibaba Cloud)
    - `google/gemma-4-31b-it:free` (Google Gemma 4 31B open instruction model)
    - `cohere/north-mini-code:free` (Cohere North Mini Code generation model)
    - `nvidia/nemotron-3.5-super-vl:free` (NVIDIA Nemotron 3.5 Super VL, 1M context)
    - Plus real-time dynamic querying of any other `:free` models on OpenRouter!
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
├── install.cmd         # 1-Line Windows Command Prompt installer
├── install.ps1         # 1-Line Windows PowerShell installer
├── install.sh          # 1-Line macOS & Linux installer
├── setup.bat           # Windows launcher
├── setup.sh            # macOS & Linux launcher
├── main.py             # Main entry point & interactive TUI engine
├── tui.py              # Zero-dependency terminal UI, arrows, spinners & formatting
├── tracker.py          # OpenRouter live credit & local token usage telemetry
├── config.py           # Cross-platform environment variable manager
├── installer.py        # System diagnostics and installer (winget / brew / apt / npm)
├── openrouter.py       # OpenRouter REST API client & model validator
├── verifier.py         # End-to-end integration verification suite
├── test_setup.py       # Unit test suite
├── requirements.txt    # Optional dependencies
├── .env.example        # Safe placeholder template
├── .gitignore          # Version control ignore rules
├── CHANGE_MODEL.md     # Quick guide for free model switching
├── LICENSE             # MIT License
└── README.md           # Documentation
```

---

## Manual Launch (From Cloned Repository)

### On Windows
```cmd
setup.bat
```

### On macOS / Linux
```bash
chmod +x setup.sh
./setup.sh
```

### Direct Python Run
```bash
python main.py
```

---

## CLI Options

Automate or inspect the setup without the interactive menu:

```bash
python main.py --status           # Display current environment configuration (masked)
python main.py --verify           # Run automated end-to-end verification suite
python main.py --list-models      # List all available top free models
python main.py --model <id>       # Switch active free model directly (e.g. --model deepseek/deepseek-r1:free)
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

## Troubleshooting

- **Windows Sandbox DNS Failure (`[Errno 11001] getaddrinfo failed`)**:
  In Windows Sandbox, DNS relay often fails on the virtual adapter. Open PowerShell as Administrator and run:
  ```powershell
  Get-NetAdapter | Where-Object Status -eq 'Up' | Set-DnsClientServerAddress -ServerAddresses ('8.8.8.8','1.1.1.1'); Clear-DnsClientCache
  ```
- **Changes not reflecting in existing terminal**:
  Environment changes take effect in newly launched shells. Open a new PowerShell, CMD, or Terminal window after running setup.
- **Direct Anthropic Fallback**:
  If Claude Code attempts to contact Anthropic directly instead of OpenRouter, run Option `7` (`Repair Environment Variables`) to remove conflicting `ANTHROPIC_API_KEY` variables.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
