"""Terminal User Interface (TUI) Engine for Claude Code + OpenRouter Setup.

Features:
- Pure-Python zero-dependency ANSI color and styling engine
- Cross-platform arrow key navigation (Windows msvcrt + Unix tty/termios)
- Interactive selectable menus with cursor indicator
- Clean flicker-free redraws preventing drift or spacing
- Background animated thread spinner
- Formatted cards, status badges, and tables
- Automatic fallback for non-interactive / redirected environments
"""

import sys
import time
import threading
from typing import List, Tuple, Optional, Dict, Callable


# Enable ANSI Virtual Terminal processing on Windows 10/11
def _init_windows_vt() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
    except Exception:
        pass
    return False

_VT_SUPPORTED = _init_windows_vt()


class Color:
    """ANSI Escape sequence palette."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    BG_BLUE = "\033[44m"
    BG_CYAN = "\033[46m"
    BG_DARK = "\033[40m"


def is_interactive() -> bool:
    """Check if standard input and output are attached to an interactive terminal."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def clear_screen() -> None:
    """Clear terminal screen completely and place cursor at row 1, col 1."""
    if not is_interactive():
        return
    if sys.platform == "win32":
        # Send ANSI home clear
        sys.stdout.write("\033[H\033[2J")
        sys.stdout.flush()
    else:
        sys.stdout.write("\033[H\033[2J")
        sys.stdout.flush()


