from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import SendMessageSchema
from .service import send_message, get_messages

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

@router.post("/send")
async def send(
    data: SendMessageSchema,
    user=Depends(get_current_user)
):
    return await send_message(user, data)

@router.get("/{chat_id}")
async def history(
    chat_id: str,
    user=Depends(get_current_user)
):
    return await get_messages(chat_id)