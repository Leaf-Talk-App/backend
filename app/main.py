import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.ratelimit import limiter
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

# ── Rate limiting (slowapi) ───────────────────────────────────────────────────
# Protege login/registro/recuperação/envio de mensagem de brute-force e abuso.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Headers de segurança ──────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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


# Endpoint leve para keep-alive (UptimeRobot etc.) — evita o cold start do
# Render free. Pingue https://leaftalk-app.onrender.com/health a cada 5 min.
@app.get("/health", include_in_schema=False)
@app.head("/health", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_to_mongo()
    # Inicia o agendador (entrega de mensagens agendadas do Humberto). Sem isto
    # as mensagens confirmadas para agendar nunca eram entregues.
    from app.modules.scheduler.service import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()