def get_key() -> str:
    """Read a single keypress in a cross-platform manner."""
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            mapping = {
                b"H": "UP",
                b"P": "DOWN",
                b"K": "LEFT",
                b"M": "RIGHT",
            }
            return mapping.get(ch2, "")
        if ch == b"\r":
            return "ENTER"
        if ch == b"\x1b":
            return "ESC"
        if ch == b"\x08":
            return "BACKSPACE"
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    seq_map = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}
                    return seq_map.get(ch3, "ESC")
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch in ("\x7f", "\x08"):
                return "BACKSPACE"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class Spinner:
    """Threaded real-time terminal spinner with animated glyphs."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Processing..."):
        self.message = message
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _spin(self):
        idx = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[idx % len(self.FRAMES)]
            out = f"\r{Color.CYAN}{frame}{Color.RESET} {self.message} "
            sys.stdout.write(out)
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.message) + 12) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        if is_interactive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            print(f"[i] {self.message}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

    def update(self, new_message: str):
        self.message = new_message


def print_banner(app_name: str = "Claude CLI + OpenRouter Setup", version: str = "v2.0"):
    """Render a stylized header banner at the top of the screen."""
    width = 68
    print(f"{Color.CYAN}{'═' * width}{Color.RESET}")
    title = f"  {app_name}  [{version}]  "
    print(f"{Color.BOLD}{Color.WHITE}{title.center(width)}{Color.RESET}")
    subtitle = "Unified Model Gateway & Environment Manager"
    print(f"{Color.GRAY}{subtitle.center(width)}{Color.RESET}")
    print(f"{Color.CYAN}{'═' * width}{Color.RESET}\n")


def print_card(title: str, items: List[Tuple[str, str, str]]):
    """Render a clean structured card."""
    width = 68
    print(f"\n{Color.BOLD}{Color.WHITE}┌── {title} {'─' * max(2, width - len(title) - 6)}┐{Color.RESET}")
    for label, val, status in items:
        badge = ""
        val_color = Color.WHITE
        if status == "ok":
            badge = f"{Color.GREEN}✔ PASS{Color.RESET}"
            val_color = Color.GREEN
        elif status == "warn":
            badge = f"{Color.YELLOW}▲ WARN{Color.RESET}"
            val_color = Color.YELLOW
        elif status == "error":
            badge = f"{Color.RED}✖ FAIL{Color.RESET}"
            val_color = Color.RED
        elif status == "active":
            badge = f"{Color.CYAN}● CURRENT{Color.RESET}"
            val_color = Color.CYAN
        elif status == "info":
            badge = f"{Color.BLUE}ℹ INFO{Color.RESET}"

        print(f"│  {Color.GRAY}{label:<22}{Color.RESET} {val_color}{val}{Color.RESET} {badge}")
    print(f"{Color.BOLD}{Color.WHITE}└──{'─' * (width - 4)}┘{Color.RESET}")


def print_success(msg: str):
    print(f"{Color.GREEN}✔ [SUCCESS]{Color.RESET} {msg}")


def print_error(msg: str):
    print(f"{Color.RED}✖ [ERROR]{Color.RESET} {msg}")


def print_warn(msg: str):
    print(f"{Color.YELLOW}▲ [WARNING]{Color.RESET} {msg}")


def print_info(msg: str):
    print(f"{Color.CYAN}ℹ [INFO]{Color.RESET} {msg}")


def menu_select(
    title: str,
    options: List[Dict[str, str]],
    default_index: int = 0,
    subtitle: Optional[str] = None,
    header_fn: Optional[Callable[[], None]] = None,
) -> Optional[int]:
    """Interactive arrow navigation menu with clean screen redrawing.
    
    Eliminates vertical spacing drift when Up/Down keys are pressed.
    """
    if not is_interactive():
        print(f"\n--- {title} ---")
        if subtitle:
            print(subtitle)
        for i, opt in enumerate(options):
            print(f"  {i}. {opt.get('title')} - {opt.get('desc', '')}")
        try:
            choice = input(f"Select [0-{len(options)-1}]: ").strip()
            if choice.isdigit() and 0 <= int(choice) < len(options):
                return int(choice)
        except (EOFError, KeyboardInterrupt):
            return None
        return None

    selected = default_index
    num_opts = len(options)

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            # 1. Clear screen to top and reset cursor
            clear_screen()

            # 2. Render header banner
            if header_fn:
                header_fn()
            else:
                print_banner()

            # 3. Render title & instructions
            print(f"{Color.BOLD}{Color.WHITE}{title}{Color.RESET}")
            if subtitle:
                print(f"{Color.GRAY}{subtitle}{Color.RESET}")
            print(f"{Color.GRAY}Use ↑/↓ or j/k to navigate, Enter to select, Esc/q to exit.{Color.RESET}\n")

            # 4. Render items
            for idx, opt in enumerate(options):
                opt_title = opt.get("title", "")
                opt_desc = opt.get("desc", "")
                if idx == selected:
                    indicator = f"{Color.CYAN}❯{Color.RESET}"
                    styled_title = f"{Color.BOLD}{Color.CYAN}{opt_title}{Color.RESET}"
                    styled_desc = f"{Color.WHITE}{opt_desc}{Color.RESET}" if opt_desc else ""
                else:
                    indicator = " "
                    styled_title = f"{Color.WHITE}{opt_title}{Color.RESET}"
                    styled_desc = f"{Color.GRAY}{opt_desc}{Color.RESET}" if opt_desc else ""

                if styled_desc:
                    print(f"{indicator} {styled_title} {Color.GRAY}—{Color.RESET} {styled_desc}")
                else:
                    print(f"{indicator} {styled_title}")

            sys.stdout.flush()

            # 5. Read single key
            key = get_key()
            if key in ("UP", "k", "K"):
                selected = (selected - 1) % num_opts
            elif key in ("DOWN", "j", "J"):
                selected = (selected + 1) % num_opts
            elif key in ("ENTER", " "):
                return selected
            elif key in ("ESC", "q", "Q"):
                return None
            elif key.isdigit() and int(key) < num_opts:
                return int(key)

    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def prompt_text(prompt: str, default: Optional[str] = None) -> str:
    """Prompt user for standard input with optional default value."""
    if default:
        p_str = f"{Color.BOLD}{prompt}{Color.RESET} [{Color.CYAN}{default}{Color.RESET}]: "
    else:
        p_str = f"{Color.BOLD}{prompt}{Color.RESET}: "
    try:
        val = input(p_str).strip()
        if not val and default is not None:
            return default
        return val
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
