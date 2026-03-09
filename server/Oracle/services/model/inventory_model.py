# Oracle/services/model/inventory_model.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple


@dataclass(kw_only=True)
class InventoryItem:
    """Represents a single item in an inventory slot."""
    item_id: int
    quantity: int
    name: Optional[str] = None
    category: Optional[str] = None


class Inventory:
    """Represents current ingame bag state."""

    def __init__(self):
        # key: (page, slot)
        self.slots: Dict[Tuple[int, int], InventoryItem] = {}

    def __len__(self) -> int:
        return len(self.slots)

    def change_item(self, page: int, slot: int,
                    item_id: int, quantity: int,
                    name: Optional[str], category: Optional[str]) -> int:
        """
        Update a specific slot with new item data.
        
        Returns:
            int: The delta in total quantity for this item_id across all slots.
                 Positive = gained, Negative = lost.
        """
        key = (page, slot)
        
        # Calculate total quantity for this item_id BEFORE the change
        previous_total = sum(
            item.quantity for item in self.slots.values()
            if item.item_id == item_id
        )
        
        # Update the slot
        if quantity <= 0:
            self.slots.pop(key, None)
        else:
            self.slots[key] = InventoryItem(
                item_id=item_id,
                quantity=quantity,
                name=name,
                category=category
            )
        
        # Calculate total quantity for this item_id AFTER the change
        new_total = sum(
            item.quantity for item in self.slots.values()
            if item.item_id == item_id
        )
        
        # Return the delta
        return new_total - previous_total

    def copy(self) -> "Inventory":
        """Deep copy for snapshot"""
        new_inv = Inventory()
        new_inv.slots = {
            (p, s): InventoryItem(
                item_id=i.item_id,
                quantity=i.quantity,
                name=i.name,
                category=i.category,
            )
            for (p, s), i in self.slots.items()
        }
        return new_inv

    def to_dict(self) -> dict:
        """Serialize inventory to dict for WebSocket transmission.

        Format: {page: [{slot, item_id, quantity, name, category}, ...]}
        Keys are string page numbers to be JSON-safe.
        """
        pages: dict = {}
        for (page, slot), item in self.slots.items():
            page_key = str(page)
            if page_key not in pages:
                pages[page_key] = []
            pages[page_key].append({
                "slot": slot,
                "item_id": item.item_id,
                "quantity": item.quantity,
                "name": item.name,
                "category": item.category,
            })
        return {"slots": pages}

    def __repr__(self) -> str:
        """Pretty representation of inventory with emojis per page."""
        if not self.slots:
            return "🎒 <Inventory: Empty>"
        
        # Group items by page
        pages: Dict[int, list] = {}
        for (page, slot), item in self.slots.items():
            pages.setdefault(page, []).append((slot, item))
        
        # Build representation
        lines = [f"🎒 <Inventory: {len(self.slots)} items across {len(pages)} page(s)>"]
        
        page_emojis = {
            1: "📦 1",  # 1 Stash
            2: "📦 2",  # 2
            3: "📦 3",  # 3
            4: "📦 4",  # 4
            5: "📦 5",  # 5
            100: "🗡️",  # Gear
            101: "🧙‍♂️",  # Skill
            102: "🎁",  # Commodity
            103: "🔧",  # Others
        }

        page_names = {
            1: "Stash",
            2: "Stash 2",
            3: "Stash 3",
            4: "Stash 4",
            5: "Stash 5",
            100: "Gear",
            101: "Skills",
            102: "Commodities",
            103: "Other",
        }
        
        for page in sorted(pages.keys()):
            emoji = page_emojis.get(page, "📄")
            items = sorted(pages[page], key=lambda x: x[0])  # Sort by slot
            item_count = len(items)
            total_qty = sum(item.quantity for _, item in items)
            lines.append(f"  {emoji} {page_names.get(page, f'Page {page}')}: {item_count} slots, {total_qty} total items")
        
        return "\n".join(lines)


@dataclass
class InventorySnapshot:
    """Snapshot of inventory state at a specific time."""
    timestamp: datetime
    data: Inventory

    @classmethod
    def from_inventory(cls, inv: Inventory) -> "InventorySnapshot":
        """Create snapshot from Inventory instance."""
        return cls(timestamp=datetime.now(), data=inv.copy())

    def compare_with(self, other: "InventorySnapshot") -> Dict[int, int]:
        """
        Returns changes: item_id → delta
        + increase | - decrease | 0 (omitted)
        """
        diff: Dict[int, int] = {}
        
        # Build item_id -> total_quantity maps for both inventories
        def get_item_totals(inv: Inventory) -> Dict[int, int]:
            totals: Dict[int, int] = {}
            for item in inv.slots.values():
                totals[item.item_id] = totals.get(item.item_id, 0) + item.quantity
            return totals
        
        old_totals = get_item_totals(other.data)
        new_totals = get_item_totals(self.data)
        
        all_ids = set(old_totals.keys()) | set(new_totals.keys())

        for item_id in all_ids:
            old_qty = old_totals.get(item_id, 0)
            new_qty = new_totals.get(item_id, 0)
            delta = new_qty - old_qty
            if delta != 0:
                diff[item_id] = delta

        return diff
