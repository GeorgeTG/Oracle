import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { MapService, MapCompletion, MapItemChange, ConsumedItem } from '../../../services/map.service';
import { ToastService } from '../../../services/toast.service';
import { DifficultyPipe } from '../../../pipes/difficulty.pipe';

@Component({
  selector: 'app-map-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule, DifficultyPipe],
  templateUrl: './map-detail.html',
  styleUrl: './map-detail.css',
})
export class MapDetailComponent implements OnChanges {
  @Input() visible: boolean = false;
  @Input() mapId: number | null = null;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() onDelete = new EventEmitter<number>();

  mapDetail: MapCompletion | null = null;
  mapItems: MapItemChange[] = [];
  consumedItems: ConsumedItem[] = [];
  itemsCollapsed: boolean = false;
  consumedCollapsed: boolean = false;
  affixesCollapsed: boolean = false;
  loading: boolean = false;

  constructor(
    private mapService: MapService,
    private toastService: ToastService
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['mapId'] && this.mapId) {
      this.loadMapDetails();
    }
  }

  loadMapDetails() {
    if (!this.mapId) return;
    
    this.loading = true;
    this.mapService.getMapDetails(this.mapId).subscribe({
      next: (details) => {
        this.mapDetail = details;
        this.itemsCollapsed = false;
        this.consumedCollapsed = false;
        this.loading = false;
        
        // Load map items
        this.mapService.getMapItems(this.mapId!).subscribe({
          next: (items) => {
            this.mapItems = items as MapItemChange[];
          },
          error: (error) => {
            console.error('[MapDetailComponent] Error loading map items:', error);
            this.toastService.error('Error', 'Failed to load item changes');
          }
        });
        
        // Load consumed items
        this.mapService.getMapItems(this.mapId!, true).subscribe({
          next: (items) => {
            this.consumedItems = items as ConsumedItem[];
          },
          error: (error) => {
            console.error('[MapDetailComponent] Error loading consumed items:', error);
            this.toastService.error('Error', 'Failed to load consumed items');
          }
        });
      },
      error: (error) => {
        console.error('[MapDetailComponent] Error loading map details:', error);
        this.toastService.error('Error', 'Failed to load map details');
        this.loading = false;
      }
    });
  }

  saveDescription() {
    if (!this.mapDetail) return;
    
    this.mapService.updateMap(this.mapDetail.id, {
      description: this.mapDetail.description || undefined
    }).subscribe({
      next: () => {
        this.toastService.success('Saved', 'Description updated successfully');
      },
      error: (error: any) => {
        console.error('[MapDetailComponent] Error saving description:', error);
        this.toastService.error('Error', 'Failed to save description');
      }
    });
  }

  deleteMap() {
    console.log('[MapDetail] deleteMap() called');
    console.log('[MapDetail] mapDetail:', this.mapDetail);
    
    if (!this.mapDetail) {
      console.log('[MapDetail] No mapDetail, returning');
      return;
    }
    
    const mapId = this.mapDetail.id;
    console.log('[MapDetail] Deleting map with ID:', mapId);
    
    this.mapService.deleteMap(mapId).subscribe({
      next: () => {
        console.log('[MapDetail] Map deleted successfully');
        this.toastService.success('Map Deleted', 'Map completion deleted successfully');
        this.onDelete.emit(mapId);
        this.closeDialog();
      },
      error: (error) => {
        console.error('[MapDetail] Error deleting map:', error);
        this.toastService.error('Delete Failed', 'Failed to delete map completion');
      }
    });
  }

  closeDialog() {
    this.visible = false;
    this.visibleChange.emit(false);
  }

  formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
  }

  formatDate(isoString: string): string {
    return new Date(isoString).toLocaleString();
  }
  
  formatNumber(value: number | undefined | null, decimals: number = 0): string {
    if (value === undefined || value === null) return 'N/A';
    const fixed = value.toFixed(decimals);
    const parts = fixed.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return parts.join(',');
  }
  
  getEntryPrice(): number {
    return this.consumedItems.reduce((sum, item) => sum + item.total_price, 0);
  }
}
