from fastapi import FastAPI
from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from fastapi.middleware.cors import CORSMiddleware
from app.modules.chats.router import router as chats_router
from app.modules.messages.router import router as messages_router
from app.core.websocket import manager
from fastapi import WebSocket, WebSocketDisconnect
from app.modules.ai.router import router as ai_router
import asyncio
from app.modules.scheduler.service import run_scheduler
from fastapi.staticfiles import StaticFiles
from app.modules.uploads.router import router as uploads_router
from app.modules.groups.router import router as groups_router
from app.modules.scheduler.service import start_scheduler

app = FastAPI(title=settings.APP_NAME)
app.include_router(auth_router)
app.include_router(users_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chats_router)
app.include_router(messages_router)
app.include_router(ai_router)
app.include_router(uploads_router)
app.include_router(groups_router)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

@app.get("/")
def health():
    return {"status": "ok"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str
):
    await manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        
@app.on_event("startup")
async def startup_event():

    async def scheduler_loop():
        while True:
            await run_scheduler()
            await asyncio.sleep(60)

    asyncio.create_task(scheduler_loop())
    
@app.on_event("startup")
async def startup():
    start_scheduler()