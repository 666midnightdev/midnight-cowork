from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    chat_id: str


class SettingsUpdate(BaseModel):
    model: Optional[str] = None
    api_key: Optional[str] = None
    auto_run: Optional[bool] = None
    system_message: Optional[str] = None


class WhatsAppQRRequest(BaseModel):
    qr: str


class WhatsAppPairingCodeRequest(BaseModel):
    code: str


class WhatsAppStatusRequest(BaseModel):
    status: str
    phone: Optional[str] = None


class WhatsAppMessageRequest(BaseModel):
    text: str
    sender: str
    reply_to: Optional[str] = None
