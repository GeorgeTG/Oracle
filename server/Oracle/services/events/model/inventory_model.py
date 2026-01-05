# Oracle/services/events/model/inventory_model.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class InventoryItem:
    """Represents a single item in an inventory slot."""
    item_id: int
    quantity: int
    name: Optional[str] = None
    category: Optional[str] = None


@dataclass
class InventorySnapshot:
    """Snapshot of inventory state at a specific time."""
    timestamp: datetime
    data: Dict[int, int]  # item_id -> total quantity

    @classmethod
    def from_inventory(cls, inv) -> "InventorySnapshot":
        """Create snapshot from Inventory instance."""
        return cls(timestamp=datetime.utcnow(), data=inv.flatten())

    def compare_with(self, other: "InventorySnapshot") -> Dict[int, int]:
        """
        Returns changes: item_id → delta
        + increase | - decrease | 0 (omitted)
        """
        diff: Dict[int, int] = {}
        all_ids = set(self.data.keys()) | set(other.data.keys())

        for item_id in all_ids:
            old_qty = self.data.get(item_id, 0)
            new_qty = other.data.get(item_id, 0)
            delta = new_qty - old_qty
            if delta != 0:
                diff[item_id] = delta

        return diff
