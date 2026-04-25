from datetime import datetime

def build_user(data: dict):
    return {
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "verified": False,
        "created_at": datetime.utcnow()
    }