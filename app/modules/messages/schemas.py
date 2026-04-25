from pydantic import BaseModel

class SendMessageSchema(BaseModel):
    chat_id: str
    receiver_id: str
    content: str