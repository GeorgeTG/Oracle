import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, filter } from 'rxjs';
import { WebSocketService } from './websocket.service';
import { ConfigurationService } from './configuration.service';
import { ServiceEventType } from '../models/enums';
import { StatsUpdateEvent, MapStartedEvent } from '../models/service-events';

export interface StatsHistoryData {
  currencyPerMap: number[];
  currencyPerHour: number[];
  currencyCurrentPerHour: number[];
  currencyCurrentRaw: number[];
  expPerHour: number[];
  inventoryValue: number[];
  labels: string[];
}

class StatsHistory {
  private series: Record<string, number[]> = {
    currencyPerMap: [],
    currencyPerHour: [],
    currencyCurrentPerHour: [],
    currencyCurrentRaw: [],
    expPerHour: [],
    inventoryValue: [],
  };

  constructor(private maxDataPoints: number = 50) {}

  push(event: StatsUpdateEvent): void {
    this.series['currencyPerMap'].push(event.currency_per_map || 0);
    this.series['currencyPerHour'].push(event.currency_per_hour || 0);
    this.series['currencyCurrentPerHour'].push(event.currency_current_per_hour || 0);
    this.series['currencyCurrentRaw'].push(event.currency_current_raw || 0);
    this.series['expPerHour'].push(event.exp_per_hour || 0);
    this.series['inventoryValue'].push(event.inventory_value || 0);

    // Trim all series to max data points
    if (this.length > this.maxDataPoints) {
      for (const key of Object.keys(this.series)) {
        this.series[key].shift();
      }
    }
  }

  get length(): number {
    return this.series['currencyPerMap'].length;
  }

  snapshot(): StatsHistoryData {
    return {
      currencyPerMap: [...this.series['currencyPerMap']],
      currencyPerHour: [...this.series['currencyPerHour']],
      currencyCurrentPerHour: [...this.series['currencyCurrentPerHour']],
      currencyCurrentRaw: [...this.series['currencyCurrentRaw']],
      expPerHour: [...this.series['expPerHour']],
      inventoryValue: [...this.series['inventoryValue']],
      labels: Array.from({ length: this.length }, (_, i) => `${i + 1}`),
    };
  }

  clear(): void {
    for (const key of Object.keys(this.series)) {
      this.series[key] = [];
    }
  }
}

@Injectable({
  providedIn: 'root'
})
export class StatsService {
  private lastStatsEvent$ = new BehaviorSubject<StatsUpdateEvent | null>(null);
  private lastMapEvent$ = new BehaviorSubject<MapStartedEvent | null>(null);
  private history = new StatsHistory(50);

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
        this.history.push(event);
      });

    // Subscribe to map events and keep the last event
    this.websocketService
      .subscribe<MapStartedEvent>(ServiceEventType.MAP_STARTED, ServiceEventType.MAP_STATUS)
      .subscribe(event => {
        console.log('[StatsService] Map started:', event);
        this.lastMapEvent$.next(event);
      });
  }

  getHistory(): StatsHistoryData {
    return this.history.snapshot();
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
  newSession(): Observable<any> {
    const ip = localStorage.getItem('ws_ip') || '127.0.0.1';
    const port = localStorage.getItem('ws_port') || '8000';
    const url = `http://${ip}:${port}/sessions`;
    this.history.clear();
    return this.http.post(url, {});
  }

  resetStats(): Observable<any> {
    const ip = localStorage.getItem('ws_ip') || '127.0.0.1';
    const port = localStorage.getItem('ws_port') || '8000';
    const url = `http://${ip}:${port}/stats/reset`;
    this.history.clear();
    return this.http.post(url, {});
  }
}
