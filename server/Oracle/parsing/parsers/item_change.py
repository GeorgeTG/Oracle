from __future__ import annotations

import asyncio
import re
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.item_change import ItemChangeEvent
from Oracle.parsing.utils.item_db import item_lookup
from datetime import datetime

# Example logs:
# [2025.11.26-20.02.54:023][713]GameLog: Display: [Game] ItemChange@ Update Id=5028_50acee19-c8e1-11f0-8ac6-000000000015 BagNum=796 in PageId=102 SlotId=21
# [2025.11.27-01.03.06:492][750]GameLog: Display: [Game] ItemChange@ Add Id=261005_27c4f38a-ac22-11f0-b152-000000000188 BagNum=1 in PageId=100 SlotId=9
# [2025.11.27-01.03.01:952][ 97]GameLog: Display: [Game] ItemChange@ Delete Id=261005_3dc0c281-ba2e-11f0-b761-000000000174 in PageId=100 SlotId=9
ITEM_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\s*\d+\]GameLog:\s*Display:\s*\[Game\]\s*ItemChange@\s+(Add|Update|Delete)\s+Id=(\d+)_\S+(?:\s+BagNum=(\d+))?\s+in\s+PageId=(\d+)\s+SlotId=(\d+)"
)

class ItemChangeParser(ParserBase):
    __PARSER__ = {
        "name": "ItemChangeParser",
        "version": "0.0.1",
        "description": "Parses item quantity and state changes"
    }
    """
    """

    def __init__(self) -> None:
        super().__init__()

    async def feed_line(self, line: str) -> None:
        m = ITEM_RE.search(line)
        
        if not m:
            return None

        timestamp_str, action, item_id_str, amount_str, page_str, slot_str = m.groups()
        timestamp = datetime.strptime(timestamp_str, "%Y.%m.%d-%H.%M.%S")

        item_id = int(item_id_str)
        page = int(page_str)
        slot = int(slot_str)
        
        # BagNum is optional (missing for Delete actions)
        amount = int(amount_str) if amount_str else 0

        # Find extra metadata from item_lookup
        item_info = item_lookup(item_id)
        name = item_info.get("name") if item_info else None
        category = item_info.get("type") if item_info else None

        event = ItemChangeEvent(
            item_id=item_id,
            action=action,
            amount=amount,
            page=page,
            slot=slot,
            name=name,
            category=category,
            timestamp=timestamp,
        )

        await self._emit(event)
