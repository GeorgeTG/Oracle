import { Component, OnInit, OnDestroy, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { SessionsService } from '../../../services/sessions.service';
import { MarketService, MarketTransaction } from '../../../services/market.service';
import { ToastService } from '../../../services/toast.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { StatsService } from '../../../services/stats.service';
import { StatsStore } from '../../../store/stats.store';
import { MapDetailComponent } from '../../shared/map-detail/map-detail';
import { DifficultyPipe } from '../../../pipes/difficulty.pipe';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { MapTile } from '../../../models/session.model';

@Component({
  selector: 'app-session',
  standalone: true,
  imports: [CommonModule, FormsModule, MapDetailComponent, DifficultyPipe, CurrencyPipe],
  templateUrl: './session.html',
  styleUrls: ['./session.css']
})
export class SessionComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  protected statsStore = inject(StatsStore);

  private sessionsService = inject(SessionsService);
  private marketService = inject(MarketService);
  private toastService = inject(ToastService);
  private configService = inject(ConfigurationService);
  private statsService = inject(StatsService);

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

  loadingStats: boolean = true;

  isEditingTitle = false;
  isEditingDescription = false;
  showMapDetail = false;
  selectedMapId: number | null = null;

  headerCollapsed = true;
  mapsCollapsed = true;
  marketCollapsed = true;

  marketTransactions: MarketTransaction[] = [];
  loadingMarketTransactions = false;

  constructor() {
    // Stop loading spinner when first stats arrive
    effect(() => {
      if (this.statsStore.lastStats() !== null) {
        this.loadingStats = false;
      }
    });
  }

  ngOnInit(): void {
    this.configService.periodicUnit$
      .pipe(takeUntil(this.destroy$))
      .subscribe(unit => {
        this.currencyLabel = `Currency / ${unit}`;
        this.expLabel = `EXP / ${unit}`;
      });

    // Subscribe to session state from service
    this.sessionsService.state$
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        this.sessionId = state.sessionId;
        this.playerName = state.playerName;
        this.title = state.title;
        this.description = state.description;
        this.currencyPerHour = state.currencyPerHour;
        this.expPerHour = state.expPerHour;
        this.totalMaps = state.totalMaps;
        this.netCurrency = state.netCurrency;
        this.maps = state.maps;
        if (this.maps.length > 0 && this.mapsCollapsed) this.mapsCollapsed = false;
        this.marketService.setCurrentSession(state.sessionId || null);
      });

    this.marketService.transactions$
      .pipe(takeUntil(this.destroy$))
      .subscribe(transactions => {
        this.marketTransactions = transactions;
        this.loadingMarketTransactions = false;
        if (this.marketTransactions.length > 0 && this.marketCollapsed) this.marketCollapsed = false;
      });

    this.sessionsService.loadActiveSession();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  saveTitle(): void {
    if (!this.sessionId) return;
    this.sessionsService.updateSession(this.sessionId, { title: this.title }).subscribe({
      next: () => { this.toastService.success('Updated', 'Title saved'); this.isEditingTitle = false; },
      error: (err) => { this.toastService.error('Error', 'Failed to save title'); console.error(err); }
    });
  }

  saveDescription(): void {
    if (!this.sessionId) return;
    this.sessionsService.updateSession(this.sessionId, { description: this.description }).subscribe({
      next: () => { this.toastService.success('Updated', 'Description saved'); this.isEditingDescription = false; },
      error: (err) => { this.toastService.error('Error', 'Failed to save description'); console.error(err); }
    });
  }

  viewMapDetails(mapId: number): void {
    this.selectedMapId = mapId;
    this.showMapDetail = true;
  }

  onMapDeleted(_mapId: number): void {
    this.sessionsService.loadActiveSession();
  }

  getDifficultyColor(difficulty: string): string {
    const colors: Record<string, string> = {
      'T8_PLUS': 'bg-red-600', 'T8_2': 'bg-red-500', 'T8_1': 'bg-orange-600',
      'T8_0': 'bg-orange-500', 'T7_2': 'bg-yellow-600', 'T7_1': 'bg-yellow-500',
      'T7_0': 'bg-green-600', 'T6': 'bg-green-500', 'T5': 'bg-blue-500',
      'T4': 'bg-blue-400', 'T3': 'bg-gray-500', 'T2': 'bg-gray-400', 'T1': 'bg-gray-300'
    };
    return colors[difficulty] || 'bg-gray-500';
  }

  toggleHeaderCollapse(): void { this.headerCollapsed = !this.headerCollapsed; }
  toggleMapsCollapse(): void { this.mapsCollapsed = !this.mapsCollapsed; }
  toggleMarketCollapse(): void { this.marketCollapsed = !this.marketCollapsed; }

  getActionColor(action: string): string {
    switch (action.toLowerCase()) {
      case 'gained': case 'bought': return 'text-green-400';
      case 'lost': case 'sold': return 'text-red-400';
      default: return 'text-gray-400';
    }
  }

  startNewSession(): void {
    this.sessionsService.startNewSession();
    this.toastService.info('Starting new session...');
  }
}
