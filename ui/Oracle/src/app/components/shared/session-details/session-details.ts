import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SessionDetails } from '../../../services/sessions.service';
import { Dialog } from 'primeng/dialog';
import { Tag } from 'primeng/tag';
import { Tabs } from 'primeng/tabs';
import { InputText } from 'primeng/inputtext';
import { Textarea } from 'primeng/textarea';
import { MapDetailComponent } from '../map-detail/map-detail';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';
import { TabList } from 'primeng/tabs';
import { Tab } from 'primeng/tabs';
import { TabPanels } from 'primeng/tabs';
import { TabPanel } from 'primeng/tabs';

@Component({
  selector: 'app-session-details',
  standalone: true,
  imports: [CommonModule, FormsModule, Dialog, Tag, Tabs, TabList, Tab, TabPanels, TabPanel, MapDetailComponent, CurrencyPipe, DurationPipe, InputText, Textarea],
  templateUrl: './session-details.html',
  styleUrl: './session-details.css',
})
export class SessionDetailsComponent {
  @Input() visible: boolean = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Input() sessionDetails: SessionDetails | null = null;
  @Input() sessionTitle: string = '';

  mapDetailVisible = false;
  selectedMapId: number | null = null;

  openMapDetail(mapId: number) {
    this.selectedMapId = mapId;
    this.mapDetailVisible = true;
  }

  // Computed statistics from maps and market data
  get mapsCurrency(): number {
    if (!this.sessionDetails?.maps) return 0;
    return this.sessionDetails.maps.reduce((sum, map) => sum + map.currency_gained, 0);
  }

  get marketCurrency(): number {
    if (!this.sessionDetails?.market_transactions) return 0;
    // Total value already has correct sign from backend (positive for gained, negative for lost)
    return this.sessionDetails.market_transactions.reduce((sum, tx) => sum + tx.total_value, 0);
  }

  get totalCurrency(): number {
    return this.mapsCurrency + this.marketCurrency;
  }

  get currencyPerHour(): number {
    if (!this.sessionDetails?.duration_seconds || this.sessionDetails.duration_seconds === 0) return 0;
    const hours = this.sessionDetails.duration_seconds / 3600;
    return this.totalCurrency / hours;
  }

  get currencyPerMap(): number {
    if (!this.sessionDetails?.maps || this.sessionDetails.maps.length === 0) return 0;
    return this.mapsCurrency / this.sessionDetails.maps.length;
  }

  onHide() {
    this.visible = false;
    this.visibleChange.emit(false);
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  getCurrencyClass(value: number): string {
    return value >= 0 ? 'text-green-400' : 'text-red-400';
  }
}
