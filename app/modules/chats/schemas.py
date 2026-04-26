from pydantic import BaseModel

class CreateChatSchema(BaseModel):
    user_id: str
    
class ChatActionSchema(BaseModel):
    chat_id: str