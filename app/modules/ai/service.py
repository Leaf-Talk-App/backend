import json
from google import genai
from app.core.config import settings
from app.core.database import get_database


genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


async def ask_ai(prompt: str, current_user):
    db = get_database()

    full_prompt = f"""
Você é assistente do app Leaf Talk.

Se a mensagem for comando de agendamento,
responda APENAS JSON:

{{
 "action":"schedule_message",
 "to":"João",
 "time":"20:00",
 "content":"oi"
}}

Se não for comando, responda normalmente.

Mensagem:
{prompt}
"""

    response = model.generate_content(full_prompt)

    text = response.text.strip()

    try:
        data = json.loads(text)

        if data["action"] == "schedule_message":

            task = {
                "user_id": current_user["sub"],
                "to": data["to"],
                "time": data["time"],
                "content": data["content"],
                "done": False
            }

            await db.scheduled_messages.insert_one(task)

            return {
                "message": "Mensagem agendada com sucesso",
                "task": task
            }

    except:
        pass

    return {"reply": text}