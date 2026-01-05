import re
import asyncio
from datetime import datetime
from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.bag_modify import BagModifyEvent
from Oracle.parsing.utils.item_db import item_lookup

BAG_MODIFY_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+]\[\d+]"
    r"GameLog: Display: \[Game] BagMgr@\:Modfy BagItem "
    r"PageId = (\d+) SlotId = (\d+) ConfigBaseId = (\d+) Num = (\d+)"
)


class BagModifyParser(ParserBase):
    __PARSER__ = {
        "name": "BagModifyParser",
        "version": "0.0.1",
        "description": "Parses bag/inventory modification events"
    }
    
    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = BAG_MODIFY_RE.search(line)
        if not m:
            return

        ts_str, page, slot, item_id, qty = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")
        item_id = int(item_id)
        qty = int(qty)

        item_info = item_lookup(item_id)
        name = item_info.get("name") if item_info else None
        category = item_info.get("type") if item_info else None

        event = BagModifyEvent(
            timestamp=timestamp,
            page=int(page),
            slot=int(slot),
            item_id=item_id,
            quantity=qty,
            name=name,
            category=category
        )

        await self._emit(event)
