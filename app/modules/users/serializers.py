def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "bio": user.get("bio"),
        "avatar": user.get("avatar"),
        "searchable": user.get("searchable", True)
    }