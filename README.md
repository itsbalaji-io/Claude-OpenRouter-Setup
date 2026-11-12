# Claude CLI + OpenRouter Setup

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com/itsbalaji-io/Claude-OpenRouter-Setup)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Compatible-purple.svg)](https://openrouter.ai/)

Zero-dependency tool to install, configure, and route Anthropic's **Claude Code CLI** through **OpenRouter** on Windows, macOS, and Linux.

---

## ⚡ Quick Install

Run in your terminal (no git clone required):

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.ps1 | iex
```

### Windows (CMD)
```cmd
curl -fsSL https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### macOS & Linux
```bash
curl -fsSL https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.sh | bash
```

After install, run `claude-setup` anytime from any directory to open the dashboard.

---

## What It Does

- **Prerequisites**: Automatically detects/installs Node.js LTS and Claude Code CLI.
- **Environment**: Sets `ANTHROPIC_BASE_URL` to OpenRouter and keeps credentials synchronized across sessions.
- **Model Switcher**: 1-click toggle between top free models (`deepseek-r1:free`, `flint-v1.0:free`, `gemini-2.0-flash-exp:free`, etc.).
- **Verification**: Validates credentials and runs live test inference (`claude -p`).

---

## CLI Usage

```bash
claude-setup                     # Launch interactive menu
claude-setup --status            # Show current configuration (masked)
claude-setup --list-models       # List available free models
claude-setup --model <model-id>  # Switch model directly
claude-setup --verify            # Run verification test
claude-setup --usage             # Show local token usage
```

---

## Development & Testing

```bash
python test_setup.py
```

---

## License

[MIT](LICENSE)
