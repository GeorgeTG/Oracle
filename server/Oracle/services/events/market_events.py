"""Market-related events."""
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType


class MarketAction(str, Enum):
    """Market actions."""
    OPEN = "market_open"
    CLOSE = "market_close"

@dataclass(kw_only=True)
class MarketActionEvent(ServiceEvent):
    """Event published when the market is opened or closed."""
    
    action: MarketAction
    type: ServiceEventType = ServiceEventType.MARKET_ACTION    
    
    def __repr__(self) -> str:
        return f"<MarketActionEvent action={self.action.value} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class MarketTransactionEvent(ServiceEvent):
    """Event published when an item transaction occurs in the market."""
    
    item_id: int
    quantity: int
    action: str  # "bought" or "sold"
    transaction_id: Optional[int] = None
    session_id: Optional[int] = None
    type: ServiceEventType = ServiceEventType.MARKET_TRANSACTION
    
    def __repr__(self) -> str:
        return f"<MarketTransactionEvent item={self.item_id} qty={self.quantity} action={self.action} tx_id={self.transaction_id} @ {self.timestamp.isoformat()}>"
