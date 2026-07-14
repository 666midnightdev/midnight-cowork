import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHATS_FILE = os.path.join(BASE_DIR, "chats.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
WHATSAPP_SESSIONS_FILE = os.path.join(BASE_DIR, "whatsapp_sessions.json")

os.makedirs(os.path.join(BASE_DIR, "templates"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "css"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "js"), exist_ok=True)

try:
    from interpreter import interpreter

    interpreter.auto_run = True
    INTERPRETER_AVAILABLE = True
except ImportError:
    INTERPRETER_AVAILABLE = False
    interpreter = None

DEFAULT_SETTINGS: dict = {
    "model": "gpt-4o",
    "api_key": "",
    "auto_run": True,
    "system_message": (
        "You are Midnight Cowork, an autonomous AI co-worker. You have full permission "
        "and access to this computer to execute Python, Shell, and Javascript commands. "
        "To perform Desktop automation, control the mouse/keyboard, take screenshots, or "
        "interact with graphical interfaces, you can write Python scripts using libraries "
        "like 'pyautogui', 'keyboard', or 'pynput'. Always run code automatically (auto-run "
        "is enabled by the user). Work autonomously to solve the user's tasks. Respond in "
        "the user's language (Indonesian). IMPORTANT DESKTOP AUTOMATION RULES: 1. When "
        "launching GUI apps (e.g., notepad, chrome), ALWAYS wait 1.5 to 2 seconds using "
        "`import time; time.sleep(2)` to let the app load and focus before typing or clicking. "
        "2. When typing text using `pyautogui.write()`, ALWAYS use the interval parameter "
        "(e.g., `pyautogui.write('text', interval=0.05)`) to prevent dropped characters. "
        "3. Use keyboard shortcuts (like Win+R, Ctrl+S) for opening or saving files instead "
        "of manual mouse clicks when possible, as shortcuts are much more reliable."
    ),
    "interpreter_available": INTERPRETER_AVAILABLE,
}
