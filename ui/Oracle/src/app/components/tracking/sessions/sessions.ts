import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SessionsService, SessionListItem, SessionDetails } from '../../../services/sessions.service';
import { PlayerService } from '../../../services/player.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { DataView } from 'primeng/dataview';
import { Card } from 'primeng/card';
import { Tag } from 'primeng/tag';
import { Select } from 'primeng/select';
import { SessionDetailsComponent } from '../../shared/session-details/session-details';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-tracking-sessions',
  standalone: true,
  imports: [CommonModule, FormsModule, DataView, Card, Tag, Select, SessionDetailsComponent, CurrencyPipe, DurationPipe],
  templateUrl: './sessions.html',
  styleUrl: './sessions.css',
})
export class SessionsComponent implements OnInit, OnDestroy {
  sessions: SessionListItem[] = [];
  loading: boolean = false;
  playerName: string | null = null;
  selectedPlayerFilter: string | null = null;
  players: {label: string, value: string | null}[] = [];
  loadingPlayers: boolean = false;
  periodicUnitShort: string = 'h';
  private playerSubscription?: Subscription;
  private configSubscription?: Subscription;
  
  // Session details dialog
  detailsDialogVisible: boolean = false;
  sessionDetails: SessionDetails | null = null;
  selectedSessionTitle: string = '';
  loadingDetails: boolean = false;
  
  // Pagination
  totalRecords: number = 0;
  page: number = 1;
  pageSize: number = 20;

  constructor(
    private sessionsService: SessionsService,
    private playerService: PlayerService,
    private configService: ConfigurationService
  ) {}

  ngOnInit() {
    this.playerName = this.playerService.getName();
    this.selectedPlayerFilter = this.playerName;
    
    this.playerSubscription = this.playerService.getNameObservable().subscribe(name => {
      this.playerName = name;
      if (!this.selectedPlayerFilter) {
        this.selectedPlayerFilter = name;
      }
    });
    
    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.periodicUnitShort = unit === 'Hour' ? 'h' : 'm';
    });
    
    this.loadPlayers();
    this.loadSessions();
  }

  ngOnDestroy() {
    this.playerSubscription?.unsubscribe();
    this.configSubscription?.unsubscribe();
  }

  loadPlayers() {
    this.loadingPlayers = true;
    this.sessionsService.getPlayers().subscribe({
      next: (response) => {
        this.players = [
          {label: 'All Players', value: null},
          ...response.players.map(p => ({label: p, value: p}))
        ];
        this.loadingPlayers = false;
      },
      error: (error) => {
        console.error('[SessionsComponent] Error loading players:', error);
        this.players = [{label: 'All Players', value: null}];
        this.loadingPlayers = false;
      }
    });
  }

  onPlayerFilterChange() {
    this.page = 1;
    this.loadSessions();
  }

  loadSessions() {
    this.loading = true;
    const playerFilter = this.selectedPlayerFilter || undefined;
    console.log('[SessionsComponent] Loading sessions with filter:', playerFilter, 'page:', this.page);
    this.sessionsService.getSessions(playerFilter, this.page, this.pageSize).subscribe({
      next: (response) => {
        console.log('[SessionsComponent] Sessions count:', response.results?.length);
        this.sessions = response.results || [];
        this.totalRecords = response.total || 0;
        this.loading = false;
      },
      error: (error) => {
        console.error('[SessionsComponent] Error loading sessions:', error);
        this.sessions = [];
        this.totalRecords = 0;
        this.loading = false;
      }
    });
  }

  onPageChange(event: any) {
    this.page = event.page + 1;
    this.pageSize = event.rows;
    this.loadSessions();
  }

  openSessionDetails(session: SessionListItem) {
    this.selectedSessionTitle = session.title;
    this.detailsDialogVisible = true;
    this.loadSessionDetails(session.id);
  }

  loadSessionDetails(sessionId: number) {
    this.loadingDetails = true;
    this.sessionsService.getSessionDetails(sessionId).subscribe({
      next: (details) => {
        this.sessionDetails = details;
        this.loadingDetails = false;
      },
      error: (error) => {
        console.error('Error loading session details:', error);
        this.loadingDetails = false;
      }
    });
  }

  getSessionDuration(session: SessionListItem): number {
    if (!session.ended_at) return 0;
    const start = new Date(session.started_at).getTime();
    const end = new Date(session.ended_at).getTime();
    return (end - start) / 1000;
  }

  getCurrencyClass(value: number): string {
    return value >= 0 ? 'text-green-400' : 'text-red-400';
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
