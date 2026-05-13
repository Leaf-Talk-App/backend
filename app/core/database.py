from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = None
db = None

async def connect_to_mongo():
    global client, db

    client = AsyncIOMotorClient(
        settings.MONGO_URL,
        serverSelectionTimeoutMS=5000
    )

    db = client[settings.DATABASE_NAME]

async def close_mongo_connection():
    global client

    if client:
        client.close()

def get_database():
    return db