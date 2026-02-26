import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ChartModule } from 'primeng/chart';
import { CheckboxModule } from 'primeng/checkbox';
import { WebSocketService } from '../../../services/websocket.service';
import { StatsService } from '../../../services/stats.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { OverlayService } from '../../../services/overlay.service';
import { ServiceEventType } from '../../../models/enums';
import { StatsUpdateEvent, MapStartedEvent, ItemObtainedEvent } from '../../../models/service-events';
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
  private statsSubscription?: Subscription;
  private mapSubscription?: Subscription;
  private configSubscription?: Subscription;
  private itemObtainedSubscription?: Subscription;
  stats: StatsUpdateEvent | null = null;
  currentMap: MapStartedEvent | null = null;

  // Item obtained history
  itemHistory: ItemObtainedEvent[] = [];
  maxHistoryItems: number = 50;
  
  currencyLabel: string = 'Currency / Hour';
  expLabel: string = 'EXP / Hour';
  
  // Chart data
  chartData: any;
  chartOptions: any;
  
  // Sparkline charts for tiles
  currencyPerHourSparkline: any;
  currencyPerMapSparkline: any;
  currentPerHourSparkline: any;
  currentCurrencySparkline: any;
  expPerHourSparkline: any;
  inventoryValueSparkline: any;
  sparklineOptions: any;
  
  constructor(
    private websocketService: WebSocketService,
    private statsService: StatsService,
    private configService: ConfigurationService,
    public overlayService: OverlayService
  ) {}
  
  async ngOnInit() {
    console.log('[Currency] Component initialized');
    console.log('[Currency] WebSocket connected:', this.websocketService.isConnected);
    
    this.initChart();
    
    // Register global shortcut for Page Up key
    try {
      const { register, isRegistered, unregister } = await import('@tauri-apps/plugin-global-shortcut');
      
      // Unregister if already registered (from hot reload)
      if (await isRegistered('PageUp')) {
        console.log('[Currency] PageUp already registered, unregistering first');
        await unregister('PageUp');
      }
      
      await register('PageUp', (event: any) => {
        // Only trigger on key press, not release
        if (event.state === 'Released') return;
        console.log('[Currency] Edit mode hotkey triggered');
        this.overlayService.handlePageUp();
      });
      console.log('[Currency] Global shortcut registered: PageUp');

      // Register global shortcut for Page Down key (toggle overlay)
      if (await isRegistered('PageDown')) {
        await unregister('PageDown');
      }
      await register('PageDown', (event: any) => {
        if (event.state === 'Released') return;
        console.log('[Currency] Toggle overlay hotkey triggered');
        this.overlayService.toggleOverlay();
      });
      console.log('[Currency] Global shortcut registered: PageDown');
    } catch (e) {
      console.error('[Currency] Error registering global shortcut:', e);
    }
    
    // Subscribe to configuration changes for currency label
    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.currencyLabel = `Currency / ${unit}`;
      this.expLabel = `EXP / ${unit}`;
    });
    
    // Subscribe to stats updates from service (gets last event immediately)
    this.statsSubscription = this.statsService.getStats().subscribe(event => {
      console.log('[Currency] Stats update received:', event);
      this.stats = event;
      this.updateChart();
    });
    
    // Subscribe to map events from service (gets last event immediately)
    this.mapSubscription = this.statsService.getMapEvents().subscribe(event => {
      console.log('[Currency] Map started:', event);
      this.currentMap = event;
    });

    // Subscribe to item obtained events
    this.itemObtainedSubscription = this.websocketService.subscribe<ItemObtainedEvent>(ServiceEventType.ITEM_OBTAINED).subscribe(event => {
      console.log('[Currency] Item obtained:', event);
      this.itemHistory.unshift(event);
      // Keep only the last maxHistoryItems
      if (this.itemHistory.length > this.maxHistoryItems) {
        this.itemHistory = this.itemHistory.slice(0, this.maxHistoryItems);
      }
    });
  }
  
  async ngOnDestroy() {
    this.statsSubscription?.unsubscribe();
    this.mapSubscription?.unsubscribe();
    this.configSubscription?.unsubscribe();
    this.itemObtainedSubscription?.unsubscribe();

    // Unregister global shortcuts
    try {
      const { unregister, isRegistered } = await import('@tauri-apps/plugin-global-shortcut');
      if (await isRegistered('PageUp')) await unregister('PageUp');
      if (await isRegistered('PageDown')) await unregister('PageDown');
    } catch {}

    // Close overlay window when main window closes
    await this.overlayService.closeOverlay();
  }
  
  newSession() {
    this.statsService.newSession().subscribe({
      next: (response) => {
        console.log('[Currency] New session started:', response);
      },
      error: (error) => {
        console.error('[Currency] New session failed:', error);
      }
    });
  }

  resetStats() {
    this.statsService.resetStats().subscribe({
      next: (response) => {
        console.log('[Currency] Stats reset successful:', response);
      },
      error: (error) => {
        console.error('[Currency] Stats reset failed:', error);
      }
    });
  }
  
  getValueGlowClass(value: number | undefined | null): string {
    if (value === undefined || value === null) return '';
    
    if (value < 0) {
      return 'shadow-[0_0_15px_rgba(239,68,68,0.6)] border-red-500/30';
    } else if (value === 0) {
      return 'shadow-[0_0_15px_rgba(245,158,11,0.6)] border-yellow-500/30';
    } else {
      return 'shadow-[0_0_15px_rgba(16,185,129,0.6)] border-green-500/30';
    }
  }
  
  getValueColorClass(value: number | undefined | null): string {
    if (value === undefined || value === null) return '';
    
    if (value < 0) {
      return 'text-red-400';
    } else if (value === 0) {
      return 'text-yellow-400';
    } else {
      return 'text-green-400';
    }
  }
  
  private initChart() {
    const documentStyle = getComputedStyle(document.documentElement);
    const textColor = documentStyle.getPropertyValue('--text-color') || '#ffffff';
    const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary') || '#94a3b8';
    const surfaceBorder = documentStyle.getPropertyValue('--surface-border') || '#334155';
    
    // Initialize sparkline options (minimal chart for tiles)
    this.sparklineOptions = {
      maintainAspectRatio: false,
      responsive: true,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: { 
          display: false,
          grid: { display: false }
        },
        y: { 
          display: false,
          grid: { display: false }
        }
      },
      elements: {
        point: { radius: 0 },
        line: { borderWidth: 1.5 }
      },
      layout: {
        padding: 0
      }
    };
    
    // Initialize sparkline data
    this.currencyPerHourSparkline = { labels: [], datasets: [] };
    this.currencyPerMapSparkline = { labels: [], datasets: [] };
    this.currentPerHourSparkline = { labels: [], datasets: [] };
    this.currentCurrencySparkline = { labels: [], datasets: [] };
    this.expPerHourSparkline = { labels: [], datasets: [] };
    this.inventoryValueSparkline = { labels: [], datasets: [] };
    
    this.chartData = {
      labels: [],
      datasets: []
    };
    
    this.chartOptions = {
      maintainAspectRatio: false,
      aspectRatio: 0.6,
      plugins: {
        legend: {
          labels: {
            color: textColor
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: {
          ticks: {
            color: textColorSecondary
          },
          grid: {
            color: surfaceBorder
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          ticks: {
            color: textColorSecondary
          },
          grid: {
            color: surfaceBorder
          },
          title: {
            display: true,
            text: this.currencyLabel,
            color: textColor
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    };
  }

  updateChart(): void {
    const history = this.statsService.getHistory();
    
    // Update sparkline charts for tiles
    const sparklineCount = 30; // Show last 30 points in sparklines
    const sparklineStartIdx = Math.max(0, history.labels.length - sparklineCount);
    const sparklineLabels = history.labels.slice(sparklineStartIdx);
    
    // Currency/Hour sparkline (green)
    this.currencyPerHourSparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.currencyPerHour.slice(sparklineStartIdx),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };
    
    // Currency/Map sparkline (blue)
    this.currencyPerMapSparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.currencyPerMap.slice(sparklineStartIdx),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };
    
    // Current/Hour sparkline (orange)
    this.currentPerHourSparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.currencyCurrentPerHour.slice(sparklineStartIdx),
        borderColor: '#f97316',
        backgroundColor: 'rgba(249, 115, 22, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };
    
    // Current Currency sparkline (red)
    this.currentCurrencySparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.currencyCurrentRaw.slice(sparklineStartIdx),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };
    
    // EXP/Hour sparkline (purple)
    this.expPerHourSparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.expPerHour.slice(sparklineStartIdx),
        borderColor: '#a855f7',
        backgroundColor: 'rgba(168, 85, 247, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };

    // Inventory Value sparkline (cyan)
    this.inventoryValueSparkline = {
      labels: sparklineLabels,
      datasets: [{
        data: history.inventoryValue.slice(sparklineStartIdx),
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6, 182, 212, 0.2)',
        fill: true,
        tension: 0.4
      }]
    };

    // Trigger updates
    this.currencyPerHourSparkline = { ...this.currencyPerHourSparkline };
    this.currencyPerMapSparkline = { ...this.currencyPerMapSparkline };
    this.currentPerHourSparkline = { ...this.currentPerHourSparkline };
    this.currentCurrencySparkline = { ...this.currentCurrencySparkline };
    this.expPerHourSparkline = { ...this.expPerHourSparkline };
    this.inventoryValueSparkline = { ...this.inventoryValueSparkline };
  }

}
