from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.core.websocket import manager

async def send_message(current_user, data):
    db = get_database()

    now = datetime.utcnow()

    message = {
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "created_at": now
    }

    result = await db.messages.insert_one(message)

    ws_message = {
        "_id": str(result.inserted_id),
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "created_at": now.isoformat()
    }

    await manager.send_personal_message(
        data.receiver_id,
        ws_message
    )

    return {"message": "sent"}

async def get_messages(chat_id):
    db = get_database()

    messages = await db.messages.find({
        "chat_id": chat_id
    }).sort("created_at", 1).to_list(100)

    for msg in messages:
        msg["_id"] = str(msg["_id"])

    return messages