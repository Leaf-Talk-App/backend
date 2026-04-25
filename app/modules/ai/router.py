from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import AIMessageSchema
from .service import ask_ai

router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)

@router.post("/chat")
async def chat_ai(
    data: AIMessageSchema,
    user=Depends(get_current_user)
):
    return await ask_ai(data.message)