import base64
import json
import os
from datetime import datetime
from bson import ObjectId
import httpx
import anthropic
from app.core.config import settings
from app.core.database import get_database

# Cliente Anthropic (Claude). A key vem de ANTHROPIC_API_KEY (env) — nunca hardcoded.
# Async para não bloquear o event loop do FastAPI.
client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Modelo solicitado: Claude Haiku 4.5 (rápido e econômico, multimodal).
AI_MODEL = "claude-haiku-4-5-20251001"

# Personalidade do Humberto — preservada exatamente como estava no Gemini.
HUMBERTO_SYSTEM = """Você é o Humberto, assistente de IA geral do Leaf Talk.

Você é um assistente de conversa geral (como um ChatGPT). Você NÃO tem acesso às
conversas, mensagens, contatos, notificações, status de leitura nem a qualquer
dado interno do app Leaf. Nunca afirme ter esse acesso e nunca invente esses dados.

O que você faz: ajuda a escrever e revisar textos e mensagens, dá ideias, explica
assuntos, ajuda com produtividade, sugere temas de conversa e responde perguntas
gerais. Se houver um anexo (imagem ou PDF), você pode analisá-lo.

Se o usuário pedir algo que dependa de dados do app (ex.: "resuma minhas
conversas", "o que ainda não respondi"), explique com gentileza que você não tem
acesso a essas informações, mas ofereça ajuda de outra forma.

Responda sempre em português, de forma clara e útil."""

# Tipos de imagem aceitos pela API da Anthropic.
_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


async def _fetch_attachment(url: str, mime: str | None):
    """Lê os bytes de um anexo (Cloudinary http(s) ou /uploads local)."""
    if not url:
        return None, None

    if url.startswith("http://") or url.startswith("https://"):
        async with httpx.AsyncClient(timeout=20) as cx:
            r = await cx.get(url)
            r.raise_for_status()
            ct = mime or r.headers.get("content-type", "application/octet-stream")
            return r.content, ct.split(";")[0].strip()

    # URL relativa local: /uploads/arquivo.ext
    path = url.lstrip("/")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read(), (mime or "application/octet-stream")

    return None, None


async def ask_ai(prompt: str, current_user, attachment_url: str = None, attachment_mime: str = None):
    db = get_database()

    # Conteúdo do turno do usuário: texto + anexo opcional (imagem / PDF).
    # Claude Haiku 4.5 é multimodal (imagem e PDF). Áudio não é suportado pela
    # API da Anthropic → anexos de áudio são ignorados (segue só com o texto).
    user_content: list = [{"type": "text", "text": prompt}]

    if attachment_url:
        try:
            file_bytes, mime = await _fetch_attachment(attachment_url, attachment_mime)
            if file_bytes and mime:
                b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
                if mime in _SUPPORTED_IMAGE_TYPES:
                    user_content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime, "data": b64},
                    })
                elif mime == "application/pdf":
                    user_content.append({
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                    })
                # demais tipos (áudio, etc.) não são aceitos → ignora
        except Exception:
            pass  # se falhar o anexo, segue só com o texto

    response = await client.messages.create(
        model=AI_MODEL,
        max_tokens=4096,
        system=HUMBERTO_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()

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

    # persist user message + reply in history
    try:
        await db.ai_conversations.insert_many([
            {
                "user_id": current_user["sub"],
                "role": "user",
                "content": prompt,
                "attachment_url": attachment_url,
                "created_at": datetime.utcnow()
            },
            {
                "user_id": current_user["sub"],
                "role": "assistant",
                "content": text,
                "created_at": datetime.utcnow()
            }
        ])
    except Exception:
        pass

    return {"reply": text}

async def get_ai_history(current_user):
    db = get_database()

    messages = await db.ai_conversations.find(
        {"user_id": current_user["sub"]}
    ).sort("created_at", 1).to_list(200)

    return [
        {
            "role": m["role"],
            "content": m["content"],
            "created_at": m["created_at"].isoformat() if m.get("created_at") else None,
        }
        for m in messages
    ]


async def clear_ai_history(current_user):
    db = get_database()

    await db.ai_conversations.delete_many(
        {"user_id": current_user["sub"]}
    )

    return {"message": "History cleared"}


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