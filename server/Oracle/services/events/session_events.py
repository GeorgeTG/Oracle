from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


class SessionControlAction(str, Enum):
    """Actions for controlling session tracking."""
    START = "start"
    CLOSE = "close"
    NEXT = "next"  # Close current session and start new one atomically
    
    def __str__(self) -> str:
        return self.value


@dataclass(kw_only=True)
class SessionControlEvent(ServiceEvent):
    """Event to control session tracking."""
    action: SessionControlAction
    player_name: str = None
    type: ServiceEventType = ServiceEventType.SESSION_CONTROL
    
    def __repr__(self) -> str:
        return f"<SessionControlEvent action={self.action} player={self.player_name} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class PlayerChangedEvent(ServiceEvent):
    """Event fired when the current player changes."""
    old_player: Optional[str]  # None for first player on init
    new_player: str
    type: ServiceEventType = ServiceEventType.PLAYER_CHANGED
    
    def __repr__(self) -> str:
        return f"<PlayerChangedEvent old={self.old_player} new={self.new_player} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class SessionStartedEvent(ServiceEvent):
    """Event fired when a farming session is started."""
    session_id: int
    player_name: str
    started_at: datetime
    description: str = None
    type: ServiceEventType = ServiceEventType.SESSION_STARTED

    def __repr__(self) -> str:
        return f"<SessionStartedEvent session_id={self.session_id} player={self.player_name} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class SessionFinishedEvent(ServiceEvent):
    """Event fired when a farming session is finished."""
    session_id: int
    player_name: str
    started_at: datetime
    ended_at: datetime
    total_maps: int
    total_currency_delta: float
    currency_per_hour: float
    currency_per_map: float
    description: str = None
    type: ServiceEventType = ServiceEventType.SESSION_FINISHED

    def __repr__(self) -> str:
        return f"<SessionFinishedEvent session_id={self.session_id} player={self.player_name} maps={self.total_maps} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class SessionSnapshotEvent(ServiceEvent):
    """Event fired in response to REQUEST_SESSION with current session data."""
    session_id: int = None
    player_name: str = None
    started_at: datetime = None
    is_active: bool = False
    type: ServiceEventType = ServiceEventType.SESSION_SNAPSHOT

    def __repr__(self) -> str:
        return f"<SessionSnapshotEvent session_id={self.session_id} player={self.player_name} active={self.is_active} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class SessionRestoreEvent(ServiceEvent):
    """Event fired when restoring session stats from database."""
    session_id: int
    player_name: str
    started_at: datetime
    total_maps: int
    total_time: float
    currency_total: float
    currency_per_hour: float
    currency_per_map: float
    exp_total: float
    exp_per_hour: float
    type: ServiceEventType = ServiceEventType.SESSION_RESTORE

    def __repr__(self) -> str:
        return f"<SessionRestoreEvent session_id={self.session_id} player={self.player_name} maps={self.total_maps} @ {self.timestamp.isoformat()}>"
