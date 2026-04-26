from datetime import datetime

from app.core.database import get_database


async def run_scheduler():
    db = get_database()

    now = datetime.now().strftime("%H:%M")

    tasks = await db.scheduled_messages.find({
        "time": now,
        "done": False
    }).to_list(100)

    for task in tasks:

        message = {
            "chat_id": None,
            "sender_id": task["user_id"],
            "receiver_name": task["to"],
            "content": task["content"],
            "created_at": datetime.utcnow()
        }

        await db.messages.insert_one(message)

        await db.scheduled_messages.update_one(
            {"_id": task["_id"]},
            {"$set": {"done": True}}
        )

        print("Mensagem enviada:", task["content"])