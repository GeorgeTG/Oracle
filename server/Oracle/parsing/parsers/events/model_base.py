from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Event type enum that can be used as EventType.VALUE and converts to lowercase string."""
    NONE = "none" 
    ITEM_CHANGE = "item_change"
    ITEM_PICKUP = "item_pickup"
    GAME_VIEW = "game_view"
    SCENE_TRANSITION_START = "scene_transition_start"
    BAG_MODIFY = "bag_modify"
    PING = "ping"
    LOADING_PROGRESS = "loading_progress"
    ENTER_LEVEL = "enter_level"
    EXIT_LEVEL = "exit_level"
    STAGE_AFFIX = "stage_affix"
    MONSTER_SPAWN = "monster_spawn"
    LEVEL_UP = "level_up"
    BOSS_SPAWN = "boss_spawn"
    LOOT_DROP = "loot_drop"
    GAME_PAUSE = "game_pause"
    
    def __str__(self) -> str:
        return self.value


@dataclass
class ModelBase:
    timestamp: datetime
    type: EventType
    
    def to_dict(self) -> dict:
        return {
            k: str(v) if isinstance(v, EventType) else v
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({fields})"