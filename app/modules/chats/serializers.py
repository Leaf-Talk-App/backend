def serialize_chat(chat):
    return {
        "id": str(chat["_id"]),
        "members": chat.get("members", []),
        "is_group": chat.get("is_group", False),
        "name": chat.get("name"),
        "created_at": chat.get("created_at"),
        "last_message": chat.get("last_message"),
        "last_message_at": chat.get("last_message_at")
    }