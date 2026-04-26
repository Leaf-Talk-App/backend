from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import AIMessageSchema
from .service import ask_ai
from .service import confirm_task

router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)

@router.post("/chat")
async def chat_ai(
    data: AIMessageSchema,
    user=Depends(get_current_user)
):
    return await ask_ai(data.message, user)

@router.post("/confirm/{task_id}")
async def confirm(
    task_id: str,
    user=Depends(get_current_user)
):
    return await confirm_task(user, task_id)