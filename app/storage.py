import json
import os
import tempfile
import threading
from typing import Any

from app.config import (
    CHATS_FILE,
    DEFAULT_SETTINGS,
    INTERPRETER_AVAILABLE,
    SETTINGS_FILE,
    WHATSAPP_SESSIONS_FILE,
)

_file_lock = threading.Lock()


def _safe_read(filepath: str, default: Any = None) -> Any:
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _safe_write(filepath: str, data: Any) -> None:
    with _file_lock:
        dir_name = os.path.dirname(filepath)
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=dir_name,
                delete=False,
                suffix=".tmp",
            ) as tmp:
                json.dump(data, tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            os.replace(tmp_path, filepath)
        except OSError:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


def load_chats() -> list[dict]:
    return _safe_read(CHATS_FILE, [])


def save_chats(chats: list[dict]) -> None:
    _safe_write(CHATS_FILE, chats)


def load_settings() -> dict:
    saved = _safe_read(SETTINGS_FILE, {})
    return {**DEFAULT_SETTINGS, **saved, "interpreter_available": INTERPRETER_AVAILABLE}


def save_settings(settings: dict) -> None:
    _safe_write(SETTINGS_FILE, settings)


def load_whatsapp_sessions() -> dict:
    return _safe_read(WHATSAPP_SESSIONS_FILE, {})


def save_whatsapp_sessions(sessions: dict) -> None:
    _safe_write(WHATSAPP_SESSIONS_FILE, sessions)
