from pydantic import BaseModel
from typing import Optional

class AIMessageSchema(BaseModel):
    message: str
    attachment_url: Optional[str] = None
    attachment_mime: Optional[str] = None

class TextSchema(BaseModel):
    text: str

class TranslateSchema(BaseModel):
    text: str
    language: str

class ConversationSchema(BaseModel):
    chat_id: str