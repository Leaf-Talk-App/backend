from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import Query
from jose import jwt, JWTError
from app.core.config import settings
from app.core.websocket import manager

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(default=None),
):
    # AUTENTICAÇÃO (corrige spoofing): o token JWT (?token=) precisa ser válido e
    # seu `sub` precisa bater com o user_id da URL. Antes qualquer um conectava
    # como qualquer user_id e recebia as mensagens em tempo real da vítima.
    authed_id = None
    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            authed_id = payload.get("sub")
        except JWTError:
            authed_id = None
    if not authed_id or authed_id != user_id:
        await websocket.close(code=4401)
        return

    await manager.connect(
        user_id,
        websocket
    )

    try:
        while True:

            data = await websocket.receive_json()

            event_type = data.get("type")

            # typing realtime
            if event_type == "typing":

                await manager.send_personal_message(
                    data["to"],
                    {
                        "type": "typing",
                        "from": user_id
                    }
                )

            # stop typing
            elif event_type == "stop_typing":

                await manager.send_personal_message(
                    data["to"],
                    {
                        "type": "stop_typing",
                        "from": user_id
                    }
                )

            # heartbeat (ping a cada ~30s) — mantém a conexão viva
            elif event_type == "ping":

                await manager.heartbeat(user_id)

    except WebSocketDisconnect:

        await manager.disconnect(user_id)