import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ConfigurationService } from './configuration.service';

@Injectable({
  providedIn: 'root'
})
export class OverlayService {
  private overlayWindow: any = null;
  private toggleInProgress = false;

  private _isOpen$ = new BehaviorSubject<boolean>(false);
  private _isEditMode$ = new BehaviorSubject<boolean>(false);
  private _isHoverMode$ = new BehaviorSubject<boolean>(false);

  isOpen$ = this._isOpen$.asObservable();
  isEditMode$ = this._isEditMode$.asObservable();
  isHoverMode$ = this._isHoverMode$.asObservable();

  get isOpen(): boolean { return this._isOpen$.value; }
  get isEditMode(): boolean { return this._isEditMode$.value; }
  get isHoverMode(): boolean { return this._isHoverMode$.value; }

  constructor(private configService: ConfigurationService) {}

  async openOverlay(): Promise<void> {
    if (this.isOpen || this.toggleInProgress) return;
    this.toggleInProgress = true;

    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');

      // Check if already exists
      const existing = await WebviewWindow.getByLabel('stats-overlay');
      if (existing) {
        this._isOpen$.next(true);
        return;
      }

      const isTransparent = this.configService.isTransparentOverlay();
      let windowConfig: any;

      if (isTransparent) {
        const { currentMonitor } = await import('@tauri-apps/api/window');
        const monitor = await currentMonitor();
        const screenWidth = monitor?.size?.width ?? 1920;
        const screenHeight = monitor?.size?.height ?? 1080;

        windowConfig = {
          url: '/overlay/stats',
          title: '',
          width: screenWidth,
          height: screenHeight,
          x: 0,
          y: 0,
          resizable: false,
          alwaysOnTop: true,
          decorations: false,
          transparent: true,
          skipTaskbar: true,
          shadow: false,
        };
      } else {
        windowConfig = {
          url: '/overlay/stats',
          title: 'Stats Overlay',
          width: 400,
          height: 500,
          resizable: true,
          alwaysOnTop: true,
          decorations: true,
          transparent: false,
          skipTaskbar: false,
        };

        const savedPosition = localStorage.getItem('stats_overlay_position');
        if (savedPosition) {
          try {
            const pos = JSON.parse(savedPosition);
            windowConfig.x = pos.x;
            windowConfig.y = pos.y;
            windowConfig.width = pos.width;
            windowConfig.height = pos.height;
          } catch {}
        }
      }

      this.overlayWindow = new WebviewWindow('stats-overlay', windowConfig);

      this.overlayWindow.once('tauri://created', () => {
        this._isOpen$.next(true);
        console.log('[OverlayService] Overlay window created');
      });

      this.overlayWindow.once('tauri://error', (e: any) => {
        this._isOpen$.next(false);
        this.overlayWindow = null;
        console.error('[OverlayService] Failed to create overlay:', e);
      });

      this.overlayWindow.listen('tauri://destroyed', () => {
        this._isOpen$.next(false);
        this._isEditMode$.next(false);
        this.overlayWindow = null;
        console.log('[OverlayService] Overlay window destroyed');
      });
    } catch (error) {
      this._isOpen$.next(false);
      this.overlayWindow = null;
      console.error('[OverlayService] Error opening overlay:', error);
    } finally {
      setTimeout(() => { this.toggleInProgress = false; }, 200);
    }
  }

  async closeOverlay(): Promise<void> {
    if (!this.isOpen) return;

    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const existing = await WebviewWindow.getByLabel('stats-overlay');
      if (existing) {
        await existing.destroy();
      }
    } catch (e) {
      console.error('[OverlayService] Error closing overlay:', e);
    }

    this.overlayWindow = null;
    this._isOpen$.next(false);
    this._isEditMode$.next(false);
    this._isHoverMode$.next(false);
  }

  async toggleOverlay(): Promise<void> {
    if (this.isOpen) {
      await this.closeOverlay();
    } else {
      await this.openOverlay();
    }
  }

  async toggleEditMode(): Promise<void> {
    if (!this.isOpen) return;

    try {
      console.log('[OverlayService] toggleEditMode() called');
      const { emitTo } = await import('@tauri-apps/api/event');
      await emitTo({ kind: 'WebviewWindow', label: 'stats-overlay' }, 'toggle-edit-mode');
      this._isEditMode$.next(!this.isEditMode);
    } catch (e) {
      console.error('[OverlayService] Error toggling edit mode:', e);
    }
  }

  async setHoverMode(enabled: boolean): Promise<void> {
    if (!this.isOpen || !this.configService.isTransparentOverlay()) return;
    if (this.isEditMode) return;

    try {
      const { emitTo } = await import('@tauri-apps/api/event');
      await emitTo({ kind: 'WebviewWindow', label: 'stats-overlay' }, 'set-hover-mode', { enabled });
      this._isHoverMode$.next(enabled);
    } catch (e) {
      console.error('[OverlayService] Error setting hover mode:', e);
    }
  }

  async handlePageUp(): Promise<void> {
    console.log(`[OverlayService] handlePageUp() called, isOpen=${this.isOpen}, isTransparent=${this.configService.isTransparentOverlay()}`);
    if (!this.isOpen) {
      await this.openOverlay();
    } else if (this.configService.isTransparentOverlay()) {
      await this.toggleEditMode();
    } else {
      await this.closeOverlay();
    }
  }
}
