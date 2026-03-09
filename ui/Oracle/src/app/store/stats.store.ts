import { computed, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { patchState, signalStore, withComputed, withHooks, withMethods, withState } from '@ngrx/signals';
import { ParserEventType, ServiceEventType } from '../models/enums';
import { MapStartedEvent, StatsUpdateEvent } from '../models/service-events';
import { StageAffixEvent } from '../models/parser-events';
import { AffixModel } from '../models/models';
import { WebSocketService } from '../services/websocket.service';

export interface StatsHistoryData {
  currencyPerMap: number[];
  currencyPerHour: number[];
  currencyCurrentPerHour: number[];
  currencyCurrentRaw: number[];
  expPerHour: number[];
  inventoryValue: number[];
  labels: string[];
}

function emptyHistory(): StatsHistoryData {
  return {
    currencyPerMap: [],
    currencyPerHour: [],
    currencyCurrentPerHour: [],
    currencyCurrentRaw: [],
    expPerHour: [],
    inventoryValue: [],
    labels: [],
  };
}

function pushHistory(history: StatsHistoryData, event: StatsUpdateEvent, maxPoints = 50): StatsHistoryData {
  const append = (arr: number[], val: number) => {
    const next = [...arr, val];
    return next.length > maxPoints ? next.slice(1) : next;
  };
  const len = history.currencyPerMap.length + 1;
  const labels = [...history.labels, `${len}`];
  return {
    currencyPerMap: append(history.currencyPerMap, event.currency_per_map ?? 0),
    currencyPerHour: append(history.currencyPerHour, event.currency_per_hour ?? 0),
    currencyCurrentPerHour: append(history.currencyCurrentPerHour, event.currency_current_per_hour ?? 0),
    currencyCurrentRaw: append(history.currencyCurrentRaw, event.currency_current_raw ?? 0),
    expPerHour: append(history.expPerHour, event.exp_per_hour ?? 0),
    inventoryValue: append(history.inventoryValue, event.inventory_value ?? 0),
    labels: labels.length > maxPoints ? labels.slice(1) : labels,
  };
}

interface StatsState {
  lastStats: StatsUpdateEvent | null;
  lastMap: MapStartedEvent | null;
  history: StatsHistoryData;
  currentAffixes: AffixModel[];
  currentGameView: string;
  isLogReading: boolean;
}

export const StatsStore = signalStore(
  { providedIn: 'root' },
  withState<StatsState>({
    lastStats: null,
    lastMap: null,
    history: emptyHistory(),
    currentAffixes: [],
    currentGameView: '',
    isLogReading: false,
  }),

  withComputed((store) => ({
    currencyPerHour: computed(() => store.lastStats()?.currency_per_hour ?? 0),
    expPerHour: computed(() => store.lastStats()?.exp_per_hour ?? 0),
    inventoryValue: computed(() => store.lastStats()?.inventory_value ?? 0),
    totalMaps: computed(() => store.lastStats()?.total_maps ?? 0),
    mapTimer: computed(() => store.lastStats()?.map_timer ?? 0),
  })),

  withMethods((store) => ({
    clearHistory(): void {
      patchState(store, { history: emptyHistory() });
    },
  })),

  withHooks({
    onInit(store, ws = inject(WebSocketService), destroyRef = inject(DestroyRef)) {
      // Stats updates
      ws.subscribe<StatsUpdateEvent>(ServiceEventType.STATS_UPDATE)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, state => ({
          lastStats: event,
          history: pushHistory(state.history, event),
        })));

      // Map events
      ws.subscribe<MapStartedEvent>(ServiceEventType.MAP_STARTED, ServiceEventType.MAP_STATUS)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { lastMap: event }));

      // Stage affixes
      ws.subscribe<StageAffixEvent>(ParserEventType.STAGE_AFFIX)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => {
          if (event.affixes?.length) {
            const affixes: AffixModel[] = event.affixes.map((a: any) => ({
              affix_id: a.affix_id,
              description: a.description ?? '',
            }));
            patchState(store, { currentAffixes: affixes });
          }
        });

      // View changes — also clear affixes on map change
      ws.subscribe<any>(ServiceEventType.VIEW_CHANGED)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { currentGameView: event.view ?? '' }));

      // Parser heartbeat for log-reader indicator
      const parserTypes = new Set<string>(
        Object.values(ParserEventType).filter(v => v !== ParserEventType.NONE)
      );
      let heartbeatTimeout: ReturnType<typeof setTimeout> | undefined;
      ws.subscribeAll()
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => {
          if (!parserTypes.has(event.type)) return;
          patchState(store, { isLogReading: true });
          clearTimeout(heartbeatTimeout);
          heartbeatTimeout = setTimeout(
            () => patchState(store, { isLogReading: false }),
            15000
          );
        });
    },
  })
);
