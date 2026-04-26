from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.core.websocket import manager

async def send_message(current_user, data):
    db = get_database()

    blocked = await db.blocked_users.find_one({
        "user_id": data.receiver_id,
        "blocked_user_id": current_user["sub"]
    })

    if blocked:
        return {"error": "You are blocked"}

    now = datetime.utcnow()

    status = (
        "delivered"
        if manager.is_online(data.receiver_id)
        else "sent"
    )

    message = {
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "status": status,
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
                    "created_at": now,
                    "status": status
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
        "status": status
    }

    await manager.send_personal_message(
        data.receiver_id,
        ws_message
    )

    return {
        "message": "sent",
        "status": status
    }

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

async def mark_as_read(chat_id, user):
    db = get_database()

    await db.messages.update_many(
        {
            "chat_id": chat_id,
            "receiver_id": user["sub"],
            "read": False
        },
        {
            "$set": {
                "read": True,
                "status": "read",
                "read_at": datetime.utcnow()
            }
        }
    )

    return {"message": "updated"}

async def get_messages(chat_id):
    db = get_database()

    messages = await db.messages.find(
        {
            "chat_id": chat_id
        }
    ).sort("created_at", 1).to_list(200)

    for message in messages:
        message["_id"] = str(message["_id"])

        if "created_at" in message:
            message["created_at"] = message[
                "created_at"
            ].isoformat()

        if "read_at" in message:
            message["read_at"] = message[
                "read_at"
            ].isoformat()

    return messages