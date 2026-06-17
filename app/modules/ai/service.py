import base64
import difflib
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
from app.modules.ai.rag import context_block

# Cliente Anthropic (Claude). A key vem de ANTHROPIC_API_KEY (env) — nunca hardcoded.
# Async para não bloquear o event loop do FastAPI.
client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Modelo solicitado: Claude Haiku 4.5 (rápido e econômico, multimodal).
AI_MODEL = "claude-haiku-4-5-20251001"

# Fuso padrão (Brasil, UTC-3) — usado só como último recurso. O fuso real vem
# do navegador do usuário a cada chamada (nome IANA ou offset em minutos).
_DEFAULT_TZ = timezone(timedelta(hours=-3))


def _resolve_tz(tz_name=None, tz_offset_min=None):
    """Fuso do usuário: IANA (DST-aware) → offset do browser → padrão UTC-3.

    tz_offset_min é o valor cru do JS getTimezoneOffset() (BR = 180), onde
    horário_local = UTC - offset, então o offset real é -tz_offset_min.
    """
    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if tz_offset_min is not None:
        try:
            return timezone(timedelta(minutes=-int(tz_offset_min)))
        except Exception:
            pass
    return _DEFAULT_TZ

# Personalidade do Humberto + protocolo de ação (enviar/agendar com confirmação).
# <DATA> é substituído pela data atual para resolver "amanhã", "hoje 18h" etc.
HUMBERTO_SYSTEM_TEMPLATE = """Você é o Humberto, assistente de IA do Leaf Talk. Responda sempre em português, de forma clara e útil. Data e hora atuais (horário do usuário): <DATA>.

IMPORTANTE: responda SOMENTE à ÚLTIMA mensagem do usuário. As mensagens anteriores servem apenas de contexto — não as responda de novo nem misture assuntos antigos com o atual.

Você é um assistente COMPLETO e prestativo: ajuda com QUALQUER assunto — listas (compras, tarefas), receitas, planejamento, estudos, ideias, escrever/revisar textos e mensagens, explicar temas, etc. NUNCA recuse um pedido dizendo que "não é sobre o Leaf Talk"; atenda normalmente. Se houver anexo (imagem ou PDF), pode analisá-lo. A única coisa que você NÃO consegue é LER as conversas, mensagens, notificações ou status do usuário — nunca invente esse conteúdo.

VOCÊ PODE, com a confirmação do usuário, ENVIAR ou AGENDAR uma mensagem para um contato dele. Use isso SOMENTE quando o usuário claramente pedir para mandar/agendar algo a alguém (ex.: "manda 'oi' pro João", "agenda 'bom dia' pra Maria amanhã às 9h").

Assim que o usuário pedir para enviar/agendar, já responda DE PRIMEIRA com o JSON (não peça confirmação por texto — a confirmação acontece no card da tela). Responda APENAS com um JSON em uma única linha, sem nenhum outro texto, neste formato:
- Enviar agora: {"action":"send_message","to":"NOME DO CONTATO","content":"texto exato da mensagem"}
- Agendar: {"action":"schedule_message","to":"NOME DO CONTATO","content":"texto","datetime":"YYYY-MM-DDTHH:MM"}

Regras: use o nome do contato exatamente como o usuário disse; em "datetime" use o horário LOCAL do usuário resolvido a partir da data atual; nunca invente um contato. A mensagem só é enviada/agendada DEPOIS que o usuário confirmar na tela — você apenas propõe.

Em QUALQUER outra situação (conversa, dúvidas, escrever/revisar texto), responda em texto normal — NUNCA use JSON."""

# Persona enxuta para quando o Humberto é MENCIONADO dentro de uma conversa/grupo.
# Sem protocolo de ação (não envia/agenda por aqui) — só responde em texto curto.
HUMBERTO_INLINE_SYSTEM = """Você é o Humberto, assistente de IA do Leaf Talk, respondendo dentro de uma conversa onde alguém te mencionou. Responda sempre em português, de forma curta, clara e útil (1 a 4 frases). Você NÃO tem acesso ao histórico da conversa nem às mensagens das pessoas — responda apenas ao que foi perguntado a você. Data e hora atuais: <DATA>."""

# ID virtual do remetente das respostas do Humberto dentro de conversas/grupos.
HUMBERTO_USER_ID = "humberto"

# Tipos de imagem aceitos pela API da Anthropic.
_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_ACTION_KINDS = {"send_message", "schedule_message"}


