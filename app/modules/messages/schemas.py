from pydantic import BaseModel
from typing import Optional

class SendMessageSchema(BaseModel):
    chat_id: str
    receiver_id: str
    content: str = ""
    type: str = "text"
    file_url: Optional[str] = None
    reply_to: Optional[str] = None
    
class ReactMessageSchema(BaseModel):
    message_id: str
    emoji: str