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
from .service import my_chats
from datetime import datetime
from app.core.database import db
from app.modules.chats.serializers import serialize_chat

router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)

@router.post("/")
async def create_chat(
    data: CreateChatSchema,
    current_user=Depends(get_current_user)
):
    members = list(set(data.user_ids + [current_user["id"]]))

    chat = {
        "members": members,
        "is_group": data.is_group,
        "name": data.name,
        "created_at": datetime.utcnow(),
        "last_message": None,
        "last_message_at": None
    }

    result = await db.chats.insert_one(chat)

    chat["_id"] = result.inserted_id

    return serialize_chat(chat)

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

@router.get("/my")
async def my(
    user=Depends(get_current_user)
):
    return await my_chats(user)