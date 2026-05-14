from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)

class Settings(BaseSettings):

    APP_NAME: str

    MONGO_URL: str
    DATABASE_NAME: str

    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRE_MINUTES: int

    GEMINI_API_KEY: str

    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    FRONTEND_URL: str
    EMAIL_FROM: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