def mentions_humberto(text: str) -> bool:
    """True se a mensagem menciona @Humberto (case-insensitive)."""
    return bool(text) and bool(re.search(r"@humberto\b", text, re.IGNORECASE))


def strip_humberto_mention(text: str) -> str:
    """Remove a menção @Humberto, deixando só a pergunta."""
    return re.sub(r"@humberto\b", "", text or "", flags=re.IGNORECASE).strip()


async def humberto_reply(prompt: str) -> str:
    """Resposta de texto do Humberto quando mencionado numa conversa/grupo.
    Sem ações nem persistência de histórico — só gera a resposta."""
    question = (prompt or "").strip()
    if not question:
        return "Oi! Em que posso ajudar? Escreva sua pergunta após @Humberto."
    system_prompt = HUMBERTO_INLINE_SYSTEM.replace(
        "<DATA>", datetime.now(_DEFAULT_TZ).strftime("%d/%m/%Y %H:%M")
    ) + context_block(question)
    try:
        response = await client.messages.create(
            model=AI_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": [{"type": "text", "text": question}]}],
        )
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or "Desculpe, não consegui responder agora."
    except Exception:
        return "Desculpe, não consegui responder agora."


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


async def ask_ai(prompt: str, current_user, attachment_url: str = None, attachment_mime: str = None,
                 tz_name: str = None, tz_offset_min: int = None):
    db = get_database()
    user_tz = _resolve_tz(tz_name, tz_offset_min)

    # Anexo SEM texto → o Humberto já analisa por conta própria (antes mandava um
    # bloco de texto vazio e ficava sem saber o que fazer com a mídia).
    prompt = (prompt or "").strip()
    if not prompt and attachment_url:
        prompt = "Analise este anexo e me diga o que é, resumindo o conteúdo principal."

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
        "<DATA>", datetime.now(user_tz).strftime("%d/%m/%Y %H:%M")
    ) + context_block(prompt)

    # Histórico recente → o Humberto mantém o contexto da conversa (antes era
    # stateless e "puxava outro assunto" quando o usuário respondia a algo).
    history_msgs = []
    try:
        hist = await db.ai_conversations.find(
            {"user_id": current_user["sub"]}
        ).sort("created_at", -1).to_list(6)
        hist.reverse()
        for h in hist:
            content = (h.get("content") or "").strip()
            if not content:
                continue
            role = "assistant" if h.get("role") == "assistant" else "user"
            # Mantém a alternância user/assistant. Se o último item já é do mesmo
            # papel (ex.: uma resposta vazia foi pulada e sobraram dois 'user'
            # seguidos), funde no anterior — senão o Claude enxerga mensagens
            # antigas como "em aberto" e responde de novo as já respondidas.
            if history_msgs and history_msgs[-1]["role"] == role:
                history_msgs[-1]["content"] += "\n" + content
            else:
                history_msgs.append({"role": role, "content": content})
        # a API exige começar por 'user'
        while history_msgs and history_msgs[0]["role"] != "user":
            history_msgs.pop(0)
    except Exception:
        history_msgs = []

    response = await client.messages.create(
        model=AI_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=history_msgs + [{"role": "user", "content": user_content}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()

    # Proposta de ação (enviar/agendar): NÃO executa aqui — cria uma pendência e
    # devolve um card de confirmação. Só envia/agenda quando o usuário confirma.
    action_data = _try_parse_action(text)
    if action_data:
        card, reply_text = await _prepare_action(current_user, action_data, user_tz)
        await _persist_history(current_user, prompt, attachment_url, attachment_mime, reply_text)
        return {"reply": reply_text, "action": card} if card else {"reply": reply_text}

    await _persist_history(current_user, prompt, attachment_url, attachment_mime, text)
    return {"reply": text}


def _try_parse_action(text: str):
    """Detecta um JSON de ação (send_message/schedule_message) na resposta —
    mesmo que o modelo coloque texto antes/depois ou cerque com ```.
    Retorna o dict da ação ou None."""
    raw = (text or "").strip()

    candidates = [raw]
    if "```" in raw:
        candidates.append(raw.replace("```json", "```").strip("`"))
    # objeto JSON achatado contendo "action" no meio do texto
    for m in re.finditer(r'\{[^{}]*"action"[^{}]*\}', raw, re.DOTALL):
        candidates.append(m.group(0))

    for cand in candidates:
        c = cand.strip().strip("`").strip()
        s, e = c.find("{"), c.rfind("}")
        if s == -1 or e == -1 or e < s:
            continue
        try:
            data = json.loads(c[s : e + 1])
        except Exception:
            continue
        if (
            isinstance(data, dict)
            and data.get("action") in _ACTION_KINDS
            and data.get("to")
            and data.get("content")
        ):
            return data
    return None


async def _resolve_contacts(name: str):
    """Todos os usuários cujo nome/display_name/e-mail bate exatamente
    (case-insensitive). Inclui e-mail p/ o usuário desambiguar homônimos."""
    db = get_database()
    rx = {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}
    return await db.users.find(
        {"$or": [{"name": rx}, {"display_name": rx}, {"email": rx}]}
    ).to_list(50)


def _name_of(user) -> str:
    return (user.get("display_name") or user.get("name") or "").strip()


async def _user_contacts(user_id: str):
    """Usuários com quem o atual já tem conversa (pool para sugestões)."""
    db = get_database()
    chats = await db.chats.find({"participants": user_id}).to_list(500)
    ids = set()
    for c in chats:
        for p in c.get("participants", []):
            if p and p != user_id:
                ids.add(p)
    oids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    if not oids:
        return []
    return await db.users.find({"_id": {"$in": oids}}).to_list(500)


def _find_similar_contacts(name: str, users, limit: int = 3):
    """Contatos com nome parecido (aproximado). Retorna lista ordenada."""
    target = (name or "").strip().lower()
    if not target:
        return []
    scored = []
    for u in users:
        n = _name_of(u)
        if not n:
            continue
        nl = n.lower()
        ratio = difflib.SequenceMatcher(None, target, nl).ratio()
        # quem contém o termo (ou vice-versa) é forte candidato
        if target in nl or nl in target:
            ratio = max(ratio, 0.88)
        scored.append((ratio, u))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [u for ratio, u in scored if ratio >= 0.55][:limit]


async def _prepare_action(current_user, data, user_tz):
    """Cria a pendência (não envia) e monta o card de confirmação.
    Retorna (card | None, reply_text)."""
    db = get_database()
    to_name = (data.get("to") or "").strip()
    content = (data.get("content") or "").strip()

    matches = await _resolve_contacts(to_name)
    if not matches:
        # Sem match exato → sugere parecidos entre os contatos e PERGUNTA antes
        # (nunca escolhe sozinho). O usuário confirma o nome e o Humberto refaz.
        contacts = await _user_contacts(current_user["sub"])
        similar = _find_similar_contacts(to_name, contacts)
        if similar:
            names = [_name_of(u) for u in similar]
            if len(names) == 1:
                ask = f'Não achei "{to_name}" exatamente. Você quis dizer {names[0]}? Se sim, me confirme o nome.'
            else:
                listed = ", ".join(names[:-1]) + f" ou {names[-1]}"
                ask = f'Não achei "{to_name}" exatamente. Você quis dizer {listed}? Me diga o nome certo.'
            return None, ask
        return None, f'Não encontrei o contato "{to_name}". Confira o nome e tente de novo.'

    ambiguous = False
    if len(matches) > 1:
        # Mais de um contato com o MESMO nome. Em vez de exigir o e-mail (o
        # usuário quase nunca sabe de cabeça), o palpite é o contato com quem ele
        # conversou MAIS RECENTEMENTE. O e-mail aparece no card p/ ele conferir
        # antes de confirmar — se for outro, é só tocar em "Não enviar".
        chats = await db.chats.find({"participants": current_user["sub"]}).to_list(500)
        recency = {}
        for c in chats:
            for p in c.get("participants", []):
                if p and p != current_user["sub"]:
                    recency[p] = c.get("updated_at") or datetime.min
        known = [m for m in matches if str(m["_id"]) in recency]
        pool = known or matches
        pool.sort(key=lambda u: recency.get(str(u["_id"])) or datetime.min, reverse=True)
        matches = pool
        ambiguous = True

    contact = matches[0]
    receiver_id = str(contact["_id"])
    display = contact.get("display_name") or contact.get("name") or to_name
    # Quando há homônimos, mostra o e-mail junto p/ o usuário confirmar a pessoa.
    email = contact.get("email")
    recipient_label = f"{display} ({email})" if ambiguous and email else display
    now = datetime.now(timezone.utc)

    # AGENDAR vs ENVIAR é decidido pela presença de datetime VÁLIDO (não pelo
    # nome da ação) — o modelo às vezes manda "send_message" mesmo no agendar,
    # o que fazia enviar na hora ao confirmar.
    parsed_dt = _parse_local_datetime(data.get("datetime"), user_tz) if data.get("datetime") else None
    wants_schedule = data.get("action") == "schedule_message" or bool(data.get("datetime"))

    run_at = now
    scheduled_label = None
    is_schedule = False
    if wants_schedule:
        if not parsed_dt:
            return None, (
                "Para agendar eu preciso da data e hora. Me diga, por exemplo, "
                '"amanhã às 9h".'
            )
        if parsed_dt <= now:
            return None, (
                "Esse horário já passou. Me diga um horário no futuro para eu agendar."
            )
        is_schedule = True
        run_at = parsed_dt
        scheduled_label = run_at.astimezone(user_tz).strftime("%d/%m/%Y às %H:%M")

    # Remove pendências anteriores ainda não confirmadas → evita reaproveitar o
    # texto/horário do agendamento anterior (card antigo "fantasma").
    await db.scheduled_messages.delete_many(
        {"user_id": current_user["sub"], "confirmed": False, "done": False}
    )

    pending = {
        "user_id": current_user["sub"],
        "to": recipient_label,
        "receiver_id": receiver_id,
        "content": content,
        "kind": "schedule" if is_schedule else "send",
        "run_at": run_at,
        "scheduled_label": scheduled_label,  # p/ reexibir o card depois
        "confirmed": False,
        "done": False,
        "created_at": now,
    }
    result = await db.scheduled_messages.insert_one(pending)

    card = {
        "task_id": str(result.inserted_id),
        "type": "schedule" if is_schedule else "send",
        "title": "Agendar mensagem" if is_schedule else "Enviar mensagem",
        "recipient": recipient_label,
        "body": content,
        "scheduledFor": scheduled_label,
    }
    reply_text = (
        f'Quero confirmar: agendar "{content}" para {recipient_label} em {scheduled_label}? '
        "Toque em Confirmar abaixo."
        if is_schedule
        else f'Quero confirmar: enviar "{content}" para {recipient_label}? Toque em Confirmar abaixo.'
    )
    if ambiguous:
        reply_text += (
            f" (Existe mais de um {display} — confira pelo e-mail; se for outro, "
            "toque em Não enviar e me diga mais detalhes.)"
        )
    return card, reply_text


async def get_pending_tasks(current_user):
    """Cards de ações ainda não confirmadas — p/ reexibir ao reabrir a tela do
    Humberto (antes o card sumia se o usuário saísse e voltasse)."""
    db = get_database()
    tasks = await db.scheduled_messages.find(
        {"user_id": current_user["sub"], "confirmed": False, "done": False}
    ).sort("created_at", 1).to_list(20)
    cards = []
    for t in tasks:
        cards.append({
            "task_id": str(t["_id"]),
            "type": t.get("kind", "send"),
            "title": "Agendar mensagem" if t.get("kind") == "schedule" else "Enviar mensagem",
            "recipient": t.get("to"),
            "body": t.get("content"),
            "scheduledFor": t.get("scheduled_label"),
        })
    return cards


async def cancel_task(current_user, task_id):
    """Cancela (remove) uma ação pendente não confirmada."""
    db = get_database()
    try:
        oid = ObjectId(task_id)
    except Exception:
        return {"error": "invalid task id"}
    await db.scheduled_messages.delete_one(
        {"_id": oid, "user_id": current_user["sub"], "confirmed": False, "done": False}
    )
    return {"message": "cancelado"}


def _parse_local_datetime(value, user_tz):
    """Parseia 'YYYY-MM-DDTHH:MM' (horário local do usuário) → datetime UTC."""
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            naive = datetime.strptime(value.strip(), fmt)
            return naive.replace(tzinfo=user_tz).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


async def _persist_history(current_user, prompt, attachment_url, attachment_mime, reply_text):
    db = get_database()
    try:
        await db.ai_conversations.insert_many([
            {
                "user_id": current_user["sub"],
                "role": "user",
                "content": prompt,
                "attachment_url": attachment_url,
                "attachment_mime": attachment_mime,
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
            "attachment_url": m.get("attachment_url"),
            "attachment_mime": m.get("attachment_mime"),
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