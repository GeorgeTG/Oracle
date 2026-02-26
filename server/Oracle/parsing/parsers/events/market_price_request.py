"""Market price request parser event."""
from __future__ import annotations
from dataclasses import dataclass

from Oracle.parsing.parsers.events.parser_event import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType


@dataclass(kw_only=True)
class MarketPriceRequestEvent(ParserEvent):
    """Emitted when a market price search request is sent (XchgSearchPrice SendMessage)."""
    request_id: int = 0   # SynId - used to match with response
    item_id: int = 0      # refer - the actual item ID
    type: ParserEventType = ParserEventType.MARKET_PRICE_REQUEST
