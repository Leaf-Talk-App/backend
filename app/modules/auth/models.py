from datetime import datetime

def user_entity(user: dict):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "verified": user.get("verified", False),
        "created_at": user["created_at"]
    }

def build_user(data: dict):
    return {
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "verified": False,
        "created_at": datetime.utcnow()
    }