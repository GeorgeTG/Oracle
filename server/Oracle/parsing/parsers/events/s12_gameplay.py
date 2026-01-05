from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class S12GameplayEvent(ParserEvent):
    """Event for S12 gameplay BGM layer changes."""
    timestamp: datetime
    layer: int  # BGM layer number
    type: ParserEventType = ParserEventType.S12_GAMEPLAY
