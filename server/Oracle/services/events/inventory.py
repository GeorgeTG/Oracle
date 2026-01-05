from dataclasses import dataclass
from typing import Optional, Dict

from Oracle.services.events.service_event import ServiceEvent, ServiceEventType
from Oracle.services.model import InventorySnapshot
from Oracle.services.model.inventory_model import Inventory


@dataclass(kw_only=True)
class RequestInventoryEvent(ServiceEvent):
    """
    Event requesting the current inventory snapshot.
    Emitted when a client or service needs the current inventory state.
    """
    type: ServiceEventType = ServiceEventType.REQUEST_INVENTORY
    requester: Optional[str] = None  # Optional identifier of who requested

    def to_dict(self) -> Dict[str, str | None]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": str(self.type),
            "requester": self.requester,
        }


@dataclass(kw_only=True)
class InventorySnapshotEvent(ServiceEvent):
    """
    Event containing a snapshot of the current inventory.
    Emitted in response to RequestInventoryEvent or periodically.
    """
    type: ServiceEventType = ServiceEventType.INVENTORY_SNAPSHOT
    snapshot: InventorySnapshot

    def to_dict(self) -> Dict[str, str | Dict[str, str | Inventory]]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": str(self.type),
            "snapshot": {
                "timestamp": self.snapshot.timestamp.isoformat(),
                "data": self.snapshot.data,
            },
        }

    def __repr__(self) -> str:
        return f"<InventorySnapshotEvent {self.snapshot} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class InventoryUpdateEvent(ServiceEvent):
    """
    Event to update entire inventory state.
    Contains an Inventory object with full inventory data.
    """
    inventory: Inventory
    type: ServiceEventType = ServiceEventType.INVENTORY_UPDATE
    
    def to_dict(self) -> Dict[str, str | Dict[str, int]]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": str(self.type),
            "inventory": {
                "slots": len(self.inventory.slots),
            },
        }
    
    def __repr__(self) -> str:
        return f"<InventoryUpdateEvent {self.inventory} @ {self.timestamp.isoformat()}>"
