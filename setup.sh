#!/usr/bin/env bash
# ==============================================================================
# Claude CLI + OpenRouter Setup Launcher for macOS & Linux
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=================================================================="
echo "      Claude CLI + OpenRouter Setup Launcher (macOS/Linux)       "
echo "=================================================================="
echo ""

# 1. Detect Python 3.10+
PYTHON_BIN=""
for candidate in python3 python python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VER=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

# 2. Attempt automatic Python install if missing
if [ -z "$PYTHON_BIN" ]; then
    echo "[-] Python 3.10+ was not found on your system."
    echo "[i] Attempting to install Python via package manager..."
    if command -v brew >/dev/null 2>&1; then
        brew install python
        PYTHON_BIN="python3"
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
        PYTHON_BIN="python3"
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip
        PYTHON_BIN="python3"
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm python python-pip
        PYTHON_BIN="python3"
    else
        echo "[ERROR] Could not install Python automatically."
        echo "Please install Python 3.10+ manually and rerun this script."
        exit 1
    fi
fi

echo "[+] Using Python runtime: $($PYTHON_BIN --version) at $(command -v "$PYTHON_BIN")"

# 3. Add common local bin paths to PATH
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

# 4. Launch main TUI application
exec "$PYTHON_BIN" main.py "$@"
