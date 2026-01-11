from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from Oracle.parsing.parsers.events import ParserEventType
from Oracle.parsing.parsers.events.exp_update import ExpUpdateEvent
from Oracle.parsing.parsers.events.game_view import GameViewEvent
from Oracle.parsing.parsers.events.item_change import ItemChangeEvent

from Oracle.events import EventBus
from Oracle.services.events.inventory import InventoryUpdateEvent, RequestInventoryEvent, InventorySnapshotEvent
from Oracle.services.events.map_events import MapStartedEvent, MapFinishedEvent, MapStatsEvent
from Oracle.services.events.notification_events import NotificationEvent, NotificationSeverity
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.events.session_events import PlayerChangedEvent, SessionRestoreEvent, SessionStartedEvent
from Oracle.services.events.stats_events import StatsUpdateEvent, StatsControlEvent, StatsControlAction
from Oracle.services.model import InventorySnapshot
from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling.decorators import event_handler

from Oracle.market import PriceDB
from Oracle.tooling.logger import Logger


logger = Logger("StatsService")


class StatsService(ServiceBase):
    """Service that tracks farming statistics."""
    
    __SERVICE__ = {
        "name": "StatsService",
        "version": "0.0.1",
        "description": "Tracks farming statistics including items per map and per hour",
        "requires": {
            "InventoryService": ">=0.0.1",
            "MapService": ">=0.0.1",
            "SessionService": ">=0.0.1",
		}
    }

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        
        # PriceDB instance (lazy loaded)
        self._price_db: Optional[PriceDB] = None
        
        # Track items per hour based on snapshots
        self._last_snapshot: Optional[InventorySnapshot] = None  # Last inventory snapshot
        self._baseline_set: bool = False  # Whether initial baseline has been set
        self._items_total: Dict[int, float] = defaultdict(float)
        self.items_per_hour: Dict[int, float] = defaultdict(float)
        
        # Track currency per map and per hour
        self.currency_total: float = 0.0
        self.currency_per_map: float = 0.0
        self.currency_per_hour: float = 0.0
        self.currency_current_per_hour: float = 0.0
        self.currency_current_raw: float = 0.0
        self.current_map_entry_cost: float = 0.0
        
        # Track exp per hour (separating gains and losses)
        self._exp_gained_total: float = 0.0  # Total XP gained
        self._exp_lost_total: float = 0.0    # Total XP lost (from deaths)
        self._last_exp_percent: Optional[int] = None
        self._last_level: Optional[int] = None
        self.exp_per_hour: float = 0.0  # Net XP per hour (gained - lost)
        
        # Track exp per map
        self._map_start_exp: int = 0
        self._map_start_level: int = 0
        self._map_exp_gained: float = 0.0
        
        # Track session statistics
        self._session_start: datetime = datetime.now()
        self._map_start: datetime = datetime.now()
        self._total_maps: int = 0
        self._total_time: float = 0.0  # Total farming time in seconds
        
        # Timestamp of last snapshot request (for throttling)
        self._last_snapshot_time: Optional[datetime] = None
        self._snapshot_interval: float = 1.0  # Seconds between snapshots
        
        # Flag to track if we've started farming after player join
        self._first_map_after_join: bool = True

        # Current game view
        self._current_view: str = "unknown"

        logger.info("📊 StatsService initialized")

    @event_handler(ServiceEventType.MAP_STARTED)
    async def on_map_started(self, event: MapStartedEvent):
        """Track when a map starts."""
        logger.info(f"📊 Map started: {event.level_id}")
        if event.map:
            logger.info(f"📊 Map details: {event.map.name} [{event.map.difficulty}]")

        self._map_start = event.timestamp
        
        # Capture exp state at map start
        self._map_start_exp = self._last_exp_percent or 0
        self._map_start_level = self._last_level or 1
        self._map_exp_gained = 0.0
        
        # Calculate entry cost from consumed items
        total = 0.0

        assert self._price_db is not None # should be initialized already

        for item in event.consumed_items:
            price = self._price_db.get_price(item.item_id)
            total += (price * item.quantity)
            logger.info(f"📊 Consumed item {item.item_id} {item.name} x{item.quantity} (-{price * item.quantity:.2f})")

        logger.info(f"📊 Total map entry cost: {total:.2f}")
        self.current_map_entry_cost = total
        self.currency_total -= total
        self.currency_current_raw = -total  # Start current raw at negative entry cost
        logger.debug(f"📊 Currency after entry cost: {self.currency_total:.2f}")

    @event_handler(ServiceEventType.MAP_FINISHED)
    async def on_map_finished(self, event: MapFinishedEvent):
        """Track when a map finishes and update statistics."""
        logger.debug(f"📊 Map finished - Duration: {event.duration:.2f}s, Changes: {len(event.inventory_changes)}")

        self._total_maps += 1
        self._total_time += event.duration

        # Request final snapshot to capture any last changes
        await self.request_and_wait(
            RequestInventoryEvent(timestamp=datetime.now()),
            ServiceEventType.INVENTORY_SNAPSHOT,
            timeout=1.0
        )

        # Calculate exp gained during this map
        current_exp = self._last_exp_percent or 0
        current_level = self._last_level or 1
        
        if current_level > self._map_start_level:
            # Level up occurred - approximate the exp gained
            # This is rough since we don't track max exp per level here
            self._map_exp_gained = current_exp + (current_level - self._map_start_level) * 10000  # Rough estimate
        elif current_level == self._map_start_level:
            # Same level, just exp difference
            self._map_exp_gained = max(0, current_exp - self._map_start_exp)
        else:
            # Level decreased (shouldn't happen)
            self._map_exp_gained = 0.0
        
        logger.debug(f"📊 Total maps: {self._total_maps}, Total time: {self._total_time:.2f}s, Exp gained: {self._map_exp_gained:.0f}")

        assert self._price_db is not None # should be initialized already
        
        # calculate currency gained during the map using the inventory changes
        currency_drops = sum( self._price_db.get_price(item_id) * delta for item_id, delta in event.inventory_changes.items())
        
        # Calculate net currency (drops - entry cost)
        currency_gained = currency_drops - self.current_map_entry_cost

        # Publish MapStatsEvent
        map_stats_event = MapStatsEvent(
            timestamp=datetime.now(),
            duration=event.duration,
            item_changes=event.inventory_changes,
            currency_gained=currency_gained,
            exp_gained=self._map_exp_gained,
            affixes=event.affixes
        )
        await self.publish(map_stats_event)

        # Publish updated stats after map completion
        await self._publish_stats()
        
        
        # Log map completion with details
        if event.map:
            logger.info(
                f"📊 Map finished: {event.map.name} [{event.map.difficulty}] - "
                f"Duration: {event.duration:.2f}s, Currency: {currency_gained:.2f} - "
                f"Total: {self._total_maps} maps, {self._total_time:.2f}s"
            )
        else:
            logger.info(
                f"📊 Map finished: Unknown - "
                f"Duration: {event.duration:.2f}s, Currency: {currency_gained:.2f} - "
                f"Total: {self._total_maps} maps, {self._total_time:.2f}s"
            )

    @event_handler(ParserEventType.GAME_VIEW)
    async def on_game_view(self, event: GameViewEvent):
        """Track game view changes."""
        self._current_view = event.view

    @event_handler(ParserEventType.ITEM_CHANGE)
    async def on_item_change(self, event: ItemChangeEvent):
        """Check if enough time has passed and request snapshot if needed."""
        now = datetime.now()
        
        # Check if we should take a snapshot (throttle to every 5 seconds)
        if self._last_snapshot_time is None:
            # First time, take snapshot immediately
            should_snapshot = True
        else:
            elapsed = (now - self._last_snapshot_time).total_seconds()
            should_snapshot = elapsed >= self._snapshot_interval
        
        if should_snapshot:
            logger.debug(f"📊 Item changed, requesting snapshot (last: {self._last_snapshot_time})")
            self._last_snapshot_time = now
            await self._request_snapshot()
        elif self._last_snapshot_time is not None:
            elapsed = (now - self._last_snapshot_time).total_seconds()
            logger.debug(f"📊 Item changed but throttled ({elapsed:.1f}s < {self._snapshot_interval}s)")
        else:
            logger.warning("📊 Item changed but last_snapshot_time is None unexpectedly")

    @event_handler(ServiceEventType.INVENTORY_SNAPSHOT)
    async def on_inventory_snapshot(self, event: InventorySnapshotEvent):
        """Process inventory snapshot and calculate differences."""
        await self._process_snapshot(event)

    @event_handler(ParserEventType.EXP_UPDATE)
    async def on_exp_update(self, event: ExpUpdateEvent):
        """Track experience changes for per-hour calculations."""
        # Note: experience is a raw value, not a percentage
        # Calculate exp change since last update
        if self._last_exp_percent is not None and self._last_level is not None:
            exp_change = 0
            
            # Handle level up - experience resets to 0 or low value
            if event.level > self._last_level:
                # Level up occurred - we gained the remaining exp in previous level + new level exp
                # Since we don't know the max exp per level, just track the raw difference
                exp_change = event.experience  # New level's exp
                # We lost track of the exp from previous level, but that's acceptable
            elif event.level == self._last_level:
                # Same level, track the difference (can be positive or negative)
                exp_change = event.experience - self._last_exp_percent
            # If level decreased (death with level loss), treat as XP loss
            elif event.level < self._last_level:
                # Level decreased - significant XP loss
                exp_change = -(self._last_exp_percent - event.experience)  # Negative value
            
            # Track gains and losses separately
            if exp_change > 0:
                self._exp_gained_total += exp_change
                logger.debug(f"📊 EXP: +{exp_change} gained (total gained: {self._exp_gained_total:.0f})")
            elif exp_change < 0:
                self._exp_lost_total += abs(exp_change)
                logger.warning(f"💀 EXP LOSS: {exp_change} (total lost: {self._exp_lost_total:.0f})")
            
            # Calculate net XP and per-hour rate
            net_exp = self._exp_gained_total - self._exp_lost_total
            hours_elapsed = (datetime.now() - self._session_start).total_seconds() / 3600.0
            if hours_elapsed > 0:
                self.exp_per_hour = net_exp / hours_elapsed
            
            if exp_change != 0:
                logger.debug(
                    f"📊 XP Summary: Net={net_exp:.0f} "
                    f"(+{self._exp_gained_total:.0f} / -{self._exp_lost_total:.0f}), "
                    f"Rate: {self.exp_per_hour:.1f}/h"
                )
        
        # Update last known values
        self._last_exp_percent = event.experience
        self._last_level = event.level

    @event_handler(ServiceEventType.INVENTORY_UPDATE)
    async def on_inventory_update(self, event: InventoryUpdateEvent):
        """Handle full inventory update (e.g., loaded from DB)"""
        logger.info("📊 [StatsService] Inventory loaded from DB")
        
        # Set the loaded inventory as the new baseline
        self._last_snapshot = InventorySnapshot.from_inventory(event.inventory)
        self._baseline_set = True  # Mark baseline as already set
        
        # Set flag to reset currency on first map
        self._first_map_after_join = True
        
        logger.info(f"📊 Stats reset complete. New baseline: {len(event.inventory.slots)} slots")

    @event_handler(ServiceEventType.STATS_CONTROL)
    async def on_stats_control(self, event: StatsControlEvent):
        """Handle stats control events."""
        logger.info(f"📊 Control action: {event.action}")
        
        if event.action == StatsControlAction.RESTART:
            await self._restart_tracking()

    @event_handler(ServiceEventType.SESSION_STARTED)
    async def on_session_started(self, event: SessionStartedEvent):
        """Handle session started - reset stats for new session."""
        logger.info(f"📊 Session started for {event.player_name} - Resetting stats")
        await self._restart_tracking()

    @event_handler(ServiceEventType.PLAYER_CHANGED)
    async def on_player_changed(self, event: PlayerChangedEvent):
        """Handle player change - SESSION_STARTED will handle the reset."""
        logger.info(f"📊 Player changed: {event.old_player} → {event.new_player}")
        # No reset here - SESSION_STARTED event will trigger reset

    @event_handler(ServiceEventType.SESSION_RESTORE)
    async def on_session_restore(self, event: SessionRestoreEvent):
        """Handle session restore - restore stats from database."""
        logger.info(f"📊 Restoring stats from session {event.session_id}...")
        logger.debug(
            f"📊 Restore values - "
            f"exp_per_hour={event.exp_per_hour}, "
            f"exp_gained_total={event.exp_gained_total}, "
            f"exp_lost_total={event.exp_lost_total}, "
            f"started_at={event.started_at}"
        )
        
        # Restore stats from event
        self._total_maps = event.total_maps
        self._total_time = event.total_time
        self.currency_total = event.currency_total
        self.currency_per_hour = event.currency_per_hour
        self.currency_per_map = event.currency_per_map
        self.exp_per_hour = event.exp_per_hour
        self._exp_total = event.exp_total
        self._exp_gained_total = event.exp_gained_total
        self._exp_lost_total = event.exp_lost_total
        
        # Restore session start time (convert to naive datetime if needed)
        started_at = event.started_at
        if started_at.tzinfo is not None:
            # Convert timezone-aware to naive datetime
            started_at = started_at.replace(tzinfo=None)
        self._session_start = started_at
        
        logger.info(
            f"📊 Restored stats - "
            f"{self._total_maps} maps, "
            f"{self._total_time:.2f}s, "
            f"{self.currency_per_hour:.2f}/h, "
            f"{self.exp_per_hour:.0f} exp/h"
        )
        
        # Publish initial stats to UI
        await self._publish_stats()

    async def _request_snapshot(self):
        """Request inventory snapshot."""
        request = RequestInventoryEvent(timestamp=datetime.now())
        await self.publish(request)
        logger.debug("📊 [StatsService] Published inventory snapshot request")

    async def _restart_tracking(self):
        """Restart stats tracking - reset all statistics."""
        
        self._last_snapshot = None
        self._baseline_set = False
        self._last_snapshot_time = None
        self._items_total.clear()
        self.items_per_hour.clear()
        self.currency_total = 0.0
        self.currency_per_map = 0.0
        self.currency_per_hour = 0.0
        self.currency_current_per_hour = 0.0
        self.currency_current_raw = 0.0
        self._exp_total = 0.0
        self._last_exp_percent = None
        self._last_level = None
        self.exp_per_hour = 0.0
        self._session_start = datetime.now()
        self._total_maps = 0
        self._total_time = 0.0
        logger.info("📊 [StatsService] Stats tracking restarted - All data reset")
        
        # Send notification to UI
        await self.publish(NotificationEvent(
            timestamp=datetime.now(),
            title="Stats Reset",
            content="All statistics have been reset. Starting fresh tracking.",
            severity=NotificationSeverity.INFO,
            duration=3000
        ))
        
        await self._publish_stats()

    async def _process_snapshot(self, event: InventorySnapshotEvent):
        """Process inventory snapshot and calculate differences."""
        current_snapshot = event.snapshot  # InventorySnapshot object
        total_items = sum(item.quantity for item in current_snapshot.data.slots.values())
        
        logger.debug(f"📊 Processing snapshot with {len(current_snapshot.data.slots)} slots, {total_items} total items")
        logger.debug(f"📊 _last_snapshot is None: {self._last_snapshot is None}, _baseline_set: {self._baseline_set}")

        if self._last_snapshot is None:
            # Very first snapshot - set as baseline
            logger.debug("📊 [StatsService] First snapshot received - setting as baseline")
            self._last_snapshot = current_snapshot
            return
        
        if not self._baseline_set:
            # Second snapshot after baseline - skip this one (would count all DB items)
            logger.debug("📊 [StatsService] Skipping first comparison after baseline (loaded from DB)")
            self._baseline_set = True
            self._last_snapshot = current_snapshot
            return

        is_fighting = "FightCtrl" in self._current_view
        if not is_fighting:
            logger.debug("📊 Not in fighting view - skipping snapshot processing")
            self._last_snapshot = current_snapshot
            return
        
        assert self._price_db is not None # should be initialized already

        # Normal operation - calculate differences
        item_changes = current_snapshot.compare_with(self._last_snapshot)
        if item_changes:
            currency_gained = 0.0
            
            # Process each item change
            for item_id, delta in item_changes.items():
                # Update running totals
                self._items_total[item_id] += delta
                
                # Calculate currency value
                price = self._price_db.get_price(item_id)
                currency_gained += price * delta
            
            # Update currency total
            self.currency_total += currency_gained
            self.currency_current_raw += currency_gained
            
            # Recalculate rates
            hours_elapsed = (datetime.now() - self._session_start).total_seconds() / 3600.0
            if hours_elapsed > 0:
                for item_id, total in self._items_total.items():
                    self.items_per_hour[item_id] = total / hours_elapsed
                self.currency_per_hour = self.currency_total / hours_elapsed
            
            if self._total_maps > 0:
                self.currency_per_map = self.currency_total / self._total_maps
            
            logger.debug(f"📊 Snapshot diff: currency={currency_gained:.2f}, items={len(item_changes)}")
            logger.debug(f"📊 Item changes: {[(item_id, delta, self._price_db.get_price(item_id)) for item_id, delta in item_changes.items()]}")
            
            # Publish stats update after processing snapshot
            await self._publish_stats()
        
        # Store current snapshot for next comparison
        self._last_snapshot = current_snapshot

    async def _publish_stats(self):
        """Publish current statistics."""
        session_duration = (datetime.now() - self._session_start).total_seconds()
        map_duration = (datetime.now() - self._map_start).total_seconds()
        current_per_hour = self.currency_current_raw / (map_duration / 3600.0) if map_duration > 0 else 0.0
        self.currency_current_per_hour = current_per_hour
        logger.info(
            f"📊 Publishing stats update - "
            f"Total: {self.currency_per_hour:.2f}/h, "
            f"Current: {self.currency_current_raw:.2f} | {current_per_hour:.2f}/h, "
            f"Per Map: {self.currency_per_map:.2f}/map, "
        )
        event = StatsUpdateEvent(
            timestamp=datetime.now(),
            total_maps=self._total_maps,
            total_time=self._total_time,
            session_duration=session_duration,
            items_per_map={},  # Deprecated, no longer tracking
            items_per_hour=dict(self.items_per_hour),
            exp_per_hour=self.exp_per_hour,
            exp_gained_total=self._exp_gained_total,
            exp_lost_total=self._exp_lost_total,
            currency_per_map=self.currency_per_map,
            currency_per_hour=self.currency_per_hour,
            currency_total=self.currency_total,
            currency_current_per_hour=current_per_hour,
            currency_current_raw=self.currency_current_raw,
            map_timer=map_duration
        )
        
        await self.publish(event)
        logger.debug(
            f"📊 [StatsService] Published stats update - "
            f"{self._total_maps} maps, {len(self.items_per_hour)} items tracked, "
            f"exp: {self.exp_per_hour:.0f}/h, "
            f"current currency: {self.currency_current_raw:.2f}, "
            f"current: {current_per_hour:.2f}/h "
            f"currency: {self.currency_per_hour:.2f}/h "
            f"per map: {self.currency_per_map:.2f}/map "
        )

    async def startup(self):
        """Initialize stats service."""
        # Stats will be restored via SessionRestoreEvent if there's an active session
        logger.info("📊 StatsService started, waiting for session...")
        self._price_db = await PriceDB.instance()

    async def shutdown(self):
        logger.info("📊 StatsService shutdown")
        logger.info(f"📊 Session stats - Maps: {self._total_maps}, Time: {self._total_time:.2f}s")

    def get_stats(self) -> dict:
        """Get current statistics summary."""
        return {
            "total_maps": self._total_maps,
            "total_time": self._total_time,
            "session_duration": (datetime.now() - self._session_start).total_seconds(),
            "items_per_hour": dict(self.items_per_hour),
            "exp_per_hour": self.exp_per_hour,
            "currency_per_map": self.currency_per_map,
            "currency_per_hour": self.currency_per_hour,
        }

    def __repr__(self) -> str:
        hours = self._total_time / 3600.0
        return (
            f"<StatsService maps={self._total_maps} "
            f"time={self._total_time:.1f}s ({hours:.2f}h) "
            f"tracked_items={len(self.items_per_hour)} "
            f"exp_rate={self.exp_per_hour:.0f}/h "
            f"currency={self.currency_per_hour:.2f}/h>"
        )
