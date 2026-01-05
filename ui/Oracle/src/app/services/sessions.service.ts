import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { MessageService } from 'primeng/api';
import { WebSocketService } from './websocket.service';
import { ConfigurationService } from './configuration.service';
import { ServiceEventType } from '../models/enums';
import { SessionStartedEvent, SessionFinishedEvent, SessionRestoreEvent, MapRecordEvent, MarketTransactionEvent, StatsUpdateEvent } from '../models/service-events';
import { MapTile, Session, SessionsResponse, SessionState } from '../models/session.model';

export interface SessionListItem {
  id: number;
  player_name: string;
  started_at: string;
  ended_at: string | null;
  total_maps: number;
  total_currency_delta: number;
  currency_per_hour: number;
  currency_per_map: number;
  title: string;
  description: string | null;
  is_active?: boolean;
}

export interface SessionDetails {
  id: number;
  player_name: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number;
  is_active: boolean;
  title: string;
  description: string | null;
  total_maps: number;
  total_currency: number;
  maps_currency: number;
  market_currency: number;
  currency_per_hour: number;
  currency_per_map: number;
  maps: MapDetails[];
  market_transactions: MarketTransactionDetails[];
}

export interface MapDetails {
  id: number;
  map_name: string;
  map_difficulty: string;
  started_at: string;
  completed_at: string;
  duration: number;
  currency_gained: number;
  exp_gained: number;
  items_gained: number;
  description: string | null;
  items: MapItemDetails[];
}

export interface MapItemDetails {
  item_id: number;
  name: string;
  delta: number;
  total_price: number;
}

export interface MarketTransactionDetails {
  id: number;
  timestamp: string;
  item_id: number;
  item_name: string;
  quantity: number;
  action: string;
  unit_price: number;
  total_value: number;
}

export interface SessionsListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: SessionListItem[];
}

@Injectable({
  providedIn: 'root'
})
export class SessionsService {
  private readonly initialState: SessionState = {
    sessionId: undefined,
    playerName: '',
    title: '',
    description: '',
    currencyPerHour: 0,
    expPerHour: 0,
    totalMaps: 0,
    netCurrency: 0,
    maps: []
  };

  private stateSubject = new BehaviorSubject<SessionState>(this.initialState);
  public state$: Observable<SessionState> = this.stateSubject.asObservable();

  private getApiUrl(): string {
    return this.configService.getApiUrl();
  }

  constructor(
    private http: HttpClient,
    private wsService: WebSocketService,
    private configService: ConfigurationService,
    private messageService: MessageService
  ) {
    this.initializeWebSocketSubscriptions();
  }

  private initializeWebSocketSubscriptions(): void {
    // Subscribe to session started events
    this.wsService.subscribe<SessionStartedEvent>(ServiceEventType.SESSION_STARTED)
      .subscribe(event => this.handleSessionStarted(event));
    
    // Subscribe to session finished events
    this.wsService.subscribe<SessionFinishedEvent>(ServiceEventType.SESSION_FINISHED)
      .subscribe(event => this.handleSessionFinished(event));
    
    // Subscribe to session restore events
    this.wsService.subscribe<SessionRestoreEvent>(ServiceEventType.SESSION_RESTORE)
      .subscribe(event => this.handleSessionRestore(event));
    
    // Subscribe to map record events
    this.wsService.subscribe<MapRecordEvent>(ServiceEventType.MAP_RECORD)
      .subscribe(event => this.handleMapRecord(event));
    
    // Subscribe to stats update events
    this.wsService.subscribe<StatsUpdateEvent>(ServiceEventType.STATS_UPDATE)
      .subscribe(event => this.handleStatsUpdate(event));
  }

  private handleSessionStarted(event: SessionStartedEvent): void {
    console.log('[SessionsService] Session started:', event);
    
    // Show toast notification
    this.messageService.add({
      severity: 'success',
      summary: 'Session Started',
      detail: `New session started for ${event.player_name}`,
      life: 3000
    });
    
    this.stateSubject.next({
      sessionId: event.session_id,
      playerName: event.player_name,
      title: '',
      description: event.description || '',
      currencyPerHour: 0,
      expPerHour: 0,
      totalMaps: 0,
      netCurrency: 0,
      maps: []
    });
  }

  private handleSessionFinished(event: SessionFinishedEvent): void {
    console.log('[SessionsService] Session finished:', event);
    const current = this.stateSubject.value;
    this.stateSubject.next({
      ...current,
      currencyPerHour: event.currency_per_hour,
      totalMaps: event.total_maps
    });
  }

  private handleSessionRestore(event: SessionRestoreEvent): void {
    console.log('[SessionsService] ⚡ Session restore event received:', event);
    
    // Show toast notification
    this.messageService.add({
      severity: 'info',
      summary: 'Session Restored',
      detail: `Restored session for ${event.player_name} with ${event.total_maps} maps`,
      life: 5000
    });
    
    console.log('[SessionsService] Toast notification sent');
    
    // Update state with restored session data
    this.stateSubject.next({
      sessionId: event.session_id,
      playerName: event.player_name,
      title: '',
      description: '',
      currencyPerHour: event.currency_per_hour,
      expPerHour: event.exp_per_hour,
      totalMaps: event.total_maps,
      netCurrency: event.currency_total,
      maps: []
    });
    
    console.log('[SessionsService] Session state updated');
  }

