from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user
from app.core.ratelimit import limiter
from .schemas import (
    SendMessageSchema,
    EditMessageSchema
)

from .service import (
    send_message,
    get_messages,
    mark_as_read,
    edit_message,
    delete_message,
    delete_message_for_me,
    toggle_favorite,
    clear_chat
)

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)


@router.post("/send")
@limiter.limit("60/minute")
async def send(
    request: Request,
    data: SendMessageSchema,
    user=Depends(get_current_user)
):
    return await send_message(user, data)


@router.get("/{chat_id}")
async def history(
    chat_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_current_user),
):
    return await get_messages(chat_id, skip=skip, limit=min(limit, 100), user_id=user["sub"])


@router.post("/clear/{chat_id}")
async def clear(
    chat_id: str,
    user=Depends(get_current_user),
):
    return await clear_chat(chat_id, user)


@router.patch("/read/{chat_id}")
async def read_messages(
    chat_id: str,
    user=Depends(get_current_user)
):
    return await mark_as_read(chat_id, user)


@router.patch("/edit/{message_id}")
async def edit(
    message_id: str,
    data: EditMessageSchema,
    user=Depends(get_current_user)
):
    return await edit_message(
        user,
        message_id,
        data.content
    )


@router.post("/{message_id}/delete-for-me")
async def delete_for_me(
    message_id: str,
    user=Depends(get_current_user)
):
    return await delete_message_for_me(user, message_id)


@router.post("/{message_id}/favorite")
async def favorite(
    message_id: str,
    user=Depends(get_current_user)
):
    return await toggle_favorite(user, message_id)


@router.delete("/{message_id}")
async def delete(
    message_id: str,
    user=Depends(get_current_user)
):
    return await delete_message(
        user,
        message_id
    )