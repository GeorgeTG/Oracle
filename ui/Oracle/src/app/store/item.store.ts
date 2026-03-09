import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { patchState, signalStore, withHooks, withMethods, withState } from '@ngrx/signals';
import { ServiceEventType } from '../models/enums';
import { ItemObtainedEvent, OverlayInfoTextEvent } from '../models/service-events';
import { ConfigurationService } from '../services/configuration.service';
import { ToastService } from '../services/toast.service';
import { WebSocketService } from '../services/websocket.service';

export interface RiverItem {
  id: number;
  delta: number;
  price: number;
  name: string;
}

export interface InfoTextItem {
  id: number;
  text: string;
  severity: string;
  duration: number;
}

interface ItemState {
  recentItems: ItemObtainedEvent[];
  notableItems: ItemObtainedEvent[];
  notableMinValue: number;
  riverItems: RiverItem[];
  infoTextItems: InfoTextItem[];
  lastDataChangeId: number; // increments on ITEM_DATA_CHANGED — components react via effect()
}

let riverIdCounter = 0;
let infoTextIdCounter = 0;

export const ItemStore = signalStore(
  { providedIn: 'root' },
  withState<ItemState>({
    recentItems: [],
    notableItems: [],
    notableMinValue: 50,
    riverItems: [],
    infoTextItems: [],
    lastDataChangeId: 0,
  }),

  withMethods((store) => ({
    clearRiverItem(id: number): void {
      patchState(store, state => ({
        riverItems: state.riverItems.filter(r => r.id !== id),
      }));
    },
    clearInfoTextItem(id: number): void {
      patchState(store, state => ({
        infoTextItems: state.infoTextItems.filter(r => r.id !== id),
      }));
    },
    setNotableMinValue(value: number): void {
      patchState(store, { notableMinValue: value });
    },
    addInfoText(event: OverlayInfoTextEvent): void {
      const duration = event.duration ?? 3000;
      const id = infoTextIdCounter++;
      patchState(store, state => ({
        infoTextItems: [...state.infoTextItems, { id, text: event.text, severity: event.severity, duration }],
      }));
      setTimeout(() => {
        patchState(store, state => ({
          infoTextItems: state.infoTextItems.filter(r => r.id !== id),
        }));
      }, duration);
    },
  })),

  withHooks({
    onInit(store, ws = inject(WebSocketService), configService = inject(ConfigurationService), toastService = inject(ToastService), destroyRef = inject(DestroyRef)) {
      // Item obtained events
      ws.subscribe<ItemObtainedEvent>(ServiceEventType.ITEM_OBTAINED)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => {
          const minValue = store.notableMinValue();

          patchState(store, state => ({
            recentItems: [event, ...state.recentItems].slice(0, 20),
            notableItems: event.item_price >= minValue
              ? [event, ...state.notableItems].slice(0, 10)
              : state.notableItems,
          }));

          // River item
          const totalValue = event.delta * event.item_price;
          const riverMinValue = configService.getConfig().riverMinValue ?? 0;
          if (Math.abs(totalValue) >= riverMinValue) {
            const id = riverIdCounter++;
            patchState(store, state => ({
              riverItems: [...state.riverItems, {
                id,
                delta: event.delta,
                price: totalValue,
                name: event.item_name ?? `Item #${event.item_id}`,
              }],
            }));
            setTimeout(() => {
              patchState(store, state => ({
                riverItems: state.riverItems.filter(r => r.id !== id),
              }));
            }, 4500);
          }
        });

      // Item data changed (price/name updates)
      ws.subscribe<any>(ServiceEventType.ITEM_DATA_CHANGED)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => {
          const name = event.name || `Item #${event.item_id}`;
          toastService.info('Item Updated', `${name} — Price: ${event.price}`);
          patchState(store, state => ({ lastDataChangeId: state.lastDataChangeId + 1 }));
        });

      // Info text events
      ws.subscribe<OverlayInfoTextEvent>(ServiceEventType.OVERLAY_INFO_TEXT)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => {
          const duration = event.duration ?? 3000;
          const id = infoTextIdCounter++;
          patchState(store, state => ({
            infoTextItems: [...state.infoTextItems, { id, text: event.text, severity: event.severity, duration }],
          }));
          setTimeout(() => {
            patchState(store, state => ({
              infoTextItems: state.infoTextItems.filter(r => r.id !== id),
            }));
          }, duration);
        });
    },
  })
);
