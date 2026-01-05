# Oracle/parsing/parsers/maps/util.py

import json
from pathlib import Path
from typing import Optional, Dict, Any
from copy import deepcopy

from Oracle.tooling.logger import Logger
from Oracle.tooling.paths import get_config_path
from Oracle.parsing.parsers.maps.map_data import MapData
from Oracle.parsing.parsers.maps.difficulty import Difficulty

logger = Logger('maps.util')

# Static cache for map data
_MAP_DB: Optional[Dict[str, MapData]] = None


def _get_difficulty_from_id(map_id: str) -> Optional[Difficulty]:
    """
    Determine difficulty tier from map ID using search algorithm.
    
    For a given map_id that doesn't exist, we search by adding 100 increments
    until we find an existing map, then calculate the difficulty offset.
    
    Example:
    - map_id 5105 doesn't exist
    - Search: 5105 + 100 = 5205 (found at difficulty index 1, T8_2)
    - Offset: 1 (we added 100 once)
    - Result: difficulty_list[1 + 1] = T8_1
    """
    difficulty_list = Difficulty.to_list()
    logger.debug(f"Difficulty list: {[str(d) for d in difficulty_list]}") 
    try:
        base_id = int(map_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid map_id: {map_id}")
    
    # Check if this exact ID exists in our DB
    db = _load_map_db()
    # Search upwards to find the tier
    search_id = base_id
    offset = 0

    while offset < len(difficulty_list):
        search_key = str(search_id)
        if search_key in db and search_id != base_id:
            # Found a reference map
            assert(offset < len(difficulty_list))

            new_difficulty = difficulty_list[offset - 1]
            # Update the db with a new MapData including difficulty_list[-offset]}")
            original_map = deepcopy(db[search_key])
            original_map.map_id = map_id
            original_map.difficulty = new_difficulty
            db[map_id] = original_map
            return new_difficulty
        
        search_id += 100
        offset += 1
    
    # If we didn't find anything, assume T8+ (index 0)
    return difficulty_list[0]
    

def _load_map_db() -> Dict[str, MapData]:
    """Load map database from en_id_map_table.json (cached)."""
    global _MAP_DB
    
    if _MAP_DB is not None:
        return _MAP_DB
    
    path = get_config_path("en_id_map_table.json")
    
    if not path.exists():
        _MAP_DB = {}
        return _MAP_DB
    
    with open(path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Convert dict to MapData objects
    _MAP_DB = {
        map_id: MapData(
            map_id=map_id,
            name=data['name'],
            asset=data['asset'],
            area=data['area'],
            difficulty=data.get('difficulty', Difficulty.T8_PLUS)
        )
        for map_id, data in raw_data.items()
    }
    
    return _MAP_DB


def get_map_by_id(map_id: int | str) -> Optional[MapData]:
    """
    Get map information by map ID.
    
    Args:
        map_id: The map ID (int or string)
    
    Returns:
        MapData object with map information (including difficulty), or None if not found
        
    Example:
        >>> map_info = get_map_by_id(5307)
        >>> print(map_info.name)  # "Grimwind Woods"
        >>> print(map_info.area)  # "Glacial Abyss"
        >>> print(map_info.difficulty)  # Difficulty.T7_0
    """
    db = _load_map_db()
    try:
        return db[str(map_id)]
    except KeyError:
        # Try to determine difficulty and create a new MapData
        logger.debug(f"Map ID {map_id} not found, attempting to determine difficulty.")
        difficulty = _get_difficulty_from_id(str(map_id))
        if difficulty:
            logger.debug(f"Determined difficulty {difficulty} for map ID {map_id}.")
            return db.get(str(map_id))
        return None
