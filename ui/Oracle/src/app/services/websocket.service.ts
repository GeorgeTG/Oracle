import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, Subject, filter } from 'rxjs';
import { ParserEventType, ServiceEventType, NotificationSeverity } from '../models/enums';
import { NotificationEvent, HotkeyPressedEvent, HoverEnterEvent, HoverLeaveEvent } from '../models/service-events';
import { ToastService } from './toast.service';
import { ConfigurationService } from './configuration.service';
import { OverlayService } from './overlay.service';

type EventType = ParserEventType | ServiceEventType;

interface BaseEvent {
  type: EventType;
  timestamp: string;
}

export interface ComponentStatus {
  name: string;
  version: string;
  connected: boolean;
}

interface HeartbeatEvent extends BaseEvent {
  name: string;
  version: string;
}

@Injectable({
  providedIn: 'root'
})
export class WebSocketService {
  private ws: WebSocket | null = null;
  private eventSubject = new Subject<BaseEvent>();
  private reconnectAttempts = 0;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000; // Max 30 seconds between attempts

  private heartbeatMap = new Map<string, { version: string; lastSeen: number }>();
  private _componentStatus$ = new BehaviorSubject<ComponentStatus[]>([]);
  componentStatus$ = this._componentStatus$.asObservable();

  constructor(
    private toastService: ToastService,
    private configService: ConfigurationService,
    private overlayService: OverlayService,
    private router: Router
  ) {
    this.connect();
    this.setupHeartbeatHandler();
    // Only setup notification handler if not in overlay
    if (!this.isOverlayRoute()) {
      this.setupNotificationHandler();
    }
    // Only handle hotkey/hover events in the main window, not the overlay window
    // (overlay window has its own Angular instance with its own services)
    if (!this.isOverlayRoute()) {
      this.setupHotkeyHandler();
      this.setupHoverHandler();
    }
  }

  private isOverlayRoute(): boolean {
    return window.location.pathname.startsWith('/overlay');
  }

  private getWebSocketUrl(): string {
    return this.configService.getWsUrl();
  }

  private connect(): void {
    const wsUrl = this.getWebSocketUrl();
    
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to', wsUrl);
        this.reconnectAttempts = 0;
        if (!this.isOverlayRoute()) {
          this.toastService.success('Connected', 'WebSocket connection established');
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type !== 'heartbeat') {
            console.log('[WebSocket] Received event:', data.type, data);
          }
          this.eventSubject.next(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Connection closed');
        if (!this.isOverlayRoute()) {
          this.toastService.warn('Disconnected', 'WebSocket connection lost. Reconnecting...');
        }
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, this.maxReconnectDelay);
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Setup automatic notification handling
   */
  private setupNotificationHandler(): void {
    this.subscribe<NotificationEvent>(ServiceEventType.NOTIFICATION).subscribe(event => {
      const duration = event.duration || 5000; // Default 5 seconds
      
      switch (event.severity) {
        case NotificationSeverity.SUCCESS:
          this.toastService.success(event.title, event.content, duration);
          break;
        case NotificationSeverity.WARNING:
          this.toastService.warn(event.title, event.content, duration);
          break;
        case NotificationSeverity.ERROR:
          this.toastService.error(event.title, event.content, duration);
          break;
        case NotificationSeverity.INFO:
        default:
          this.toastService.info(event.title, event.content, duration);
          break;
      }
    });
  }

  /**
   * Setup hotkey event handling - listens for HOTKEY_PRESSED from external hotkey tool
   */
  private setupHotkeyHandler(): void {
    this.subscribe<HotkeyPressedEvent>(ServiceEventType.HOTKEY_PRESSED).subscribe(event => {
      const config = this.configService.getConfig();
      const normalize = (k: string) => k.toLowerCase().replace(/_/g, '');
      const key = normalize(event.key);
      console.log(`[WebSocket] Hotkey received: "${event.key}" -> normalized: "${key}" | editKey: "${normalize(config.hotkeyKey)}" | toggleKey: "${normalize(config.toggleOverlayKey)}"`);

      if (key === normalize(config.hotkeyKey)) {
        // Edit mode toggle always works (needed to exit edit mode via oracle-hotkey)
        console.log(`[WebSocket] Edit mode hotkey matched: ${event.key}`);
        this.overlayService.handlePageUp();
      } else if (this.overlayService.isEditMode) {
        // In edit mode, block all other hotkeys from oracle-hotkey
        console.log(`[WebSocket] Ignoring hotkey in edit mode: ${event.key}`);
      } else if (key === normalize(config.toggleOverlayKey)) {
        console.log(`[WebSocket] Toggle overlay hotkey matched: ${event.key}`);
        this.overlayService.toggleOverlay();
      }
    });
  }

  /**
   * Setup hover event handling - listens for HOVER_ENTER/HOVER_LEAVE from Oracle-Hotkey
   */
  private setupHoverHandler(): void {
    this.subscribe<HoverEnterEvent>(ServiceEventType.HOVER_ENTER).subscribe(() => {
      console.log('[WebSocket] Hover enter event received');
      this.overlayService.setHoverMode(true);
    });

    this.subscribe<HoverLeaveEvent>(ServiceEventType.HOVER_LEAVE).subscribe(() => {
      console.log('[WebSocket] Hover leave event received');
      this.overlayService.setHoverMode(false);
    });
  }

  private setupHeartbeatHandler(): void {
    this.subscribe<HeartbeatEvent>(ServiceEventType.HEARTBEAT).subscribe(event => {
      this.heartbeatMap.set(event.name, { version: event.version, lastSeen: Date.now() });
    });

    setInterval(() => {
      const now = Date.now();
      const status: ComponentStatus[] = Array.from(this.heartbeatMap.entries()).map(([name, data]) => ({
        name,
        version: data.version,
        connected: (now - data.lastSeen) < 3000
      }));
      this._componentStatus$.next(status);
    }, 1000);
  }

  /**
   * Subscribe to specific event types
   * @param eventTypes One or more event types to filter
   * @returns Observable that emits only the specified event types
   * 
   * @example
   * // Subscribe to single event type
   * websocketService.subscribe(ParserEventType.MAP_LOADED).subscribe(event => {
   *   console.log('Map loaded:', event);
   * });
   * 
   * @example
   * // Subscribe to multiple event types
   * websocketService.subscribe(
   *   ParserEventType.MAP_LOADED,
   *   ServiceEventType.MAP_STARTED
   * ).subscribe(event => {
   *   console.log('Event received:', event);
   * });
   */
  subscribe<T extends BaseEvent>(...eventTypes: EventType[]): Observable<T> {
    return this.eventSubject.asObservable().pipe(
      filter(event => eventTypes.includes(event.type))
    ) as Observable<T>;
  }

  /**
   * Subscribe to all events (no filtering)
   * @returns Observable that emits all events
   */
  subscribeAll(): Observable<BaseEvent> {
    return this.eventSubject.asObservable();
  }

  /**
   * Send a message through the WebSocket
   * @param message Message to send
   */
  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof message === 'string' ? message : JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message - connection not open');
    }
  }

  /**
   * Close the WebSocket connection
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Reconnect to WebSocket (useful after settings change)
   */
  reconnect(): void {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.connect();
  }

  /**
   * Get current connection state
   */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
