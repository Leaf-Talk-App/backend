from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_database
from app.core.websocket import manager


async def deliver_direct_message(sender_id: str, receiver_id: str, content: str):
    """Entrega uma mensagem 1:1 pelo caminho real (resolve/cria o chat, grava a
    mensagem com chat_id + receiver_id corretos, atualiza last_message e notifica
    por WebSocket). Usado pelo Humberto (enviar ao confirmar) e pelo agendador.
    """
    db = get_database()
    now = datetime.now(timezone.utc)

    participants = sorted([sender_id, receiver_id])
    chat = await db.chats.find_one({"participants": participants})
    if chat:
        chat_id = str(chat["_id"])
    else:
        result = await db.chats.insert_one({
            "participants": participants,
            "created_at": now,
            "updated_at": now,
            "last_message": None,
        })
        chat_id = str(result.inserted_id)

    status = "delivered" if manager.is_online(receiver_id) else "sent"

    msg = {
        "chat_id": chat_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "type": "text",
        "file_url": None,
        "status": status,
        "read": False,
        "read_by": [],
        "created_at": now,
    }
    result = await db.messages.insert_one(msg)

    await db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": {
            "updated_at": now,
            "last_message": {"content": content, "type": "text", "created_at": now, "status": status},
            "deleted_by": [],
        }},
    )

    ws_message = {
        "type": "new_message",
        "_id": str(result.inserted_id),
        "chat_id": chat_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "type_msg": "text",
        "file_url": None,
        "created_at": now.isoformat(),
        "status": status,
    }
    await manager.send_personal_message(receiver_id, ws_message)
    await manager.send_personal_message(sender_id, ws_message)

    return {"chat_id": chat_id, "message_id": str(result.inserted_id)}


def _iso_utc(dt):
    """Serializa datetime como ISO UTC com offset.

    Os timestamps são gravados como UTC *naïve* (datetime.utcnow legado / agora
    aware). Sem o marcador de fuso, JS `new Date(str)` interpreta como hora
    LOCAL — deslocando o horário exibido. Forçamos +00:00 para o cliente parsear
    como UTC e exibir no fuso do dispositivo via toLocaleTimeString.
    """
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

