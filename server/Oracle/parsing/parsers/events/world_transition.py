from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class WorldTransitionEvent(ParserEvent):
    """Event for world transition state (SubWorld to MainWorld switch)."""
    timestamp: datetime
    back_flow_step: int  # BackFlow step number (0, 4, etc.)
    is_switching_to_main_world: bool  # Whether transitioning from SubWorld to MainWorld
    type: ParserEventType = ParserEventType.WORLD_TRANSITION
