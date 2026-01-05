from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class MapLoadedEvent(ParserEvent):
    timestamp: datetime
    map_path: str
    type: ParserEventType = ParserEventType.MAP_LOADED

    def __repr__(self):
        map_name = self.map_path.split('/')[-1] if self.map_path else "Unknown"
        return f"<MapLoadedEvent {map_name} @ {self.timestamp.isoformat()}>"
