from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import get_database
from app.modules.messages.service import deliver_direct_message
scheduler = AsyncIOScheduler()

async def process_scheduled_messages():
    """Entrega mensagens agendadas (confirmadas) cujo run_at já chegou, pelo
    caminho real (chat + receiver_id + WebSocket). Substitui o match por HH:MM."""
    db = get_database()

    now = datetime.now(timezone.utc)

    tasks = await db.scheduled_messages.find({
        "kind": "schedule",
        "done": False,
        "confirmed": True,
        "run_at": {"$lte": now},
    }).to_list(100)

    for task in tasks:
        receiver_id = task.get("receiver_id")
        if not receiver_id:
            # registro legado sem destinatário resolvido → ignora
            await db.scheduled_messages.update_one(
                {"_id": task["_id"]}, {"$set": {"done": True, "done_at": now, "skipped": True}}
            )
            continue

        print("Enviando mensagem agendada:", task.get("content"))
        try:
            await deliver_direct_message(task["user_id"], receiver_id, task.get("content", ""))
        except Exception as e:
            print("[SCHEDULER] falha ao entregar:", e)
            continue

        await db.scheduled_messages.update_one(
            {"_id": task["_id"]},
            {"$set": {"done": True, "done_at": now}},
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