"""WebSocket API router - handles WebSocket connections."""
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from Oracle.services.event_bus import EventBus
from Oracle.services.events.websocket_events import WebSocketEvent, WebSocketStatus
from Oracle.api.dependencies import get_event_bus
from Oracle.tooling.logger import Logger

logger = Logger("WebSocketRouter")
router = APIRouter(
    tags=["websocket"]
)


@router.websocket(
    "/ws",
    name="WebSocket Connection"
)
async def ws_endpoint(ws: WebSocket, event_bus: EventBus = Depends(get_event_bus)):
    """WebSocket endpoint for real-time updates.
    
    Connect to this endpoint to receive real-time events:
    - Map completions
    - Session updates
    - Inventory changes
    - Game events
    """
    await ws.accept()

    await event_bus.publish(WebSocketEvent(
        timestamp=datetime.now(),
        status=WebSocketStatus.CONNECTED,
        websocket=ws,
        client_info=str(ws.client)
    ))
    logger.info(f"WS connected: {ws.client}")

    try:
        while True:
            # keep-alive / or commands in the future
            await ws.receive_text()
    except WebSocketDisconnect:
        await event_bus.publish(WebSocketEvent(
            timestamp=datetime.now(),
            status=WebSocketStatus.DISCONNECTED,
            websocket=ws,
            client_info=str(ws.client)
        ))
        logger.info("WS disconnected")
