from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId

from app.dependencies import get_current_user
from app.core.database import get_database
from .schemas import CreateChatSchema, CreateDirectChatSchema, ChatActionSchema
from .serializers import serialize_chat
from .service import (
    create_chat,
    list_chats,
    delete_chat,
    archive_chat,
    pin_chat,
    mute_chat,
    hide_chat,
    my_chats,
)

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post("/create")
async def create_direct_chat(
    data: CreateDirectChatSchema,
    current_user=Depends(get_current_user),
):
    return await create_chat(current_user, data)


@router.post("/")
async def create_chat_group(
    data: CreateChatSchema,
    current_user=Depends(get_current_user),
):
    db = get_database()
    members = list(set(data.user_ids + [current_user["sub"]]))

    chat = {
        "members": members,
        "is_group": data.is_group,
        "name": data.name,
        "created_at": datetime.utcnow(),
        "last_message": None,
        "last_message_at": None,
    }

    result = await db.chats.insert_one(chat)
    chat["_id"] = result.inserted_id
    return serialize_chat(chat)


@router.get("/my")
async def my(user=Depends(get_current_user)):
    return await my_chats(user)


@router.get("/")
async def get_chats(user=Depends(get_current_user)):
    return await list_chats(user)


# ── GET /chats/{chat_id} — retorna um único chat pelo ID ──────────────────────
@router.get("/{chat_id}")
async def get_chat_by_id(
    chat_id: str,
    current_user=Depends(get_current_user),
):
    db = get_database()
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    chat = await db.chats.find_one({"_id": oid})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_id = current_user["sub"]
    participants = chat.get("participants", [])
    members = chat.get("members", [])
    if user_id not in participants and user_id not in members:
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    chat_id_str = str(chat["_id"])

    settings = await db.user_chat_settings.find_one({
        "user_id": user_id, "chat_id": chat_id_str
    })
    unread = await db.messages.count_documents({
        "chat_id": chat_id_str, "receiver_id": user_id, "read": False
    })

    return {
        "_id": chat_id_str,
        "participants": participants,
        "members": members,
        "created_at": chat.get("created_at"),
        "updated_at": chat.get("updated_at"),
        "last_message": chat.get("last_message"),
        "pinned": settings.get("pinned", False) if settings else False,
        "archived": settings.get("archived", False) if settings else False,
        "muted": settings.get("muted", False) if settings else False,
        "unread_count": unread,
    }


@router.post("/archive")
async def archive(data: ChatActionSchema, user=Depends(get_current_user)):
    return await archive_chat(user, data)


@router.post("/pin")
async def pin(data: ChatActionSchema, user=Depends(get_current_user)):
    return await pin_chat(user, data)


@router.post("/mute")
async def mute(data: ChatActionSchema, user=Depends(get_current_user)):
    return await mute_chat(user, data)


@router.post("/hide")
async def hide(data: ChatActionSchema, user=Depends(get_current_user)):
    return await hide_chat(user, data)


@router.delete("/{chat_id}")
async def remove_chat(chat_id: str, user=Depends(get_current_user)):
    return await delete_chat(user, chat_id)
