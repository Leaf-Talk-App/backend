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
        "status": "sent",
        "read": False,
        "created_at": now
    }

    result = await db.messages.insert_one(message)
    
    await db.chats.update_one(
        {"_id": ObjectId(data.chat_id)},
        {
            "$set": {
                "updated_at": now,
                "last_message": {
                    "content": data.content,
                    "created_at": now
                }
            }
        }
    )

    ws_message = {
        "_id": str(result.inserted_id),
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "created_at": now.isoformat(),
        "status": "sent"
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

async def react_message(current_user, data):
    db = get_database()

    await db.messages.update_one(
        {"_id": ObjectId(data.message_id)},
        {
            "$addToSet": {
                f"reactions.{data.emoji}":
                current_user["sub"]
            }
        }
    )

    return {"message": "reacted"}

async def delete_message(current_user, message_id):
    db = get_database()

    await db.messages.update_one(
        {
            "_id": ObjectId(message_id),
            "sender_id": current_user["sub"]
        },
        {
            "$set": {
                "deleted": True,
                "content": "Mensagem apagada"
            }
        }
    )

    return {"message": "deleted"}

async def edit_message(current_user, message_id, content):
    db = get_database()

    await db.messages.update_one(
        {
            "_id": ObjectId(message_id),
            "sender_id": current_user["sub"]
        },
        {
            "$set": {
                "content": content,
                "edited": True
            }
        }
    )

    return {"message": "edited"}