import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MenuItem } from 'primeng/api';
import { PlayerService } from '../../services/player.service';
import { WebSocketService } from '../../services/websocket.service';
import { ConfigurationService } from '../../services/configuration.service';
import { ServiceEventType } from '../../models/enums';
import { LevelProgressEvent } from '../../models/service-events';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class SidebarComponent implements OnInit, OnDestroy {
  playerName: string | null = null;
  playerLevel: number = 1;
  expPercentage: number = 0;
  expCurrent: number = 0;
  private levelSubscription?: Subscription;
  private playerSubscription?: Subscription;

  get shouldShowLevel(): boolean {
    return this.playerLevel > 1 || this.expCurrent > 0;
  }
  
  menuSections = [
    {
      title: 'Live',
      items: [
        { label: 'Currency', icon: 'pi pi-dollar', route: '/live/currency' },
        { label: 'Session', icon: 'pi pi-clock', route: '/live/session' }
      ]
    },
    {
      title: 'Tracking',
      items: [
        { label: 'Maps', icon: 'pi pi-map-marker', route: '/tracking/maps' },
        { label: 'Sessions', icon: 'pi pi-history', route: '/tracking/sessions' },
        { label: 'Market', icon: 'pi pi-shopping-cart', route: '/tracking/market' },
        { label: 'Items', icon: 'pi pi-tags', route: '/tracking/items' },
        { label: 'Inventory', icon: 'pi pi-box', route: '/tracking/inventory' }
      ]
    },
    {
      title: 'Settings',
      items: [
        { label: 'Configuration', icon: 'pi pi-cog', route: '/settings/configuration' },
        { label: 'About', icon: 'pi pi-info-circle', route: '/settings/about' }
      ]
    }
  ];

  constructor(
    private router: Router,
    private playerService: PlayerService,
    private websocketService: WebSocketService,
    private http: HttpClient,
    private config: ConfigurationService
  ) {}

  ngOnInit() {
    this.playerName = this.playerService.getName();
    
    this.playerSubscription = this.playerService.getNameObservable().subscribe(name => {
      this.playerName = name;
    });
    
    // Subscribe to level progress events
    this.levelSubscription = this.websocketService.subscribe<LevelProgressEvent>(
      ServiceEventType.LEVEL_PROGRESS
    ).subscribe(event => {
      this.playerLevel = event.level;
      this.expPercentage = event.percentage;
      this.expCurrent = event.current;
    });
  }

  ngOnDestroy() {
    this.levelSubscription?.unsubscribe();
    this.playerSubscription?.unsubscribe();
  }

  navigate(route: string) {
    this.router.navigate([route]);
  }

  isActive(route: string): boolean {
    return this.router.url === route;
  }

  restartServer() {
    if (!confirm('Are you sure you want to restart the server?')) {
      return;
    }

    const wsConfig = this.config.getConfig();
    const apiUrl = `http://${wsConfig.wsIp}:${wsConfig.wsPort}`;
    
    this.http.post(`${apiUrl}/system/restart`, {}).subscribe({
      next: () => {
        console.log('Server restart initiated');
      },
      error: (err) => {
        console.error('Failed to restart server:', err);
      }
    });
  }

  reloadPage() {
    window.location.reload();
  }
}
