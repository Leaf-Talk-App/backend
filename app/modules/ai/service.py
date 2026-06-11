import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import httpx
import anthropic
from app.core.config import settings
from app.core.database import get_database
from app.modules.messages.service import deliver_direct_message

# Cliente Anthropic (Claude). A key vem de ANTHROPIC_API_KEY (env) — nunca hardcoded.
# Async para não bloquear o event loop do FastAPI.
client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Modelo solicitado: Claude Haiku 4.5 (rápido e econômico, multimodal).
AI_MODEL = "claude-haiku-4-5-20251001"

# Fuso do usuário (Brasil, UTC-3). Agendamentos vêm em horário local e são
# convertidos para UTC ao gravar. (TODO: tornar configurável por usuário.)
_USER_TZ = timezone(timedelta(hours=-3))

# Personalidade do Humberto + protocolo de ação (enviar/agendar com confirmação).
# <DATA> é substituído pela data atual para resolver "amanhã", "hoje 18h" etc.
HUMBERTO_SYSTEM_TEMPLATE = """Você é o Humberto, assistente de IA do Leaf Talk. Responda sempre em português, de forma clara e útil. Data e hora atuais (horário do usuário): <DATA>.

O que você faz: ajuda a escrever e revisar textos e mensagens, dá ideias, explica assuntos, ajuda com produtividade e responde perguntas gerais. Se houver um anexo (imagem ou PDF), você pode analisá-lo. Você NÃO tem acesso para LER as conversas, mensagens, notificações ou status do usuário — nunca invente esse conteúdo.

VOCÊ PODE, com a confirmação do usuário, ENVIAR ou AGENDAR uma mensagem para um contato dele. Use isso SOMENTE quando o usuário claramente pedir para mandar/agendar algo a alguém (ex.: "manda 'oi' pro João", "agenda 'bom dia' pra Maria amanhã às 9h").

Quando for ENVIAR ou AGENDAR, responda APENAS com um JSON em uma única linha, sem nenhum outro texto, neste formato:
- Enviar agora: {"action":"send_message","to":"NOME DO CONTATO","content":"texto exato da mensagem"}
- Agendar: {"action":"schedule_message","to":"NOME DO CONTATO","content":"texto","datetime":"YYYY-MM-DDTHH:MM"}

Regras: use o nome do contato exatamente como o usuário disse; em "datetime" use o horário LOCAL do usuário resolvido a partir da data atual; nunca invente um contato. A mensagem só é enviada/agendada DEPOIS que o usuário confirmar na tela — você apenas propõe.

Em QUALQUER outra situação (conversa, dúvidas, escrever/revisar texto), responda em texto normal — NUNCA use JSON."""

