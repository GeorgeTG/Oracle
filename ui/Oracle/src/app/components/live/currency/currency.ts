import { Component, OnDestroy, OnInit, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ChartModule } from 'primeng/chart';
import { CheckboxModule } from 'primeng/checkbox';
import { StatsStore } from '../../../store/stats.store';
import { ItemStore } from '../../../store/item.store';
import { StatsService } from '../../../services/stats.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { OverlayService } from '../../../services/overlay.service';
import { DifficultyPipe } from '../../../pipes/difficulty.pipe';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';

@Component({
  selector: 'app-currency',
  imports: [CommonModule, ChartModule, CheckboxModule, FormsModule, DifficultyPipe, CurrencyPipe, DurationPipe],
  templateUrl: './currency.html',
  styleUrl: './currency.css',
})
export class CurrencyComponent implements OnInit, OnDestroy {
  protected statsStore = inject(StatsStore);
  protected itemStore = inject(ItemStore);

  private statsService = inject(StatsService);
  private configService = inject(ConfigurationService);
  public overlayService = inject(OverlayService);

  private configSubscription?: Subscription;

  currencyLabel: string = 'Currency / Hour';

  constructor() {
    // Re-render sparklines whenever StatsStore history updates
    effect(() => {
      this.statsStore.history(); // track signal
      this.updateChart();
    });
  }
  expLabel: string = 'EXP / Hour';

  // Chart data
  chartData: any;
  chartOptions: any;

  // Sparkline charts
  currencyPerHourSparkline: any;
  currencyPerMapSparkline: any;
  currentPerHourSparkline: any;
  currentCurrencySparkline: any;
  expPerHourSparkline: any;
  inventoryValueSparkline: any;
  sparklineOptions: any;

  // Template-compatible getters
  get stats() { return this.statsStore.lastStats(); }
  get currentMap() { return this.statsStore.lastMap(); }
  get itemHistory() { return this.itemStore.recentItems(); }

  async ngOnInit() {
    console.log('[Currency] Component initialized');

    this.initChart();

    // Register global shortcuts
    try {
      const { register, isRegistered, unregister } = await import('@tauri-apps/plugin-global-shortcut');
      if (await isRegistered('PageUp')) await unregister('PageUp');
      await register('PageUp', (event: any) => {
        if (event.state === 'Released') return;
        this.overlayService.handlePageUp();
      });
      if (await isRegistered('PageDown')) await unregister('PageDown');
      await register('PageDown', (event: any) => {
        if (event.state === 'Released') return;
        this.overlayService.toggleOverlay();
      });
    } catch (e) {
      console.error('[Currency] Error registering global shortcut:', e);
    }

    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.currencyLabel = `Currency / ${unit}`;
      this.expLabel = `EXP / ${unit}`;
    });

    // effect() in constructor handles chart updates reactively
  }

  async ngOnDestroy() {
    this.configSubscription?.unsubscribe();
    try {
      const { unregister, isRegistered } = await import('@tauri-apps/plugin-global-shortcut');
      if (await isRegistered('PageUp')) await unregister('PageUp');
      if (await isRegistered('PageDown')) await unregister('PageDown');
    } catch {}
    await this.overlayService.closeOverlay();
  }

  newSession() {
    this.statsService.newSession().subscribe({
      next: (r) => console.log('[Currency] New session:', r),
      error: (e) => console.error('[Currency] New session failed:', e),
    });
  }

  resetStats() {
    this.statsService.resetStats().subscribe({
      next: (r) => console.log('[Currency] Stats reset:', r),
      error: (e) => console.error('[Currency] Stats reset failed:', e),
    });
  }

  getValueGlowClass(value: number | undefined | null): string {
    if (value === undefined || value === null) return '';
    if (value < 0) return 'shadow-[0_0_15px_rgba(239,68,68,0.6)] border-red-500/30';
    if (value === 0) return 'shadow-[0_0_15px_rgba(245,158,11,0.6)] border-yellow-500/30';
    return 'shadow-[0_0_15px_rgba(16,185,129,0.6)] border-green-500/30';
  }

  getValueColorClass(value: number | undefined | null): string {
    if (value === undefined || value === null) return '';
    if (value < 0) return 'text-red-400';
    if (value === 0) return 'text-yellow-400';
    return 'text-green-400';
  }

  private initChart() {
    const documentStyle = getComputedStyle(document.documentElement);
    const textColor = documentStyle.getPropertyValue('--text-color') || '#ffffff';
    const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary') || '#94a3b8';
    const surfaceBorder = documentStyle.getPropertyValue('--surface-border') || '#334155';

    this.sparklineOptions = {
      maintainAspectRatio: false, responsive: true, animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false, grid: { display: false } },
        y: { display: false, grid: { display: false } }
      },
      elements: { point: { radius: 0 }, line: { borderWidth: 1.5 } },
      layout: { padding: 0 }
    };

    this.currencyPerHourSparkline = { labels: [], datasets: [] };
    this.currencyPerMapSparkline = { labels: [], datasets: [] };
    this.currentPerHourSparkline = { labels: [], datasets: [] };
    this.currentCurrencySparkline = { labels: [], datasets: [] };
    this.expPerHourSparkline = { labels: [], datasets: [] };
    this.inventoryValueSparkline = { labels: [], datasets: [] };

    this.chartData = { labels: [], datasets: [] };
    this.chartOptions = {
      maintainAspectRatio: false, aspectRatio: 0.6,
      plugins: {
        legend: { labels: { color: textColor } },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: { ticks: { color: textColorSecondary }, grid: { color: surfaceBorder } },
        y: {
          type: 'linear', display: true, position: 'left',
          ticks: { color: textColorSecondary }, grid: { color: surfaceBorder },
          title: { display: true, text: this.currencyLabel, color: textColor }
        }
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false }
    };
  }

  updateChart(): void {
    const history = this.statsStore.history();
    const sparklineCount = 30;
    const startIdx = Math.max(0, history.labels.length - sparklineCount);
    const labels = history.labels.slice(startIdx);

    const mkSparkline = (data: number[], color: string, rgba: string) => ({
      labels,
      datasets: [{ data: data.slice(startIdx), borderColor: color, backgroundColor: rgba, fill: true, tension: 0.4 }]
    });

    this.currencyPerHourSparkline = mkSparkline(history.currencyPerHour, '#10b981', 'rgba(16,185,129,0.2)');
    this.currencyPerMapSparkline = mkSparkline(history.currencyPerMap, '#3b82f6', 'rgba(59,130,246,0.2)');
    this.currentPerHourSparkline = mkSparkline(history.currencyCurrentPerHour, '#f97316', 'rgba(249,115,22,0.2)');
    this.currentCurrencySparkline = mkSparkline(history.currencyCurrentRaw, '#ef4444', 'rgba(239,68,68,0.2)');
    this.expPerHourSparkline = mkSparkline(history.expPerHour, '#a855f7', 'rgba(168,85,247,0.2)');
    this.inventoryValueSparkline = mkSparkline(history.inventoryValue, '#06b6d4', 'rgba(6,182,212,0.2)');
  }
}
