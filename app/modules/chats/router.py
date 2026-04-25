from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import CreateChatSchema
from .service import create_chat, list_chats

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)

@router.post("/create")
async def new_chat(
    data: CreateChatSchema,
    user=Depends(get_current_user)
):
    return await create_chat(user, data)

@router.get("/")
async def get_chats(
    user=Depends(get_current_user)
):
    return await list_chats(user)