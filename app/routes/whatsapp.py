import asyncio
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import APIRouter, BackgroundTasks

from app.config import BASE_DIR, interpreter
from app.models import WhatsAppMessageRequest, WhatsAppPairingCodeRequest, WhatsAppQRRequest, WhatsAppStatusRequest
from app.services.interpreter import apply_settings_to_interpreter
from app.services.whatsapp import whatsapp_state
from app.services.workflows import (
    WorkflowManager,
    fetch_claude_output,
    gui_run_claude,
    gui_start_workflow,
    is_workflow_trigger,
    workflow_manager,
)
from app.storage import (
    load_chats,
    load_whatsapp_sessions,
    save_chats,
    save_whatsapp_sessions,
)

router = APIRouter()

NODE_SEND_URL = "http://localhost:8001/send"


@router.get("/api/whatsapp/status")
async def get_whatsapp_status() -> dict:
    return {
        "status": whatsapp_state.status,
        "phone": whatsapp_state.phone,
        "qr": whatsapp_state.qr,
        "pairing_code": whatsapp_state.pairing_code,
    }


@router.post("/api/whatsapp/status")
async def post_whatsapp_status(req: WhatsAppStatusRequest) -> dict:
    whatsapp_state.status = req.status
    whatsapp_state.phone = req.phone
    if req.status == "connected":
        whatsapp_state.qr = None
    return {"status": "success"}


@router.post("/api/whatsapp/qr")
async def post_whatsapp_qr(req: WhatsAppQRRequest) -> dict:
    whatsapp_state.status = "scan"
    whatsapp_state.qr = req.qr
    return {"status": "success"}


@router.post("/api/whatsapp/pairing-code")
async def post_whatsapp_pairing_code(req: WhatsAppPairingCodeRequest) -> dict:
    whatsapp_state.status = "pairing"
    whatsapp_state.pairing_code = req.code
    return {"status": "success"}


@router.post("/api/whatsapp/message")
async def post_whatsapp_message(
    req: WhatsAppMessageRequest, background_tasks: BackgroundTasks
) -> dict:
    text = req.text.strip()
    sender = req.sender
    if req.reply_to:
        whatsapp_state.set_reply_to(sender, req.reply_to)

    sessions = load_whatsapp_sessions()
    chat_id = sessions.get(sender)

    if text.lower() == "/new":
        return await _handle_new_session(sender, sessions)

    if text.lower() in ("/stoppercakapan", "/stop"):
        return await _handle_stop(sender)

    if text.lower() == "/help":
        return await _handle_help(sender)

    if is_workflow_trigger(text):
        return await _handle_workflow_trigger(sender)

    if workflow_manager.is_waiting_prompt(sender):
        return await _handle_workflow_prompt(sender, text)

    if not chat_id:
        chat_id = str(uuid.uuid4())
        new_chat = {"id": chat_id, "title": "Percakapan Baru", "messages": []}
        current_chats = load_chats()
        current_chats.insert(0, new_chat)
        save_chats(current_chats)
        sessions[sender] = chat_id
        save_whatsapp_sessions(sessions)

    background_tasks.add_task(_run_whatsapp_interpreter, sender, text, chat_id)
    return {"status": "queued"}


async def _handle_new_session(sender: str, sessions: dict) -> dict:
    new_chat_id = str(uuid.uuid4())
    new_chat = {"id": new_chat_id, "title": "Percakapan Baru", "messages": []}
    current_chats = load_chats()
    current_chats.insert(0, new_chat)
    save_chats(current_chats)

    sessions[sender] = new_chat_id
    save_whatsapp_sessions(sessions)

    await _wa_send(
        sender, "🆕 *Sesi obrolan baru telah dibuat.* Midnight Cowork siap menerima perintah Anda!"
    )
    return {"status": "success"}


async def _handle_stop(sender: str) -> dict:
    workflow_manager.reset(sender)
    if interpreter is not None:
        interpreter.messages = []  # type: ignore[union-attr]
    await _wa_send(sender, "⏹️ *Percakapan dihentikan.* State asisten telah dibersihkan.")
    return {"status": "success"}


async def _handle_help(sender: str) -> dict:
    help_text = (
        "🤖 *Midnight Cowork WhatsApp Commands:*\n\n"
        "• */new* : Memulai sesi percakapan baru (clear token)\n"
        "• */stop* : Menghentikan sesi aktif\n"
        "• *pola kerja* : Aktifkan mode Claude remote server\n"
        "• *Ketik perintah apa saja* : Asisten akan mengeksekusi secara otomatis"
    )
    await _wa_send(sender, help_text)
    return {"status": "success"}


async def _handle_workflow_trigger(sender: str) -> dict:
    workflow_manager.set_state(sender, WorkflowManager.WAITING_PROMPT)
    asyncio.create_task(_run_visual_workflow(sender))
    return {"status": "success"}


async def _run_visual_workflow(sender: str) -> None:
    loop = asyncio.get_running_loop()
    try:
        await _wa_send(sender, "Memulai pola kerja...")

        await _wa_send(sender, "Membuka WSL...")
        await loop.run_in_executor(None, gui_start_workflow)

        await _wa_send(sender, "claude : (Ketik Prompt anda untuk Claude)")
    except Exception as e:
        await _wa_send(sender, f"Error workflow: {e}")
        workflow_manager.reset(sender)


