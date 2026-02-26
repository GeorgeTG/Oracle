"""Overlay events: hover detection, info text."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


@dataclass(kw_only=True)
class OverlayBoundsUpdateEvent(ServiceEvent):
    """Event containing all dialog bounding boxes from the overlay."""
    bounds: List[Dict[str, Any]] = field(default_factory=list)
    type: ServiceEventType = ServiceEventType.OVERLAY_BOUNDS_UPDATE

    def to_dict(self):
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "bounds": self.bounds
        }


@dataclass(kw_only=True)
class HoverEnterEvent(ServiceEvent):
    """Event fired when mouse enters a dialog bounding box."""
    type: ServiceEventType = ServiceEventType.HOVER_ENTER

    def to_dict(self):
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass(kw_only=True)
class HoverLeaveEvent(ServiceEvent):
    """Event fired when mouse leaves all dialog bounding boxes."""
    type: ServiceEventType = ServiceEventType.HOVER_LEAVE

    def to_dict(self):
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass(kw_only=True)
class OverlayInfoTextEvent(ServiceEvent):
    """Info text message displayed on the overlay."""
    text: str = ""
    severity: str = "info"  # info | warn | danger
    duration: Optional[int] = None  # ms, None = default
    type: ServiceEventType = ServiceEventType.OVERLAY_INFO_TEXT

    def to_dict(self):
        d = {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "severity": self.severity,
        }
        if self.duration is not None:
            d["duration"] = self.duration
        return d


@dataclass(kw_only=True)
class ViewChangedEvent(ServiceEvent):
    """Broadcast when the game view changes (e.g. FightCtrl, AuctionHouse)."""
    view: str = ""
    type: ServiceEventType = ServiceEventType.VIEW_CHANGED

    def to_dict(self):
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "view": self.view,
        }
