from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class GameMessageEvent(ParserEvent):
    """Event for in-game system messages."""
    timestamp: datetime
    message: str  # The game message text
    type: ParserEventType = ParserEventType.GAME_MESSAGE
