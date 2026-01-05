"""Notification events for sending alerts/messages to connected clients."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


class NotificationSeverity(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(kw_only=True)
class NotificationEvent(ServiceEvent):
    """Event for broadcasting notifications to UI clients."""
    
    title: str
    content: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    duration: Optional[int] = None  # Duration in ms, None = use default
    type: ServiceEventType = ServiceEventType.NOTIFICATION
    
    def to_dict(self):
        """Convert to dictionary for WebSocket transmission."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "content": self.content,
            "severity": self.severity.value,
            "duration": self.duration
        }
