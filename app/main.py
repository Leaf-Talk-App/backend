import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.chats.router import router as chats_router
from app.modules.messages.router import router as messages_router
from app.modules.ai.router import router as ai_router
from app.modules.upload.router import router as upload_router
from app.modules.groups.router import router as groups_router
from app.modules.websocket.router import router as websocket_router

app = FastAPI(title=settings.APP_NAME)

# ── CORS ─────────────────────────────────────────────────────────────────────
# allow_origins=["*"] + allow_credentials=True é rejeitado pelos browsers.
# Usamos lista explícita via settings.allowed_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chats_router)
app.include_router(messages_router)
app.include_router(ai_router)
app.include_router(upload_router)
app.include_router(groups_router)
app.include_router(websocket_router)   # /ws/{user_id} — typing + new_message

# ── Static (uploads) ──────────────────────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Utilitários ───────────────────────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    path = "static/favicon.ico"
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=204, content=None)


@app.get("/")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "cors_origins": settings.allowed_origins,
    }


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()
