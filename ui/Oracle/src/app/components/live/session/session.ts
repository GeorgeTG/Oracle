import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { SessionsService } from '../../../services/sessions.service';
import { WebSocketService } from '../../../services/websocket.service';
import { MarketService, MarketTransaction } from '../../../services/market.service';
import { ToastService } from '../../../services/toast.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { StatsService } from '../../../services/stats.service';
import { MapDetailComponent } from '../../shared/map-detail/map-detail';
import { DifficultyPipe } from '../../../pipes/difficulty.pipe';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { MapTile } from '../../../models/session.model';
import { ServiceEventType } from '../../../models/enums';
import { SessionRestoreEvent } from '../../../models/service-events';

@Component({
  selector: 'app-session',
  standalone: true,
  imports: [CommonModule, FormsModule, MapDetailComponent, DifficultyPipe, CurrencyPipe],
  templateUrl: './session.html',
  styleUrls: ['./session.css']
})
export class SessionComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  // Component state (synchronized from service)
  sessionId?: number;
  playerName: string = '';
  title: string = '';
  description: string = '';
  currencyPerHour: number = 0;
  expPerHour: number = 0;
  totalMaps: number = 0;
  netCurrency: number = 0;

  currencyLabel: string = 'Currency / Hour';
  expLabel: string = 'EXP / Hour';
  maps: MapTile[] = [];
  
  // Loading state
  loadingStats: boolean = true;
  
  // UI state
  isEditingTitle = false;
  isEditingDescription = false;
  showMapDetail = false;
  selectedMapId: number | null = null;
  
  // Collapsible sections
  headerCollapsed = true;
  mapsCollapsed = true;
  marketCollapsed = true;
  
  // Market transactions
  marketTransactions: MarketTransaction[] = [];
  loadingMarketTransactions = false;

  constructor(
    private sessionsService: SessionsService,
    private websocketService: WebSocketService,
    private marketService: MarketService,
    private toastService: ToastService,
    private configService: ConfigurationService,
    private statsService: StatsService
  ) {}

  ngOnInit(): void {
    // Subscribe to configuration changes for currency label
    this.configService.periodicUnit$
      .pipe(takeUntil(this.destroy$))
      .subscribe(unit => {
        this.currencyLabel = `Currency / ${unit}`;
        this.expLabel = `EXP / ${unit}`;
      });
    
    // Subscribe to session restore events and reload page
    this.websocketService.subscribe<SessionRestoreEvent>(ServiceEventType.SESSION_RESTORE)
      .pipe(takeUntil(this.destroy$))
      .subscribe(event => {
        console.log('[Session] Session restore event received, reloading page...');
        window.location.reload();
      });
    
    // Subscribe to session state from service
    this.sessionsService.state$
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        console.log('[Session] State updated from service:', state);
        // Update component state from service
        this.sessionId = state.sessionId;
        this.playerName = state.playerName;
        this.title = state.title;
        this.description = state.description;
        this.currencyPerHour = state.currencyPerHour;
        this.expPerHour = state.expPerHour;
        this.totalMaps = state.totalMaps;
        this.netCurrency = state.netCurrency;
        this.maps = state.maps;
        
        // Auto-expand if not empty
        if (this.maps.length > 0 && this.mapsCollapsed) {
          this.mapsCollapsed = false;
        }
        
        // Update market service with current session
        this.marketService.setCurrentSession(state.sessionId || null);
      });
    
    // Subscribe to stats updates to stop loading when first update arrives
    this.statsService.getStats()
      .pipe(takeUntil(this.destroy$))
      .subscribe(stats => {
        if (stats) {
          console.log('[Session] Stats update received, stopping loading');
          this.loadingStats = false;
        }
      });
    
    // Subscribe to market transactions from service
    this.marketService.transactions$
      .pipe(takeUntil(this.destroy$))
      .subscribe(transactions => {
        console.log('[Session] Market transactions updated:', transactions);
        this.marketTransactions = transactions;
        this.loadingMarketTransactions = false;
        
        // Auto-expand if not empty
        if (this.marketTransactions.length > 0 && this.marketCollapsed) {
          this.marketCollapsed = false;
        }
      });
    
    // Load active session on init
    this.sessionsService.loadActiveSession();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  saveTitle(): void {
    if (!this.sessionId) return;
    
    this.sessionsService.updateSession(this.sessionId, { title: this.title }).subscribe({
      next: () => {
        this.toastService.success('Updated', 'Title saved');
        this.isEditingTitle = false;
      },
      error: (err) => {
        this.toastService.error('Error', 'Failed to save title');
        console.error('Failed to save title:', err);
      }
    });
  }

  saveDescription(): void {
    if (!this.sessionId) return;
    
    this.sessionsService.updateSession(this.sessionId, { description: this.description }).subscribe({
      next: () => {
        this.toastService.success('Updated', 'Description saved');
        this.isEditingDescription = false;
      },
      error: (err) => {
        this.toastService.error('Error', 'Failed to save description');
        console.error('Failed to save description:', err);
      }
    });
  }

  private formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  viewMapDetails(mapId: number): void {
    this.selectedMapId = mapId;
    this.showMapDetail = true;
  }

  onMapDeleted(mapId: number): void {
    console.log('[Session] onMapDeleted called - reloading session');
    // Reload session to get updated stats
    this.sessionsService.loadActiveSession();
  }

  getDifficultyColor(difficulty: string): string {
    const colors: Record<string, string> = {
      'T8_PLUS': 'bg-red-600',
      'T8_2': 'bg-red-500',
      'T8_1': 'bg-orange-600',
      'T8_0': 'bg-orange-500',
      'T7_2': 'bg-yellow-600',
      'T7_1': 'bg-yellow-500',
      'T7_0': 'bg-green-600',
      'T6': 'bg-green-500',
      'T5': 'bg-blue-500',
      'T4': 'bg-blue-400',
      'T3': 'bg-gray-500',
      'T2': 'bg-gray-400',
      'T1': 'bg-gray-300'
    };
    return colors[difficulty] || 'bg-gray-500';
  }
  
  toggleHeaderCollapse(): void {
    this.headerCollapsed = !this.headerCollapsed;
  }
  
  toggleMapsCollapse(): void {
    this.mapsCollapsed = !this.mapsCollapsed;
  }
  
  toggleMarketCollapse(): void {
    this.marketCollapsed = !this.marketCollapsed;
  }
  
  getActionColor(action: string): string {
    switch (action.toLowerCase()) {
      case 'gained':
      case 'bought':
        return 'text-green-400';
      case 'lost':
      case 'sold':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  }

  startNewSession(): void {
    this.sessionsService.startNewSession();
    this.toastService.info('Starting new session...');
  }
}
