#!/usr/bin/env bash
# ==============================================================================
# Claude CLI + OpenRouter 1-Click Installer for macOS & Linux
# Usage: curl -fsSL https://raw.githubusercontent.com/itsbalaji-io/Claude-OpenRouter-Setup/main/install.sh | bash
# ==============================================================================
set -e

echo "=================================================================="
echo "      Claude CLI + OpenRouter Automated 1-Click Installer         "
echo "=================================================================="
echo ""

TARGET_DIR="$HOME/.claude-openrouter-setup"
REPO_URL="https://github.com/itsbalaji-io/Claude-OpenRouter-Setup.git"
ZIP_URL="https://github.com/itsbalaji-io/Claude-OpenRouter-Setup/archive/refs/heads/main.zip"

if command -v git >/dev/null 2>&1; then
    if [ -d "$TARGET_DIR/.git" ]; then
        echo "[+] Updating existing installation at $TARGET_DIR..."
        git -C "$TARGET_DIR" fetch origin main >/dev/null 2>&1 || true
        git -C "$TARGET_DIR" reset --hard origin/main >/dev/null 2>&1 || true
    else
        echo "[+] Cloning repository to $TARGET_DIR..."
        rm -rf "$TARGET_DIR"
        git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
    fi
else
    echo "[i] Git not detected. Downloading package archive from GitHub..."
    TMP_ZIP="/tmp/claude-openrouter-setup.zip"
    TMP_EXTRACT="/tmp/claude-openrouter-extract"
    rm -rf "$TMP_ZIP" "$TMP_EXTRACT"
    curl -fLso "$TMP_ZIP" "$ZIP_URL"
    mkdir -p "$TMP_EXTRACT"
    unzip -q "$TMP_ZIP" -d "$TMP_EXTRACT"
    rm -f "$TMP_ZIP"
    rm -rf "$TARGET_DIR"
    mkdir -p "$TARGET_DIR"
    cp -r "$TMP_EXTRACT"/Claude-OpenRouter-Setup-main/* "$TARGET_DIR"/
    rm -rf "$TMP_EXTRACT"
fi

chmod +x "$TARGET_DIR/setup.sh"

# Create global claude-setup symlink in ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$TARGET_DIR/setup.sh" "$HOME/.local/bin/claude-setup"
echo "[+] Registered global command: claude-setup"

cd "$TARGET_DIR"
exec ./setup.sh "$@"
