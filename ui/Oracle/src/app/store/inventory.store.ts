import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { patchState, signalStore, withHooks, withMethods, withState } from '@ngrx/signals';
import { ServiceEventType } from '../models/enums';
import { Inventory } from '../models/models';
import { InventorySnapshotEvent, InventoryUpdateEvent } from '../models/service-events';
import { WebSocketService } from '../services/websocket.service';

interface InventoryState {
  inventory: Inventory | null;
}

export const InventoryStore = signalStore(
  { providedIn: 'root' },
  withState<InventoryState>({ inventory: null }),

  withMethods((store, ws = inject(WebSocketService)) => ({
    requestSnapshot(): void {
      ws.send({ type: ServiceEventType.REQUEST_INVENTORY });
    },
  })),

  withHooks({
    onInit(store, ws = inject(WebSocketService), destroyRef = inject(DestroyRef)) {
      ws.subscribe<InventoryUpdateEvent>(ServiceEventType.INVENTORY_UPDATE)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { inventory: event.inventory }));

      ws.subscribe<InventorySnapshotEvent>(ServiceEventType.INVENTORY_SNAPSHOT)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { inventory: event.snapshot.data }));
    },
  })
);
