"""Hotkey events for external hotkey tool communication."""
from dataclasses import dataclass

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


@dataclass(kw_only=True)
class HotkeyPressedEvent(ServiceEvent):
    """Event fired when an external hotkey tool sends a key press."""

    key: str
    type: ServiceEventType = ServiceEventType.HOTKEY_PRESSED

    def to_dict(self):
        """Convert to dictionary for WebSocket transmission."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "key": self.key
        }
