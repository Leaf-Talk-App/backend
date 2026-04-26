from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import (
    SendMessageSchema,
    EditMessageSchema
)

from .service import (
    send_message,
    get_messages,
    mark_as_read,
    edit_message,
    delete_message
)

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


@router.delete("/{message_id}")
async def delete(
    message_id: str,
    user=Depends(get_current_user)
):
    return await delete_message(
        user,
        message_id
    )