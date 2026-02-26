"""Multi-line parser for market price response (XchgSearchPrice RecvMessage)."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional, List

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.market_price_response import MarketPriceResponseEvent


TIMESTAMP_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})]"
)

# RecvMessage STT----XchgSearchPrice----SynId = 237797
RESPONSE_START_RE = re.compile(
    r"RecvMessage STT----XchgSearchPrice----SynId\s*=\s*(\d+)"
)

# +unitPrices+1 [10.0]  (first line)
UNIT_PRICE_START_RE = re.compile(
    r"\+unitPrices\+\d+\s*\[([\d.]+)\]"
)

# |          +2 [10.0]  (continuation lines: +N [price] without letters before [)
PRICE_CONTINUATION_RE = re.compile(
    r"\+(\d+)\s+\[([\d.]+)\]"
)

# ----Socket RecvMessage End----
MESSAGE_END_RE = re.compile(
    r"----Socket RecvMessage End----"
)

# Func_dealSearch_searchSuccess
SEARCH_SUCCESS_RE = re.compile(
    r"Func_dealSearch_searchSuccess"
)


class MarketPriceResponseParser(ParserBase):
    __PARSER__ = {
        "name": "MarketPriceResponseParser",
        "version": "0.0.2",
        "description": "Parses market price search responses from auction house"
    }

    def __init__(self):
        super().__init__()
        self._collecting: bool = False
        self._collecting_prices: bool = False
        self._request_id: int = 0
        self._prices: List[float] = []
        self._block_timestamp: Optional[datetime] = None

    def _reset(self):
        self._collecting = False
        self._collecting_prices = False
        self._request_id = 0
        self._prices = []
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

        # Start: RecvMessage XchgSearchPrice with SynId
        m_start = RESPONSE_START_RE.search(line)
        if m_start:
            self._collecting = True
            self._request_id = int(m_start.group(1))
            self._prices = []
            self._block_timestamp = ts
            return

        if not self._collecting:
            return

        # First unitPrices line starts price collection
        m_price = UNIT_PRICE_START_RE.search(line)
        if m_price:
            self._collecting_prices = True
            self._prices.append(float(m_price.group(1)))
            return

        # Continuation price lines (+2 [10.0], +3 [10.0], ...)
        if self._collecting_prices:
            m_cont = PRICE_CONTINUATION_RE.search(line)
            if m_cont:
                self._prices.append(float(m_cont.group(2)))
                return
            else:
                # Non-price line ends price collection section
                self._collecting_prices = False

        # End of message block
        if MESSAGE_END_RE.search(line):
            return

        # Search success confirmation → emit
        if SEARCH_SUCCESS_RE.search(line):
            if self._request_id and self._block_timestamp:
                event = MarketPriceResponseEvent(
                    timestamp=self._block_timestamp,
                    request_id=self._request_id,
                    prices=self._prices.copy(),
                    success=True,
                )
                await self._emit(event)
            self._reset()
            return
