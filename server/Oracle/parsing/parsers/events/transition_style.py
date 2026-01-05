from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class TransitionStyleEvent(ParserEvent):
    """Event for screen transition style changes."""
    timestamp: datetime
    transition_style: str  # Transition style name (e.g., S12TransitionBlackItem)
    type: ParserEventType = ParserEventType.TRANSITION_STYLE
