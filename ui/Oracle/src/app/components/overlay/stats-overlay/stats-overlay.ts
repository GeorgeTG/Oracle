import { Component, OnInit, OnDestroy, HostBinding, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { StatsService } from '../../../services/stats.service';
import { WebSocketService } from '../../../services/websocket.service';
import { ConfigurationService } from '../../../services/configuration.service';
import { OverlayService } from '../../../services/overlay.service';
import { ServiceEventType, ParserEventType } from '../../../models/enums';
import { StatsUpdateEvent, ItemObtainedEvent, MapStartedEvent, OverlayInfoTextEvent, ViewChangedEvent } from '../../../models/service-events';
import { StageAffixEvent } from '../../../models/parser-events';
import { CurrencyPipe } from '../../../pipes/currency.pipe';
import { DurationPipe } from '../../../pipes/duration.pipe';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';

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
  private statsSubscription?: Subscription;
  private configSubscription?: Subscription;
  private itemObtainedSubscription?: Subscription;
  private mapSubscription?: Subscription;
  private viewChangeSubscription?: Subscription;
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

  // --- Panel Registry ---
  panels = new Map<string, PanelState>();
  get panelArray(): PanelState[] { return Array.from(this.panels.values()); }

  // Getter/setter pairs for template two-way binding compatibility
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

  // --- Data properties (unique per panel) ---
  stats: StatsUpdateEvent | null = null;
  currentMap: MapStartedEvent | null = null;
  itemHistory: ItemObtainedEvent[] = [];
  maxHistoryItems: number = 20;
  notableItems: ItemObtainedEvent[] = [];
  maxNotableItems: number = 10;
  notableMinValue: number = 50;

  currencyLabel: string = 'Currency / Hour';
  expLabel: string = 'EXP / Hour';
  currentUnit: string = 'Hour';

  // Currency river
  riverItems: { id: number; delta: number; price: number; name: string }[] = [];
  private riverIdCounter = 0;
  private riverItemSubscription?: Subscription;

  // Map detail popups
  currentAffixes: { affix_id: number; description: string }[] = [];
  showConsumedPopup: boolean = false;
  showAffixesPopup: boolean = false;
  private affixSubscription?: Subscription;

  // Info text
  infoTextItems: { id: number; text: string; severity: string; duration: number }[] = [];
  private infoTextIdCounter = 0;
  private infoTextSubscription?: Subscription;

  // Radial menu position (not a panel)
  radialPosition: { left: string; top: string } | null = null;

  // View state
  private currentGameView: string = '';

  @HostBinding('class.transparent-mode')
  get isTransparentModeBinding(): boolean {
    return this.configService.isTransparentOverlay();
  }

  @HostBinding('class.edit-mode')
  get isEditModeBinding(): boolean {
    return this.editMode;
  }

  @HostBinding('class.hover-mode')
  get isHoverModeBinding(): boolean {
    return this.hoverMode;
  }

  get isTransparentMode(): boolean {
    return this.configService.isTransparentOverlay();
  }

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

  constructor(
    private statsService: StatsService,
    private websocketService: WebSocketService,
    private configService: ConfigurationService,
    private overlayService: OverlayService,
    private confirmationService: ConfirmationService,
    private ngZone: NgZone
  ) {
    // Build panel states from config
    for (const config of PANEL_CONFIGS) {
      this.panels.set(config.id, {
        config,
        visible: true,
        position: null,
        viewHidden: false,
      });
    }

    // Restore dialog visibility
    const saved = localStorage.getItem('overlay_panel_visibility');
    if (saved) {
      try {
        const state = JSON.parse(saved);
        for (const [id, panel] of this.panels) {
          if (id in state) panel.visible = state[id] ?? true;
        }
      } catch {}
    }

    // Restore dialog positions
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

    this.statsSubscription = this.statsService.getStats().subscribe(event => {
      this.stats = event;
    });

    this.itemObtainedSubscription = this.websocketService.subscribe<ItemObtainedEvent>(ServiceEventType.ITEM_OBTAINED).subscribe(event => {
      this.itemHistory.unshift(event);
      if (this.itemHistory.length > this.maxHistoryItems) {
        this.itemHistory = this.itemHistory.slice(0, this.maxHistoryItems);
      }
      // Track notable items (price >= 50)
      if (event.item_price >= this.notableMinValue) {
        this.notableItems.unshift(event);
        if (this.notableItems.length > this.maxNotableItems) {
          this.notableItems = this.notableItems.slice(0, this.maxNotableItems);
        }
      }
    });

    this.mapSubscription = this.statsService.getMapEvents().subscribe(event => {
      this.currentMap = event;
      this.currentAffixes = []; // Clear affixes on new map
    });

    // Subscribe to affix events
    this.affixSubscription = this.websocketService.subscribe<StageAffixEvent>(ParserEventType.STAGE_AFFIX).subscribe(event => {
      if (event.affixes?.length) {
        this.currentAffixes = event.affixes.map((a: any) => ({
          affix_id: a.affix_id,
          description: a.description || ''
        }));
      }
    });

    // Currency river - subscribe to item events, auto-remove after animation
    this.riverItemSubscription = this.websocketService.subscribe<ItemObtainedEvent>(ServiceEventType.ITEM_OBTAINED).subscribe(event => {
      if (!this.showRiver) return;
      const totalValue = event.delta * event.item_price;
      if (Math.abs(totalValue) < this.configService.getConfig().riverMinValue) return;
      const id = this.riverIdCounter++;
      this.riverItems.push({ id, delta: event.delta, price: totalValue, name: event.item_name || `Item #${event.item_id}` });
      // Remove after animation completes (4.5s)
      setTimeout(() => {
        this.riverItems = this.riverItems.filter(r => r.id !== id);
      }, 4500);
    });

    // Info text - subscribe to overlay info text events, auto-remove after duration
    this.infoTextSubscription = this.websocketService.subscribe<OverlayInfoTextEvent>(ServiceEventType.OVERLAY_INFO_TEXT).subscribe(event => {
      if (!this.showInfoText) return;
      const duration = event.duration ?? 3000;
      const id = this.infoTextIdCounter++;
      this.infoTextItems.push({ id, text: event.text, severity: event.severity, duration });
      setTimeout(() => {
        this.infoTextItems = this.infoTextItems.filter(r => r.id !== id);
      }, duration);
    });

    // Subscribe to view changes for auto-hide/show
    this.viewChangeSubscription = this.websocketService
      .subscribe<ViewChangedEvent>(ServiceEventType.VIEW_CHANGED)
      .subscribe(event => this.applyViewRules(event.view));

    this.setupWindowCleanup();
  }

  // --- Panel Registry Methods ---

  isPanelVisible(id: string): boolean {
    const p = this.panels.get(id);
    return p ? p.visible && !p.viewHidden : false;
  }

  togglePanel(id: string): void {
    const p = this.panels.get(id);
    if (!p) return;
    p.visible = !p.visible;
    this.saveVisibility();
  }

  onDialogHide(id: string): void {
    const p = this.panels.get(id);
    if (!p) return;
    // Don't persist hide if it was auto-hidden by view rules
    if (!p.viewHidden) {
      p.visible = false;
      this.saveVisibility();
    }
  }

  onDialogShow(_id: string): void {
    // Position is handled via [style] binding + CSS absolute positioning
  }

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

  // --- View State ---

  private applyViewRules(view: string): void {
    this.currentGameView = view;
    for (const [, panel] of this.panels) {
      const rules = panel.config.viewRules;
      if (!rules) {
        panel.viewHidden = false;
        continue;
      }
      // Hide when view matches any hide rule
      if (rules.hide?.some(v => view.includes(v))) {
        panel.viewHidden = true;
        continue;
      }
      // If show rules defined, hide unless view matches one of them
      if (rules.show?.length) {
        panel.viewHidden = !rules.show.some(v => view.includes(v));
        continue;
      }
      panel.viewHidden = false;
    }
    setTimeout(() => this.broadcastBounds(), 100);
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

        // Use manual fullscreen with slight oversize to hide Windows DWM 1px border
        const { currentMonitor } = await import('@tauri-apps/api/window');
        const { PhysicalPosition, PhysicalSize } = await import('@tauri-apps/api/dpi');
        const monitor = await currentMonitor();
        if (monitor) {
          await this.appWindow.setPosition(new PhysicalPosition(-2, -2));
          await this.appWindow.setSize(new PhysicalSize(monitor.size.width + 4, monitor.size.height + 4));
        }

        // Start in Normal state (click-through ON)
        await this.appWindow.setIgnoreCursorEvents(true);

        // Listen for edit mode toggle from main window
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

        // Listen for hover mode changes from overlay service
        this.hoverModeListener = await listen('set-hover-mode', async (event: any) => {
          const enabled = event.payload?.enabled ?? false;
          if (this.state === OverlayState.Edit || this.isDragging || this.confirmDialogOpen) return;
          this.ngZone.run(async () => {
            await this.changeState(enabled ? OverlayState.Hover : OverlayState.Normal);
          });
        });

        // Start broadcasting bounding boxes for hover detection
        this.startBoundsBroadcast();

        // Detect PrimeNG dialog drag start via header mousedown
        const onHeaderMouseDown = (e: Event) => {
          if ((e.target as HTMLElement).closest('.p-dialog-header')) {
            this.isDragging = true;
          }
        };
        const onHeaderMouseUp = () => {
          if (this.isDragging) {
            this.isDragging = false;
          }
        };
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
      accept: async () => {
        this.statsService.newSession().subscribe();
        await onDialogClose();
      },
      reject: async () => {
        await onDialogClose();
      }
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
        x: Math.round(rect.left),
        y: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
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
      panel: 'radial-menu',
      visible: true,
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
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

  getAbsPrice(price: number): number {
    return Math.abs(price);
  }

  getValueGlowClass(value: number): string {
    if (value > 0) {
      return 'shadow-[0_0_15px_rgba(16,185,129,0.6)] border-green-500';
    } else if (value < 0) {
      return 'shadow-[0_0_15px_rgba(239,68,68,0.6)] border-red-500';
    }
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
    this.statsSubscription?.unsubscribe();
    this.itemObtainedSubscription?.unsubscribe();
    this.mapSubscription?.unsubscribe();
    this.affixSubscription?.unsubscribe();
    this.riverItemSubscription?.unsubscribe();
    this.infoTextSubscription?.unsubscribe();
    this.viewChangeSubscription?.unsubscribe();
    if (this.boundsBroadcastInterval) {
      clearInterval(this.boundsBroadcastInterval);
    }

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
