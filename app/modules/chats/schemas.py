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