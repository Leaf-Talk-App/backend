from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

def get_database():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    return client[settings.DATABASE_NAME]