from datetime import datetime
from bson import ObjectId
from app.core.database import get_database

async def create_chat(current_user, data):
    db = get_database()

    participants = sorted([
        current_user["sub"],
        data.user_id
    ])

    existing = await db.chats.find_one({
        "participants": participants
    })

    if existing:
        return {
            "chat_id": str(existing["_id"]),
            "existing": True
        }

    chat = {
        "participants": participants,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_message": None
    }

    result = await db.chats.insert_one(chat)

    return {
        "chat_id": str(result.inserted_id),
        "existing": False
    }

async def list_chats(current_user):
    db = get_database()

    chats = await db.chats.find({
        "participants": current_user["sub"]
    }).sort("updated_at", -1).to_list(50)

    for chat in chats:
        chat["_id"] = str(chat["_id"])

    return chats

async def archive_chat(current_user, data):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "archived": True
            }
        },
        upsert=True
    )

    return {"message": "Chat archived"}


async def pin_chat(current_user, data):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "pinned": True
            }
        },
        upsert=True
    )

    return {"message": "Chat pinned"}


async def mute_chat(current_user, data):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "muted": True
            }
        },
        upsert=True
    )

    return {"message": "Chat muted"}


async def hide_chat(current_user, data):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "hidden": True
            }
        },
        upsert=True
    )

    return {"message": "Chat hidden"}

async def my_chats(current_user):
    db = get_database()

    user_id = current_user["sub"]

    chats = await db.chats.find({
        "members": user_id
    }).to_list(100)

    result = []

    for chat in chats:
        chat_id = str(chat["_id"])

        settings = await db.user_chat_settings.find_one({
            "user_id": user_id,
            "chat_id": chat_id
        })

        if settings and settings.get("hidden"):
            continue

        unread = await db.messages.count_documents({
            "chat_id": chat_id,
            "receiver_id": user_id,
            "read": False
        })

        item = {
            "_id": chat_id,
            "members": chat["members"],
            "updated_at": chat.get("updated_at"),
            "last_message": chat.get("last_message"),
            "pinned": settings.get("pinned", False) if settings else False,
            "archived": settings.get("archived", False) if settings else False,
            "muted": settings.get("muted", False) if settings else False,
            "unread_count": unread
        }

        result.append(item)

    result.sort(
        key=lambda x: (
            x["archived"],
            not x["pinned"],
            x["updated_at"] or ""
        ),
        reverse=False
    )

    result.reverse()

    return result