# How to Change the Model or OpenRouter API Key

This guide provides simple methods to update your OpenRouter model or API key on Windows without reinstalling Claude Code.

---

## Method 1: Using the Interactive Setup Tool (Recommended)

1. Open **PowerShell** or **Command Prompt**.
2. Navigate to the setup folder:
   ```powershell
   cd C:\Users\Balaji\Claude-OpenRouter-Setup
   python main.py
   ```
3. To change the **model**:
   - Select option **`3`** (`Change the model`).
   - The tool will fetch the latest free models from OpenRouter.
   - Select a number from the list or type any model ID (e.g., `recursive/flint-v1.0:free`, `google/gemma-4-26b-a4b-it:free`, etc.).
   - The tool updates all matching model aliases (`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`) and sets the context window automatically.
4. To change the **API Key**:
   - Select option **`2`** (`Configure OpenRouter API key`).
   - Paste your new key (input is masked for security).
   - The key is validated against OpenRouter and saved.
5. Select option **`4`** to verify your changes.

---

## Method 2: Changing Variables via PowerShell

If you prefer using PowerShell commands directly, run the following:

### To Change the Model:
```powershell
# Set your desired model
$NewModel = "recursive/flint-v1.0:free"

[System.Environment]::SetEnvironmentVariable("OPENROUTER_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_HAIKU_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_SONNET_MODEL", $NewModel, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_DEFAULT_OPUS_MODEL", $NewModel, "User")

Write-Host "Model updated to: $NewModel"
```

### To Change the API Key:
```powershell
# Prompt securely without printing the key
$SecureKey = Read-Host -Prompt "Enter new OpenRouter API Key" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
$PlainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

[System.Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", $PlainKey, "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $PlainKey, "User")

Write-Host "API key updated successfully."
```

> **Important:** After updating user environment variables directly in PowerShell, open a **new** PowerShell window so the terminal session inherits the updated variables.

---

## Method 3: Temporarily Changing the Model for a Single Session

You can override the model for just the current terminal session without affecting persistent settings:

```powershell
$env:ANTHROPIC_MODEL = "recursive/flint-v1.0:free"
claude
```

Or pass the `--model` flag directly to Claude Code:

```powershell
claude --model recursive/flint-v1.0:free
```

---

## Verifying the Change

Run the setup tool's verification command:
```powershell
python main.py --test
```
Or check the current status:
```powershell
python main.py --status
```
