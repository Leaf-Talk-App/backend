from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Leaf Talk API"

    MONGO_URL: str
    DATABASE_NAME: str = "leaf_talk"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias de sessão ativa

    GEMINI_API_KEY: str = ""

    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    EMAIL_FROM: str = ""

    # Resend (HTTP) — Render free bloqueia SMTP de saída; e-mail vai por HTTPS.
    # Se RESEND_API_KEY existir, é o método primário (SMTP só fallback local).
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "Leaf Talk <onboarding@resend.dev>"

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    # Cloudinary — opcional; se ausente, usa disco local
    # Opção 1: URL completa  cloudinary://KEY:SECRET@CLOUD_NAME
    CLOUDINARY_URL: str = ""
    # Opção 2: variáveis separadas
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Lista extra de origens CORS separada por vírgula
    # Ex: CORS_ORIGINS=https://leaf.app,https://leaftalk.vercel.app
    CORS_ORIGINS: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        origins = {
            self.FRONTEND_URL,
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:4173",
        }
        if self.CORS_ORIGINS:
            for o in self.CORS_ORIGINS.split(","):
                o = o.strip()
                if o:
                    origins.add(o)
        return list(origins)


settings = Settings()
