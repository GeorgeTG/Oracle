from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class BagModifyEvent(ParserEvent):
    page: int
    slot: int
    item_id: int
    quantity: int
    name: Optional[str] = None
    category: Optional[str] = None
    type: ParserEventType = ParserEventType.BAG_MODIFY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "page": self.page,
            "slot": self.slot,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "name": self.name,
            "category": self.category,
            "type": self.type,
        }

    def __repr__(self) -> str:
        parts = [
            f"timestamp={self.timestamp.isoformat()}",
            f"page={self.page}",
            f"slot={self.slot}",
            f"item_id={self.item_id}",
            f"quantity={self.quantity}",
        ]
        if self.name:
            parts.append(f"name='{self.name}'")
        if self.category:
            parts.append(f"category='{self.category}'")
        return f"<BagModifyEvent {', '.join(parts)}>"
