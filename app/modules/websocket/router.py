from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from app.core.websocket import manager

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str
):
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

    except WebSocketDisconnect:

        await manager.disconnect(user_id)