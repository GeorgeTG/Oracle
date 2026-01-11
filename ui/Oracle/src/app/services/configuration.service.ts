import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export type PeriodicUnit = 'Hour' | 'Minute';

export interface ConfigurationState {
  wsIp: string;
  wsPort: string;
  transparentOverlay: boolean;
  showDataPerMinute: boolean;
  aggregateNumbers: boolean;
}

/**
 * ConfigurationService - Centralized configuration management
 * 
 * This service manages all application configuration settings using localStorage internally.
 * It provides reactive observables for configuration changes and utility methods for
 * common configuration-related tasks.
 * 
 * Features:
 * - Reactive configuration changes via observables
 * - Automatic localStorage synchronization
 * - Utility methods for periodic value conversion (fe/h ↔ fe/m)
 * - WebSocket and API URL generation
 * - Type-safe configuration state
 * 
 * Usage:
 * ```typescript
 * // Subscribe to configuration changes
 * configService.config$.subscribe(config => {...});
 * 
 * // Get periodic unit observable
 * configService.periodicUnit$.subscribe(unit => {...}); // "Hour" | "Minute"
 * 
 * // Convert periodic values
 * const converted = configService.convertPeriodicValue(120); // 120 or 2 based on config
 * 
 * // Format periodic values
 * const formatted = configService.formatPeriodicValue(120); // "+120.00fe/h" or "+2.00fe/m"
 * ```
 */
@Injectable({
  providedIn: 'root'
})
export class ConfigurationService {
  private readonly DEFAULT_CONFIG: ConfigurationState = {
    wsIp: '127.0.0.1',
    wsPort: '8000',
    transparentOverlay: false,
    showDataPerMinute: false,
    aggregateNumbers: false
  };

  private configSubject = new BehaviorSubject<ConfigurationState>(this.DEFAULT_CONFIG);
  public config$: Observable<ConfigurationState> = this.configSubject.asObservable();

  // Observable for the periodic unit ("Hour" or "Minute")
  public periodicUnit$: Observable<PeriodicUnit> = this.config$.pipe(
    map(config => config.showDataPerMinute ? 'Minute' : 'Hour')
  );

  constructor() {
    this.loadFromLocalStorage();
  }

  /**
   * Load configuration from localStorage
   */
  private loadFromLocalStorage(): void {
    const config: ConfigurationState = {
      wsIp: localStorage.getItem('ws_ip') || this.DEFAULT_CONFIG.wsIp,
      wsPort: localStorage.getItem('ws_port') || this.DEFAULT_CONFIG.wsPort,
      transparentOverlay: localStorage.getItem('transparent_overlay') === 'true',
      showDataPerMinute: localStorage.getItem('show_data_per_minute') === 'true',
      aggregateNumbers: localStorage.getItem('aggregate_numbers') === 'true'
    };
    this.configSubject.next(config);
  }

  /**
   * Save configuration to localStorage and emit changes
   */
  public saveConfiguration(config: Partial<ConfigurationState>): void {
    const currentConfig = this.configSubject.value;
    const newConfig = { ...currentConfig, ...config };

    // Save to localStorage
    localStorage.setItem('ws_ip', newConfig.wsIp);
    localStorage.setItem('ws_port', newConfig.wsPort);
    localStorage.setItem('transparent_overlay', newConfig.transparentOverlay.toString());
    localStorage.setItem('show_data_per_minute', newConfig.showDataPerMinute.toString());
    localStorage.setItem('aggregate_numbers', newConfig.aggregateNumbers.toString());

    // Emit new state
    this.configSubject.next(newConfig);
  }

  /**
   * Get current configuration snapshot
   */
  public getConfig(): ConfigurationState {
    return this.configSubject.value;
  }

  /**
   * Get WebSocket IP
   */
  public getWsIp(): string {
    return this.configSubject.value.wsIp;
  }

  /**
   * Get WebSocket Port
   */
  public getWsPort(): string {
    return this.configSubject.value.wsPort;
  }

  /**
   * Get WebSocket URL
   */
  public getWsUrl(): string {
    const config = this.configSubject.value;
    return `ws://${config.wsIp}:${config.wsPort}/ws`;
  }

