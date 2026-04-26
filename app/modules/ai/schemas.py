from pydantic import BaseModel

class AIMessageSchema(BaseModel):
    message: str
    
class TextSchema(BaseModel):
    text: str

class TranslateSchema(BaseModel):
    text: str
    language: str

class ConversationSchema(BaseModel):
    chat_id: str