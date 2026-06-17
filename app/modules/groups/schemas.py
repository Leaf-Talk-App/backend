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

class UpdateGroupSchema(BaseModel):
    group_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    only_admins_can_send: Optional[bool] = None
    photo: Optional[str] = None

class SetAdminSchema(BaseModel):
    group_id: str
    user_id: str
    make_admin: bool = True

class SendGroupMessageSchema(BaseModel):
    group_id: str
    content: str = ""
    type: Optional[str] = "text"
    file_url: Optional[str] = None
    reply_to: Optional[str] = None
