# How to Change the Model, Profiles, or OpenRouter API Key

This guide explains how to switch models, manage profiles, adjust context window sizes, or update your OpenRouter API key across Windows, macOS, and Linux.

---

## Method 1: Using Profiles via the Interactive Setup Tool (Recommended)

1. Run the setup tool:
   - On Windows: Run `setup.bat` or `python main.py`
   - On macOS/Linux: Run `./setup.sh` or `python3 main.py`
2. Select option **`3`** (`Profiles & Model Presets`).
3. You can:
   - Select any built-in preset (`flint-free`, `claude-3-7-sonnet`, `deepseek-r1`, `deepseek-chat`, `gemini-2-flash`, `llama-3-3-70b`, `qwen-2-5-coder`).
   - Create your own custom profile (`➕ Create New Profile`).
   - Pick a context window size preset (32k, 64k, 128k, 163k, 200k, 262k, 1M, or custom).
4. The tool automatically updates all required model aliases (`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS`) in persistent user storage.

---

## Method 2: Fast 1-Liner CLI Profile Switching

You can switch active profiles instantly from your terminal without opening the interactive menu:

```bash
# List all profiles
python main.py --list-profiles

# Switch directly to DeepSeek R1
python main.py --profile deepseek-r1

# Switch directly to Claude 3.7 Sonnet
python main.py --profile claude-3-7-sonnet

# Switch directly to the free default
python main.py --profile flint-free
```

---

## Method 3: Manual Environment Variable Updates

### On Windows (PowerShell)
```powershell
$NewModel = "anthropic/claude-3.7-sonnet"
$ContextTokens = "200000"

[System.Environment]::SetEnvironmentVariable("OPENROUTER_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_HAIKU_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_SONNET_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_OPUS_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("CLAUDE_CODE_MAX_CONTEXT_TOKENS", $ContextTokens, "User")
```

### On macOS / Linux (Bash / Zsh)
Add or update in `~/.bashrc` or `~/.zshrc`:
```bash
export OPENROUTER_MODEL="anthropic/claude-3.7-sonnet"
export ANTHROPIC_MODEL="anthropic/claude-3.7-sonnet"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="anthropic/claude-3.7-sonnet"
export ANTHROPIC_DEFAULT_SONNET_MODEL="anthropic/claude-3.7-sonnet"
export ANTHROPIC_DEFAULT_OPUS_MODEL="anthropic/claude-3.7-sonnet"
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="200000"
```
