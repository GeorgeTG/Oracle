from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class ExpUpdateEvent(ParserEvent):
    """Event for experience/level updates."""
    timestamp: datetime
    experience: int  # Raw experience value
    level: int  # Current character level
    type: ParserEventType = ParserEventType.EXP_UPDATE
