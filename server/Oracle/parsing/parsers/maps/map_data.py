# Oracle/parsing/parsers/maps/map_data.py

from dataclasses import dataclass
from typing import Optional

from Oracle.parsing.parsers.maps.difficulty import Difficulty


@dataclass
class MapData:
    """Map information data class."""
    map_id: str
    name: str
    asset: str
    area: str
    difficulty: Optional[Difficulty] = None
    
    def __repr__(self) -> str:
        diff_str = f" [{self.difficulty}]" if self.difficulty else ""
        return f"<MapData {self.map_id}: {self.name} ({self.area}){diff_str}>"
