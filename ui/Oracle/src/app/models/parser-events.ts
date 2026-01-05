// Auto-generated TypeScript models
// Do not edit manually - run tools/generate_ts_models.py to regenerate

import { ParserEventType } from './enums';
import { MapData } from './models';

// Generated from parsing\parsers\events\bag_modify.py
export interface BagModifyEvent extends ParserEvent {
  page: number;
  slot: number;
  item_id: number;
  quantity: number;
  name?: string;
  category?: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\enter_level.py
export interface EnterLevelEvent extends ParserEvent {
  level_id: number;
  level_uid: number;
  level_type: number;
  map?: MapData;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\exit_level.py
export interface ExitLevelEvent extends ParserEvent {
  type: ParserEventType;
}

// Generated from parsing\parsers\events\exp_update.py
export interface ExpUpdateEvent extends ParserEvent {
  timestamp: string;
  experience: number;
  level: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\game_message.py
export interface GameMessageEvent extends ParserEvent {
  timestamp: string;
  message: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\game_pause.py
export interface GamePauseEvent extends ParserEvent {
  timestamp: string;
  is_paused: boolean;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\game_view.py
export interface GameViewEvent extends ParserEvent {
  view: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\item_change.py
export interface ItemChangeEvent extends ParserEvent {
  item_id: number;
  page: number;
  slot: number;
  action: string;
  amount?: number;
  name?: string;
  category?: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\loading_progress.py
export interface LoadingProgressEvent extends ParserEvent {
  primary: number;
  secondary_type: string;
  secondary_progress: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\map_loaded.py
export interface MapLoadedEvent extends ParserEvent {
  timestamp: string;
  map_path: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\parser_event.py
export interface ParserEvent {
  timestamp: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\ping.py
export interface PingEvent extends ParserEvent {
  ping: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\player_join.py
export interface PlayerJoinEvent extends ParserEvent {
  player_name: string;
  mode: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\s12_gameplay.py
export interface S12GameplayEvent extends ParserEvent {
  timestamp: string;
  layer: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\stage_affix.py
export interface StageAffixEvent extends ParserEvent {
  affixes: any;
  level_id?: number;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\transition_style.py
export interface TransitionStyleEvent extends ParserEvent {
  timestamp: string;
  transition_style: string;
  type: ParserEventType;
}

// Generated from parsing\parsers\events\world_transition.py
export interface WorldTransitionEvent extends ParserEvent {
  timestamp: string;
  back_flow_step: number;
  is_switching_to_main_world: boolean;
  type: ParserEventType;
}
