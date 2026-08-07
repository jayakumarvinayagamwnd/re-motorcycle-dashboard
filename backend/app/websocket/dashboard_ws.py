from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo:{message}")
    except WebSocketDisconnect:
        return
