from pydantic import BaseModel
from typing import List, Optional

class CreateChatSchema(BaseModel):
    user_ids: List[str]
    is_group: bool = False
    name: Optional[str] = None
    
class ChatActionSchema(BaseModel):
    chat_id: str