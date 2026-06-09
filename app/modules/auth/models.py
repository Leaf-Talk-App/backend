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
        "phone": None,
        "phone_normalized": None,
        "phone_verified": False,
        "searchable": True,
        "show_read_receipts": True,
        "created_at": datetime.utcnow()
    }