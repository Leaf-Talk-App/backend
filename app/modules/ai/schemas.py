from pydantic import BaseModel

class AIMessageSchema(BaseModel):
    message: str