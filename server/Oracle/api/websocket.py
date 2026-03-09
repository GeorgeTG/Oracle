"""WebSocket API router - handles WebSocket connections."""
import asyncio
import json
import os
import signal
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from Oracle.events import EventBus
from Oracle.services.events.websocket_events import WebSocketEvent, WebSocketStatus
from Oracle.services.events.hotkey_events import HotkeyPressedEvent
from Oracle.services.events.overlay_events import OverlayBoundsUpdateEvent, HoverEnterEvent, HoverLeaveEvent
from Oracle.api.dependencies import get_event_bus, get_service_manager
from Oracle.services.service_manager import ServiceManager
from Oracle.tooling.logger import Logger

logger = Logger("WebSocketRouter")
router = APIRouter(
    tags=["websocket"]
)


@router.websocket(
    "/ws",
    name="WebSocket Connection"
)
async def ws_endpoint(ws: WebSocket, event_bus: EventBus = Depends(get_event_bus), service_manager: ServiceManager = Depends(get_service_manager)):
    """WebSocket endpoint for real-time updates.

    Connect to this endpoint to receive real-time events:
    - Map completions
    - Session updates
    - Inventory changes
    - Game events

    Accepts incoming commands:
    - {"command": "hotkey", "key": "<key_name>"} - Trigger a hotkey event
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
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                command = msg.get("command")

                if msg_type == "overlay_bounds_update":
                    bounds = msg.get("bounds", [])
                    await event_bus.publish(OverlayBoundsUpdateEvent(
                        bounds=bounds, timestamp=datetime.now()
                    ))
                elif command == "hotkey":
                    key = msg.get("key", "")
                    logger.info(f"WS hotkey command received: key={key}")
                    await event_bus.publish(HotkeyPressedEvent(
                        key=key, timestamp=datetime.now()
                    ))
                elif command == "heartbeat" or msg_type == "heartbeat":
                    # Relay heartbeat from external components (e.g. hotkey) to all UI clients
                    ws_service = next((s for s in service_manager.services if s.__class__.__name__ == "WebSocketBroadcastService"), None)
                    if ws_service:
                        await ws_service._broadcast_to_clients(msg)
                elif command == "hover_enter":
                    logger.info("WS hover_enter command received")
                    await event_bus.publish(HoverEnterEvent(timestamp=datetime.now()))
                elif command == "hover_leave":
                    logger.info("WS hover_leave command received")
                    await event_bus.publish(HoverLeaveEvent(timestamp=datetime.now()))
                elif command == "shutdown":
                    logger.info("WS shutdown command received, initiating graceful shutdown...")
                    try:
                        await ws.send_text(json.dumps({"type": "shutdown_acknowledged"}))
                        await ws.close()
                    except Exception:
                        pass
                    asyncio.get_event_loop().call_later(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM))
                    return
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await event_bus.publish(WebSocketEvent(
            timestamp=datetime.now(),
            status=WebSocketStatus.DISCONNECTED,
            websocket=ws,
            client_info=str(ws.client)
        ))
        logger.info("WS disconnected")