  /**
   * Get API URL
   */
  public getApiUrl(): string {
    const config = this.configSubject.value;
    return `http://${config.wsIp}:${config.wsPort}`;
  }

  /**
   * Check if transparent overlay is enabled
   */
  public isTransparentOverlay(): boolean {
    return this.configSubject.value.transparentOverlay;
  }

  /**
   * Check if data should be shown per minute
   */
  public isShowDataPerMinute(): boolean {
    return this.configSubject.value.showDataPerMinute;
  }

  /**
   * Get periodic unit ("Hour" or "Minute")
   */
  public getPeriodicUnit(): PeriodicUnit {
    return this.configSubject.value.showDataPerMinute ? 'Minute' : 'Hour';
  }

  /**
   * Convert periodic value based on configuration
   * Divides by 60 only if showDataPerMinute is true
   */
  public convertPeriodicValue(value: number): number {
    return this.configSubject.value.showDataPerMinute ? value / 60 : value;
  }

  /**
   * Aggregate large numbers to K (thousands) or M (millions)
   * @param value - The value to aggregate
   * @param decimals - Number of decimal places (default: 2)
   * @returns Aggregated string like "22.32K" or "1.26M"
   */
  private aggregateValue(value: number, decimals: number = 2): string {
    const absValue = Math.abs(value);
    
    // When aggregating, use at least 1 decimal for clarity
    const effectiveDecimals = Math.max(1, decimals);
    
    if (absValue >= 1000000000) {
      // Billions
      return (value / 1000000000).toFixed(effectiveDecimals) + 'B';
    } else if (absValue >= 1000000) {
      // Millions
      return (value / 1000000).toFixed(effectiveDecimals) + 'M';
    } else if (absValue >= 1000) {
      // Thousands
      return (value / 1000).toFixed(effectiveDecimals) + 'K';
    } else {
      // Less than 1000, show as is with original decimals
      return value.toFixed(decimals);
    }
  }

  /**
   * Format value as string with unit (non-periodic)
   * @param value - The value to format
   * @param unit - The unit symbol (e.g., "fe" for currency, "exp" for experience)
   * @param decimals - Number of decimal places (default: 2)
   * @returns Formatted string like "+10.50 fe" or "+1234 exp" or "+22.32K fe"
   */
  public formatValue(value: number, unit: string = 'fe', decimals: number = 2): string {
    const displayValue = value;
    
    const sign = displayValue >= 0 ? '+' : '';
    const formattedNumber = this.configSubject.value.aggregateNumbers 
      ? this.aggregateValue(displayValue, decimals)
      : displayValue.toFixed(decimals);
    
    return `${sign}${formattedNumber} ${unit}`;
  }

  /**
   * Format periodic value as string with unit
   * @param value - The value to format
   * @param unit - The unit symbol (e.g., "fe" for currency, "exp" for experience)
   * @param decimals - Number of decimal places (default: 2)
   * @param prefix - Optional prefix before the value
   * @returns Formatted string like "+10.50 fe/h" or "+0.18 fe/m" or "+22.32K exp/h"
   */
  public formatPeriodicValue(value: number, unit: string = 'fe', decimals: number = 2, prefix: string = ''): string {
    const displayValue = value;
    
    const converted = this.convertPeriodicValue(displayValue);
    const periodicUnit = this.getPeriodicUnit();
    const sign = displayValue >= 0 ? '+' : '';
    const formattedNumber = this.configSubject.value.aggregateNumbers
      ? this.aggregateValue(converted, decimals)
      : converted.toFixed(decimals);
    
    return `${prefix}${sign}${formattedNumber} ${unit}/${periodicUnit === 'Hour' ? 'h' : 'm'}`;
  }

  /**
   * Get periodic label for display
   * @param baseLabel - The base label (e.g., "Currency", "EXP")
   * @returns Label like "Currency / Hour" or "EXP / Minute"
   */
  public getPeriodicLabel(baseLabel: string = 'Currency'): string {
    const unit = this.getPeriodicUnit();
    return `${baseLabel} / ${unit}`;
  }
}
