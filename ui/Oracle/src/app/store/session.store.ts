import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { patchState, signalStore, withHooks, withState } from '@ngrx/signals';
import { ServiceEventType } from '../models/enums';
import { MapRecordEvent, SessionFinishedEvent, SessionRestoreEvent, SessionStartedEvent } from '../models/service-events';
import { WebSocketService } from '../services/websocket.service';

interface SessionState {
  currentSession: SessionStartedEvent | null;
  isActive: boolean;
  lastMapRecord: MapRecordEvent | null;
}

export const SessionStore = signalStore(
  { providedIn: 'root' },
  withState<SessionState>({
    currentSession: null,
    isActive: false,
    lastMapRecord: null,
  }),

  withHooks({
    onInit(store, ws = inject(WebSocketService), destroyRef = inject(DestroyRef)) {
      ws.subscribe<SessionStartedEvent>(ServiceEventType.SESSION_STARTED)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { currentSession: event, isActive: true }));

      ws.subscribe<SessionFinishedEvent>(ServiceEventType.SESSION_FINISHED)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(() => patchState(store, { isActive: false }));

      ws.subscribe<SessionRestoreEvent>(ServiceEventType.SESSION_RESTORE)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, {
          currentSession: {
            session_id: event.session_id,
            player_name: event.player_name,
            started_at: event.started_at,
            type: event.type,
            timestamp: event.timestamp,
          } as SessionStartedEvent,
          isActive: true,
        }));

      ws.subscribe<MapRecordEvent>(ServiceEventType.MAP_RECORD)
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe(event => patchState(store, { lastMapRecord: event }));
    },
  })
);
