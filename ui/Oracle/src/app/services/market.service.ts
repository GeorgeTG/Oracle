import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { WebSocketService } from './websocket.service';
import { ConfigurationService } from './configuration.service';
import { ServiceEventType } from '../models/enums';
import { MarketTransactionEvent } from '../models/service-events';

export interface MarketTransaction {
  id: number;
  player_name: string | null;
  timestamp: string;
  item_id: number | null;
  item_name: string | null;
  quantity: number;
  action: string;
  session_id: number | null;
  session_title: string | null;
}

export interface MarketResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: MarketTransaction[];
}

@Injectable({
  providedIn: 'root'
})
export class MarketService {
  private transactionsSubject = new BehaviorSubject<MarketTransaction[]>([]);
  public transactions$ = this.transactionsSubject.asObservable();
  
  private currentSessionId: number | null = null;
  
  constructor(
    private http: HttpClient,
    private websocketService: WebSocketService,
    private configService: ConfigurationService
  ) {
    this.initializeWebSocketSubscriptions();
  }
  
  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }
  
  private initializeWebSocketSubscriptions(): void {
    // Subscribe to market transaction events
    this.websocketService.subscribe<MarketTransactionEvent>(ServiceEventType.MARKET_TRANSACTION)
      .subscribe(event => this.handleMarketTransaction(event));
  }
  
  private handleMarketTransaction(event: MarketTransactionEvent): void {
    console.log('[MarketService] Market transaction event:', event);
    
    // Only add if it's for the current session
    if (this.currentSessionId && event.session_id === this.currentSessionId) {
      // Reload transactions for current session
      this.loadTransactionsForSession(this.currentSessionId);
    }
  }
  
  public setCurrentSession(sessionId: number | null): void {
    this.currentSessionId = sessionId;
    if (sessionId) {
      this.loadTransactionsForSession(sessionId);
    } else {
      this.transactionsSubject.next([]);
    }
  }
  
  private loadTransactionsForSession(sessionId: number): void {
    this.getTransactions(1, 100, undefined, 'timestamp', -1, { sessionId }).subscribe({
      next: (response) => {
        this.transactionsSubject.next(response.results);
      },
      error: (err) => {
        console.error('[MarketService] Failed to load transactions:', err);
      }
    });
  }

  getTransactions(
    page: number = 1, 
    pageSize: number = 20, 
    playerName?: string,
    sortField?: string,
    sortOrder?: number,
    filters?: {
      itemName?: string;
      action?: string;
      minQuantity?: number;
      sessionId?: number;
    }
  ): Observable<MarketResponse> {
    const url = `${this.getApiUrl()}/market`;
    
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
      if (filters.itemName) {
        params = params.set('item_name_filter', filters.itemName);
      }
      
      if (filters.action) {
        params = params.set('action_filter', filters.action);
      }
      
      if (filters.minQuantity !== undefined) {
        params = params.set('min_quantity', filters.minQuantity.toString());
      }
      
      if (filters.sessionId !== undefined) {
        params = params.set('session_id', filters.sessionId.toString());
      }
    }
    
    return this.http.get<MarketResponse>(url, { params });
  }

  getTransactionDetail(transactionId: number): Observable<MarketTransaction> {
    const url = `${this.getApiUrl()}/market/${transactionId}`;
    return this.http.get<MarketTransaction>(url);
  }
}
