from pydantic import BaseModel
from typing import List, Optional

class CreateGroupSchema(BaseModel):
    name: str
    members: List[str] = []

class AddMemberSchema(BaseModel):
    group_id: str
    user_id: str

class RemoveMemberSchema(BaseModel):
    group_id: str
    user_id: str

class SendGroupMessageSchema(BaseModel):
    group_id: str
    content: str = ""
    type: Optional[str] = "text"
    file_url: Optional[str] = None
