from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class ItemChangeEvent(ParserEvent):
    item_id: int
    page: int
    slot: int
    action: str  # "Add", "Update", or "Delete"
    amount: int = 0  # BagNum (quantity), 0 for Delete actions
    name: Optional[str] = None
    category: Optional[str] = None
    type: ParserEventType = ParserEventType.ITEM_CHANGE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "item_id": self.item_id,
            "amount": self.amount,
            "page": self.page,
            "slot": self.slot,
            "name": self.name,
            "category": self.category,
            "type": self.type,
        }

    def __repr__(self) -> str:
        parts = [
            f"timestamp={self.timestamp.isoformat()}",
            f"action={self.action}",
            f"item_id={self.item_id}",
            f"amount={self.amount}",
            f"page={self.page}",
            f"slot={self.slot}",
        ]
        if self.name:
            parts.append(f"name='{self.name}'")
        if self.category:
            parts.append(f"category='{self.category}'")
        return f"<ItemChangeEvent {', '.join(parts)}>"
