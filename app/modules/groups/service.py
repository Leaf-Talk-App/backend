import secrets
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.core.database import get_database
from app.core.websocket import manager


def _iso(dt):
    """datetime → ISO 8601 UTC (com sufixo Z). None → None."""
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _oid(value):
    """Converte string → ObjectId; inválido → None (evita 500)."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _serialize_group(g, last_message=None):
    return {
        "_id": str(g["_id"]),
        "name": g.get("name", "Grupo"),
        "description": g.get("description", ""),
        "photo": g.get("photo"),
        "members": g.get("members", []),
        "admins": g.get("admins", []),
        "only_admins_can_send": bool(g.get("only_admins_can_send", False)),
        "invite_code": g.get("invite_code"),
        "created_by": g.get("created_by"),
        "member_count": len(g.get("members", [])),
        "last_message": last_message,
        "created_at": _iso(g.get("created_at")),
        "updated_at": _iso(g.get("updated_at")),
    }


def _serialize_message(m):
    return {
        "_id": str(m["_id"]),
        "group_id": m.get("group_id", ""),
        "sender_id": m.get("sender_id", ""),
        "content": m.get("content", ""),
        "type": m.get("type", "text"),
        "file_url": m.get("file_url"),
        "created_at": _iso(m.get("created_at")),
    }


async def create_group(current_user, data):
    db = get_database()

    name = (data.name or "").strip()
    if not name:
        return {"error": "Nome do grupo é obrigatório"}

    # remove duplicados e garante o criador como membro
    members = list({*(data.members or []), current_user["sub"]})

    now = datetime.now(timezone.utc)
    group = {
        "name": name,
        "description": "",
        "photo": None,
        "members": members,
        "admins": [current_user["sub"]],
        "only_admins_can_send": False,
        "invite_code": secrets.token_hex(4),
        "created_by": current_user["sub"],
        "created_at": now,
        "updated_at": now,
        "last_message": None,
    }

    result = await db.groups.insert_one(group)
    return {"group_id": str(result.inserted_id)}


async def my_groups(current_user):
    db = get_database()

    groups = await db.groups.find(
        {"members": current_user["sub"]}
    ).sort("updated_at", -1).to_list(100)

    return [_serialize_group(g, g.get("last_message")) for g in groups]


async def get_group(current_user, group_id):
    db = get_database()

    oid = _oid(group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("members", []):
        return {"error": "Você não faz parte deste grupo"}

    return _serialize_group(group, group.get("last_message"))


async def get_group_messages(current_user, group_id, skip: int = 0, limit: int = 50):
    db = get_database()

    oid = _oid(group_id)
    if not oid:
        return []

    group = await db.groups.find_one({"_id": oid})
    if not group or current_user["sub"] not in group.get("members", []):
        return []

    # Página 0 = mais recentes (desc + skip), depois inverte para ordem cronológica.
    messages = await db.group_messages.find(
        {"group_id": group_id}
    ).sort("created_at", -1).skip(skip).to_list(limit)
    messages.reverse()

    return [_serialize_message(m) for m in messages]


async def send_group_message(current_user, data):
    db = get_database()

    oid = _oid(data.group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("members", []):
        return {"error": "Você não faz parte deste grupo"}

    # Regra interna: só admins enviam mensagens (se ativada).
    if group.get("only_admins_can_send") and current_user["sub"] not in group.get("admins", []):
        return {"error": "Apenas administradores podem enviar mensagens neste grupo"}

    content = (data.content or "").strip()
    msg_type = getattr(data, "type", None) or "text"
    file_url = getattr(data, "file_url", None)
    if not content and not file_url:
        return {"error": "Mensagem vazia"}

    now = datetime.now(timezone.utc)
    message = {
        "group_id": data.group_id,
        "sender_id": current_user["sub"],
        "content": content,
        "type": msg_type,
        "file_url": file_url,
        "created_at": now,
    }

    result = await db.group_messages.insert_one(message)

    # prévia da última mensagem para a lista de grupos
    preview = content or ("📎 Arquivo" if file_url else "")
    await db.groups.update_one(
        {"_id": oid},
        {"$set": {
            "updated_at": now,
            "last_message": {
                "content": preview,
                "sender_id": current_user["sub"],
                "created_at": _iso(now),
            },
        }},
    )

    ws_message = {
        "type": "group_message",
        "_id": str(result.inserted_id),
        "group_id": data.group_id,
        "sender_id": current_user["sub"],
        "content": content,
        "msg_type": msg_type,
        "file_url": file_url,
        "created_at": _iso(now),
    }

    for member_id in group.get("members", []):
        if member_id != current_user["sub"]:
            await manager.send_personal_message(member_id, ws_message)

    # @Humberto mencionado no grupo → responde ali mesmo. Import tardio evita ciclo.
    if msg_type == "text":
        from app.modules.ai.service import (
            mentions_humberto, strip_humberto_mention, humberto_reply, HUMBERTO_USER_ID,
        )
        if mentions_humberto(content):
            reply_text = await humberto_reply(strip_humberto_mention(content))
            now2 = datetime.now(timezone.utc)
            hmsg = {
                "group_id": data.group_id,
                "sender_id": HUMBERTO_USER_ID,
                "content": reply_text,
                "type": "text",
                "file_url": None,
                "created_at": now2,
            }
            hres = await db.group_messages.insert_one(hmsg)
            await db.groups.update_one(
                {"_id": oid},
                {"$set": {
                    "updated_at": now2,
                    "last_message": {
                        "content": reply_text,
                        "sender_id": HUMBERTO_USER_ID,
                        "created_at": _iso(now2),
                    },
                }},
            )
            hws = {
                "type": "group_message",
                "_id": str(hres.inserted_id),
                "group_id": data.group_id,
                "sender_id": HUMBERTO_USER_ID,
                "content": reply_text,
                "msg_type": "text",
                "file_url": None,
                "created_at": _iso(now2),
            }
            for member_id in group.get("members", []):
                await manager.send_personal_message(member_id, hws)

    return _serialize_message({**message, "_id": result.inserted_id})


async def update_group(current_user, data):
    """Renomeia, define descrição e regra de envio. Apenas admin."""
    db = get_database()

    oid = _oid(data.group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("admins", []):
        return {"error": "Apenas administradores podem editar o grupo"}

    updates = {}
    if data.name is not None:
        name = data.name.strip()
        if not name:
            return {"error": "Nome do grupo é obrigatório"}
        updates["name"] = name
    if data.description is not None:
        updates["description"] = data.description.strip()
    if data.only_admins_can_send is not None:
        updates["only_admins_can_send"] = bool(data.only_admins_can_send)

    if not updates:
        return _serialize_group(group, group.get("last_message"))

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.groups.update_one({"_id": oid}, {"$set": updates})

    updated = await db.groups.find_one({"_id": oid})
    serialized = _serialize_group(updated, updated.get("last_message"))

    # Notifica os membros para refetch do detalhe do grupo.
    ws = {"type": "group_updated", "group_id": data.group_id}
    for member_id in group.get("members", []):
        await manager.send_personal_message(member_id, ws)

    return serialized


async def set_admin(current_user, data):
    """Promove/rebaixa um membro a administrador. Apenas admin."""
    db = get_database()

    oid = _oid(data.group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("admins", []):
        return {"error": "Apenas administradores podem alterar permissões"}

    if data.user_id not in group.get("members", []):
        return {"error": "Usuário não faz parte do grupo"}

    if data.make_admin:
        await db.groups.update_one({"_id": oid}, {"$addToSet": {"admins": data.user_id}})
        msg = "Membro promovido a administrador"
    else:
        # criador nunca perde o admin
        if data.user_id == group.get("created_by"):
            return {"error": "O criador do grupo não pode deixar de ser administrador"}
        await db.groups.update_one({"_id": oid}, {"$pull": {"admins": data.user_id}})
        msg = "Administrador rebaixado a membro"

    updated = await db.groups.find_one({"_id": oid})
    return {"message": msg, "group": _serialize_group(updated, updated.get("last_message"))}


async def add_member(current_user, data):
    db = get_database()

    oid = _oid(data.group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("admins", []):
        return {"error": "Apenas administradores podem adicionar membros"}

    await db.groups.update_one(
        {"_id": oid},
        {"$addToSet": {"members": data.user_id}},
    )
    return {"message": "Membro adicionado"}


async def remove_member(current_user, data):
    db = get_database()

    oid = _oid(data.group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    group = await db.groups.find_one({"_id": oid})
    if not group:
        return {"error": "Grupo não encontrado"}

    if current_user["sub"] not in group.get("admins", []):
        return {"error": "Apenas administradores podem remover membros"}

    await db.groups.update_one(
        {"_id": oid},
        {"$pull": {"members": data.user_id, "admins": data.user_id}},
    )
    return {"message": "Membro removido"}


async def leave_group(current_user, group_id):
    db = get_database()

    oid = _oid(group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    await db.groups.update_one(
        {"_id": oid},
        {"$pull": {
            "members": current_user["sub"],
            "admins": current_user["sub"],
        }},
    )
    return {"message": "Você saiu do grupo"}


async def join_by_code(current_user, code):
    db = get_database()

    group = await db.groups.find_one({"invite_code": code})
    if not group:
        return {"error": "Código inválido"}

    await db.groups.update_one(
        {"invite_code": code},
        {"$addToSet": {"members": current_user["sub"]}},
    )
    return {"message": "Você entrou no grupo", "group_id": str(group["_id"])}
