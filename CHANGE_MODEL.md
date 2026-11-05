# How to Change the Model or OpenRouter API Key

This guide explains how to switch free models, adjust context window sizes, or update your OpenRouter API key across Windows, macOS, and Linux.

---

## Method 1: Using the Interactive Setup Tool (Recommended)

1. Run the setup tool:
   - On Windows: Run `setup.bat` or `python main.py`
   - On macOS/Linux: Run `./setup.sh` or `python3 main.py`
   - Or simply run `claude-setup` from anywhere.
2. Select option **`3`** (`Switch Model`).
3. You will see a curated and live list of all top available **free models** on OpenRouter:
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
   - Any other newly added free models on OpenRouter
   - Or enter a custom free model ID manually.
4. Select your preferred free model using arrow keys and press **Enter**.
5. The tool automatically updates all required model aliases (`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `CLAUDE_CODE_MAX_CONTEXT_TOKENS`) in persistent user storage.

---

## Method 2: Fast CLI 1-Liner Model Switching

You can switch active models instantly from your terminal without opening the interactive menu:

```bash
# List all top free models
python main.py --list-models

# Switch directly to DeepSeek R1 (free)
python main.py --model deepseek/deepseek-r1:free

# Switch directly to Gemini 2.0 Flash (free)
python main.py --model google/gemini-2.0-flash-exp:free

# Switch directly to the default Recursive Flint 1.0 (free)
python main.py --model recursive/flint-v1.0:free
```

---

## Method 3: Manual Environment Variable Updates

### On Windows (PowerShell)
```powershell
$NewModel = "recursive/flint-v1.0:free"
$ContextTokens = "262144"

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
export OPENROUTER_MODEL="recursive/flint-v1.0:free"
export ANTHROPIC_MODEL="recursive/flint-v1.0:free"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="recursive/flint-v1.0:free"
export ANTHROPIC_DEFAULT_SONNET_MODEL="recursive/flint-v1.0:free"
export ANTHROPIC_DEFAULT_OPUS_MODEL="recursive/flint-v1.0:free"
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="262144"
```
