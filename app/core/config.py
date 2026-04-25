from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str

    MONGO_URL: str
    DATABASE_NAME: str

    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRE_MINUTES: int

    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()