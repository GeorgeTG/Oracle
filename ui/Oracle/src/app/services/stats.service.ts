import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, filter } from 'rxjs';
import { WebSocketService } from './websocket.service';
import { ConfigurationService } from './configuration.service';
import { ServiceEventType } from '../models/enums';
import { StatsUpdateEvent, MapStartedEvent } from '../models/service-events';

@Injectable({
  providedIn: 'root'
})
export class StatsService {
  private lastStatsEvent$ = new BehaviorSubject<StatsUpdateEvent | null>(null);
  private lastMapEvent$ = new BehaviorSubject<MapStartedEvent | null>(null);

  // Historical data for charts
  private currencyPerMapHistory: number[] = [];
  private currencyPerHourHistory: number[] = [];
  private currencyCurrentPerHourHistory: number[] = [];
  private currencyCurrentRawHistory: number[] = [];
  private maxDataPoints = 50;

  constructor(
    private http: HttpClient,
    private websocketService: WebSocketService,
    private configService: ConfigurationService
  ) {
    // Subscribe to stats updates and keep the last event
    this.websocketService
      .subscribe<StatsUpdateEvent>(ServiceEventType.STATS_UPDATE)
      .subscribe(event => {
        console.log('[StatsService] Stats update received:', event);
        this.lastStatsEvent$.next(event);
        this.updateHistory(event);
      });

    // Subscribe to map events and keep the last event
    this.websocketService
      .subscribe<MapStartedEvent>(ServiceEventType.MAP_STARTED)
      .subscribe(event => {
        console.log('[StatsService] Map started:', event);
        this.lastMapEvent$.next(event);
      });
  }

  private updateHistory(event: StatsUpdateEvent): void {
    // Add new data points
    this.currencyPerMapHistory.push(event.currency_per_map || 0);
    this.currencyPerHourHistory.push(event.currency_per_hour || 0);
    this.currencyCurrentPerHourHistory.push(event.currency_current_per_hour || 0);
    this.currencyCurrentRawHistory.push(event.currency_current_raw || 0);

    // Keep only last N data points
    if (this.currencyPerMapHistory.length > this.maxDataPoints) {
      this.currencyPerMapHistory.shift();
      this.currencyPerHourHistory.shift();
      this.currencyCurrentPerHourHistory.shift();
      this.currencyCurrentRawHistory.shift();
    }
  }

  getHistory() {
    return {
      currencyPerMap: [...this.currencyPerMapHistory],
      currencyPerHour: [...this.currencyPerHourHistory],
      currencyCurrentPerHour: [...this.currencyCurrentPerHourHistory],
      currencyCurrentRaw: [...this.currencyCurrentRawHistory],
      labels: Array.from({ length: this.currencyPerMapHistory.length }, (_, i) => `${i + 1}`)
    };
  }

  clearHistory(): void {
    this.currencyPerMapHistory = [];
    this.currencyPerHourHistory = [];
    this.currencyCurrentPerHourHistory = [];
    this.currencyCurrentRawHistory = [];
  }

  /**
   * Get stats updates - immediately provides last event if available,
   * then continues with new events
   */
  getStats(): Observable<StatsUpdateEvent> {
    return this.lastStatsEvent$.asObservable().pipe(
      filter((event): event is StatsUpdateEvent => event !== null)
    );
  }

  /**
   * Get map events - immediately provides last event if available,
   * then continues with new events
   */
  getMapEvents(): Observable<MapStartedEvent> {
    return this.lastMapEvent$.asObservable().pipe(
      filter((event): event is MapStartedEvent => event !== null)
    );
  }

  /**
   * Get the current stats snapshot (synchronous)
   */
  getCurrentStats(): StatsUpdateEvent | null {
    return this.lastStatsEvent$.value;
  }

  /**
   * Get the current map snapshot (synchronous)
   */
  getCurrentMap(): MapStartedEvent | null {
    return this.lastMapEvent$.value;
  }

  /**
   * Reset stats via HTTP API
   */
  resetStats(): Observable<any> {
    const ip = localStorage.getItem('ws_ip') || '127.0.0.1';
    const port = localStorage.getItem('ws_port') || '8000';
    const url = `http://${ip}:${port}/stats/reset`;
    this.clearHistory(); // Clear history when resetting stats
    return this.http.post(url, {});
  }
}
