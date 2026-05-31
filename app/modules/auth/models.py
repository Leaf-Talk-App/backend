from datetime import datetime

def build_user(data: dict):
    return {
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "verified": False,
        "display_name": None,
        "bio": None,
        "avatar": None,
        "searchable": True,
        "created_at": datetime.utcnow()
    }