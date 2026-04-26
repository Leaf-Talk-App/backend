from datetime import datetime
from fastapi import WebSocket
from app.core.database import get_database

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()

        self.active_connections[user_id] = websocket

        db = get_database()

        await db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "online": True
                }
            }
        )

    async def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

        db = get_database()

        await db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "online": False,
                    "last_seen": datetime.utcnow()
                }
            }
        )

    async def send_personal_message(
        self,
        user_id: str,
        message: dict
    ):
        ws = self.active_connections.get(user_id)

        if ws:
            await ws.send_json(message)

    def is_online(self, user_id: str):
        return user_id in self.active_connections

    def get_online_users(self):
        return list(self.active_connections.keys())

manager = ConnectionManager()