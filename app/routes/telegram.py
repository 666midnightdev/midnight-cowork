import asyncio
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import APIRouter, BackgroundTasks

from app.config import interpreter
from app.services.interpreter import apply_settings_to_interpreter
from app.services.telegram import telegram_state
from app.services.workflows import (
    WorkflowManager,
    fetch_claude_output,
    gui_run_claude,
    gui_start_workflow,
    is_workflow_trigger,
    workflow_manager,
)
from app.storage import load_chats, save_chats

router = APIRouter()

TELEGRAM_SESSIONS_FILE = "telegram_sessions.json"


def _load_tg_sessions() -> dict:
    import os
    from app.config import BASE_DIR

    path = os.path.join(BASE_DIR, TELEGRAM_SESSIONS_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_tg_sessions(sessions: dict) -> None:
    import os
    from app.config import BASE_DIR

    path = os.path.join(BASE_DIR, TELEGRAM_SESSIONS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


@router.get("/api/telegram/status")
async def get_telegram_status() -> dict:
    return {
        "status": telegram_state.status,
        "bot_username": telegram_state.bot_username,
    }


@router.post("/api/telegram/start")
async def start_telegram(req: dict) -> dict:
    token = req.get("token", "").strip()
    if not token:
        return {"status": "error", "message": "Token kosong"}

    telegram_state.token = token
    telegram_state.status = "connecting"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{telegram_state.api_url}/getMe")
        data = resp.json()

    if not data.get("ok"):
        telegram_state.status = "disconnected"
        return {"status": "error", "message": "Token tidak valid"}

    bot_info = data["result"]
    telegram_state.bot_username = bot_info.get("username", "unknown")
    telegram_state.status = "connected"
    telegram_state._polling = True

    thread = threading.Thread(target=_polling_loop, daemon=True)
    thread.start()
    telegram_state._thread = thread

    return {"status": "success", "bot_username": telegram_state.bot_username}


@router.post("/api/telegram/stop")
async def stop_telegram() -> dict:
    telegram_state.stop_polling()
    telegram_state.reset()
    return {"status": "success"}


def _polling_loop() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while telegram_state._polling:
        try:
            resp = httpx.get(
                f"{telegram_state.api_url}/getUpdates",
                params={"offset": telegram_state._offset, "timeout": 10},
                timeout=15.0,
            )
            data = resp.json()

            if not data.get("ok"):
                break

            for update in data.get("result", []):
                telegram_state._offset = update["update_id"] + 1
                loop.run_until_complete(_process_update(update))

        except Exception:
            break

    telegram_state.status = "disconnected"


async def _process_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip()
    from_user = msg.get("from", {})
    username = from_user.get("username") or from_user.get("first_name") or str(chat_id)
    is_bot = from_user.get("is_bot", False)

    if not chat_id or not text or is_bot:
        return

    sender_key = f"tg_{chat_id}"

    if text.lower() == "/start":
        await _tg_send(chat_id, "🤖 *Midnight Cowork Telegram Bot*\n\nKetik perintah apa saja, atau:\n• /new — Sesi baru\n• /stop — Hentikan sesi\n• /help — Bantuan\n• *pola kerja* — Claude remote")
        return

    if text.lower() == "/new":
        await _handle_new_session_tg(sender_key, chat_id)
        return

    if text.lower() in ("/stop", "/stoppercakapan"):
        await _handle_stop_tg(sender_key, chat_id)
        return

    if text.lower() == "/help":
        await _tg_send(chat_id, (
            "🤖 *Midnight Cowork Commands:*\n\n"
            "• */new* : Mulai sesi baru\n"
            "• */stop* : Hentikan sesi\n"
            "• *pola kerja* : Mode Claude remote\n"
            "• *Ketik apa saja* : Eksekusi otomatis"
        ))
        return

    if is_workflow_trigger(text):
        workflow_manager.set_state(sender_key, WorkflowManager.WAITING_PROMPT)
        await _run_visual_workflow_tg(sender_key, chat_id)
        return

    if workflow_manager.is_waiting_prompt(sender_key):
        await _handle_workflow_prompt_tg(sender_key, chat_id, text)
        return

    sessions = _load_tg_sessions()
    active_chat_id = sessions.get(sender_key)

    if not active_chat_id:
        active_chat_id = str(uuid.uuid4())
        new_chat = {"id": active_chat_id, "title": "Telegram Baru", "messages": []}
        current_chats = load_chats()
        current_chats.insert(0, new_chat)
        save_chats(current_chats)
        sessions[sender_key] = active_chat_id
        _save_tg_sessions(sessions)

    await _run_tg_interpreter(chat_id, sender_key, text, active_chat_id)


async def _tg_send(chat_id: int, text: str) -> None:
    if not telegram_state.token:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{telegram_state.api_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            if resp.status_code == 400:
                await client.post(
                    f"{telegram_state.api_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
    except Exception:
        pass


async def _handle_new_session_tg(sender_key: str, chat_id: int) -> None:
    new_chat_id = str(uuid.uuid4())
    new_chat = {"id": new_chat_id, "title": "Telegram Baru", "messages": []}
    current_chats = load_chats()
    current_chats.insert(0, new_chat)
    save_chats(current_chats)

    sessions = _load_tg_sessions()
    sessions[sender_key] = new_chat_id
    _save_tg_sessions(sessions)

    await _tg_send(chat_id, "🆕 *Sesi baru dibuat.* Midnight Cowork siap!")


async def _handle_stop_tg(sender_key: str, chat_id: int) -> None:
    workflow_manager.reset(sender_key)
    if interpreter is not None:
        interpreter.messages = []
    await _tg_send(chat_id, "⏹️ *Percakapan dihentikan.*")


async def _run_visual_workflow_tg(sender_key: str, chat_id: int) -> None:
    loop = asyncio.get_running_loop()
    try:
        await _tg_send(chat_id, "Memulai pola kerja...")
        await _tg_send(chat_id, "Membuka WSL...")
        await loop.run_in_executor(None, gui_start_workflow)
        await _tg_send(chat_id, "claude : (Ketik Prompt anda untuk Claude)")
    except Exception as e:
        await _tg_send(chat_id, f"Error workflow: {e}")
        workflow_manager.reset(sender_key)


async def _handle_workflow_prompt_tg(sender_key: str, chat_id: int, prompt: str) -> None:
    workflow_manager.reset(sender_key)
    await _tg_send(chat_id, "Menjalankan prompt di Claude...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, gui_run_claude, prompt)
    output = await loop.run_in_executor(None, fetch_claude_output)
    if len(output) > 4000:
        output = output[:4000] + "\n\n... (dipotong)"
    await _tg_send(chat_id, f"*Hasil Claude:*\n\n{output}")


async def _run_tg_interpreter(chat_id: int, sender_key: str, message: str, active_chat_id: str) -> None:
    await _tg_send(chat_id, "⏳ _Memproses perintah..._")

    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    chats = load_chats()
    active_chat = None
    for chat in chats:
        if chat["id"] == active_chat_id:
            active_chat = chat
            break

    if not active_chat:
        return

    def execute() -> str:
        apply_settings_to_interpreter()
        interpreter.messages = active_chat.get("messages", [])

        response_text = ""
        last_type = None

        try:
            for chunk in interpreter.chat(message, display=False, stream=True):
                chunk_type = chunk.get("type")
                content = chunk.get("content", "")

                if chunk.get("start") is True:
                    if chunk_type == "code":
                        fmt = chunk.get("format", "code")
                        response_text += f"\n\n*💻 Kode ({fmt}):*\n```"
                    elif chunk_type == "console":
                        response_text += "\n\n*📟 Output:*\n```\n"
                    last_type = chunk_type

                if content:
                    response_text += str(content)

                if chunk.get("end") is True:
                    if last_type == "code":
                        response_text += "```"
                    elif last_type == "console":
                        response_text += "\n```"
                    last_type = None

            active_chat["messages"] = interpreter.messages

        except Exception as e:
            err_msg = str(e)
            if "display_markdown_message" in err_msg or isinstance(e, NameError):
                err_msg = "⚠️ Batas Quota / Rate Limit."
            response_text += f"\n\n❌ *Error:* {err_msg}"

        _sync_tg_chat(active_chat_id, message, active_chat)
        return response_text

    final_response = await loop.run_in_executor(executor, execute)

    if not final_response:
        final_response = "Asisten selesai tanpa output."

    await _tg_send(chat_id, final_response.strip())


def _sync_tg_chat(active_chat_id: str, message: str, active_chat: dict) -> None:
    current_chats = load_chats()
    for idx, c in enumerate(current_chats):
        if c["id"] == active_chat_id:
            current_chats[idx]["messages"] = interpreter.messages
            if current_chats[idx]["title"] in ("Telegram Baru", "Percakapan Baru"):
                current_chats[idx]["title"] = (
                    message[:30] + "..." if len(message) > 30 else message
                )
            break
    save_chats(current_chats)
