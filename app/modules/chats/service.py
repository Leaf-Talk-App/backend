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

    existing = await db.user_chat_settings.find_one({
        "user_id": current_user["sub"],
        "chat_id": data.chat_id,
    })
    new_val = not (existing.get("muted", False) if existing else False)

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "muted": new_val
            }
        },
        upsert=True
    )

    return {"message": "Chat muted" if new_val else "Chat unmuted", "muted": new_val}


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

async def delete_chat(current_user, chat_id):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": chat_id
        },
        {"$set": {"deleted": True, "hidden": True}},
        upsert=True
    )

    return {"message": "Chat deleted"}


async def my_chats(current_user):
    db = get_database()

    user_id = current_user["sub"]

    chats = await db.chats.find({
        "$or": [
            {"participants": user_id},
            {"members": user_id}
        ]
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

        updated_at = chat.get("updated_at")
        # Normaliza para ISO string para evitar TypeError no sort (datetime vs str)
        updated_at_iso = updated_at.isoformat() if updated_at else ""

        # Serializa last_message (created_at pode ser datetime)
        raw_lm = chat.get("last_message")
        last_message = None
        if raw_lm:
            lm_created = raw_lm.get("created_at")
            last_message = {
                **{k: v for k, v in raw_lm.items() if k != "created_at"},
                "created_at": lm_created.isoformat() if hasattr(lm_created, "isoformat") else lm_created,
            }

        item = {
            "_id": chat_id,
            "participants": chat.get("participants"),
            "members": chat.get("members"),
            "updated_at": updated_at_iso,
            "last_message": last_message,
            "pinned": settings.get("pinned", False) if settings else False,
            "archived": settings.get("archived", False) if settings else False,
            "muted": settings.get("muted", False) if settings else False,
            "unread_count": unread,
        }

        result.append(item)

    # Ordena: não arquivados primeiro, pinados antes, mais recentes primeiro
    result.sort(
        key=lambda x: (
            x["archived"],         # False (0) antes de True (1)
            not x["pinned"],       # pinados (False=0) antes dos não-pinados
            x["updated_at"],       # ISO string — ordenável
        ),
        reverse=False,
    )
    result.reverse()  # mais recentes no topo

    return result