import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ChartModule } from 'primeng/chart';
import { CheckboxModule } from 'primeng/checkbox';
import { WebSocketService } from '../../../services/websocket.service';
import { StatsService } from '../../../services/stats.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { ServiceEventType } from '../../../models/enums';
import { StatsUpdateEvent, MapStartedEvent } from '../../../models/service-events';
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
  private overlayWindow: any = null;
  private toggleInProgress: boolean = false;
  
  stats: StatsUpdateEvent | null = null;
  currentMap: MapStartedEvent | null = null;
  overlayOpen: boolean = false;
  
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
  sparklineOptions: any;
  
  constructor(
    private websocketService: WebSocketService,
    private statsService: StatsService,
    private configService: ConfigurationService
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
      
      await register('PageUp', () => {
        console.log('[Currency] Hotkey triggered - toggling stats overlay');
        this.toggleStatsOverlay();
      });
      console.log('[Currency] Global shortcut registered: PageUp');
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
  }
  
  ngOnDestroy() {
    this.statsSubscription?.unsubscribe();
    this.mapSubscription?.unsubscribe();
    this.configSubscription?.unsubscribe();
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
    
    // Trigger updates
    this.currencyPerHourSparkline = { ...this.currencyPerHourSparkline };
    this.currencyPerMapSparkline = { ...this.currencyPerMapSparkline };
    this.currentPerHourSparkline = { ...this.currentPerHourSparkline };
    this.currentCurrencySparkline = { ...this.currentCurrencySparkline };
    this.expPerHourSparkline = { ...this.expPerHourSparkline };
  }

  async toggleStatsOverlay(): Promise<void> {
    // Prevent multiple simultaneous toggles
    if (this.toggleInProgress) {
      console.log('[Currency] Toggle already in progress, ignoring');
      return;
    }
    
    this.toggleInProgress = true;
    
    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      
      // Try to get existing window by label
      const existingWindow = await WebviewWindow.getByLabel('stats-overlay');
      
      // If overlay is open or existing window found, close it
      if (existingWindow) {
        console.log('[Currency] Found existing stats overlay window, destroying...');
        try {
          await existingWindow.destroy();
          console.log('[Currency] Stats overlay window destroyed');
        } catch (e) {
          console.error('[Currency] Error destroying window:', e);
        }
        this.overlayWindow = null;
        this.overlayOpen = false;
        
        // Wait a bit to ensure window is fully destroyed
        await new Promise(resolve => setTimeout(resolve, 100));
        return;
      }

      // Otherwise, open it
      console.log('[Currency] Creating new stats overlay window');
      const isTransparent = localStorage.getItem('transparent_overlay') === 'true';
      
      // Restore saved position if available
      const savedPosition = localStorage.getItem('stats_overlay_position');
      let windowConfig: any = {
        url: '/overlay/stats',
        title: 'Stats Overlay',
        width: 400,
        height: 300,
        resizable: true,
        alwaysOnTop: true,
        decorations: !isTransparent,
        transparent: isTransparent,
        skipTaskbar: isTransparent
      };
      
      if (savedPosition) {
        try {
          const pos = JSON.parse(savedPosition);
          windowConfig.x = pos.x;
          windowConfig.y = pos.y;
          windowConfig.width = pos.width;
          windowConfig.height = pos.height;
        } catch (e) {
          console.error('[Currency] Error parsing saved position:', e);
        }
      }
      
      this.overlayWindow = new WebviewWindow('stats-overlay', windowConfig);

      this.overlayWindow.once('tauri://created', () => {
        this.overlayOpen = true;
        console.log('Stats overlay window created');
      });

      this.overlayWindow.once('tauri://error', (e: any) => {
        this.overlayOpen = false;
        this.overlayWindow = null;
        console.error('Failed to create stats overlay window:', e);
      });

      // Listen for window close event to update state
      this.overlayWindow.listen('tauri://destroyed', () => {
        this.overlayOpen = false;
        this.overlayWindow = null;
        console.log('Stats overlay window destroyed event');
      });
    } catch (error) {
      this.overlayOpen = false;
      this.overlayWindow = null;
      console.error('Error toggling stats overlay:', error);
    } finally {
      // Reset toggle lock after a short delay
      setTimeout(() => {
        this.toggleInProgress = false;
      }, 200);
    }
  }
}
