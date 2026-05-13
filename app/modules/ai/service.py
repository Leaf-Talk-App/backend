import json
from datetime import datetime
from google import genai
from app.core.config import settings
from app.core.database import get_database

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


async def ask_ai(prompt: str, current_user):
    db = get_database()

    full_prompt = f"""
Você é assistente do app Leaf Talk.

Se identificar intenção, responda JSON.

Tipos:

1 envio imediato

{{
 "action":"send_message",
 "to":"João",
 "content":"Oi"
}}

2 agendamento

{{
 "action":"schedule_message",
 "to":"João",
 "time":"20:00",
 "content":"Oi"
}}

3 follow-up

{{
 "action":"conditional_message",
 "to":"João",
 "condition":"no_reply",
 "timeout":"2h",
 "content":"Você viu minha mensagem?"
}}

Se não for comando, responda texto normal.

Mensagem:
{prompt}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    text = response.text.strip()

    try:
        data = json.loads(text)

        action = data.get("action")

        if action == "send_message":
            return await execute_send(
                current_user,
                data
            )

        if action == "schedule_message":
            return await execute_schedule(
                current_user,
                data
            )

        if action == "conditional_message":
            return await execute_followup(
                current_user,
                data
            )

    except:
        pass

    return {"reply": text}

async def confirm_task(current_user, task_id):
    db = get_database()

    await db.scheduled_messages.update_one(
        {
            "_id": ObjectId(task_id),
            "user_id": current_user["sub"]
        },
        {
            "$set": {
                "confirmed": True
            }
        }
    )

    return {
        "message": "Agendamento confirmado"
    }

async def execute_send(current_user, data):
    db = get_database()

    user = await db.users.find_one({
        "name": data["to"]
    })

    if not user:
        return {"error": "User not found"}

    chat = await db.chats.find_one({
        "members": {
            "$all": [
                current_user["sub"],
                str(user["_id"])
            ]
        }
    })

    if not chat:
        result = await db.chats.insert_one({
            "members": [
                current_user["sub"],
                str(user["_id"])
            ],
            "created_at": datetime.utcnow()
        })

        chat_id = str(result.inserted_id)

    else:
        chat_id = str(chat["_id"])

    await db.messages.insert_one({
        "chat_id": chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": str(user["_id"]),
        "content": data["content"],
        "created_at": datetime.utcnow(),
        "status": "sent",
        "read": False
    })

    return {
        "message": "Mensagem enviada"
    }

async def execute_schedule(current_user, data):
    db = get_database()

    await db.scheduled_messages.insert_one({
        "user_id": current_user["sub"],
        "to": data["to"],
        "time": data["time"],
        "content": data["content"],
        "done": False,
        "created_at": datetime.utcnow()
    })

    return {
        "message": "Mensagem agendada"
    }
    
async def execute_followup(current_user, data):
    db = get_database()

    await db.conditional_messages.insert_one({
        "user_id": current_user["sub"],
        "to": data["to"],
        "condition": data["condition"],
        "timeout": data["timeout"],
        "content": data["content"],
        "done": False,
        "created_at": datetime.utcnow()
    })

    return {
        "message": "Follow-up configurado"
    }