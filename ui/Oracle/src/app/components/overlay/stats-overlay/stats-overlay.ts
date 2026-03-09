import { Component, OnInit, OnDestroy, HostBinding, NgZone, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { StatsStore } from '../../../store/stats.store';
import { ItemStore } from '../../../store/item.store';
import { StatsService } from '../../../services/stats.service';
import { WebSocketService } from '../../../services/websocket.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { OverlayService } from '../../../services/overlay.service';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';

// --- Panel Registry Types ---

type PanelKind = 'dialog' | 'river';

interface PanelConfig {
  id: string;
  kind: PanelKind;
  header: string;
  icon: string;
  radialPosition: string;
  defaultWidth: string;
  defaultPosition: { left: string; top: string };
  viewRules?: {
    hide?: string[];
    show?: string[];
  };
}

interface PanelState {
  config: PanelConfig;
  visible: boolean;
  position: { left: string; top: string } | null;
  viewHidden: boolean;
}

const PANEL_CONFIGS: PanelConfig[] = [
  {
    id: 'stats', kind: 'dialog', header: '📊 Stats', icon: 'pi pi-chart-bar',
    radialPosition: 'radial-top', defaultWidth: '320px',
    defaultPosition: { left: '20px', top: '20px' },
  },
  {
    id: 'items', kind: 'dialog', header: '🎒 Recent Items', icon: 'pi pi-list',
    radialPosition: 'radial-right', defaultWidth: '340px',
    defaultPosition: { left: '360px', top: '20px' },
  },
  {
    id: 'notable', kind: 'dialog', header: '⭐ Notable Items', icon: 'pi pi-star',
    radialPosition: 'radial-bottom-left', defaultWidth: '340px',
    defaultPosition: { left: '360px', top: '400px' },
  },
  {
    id: 'map', kind: 'dialog', header: '🗺️ Map Details', icon: 'pi pi-map',
    radialPosition: 'radial-bottom', defaultWidth: '280px',
    defaultPosition: { left: '20px', top: '350px' },
    viewRules: { hide: ['AuctionHouse'], show: ['FightCtrl'] },
  },
  {
    id: 'river', kind: 'river', header: '💰 Currency River', icon: 'pi pi-dollar',
    radialPosition: 'radial-left', defaultWidth: '500px',
    defaultPosition: { left: '700px', top: '200px' },
    viewRules: { hide: ['AuctionHouse'] },
  },
  {
    id: 'infoText', kind: 'river', header: 'ℹ️ Info Text', icon: 'pi pi-info-circle',
    radialPosition: 'radial-top-left', defaultWidth: '800px',
    defaultPosition: { left: '700px', top: '550px' },
  },
];

enum OverlayState {
  Normal = 'normal',
  Hover = 'hover',
  Edit = 'edit',
}

@Component({
  selector: 'app-stats-overlay',
  imports: [CommonModule, CurrencyPipe, DurationPipe, DialogModule, ButtonModule, ConfirmDialogModule],
  providers: [ConfirmationService],
  templateUrl: './stats-overlay.html',
  styleUrl: './stats-overlay.css',
})
export class StatsOverlayComponent implements OnInit, OnDestroy {
  // Stores (signal-based — no subscription management needed)
  protected statsStore = inject(StatsStore);
  protected itemStore = inject(ItemStore);

  private configService = inject(ConfigurationService);
  private overlayService = inject(OverlayService);
  private statsService = inject(StatsService);
  private websocketService = inject(WebSocketService);
  private confirmationService = inject(ConfirmationService);
  private ngZone = inject(NgZone);

  // Only remaining subscription: config periodic unit (not WebSocket-driven)
  private configSubscription?: Subscription;

  private destroyListener?: any;
  private toggleEditModeListener?: any;
  private hoverModeListener?: any;
  private dialogDragListener?: () => void;
  private lastBoundsJson: string = '';
  private boundsBroadcastInterval?: ReturnType<typeof setInterval>;
  private appWindow: any = null;

  state: OverlayState = OverlayState.Normal;
  isDragging: boolean = false;
  confirmDialogOpen: boolean = false;

  get editMode(): boolean { return this.state === OverlayState.Edit; }
  get hoverMode(): boolean { return this.state === OverlayState.Hover; }

  // Template-compatible getters delegating to signal stores
  get stats() { return this.statsStore.lastStats(); }
  get currentMap() { return this.statsStore.lastMap(); }
  get currentAffixes() { return this.statsStore.currentAffixes(); }
  get isLogReading() { return this.statsStore.isLogReading(); }
  get itemHistory() { return this.itemStore.recentItems(); }
  get notableItems() { return this.itemStore.notableItems(); }
  get riverItems() { return this.itemStore.riverItems(); }
  get infoTextItems() { return this.itemStore.infoTextItems(); }

  // --- Panel Registry ---
  panels = new Map<string, PanelState>();
  get panelArray(): PanelState[] { return Array.from(this.panels.values()); }

  get showStats(): boolean { return this.isPanelVisible('stats'); }
  set showStats(v: boolean) { this.panels.get('stats')!.visible = v; }

  get showItems(): boolean { return this.isPanelVisible('items'); }
  set showItems(v: boolean) { this.panels.get('items')!.visible = v; }

  get showNotable(): boolean { return this.isPanelVisible('notable'); }
  set showNotable(v: boolean) { this.panels.get('notable')!.visible = v; }

  get showMap(): boolean { return this.isPanelVisible('map'); }
  set showMap(v: boolean) { this.panels.get('map')!.visible = v; }

  get showRiver(): boolean { return this.isPanelVisible('river'); }
  set showRiver(v: boolean) { this.panels.get('river')!.visible = v; }

  get showInfoText(): boolean { return this.isPanelVisible('infoText'); }
  set showInfoText(v: boolean) { this.panels.get('infoText')!.visible = v; }

  // Labels driven by config
  currencyLabel: string = 'Currency / Hour';
  expLabel: string = 'EXP / Hour';
  currentUnit: string = 'Hour';

  // Map detail popups
  showConsumedPopup: boolean = false;
  showAffixesPopup: boolean = false;

  // Radial menu position
  radialPosition: { left: string; top: string } | null = null;

  @HostBinding('class.transparent-mode')
  get isTransparentModeBinding(): boolean { return this.configService.isTransparentOverlay(); }

  @HostBinding('class.edit-mode')
  get isEditModeBinding(): boolean { return this.editMode; }

  @HostBinding('class.hover-mode')
  get isHoverModeBinding(): boolean { return this.hoverMode; }

  get isTransparentMode(): boolean { return this.configService.isTransparentOverlay(); }

  private async changeState(newState: OverlayState): Promise<void> {
    if (this.state === newState) return;
    const prev = this.state;
    this.state = newState;
    this.isDragging = false;
    if (this.isTransparentMode && this.appWindow) {
      await this.appWindow.setIgnoreCursorEvents(newState === OverlayState.Normal);
    }
    console.log(`[StatsOverlay] State: ${prev} -> ${newState}`);
  }

  constructor() {
    for (const config of PANEL_CONFIGS) {
      this.panels.set(config.id, { config, visible: true, position: null, viewHidden: false });
    }

    const saved = localStorage.getItem('overlay_panel_visibility');
    if (saved) {
      try {
        const state = JSON.parse(saved);
        for (const [id, panel] of this.panels) {
          if (id in state) panel.visible = state[id] ?? true;
        }
      } catch {}
    }

    const positions = localStorage.getItem('overlay_dialog_positions');
    if (positions) {
      try {
        const pos = JSON.parse(positions);
        for (const [id, panel] of this.panels) {
          if (pos[id]) panel.position = pos[id];
        }
        this.radialPosition = pos.radial ?? null;
      } catch {}
    }
  }

  async ngOnInit() {
    await this.setupOverlayWindow();

    this.configSubscription = this.configService.periodicUnit$.subscribe(unit => {
      this.currentUnit = unit;
      this.currencyLabel = `Currency / ${unit}`;
      this.expLabel = `EXP / ${unit}`;
    });

    this.setupWindowCleanup();
  }

  // --- Panel visibility with view rules (reads from StatsStore signal) ---

  isPanelVisible(id: string): boolean {
    const p = this.panels.get(id);
    if (!p || !p.visible) return false;
    const rules = p.config.viewRules;
    if (!rules) return true;
    const view = this.statsStore.currentGameView();
    if (rules.hide?.some(v => view.includes(v))) return false;
    if (rules.show?.length) return rules.show.some(v => view.includes(v));
    return true;
  }

  // --- Panel Registry Methods ---

  togglePanel(id: string): void {
    const p = this.panels.get(id);
    if (!p) return;
    p.visible = !p.visible;
    this.saveVisibility();
  }

  onDialogHide(id: string): void {
    const p = this.panels.get(id);
    if (!p) return;
    p.visible = false;
    this.saveVisibility();
  }

  onDialogShow(_id: string): void {}

  onDialogDragEnd(id: string): void {
    this.isDragging = false;
    const el = document.querySelector(`.dialog-${id}.p-dialog`) as HTMLElement;
    if (!el) return;
    const p = this.panels.get(id)!;
    p.position = { left: el.style.left, top: el.style.top };
    this.saveDialogPositions();
    this.broadcastBounds();
  }

  getDialogStyle(id: string): Record<string, string> {
    const p = this.panels.get(id)!;
    const pos = p.position || p.config.defaultPosition;
    return { width: p.config.defaultWidth, left: pos.left, top: pos.top };
  }

  getPanelPosition(id: string): { left: string; top: string } {
    const p = this.panels.get(id)!;
    return p.position || p.config.defaultPosition;
  }

  // --- Overlay Window Setup ---

  private async setupOverlayWindow() {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      this.appWindow = getCurrentWindow();

      if (this.isTransparentMode) {
        document.documentElement.style.backgroundColor = 'transparent';
        document.body.style.backgroundColor = 'transparent';
        await this.appWindow.setDecorations(false);
        await this.appWindow.setShadow(false);

        const { currentMonitor } = await import('@tauri-apps/api/window');
        const { PhysicalPosition, PhysicalSize } = await import('@tauri-apps/api/dpi');
        const monitor = await currentMonitor();
        if (monitor) {
          await this.appWindow.setPosition(new PhysicalPosition(-2, -2));
          await this.appWindow.setSize(new PhysicalSize(monitor.size.width + 4, monitor.size.height + 4));
        }

        await this.appWindow.setIgnoreCursorEvents(true);

        const { listen } = await import('@tauri-apps/api/event');
        let lastToggleTime = 0;
        this.toggleEditModeListener = await listen('toggle-edit-mode', async () => {
          const now = Date.now();
          if (now - lastToggleTime < 300) return;
          lastToggleTime = now;
          this.ngZone.run(async () => {
            this.confirmDialogOpen = false;
            await this.changeState(this.state === OverlayState.Edit ? OverlayState.Normal : OverlayState.Edit);
          });
        });

        this.hoverModeListener = await listen('set-hover-mode', async (event: any) => {
          const enabled = event.payload?.enabled ?? false;
          if (this.state === OverlayState.Edit || this.isDragging || this.confirmDialogOpen) return;
          this.ngZone.run(async () => {
            await this.changeState(enabled ? OverlayState.Hover : OverlayState.Normal);
          });
        });

        this.startBoundsBroadcast();

        const onHeaderMouseDown = (e: Event) => {
          if ((e.target as HTMLElement).closest('.p-dialog-header')) this.isDragging = true;
        };
        const onHeaderMouseUp = () => { if (this.isDragging) this.isDragging = false; };
        document.addEventListener('mousedown', onHeaderMouseDown);
        document.addEventListener('mouseup', onHeaderMouseUp);
        this.dialogDragListener = () => {
          document.removeEventListener('mousedown', onHeaderMouseDown);
          document.removeEventListener('mouseup', onHeaderMouseUp);
        };
      } else {
        await this.setupPositionTracking();
      }
    } catch (error) {
      console.error('[StatsOverlay] Error setting up overlay window:', error);
    }
  }

  private async setupPositionTracking() {
    if (!this.appWindow) return;
    try {
      const savePosition = async () => {
        const position = await this.appWindow.outerPosition();
        const size = await this.appWindow.outerSize();
        localStorage.setItem('stats_overlay_position', JSON.stringify({
          x: position.x, y: position.y,
          width: size.width, height: size.height
        }));
      };
      await this.appWindow.listen('tauri://move', savePosition);
      await this.appWindow.listen('tauri://resize', savePosition);
    } catch (error) {
      console.error('[StatsOverlay] Error setting up position tracking:', error);
    }
  }

  // --- Drag Handlers ---

  onRadialDragStart(event: MouseEvent) {
    if (!this.editMode && !this.hoverMode) return;
    event.preventDefault();
    this.isDragging = true;
    const menuEl = (event.currentTarget as HTMLElement).closest('.radial-menu') as HTMLElement;
    if (!menuEl) return;
    const startX = event.clientX;
    const startY = event.clientY;
    const rect = menuEl.getBoundingClientRect();
    const origLeft = rect.left;
    const origTop = rect.top;

    const onMouseMove = (e: MouseEvent) => {
      menuEl.style.left = `${origLeft + (e.clientX - startX)}px`;
      menuEl.style.top = `${origTop + (e.clientY - startY)}px`;
      menuEl.style.right = 'auto';
      menuEl.style.bottom = 'auto';
    };
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      this.isDragging = false;
      this.radialPosition = { left: menuEl.style.left, top: menuEl.style.top };
      this.saveDialogPositions();
      this.broadcastBounds();
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  onElementDragStart(event: MouseEvent, panelId: string) {
    if (!this.editMode) return;
    event.preventDefault();
    this.isDragging = true;
    const el = event.currentTarget as HTMLElement;
    const startX = event.clientX;
    const startY = event.clientY;
    const origLeft = parseInt(el.style.left || '0', 10);
    const origTop = parseInt(el.style.top || '0', 10);

    const onMouseMove = (e: MouseEvent) => {
      el.style.left = `${origLeft + (e.clientX - startX)}px`;
      el.style.top = `${origTop + (e.clientY - startY)}px`;
    };
    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      this.isDragging = false;
      this.panels.get(panelId)!.position = { left: el.style.left, top: el.style.top };
      this.saveDialogPositions();
      this.broadcastBounds();
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  // --- Actions ---

  async newSession() {
    this.confirmDialogOpen = true;
    if (this.isTransparentMode && this.appWindow) {
      await this.appWindow.setIgnoreCursorEvents(false);
    }

    const onDialogClose = async () => {
      this.confirmDialogOpen = false;
      this.state = OverlayState.Hover;
      await this.changeState(OverlayState.Normal);
    };

    this.confirmationService.confirm({
      message: 'Start a new session? Current stats will be reset.',
      header: 'New Session',
      icon: 'pi pi-refresh',
      accept: async () => { this.statsService.newSession().subscribe(); await onDialogClose(); },
      reject: async () => { await onDialogClose(); }
    });
  }

  async showConsumedItems() {
    this.showConsumedPopup = true;
    if (this.isTransparentMode && this.appWindow) {
      await this.appWindow.setIgnoreCursorEvents(false);
    }
  }

  async showAffixes() {
    this.showAffixesPopup = true;
    if (this.isTransparentMode && this.appWindow) {
      await this.appWindow.setIgnoreCursorEvents(false);
    }
  }

  async onPopupHide() {
    this.showConsumedPopup = false;
    this.showAffixesPopup = false;
    if (this.state === OverlayState.Normal && this.isTransparentMode && this.appWindow) {
      await this.appWindow.setIgnoreCursorEvents(true);
    }
  }

  // --- Persistence ---

  private saveVisibility(): void {
    const state: Record<string, boolean> = {};
    for (const [id, p] of this.panels) state[id] = p.visible;
    localStorage.setItem('overlay_panel_visibility', JSON.stringify(state));
    setTimeout(() => this.broadcastBounds(), 100);
  }

  private saveDialogPositions(): void {
    const pos: Record<string, any> = {};
    for (const [id, p] of this.panels) pos[id] = p.position;
    pos['radial'] = this.radialPosition;
    localStorage.setItem('overlay_dialog_positions', JSON.stringify(pos));
  }

  // --- Bounds Broadcasting ---

  private getAllDialogBounds() {
    const bounds: any[] = [];
    for (const [id, p] of this.panels) {
      if (p.config.kind !== 'dialog') continue;
      const el = document.querySelector(`.dialog-${id}.p-dialog`) as HTMLElement;
      if (!el) {
        bounds.push({ panel: id, visible: false, x: 0, y: 0, width: 0, height: 0 });
        continue;
      }
      const rect = el.getBoundingClientRect();
      bounds.push({
        panel: id,
        visible: this.isPanelVisible(id),
        x: Math.round(rect.left), y: Math.round(rect.top),
        width: Math.round(rect.width), height: Math.round(rect.height),
      });
    }
    const radial = this.getRadialMenuBounds();
    if (radial) bounds.push(radial);
    return bounds;
  }

  private getRadialMenuBounds() {
    const el = document.querySelector('.radial-menu') as HTMLElement;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return {
      panel: 'radial-menu', visible: true,
      x: Math.round(rect.left), y: Math.round(rect.top),
      width: Math.round(rect.width), height: Math.round(rect.height),
    };
  }

  private broadcastBounds() {
    const bounds = this.getAllDialogBounds();
    const json = JSON.stringify(bounds);
    if (json === this.lastBoundsJson) return;
    this.lastBoundsJson = json;
    this.websocketService.send({ type: 'overlay_bounds_update', bounds });
  }

  private startBoundsBroadcast() {
    setTimeout(() => this.broadcastBounds(), 500);
    this.boundsBroadcastInterval = setInterval(() => this.broadcastBounds(), 2000);
  }

  // --- Utility ---

  getAbsPrice(price: number): number { return Math.abs(price); }

  getValueGlowClass(value: number): string {
    if (value > 0) return 'shadow-[0_0_15px_rgba(16,185,129,0.6)] border-green-500';
    if (value < 0) return 'shadow-[0_0_15px_rgba(239,68,68,0.6)] border-red-500';
    return 'shadow-[0_0_15px_rgba(245,158,11,0.6)] border-yellow-500';
  }

  // --- Cleanup ---

  private async setupWindowCleanup() {
    try {
      if (!this.appWindow) {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        this.appWindow = getCurrentWindow();
      }
      this.destroyListener = await this.appWindow.onCloseRequested(async () => {
        await this.cleanup();
      });
    } catch (error) {
      console.error('[StatsOverlay] Error setting up cleanup:', error);
    }
  }

  private async cleanup() {
    clearInterval(this.boundsBroadcastInterval);
    if (this.isTransparentMode) {
      document.documentElement.style.backgroundColor = '';
      document.body.style.backgroundColor = '';
    }
  }

  async ngOnDestroy() {
    this.configSubscription?.unsubscribe();
    this.destroyListener?.();
    this.toggleEditModeListener?.();
    this.hoverModeListener?.();
    this.dialogDragListener?.();
    await this.cleanup();
  }
}
