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

def start_scheduler():
    # a cada 20s → mensagem agendada chega quase na hora (antes era 1 min)
    scheduler.add_job(
        process_scheduled_messages,
        "interval",
        seconds=20,
    )
    scheduler.start()
