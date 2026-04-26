from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import get_database
scheduler = AsyncIOScheduler()

async def process_scheduled_messages():
    db = get_database()

    now = datetime.utcnow()

    tasks = await db.scheduled_messages.find({
        "done": False,
        "confirmed": True
    }).to_list(100)

    for task in tasks:
        hour_now = now.strftime("%H:%M")

        if task["time"] == hour_now:

            print("Enviando mensagem agendada:", task["content"])

            await db.messages.insert_one({
                "chat_id": None,
                "sender_id": task["user_id"],
                "receiver_name": task["to"],
                "content": task["content"],
                "status": "sent",
                "read": False,
                "created_at": now
            })

            await db.scheduled_messages.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "done": True,
                        "done_at": now
                    }
                }
            )

async def process_followups():
    db = get_database()

    now = datetime.utcnow()

    tasks = await db.conditional_messages.find({
        "done": False,
        "run_at": {
            "$lte": now
        }
    }).to_list(100)

    for task in tasks:

        print("Executando follow-up")

        await db.messages.insert_one({
            "chat_id": None,
            "sender_id": task["user_id"],
            "receiver_name": task["to"],
            "content": task["content"],
            "status": "sent",
            "read": False,
            "created_at": now
        })

        await db.conditional_messages.update_one(
            {"_id": task["_id"]},
            {
                "$set": {
                    "done": True,
                    "done_at": now
                }
            }
        )

def start_scheduler():

    scheduler.add_job(
        process_scheduled_messages,
        "interval",
        minutes=1
    )

    scheduler.add_job(
        process_followups,
        "interval",
        minutes=1
    )

    scheduler.start()
    
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