from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_database
from app.core.websocket import manager


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

    # Destinatário bloqueou o remetente → retorna 403 (erro real, não 200 silencioso)
    blocked = await db.blocked_users.find_one({
        "user_id": data.receiver_id,
        "blocked_user_id": current_user["sub"]
    })

    if blocked:
        # log p/ diagnóstico no Render — identifica conversas "travadas" por bloqueio
        print(f"[SEND] 403 blocked: {current_user['sub']} -> {data.receiver_id} (chat {data.chat_id})")
        raise HTTPException(status_code=403, detail="blocked")

    now = datetime.now(timezone.utc)

    status = (
        "delivered"
        if manager.is_online(data.receiver_id)
        else "sent"
    )

    message = {
        "chat_id": data.chat_id,
        "sender_id": current_user["sub"],
        "receiver_id": data.receiver_id,

        "content": data.content,

        "type": data.type,
        "file_url": data.file_url,

        "status": status,
        "read": False,
        "read_by": [],
        "created_at": now
    }

    result = await db.messages.insert_one(message)

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
        "created_at": now.isoformat(),
        "status": status,
    }

    # Notifica o destinatário em tempo-real
    await manager.send_personal_message(data.receiver_id, ws_message)
    # Notifica também o remetente (para multi-dispositivo / confirmação imediata)
    await manager.send_personal_message(current_user["sub"], ws_message)

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
        "created_at": now.isoformat(),
        "read": False,
        "edited": False,
        "deleted": False,
    }

async def delete_message(current_user, message_id):
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

    # filtro de "limpar conversa" (per-user): só mensagens após cleared_at
    if user_id:
        settings = await db.user_chat_settings.find_one(
            {"user_id": user_id, "chat_id": chat_id}
        )
        cleared_at = settings.get("cleared_at") if settings else None
        if cleared_at:
            query["created_at"] = {"$gt": cleared_at}

    messages = await db.messages.find(query).sort("created_at", 1).skip(skip).to_list(limit)

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
            "created_at": _iso_utc(message.get("created_at")),
        })

    return parsed