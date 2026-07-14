import asyncio
import threading
from typing import Optional

TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramState:
    def __init__(self) -> None:
        self.token: Optional[str] = None
        self.status: str = "disconnected"
        self.bot_username: Optional[str] = None
        self._offset: int = 0
        self._polling: bool = False
        self._thread: Optional[threading.Thread] = None

    def reset(self) -> None:
        self.token = None
        self.status = "disconnected"
        self.bot_username = None
        self._offset = 0
        self._polling = False

    def stop_polling(self) -> None:
        self._polling = False

    @property
    def api_url(self) -> str:
        return TELEGRAM_API.format(token=self.token) if self.token else ""


telegram_state = TelegramState()
