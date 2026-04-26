from pydantic import BaseModel
from typing import List

class CreateGroupSchema(BaseModel):
    name: str
    members: List[str]

class AddMemberSchema(BaseModel):
    group_id: str
    user_id: str

class SendGroupMessageSchema(BaseModel):
    group_id: str
    content: str

class RemoveMemberSchema(BaseModel):
    group_id: str
    user_id: str