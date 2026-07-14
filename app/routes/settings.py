from fastapi import APIRouter

from app.models import SettingsUpdate
from app.storage import load_settings, save_settings
from app.services.interpreter import apply_settings_to_interpreter

router = APIRouter()


@router.get("/api/settings")
async def get_settings() -> dict:
    return load_settings()


@router.post("/api/settings")
async def update_settings(settings_upd: SettingsUpdate) -> dict:
    settings = load_settings()

    if settings_upd.model is not None:
        settings["model"] = settings_upd.model
    if settings_upd.api_key is not None:
        settings["api_key"] = settings_upd.api_key
    if settings_upd.auto_run is not None:
        settings["auto_run"] = settings_upd.auto_run
    if settings_upd.system_message is not None:
        settings["system_message"] = settings_upd.system_message

    save_settings(settings)
    apply_settings_to_interpreter()
    return settings
