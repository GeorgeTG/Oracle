from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType
from Oracle.parsing.parsers.maps import MapData


@dataclass(kw_only=True)
class EnterLevelEvent(ParserEvent):
    level_id: int
    level_uid: int
    level_type: int
    map: Optional[MapData] = None
    type: ParserEventType = ParserEventType.ENTER_LEVEL
    
    def __repr__(self) -> str:
        map_info = f"{self.map.name} [{self.map.difficulty}]" if self.map else f"ID:{self.level_id}"
        return f"<EnterLevelEvent {map_info} uid={self.level_uid} type={self.level_type} @ {self.timestamp.isoformat() if self.timestamp else 'N/A'}>"
