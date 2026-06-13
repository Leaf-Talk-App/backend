from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import AIMessageSchema
from .service import ask_ai, confirm_task, get_ai_history, clear_ai_history

router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)

@router.post("/chat")
async def chat_ai(
    data: AIMessageSchema,
    user=Depends(get_current_user)
):
    return await ask_ai(
        data.message,
        user,
        data.attachment_url,
        data.attachment_mime,
        data.timezone,
        data.tz_offset,
    )

@router.post("/confirm/{task_id}")
async def confirm(
    task_id: str,
    user=Depends(get_current_user)
):
    return await confirm_task(user, task_id)

@router.get("/history")
async def history(
    user=Depends(get_current_user)
):
    return await get_ai_history(user)

@router.post("/history/clear")
async def clear_history(
    user=Depends(get_current_user)
):
    return await clear_ai_history(user)