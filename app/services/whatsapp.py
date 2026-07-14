import subprocess
from typing import Optional


class WhatsAppState:
    def __init__(self) -> None:
        self.qr: Optional[str] = None
        self.pairing_code: Optional[str] = None
        self.status: str = "disconnected"
        self.phone: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self._reply_to: dict[str, str] = {}

    def set_reply_to(self, sender: str, jid: str) -> None:
        self._reply_to[sender] = jid

    def get_reply_to(self, sender: str) -> str:
        return self._reply_to.get(sender, sender)

    def reset(self) -> None:
        self.qr = None
        self.pairing_code = None
        self.status = "disconnected"
        self.phone = None
        self._reply_to.clear()

    def terminate_process(self) -> None:
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=3)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self.process = None


whatsapp_state = WhatsAppState()
