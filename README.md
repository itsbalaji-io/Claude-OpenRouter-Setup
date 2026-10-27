# Claude CLI + OpenRouter Automated Windows Setup Tool

An automated, reusable Python application that installs, configures, and tests Anthropic's **Claude Code CLI** to route through **OpenRouter** as the unified API provider on Microsoft Windows.

---

## Overview

Claude Code CLI uses the Anthropic Messages API. By configuring custom environment variables (`ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`), Claude Code routes requests to OpenRouter's Anthropic-compatible gateway (`https://openrouter.ai/api/v1/messages`), enabling you to use OpenRouter's diverse model catalogue, including free models like `recursive/flint-v1.0:free`.

This setup tool automates the detection, prerequisite installation (Node.js LTS, Claude Code CLI), credential management, model binding, and real-world inference testing without exposing secrets.

---

## Features

- **Automated Prerequisite Detection & Installation**: Checks Windows version, PowerShell version, Python 3.10+, Node.js LTS, npm, and Claude Code CLI. Installs missing tools via `winget` or `npm`.
- **Persistent User-Level Configuration**: Stores settings in `HKCU\Environment` (Windows Registry) and broadcasts `WM_SETTINGCHANGE` so newly launched PowerShell or CMD windows pick up settings automatically.
- **Strict Secret Protection**:
  - Prompts for API keys with hidden input (`getpass`).
  - Redacts keys across CLI output, logs, and status checks (e.g., `sk-or-v1-a84...06ebe`).
  - Does **not** store plaintext keys in `.env` files or source repositories.
- **Live Model Catalog & Validation**: Queries OpenRouter's API in real time to validate model identifiers, retrieve context window lengths, and check tool support.
- **Dual Inference Verification**: Tests both direct OpenRouter HTTP inference and actual non-interactive Claude Code CLI execution (`claude -p`).
- **Idempotent & Modular**: Re-running the application updates existing configurations without creating duplicate entries or reinstalling already configured packages.

---

## Project Structure

```text
Claude-OpenRouter-Setup/
├── setup.bat           # 1-Click Windows batch launcher (auto-installs Python via winget if missing)
├── main.py             # Interactive CLI application & menu workflow
├── config.py           # Windows Registry environment variable manager
├── installer.py        # System diagnostics and prerequisite installer (winget / npm)
├── openrouter.py       # OpenRouter REST API client & model validator
├── verifier.py         # End-to-end integration verification suite
├── test_setup.py       # Unit test suite (9 tests)
├── requirements.txt    # Optional external dependencies
├── .env.example        # Safe placeholder template (no real secrets)
├── .gitignore          # Version control ignore rules
├── CHANGE_MODEL.md     # Quick guide for updating models and keys
├── LICENSE             # MIT License
└── README.md           # Documentation
```

---

## Quickstart (Fresh Windows Machine)

### 1. One-Click Launch via `setup.bat` (Recommended)
Simply double-click **`setup.bat`** or run it from any terminal:
```cmd
setup.bat
```
- **Auto-installs Python**: If Python is missing, `setup.bat` automatically installs Python 3.12 via `winget`, refreshes your PATH in the active session, and proceeds directly to the setup application.
- **Auto-installs Node.js & Claude Code**: Through Option 0 or Option 1 in the menu, the tool installs Node.js LTS and Claude Code CLI.

### 2. Manual Python Launch
Alternatively, if Python 3.10+ is already installed on your system:
```powershell
python main.py
```

Choose **Option 0** for a full guided setup, or choose individual menu items:

```text
==================================================================
      Claude CLI + OpenRouter Automated Windows Setup Tool
==================================================================
  0. Run Full Guided Setup (Recommended for first-time setup)
  1. Install or repair Claude Code
  2. Configure OpenRouter API key
  3. Change the model
  4. Test OpenRouter connection & inference
  5. Display configuration status (never reveals key)
  6. Repair environment variables
  7. Exit
==================================================================
```

---

## Environment Variables Configured

The tool writes the following persistent **Windows User Environment Variables** (`HKCU\Environment`):

| Variable Name | Value / Purpose |
| :--- | :--- |
| `OPENROUTER_API_KEY` | Your OpenRouter secret key (`sk-or-v1-...`) |
| `ANTHROPIC_AUTH_TOKEN` | Set to your OpenRouter API key so Claude Code's Anthropic client authenticates properly |
| `ANTHROPIC_BASE_URL` | `https://openrouter.ai/api/v1` (Routes requests to OpenRouter's gateway) |
| `OPENROUTER_MODEL` | Dedicated variable storing the selected model identifier |
| `ANTHROPIC_MODEL` | Default model override for all Claude Code sessions |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Pinned to your selected OpenRouter model |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Pinned to your selected OpenRouter model |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Pinned to your selected OpenRouter model |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS`| Context window size in tokens (e.g. `262144` for Recursive Flint) |
| `ANTHROPIC_API_KEY` | Explicitly cleared/deleted from User environment to prevent direct Anthropic fallback |

> **Note on PowerShell Sessions:** Persistent user environment variables take effect in newly launched shells. After running setup, open a **new** PowerShell window before running `claude`.

---

## Verification & Testing

### Run Automated Tests
To run the included unit tests:
```powershell
python test_setup.py
```

### Run Live CLI Diagnostics
To inspect configuration status:
```powershell
python main.py --status
```

To run end-to-end inference verification:
```powershell
python main.py --test
```

### Manual Verification in PowerShell
Open a new PowerShell window and run:
```powershell
claude -p "Say hello in one word"
```
Sample expected output:
```text
Hello!
```

---

## Security Architecture

1. **No Hardcoded Credentials**: Source code, tests, and version control files contain no API keys.
2. **Registry-Level Isolation**: Environment variables are stored under `HKEY_CURRENT_USER\Environment`. On Windows, this registry hive is secured by user account ACLs, inaccessible to other non-administrator user accounts on the machine.
3. **No Plaintext Configuration Files**: Keys are not written to `.env`, `.json`, or `.yaml` files in the repository.
4. **Masked Output**: Diagnostic outputs and logs only show truncated prefixes and suffixes (e.g., `sk-or-v1-a84...06ebe`).

---

## Portability to Another Windows System

To transfer this application to another Windows machine:
1. Copy or extract the `Claude-OpenRouter-Setup` directory (or `Claude-OpenRouter-Setup.zip`).
2. Open PowerShell in the directory.
3. Run:
   ```powershell
   python main.py
   ```
4. Follow the interactive prompts to install dependencies and configure your OpenRouter API key.

---

## Troubleshooting

### Issue: `claude : The term 'claude' is not recognized`
- **Cause**: Path environment variable has not been reloaded in the current terminal.
- **Solution**: Close PowerShell and open a new PowerShell window, or run `main.py` option 1.

### Issue: `Authentication failed: Invalid OpenRouter API key`
- **Cause**: Key syntax is invalid or key was revoked on OpenRouter.
- **Solution**: Check [https://openrouter.ai/keys](https://openrouter.ai/keys) and update via `main.py` option 2.

### Issue: Claude Code attempts to connect to `api.anthropic.com`
- **Cause**: A conflicting `ANTHROPIC_API_KEY` environment variable is overriding the custom gateway.
- **Solution**: Run `main.py` option 6 (`Repair environment variables`) to clear stale Anthropic variables.

---

## License

This project is licensed under the [MIT License](LICENSE).
