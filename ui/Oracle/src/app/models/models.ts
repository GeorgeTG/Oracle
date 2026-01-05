// Auto-generated TypeScript models
// Do not edit manually - run generate_ts_models.py to regenerate

import { Difficulty, EventType } from "./enums";

// Generated from parsing\parsers\events\stage_affix.py
export interface AffixModel {
  affix_id: number;
  description?: string;
}

// Generated from services\model\inventory_model.py
export interface InventoryItem {
  item_id: number;
  quantity: number;
  name?: string;
  category?: string;
}

// Generated from services\model\inventory_model.py
export interface Inventory {
  slots: Record<number, number>;
}

// Generated from services\model\inventory_model.py
export interface InventorySnapshot {
  timestamp: string;
  data: Inventory;
}

// Generated from parsing\parsers\maps\map_data.py
export interface MapData {
  map_id: string;
  name: string;
  asset: string;
  area: string;
  difficulty?: Difficulty;
}

// Generated from parsing\parsers\events\model_base.py
export interface ModelBase {
  timestamp: string;
  type: EventType;
}
