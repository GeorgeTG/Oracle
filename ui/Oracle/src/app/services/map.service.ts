import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigurationService } from './configuration.service';

export interface Affix {
  affix_id: number;
  description: string | null;
}

export interface MapCompletion {
  id: number;
  player_name: string | null;
  map_id: number;
  map_name: string | null;
  map_difficulty: string | null;
  affixes?: Affix[];
  started_at: string;
  completed_at: string;
  duration: number;
  currency_gained: number;
  exp_gained: number;
  items_gained: number;
  description?: string | null;
}

export interface MapItemChange {
  id: number;
  name: string | null;
  category: string | null;
  delta: number;
  total_price: number;
}

export interface ConsumedItem {
  id: number;
  name: string | null;
  category: string | null;
  quantity: number;
  total_price: number;
}

export interface MapsResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: MapCompletion[];
}

@Injectable({
  providedIn: 'root'
})
export class MapService {
  constructor(
    private http: HttpClient,
    private configService: ConfigurationService
  ) {}

  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }

  getMaps(
    page: number = 1, 
    pageSize: number = 20, 
    playerName?: string,
    sortField?: string,
    sortOrder?: number,
    filters?: {
      mapName?: string;
      difficulties?: string[];
      minCurrency?: number;
      minExp?: number;
      minItems?: number;
      sessionId?: number;
    }
  ): Observable<MapsResponse> {
    const url = `${this.getApiUrl()}/maps`;
    
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    
    if (playerName) {
      params = params.set('player_name', playerName);
    }
    
    if (sortField) {
      params = params.set('sort_field', sortField);
    }
    
    if (sortOrder) {
      params = params.set('sort_order', sortOrder.toString());
    }
    
    if (filters) {
      if (filters.mapName) {
        params = params.set('map_name_filter', filters.mapName);
      }
      
      if (filters.difficulties && filters.difficulties.length > 0) {
        params = params.set('difficulty_filter', filters.difficulties.join(','));
      }
      
      if (filters.minCurrency !== undefined) {
        params = params.set('min_currency', filters.minCurrency.toString());
      }
      
      if (filters.minExp !== undefined) {
        params = params.set('min_exp', filters.minExp.toString());
      }
      
      if (filters.minItems !== undefined) {
        params = params.set('min_items', filters.minItems.toString());
      }
      
      if (filters.sessionId !== undefined) {
        params = params.set('session_id', filters.sessionId.toString());
      }
    }
    
    return this.http.get<MapsResponse>(url, { params });
  }

  getMapDetails(mapId: number): Observable<MapCompletion> {
    const url = `${this.getApiUrl()}/maps/${mapId}`;
    return this.http.get<MapCompletion>(url);
  }

  getMapItems(mapId: number, consumed: boolean = false): Observable<MapItemChange[] | ConsumedItem[]> {
    const url = `${this.getApiUrl()}/maps/${mapId}/items`;
    const params = new HttpParams().set('consumed', consumed.toString());
    return this.http.get<MapItemChange[] | ConsumedItem[]>(url, { params });
  }

  deleteMap(mapId: number): Observable<any> {
    const url = `${this.getApiUrl()}/maps/${mapId}`;
    return this.http.delete(url);
  }

  updateMap(mapId: number, data: { description?: string }): Observable<any> {
    const url = `${this.getApiUrl()}/maps/${mapId}`;
    return this.http.patch(url, data);
  }
}