async def _handle_workflow_prompt(sender: str, prompt: str) -> dict:
    workflow_manager.reset(sender)
    await _wa_send(sender, "Menjalankan prompt di Claude...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, gui_run_claude, prompt)
    output = await loop.run_in_executor(None, fetch_claude_output)
    if len(output) > 4000:
        output = output[:4000] + "\n\n... (output dipotong)"
    await _wa_send(sender, f"*Hasil Claude:*\n\n{output}")
    return {"status": "success"}


async def _wa_send(to: str, text: str) -> None:
    try:
        reply_to = whatsapp_state.get_reply_to(to)
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(NODE_SEND_URL, json={"to": reply_to, "text": text})
    except Exception:
        pass


@router.post("/api/whatsapp/start")
async def start_whatsapp() -> dict:
    if whatsapp_state.process is not None and whatsapp_state.process.poll() is None:
        return {"status": "already_running"}

    node_exe = os.path.join(BASE_DIR, "node_bin", "node.exe")
    index_js = os.path.join(BASE_DIR, "whatsapp", "index.js")

    if not os.path.exists(node_exe) or not os.path.exists(index_js):
        return {
            "status": "error",
            "message": "Node.js portable belum terpasang. Jalankan setup terlebih dahulu.",
        }

    whatsapp_state.status = "connecting"

    node_dir = os.path.join(BASE_DIR, "node_bin")
    env = os.environ.copy()
    env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

    try:
        log_path = os.path.join(BASE_DIR, "whatsapp", "whatsapp_error.log")
        log_file = open(log_path, "w", encoding="utf-8")
        whatsapp_state.process = subprocess.Popen(
            [node_exe, index_js],
            cwd=os.path.join(BASE_DIR, "whatsapp"),
            env=env,
            stdout=log_file,
            stderr=log_file,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        log_file.close()
        return {"status": "success"}
    except Exception as e:
        whatsapp_state.status = "disconnected"
        return {"status": "error", "message": str(e)}


@router.post("/api/whatsapp/stop")
async def stop_whatsapp() -> dict:
    whatsapp_state.terminate_process()
    whatsapp_state.reset()
    return {"status": "success"}


@router.post("/api/whatsapp/unlink")
async def unlink_whatsapp() -> dict:
    await stop_whatsapp()

    auth_dir = os.path.join(BASE_DIR, "whatsapp", "auth_info")
    if os.path.exists(auth_dir):
        try:
            import shutil

            shutil.rmtree(auth_dir)
        except Exception as e:
            return {"status": "error", "message": f"Gagal menghapus sesi: {e}"}
    return {"status": "success"}


async def _run_whatsapp_interpreter(sender: str, message: str, chat_id: str) -> None:
    await _wa_send(sender, "⏳ _Midnight Cowork sedang memproses perintah Anda..._")

    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    chats = load_chats()
    active_chat = None
    for chat in chats:
        if chat["id"] == chat_id:
            active_chat = chat
            break

    if not active_chat:
        return

    def execute() -> str:
        apply_settings_to_interpreter()
        interpreter.messages = active_chat.get("messages", [])  # type: ignore[union-attr]

        response_text = ""
        last_type: str | None = None

        try:
            for chunk in interpreter.chat(message, display=False, stream=True):  # type: ignore[union-attr]
                chunk_type = chunk.get("type")
                content = chunk.get("content", "")

                if chunk.get("start") is True:
                    if chunk_type == "code":
                        fmt = chunk.get("format", "code")
                        response_text += f"\n\n*💻 Menjalankan Kode ({fmt}):*\n```"
                    elif chunk_type == "console":
                        response_text += "\n\n*📟 Output Konsol:*\n```\n"
                    last_type = chunk_type

                if content:
                    response_text += str(content)

                if chunk.get("end") is True:
                    if last_type == "code":
                        response_text += "```"
                    elif last_type == "console":
                        response_text += "\n```"
                    last_type = None

            active_chat["messages"] = interpreter.messages  # type: ignore[union-attr]

        except Exception as e:
            err_msg = str(e)
            if "display_markdown_message" in err_msg or isinstance(e, NameError):
                err_msg = "⚠️ Batas Quota / Rate Limit Terlampaui."
            response_text += f"\n\n❌ *Error:* {err_msg}"

        _sync_whatsapp_chat(chat_id, message, active_chat)
        return response_text

    final_response = await loop.run_in_executor(executor, execute)

    if not final_response:
        final_response = "Asisten menyelesaikan tugas tanpa output teks."

    await _wa_send(sender, final_response.strip())


def _sync_whatsapp_chat(chat_id: str, message: str, active_chat: dict) -> None:
    current_chats = load_chats()
    for idx, c in enumerate(current_chats):
        if c["id"] == chat_id:
            current_chats[idx]["messages"] = interpreter.messages  # type: ignore[union-attr]
            if current_chats[idx]["title"] == "Percakapan Baru":
                current_chats[idx]["title"] = (
                    message[:30] + "..." if len(message) > 30 else message
                )
            break
    save_chats(current_chats)
