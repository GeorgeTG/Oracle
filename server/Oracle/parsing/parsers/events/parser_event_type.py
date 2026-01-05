from __future__ import annotations
from enum import Enum


class ParserEventType(str, Enum):
    """Event type enum that can be used as ParserEventType.VALUE and converts to lowercase string."""
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
    MAP_LOADED = "map_loaded"
    WORLD_TRANSITION = "world_transition"
    MONSTER_SPAWN = "monster_spawn"
    LEVEL_UP = "level_up"
    BOSS_SPAWN = "boss_spawn"
    LOOT_DROP = "loot_drop"
    GAME_PAUSE = "game_pause"
    EXP_UPDATE = "exp_update"
    GAME_MESSAGE = "game_message"
    S12_GAMEPLAY = "s12_gameplay"
    TRANSITION_STYLE = "transition_style"
    PLAYER_JOIN = "player_join"
    
    def __str__(self) -> str:
        return self.value
