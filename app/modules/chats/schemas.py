from pydantic import BaseModel

class CreateChatSchema(BaseModel):
    user_id: str