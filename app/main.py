from fastapi import FastAPI
from app.core.config import settings
from app.modules.auth.router import router as auth_router

app = FastAPI(title=settings.APP_NAME)

app.include_router(auth_router)

@app.get("/")
def health():
    return {"status": "ok"}