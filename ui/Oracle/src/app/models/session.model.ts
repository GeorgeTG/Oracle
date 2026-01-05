export interface MapTile {
  id: number;
  name: string;
  difficulty: string;
  currency: number;
  duration: string;
  description?: string | null;
}

export interface ApiMap {
  id: number;
  map_name: string | null;
  map_difficulty: string | null;
  completed_at: string;
  duration: number;
  currency_gained: number;
  exp_gained: number;
  description?: string | null;
}

export interface Session {
  id: number;
  player_name: string | null;
  started_at: string;
  ended_at: string | null;
  total_maps: number;
  total_currency_delta: number;
  currency_per_hour: number;
  currency_per_map: number;
  title: string | null;
  description: string | null;
  is_active?: boolean;
  maps?: ApiMap[];
}

export interface SessionsResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: Session[];
}

export interface SessionState {
  sessionId?: number;
  playerName: string;
  title: string;
  description: string;
  currencyPerHour: number;
  expPerHour: number;
  totalMaps: number;
  netCurrency: number;
  maps: MapTile[];
}
