from dataclasses import dataclass, field
from typing import Optional, Dict, List

from Oracle.parsing.parsers.maps import MapData
from Oracle.services.events.service_event import ServiceEvent, ServiceEventType
from Oracle.services.model import InventoryItem


@dataclass(kw_only=True)
class MapStartedEvent(ServiceEvent):
    """Event emitted when a map is started."""
    level_id: int
    level_uid: int
    level_type: int
    map: Optional[MapData] = None
    consumed_items: List[InventoryItem] = field(default_factory=list)
    type: ServiceEventType = ServiceEventType.MAP_STARTED
    
    def __repr__(self) -> str:
        map_info = f"{self.map.name} [{self.map.difficulty}]" if self.map else f"ID:{self.level_id}"
        return f"<MapStartedEvent {map_info} uid={self.level_uid} type={self.level_type} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class MapFinishedEvent(ServiceEvent):
    """Event emitted when a map is finished."""
    duration: float  # Duration in seconds
    inventory_changes: Dict[int, int]  # Dict[item_id, quantity_change]
    map: Optional[MapData] = None
    affixes: Optional[List[Dict[str, str]]] = None  # List of {affix_id, description}
    type: ServiceEventType = ServiceEventType.MAP_FINISHED
    
    def __repr__(self) -> str:
        total_changes = sum(abs(v) for v in self.inventory_changes.values())
        map_info = f"{self.map.name} [{self.map.difficulty}]" if self.map else "Unknown"
        return f"<MapFinishedEvent {map_info} duration={self.duration:.2f}s changes={total_changes} items @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class MapStatsEvent(ServiceEvent):
    """Event emitted with statistics for a completed map."""
    duration: float  # Duration in seconds
    item_changes: Dict[int, int]  # Dict[item_id, quantity_change]
    currency_gained: float  # Total currency value of items gained
    exp_gained: float = 0.0  # Experience gained during the map
    affixes: Optional[List[Dict[str, str]]] = None  # List of {affix_id, description}
    type: ServiceEventType = ServiceEventType.MAP_STATS
    
    def __repr__(self) -> str:
        return f"<MapStatsEvent duration={self.duration:.2f}s currency={self.currency_gained:.2f} exp={self.exp_gained:.0f} @ {self.timestamp.isoformat()}>"


@dataclass(kw_only=True)
class MapRecordEvent(ServiceEvent):
    """Event fired when a map completion is recorded in the database."""
    map_record: Dict[str, str]  # Serialized MapCompletion model (as returned by GET /maps/{id})
    type: ServiceEventType = ServiceEventType.MAP_RECORD

    def __repr__(self) -> str:
        map_id = self.map_record.get('id', 'unknown')
        player = self.map_record.get('player_name', 'unknown')
        return f"<MapRecordEvent id={map_id} player={player} @ {self.timestamp.isoformat()}>"
