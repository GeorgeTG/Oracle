import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MapService, MapCompletion, MapsResponse, MapItemChange } from '../../../services/map.service';
import { SessionsService } from '../../../services/sessions.service';
import { Session } from '../../../models/session.model';
import { PlayerService } from '../../../services/player.service';
import { ToastService } from '../../../services/toast.service';
import { Table, TableModule, TableLazyLoadEvent } from 'primeng/table';
import { MultiSelect } from 'primeng/multiselect';
import { Select } from 'primeng/select';
import { InputText } from 'primeng/inputtext';
import { MessageService } from 'primeng/api';
import { Subscription } from 'rxjs';
import { MapDetailComponent } from '../../shared/map-detail/map-detail';
import { DifficultyPipe } from '../../../pipes/difficulty.pipe';

@Component({
  selector: 'app-tracking-maps',
  imports: [CommonModule, FormsModule, TableModule, MultiSelect, Select, InputText, MapDetailComponent, DifficultyPipe],
  templateUrl: './maps.html',
  styleUrl: './maps.css',
})
export class MapsComponent implements OnInit, OnDestroy {
  maps: MapCompletion[] = [];
  totalRecords: number = 0;
  loading: boolean = false;
  playerName: string | null = null;
  private playerSubscription?: Subscription;
  showDetailDialog: boolean = false;
  selectedMapId: number | null = null;
  
  // Session filter
  sessions: any[] = [];
  selectedSession: any = null;
  
  // Filter values
  filterMapName: string = '';
  filterDifficulties: string[] = [];
  filterMinCurrency: number | null = null;
  filterMinExp: number | null = null;
  filterMinItems: number | null = null;
  
  private difficultyPipe = new DifficultyPipe();
  
  // Difficulty options for filter
  difficultyOptions = [
    { label: this.difficultyPipe.transform('T8+'), value: 'T8+' },
    { label: this.difficultyPipe.transform('T8_2'), value: 'T8_2' },
    { label: this.difficultyPipe.transform('T8_1'), value: 'T8_1' },
    { label: this.difficultyPipe.transform('T8_0'), value: 'T8_0' },
    { label: this.difficultyPipe.transform('T7_2'), value: 'T7_2' },
    { label: this.difficultyPipe.transform('T7_1'), value: 'T7_1' },
    { label: this.difficultyPipe.transform('T7_0'), value: 'T7_0' },
    { label: this.difficultyPipe.transform('T6'), value: 'T6' },
    { label: this.difficultyPipe.transform('T5'), value: 'T5' },
    { label: this.difficultyPipe.transform('T4'), value: 'T4' },
    { label: this.difficultyPipe.transform('T3'), value: 'T3' },
    { label: this.difficultyPipe.transform('T2'), value: 'T2' },
    { label: this.difficultyPipe.transform('T1'), value: 'T1' },
    { label: this.difficultyPipe.transform('DS'), value: 'DS' }
  ];

  constructor(
    private mapService: MapService,
    private sessionsService: SessionsService,
    private playerService: PlayerService,
    private toastService: ToastService
  ) {}

  ngOnInit() {
    this.playerName = this.playerService.getName();
    this.playerSubscription = this.playerService.getNameObservable().subscribe(name => {
      this.playerName = name;
      this.loadSessions();
    });
    this.loadSessions();
  }

  ngOnDestroy() {
    if (this.playerSubscription) {
      this.playerSubscription.unsubscribe();
    }
  }

  loadMaps(event: TableLazyLoadEvent) {
    this.loading = true;
    
    const page = ((event.first || 0) / (event.rows || 20)) + 1;
    const pageSize = event.rows || 20;
    
    // Extract sort field and order
    let sortField: string | undefined;
    let sortOrder: number | undefined;
    
    if (event.sortField) {
      sortField = event.sortField as string;
      sortOrder = event.sortOrder || 1;
    }
    
    // Build filters object
    const filters: any = {};
    
    if (this.filterMapName) {
      filters.mapName = this.filterMapName;
    }
    
    if (this.filterDifficulties && this.filterDifficulties.length > 0) {
      filters.difficulties = this.filterDifficulties;
    }
    
    if (this.filterMinCurrency !== null) {
      filters.minCurrency = this.filterMinCurrency;
    }
    
    if (this.filterMinExp !== null) {
      filters.minExp = this.filterMinExp;
    }
    
    if (this.filterMinItems !== null) {
      filters.minItems = this.filterMinItems;
    }
    
    if (this.selectedSession?.value) {
      filters.sessionId = this.selectedSession.value;
    }
    
    this.mapService.getMaps(page, pageSize, this.playerName || undefined, sortField, sortOrder, filters)
      .subscribe({
        next: (response: MapsResponse) => {
          this.maps = response.results;
          this.totalRecords = response.total;
          this.loading = false;
        },
        error: (error) => {
          console.error('[MapsComponent] Error loading maps:', error);
          this.loading = false;
        }
      });
  }

  onFilterChange(dt: any) {
    // Reload from first page when filters change
    dt.first = 0;
    dt._lazy = true;
    dt.onLazyLoad.emit(dt.createLazyLoadMetadata());
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

  showMapDetails(map: MapCompletion) {
    this.selectedMapId = map.id;
    this.showDetailDialog = true;
  }

  confirmDeleteMap(map: MapCompletion) {
    if (confirm(`Are you sure you want to delete this map completion? (ID: ${map.id})\n${map.map_name || 'Map'} - ${map.map_difficulty}`)) {
      this.onMapDeleted(map.id);
    }
  }

  onMapDeleted(mapId: number) {
    this.mapService.deleteMap(mapId).subscribe({
      next: () => {
        this.toastService.success('Map Deleted', 'Map completion deleted successfully');
        // Reload the table
        this.maps = this.maps.filter(m => m.id !== mapId);
        this.totalRecords--;
      },
      error: (error) => {
        console.error('Error deleting map:', error);
        this.toastService.error('Delete Failed', 'Failed to delete map completion');
      }
    });
  }

  loadSessions() {
    this.sessionsService.getSessions(this.playerName || undefined, 1, 100).subscribe({
      next: (response) => {
        this.sessions = (response.results || []).map((session: Session) => {
          const startDate = new Date(session.started_at);
          const dateStr = startDate.toLocaleDateString('en-GB'); // DD/MM/YYYY
          const timeStr = startDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }); // HH:MM
          
          return {
            label: `${session.player_name} - Session #${session.id} - ${dateStr} ${timeStr} (${session.total_maps} maps)`,
            value: session.id,
            session: session
          };
        });
      },
      error: (error) => {
        console.error('Error loading sessions:', error);
        this.toastService.error('Load Failed', 'Failed to load sessions');
      }
    });
  }

  onSessionChange(dt: any) {
    // Reload from first page when session filter changes
    dt.first = 0;
    dt._lazy = true;
    dt.onLazyLoad.emit(dt.createLazyLoadMetadata());
  }
}