# Tipos de imagem aceitos pela API da Anthropic.
_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_ACTION_KINDS = {"send_message", "schedule_message"}


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

    system_prompt = HUMBERTO_SYSTEM_TEMPLATE.replace(
        "<DATA>", datetime.now(_USER_TZ).strftime("%d/%m/%Y %H:%M")
    )

    response = await client.messages.create(
        model=AI_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()

    # Proposta de ação (enviar/agendar): NÃO executa aqui — cria uma pendência e
    # devolve um card de confirmação. Só envia/agenda quando o usuário confirma.
    action_data = _try_parse_action(text)
    if action_data:
        card, reply_text = await _prepare_action(current_user, action_data)
        await _persist_history(current_user, prompt, attachment_url, reply_text)
        return {"reply": reply_text, "action": card} if card else {"reply": reply_text}

    await _persist_history(current_user, prompt, attachment_url, text)
    return {"reply": text}


def _try_parse_action(text: str):
    """Detecta um JSON de ação (send_message/schedule_message) na resposta.
    Tolera cercas de código. Retorna o dict da ação ou None."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):] if "{" in raw else raw
    if not (raw.startswith("{") and raw.endswith("}")):
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if isinstance(data, dict) and data.get("action") in _ACTION_KINDS:
        if data.get("to") and data.get("content"):
            return data
    return None


async def _resolve_contact(name: str):
    """Acha o usuário-alvo pelo nome/display_name (case-insensitive)."""
    db = get_database()
    rx = {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}
    return await db.users.find_one({"$or": [{"name": rx}, {"display_name": rx}]})


async def _prepare_action(current_user, data):
    """Cria a pendência (não envia) e monta o card de confirmação.
    Retorna (card | None, reply_text)."""
    db = get_database()
    to_name = (data.get("to") or "").strip()
    content = (data.get("content") or "").strip()
    is_schedule = data.get("action") == "schedule_message"

    contact = await _resolve_contact(to_name)
    if not contact:
        return None, f'Não encontrei o contato "{to_name}". Confira o nome e tente de novo.'

    receiver_id = str(contact["_id"])
    display = contact.get("display_name") or contact.get("name") or to_name
    now = datetime.now(timezone.utc)

    run_at = now
    scheduled_label = None
    if is_schedule:
        run_at = _parse_local_datetime(data.get("datetime"))
        if not run_at:
            return None, (
                "Para agendar eu preciso da data e hora. Me diga, por exemplo, "
                '"amanhã às 9h".'
            )
        scheduled_label = run_at.astimezone(_USER_TZ).strftime("%d/%m/%Y às %H:%M")

    pending = {
        "user_id": current_user["sub"],
        "to": display,
        "receiver_id": receiver_id,
        "content": content,
        "kind": "schedule" if is_schedule else "send",
        "run_at": run_at,
        "confirmed": False,
        "done": False,
        "created_at": now,
    }
    result = await db.scheduled_messages.insert_one(pending)

    card = {
        "task_id": str(result.inserted_id),
        "type": "schedule" if is_schedule else "send",
        "title": "Agendar mensagem" if is_schedule else "Enviar mensagem",
        "recipient": display,
        "body": content,
        "scheduledFor": scheduled_label,
    }
    reply_text = (
        f'Quero confirmar: agendar "{content}" para {display} em {scheduled_label}? '
        "Toque em Confirmar abaixo."
        if is_schedule
        else f'Quero confirmar: enviar "{content}" para {display}? Toque em Confirmar abaixo.'
    )
    return card, reply_text


def _parse_local_datetime(value):
    """Parseia 'YYYY-MM-DDTHH:MM' (horário local do usuário) → datetime UTC."""
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(value.strip(), fmt)
            return naive.replace(tzinfo=_USER_TZ).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


async def _persist_history(current_user, prompt, attachment_url, reply_text):
    db = get_database()
    try:
        await db.ai_conversations.insert_many([
            {
                "user_id": current_user["sub"],
                "role": "user",
                "content": prompt,
                "attachment_url": attachment_url,
                "created_at": datetime.utcnow(),
            },
            {
                "user_id": current_user["sub"],
                "role": "assistant",
                "content": reply_text,
                "created_at": datetime.utcnow(),
            },
        ])
    except Exception:
        pass

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
    """Confirma a ação proposta. Envio imediato → entrega agora pelo caminho
    real (WS + chat). Agendamento → marca confirmed:True; o agendador entrega
    quando chegar a hora."""
    db = get_database()

    try:
        oid = ObjectId(task_id)
    except Exception:
        return {"error": "invalid task id"}

    task = await db.scheduled_messages.find_one(
        {"_id": oid, "user_id": current_user["sub"]}
    )
    if not task:
        return {"error": "Tarefa não encontrada"}
    if task.get("done"):
        return {"message": "Já confirmado"}

    if task.get("kind") == "schedule":
        await db.scheduled_messages.update_one(
            {"_id": oid}, {"$set": {"confirmed": True}}
        )
        return {"message": "Mensagem agendada"}

    # envio imediato
    await deliver_direct_message(
        current_user["sub"], task["receiver_id"], task.get("content", "")
    )
    await db.scheduled_messages.update_one(
        {"_id": oid},
        {"$set": {"confirmed": True, "done": True, "done_at": datetime.utcnow()}},
    )
    return {"message": "Mensagem enviada"}