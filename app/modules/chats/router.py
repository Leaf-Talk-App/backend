from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import CreateChatSchema
from .service import create_chat, list_chats
from .schemas import ChatActionSchema
from .service import (
    archive_chat,
    pin_chat,
    mute_chat,
    hide_chat
)

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

@router.post("/archive")
async def archive(
    data: ChatActionSchema,
    user=Depends(get_current_user)
):
    return await archive_chat(user, data)


@router.post("/pin")
async def pin(
    data: ChatActionSchema,
    user=Depends(get_current_user)
):
    return await pin_chat(user, data)


@router.post("/mute")
async def mute(
    data: ChatActionSchema,
    user=Depends(get_current_user)
):
    return await mute_chat(user, data)


@router.post("/hide")
async def hide(
    data: ChatActionSchema,
    user=Depends(get_current_user)
):
    return await hide_chat(user, data)