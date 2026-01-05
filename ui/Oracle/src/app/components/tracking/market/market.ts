import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarketService, MarketTransaction, MarketResponse } from '../../../services/market.service';
import { SessionsService } from '../../../services/sessions.service';
import { Session } from '../../../models/session.model';
import { PlayerService } from '../../../services/player.service';
import { WebSocketService } from '../../../services/websocket.service';
import { ToastService } from '../../../services/toast.service';
import { Table, TableModule, TableLazyLoadEvent } from 'primeng/table';
import { Select } from 'primeng/select';
import { InputText } from 'primeng/inputtext';
import { Subscription } from 'rxjs';
import { ServiceEventType } from '../../../models/enums';
import { MarketTransactionEvent } from '../../../models/service-events';

@Component({
  selector: 'app-tracking-market',
  imports: [CommonModule, FormsModule, TableModule, Select, InputText],
  templateUrl: './market.html',
  styleUrl: './market.css',
})
export class MarketComponent implements OnInit, OnDestroy {
  transactions: MarketTransaction[] = [];
  totalRecords: number = 0;
  loading: boolean = false;
  playerName: string | null = null;
  private playerSubscription?: Subscription;
  private marketSubscription?: Subscription;
  private lastLazyEvent?: TableLazyLoadEvent;
  
  // Session filter
  sessions: any[] = [];
  selectedSession: any = null;
  
  // Filter values
  filterItemName: string = '';
  filterAction: string = '';
  filterMinQuantity: number | null = null;
  
  // Action options for filter
  actionOptions = [
    { label: 'All', value: '' },
    { label: 'Bought', value: 'bought' },
    { label: 'Sold', value: 'sold' },
    { label: 'Gained', value: 'gained' }
  ];

  constructor(
    private marketService: MarketService,
    private sessionsService: SessionsService,
    private playerService: PlayerService,
    private websocketService: WebSocketService,
    private toastService: ToastService
  ) {}

  ngOnInit() {
    this.playerName = this.playerService.getName();
    this.playerSubscription = this.playerService.getNameObservable().subscribe(name => {
      this.playerName = name;
      this.loadSessions();
    });
    this.loadSessions();
    
    // Subscribe to market transaction events
    this.marketSubscription = this.websocketService.subscribe<MarketTransactionEvent>(
      ServiceEventType.MARKET_TRANSACTION
    ).subscribe(event => {
      console.log('[MarketComponent] Market transaction event received:', event);
      
      // Reload the current page to show the new transaction
      if (this.lastLazyEvent) {
        this.loadTransactions(this.lastLazyEvent);
      }
    });
  }

  ngOnDestroy() {
    if (this.playerSubscription) {
      this.playerSubscription.unsubscribe();
    }
    if (this.marketSubscription) {
      this.marketSubscription.unsubscribe();
    }
  }

  loadTransactions(event: TableLazyLoadEvent) {
    this.loading = true;
    this.lastLazyEvent = event; // Store for reload on WebSocket events
    
    const page = ((event.first || 0) / (event.rows || 20)) + 1;
    const pageSize = event.rows || 20;
    
    // Extract sort field and order
    let sortField: string | undefined;
    let sortOrder: number | undefined;
    
    if (event.sortField) {
      sortField = event.sortField as string;
      sortOrder = event.sortOrder || 1;
    }
    
    // Build filters object
    const filters: any = {};
    
    if (this.filterItemName) {
      filters.itemName = this.filterItemName;
    }
    
    if (this.filterAction) {
      filters.action = this.filterAction;
    }
    
    if (this.filterMinQuantity !== null) {
      filters.minQuantity = this.filterMinQuantity;
    }
    
    if (this.selectedSession?.value) {
      filters.sessionId = this.selectedSession.value;
    }
    
    this.marketService.getTransactions(page, pageSize, this.playerName || undefined, sortField, sortOrder, filters)
      .subscribe({
        next: (response: MarketResponse) => {
          this.transactions = response.results;
          this.totalRecords = response.total;
          this.loading = false;
        },
        error: (error) => {
          console.error('[MarketComponent] Error loading transactions:', error);
          this.loading = false;
        }
      });
  }

  onFilterChange(dt: any) {
    // Reload from first page when filters change
    dt.first = 0;
    dt._lazy = true;
    dt.onLazyLoad.emit(dt.createLazyLoadMetadata());
  }

  formatTimestamp(timestamp: string): string {
    // Backend sends local time, not UTC - parse as local time
    // Format: "2026-01-03T03:23:16.016228"
    const parts = timestamp.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
    if (!parts) return timestamp;
    
    const [, year, month, day, hour, minute, second] = parts;
    const date = new Date(
      parseInt(year),
      parseInt(month) - 1, // months are 0-indexed
      parseInt(day),
      parseInt(hour),
      parseInt(minute),
      parseInt(second)
    );
    
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  loadSessions() {
    this.sessionsService.getSessions(this.playerName || undefined, 1, 100).subscribe({
      next: (response) => {
        this.sessions = (response.results || []).map((session: Session) => {
          const startDate = new Date(session.started_at);
          const dateStr = startDate.toLocaleDateString('en-GB');
          const timeStr = startDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
          
          return {
            label: session.title 
              ? `${session.title} - ${dateStr} ${timeStr}`
              : `${session.player_name} - Session #${session.id} - ${dateStr} ${timeStr}`,
            value: session.id,
            session: session
          };
        });
      },
      error: (error) => {
        console.error('Error loading sessions:', error);
        this.sessions = [];
      }
    });
  }

  onSessionChange(dt: any) {
    // Reload from first page when session filter changes
    dt.first = 0;
    dt._lazy = true;
    dt.onLazyLoad.emit(dt.createLazyLoadMetadata());
  }
}
