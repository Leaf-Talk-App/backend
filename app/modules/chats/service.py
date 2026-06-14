from datetime import datetime, timedelta, timezone
from bson import ObjectId
from fastapi import HTTPException
from app.core.database import get_database
from app.core.websocket import manager

MAX_PINNED = 3  # limite de conversas fixadas por usuário


def _is_muted(settings) -> bool:
    """muted efetivo: respeita muted_until (expira sozinho)."""
    if not settings or not settings.get("muted"):
        return False
    until = settings.get("muted_until")
    if until is None:
        return True  # para sempre
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > datetime.now(timezone.utc)

async def create_chat(current_user, data):
    db = get_database()

    participants = sorted([
        current_user["sub"],
        data.user_id
    ])

    existing = await db.chats.find_one({
        "participants": participants
    })

    if existing:
        return {
            "chat_id": str(existing["_id"]),
            "existing": True
        }

    chat = {
        "participants": participants,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_message": None
    }

    result = await db.chats.insert_one(chat)

    return {
        "chat_id": str(result.inserted_id),
        "existing": False
    }

async def list_chats(current_user):
    db = get_database()

    chats = await db.chats.find({
        "participants": current_user["sub"]
    }).sort("updated_at", -1).to_list(50)

    for chat in chats:
        chat["_id"] = str(chat["_id"])

    return chats

async def archive_chat(current_user, data):
    db = get_database()

    existing = await db.user_chat_settings.find_one({
        "user_id": current_user["sub"],
        "chat_id": data.chat_id,
    })
    new_val = not (existing.get("archived", False) if existing else False)

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "archived": new_val
            }
        },
        upsert=True
    )

    return {"message": "Chat archived" if new_val else "Chat unarchived", "archived": new_val}


async def pin_chat(current_user, data):
    """Fixa/desafixa (toggle). Máximo de 3 conversas fixadas por usuário."""
    db = get_database()
    user_id = current_user["sub"]

    existing = await db.user_chat_settings.find_one(
        {"user_id": user_id, "chat_id": data.chat_id}
    )
    currently = bool(existing and existing.get("pinned"))

    if not currently:
        count = await db.user_chat_settings.count_documents(
            {"user_id": user_id, "pinned": True}
        )
        if count >= MAX_PINNED:
            return {
                "error": f"Você pode fixar no máximo {MAX_PINNED} conversas.",
                "pinned": False,
            }

    await db.user_chat_settings.update_one(
        {"user_id": user_id, "chat_id": data.chat_id},
        {"$set": {"pinned": not currently}},
        upsert=True,
    )
    return {"message": "ok", "pinned": not currently}


async def mute_chat(current_user, data):
    db = get_database()

    if data.unmute:
        # Reativar notificações
        await db.user_chat_settings.update_one(
            {"user_id": current_user["sub"], "chat_id": data.chat_id},
            {"$set": {"muted": False, "muted_until": None}},
            upsert=True,
        )
        return {"message": "Chat unmuted", "muted": False}

    # Silenciar: mute_minutes>0 → expira; None → para sempre
    until = None
    if data.mute_minutes:
        until = datetime.now(timezone.utc) + timedelta(minutes=data.mute_minutes)

    await db.user_chat_settings.update_one(
        {"user_id": current_user["sub"], "chat_id": data.chat_id},
        {"$set": {"muted": True, "muted_until": until}},
        upsert=True,
    )

    return {
        "message": "Chat muted",
        "muted": True,
        "muted_until": until.isoformat() if until else None,
    }


async def hide_chat(current_user, data):
    db = get_database()

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": data.chat_id
        },
        {
            "$set": {
                "hidden": True
            }
        },
        upsert=True
    )

    return {"message": "Chat hidden"}

async def delete_chat(current_user, chat_id):
    """Apaga a conversa SÓ para o usuário atual (soft delete):
    - adiciona o usuário em chats.deleted_by → some da lista dele;
    - marca cleared_at → o histórico antigo não volta para ele.
    Se o outro lado enviar nova mensagem, send_message zera deleted_by e a
    conversa reaparece (apenas com as mensagens novas para quem apagou)."""
    db = get_database()

    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    await db.chats.update_one(
        {"_id": oid},
        {"$addToSet": {"deleted_by": current_user["sub"]}},
    )

    await db.user_chat_settings.update_one(
        {
            "user_id": current_user["sub"],
            "chat_id": chat_id
        },
        {"$set": {"cleared_at": datetime.utcnow()}},
        upsert=True
    )

    return {"message": "Chat deleted"}


def _iso(dt):
    return dt.isoformat() if hasattr(dt, "isoformat") else (dt or "")


