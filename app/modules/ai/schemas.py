from pydantic import BaseModel
from typing import Optional

class AIMessageSchema(BaseModel):
    message: str
    attachment_url: Optional[str] = None
    attachment_mime: Optional[str] = None
    # Fuso do usuário (para agendar no horário certo dele, não num fixo).
    # timezone = nome IANA ("America/Sao_Paulo"); tz_offset = minutos do
    # JS getTimezoneOffset() (BR = 180) como fallback se o IANA falhar.
    timezone: Optional[str] = None
    tz_offset: Optional[int] = None

class TextSchema(BaseModel):
    text: str

class TranslateSchema(BaseModel):
    text: str
    language: str

class ConversationSchema(BaseModel):
    chat_id: str