"""Item-related service events."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


@dataclass(kw_only=True)
class ItemDataChangedEvent(ServiceEvent):
    """Event published when item data is changed via API."""
    item_id: int
    name: Optional[str] = None
    category: Optional[str] = None
    price: float = 0.0

    def __init__(
        self,
        item_id: int,
        name: Optional[str] = None,
        category: Optional[str] = None,
        price: float = 0.0
    ):
        super().__init__(
            timestamp=datetime.now(),
            type=ServiceEventType.ITEM_DATA_CHANGED
        )
        self.item_id = item_id
        self.name = name
        self.category = category
        self.price = price


@dataclass(kw_only=True)
class ItemObtainedEvent(ServiceEvent):
    """Event published when an item is obtained/lost during gameplay."""
    item_id: int
    item_name: Optional[str] = None
    delta: int = 0  # Positive = gained, Negative = lost
    item_price: float = 0.0
    total_value: float = 0.0  # delta * item_price
    type: ServiceEventType = ServiceEventType.ITEM_OBTAINED

    def __repr__(self) -> str:
        action = "gained" if self.delta > 0 else "lost"
        return f"<ItemObtainedEvent {self.item_name or self.item_id} {action} {abs(self.delta)} (value: {self.total_value:.2f}) @ {self.timestamp.isoformat()}>"
