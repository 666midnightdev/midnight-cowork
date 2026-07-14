import os
from typing import Optional

from app.config import INTERPRETER_AVAILABLE, interpreter
from app.storage import load_settings


def apply_settings_to_interpreter() -> None:
    if not INTERPRETER_AVAILABLE or interpreter is None:
        return

    settings = load_settings()
    model: str = settings.get("model", "")
    api_key: str = settings.get("api_key", "")

    if model:
        interpreter.llm.model = model

    if api_key:
        interpreter.llm.api_key = api_key
        _set_provider_env(model, api_key)

    _configure_context_window(model)

    interpreter.auto_run = settings.get("auto_run", True)
    system_msg: Optional[str] = settings.get("system_message")
    if system_msg:
        interpreter.system_message = system_msg


def _set_provider_env(model: str, api_key: str) -> None:
    if model.startswith(("huggingface/", "hf/")):
        os.environ["HF_API_KEY"] = api_key
        os.environ["HUGGINGFACE_API_KEY"] = api_key
    elif model.startswith("groq/"):
        os.environ["GROQ_API_KEY"] = api_key
    elif model.startswith(("anthropic/", "claude")):
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif model.startswith("gemini/"):
        os.environ["GEMINI_API_KEY"] = api_key
    else:
        os.environ["OPENAI_API_KEY"] = api_key


def _configure_context_window(model: str) -> None:
    if not INTERPRETER_AVAILABLE or interpreter is None:
        return

    if model.startswith("groq/"):
        if "8b" in model:
            interpreter.llm.context_window = 3000
            interpreter.llm.max_tokens = 800
        else:
            interpreter.llm.context_window = 6000
            interpreter.llm.max_tokens = 1500
    else:
        interpreter.llm.context_window = 16000
        interpreter.llm.max_tokens = 4096
