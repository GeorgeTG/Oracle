import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { WebSocketService } from './websocket.service';
import { ParserEventType } from '../models/enums';

interface PlayerJoinEvent {
  type: ParserEventType;
  timestamp: string;
  player_name: string;
  mode: number;
}

@Injectable({
  providedIn: 'root'
})
export class PlayerService {
  private playerName: string | null = null;
  private playerNameSubject = new Subject<string>();

  constructor(private websocketService: WebSocketService) {
    console.log('[PlayerService] Initializing...');
    console.log('[PlayerService] WebSocket connected:', this.websocketService.isConnected);
    this.subscribeToPlayerJoin();
  }

  private subscribeToPlayerJoin(): void {
    console.log('[PlayerService] Subscribing to PLAYER_JOIN events...');
    console.log('[PlayerService] Looking for event type:', ParserEventType.PLAYER_JOIN);
    
    this.websocketService
      .subscribe<PlayerJoinEvent>(ParserEventType.PLAYER_JOIN)
      .subscribe(event => {
        console.log('[PlayerService] Player joined:', event.player_name);
        this.playerName = event.player_name;
        this.playerNameSubject.next(event.player_name);
      });
  }

  getName(): string | null {
    return this.playerName;
  }

  getNameObservable(): Observable<string> {
    return this.playerNameSubject.asObservable();
  }
}
