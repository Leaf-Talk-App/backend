import secrets
from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.core.websocket import manager

async def create_group(current_user, data):
    db = get_database()

    members = list(set(
        data.members + [current_user["sub"]]
    ))

    group = {
        "name": data.name,
        "photo": None,
        "members": members,
        "admins": [current_user["sub"]],
        "invite_code": secrets.token_hex(4),
        "created_by": current_user["sub"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.groups.insert_one(group)

    return {
        "group_id": str(result.inserted_id)
    }

async def my_groups(current_user):
    db = get_database()

    groups = await db.groups.find({
        "members": current_user["sub"]
    }).to_list(100)

    for g in groups:
        g["_id"] = str(g["_id"])

    return groups

async def add_member(current_user, data):
    db = get_database()

    group = await db.groups.find_one({
        "_id": ObjectId(data.group_id)
    })

    if current_user["sub"] not in group["admins"]:
        return {"error": "Only admins"}

    await db.groups.update_one(
        {"_id": ObjectId(data.group_id)},
        {
            "$addToSet": {
                "members": data.user_id
            }
        }
    )

    return {"message": "Member added"}

async def send_group_message(current_user, data):
    db = get_database()

    group = await db.groups.find_one({
        "_id": ObjectId(data.group_id)
    })

    if not group:
        return {"error": "Group not found"}

    now = datetime.utcnow()

    message = {
        "group_id": data.group_id,
        "sender_id": current_user["sub"],
        "content": data.content,
        "created_at": now
    }

    result = await db.group_messages.insert_one(message)

    ws_message = {
        "_id": str(result.inserted_id),
        "group_id": data.group_id,
        "sender_id": current_user["sub"],
        "content": data.content,
        "created_at": now.isoformat(),
        "type": "group_message"
    }

    for member_id in group["members"]:
        if member_id != current_user["sub"]:
            await manager.send_personal_message(
                member_id,
                ws_message
            )

    return {"message": "sent"}

async def remove_member(current_user, data):
    db = get_database()

    group = await db.groups.find_one({
        "_id": ObjectId(data.group_id)
    })

    if current_user["sub"] not in group["admins"]:
        return {"error": "Only admins"}

    await db.groups.update_one(
        {"_id": ObjectId(data.group_id)},
        {
            "$pull": {
                "members": data.user_id
            }
        }
    )

    return {"message": "Removed"}

async def leave_group(current_user, group_id):
    db = get_database()

    await db.groups.update_one(
        {"_id": ObjectId(group_id)},
        {
            "$pull": {
                "members": current_user["sub"],
                "admins": current_user["sub"]
            }
        }
    )

    return {"message": "Left group"}

async def join_by_code(current_user, code):
    db = get_database()

    await db.groups.update_one(
        {"invite_code": code},
        {
            "$addToSet": {
                "members": current_user["sub"]
            }
        }
    )

    return {"message": "Joined"}