  private handleMapRecord(event: MapRecordEvent): void {
    const map = event.map_record;
    const current = this.stateSubject.value;
    
    // Only add if it's from current session
    if (current.sessionId === undefined || map.session_id === current.sessionId) {
      console.log('[SessionsService] Adding map:', map);
      const duration = this.formatDuration(map.duration);
      
      const newMap: MapTile = {
        id: map.id,
        name: map.map_name,
        difficulty: map.map_difficulty,
        currency: map.currency_gained,
        duration,
        description: map.description
      };
      
      const updatedMaps = [newMap, ...current.maps].slice(0, 10);
      
      this.stateSubject.next({
        ...current,
        maps: updatedMaps,
        totalMaps: current.totalMaps + 1
      });
    }
  }

  private handleStatsUpdate(event: StatsUpdateEvent): void {
    const current = this.stateSubject.value;
    const updates: Partial<SessionState> = {};
    
    if (event.currency_total !== undefined) {
      updates.netCurrency = event.currency_total;
    }
    if (event.currency_per_hour !== undefined) {
      updates.currencyPerHour = event.currency_per_hour;
    }
    if (event.exp_per_hour !== undefined) {
      updates.expPerHour = event.exp_per_hour;
    }
    
    if (Object.keys(updates).length > 0) {
      this.stateSubject.next({ ...current, ...updates });
    }
  }

  private formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  get currentState(): SessionState {
    return this.stateSubject.value;
  }

  updateState(partial: Partial<SessionState>): void {
    const current = this.stateSubject.value;
    this.stateSubject.next({ ...current, ...partial });
  }

  resetState(): void {
    this.stateSubject.next({ ...this.initialState });
  }

  addMap(map: MapTile): void {
    const current = this.stateSubject.value;
    const updatedMaps = [map, ...current.maps].slice(0, 10); // Keep last 10 maps
    this.stateSubject.next({
      ...current,
      maps: updatedMaps,
      totalMaps: current.totalMaps + 1
    });
  }

  getPlayers(): Observable<{players: string[], total: number}> {
    const url = `${this.getApiUrl()}/players`;
    return this.http.get<{players: string[], total: number}>(url);
  }

  getSessions(
    playerName?: string,
    page: number = 1,
    pageSize: number = 50
  ): Observable<SessionsListResponse> {
    const url = `${this.getApiUrl()}/sessions`;
    
    let params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    
    if (playerName) {
      params = params.set('player_name', playerName);
    }
    
    return this.http.get<SessionsListResponse>(url, { params });
  }

  getSessionDetails(sessionId: number): Observable<SessionDetails> {
    const url = `${this.getApiUrl()}/sessions/${sessionId}`;
    return this.http.get<SessionDetails>(url);
  }

  updateSession(sessionId: number, data: Partial<Session>): Observable<Session> {
    const url = `${this.getApiUrl()}/sessions/${sessionId}`;
    return this.http.patch<Session>(url, data);
  }

  getActiveSession(): Observable<{ session: Session | null }> {
    const url = `${this.getApiUrl()}/sessions/active`;
    return this.http.get<{ session: Session | null }>(url);
  }

  loadActiveSession(): void {
    this.getActiveSession().subscribe({
      next: (response) => {
        console.log('[SessionsService] Loaded active session:', response);
        if (response.session) {
          const session = response.session;
          this.stateSubject.next({
            sessionId: session.id,
            playerName: session.player_name || '',
            title: session.title || '',
            description: session.description || '',
            currencyPerHour: 0,  // Will be updated by STATS_UPDATE event
            expPerHour: 0,       // Will be updated by STATS_UPDATE event
            totalMaps: session.total_maps || 0,
            netCurrency: 0,      // Will be updated by STATS_UPDATE event
            maps: (session.maps || []).map(m => ({
              id: m.id,
              name: m.map_name || 'Unknown',
              difficulty: m.map_difficulty || '',
              currency: m.currency_gained || 0,
              duration: this.formatDuration(m.duration || 0),
              description: m.description
            }))
          });
        } else {
          // No active session - reset to initial state
          this.resetState();
        }
      },
      error: (err) => {
        console.error('[SessionsService] Failed to load active session:', err);
        this.resetState();
      }
    });
  }

  startNewSession(): void {
    console.log('[SessionsService] Starting new session');
    
    this.http.post(`${this.getApiUrl()}/sessions`, {}).subscribe({
      next: (response: any) => {
        console.log('[SessionsService] Session control event published:', response);
      },
      error: (error) => {
        console.error('[SessionsService] Failed to publish session control event:', error);
      }
    });
  }
}
