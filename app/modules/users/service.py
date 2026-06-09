import re
from app.core.database import get_database
from app.core.websocket import manager
from bson import ObjectId
from fastapi import HTTPException

async def get_me(user_data):
    db = get_database()

    user = await db.users.find_one(
        {"email": user_data["email"]},
        {
            "password": 0,
            "verification_code": 0,
            "verification_code_expires_at": 0,
            "reset_token": 0,
            "reset_token_expires_at": 0,
        },
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user["_id"] = str(user["_id"])
    user["id"] = user["_id"]

    return user


async def update_profile(user_data, data):
    db = get_database()

    payload = data.model_dump(exclude_none=True)
    # phone_normalized = só dígitos → permite login por telefone (lookup exato).
    if "phone" in payload:
        payload["phone_normalized"] = re.sub(r"\D", "", payload["phone"]) or None

    await db.users.update_one(
        {"email": user_data["email"]},
        {"$set": payload},
    )

    return {"message": "Profile updated"}


async def search_users(current_user, query):
    db = get_database()

    term = (query or "").strip()

    blocked = await db.blocked_users.find({
        "blocked_user_id": current_user["sub"]
    }).to_list(100)

    blocked_ids = [str(x["user_id"]) for x in blocked]

    # inclui searchable=True OU sem o campo (legados); só searchable=False fica de fora.
    filters = {"searchable": {"$ne": False}}

    if term:
        esc = re.escape(term)
        # name/display_name: início de palavra (começo do campo ou após espaço)
        name_regex = {"$regex": rf"(^|\s){esc}", "$options": "i"}
        # email: só o início do endereço (parte local) — sem ruído de domínio
        email_regex = {"$regex": rf"^{esc}", "$options": "i"}
        filters["$or"] = [
            {"name": name_regex},
            {"display_name": name_regex},
            {"email": email_regex},
        ]
    # BUG-12: termo vazio → retorna todos (limitado a 50).
    # BUG-9: NÃO exclui o próprio usuário (permite mandar mensagem para si mesmo).

    users = await db.users.find(filters, {"password": 0}).to_list(50)

    parsed = []

    for user in users:

        if str(user["_id"]) in blocked_ids:
            continue

        user["_id"] = str(user["_id"])
        user["online"] = manager.is_online(user["_id"])

        parsed.append(user)

    return parsed


async def block_user(current_user, data):
    db = get_database()

    if current_user["sub"] == data.user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot block yourself"
        )

    exists = await db.blocked_users.find_one({
        "user_id": current_user["sub"],
        "blocked_user_id": data.user_id
    })

    if exists:
        return {"message": "Already blocked"}

    await db.blocked_users.insert_one({
        "user_id": current_user["sub"],
        "blocked_user_id": data.user_id
    })

    return {"message": "User blocked"}


async def unblock_user(current_user, user_id):
    db = get_database()

    await db.blocked_users.delete_one({
        "user_id": current_user["sub"],
        "blocked_user_id": user_id
    })

    return {"message": "User unblocked"}


async def list_blocked_users(current_user):
    db = get_database()

    blocked = await db.blocked_users.find({
        "user_id": current_user["sub"]
    }).to_list(100)

    ids = [
        x["blocked_user_id"]
        for x in blocked
    ]

    users = await db.users.find({
        "_id": {
            "$in": ids
        }
    }).to_list(100)

    result = []

    for user in users:
        result.append({
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        })

    return result


async def get_user_by_id(user_id: str):
    db = get_database()

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await db.users.find_one({"_id": oid}, {"password": 0})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["_id"] = str(user["_id"])
    # verdade = conexões ativas em memória (flag do banco pode ficar presa em True)
    user["online"] = manager.is_online(user["_id"])
    return user


async def get_user_status(user_id):
    db = get_database()

    user = await db.users.find_one(
        {"_id": user_id},
        {"online": 1, "last_seen": 1}
    )

    return user