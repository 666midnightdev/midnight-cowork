import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import BASE_DIR


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        _auto_start_whatsapp()
        yield

    application = FastAPI(title="Midnight Cowork", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.mount(
        "/static",
        StaticFiles(directory=os.path.join(BASE_DIR, "static")),
        name="static",
    )

    from app.routes import chat, settings, system, telegram, whatsapp

    application.include_router(system.router)
    application.include_router(chat.router)
    application.include_router(settings.router)
    application.include_router(whatsapp.router)
    application.include_router(telegram.router)

    return application


def _auto_start_whatsapp() -> None:
    import subprocess
    import sys

    from app.config import BASE_DIR
    from app.services.whatsapp import whatsapp_state

    auth_dir = os.path.join(BASE_DIR, "whatsapp", "auth_info")
    if not os.path.exists(auth_dir):
        return

    node_exe = os.path.join(BASE_DIR, "node_bin", "node.exe")
    index_js = os.path.join(BASE_DIR, "whatsapp", "index.js")
    if not os.path.exists(node_exe) or not os.path.exists(index_js):
        return

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
    except Exception:
        whatsapp_state.status = "disconnected"
