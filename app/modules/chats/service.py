from datetime import datetime
from bson import ObjectId
from app.core.database import get_database

async def create_chat(current_user, data):
    db = get_database()

    chat = {
        "participants": [
            current_user["sub"],
            data.user_id
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.chats.insert_one(chat)

    return {
        "chat_id": str(result.inserted_id)
    }

async def list_chats(current_user):
    db = get_database()

    chats = await db.chats.find({
        "participants": current_user["sub"]
    }).to_list(50)

    for chat in chats:
        chat["_id"] = str(chat["_id"])

    return chats