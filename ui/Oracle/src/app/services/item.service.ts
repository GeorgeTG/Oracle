import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { ConfigurationService } from './configuration.service';
import { WebSocketService } from './websocket.service';
import { ToastService } from './toast.service';
import { ServiceEventType } from '../models/enums';
import { ItemObtainedEvent } from '../models/service-events';

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
  private _itemChanged$ = new Subject<ItemObtainedEvent>();
  itemChanged$ = this._itemChanged$.asObservable();

  constructor(
    private http: HttpClient,
    private configService: ConfigurationService,
    private websocketService: WebSocketService,
    private toastService: ToastService
  ) {
    this.websocketService.subscribe<ItemObtainedEvent>(
      ServiceEventType.ITEM_OBTAINED
    ).subscribe(event => {
      this._itemChanged$.next(event);
    });

    this.websocketService.subscribe<any>(
      ServiceEventType.ITEM_DATA_CHANGED
    ).subscribe(event => {
      const name = event.name || `Item #${event.item_id}`;
      this.toastService.info('Item Updated', `${name} — Price: ${event.price}`);
      this._itemChanged$.next(event);
    });
  }

  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }

  getItems(category?: string, minPrice?: number, maxPrice?: number, limit: number = 100): Observable<Item[]> {
    let params = new HttpParams();
    
    if (category) {
      params = params.set('category', category);
    }
    if (minPrice !== undefined && minPrice !== null) {
      params = params.set('min_price', minPrice.toString());
    }
    if (maxPrice !== undefined && maxPrice !== null) {
      params = params.set('max_price', maxPrice.toString());
    }
    params = params.set('limit', limit.toString());
    
    const url = `${this.getApiUrl()}/items`;
    return this.http.get<Item[]>(url, { params });
  }

  getItem(id: number, byItemId: boolean = false): Observable<Item> {
    let params = new HttpParams();
    if (byItemId) {
      params = params.set('byItemId', 'true');
    }
    const url = `${this.getApiUrl()}/items/${id}`;
    return this.http.get<Item>(url, { params });
  }

  getItemByGameId(gameItemId: number): Observable<Item> {
    const url = `${this.getApiUrl()}/items/by-game-id/${gameItemId}`;
    return this.http.get<Item>(url);
  }

  createItem(item: ItemCreate): Observable<Item> {
    const url = `${this.getApiUrl()}/items`;
    return this.http.post<Item>(url, item);
  }

  updateItem(id: number, item: ItemUpdate): Observable<Item> {
    const url = `${this.getApiUrl()}/items/${id}`;
    return this.http.patch<Item>(url, item);
  }

  deleteItem(id: number): Observable<void> {
    const url = `${this.getApiUrl()}/items/${id}`;
    return this.http.delete<void>(url);
  }

  getCategories(): Observable<string[]> {
    const url = `${this.getApiUrl()}/items/categories`;
    return this.http.get<string[]>(url);
  }

  exportItems(): Observable<Blob> {
    const url = `${this.getApiUrl()}/items/export`;
    return this.http.get(url, { responseType: 'blob' });
  }
}
