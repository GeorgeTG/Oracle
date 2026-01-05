import { Component, OnInit, HostListener } from "@angular/core";
import { CommonModule } from '@angular/common';
import { Router, RouterOutlet, NavigationEnd } from "@angular/router";
import { Drawer } from 'primeng/drawer';
import { Toast } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { SidebarComponent } from './components/sidebar/sidebar';
import { SessionsService } from './services/sessions.service';

import { environment } from "../environments/environment";

@Component({
  selector: "app-root",
  imports: [CommonModule, RouterOutlet, Drawer, Toast, SidebarComponent],
  templateUrl: "./app.component.html",
  styleUrl: "./app.component.css",
})
export class AppComponent implements OnInit {
  sidebarVisible: boolean = true;
  isOverlayRoute: boolean = false;
  private hoverTimeout: any;
  private readonly edgeThreshold = 10; // pixels from left edge
  private readonly hoverDelay = 300; // milliseconds

  constructor(
    private router: Router,
    private sessionsService: SessionsService  // Inject to ensure early initialization
  ) {}

  ngOnInit() {
    // Display Oracle quote
    console.log('%c"Gods adore their creations, much like how birds of prey love their lambs"', 'color: #a855f7; font-size: 14px; font-style: italic;');
    console.log('%c- Thea, Blasphemer', 'color: #9333ea; font-size: 12px; margin-left: 20px;');
    console.log(`%cEnvironment: ${environment.production ? 'Production' : 'Development'}`, 'color: #6b7280; font-size: 12px;');
    console.log(`version: ${environment.version}`, 'color: #6b7280; font-size: 12px;');
    console.log(`buildDate: ${environment.buildDate}`, 'color: #6b7280; font-size: 12px;');
    
    // Check initial route
    this.checkIfOverlayRoute(this.router.url);
    
    // Subscribe to route changes
    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.checkIfOverlayRoute(event.urlAfterRedirects);
      }
    });
  }

  private checkIfOverlayRoute(url: string) {
    this.isOverlayRoute = url.startsWith('/overlay');
  }

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    // Check if mouse is at the left edge
    if (event.clientX <= this.edgeThreshold && !this.sidebarVisible) {
      // Start timeout to open sidebar
      if (!this.hoverTimeout) {
        this.hoverTimeout = setTimeout(() => {
          this.sidebarVisible = true;
          this.hoverTimeout = null;
        }, this.hoverDelay);
      }
    } else {
      // Clear timeout if mouse moves away from edge
      if (this.hoverTimeout) {
        clearTimeout(this.hoverTimeout);
        this.hoverTimeout = null;
      }
    }
  }

  closeSidebarIfOpen() {
    if (this.sidebarVisible) {
      this.sidebarVisible = false;
    }
  }
}
