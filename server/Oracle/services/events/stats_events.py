from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


class StatsControlAction(str, Enum):
    """Actions for controlling stats tracking."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    
    def __str__(self) -> str:
        return self.value


@dataclass(kw_only=True)
class StatsControlEvent(ServiceEvent):
    """Event to control stats tracking."""
    action: StatsControlAction
    type: ServiceEventType = ServiceEventType.STATS_CONTROL
    
    def __repr__(self) -> str:
        return f"<StatsControlEvent action={self.action} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class StatsUpdateEvent(ServiceEvent):
    """Event containing current statistics."""
    total_maps: int
    total_time: float  # Total farming time in seconds
    session_duration: float  # Total session time in seconds
    items_per_map: Dict[int, float]  # Dict[item_id, avg_quantity_per_map] (deprecated)
    items_per_hour: Dict[int, float]  # Dict[item_id, quantity_per_hour]
    exp_per_hour: float = 0.0  # Experience gained per hour in percent
    exp_gained_total: float = 0.0  # Total XP gained
    exp_lost_total: float = 0.0  # Total XP lost
    currency_per_map: float = 0.0  # Average currency per map
    currency_per_hour: float = 0.0  # Currency gained per hour
    currency_total: float = 0.0  # Total net currency (maps + market)
    currency_current_per_hour: float = 0.0  # Current map currency per hour
    currency_current_raw: float = 0.0  # Total currency in current map
    map_timer: float = 0.0  # Current map duration in seconds
    type: ServiceEventType = ServiceEventType.STATS_UPDATE
    
    def __repr__(self) -> str:
        hours = self.total_time / 3600.0
        return (
            f"<StatsUpdateEvent maps={self.total_maps} "
            f"time={hours:.2f}h tracked_items={len(self.items_per_hour)} "
            f"exp_rate={self.exp_per_hour:.1f}%/h "
            f"currency={self.currency_per_hour:.2f}/h "
            f"current_map={self.currency_current_per_hour:.2f}/h "
            f"@ {self.timestamp.isoformat()}>"
        )
