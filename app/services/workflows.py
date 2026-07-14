from __future__ import annotations

import os
import subprocess
import time
from typing import Optional

import paramiko
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

SERVER_HOST = os.environ.get("MIDNIGHT_SSH_HOST", "")
SERVER_PORT = int(os.environ.get("MIDNIGHT_SSH_PORT", "22"))
SERVER_USER = os.environ.get("MIDNIGHT_SSH_USER", "")
SERVER_PASSWORD = os.environ.get("MIDNIGHT_SSH_PASSWORD", "")
REMOTE_DIR = os.environ.get("MIDNIGHT_SSH_DIR", "")

WORKFLOW_TRIGGERS = ["pola kerja", "lakukan pola kerja", "oi lakukan pola kerja"]

OPEN_WSL_DELAY = 3
SSH_CONNECT_DELAY = 5
AUTH_DELAY = 3
CD_DELAY = 1
CLAUDE_RESPONSE_DELAY = 60


class WorkflowManager:
    IDLE = "idle"
    WAITING_PROMPT = "waiting_prompt"

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def get_state(self, sender: str) -> str:
        return self._states.get(sender, self.IDLE)

    def set_state(self, sender: str, state: str) -> None:
        self._states[sender] = state

    def reset(self, sender: str) -> None:
        self._states.pop(sender, None)

    def is_waiting_prompt(self, sender: str) -> bool:
        return self.get_state(sender) == self.WAITING_PROMPT


workflow_manager = WorkflowManager()


def is_workflow_trigger(text: str) -> bool:
    lower = text.lower().strip()
    return any(trigger in lower for trigger in WORKFLOW_TRIGGERS)


# ── GUI Automation (pyautogui) ──────────────────────────────────


def gui_open_wsl() -> None:
    subprocess.Popen(["cmd", "/c", "start", "wsl.exe"])
    time.sleep(OPEN_WSL_DELAY)


def gui_type(text: str, enter: bool = True, interval: float = 0.03) -> None:
    pyautogui.write(text, interval=interval)
    time.sleep(0.3)
    if enter:
        pyautogui.press("enter")
        time.sleep(0.3)


def gui_start_workflow() -> None:
    gui_open_wsl()
    gui_type(f"ssh {SERVER_USER}@{SERVER_HOST}")
    time.sleep(SSH_CONNECT_DELAY)
    if SERVER_PASSWORD:
        gui_type(SERVER_PASSWORD)
    time.sleep(AUTH_DELAY)
    gui_type(f"cd {REMOTE_DIR}")
    time.sleep(CD_DELAY)


def gui_run_claude(prompt: str) -> None:
    escaped = prompt.replace('"', '\\"')
    gui_type(f'claude -p "{escaped}" 2>&1 | tee /tmp/midnight_output.txt')
    time.sleep(CLAUDE_RESPONSE_DELAY)


# ── SSH (paramiko) for output capture ───────────────────────────


def run_remote_command(command: str, timeout: int = 120) -> str:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            SERVER_HOST,
            port=SERVER_PORT,
            username=SERVER_USER,
            password=SERVER_PASSWORD,
            timeout=15,
        )
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode().strip()
        errors = stderr.read().decode().strip()
        client.close()

        if errors and not output:
            return f"Error:\n{errors}"
        return output or "Perintah berhasil dieksekusi (tidak ada output)."
    except paramiko.AuthenticationException:
        return "Error: Autentikasi SSH gagal. Periksa password."
    except paramiko.SSHException as e:
        return f"Error SSH: {e}"
    except Exception as e:
        return f"Error koneksi: {e}"


def fetch_claude_output() -> str:
    return run_remote_command("cat /tmp/midnight_output.txt 2>&1", timeout=10)
