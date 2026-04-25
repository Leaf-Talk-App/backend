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