// Auto-generated TypeScript models
// Do not edit manually - run tools/generate_ts_models.py to regenerate

import { ServiceEventType, StatsControlAction, WebSocketStatus, NotificationSeverity } from './enums';
import { Inventory, InventoryItem, InventorySnapshot, MapData } from './models';

// Generated from services\events\inventory.py
export interface InventorySnapshotEvent extends ServiceEvent {
  type: ServiceEventType;
  snapshot: InventorySnapshot;
}

// Generated from services\events\inventory.py
export interface InventoryUpdateEvent extends ServiceEvent {
  inventory: Inventory;
  type: ServiceEventType;
}

// Generated from services\events\map_events.py
export interface MapFinishedEvent extends ServiceEvent {
  duration: number;
  inventory_changes: Record<number, number>;
  map?: MapData;
  type: ServiceEventType;
}

// Generated from services\events\map_events.py
export interface MapStartedEvent extends ServiceEvent {
  level_id: number;
  level_uid: number;
  level_type: number;
  map?: MapData;
  consumed_items?: InventoryItem[];
  type: ServiceEventType;
}

// Generated from services\events\map_events.py
export interface MapStatsEvent extends ServiceEvent {
  duration: number;
  item_changes: Record<number, number>;
  currency_gained: number;
  exp_gained?: number;
  type: ServiceEventType;
}

// Generated from services\events\map_events.py
export interface MapRecordEvent extends ServiceEvent {
  map_record: {
    id: number;
    player_name: string;
    session_id?: number;
    map_id: number;
    map_name: string;
    map_difficulty: string;
    started_at: string;
    completed_at: string;
    duration: number;
    currency_gained: number;
    exp_gained: number;
    items_gained: number;
    description?: string;
  };
  type: ServiceEventType;
}

// Generated from services\events\session_events.py
export interface SessionStartedEvent extends ServiceEvent {
  session_id: number;
  player_name: string;
  started_at: string;
  description?: string;
  type: ServiceEventType;
}

// Generated from services\events\session_events.py
export interface SessionFinishedEvent extends ServiceEvent {
  session_id: number;
  player_name: string;
  started_at: string;
  ended_at: string;
  total_maps: number;
  total_currency_delta: number;
  currency_per_hour: number;
  currency_per_map: number;
  description?: string;
  type: ServiceEventType;
}

// Generated from services\events\session_events.py
export interface SessionRestoreEvent extends ServiceEvent {
  session_id: number;
  player_name: string;
  started_at: string;
  total_maps: number;
  total_time: number;
  currency_total: number;
  currency_per_hour: number;
  currency_per_map: number;
  exp_total: number;
  exp_per_hour: number;
  type: ServiceEventType;
}

// Generated from services\events\market_events.py
export interface MarketTransactionEvent extends ServiceEvent {
  item_id: number;
  quantity: number;
  action: string;
  transaction_id?: number;
  session_id?: number;
  type: ServiceEventType;
}

// Generated from services\events\level_events.py
export interface LevelProgressEvent extends ServiceEvent {
  level: number;
  current: number;
  remaining: number;
  level_total: number;
  percentage: number;
  type: ServiceEventType;
}

// Generated from services\events\inventory.py
export interface RequestInventoryEvent extends ServiceEvent {
  type: ServiceEventType;
  requester?: string;
}

// Generated from services\events\service_event.py
export interface ServiceEvent {
  timestamp: string;
  type: ServiceEventType;
}

// Generated from services\events\stats_events.py
export interface StatsControlEvent extends ServiceEvent {
  action: StatsControlAction;
  type: ServiceEventType;
}

// Generated from services\events\stats_events.py
export interface StatsUpdateEvent extends ServiceEvent {
  total_maps: number;
  total_time: number;
  session_duration: number;
  items_per_map: Record<number, number>;
  items_per_hour: Record<number, number>;
  exp_per_hour?: number;
  currency_per_map?: number;
  currency_per_hour?: number;
  currency_total?: number;
  currency_current_per_hour?: number;
  currency_current_raw?: number;
  map_timer?: number;
  type: ServiceEventType;
}

// Generated from services\events\websocket_events.py
export interface WebSocketEvent extends ServiceEvent {
  status: WebSocketStatus;
  websocket: any;
  client_info?: string;
  type: ServiceEventType;
}

// Generated from services\events\notification_events.py
export interface NotificationEvent extends ServiceEvent {
  title: string;
  content: string;
  severity: NotificationSeverity;
  duration?: number;
  type: ServiceEventType;
}
