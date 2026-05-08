from app.core.database import get_database
from bson import ObjectId
from fastapi import HTTPException

async def get_me(user_data):
    db = get_database()

    user = await db.users.find_one(
        {"email": user_data["email"]},
        {"password": 0}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user["_id"] = str(user["_id"])

    return user


async def update_profile(user_data, data):
    db = get_database()

    await db.users.update_one(
        {"email": user_data["email"]},
        {"$set": data.model_dump(exclude_none=True)}
    )

    return {"message": "Profile updated"}


async def search_users(current_user, query):
    db = get_database()

    blocked = await db.blocked_users.find({
        "blocked_user_id": current_user["sub"]
    }).to_list(100)

    blocked_ids = []

    for x in blocked:
        blocked_ids.append(str(x["user_id"]))

    users = await db.users.find(
        {
            "searchable": True,
            "name": {
                "$regex": query,
                "$options": "i"
            }
        },
        {
            "password": 0
        }
    ).to_list(20)

    parsed = []

    for user in users:

        if str(user["_id"]) in blocked_ids:
            continue

        user["_id"] = str(user["_id"])

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


async def get_user_status(user_id):
    db = get_database()

    user = await db.users.find_one(
        {"_id": user_id},
        {"online": 1, "last_seen": 1}
    )

    return user