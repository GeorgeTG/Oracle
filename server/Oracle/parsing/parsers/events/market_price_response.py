"""Market price response parser event."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from Oracle.parsing.parsers.events.parser_event import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType


@dataclass(kw_only=True)
class MarketPriceResponseEvent(ParserEvent):
    """Emitted when a market price response arrives (XchgSearchPrice response)."""
    request_id: int = 0
    prices: List[float] = field(default_factory=list)
    success: bool = False
    type: ParserEventType = ParserEventType.MARKET_PRICE_RESPONSE
