from app.core.database import get_database

async def get_me(user_data):
    db = get_database()

    user = await db.users.find_one(
        {"email": user_data["email"]},
        {"password": 0}
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

async def search_users(query):
    db = get_database()

    users = await db.users.find(
        {
            "searchable": True,
            "name": {"$regex": query, "$options": "i"}
        },
        {"password": 0}
    ).to_list(20)

    for user in users:
        user["_id"] = str(user["_id"])

    return users