"""Multi-line parser for market price request (XchgSearchPrice SendMessage)."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.market_price_request import MarketPriceRequestEvent


TIMESTAMP_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})]"
)

# SendMessage STT----XchgSearchPrice----SynId = 237797
REQUEST_START_RE = re.compile(
    r"SendMessage STT----XchgSearchPrice----SynId\s*=\s*(\d+)"
)

# +refer [200030]
REFER_RE = re.compile(
    r"\+refer\s*\[(\d+)\]"
)

# ----Socket SendMessage End----
MESSAGE_END_RE = re.compile(
    r"----Socket SendMessage End----"
)


class MarketPriceRequestParser(ParserBase):
    __PARSER__ = {
        "name": "MarketPriceRequestParser",
        "version": "0.0.1",
        "description": "Parses market price search requests to auction house"
    }

    def __init__(self):
        super().__init__()
        self._collecting: bool = False
        self._request_id: int = 0
        self._item_id: int = 0
        self._block_timestamp: Optional[datetime] = None

    def _reset(self):
        self._collecting = False
        self._request_id = 0
        self._item_id = 0
        self._block_timestamp = None

    async def feed_line(self, line: str) -> None:
        # Parse timestamp
        ts = None
        m_ts = TIMESTAMP_RE.search(line)
        if m_ts:
            date_str, time_str, ms_str = m_ts.groups()
            ts = datetime.strptime(
                f"{date_str} {time_str}.{ms_str}",
                "%Y.%m.%d %H.%M.%S.%f"
            )

        # Start: SendMessage XchgSearchPrice with SynId
        m_start = REQUEST_START_RE.search(line)
        if m_start:
            self._collecting = True
            self._request_id = int(m_start.group(1))
            self._item_id = 0
            self._block_timestamp = ts
            return

        if not self._collecting:
            return

        # Collect refer (real item ID) — keep only the first non-zero refer
        m_refer = REFER_RE.search(line)
        if m_refer:
            refer_val = int(m_refer.group(1))
            if refer_val > 0 and self._item_id == 0:
                self._item_id = refer_val
            return

        # End of message block → emit
        if MESSAGE_END_RE.search(line):
            if self._request_id and self._item_id and self._block_timestamp:
                event = MarketPriceRequestEvent(
                    timestamp=self._block_timestamp,
                    request_id=self._request_id,
                    item_id=self._item_id,
                )
                await self._emit(event)
            self._reset()
            return
