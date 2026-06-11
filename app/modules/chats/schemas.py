from pydantic import BaseModel
from typing import List, Optional

class CreateChatSchema(BaseModel):
    user_ids: List[str]
    is_group: bool = False
    name: Optional[str] = None

class CreateDirectChatSchema(BaseModel):
    user_id: str

class ChatActionSchema(BaseModel):
    chat_id: str
    # Silenciar: minutos de duração (>0). None = para sempre (quando muting).
    mute_minutes: Optional[int] = None
    # Reativar notificações.
    unmute: Optional[bool] = False