def _serialize_last_message(raw_lm):
    if not raw_lm:
        return None
    lm_created = raw_lm.get("created_at")
    return {
        **{k: v for k, v in raw_lm.items() if k != "created_at"},
        "created_at": _iso(lm_created),
    }


async def my_chats(current_user):
    """Lista conversas 1:1 + grupos do usuário numa só resposta.

    Otimizado: antes fazia N+1 (1 settings + 1 contagem de não-lidas POR chat)
    e o frontend ainda buscava cada usuário separado → lista demorava a aparecer.
    Agora são poucas queries em lote (settings, não-lidas via aggregation, e os
    dados dos outros participantes embutidos em `other_user`).
    """
    db = get_database()
    user_id = current_user["sub"]

    chats = await db.chats.find({"participants": user_id}).to_list(200)
    groups = await db.groups.find({"members": user_id}).to_list(200)

    chat_ids = [str(c["_id"]) for c in chats]
    group_ids = [str(g["_id"]) for g in groups]
    all_ids = chat_ids + group_ids

    # 1 query: todos os settings (pin/mute/hidden/archived/cleared) do usuário
    settings_by_id = {}
    if all_ids:
        for s in await db.user_chat_settings.find(
            {"user_id": user_id, "chat_id": {"$in": all_ids}}
        ).to_list(2000):
            settings_by_id[s["chat_id"]] = s

    # 1 query: contagem de não-lidas agrupada por chat
    unread_by_chat = {}
    if chat_ids:
        agg = await db.messages.aggregate([
            {"$match": {"chat_id": {"$in": chat_ids}, "receiver_id": user_id, "read": False}},
            {"$group": {"_id": "$chat_id", "count": {"$sum": 1}}},
        ]).to_list(2000)
        unread_by_chat = {a["_id"]: a["count"] for a in agg}

    # outro participante de cada 1:1
    other_id_by_chat = {}
    other_ids = set()
    for chat in chats:
        parts = chat.get("participants") or []
        others = [p for p in parts if p != user_id]
        oid = others[0] if others else (parts[0] if parts else None)
        if oid:
            other_id_by_chat[str(chat["_id"])] = oid
            other_ids.add(oid)

    # 1 query: dados básicos dos outros participantes (embed → sem N+1 no front)
    users_by_id = {}
    valid_oids = [ObjectId(i) for i in other_ids if ObjectId.is_valid(i)]
    if valid_oids:
        for u in await db.users.find(
            {"_id": {"$in": valid_oids}}, {"password": 0}
        ).to_list(2000):
            uid = str(u["_id"])
            users_by_id[uid] = {
                "id": uid,
                "_id": uid,
                "name": u.get("name", ""),
                "display_name": u.get("display_name"),
                "avatar": u.get("avatar"),
                "online": manager.is_online(uid),
                "last_seen": _iso(u.get("last_seen")) or None,
            }

    result = []

    for chat in chats:
        chat_id = str(chat["_id"])
        if user_id in (chat.get("deleted_by") or []):
            continue
        settings = settings_by_id.get(chat_id)
        if settings and settings.get("hidden"):
            continue
        oid = other_id_by_chat.get(chat_id)
        result.append({
            "_id": chat_id,
            "kind": "chat",
            "participants": chat.get("participants"),
            "other_user": users_by_id.get(oid) if oid else None,
            "updated_at": _iso(chat.get("updated_at")),
            "last_message": _serialize_last_message(chat.get("last_message")),
            "pinned": settings.get("pinned", False) if settings else False,
            "archived": settings.get("archived", False) if settings else False,
            "muted": _is_muted(settings),
            "unread_count": unread_by_chat.get(chat_id, 0),
        })

    for g in groups:
        gid = str(g["_id"])
        settings = settings_by_id.get(gid)
        if settings and settings.get("hidden"):
            continue
        result.append({
            "_id": gid,
            "kind": "group",
            "name": g.get("name", "Grupo"),
            "photo": g.get("photo"),
            "members": g.get("members", []),
            "member_count": len(g.get("members", [])),
            "updated_at": _iso(g.get("updated_at")),
            "last_message": _serialize_last_message(g.get("last_message")),
            "pinned": settings.get("pinned", False) if settings else False,
            "archived": settings.get("archived", False) if settings else False,
            "muted": _is_muted(settings),
            "unread_count": 0,
        })

    # Ordena (sort estável, em 2 passes): 1º por data desc (mais recente no topo),
    # depois por (arquivado, não-fixado) — fixados sobem ao topo, arquivados caem.
    # Antes era um sort+reverse global que invertia também os booleanos e jogava
    # os fixados pro FIM.
    result.sort(key=lambda x: x["updated_at"] or "", reverse=True)
    result.sort(key=lambda x: (x["archived"], not x["pinned"]))
    return result