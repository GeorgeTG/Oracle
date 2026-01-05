// Auto-generated TypeScript enums
// Do not edit manually - run tools/generate_ts_models.py to regenerate

export enum Difficulty {
  T8_PLUS = 'T8_PLUS',
  T8_2 = 'T8_2',
  T8_1 = 'T8_1',
  T8_0 = 'T8_0',
  T7_2 = 'T7_2',
  T7_1 = 'T7_1',
  T7_0 = 'T7_0',
  T6 = 'T6',
  T5 = 'T5',
  T4 = 'T4',
  T3 = 'T3',
  T2 = 'T2',
  T1 = 'T1',
  DS = 'DS',
}

export enum EventType {
  NONE = 'NONE',
  ITEM_CHANGE = 'ITEM_CHANGE',
  ITEM_PICKUP = 'ITEM_PICKUP',
  GAME_VIEW = 'GAME_VIEW',
  SCENE_TRANSITION_START = 'SCENE_TRANSITION_START',
  BAG_MODIFY = 'BAG_MODIFY',
  PING = 'PING',
  LOADING_PROGRESS = 'LOADING_PROGRESS',
  ENTER_LEVEL = 'ENTER_LEVEL',
  EXIT_LEVEL = 'EXIT_LEVEL',
  STAGE_AFFIX = 'STAGE_AFFIX',
  MONSTER_SPAWN = 'MONSTER_SPAWN',
  LEVEL_UP = 'LEVEL_UP',
  BOSS_SPAWN = 'BOSS_SPAWN',
  LOOT_DROP = 'LOOT_DROP',
  GAME_PAUSE = 'GAME_PAUSE',
}

export enum MapState {
  IDLE = 'IDLE',
  FARMING = 'FARMING',
  PAUSED = 'PAUSED',
}

export enum ParseState {
  IDLE = 'IDLE',
  GOT_ENTER = 'GOT_ENTER',
  GOT_LEVEL_INFO = 'GOT_LEVEL_INFO',
}

export enum ParserEventType {
  NONE = 'none',
  ITEM_CHANGE = 'item_change',
  ITEM_PICKUP = 'item_pickup',
  GAME_VIEW = 'game_view',
  SCENE_TRANSITION_START = 'scene_transition_start',
  BAG_MODIFY = 'bag_modify',
  PING = 'ping',
  LOADING_PROGRESS = 'loading_progress',
  ENTER_LEVEL = 'enter_level',
  EXIT_LEVEL = 'exit_level',
  STAGE_AFFIX = 'stage_affix',
  MAP_LOADED = 'map_loaded',
  WORLD_TRANSITION = 'world_transition',
  MONSTER_SPAWN = 'monster_spawn',
  LEVEL_UP = 'level_up',
  BOSS_SPAWN = 'boss_spawn',
  LOOT_DROP = 'loot_drop',
  GAME_PAUSE = 'game_pause',
  EXP_UPDATE = 'exp_update',
  GAME_MESSAGE = 'game_message',
  S12_GAMEPLAY = 's12_gameplay',
  TRANSITION_STYLE = 'transition_style',
  PLAYER_JOIN = 'player_join',
}

export enum ServiceEventType {
  NONE = 'none',
  CLIENT_CONNECTED = 'client_connected',
  CLIENT_DISCONNECTED = 'client_disconnected',
  REQUEST_INVENTORY = 'request_inventory',
  REQUEST_MAP = 'request_map',
  INVENTORY_SNAPSHOT = 'inventory_snapshot',
  INVENTORY_UPDATE = 'inventory_update',
  MAP_SNAPSHOT = 'map_snapshot',
  ITEM_LOOT = 'item_loot',
  MAP_STARTED = 'map_started',
  MAP_FINISHED = 'map_finished',
  MAP_STATS = 'map_stats',
  STATS_UPDATE = 'stats_update',
  STATS_CONTROL = 'stats_control',
  SESSION_CONTROL = 'session_control',
  SESSION_STARTED = 'session_started',
  SESSION_FINISHED = 'session_finished',
  SESSION_RESTORE = 'session_restore',
  MAP_RECORD = 'map_record',
  MARKET_TRANSACTION = 'market_transaction',
  LEVEL_PROGRESS = 'level_progress',
  WEBSOCKET_CONNECTED = 'websocket_connected',
  WEBSOCKET_DISCONNECTED = 'websocket_disconnected',
  NOTIFICATION = 'notification',
}

export enum NotificationSeverity {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

export enum StatsControlAction {
  START = 'START',
  STOP = 'STOP',
  RESTART = 'RESTART',
}

export enum WebSocketStatus {
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
}
