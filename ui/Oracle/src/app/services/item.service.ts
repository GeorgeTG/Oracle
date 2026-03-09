import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigurationService } from './configuration.service';

export interface Item {
  id: number;
  item_id: number;
  name: string | null;
  category: string | null;
  rarity: string | null;
  price: number;
}

export interface ItemCreate {
  item_id: number;
  name?: string;
  category?: string;
  rarity?: string;
  price?: number;
}

export interface ItemUpdate {
  name?: string;
  category?: string;
  rarity?: string;
  price?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ItemService {
  constructor(
    private http: HttpClient,
    private configService: ConfigurationService,
  ) {}

  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }

  getItems(category?: string, minPrice?: number, maxPrice?: number, limit: number = 100): Observable<Item[]> {
    let params = new HttpParams();
    if (category) params = params.set('category', category);
    if (minPrice !== undefined && minPrice !== null) params = params.set('min_price', minPrice.toString());
    if (maxPrice !== undefined && maxPrice !== null) params = params.set('max_price', maxPrice.toString());
    params = params.set('limit', limit.toString());
    return this.http.get<Item[]>(`${this.getApiUrl()}/items`, { params });
  }

  getItem(id: number, byItemId: boolean = false): Observable<Item> {
    const params = byItemId ? new HttpParams().set('byItemId', 'true') : new HttpParams();
    return this.http.get<Item>(`${this.getApiUrl()}/items/${id}`, { params });
  }

  getItemByGameId(gameItemId: number): Observable<Item> {
    return this.http.get<Item>(`${this.getApiUrl()}/items/by-game-id/${gameItemId}`);
  }

  createItem(item: ItemCreate): Observable<Item> {
    return this.http.post<Item>(`${this.getApiUrl()}/items`, item);
  }

  updateItem(id: number, item: ItemUpdate): Observable<Item> {
    return this.http.patch<Item>(`${this.getApiUrl()}/items/${id}`, item);
  }

  deleteItem(id: number): Observable<void> {
    return this.http.delete<void>(`${this.getApiUrl()}/items/${id}`);
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.getApiUrl()}/items/categories`);
  }

  exportItems(): Observable<Blob> {
    return this.http.get(`${this.getApiUrl()}/items/export`, { responseType: 'blob' });
  }
}
