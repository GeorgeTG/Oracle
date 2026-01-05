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
