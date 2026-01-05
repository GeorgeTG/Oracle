from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class PlayerJoinEvent(ParserEvent):
    player_name: str
    mode: int
    type: ParserEventType = ParserEventType.PLAYER_JOIN
    
    def __repr__(self) -> str:
        return f"<PlayerJoinEvent player={self.player_name} mode={self.mode} @ {self.timestamp.isoformat() if self.timestamp else 'N/A'}>"
