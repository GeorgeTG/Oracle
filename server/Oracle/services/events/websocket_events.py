from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


class WebSocketStatus(str, Enum):
    """WebSocket connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    
    def __str__(self) -> str:
        return self.value


@dataclass(kw_only=True)
class WebSocketEvent(ServiceEvent):
    """Event for WebSocket connection status changes."""
    status: WebSocketStatus
    websocket: Any  # WebSocket instance
    client_info: str = ""
    type: ServiceEventType = ServiceEventType.WEBSOCKET_CONNECTED
    
    def __post_init__(self):
        """Set the correct event type based on status."""
        if self.status == WebSocketStatus.CONNECTED:
            self.type = ServiceEventType.WEBSOCKET_CONNECTED
        elif self.status == WebSocketStatus.DISCONNECTED:
            self.type = ServiceEventType.WEBSOCKET_DISCONNECTED
    
    def __repr__(self) -> str:
        return f"<WebSocketEvent status={self.status} client={self.client_info} @ {self.timestamp.isoformat()}>"
