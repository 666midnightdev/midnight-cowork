import json
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import INTERPRETER_AVAILABLE, interpreter
from app.models import ChatRequest
from app.storage import load_chats, save_chats
from app.services.interpreter import apply_settings_to_interpreter

router = APIRouter()


@router.get("/api/chats")
async def get_all_chats() -> list[dict]:
    chats = load_chats()
    return [{"id": c["id"], "title": c["title"]} for c in chats]


@router.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str) -> dict:
    chats = load_chats()
    for chat in chats:
        if chat["id"] == chat_id:
            return chat
    raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/api/chats")
async def create_chat() -> dict:
    chats = load_chats()
    new_chat = {
        "id": "chat_" + uuid.uuid4().hex[:12],
        "title": "Percakapan Baru",
        "messages": [],
    }
    chats.insert(0, new_chat)
    save_chats(chats)
    return new_chat


@router.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str) -> dict:
    chats = load_chats()
    filtered = [c for c in chats if c["id"] != chat_id]
    if len(filtered) == len(chats):
        raise HTTPException(status_code=404, detail="Chat not found")
    save_chats(filtered)
    return {"status": "success"}


@router.post("/api/chat")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    if not INTERPRETER_AVAILABLE:
        return StreamingResponse(_mock_generator(), media_type="text/event-stream")

    chats = load_chats()
    active_chat = None
    for chat in chats:
        if chat["id"] == req.chat_id:
            active_chat = chat
            break

    if not active_chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    interpreter.messages = active_chat.get("messages", [])  # type: ignore[union-attr]

    if active_chat["title"] == "Percakapan Baru":
        title = req.message[:30] + "..." if len(req.message) > 30 else req.message
        active_chat["title"] = title
        save_chats(chats)

    return StreamingResponse(
        _event_generator(req.message, req.chat_id, active_chat),
        media_type="text/event-stream",
    )


async def _mock_generator():  # type: ignore[no-untyped-def]
    chunks = [
        {"role": "assistant", "type": "message", "start": True},
        {
            "role": "assistant",
            "type": "message",
            "content": "### ⚠️ Midnight Cowork (Open Interpreter) Tidak Terdeteksi\n\n",
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "Paket Python `open-interpreter` belum terinstal di sistem Anda.\n\n",
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "Untuk menggunakannya, silakan instal melalui command prompt dengan perintah:\n\n",
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "```bash\npip install open-interpreter\n```\n\n",
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "Setelah itu, matikan server dengan `stop.bat` lalu jalankan kembali `start.bat`.",
        },
        {"role": "assistant", "type": "message", "end": True},
    ]
    for chunk in chunks:
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)


_RATE_LIMIT_ERROR = (
    "### ⚠️ Batas Quota / Rate Limit Terlampaui (Groq Free Tier)\n\n"
    "Open Interpreter mengalami kegagalan karena batasan **Tokens Per Minute (TPM)** "
    "pada akun Groq Free Tier Anda.\n\n"
    "**Solusi:**\n"
    "1. **Buat Percakapan Baru** di sidebar untuk mengosongkan riwayat obrolan.\n"
    "2. Ubah model ke **`groq/llama-3.3-70b-versatile`** (TPM lebih besar).\n"
    "3. Gunakan penyedia API berbayar atau alternatif gratis (Gemini).\n"
    "4. Tunggu 1 menit lalu coba kembali."
)


async def _event_generator(  # type: ignore[no-untyped-def]
    message: str,
    chat_id: str,
    active_chat: dict,
):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    queue: asyncio.Queue = asyncio.Queue()

    def run_interpreter() -> None:
        try:
            apply_settings_to_interpreter()
            for chunk in interpreter.chat(message, display=False, stream=True):  # type: ignore[union-attr]
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
        except Exception as e:
            error_msg = str(e)
            if "display_markdown_message" in error_msg or isinstance(e, NameError):
                error_msg = _RATE_LIMIT_ERROR
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "content": error_msg})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(executor, run_interpreter)

    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield f"data: {json.dumps(chunk)}\n\n"

    _save_chat_messages(chat_id, active_chat)


def _save_chat_messages(chat_id: str, active_chat: dict) -> None:
    active_chat["messages"] = interpreter.messages  # type: ignore[union-attr]
    current_chats = load_chats()
    for idx, c in enumerate(current_chats):
        if c["id"] == chat_id:
            current_chats[idx]["messages"] = interpreter.messages  # type: ignore[union-attr]
            current_chats[idx]["title"] = active_chat["title"]
            break
    save_chats(current_chats)
