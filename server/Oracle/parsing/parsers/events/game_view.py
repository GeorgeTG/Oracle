from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class GameViewEvent(ParserEvent):
    view: str
    type: ParserEventType = ParserEventType.GAME_VIEW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view": self.view,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
        }

    def __repr__(self) -> str:
        return f"<GameViewEvent view='{self.view}' timestamp={self.timestamp.isoformat()}>"
