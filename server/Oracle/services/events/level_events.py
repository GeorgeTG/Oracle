from dataclasses import dataclass

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


@dataclass(kw_only=True)
class LevelProgressEvent(ServiceEvent):
    """Event containing character level progress information."""
    level: int  # Current character level
    current: int  # Current experience points in this level
    remaining: int  # Experience points remaining to next level
    level_total: int  # Total experience required for current level
    percentage: float  # Progress percentage (0-100) in current level
    type: ServiceEventType = ServiceEventType.LEVEL_PROGRESS
    
    def __repr__(self) -> str:
        return (
            f"<LevelProgressEvent level={self.level} "
            f"{self.current}/{self.level_total} ({self.percentage:.1f}%) "
            f"remaining={self.remaining}>"
        )
