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


def _serialize_message(m, user_id=None):
    return {
        "_id": str(m["_id"]),
        "group_id": m.get("group_id", ""),
        "sender_id": m.get("sender_id", ""),
        "content": m.get("content", ""),
        "type": m.get("type", "text"),
        "file_url": m.get("file_url"),
        "reply_to": m.get("reply_to"),
        "reply_preview": m.get("reply_preview"),
        "deleted": m.get("deleted", False),
        "edited": m.get("edited", False),
        "favorited": bool(user_id) and user_id in (m.get("favorited_by") or []),
        "created_at": _iso(m.get("created_at")),
    }


async def _display_name(db, user_id):
    """Nome de exibição de um usuário (para mensagens de sistema)."""
    if user_id == "humberto":
        return "Humberto"
    oid = _oid(user_id)
    if not oid:
        return "Alguém"
    u = await db.users.find_one({"_id": oid}, {"display_name": 1, "name": 1})
    if not u:
        return "Alguém"
    return u.get("display_name") or u.get("name") or "Alguém"


async def _system_message(db, group, text):
    """Insere uma mensagem de sistema no grupo e notifica todos (entrou/saiu/
    alteração de configurações). Aparece centralizada no histórico."""
    oid = group["_id"]
    group_id = str(oid)
    now = datetime.now(timezone.utc)
    msg = {
        "group_id": group_id,
        "sender_id": "system",
        "content": text,
        "type": "system",
        "file_url": None,
        "created_at": now,
    }
    res = await db.group_messages.insert_one(msg)
    await db.groups.update_one(
        {"_id": oid},
        {"$set": {"updated_at": now, "last_message": {
            "content": text, "sender_id": "system", "created_at": _iso(now),
        }}},
    )
    ws = {
        "type": "group_message",
        "_id": str(res.inserted_id),
        "group_id": group_id,
        "sender_id": "system",
        "content": text,
        "msg_type": "system",
        "file_url": None,
        "created_at": _iso(now),
    }
    for member_id in group.get("members", []):
        await manager.send_personal_message(member_id, ws)


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
    # Filtra "apagar para mim" (deleted_for) do usuário atual.
    messages = await db.group_messages.find(
        {"group_id": group_id, "deleted_for": {"$ne": current_user["sub"]}}
    ).sort("created_at", -1).skip(skip).to_list(limit)
    messages.reverse()

    return [_serialize_message(m, current_user["sub"]) for m in messages]


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

    # Resposta: denormaliza prévia da original (igual ao 1:1).
    reply_to = getattr(data, "reply_to", None) or None
    reply_preview = None
    if reply_to:
        orig_oid = _oid(reply_to)
        original = await db.group_messages.find_one({"_id": orig_oid}) if orig_oid else None
        if original:
            reply_preview = {
                "_id": str(original["_id"]),
                "sender_id": original.get("sender_id", ""),
                "content": (original.get("content") or "")[:120],
                "type": original.get("type", "text"),
            }
        else:
            reply_to = None

    now = datetime.now(timezone.utc)
    message = {
        "group_id": data.group_id,
        "sender_id": current_user["sub"],
        "content": content,
        "type": msg_type,
        "file_url": file_url,
        "reply_to": reply_to,
        "reply_preview": reply_preview,
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
        "reply_to": reply_to,
        "reply_preview": reply_preview,
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

    return _serialize_message({**message, "_id": result.inserted_id}, current_user["sub"])


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

    # Mensagem de sistema descrevendo a alteração.
    actor = await _display_name(db, current_user["sub"])
    changes = []
    if "name" in updates:
        changes.append(f'renomeou o grupo para "{updates["name"]}"')
    if "description" in updates:
        changes.append("alterou a descrição" if updates["description"] else "removeu a descrição")
    if "only_admins_can_send" in updates:
        changes.append(
            "ativou: só admins enviam mensagens"
            if updates["only_admins_can_send"]
            else "liberou o envio de mensagens para todos"
        )
    if changes:
        await _system_message(db, updated, f"{actor} {'; '.join(changes)}.")

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
    target = await _display_name(db, data.user_id)
    note = f"{target} agora é administrador." if data.make_admin else f"{target} deixou de ser administrador."
    await _system_message(db, updated, note)
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

    already = data.user_id in group.get("members", [])
    await db.groups.update_one(
        {"_id": oid},
        {"$addToSet": {"members": data.user_id}},
    )
    if not already:
        updated = await db.groups.find_one({"_id": oid})
        actor = await _display_name(db, current_user["sub"])
        target = await _display_name(db, data.user_id)
        await _system_message(db, updated, f"{actor} adicionou {target}.")
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

    target = await _display_name(db, data.user_id)
    await db.groups.update_one(
        {"_id": oid},
        {"$pull": {"members": data.user_id, "admins": data.user_id}},
    )
    # grupo (com members atualizados) para notificar quem ficou
    updated = await db.groups.find_one({"_id": oid})
    actor = await _display_name(db, current_user["sub"])
    await _system_message(db, updated, f"{actor} removeu {target}.")
    return {"message": "Membro removido"}


async def leave_group(current_user, group_id):
    db = get_database()

    oid = _oid(group_id)
    if not oid:
        return {"error": "Grupo inválido"}

    actor = await _display_name(db, current_user["sub"])
    await db.groups.update_one(
        {"_id": oid},
        {"$pull": {
            "members": current_user["sub"],
            "admins": current_user["sub"],
        }},
    )
    # avisa quem ficou (grupo já sem o usuário que saiu)
    updated = await db.groups.find_one({"_id": oid})
    if updated:
        await _system_message(db, updated, f"{actor} saiu do grupo.")
    return {"message": "Você saiu do grupo"}


async def join_by_code(current_user, code):
    db = get_database()

    group = await db.groups.find_one({"invite_code": code})
    if not group:
        return {"error": "Código inválido"}

    already = current_user["sub"] in group.get("members", [])
    await db.groups.update_one(
        {"invite_code": code},
        {"$addToSet": {"members": current_user["sub"]}},
    )
    if not already:
        updated = await db.groups.find_one({"invite_code": code})
        actor = await _display_name(db, current_user["sub"])
        await _system_message(db, updated, f"{actor} entrou no grupo.")
    return {"message": "Você entrou no grupo", "group_id": str(group["_id"])}


# ── Reações/remoção de mensagens do grupo (paridade com o 1:1) ───────────────
async def favorite_group_message(current_user, message_id):
    """Favorita/desfavorita (por usuário)."""
    db = get_database()
    oid = _oid(message_id)
    if not oid:
        return {"error": "Mensagem inválida"}
    msg = await db.group_messages.find_one({"_id": oid}, {"favorited_by": 1})
    if not msg:
        return {"error": "Mensagem não encontrada"}
    uid = current_user["sub"]
    is_fav = uid in (msg.get("favorited_by") or [])
    op = {"$pull": {"favorited_by": uid}} if is_fav else {"$addToSet": {"favorited_by": uid}}
    await db.group_messages.update_one({"_id": oid}, op)
    return {"message": "ok", "favorited": not is_fav}


async def delete_group_message_for_me(current_user, message_id):
    """Apaga só para o usuário atual (deleted_for)."""
    db = get_database()
    oid = _oid(message_id)
    if not oid:
        return {"error": "Mensagem inválida"}
    await db.group_messages.update_one(
        {"_id": oid}, {"$addToSet": {"deleted_for": current_user["sub"]}}
    )
    return {"message": "deleted_for_me"}


async def delete_group_message(current_user, message_id):
    """Apaga para todos. Pode: o autor OU um administrador do grupo."""
    db = get_database()
    oid = _oid(message_id)
    if not oid:
        return {"error": "Mensagem inválida"}

    msg = await db.group_messages.find_one({"_id": oid})
    if not msg:
        return {"error": "Mensagem não encontrada"}

    goid = _oid(msg.get("group_id"))
    group = await db.groups.find_one({"_id": goid}) if goid else None
    if not group:
        return {"error": "Grupo não encontrado"}

    uid = current_user["sub"]
    is_author = msg.get("sender_id") == uid
    is_admin = uid in group.get("admins", [])
    if not (is_author or is_admin):
        return {"error": "Sem permissão para apagar esta mensagem"}

    await db.group_messages.update_one(
        {"_id": oid},
        {"$set": {"deleted": True, "content": "Mensagem apagada", "file_url": None}},
    )
    ws = {
        "type": "group_message_deleted",
        "group_id": msg.get("group_id"),
        "message_id": message_id,
    }
    for member_id in group.get("members", []):
        await manager.send_personal_message(member_id, ws)
    return {"message": "deleted"}
