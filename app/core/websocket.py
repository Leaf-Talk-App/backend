from datetime import datetime
from fastapi import WebSocket
from bson import ObjectId
from app.core.database import get_database


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

        db = get_database()
        try:
            # _id é ObjectId no Mongo; user_id vem como string do JWT/URL
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"online": True}},
            )
        except Exception:
            pass  # ObjectId inválido ou usuário não encontrado — não travar

        # avisa os demais conectados que este usuário ficou online
        await self.broadcast(
            {"type": "presence", "user_id": user_id, "online": True},
            exclude=user_id,
        )

    async def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

        db = get_database()
        last_seen = datetime.utcnow()
        try:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"online": False, "last_seen": last_seen}},
            )
        except Exception:
            pass

        await self.broadcast({
            "type": "presence",
            "user_id": user_id,
            "online": False,
            "last_seen": last_seen.isoformat(),
        })

    async def heartbeat(self, user_id: str):
        """Ping do cliente (a cada ~30s) — mantém last_seen fresco e online=True."""
        db = get_database()
        try:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"online": True, "last_seen": datetime.utcnow()}},
            )
        except Exception:
            pass

    async def send_personal_message(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                # conexão quebrada silenciosamente — remove
                self.active_connections.pop(user_id, None)

    async def broadcast(self, message: dict, exclude: str | None = None):
        """Envia um evento a todas as conexões ativas (presença, etc.)."""
        for uid, ws in list(self.active_connections.items()):
            if exclude and uid == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                self.active_connections.pop(uid, None)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections

    def get_online_users(self) -> list[str]:
        return list(self.active_connections.keys())


manager = ConnectionManager()
