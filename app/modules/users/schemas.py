from pydantic import BaseModel

class UpdateProfileSchema(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar: str | None = None
    searchable: bool | None = None
    
class BlockUserSchema(BaseModel):
    user_id: str