async def send_message(current_user, data):
    db = get_database()

    # Valida chat_id antes de qualquer operação (ObjectId lança exceção para IDs inválidos)
    try:
        chat_oid = ObjectId(data.chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    # Destinatário bloqueou o remetente → NÃO avisa o remetente nem entrega.
    # Estilo WhatsApp: o envio "parece" ok pra quem bloqueou-não-sabe, mas a
    # mensagem fica oculta do bloqueador (deleted_for) e nada chega/notifica ele.
    blocked = await db.blocked_users.find_one({
        "user_id": data.receiver_id,
        "blocked_user_id": current_user["sub"]
    })
    is_blocked = bool(blocked)

    # Conversa consigo mesmo: a mensagem não é "nova/não lida" (você é o autor).
    is_self = data.receiver_id == current_user["sub"]

    now = datetime.now(timezone.utc)

    status = (
        "read"
        if is_self
        else "delivered"
        if manager.is_online(data.receiver_id)
        else "sent"
    )

    # Resposta a mensagem: denormaliza uma prévia da original no envio, para o
    # balão citar sem precisar de outra consulta. Se a original sumiu, ignora.
    reply_to = getattr(data, "reply_to", None) or None
    reply_preview = None
    if reply_to:
        try:
            original = await db.messages.find_one({"_id": ObjectId(reply_to)})
        except Exception:
            original = None
        if original:
            snippet = (original.get("content") or "")[:120]
            reply_preview = {
                "_id": str(original["_id"]),
                "sender_id": original.get("sender_id", ""),
                "content": snippet,
                "type": original.get("type", "text"),
            }
        else:
            reply_to = None  # original não existe mais → não cita

    message = {
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,

        "content": data.content,

        "type": data.type,
        "file_url": data.file_url,

        "reply_to": reply_to,
        "reply_preview": reply_preview,

        "status": status,
        "read": is_self,  # auto-conversa: já "lida" → não vira badge de não lida
        "read_by": [],
        # bloqueado → oculta do bloqueador (ele nunca vê nem é notificado)
        "deleted_for": [data.receiver_id] if is_blocked else [],
        "created_at": now
    }

    result = await db.messages.insert_one(message)

    # Bloqueado: não mexe na conversa do bloqueador (sem preview/“ressuscitar”).
    if not is_blocked:
        await db.chats.update_one(
            {"_id": chat_oid},
            {
                "$set": {
                    "updated_at": now,
                    "last_message": {
                        "content": data.content,
                        "type": data.type,
                        "created_at": now,
                        "status": status
                    },
                    # nova mensagem "ressuscita" a conversa para quem a apagou
                    "deleted_by": [],
                }
            }
        )

    ws_message = {
        "type": "new_message",         # permite filtrar no frontend
        "_id": str(result.inserted_id),
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "type_msg": data.type,         # "text" | "file" | "audio"
        "file_url": data.file_url,
        "reply_to": reply_to,
        "reply_preview": reply_preview,
        "created_at": now.isoformat(),
        "status": status,
    }

    # Notifica o destinatário em tempo-real — exceto se ele bloqueou o remetente.
    if not is_blocked:
        await manager.send_personal_message(data.receiver_id, ws_message)
    # Notifica também o remetente (para multi-dispositivo / confirmação imediata)
    await manager.send_personal_message(current_user["sub"], ws_message)

    # @Humberto mencionado na conversa → ele responde ali mesmo (mensagem da IA).
    # Import tardio evita ciclo (ai.service importa deliver_direct_message daqui).
    if not is_blocked and (data.type or "text") == "text":
        from app.modules.ai.service import (
            mentions_humberto, strip_humberto_mention, humberto_reply, HUMBERTO_USER_ID,
        )
        if mentions_humberto(data.content):
            reply_text = await humberto_reply(strip_humberto_mention(data.content))
            now2 = datetime.now(timezone.utc)
            hmsg = {
                "chat_id": data.chat_id,
                "sender_id": HUMBERTO_USER_ID,
                "receiver_id": current_user["sub"],
                "content": reply_text,
                "type": "text",
                "file_url": None,
                "reply_to": None,
                "reply_preview": None,
                "status": "delivered",
                "read": False,
                "read_by": [],
                "created_at": now2,
            }
            hres = await db.messages.insert_one(hmsg)
            await db.chats.update_one(
                {"_id": chat_oid},
                {"$set": {
                    "updated_at": now2,
                    "last_message": {
                        "content": reply_text, "type": "text",
                        "created_at": now2, "status": "delivered",
                    },
                    "deleted_by": [],
                }},
            )
            hws = {
                "type": "new_message",
                "_id": str(hres.inserted_id),
                "chat_id": data.chat_id,
                "sender_id": HUMBERTO_USER_ID,
                "receiver_id": current_user["sub"],
                "content": reply_text,
                "type_msg": "text",
                "file_url": None,
                "created_at": now2.isoformat(),
                "status": "delivered",
            }
            await manager.send_personal_message(current_user["sub"], hws)
            await manager.send_personal_message(data.receiver_id, hws)

    return {
        "message": "sent",
        "status": status,
        # retorna a mensagem completa para atualização otimista no frontend
        "_id": str(result.inserted_id),
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,
        "content": data.content,
        "type": data.type,
        "file_url": data.file_url,
        "reply_to": reply_to,
        "reply_preview": reply_preview,
        "created_at": now.isoformat(),
        "read": False,
        "edited": False,
        "deleted": False,
    }

async def toggle_favorite(current_user, message_id):
    """Favorita/desfavorita uma mensagem (por usuário, em favorited_by)."""
    db = get_database()

    try:
        oid = ObjectId(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    uid = current_user["sub"]
    msg = await db.messages.find_one({"_id": oid}, {"favorited_by": 1})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    is_fav = uid in (msg.get("favorited_by") or [])
    op = {"$pull": {"favorited_by": uid}} if is_fav else {"$addToSet": {"favorited_by": uid}}
    await db.messages.update_one({"_id": oid}, op)

    return {"message": "ok", "favorited": not is_fav}


async def delete_message_for_me(current_user, message_id):
    """Apaga a mensagem SÓ para o usuário atual (some da lista dele;
    o outro lado continua vendo). Vale para qualquer mensagem."""
    db = get_database()

    try:
        oid = ObjectId(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    await db.messages.update_one(
        {"_id": oid},
        {"$addToSet": {"deleted_for": current_user["sub"]}},
    )

    return {"message": "deleted_for_me"}


async def delete_message(current_user, message_id):
    db = get_database()

    message = await db.messages.find_one({
        "_id": ObjectId(message_id)
    })

    if not message:
        return {"error": "Message not found"}

    # "apagar para todos": só o remetente pode
    if message.get("sender_id") != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the sender can delete for everyone")

    await db.messages.update_one(
        {
            "_id": ObjectId(message_id),
            "sender_id": current_user["sub"]
        },
        {
            "$set": {
                "deleted": True,
                "content": "Mensagem apagada"
            }
        }
    )

    await manager.send_personal_message(
        message["receiver_id"],
        {
            "type": "message_deleted",
            "message_id": message_id
        }
    )

    return {"message": "deleted"}

async def edit_message(current_user, message_id, content):
    db = get_database()

    message = await db.messages.find_one({
        "_id": ObjectId(message_id)
    })

    if not message:
        return {"error": "Message not found"}

    await db.messages.update_one(
        {
            "_id": ObjectId(message_id),
            "sender_id": current_user["sub"]
        },
        {
            "$set": {
                "content": content,
                "edited": True
            }
        }
    )

    await manager.send_personal_message(
        message["receiver_id"],
        {
            "type": "message_edited",
            "message_id": message_id,
            "content": content
        }
    )

    return {"message": "edited"}

async def mark_as_read(chat_id, user):
    db = get_database()

    # Privacidade: se o leitor desativou as confirmações, não revela a leitura
    # (sem status "read"/read_by/broadcast). O campo "read" ainda é setado para
    # zerar o contador de não-lidas DO PRÓPRIO leitor.
    try:
        reader = await db.users.find_one(
            {"_id": ObjectId(user["sub"])}, {"show_read_receipts": 1}
        )
    except Exception:
        reader = None
    reveal = (reader or {}).get("show_read_receipts", True)

    set_fields = {"read": True}
    update = {"$set": set_fields}
    if reveal:
        set_fields["status"] = "read"
        set_fields["read_at"] = datetime.now(timezone.utc)
        update["$addToSet"] = {"read_by": user["sub"]}

    result = await db.messages.update_many(
        {
            "chat_id": chat_id,
            "receiver_id": user["sub"],
            "read": False
        },
        update,
    )

    # Avisa o(s) remetente(s) p/ atualizar os ticks → ✓✓ verde — só se revela
    if reveal and result.modified_count:
        try:
            chat = await db.chats.find_one({"_id": ObjectId(chat_id)})
        except Exception:
            chat = None
        if chat:
            others = [
                p
                for p in (chat.get("participants") or chat.get("members") or [])
                if p != user["sub"]
            ]
            for sender_id in others:
                await manager.send_personal_message(
                    sender_id,
                    {
                        "type": "messages_read",
                        "chat_id": chat_id,
                        "reader_id": user["sub"],
                    },
                )

    return {"message": "updated"}

async def clear_chat(chat_id, user):
    """Limpa a conversa SÓ para o usuário atual (soft): marca cleared_at;
    get_messages passa a filtrar mensagens anteriores a esse instante."""
    db = get_database()
    await db.user_chat_settings.update_one(
        {"user_id": user["sub"], "chat_id": chat_id},
        {"$set": {"cleared_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"message": "cleared"}


async def get_messages(chat_id: str, skip: int = 0, limit: int = 50, user_id: str | None = None):
    db = get_database()

    query = {"chat_id": chat_id}

    if user_id:
        # "apagar para mim" (per-user): some só para quem apagou
        query["deleted_for"] = {"$ne": user_id}

        # filtro de "limpar conversa" (per-user): só mensagens após cleared_at
        settings = await db.user_chat_settings.find_one(
            {"user_id": user_id, "chat_id": chat_id}
        )
        cleared_at = settings.get("cleared_at") if settings else None
        if cleared_at:
            query["created_at"] = {"$gt": cleared_at}

    # Página 0 = as MAIS RECENTES (sort desc + skip), depois inverte para
    # exibir em ordem cronológica. Antes era sort asc → página 0 trazia as 50
    # mais ANTIGAS: em conversas longas a mensagem recém-enviada não entrava
    # na janela, então o refetch via WebSocket a fazia "piscar e sumir", e as
    # não-lidas (recentes) nunca carregavam → badge nunca zerava.
    messages = await db.messages.find(query).sort("created_at", -1).skip(skip).to_list(limit)
    messages.reverse()

    parsed = []

    for message in messages:
        # .get() em TODOS os campos — uma única mensagem legada/sem chave
        # quebrava a rota inteira com KeyError (500) e a conversa "parava de
        # enviar/receber" porque o histórico nunca carregava.
        parsed.append({
            "_id": str(message["_id"]),
            "chat_id": message.get("chat_id", chat_id),
            "sender_id": message.get("sender_id", ""),
            "receiver_id": message.get("receiver_id", ""),
            "content": message.get("content", ""),
            "type": message.get("type", "text"),
            "file_url": message.get("file_url"),
            "status": message.get("status"),
            "read": message.get("read"),
            "read_by": message.get("read_by", []),
            "edited": message.get("edited", False),
            "deleted": message.get("deleted", False),
            "reply_to": message.get("reply_to"),
            "reply_preview": message.get("reply_preview"),
            "favorited": bool(user_id) and user_id in (message.get("favorited_by") or []),
            "created_at": _iso_utc(message.get("created_at")),
        })

    return parsed