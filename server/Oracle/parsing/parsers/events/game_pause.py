from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class GamePauseEvent(ParserEvent):
    """Event for game pause/unpause state changes."""
    timestamp: datetime
    is_paused: bool  # True if game is paused, False if unpaused
    type: ParserEventType = ParserEventType.GAME_PAUSE
