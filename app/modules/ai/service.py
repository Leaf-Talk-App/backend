from google import genai

client = genai.Client(api_key="SUA_KEY")


async def ask_ai(prompt: str):
    full_prompt = f"""
Você é assistente do app Leaf Talk.

Se a mensagem for comando de agendamento,
responda JSON.

Formato:

{{
 "action": "schedule_message",
 "to": "João",
 "time": "20:00",
 "content": "oi"
}}

Se não for comando, responda normalmente.

Mensagem:
{prompt}
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=full_prompt
        )

        return {
            "reply": response.text or ""
        }

    except Exception as e:
        return {
            "reply": f"Erro na IA: {str(e)}"
        }