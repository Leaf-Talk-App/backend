from pydantic import BaseModel
from typing import Optional

class UpdateUserSchema(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    searchable: Optional[bool] = None
    
class BlockUserSchema(BaseModel):
    user_id: str