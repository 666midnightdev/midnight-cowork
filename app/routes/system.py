import os
import signal
import sys

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import HTMLResponse

from app.config import BASE_DIR, INTERPRETER_AVAILABLE

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_index() -> str:
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found. Please verify templates folder.</h1>"


@router.get("/api/status")
async def get_status() -> dict:
    return {
        "interpreter_available": INTERPRETER_AVAILABLE,
        "python_version": sys.version,
        "os": sys.platform,
    }


def _shutdown_process() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


@router.post("/api/shutdown")
async def shutdown(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_shutdown_process)
    return {"message": "Shutting down FastAPI server..."}
