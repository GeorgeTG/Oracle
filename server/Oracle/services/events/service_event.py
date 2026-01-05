# Oracle/services/events.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class ServiceEventType(str, Enum):
    """Event type enum that can be used as ServiceEventType.VALUE and converts to lowercase string."""
    NONE = "none" 
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    REQUEST_INVENTORY = "request_inventory"
    REQUEST_MAP = "request_map"
    INVENTORY_SNAPSHOT = "inventory_snapshot"
    INVENTORY_UPDATE = "inventory_update"
    MAP_SNAPSHOT = "map_snapshot"
    ITEM_LOOT = "item_loot"
    MAP_STARTED = "map_started"
    MAP_FINISHED = "map_finished"
    MAP_STATS = "map_stats"
    MARKET_ACTION = "market_action"
    MARKET_TRANSACTION = "market_transaction"
    STATS_UPDATE = "stats_update"
    STATS_CONTROL = "stats_control"
    SESSION_CONTROL = "session_control"
    SESSION_STARTED = "session_started"
    SESSION_FINISHED = "session_finished"
    SESSION_RESTORE = "session_restore"
    REQUEST_SESSION = "request_session"
    SESSION_SNAPSHOT = "session_snapshot"
    PLAYER_CHANGED = "player_changed"
    MAP_RECORD = "map_record"
    WEBSOCKET_CONNECTED = "websocket_connected"
    WEBSOCKET_DISCONNECTED = "websocket_disconnected"
    NOTIFICATION = "notification"
    ITEM_DATA_CHANGED = "item_data_changed"
    LEVEL_PROGRESS = "level_progress"
    
    def __str__(self) -> str:
        return self.value


@dataclass
class ServiceEvent:
    """Base class for all service events."""
    timestamp: datetime
    type: ServiceEventType

    def to_dict(self) -> dict:
        return {
            k: str(v) if isinstance(v, ServiceEventType) else v
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({fields})"
