import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DashboardService, DashboardOverview, HeroStats, TopItem, EfficiencyPeriod, EfficiencySummary } from '../../../services/dashboard.service';
import { SessionsService } from '../../../services/sessions.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { TableModule } from 'primeng/table';
import { Select } from 'primeng/select';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-tracking-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, TableModule, Select, CurrencyPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit, OnDestroy {
  // Filters
  selectedPlayerFilter: string | null = null;
  players: { label: string; value: string | null }[] = [];
  selectedGroupBy: string = 'day';
  groupByOptions = [
    { label: 'Daily', value: 'day' },
    { label: 'Weekly', value: 'week' },
    { label: 'Monthly', value: 'month' },
  ];

  // Data
  overview: DashboardOverview | null = null;
  heroes: HeroStats[] = [];
  topItems: TopItem[] = [];
  efficiencyPeriods: EfficiencyPeriod[] = [];
  efficiencySummary: EfficiencySummary | null = null;

  // Loading states
  loadingOverview = false;
  loadingHeroes = false;
  loadingItems = false;
  loadingEfficiency = false;
  loadingPlayers = false;

  periodicUnitShort: string = 'h';
  private configSubscription?: Subscription;

  constructor(
    private dashboardService: DashboardService,
    private sessionsService: SessionsService,
    private configService: ConfigurationService
  ) {}

  ngOnInit() {
    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.periodicUnitShort = unit === 'Hour' ? 'h' : 'm';
    });

    this.loadPlayers();
    this.loadAll();
  }

  ngOnDestroy() {
    this.configSubscription?.unsubscribe();
  }

  loadPlayers() {
    this.loadingPlayers = true;
    this.sessionsService.getPlayers().subscribe({
      next: (response) => {
        this.players = [
          { label: 'All Players', value: null },
          ...response.players.map(p => ({ label: p, value: p }))
        ];
        this.loadingPlayers = false;
      },
      error: () => {
        this.players = [{ label: 'All Players', value: null }];
        this.loadingPlayers = false;
      }
    });
  }

  onFilterChange() {
    this.loadAll();
  }

  onGroupByChange() {
    this.loadEfficiency();
  }

  loadAll() {
    this.loadOverview();
    this.loadHeroes();
    this.loadItems();
    this.loadEfficiency();
  }

  loadOverview() {
    this.loadingOverview = true;
    const player = this.selectedPlayerFilter || undefined;
    this.dashboardService.getOverview(player).subscribe({
      next: (data) => {
        this.overview = data;
        this.loadingOverview = false;
      },
      error: () => { this.loadingOverview = false; }
    });
  }

  loadHeroes() {
    this.loadingHeroes = true;
    this.dashboardService.getHeroes().subscribe({
      next: (data) => {
        this.heroes = data.heroes;
        this.loadingHeroes = false;
      },
      error: () => { this.loadingHeroes = false; }
    });
  }

  loadItems() {
    this.loadingItems = true;
    const player = this.selectedPlayerFilter || undefined;
    this.dashboardService.getItems(player).subscribe({
      next: (data) => {
        this.topItems = data.items;
        this.loadingItems = false;
      },
      error: () => { this.loadingItems = false; }
    });
  }

  loadEfficiency() {
    this.loadingEfficiency = true;
    const player = this.selectedPlayerFilter || undefined;
    this.dashboardService.getEfficiency(player, undefined, undefined, this.selectedGroupBy).subscribe({
      next: (data) => {
        this.efficiencyPeriods = data.periods;
        this.efficiencySummary = data.summary;
        this.loadingEfficiency = false;
      },
      error: () => { this.loadingEfficiency = false; }
    });
  }

  formatDate(dateString: string | null): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  formatHours(hours: number): string {
    if (hours < 1) {
      return `${Math.round(hours * 60)}m`;
    }
    return `${hours.toFixed(1)}h`;
  }
}
