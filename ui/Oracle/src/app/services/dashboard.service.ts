import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigurationService } from './configuration.service';

export interface DashboardOverview {
  total_sessions: number;
  total_maps: number;
  total_playtime_hours: number;
  total_currency: number;
  total_exp: number;
  avg_currency_per_hour: number;
  avg_currency_per_map: number;
  avg_exp_per_hour: number;
  avg_maps_per_session: number;
  first_session: string | null;
  last_session: string | null;
}

export interface HeroStats {
  player_name: string;
  total_sessions: number;
  total_maps: number;
  total_playtime_hours: number;
  total_currency: number;
  avg_currency_per_hour: number;
  avg_currency_per_map: number;
  best_currency_per_hour: number;
  last_played: string;
}

export interface HeroesResponse {
  heroes: HeroStats[];
}

export interface TopItem {
  item_id: number;
  name: string;
  category: string;
  total_quantity: number;
  total_value: number;
  current_price: number;
  drop_count: number;
  maps_dropped_in: number;
}

export interface ItemsResponse {
  items: TopItem[];
  total_value_all: number;
}

export interface EfficiencyPeriod {
  period: string;
  sessions: number;
  maps: number;
  playtime_hours: number;
  currency: number;
  currency_per_hour: number;
}

export interface EfficiencySummary {
  avg_daily_currency: number;
  avg_daily_playtime_hours: number;
  best_period: string | null;
  best_currency: number;
}

export interface EfficiencyResponse {
  group_by: string;
  periods: EfficiencyPeriod[];
  summary: EfficiencySummary;
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {

  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }

  constructor(
    private http: HttpClient,
    private configService: ConfigurationService
  ) {}

  getOverview(playerName?: string, startDate?: string, endDate?: string): Observable<DashboardOverview> {
    let params = new HttpParams();
    if (playerName) params = params.set('player_name', playerName);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<DashboardOverview>(`${this.getApiUrl()}/dashboard/overview`, { params });
  }

  getHeroes(startDate?: string, endDate?: string, minSessions: number = 1): Observable<HeroesResponse> {
    let params = new HttpParams().set('min_sessions', minSessions.toString());
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<HeroesResponse>(`${this.getApiUrl()}/dashboard/heroes`, { params });
  }

  getItems(playerName?: string, startDate?: string, endDate?: string, limit: number = 50, sortBy: string = 'value'): Observable<ItemsResponse> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('sort_by', sortBy);
    if (playerName) params = params.set('player_name', playerName);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<ItemsResponse>(`${this.getApiUrl()}/dashboard/items`, { params });
  }

  getEfficiency(playerName?: string, startDate?: string, endDate?: string, groupBy: string = 'day'): Observable<EfficiencyResponse> {
    let params = new HttpParams().set('group_by', groupBy);
    if (playerName) params = params.set('player_name', playerName);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<EfficiencyResponse>(`${this.getApiUrl()}/dashboard/efficiency`, { params });
  }
}
