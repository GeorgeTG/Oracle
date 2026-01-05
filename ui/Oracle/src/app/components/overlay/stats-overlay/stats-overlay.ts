import { Component, OnInit, OnDestroy, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { StatsService } from '../../../services/stats.service';
import { WebSocketService } from '../../../services/websocket.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { StatsUpdateEvent } from '../../../models/service-events';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';
import { ChartModule } from 'primeng/chart';

@Component({
  selector: 'app-stats-overlay',
  imports: [CommonModule, CurrencyPipe, DurationPipe, ChartModule],
  templateUrl: './stats-overlay.html',
  styleUrl: './stats-overlay.css',
})
export class StatsOverlayComponent implements OnInit, OnDestroy {
  private statsSubscription?: Subscription;
  private configSubscription?: Subscription;
  private destroyListener?: any;
  
  stats: StatsUpdateEvent | null = null;
  
  currencyLabel: string = 'Currency / Hour';
  expLabel: string = 'EXP / Hour';
  currentUnit: string = 'Hour';
  
  // Gauge chart
  gaugeData: any;
  gaugeOptions: any;

  @HostBinding('class.transparent-mode')
  get isTransparentMode(): boolean {
    return this.configService.isTransparentOverlay();
  }

  constructor(
    private statsService: StatsService,
    private websocketService: WebSocketService,
    private configService: ConfigurationService
  ) {}
  
  async ngOnInit() {
    // Initialize gauge chart
    this.initGaugeChart();
    
    // Subscribe to configuration changes for currency label
    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.currentUnit = unit;
      this.currencyLabel = `Currency / ${unit}`;
      this.expLabel = `EXP / ${unit}`;
    });
    
    // Apply transparent background to html element if transparent mode is enabled
    if (this.isTransparentMode) {
      document.documentElement.style.backgroundColor = 'transparent';
      document.body.style.backgroundColor = 'transparent';
      
      // Set window decorations to false
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        const appWindow = getCurrentWindow();
        await appWindow.setDecorations(false);
        await appWindow.setShadow(false);
      } catch (error) {
        console.error('Error setting window decorations:', error);
      }
    }
    
    // Track window position changes to save them
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      const appWindow = getCurrentWindow();
      
      // Save position when window is moved
      await appWindow.listen('tauri://move', async () => {
        const position = await appWindow.outerPosition();
        const size = await appWindow.outerSize();
        localStorage.setItem('stats_overlay_position', JSON.stringify({
          x: position.x,
          y: position.y,
          width: size.width,
          height: size.height
        }));
      });
      
      // Save size when window is resized
      await appWindow.listen('tauri://resize', async () => {
        const position = await appWindow.outerPosition();
        const size = await appWindow.outerSize();
        localStorage.setItem('stats_overlay_position', JSON.stringify({
          x: position.x,
          y: position.y,
          width: size.width,
          height: size.height
        }));
      });
    } catch (error) {
      console.error('Error setting up position tracking:', error);
    }
    
    // Listen for beforeunload to cleanup properly
    this.setupWindowCleanup();
    
    // Subscribe to stats updates from service
    this.statsSubscription = this.statsService.getStats().subscribe(event => {
      this.stats = event;
      if (event) {
        this.updateGaugeChart(event.currency_per_hour || 0);
      }
    });
    
    // Initialize gauge chart
    this.initGaugeChart();
  }
  
  private async setupWindowCleanup() {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      const appWindow = getCurrentWindow();
      
      // Listen for window destroy event
      this.destroyListener = await appWindow.onCloseRequested(async (event) => {
        console.log('[StatsOverlay] Window close requested - cleaning up');
        // Cleanup before window closes
        await this.cleanup();
      });
    } catch (error) {
      console.error('Error setting up window cleanup:', error);
    }
  }
  
  private async cleanup() {
    console.log('[StatsOverlay] Cleaning up resources');
    
    // Unsubscribe from stats
    if (this.statsSubscription) {
      this.statsSubscription.unsubscribe();
      this.statsSubscription = undefined;
    }
    
    // NOTE: We don't disconnect WebSocket here because it's a singleton service
    // shared across all windows. The WebSocket will be cleaned up when the 
    // Angular application is destroyed (when the window closes).
    
    // Reset background
    if (this.isTransparentMode) {
      document.documentElement.style.backgroundColor = '';
      document.body.style.backgroundColor = '';
    }
  }

  async ngOnDestroy() {
    console.log('[StatsOverlay] Component destroying');
    
    // Unsubscribe from config
    if (this.configSubscription) {
      this.configSubscription.unsubscribe();
    }
    
    // Unlisten from window events
    if (this.destroyListener) {
      this.destroyListener();
    }
    
    // Cleanup resources
    await this.cleanup();
  }

  formatNumber(value: number, decimals: number = 2): string {
    return value.toFixed(decimals);
  }

  formatTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  }

  getValueGlowClass(value: number): string {
    if (value > 0) {
      return 'shadow-[0_0_15px_rgba(16,185,129,0.6)] border-green-500';
    } else if (value < 0) {
      return 'shadow-[0_0_15px_rgba(239,68,68,0.6)] border-red-500';
    }
    return 'shadow-[0_0_15px_rgba(245,158,11,0.6)] border-yellow-500';
  }
  
  private initGaugeChart(): void {
    const documentStyle = getComputedStyle(document.documentElement);
    
    this.gaugeData = {
      datasets: [{
        data: [0, 100],
        backgroundColor: [
          documentStyle.getPropertyValue('--green-500') || '#22c55e',
          documentStyle.getPropertyValue('--surface-700') || '#374151'
        ],
        borderWidth: 0
      }]
    };
    
    this.gaugeOptions = {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      rotation: -90,
      circumference: 180,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          enabled: false
        }
      }
    };
  }
  
  private updateGaugeChart(value: number): void {
    // Normalize to 0-100 scale (assuming max ~500/h is 100%)
    const maxValue = 500;
    const percentage = Math.min(Math.abs(value) / maxValue * 100, 100);
    
    const documentStyle = getComputedStyle(document.documentElement);
    let fillColor: string;
    
    if (value > 0) {
      fillColor = documentStyle.getPropertyValue('--green-500') || '#22c55e';
    } else if (value < 0) {
      fillColor = documentStyle.getPropertyValue('--red-500') || '#ef4444';
    } else {
      fillColor = documentStyle.getPropertyValue('--yellow-500') || '#eab308';
    }
    
    this.gaugeData = {
      datasets: [{
        data: [percentage, 100 - percentage],
        backgroundColor: [
          fillColor,
          documentStyle.getPropertyValue('--surface-700') || '#374151'
        ],
        borderWidth: 0
      }]
    };
  }
}
