
from datetime import datetime
from enum import Enum
from collections import deque
from typing import Optional
import re

from Oracle.database.models import Player, Item, MapCompletion, MapCompletionItem, Session, Affix, MapAffix
from Oracle.parsing.parsers.events import ParserEventType, ExitLevelEvent, EnterLevelEvent, GamePauseEvent, ItemChangeEvent, GameViewEvent
from Oracle.parsing.parsers.events.stage_affix import StageAffixEvent
from Oracle.parsing.parsers.maps.map_data import MapData
from Oracle.parsing.parsers.maps import get_map_by_id
from Oracle.parsing.utils.item_db import item_lookup

from Oracle.services.event_bus import EventBus
from Oracle.services.events.inventory import InventoryUpdateEvent, RequestInventoryEvent
from Oracle.services.events.map_events import MapFinishedEvent, MapStartedEvent, MapStatsEvent, MapRecordEvent
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling.decorators import event_handler
from Oracle.services.model import InventorySnapshot, InventoryItem

from Oracle.tooling.logger import Logger
from Oracle.market.price_db import PriceDB

logger = Logger("MapService")


class MapState(str, Enum):
    """Map service FSM states."""
    IDLE = "idle"
    FARMING = "farming"
    PAUSED = "paused"
    
    def __str__(self) -> str:
        return self.value


class MapService(ServiceBase):
    
    __SERVICE__ = {
        "name": "MapService",
        "version": "0.0.1",
        "description": "Manages map state, transitions, and farming sessions",
        "requires": {
            "InventoryService": ">=0.0.1"
        }
    }

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.state = MapState.IDLE
        self.current_map_id: int | None = 0
        self.current_map_uuid: int | None = None
        self.current_map: MapData | None = None
        self.inventory: InventorySnapshot | None = None
        self.pre_enter: InventorySnapshot | None = None
        self.consumed_items: list[InventoryItem] = []  # Items consumed between pre_enter and map start
        self.map_start_time: datetime | None = None
        
        # PriceDB instance (lazy loaded)
        self._price_db = None
        
        # Affix tracking - only store first affix event per map
        self.current_affixes: list[dict] | None = None
        
        # Experience tracking
        self.map_start_exp: int = 0
        self.map_start_level: int = 0
        
        # Ring buffer for last 7 item changes
        self._recent_item_changes: deque = deque(maxlen=7)
    
    async def start_map(self, level_id: int, level_uid: int, level_type: int):
        """Handle start of a new map."""
        logger.debug(f"🗺️ Starting map: {level_id} (UID: {level_uid})")
        self.state = MapState.FARMING
        self.current_map_id = level_id
        self.current_map_uuid = level_uid
        self.map_start_time = datetime.now()
        
        # Reset affixes for new map
        self.current_affixes = None
        
        # Get MapData if available
        self.current_map = get_map_by_id(level_id)

        inventory_event = await self.request_and_wait(
            RequestInventoryEvent(timestamp=datetime.now()),
            ServiceEventType.INVENTORY_SNAPSHOT,
            timeout=1.0
        )
        self.inventory = inventory_event.snapshot if inventory_event else None

        # Calculate consumed items (difference between pre_enter and current inventory)
        self.consumed_items = self._calculate_consumed_items()

        await self.publish(MapStartedEvent(
            timestamp=self.map_start_time,
            level_id=level_id,
            level_uid=level_uid,
            level_type=level_type,
            map=self.current_map,
            consumed_items=self.consumed_items
        ))
        logger.debug(f"🗺️ Published MapStartedEvent for map: {level_id}")

    async def end_map(self):
        """Handle end of current map."""
        logger.debug(f"🗺️ Ending map: {self.current_map_id}")
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - self.map_start_time).total_seconds() if self.map_start_time else 0.0
        
        self.state = MapState.IDLE
        self.current_map_id = None
        self.current_map_uuid = None

        inventory_event = await self.request_and_wait(
            RequestInventoryEvent(timestamp=datetime.now()),
            ServiceEventType.INVENTORY_SNAPSHOT,
            timeout=1.0
        )
        end_inventory = inventory_event.snapshot if inventory_event else None

        await self.publish(MapFinishedEvent(
            timestamp=end_time,
            duration=duration,
            inventory_changes= end_inventory.compare_with(self.inventory) if self.inventory and end_inventory else {},
            map=self.current_map,
            affixes=self.current_affixes
        ))
        
        self.map_start_time = None
        self.current_map = None
        self.current_affixes = None
        self.pre_enter = None
        logger.debug(f"🗺️ Published MapFinishedEvent - Duration: {duration:.2f}s") 

    def _calculate_consumed_items(self) -> list[InventoryItem]:
        """Calculate items consumed between pre_enter and current inventory."""
        consumed_items = []
        
        if not self.pre_enter or not self.inventory:
            return consumed_items
        
        # Get differences (negative values = consumed)
        diff = self.inventory.compare_with(self.pre_enter)
        
        # Build list of consumed InventoryItems (only negative deltas)
        for item_id, delta in diff.items():
            if delta < 0:  # Item was consumed
                # Get item info from item_lookup
                item_info = item_lookup(item_id)
                
                consumed_items.append(InventoryItem(
                    item_id=item_id,
                    quantity=abs(delta),  # Make positive for display
                    name=item_info.get("name"),
                    category=item_info.get("type")
                ))
        
        if consumed_items:
            consumed_summary = ", ".join([f"{item.name or item.item_id} x{item.quantity}" for item in consumed_items])
            logger.debug(f"🗺️ Consumed items: {consumed_summary}")
        
        return consumed_items

    async def _save_affixes(self, map_completion: MapCompletion):
        """Save map affixes to database."""
        if not self.current_affixes:
            logger.debug(f"🗺️ No affixes to save for map completion {map_completion.id}")
            return
        
        logger.info(f"🗺️ Saving {len(self.current_affixes)} affixes for map completion {map_completion.id}")
        for affix_data in self.current_affixes:
            # Clean HTML tags from description
            description = affix_data.get("description", "")
            if description:
                # Remove HTML tags like <p>, </p>, <e id=507>, </e>
                description = re.sub(r'<[^>]+>', '', description)
            
            # Get or create affix
            affix, created = await Affix.get_or_create(
                affix_id=affix_data["affix_id"],
                defaults={"description": description}
            )
            if created:
                logger.debug(f"🗺️ Created new affix: {affix.affix_id}")
            
            # Get or create map-affix relation (avoid duplicates)
            _, created = await MapAffix.get_or_create(
                map_completion=map_completion,
                affix=affix
            )
        logger.info(f"🗺️ Successfully saved {len(self.current_affixes)} affixes")

    async def _save_item_changes(self, map_completion: MapCompletion, item_changes: dict[int, int], consumed: bool = False):
        """Save individual items gained/lost to database."""
        for item_id, delta in item_changes.items():
            # Get or create item
            item = await Item.get_or_none(item_id=item_id)
            if not item:
                # Get item info from lookup
                item_info = item_lookup(item_id)
                item = await Item.create(
                    item_id=item_id,
                    name=item_info.get("name") if item_info else None,
                    category=item_info.get("type") if item_info else None
                )
            
            # Calculate total price (positive or negative)
            item_price = self._price_db.get_price(item_id)
            total_price = item_price * delta
            
            # Create map completion item record
            await MapCompletionItem.create(
                map_completion=map_completion,
                item=item,
                delta=delta,
                total_price=total_price,
                consumed=consumed
            )

    @event_handler(ServiceEventType.INVENTORY_UPDATE)
    async def on_inventory_update(self, event: InventoryUpdateEvent):
        """Update internal inventory snapshot on inventory updates."""
        self.inventory = InventorySnapshot.from_inventory(event.inventory)
        logger.debug(f"🗺️ Inventory updated from database - {len(self.inventory.data)} items")

    @event_handler(ParserEventType.ITEM_CHANGE)
    async def on_item_change(self, event: ItemChangeEvent):
        """Track recent item changes in ring buffer."""
        self._recent_item_changes.append(event)
        logger.debug(f"🗺️ Tracked item change: {event.item_id} ({event.action}) - Buffer size: {len(self._recent_item_changes)}")

    @event_handler(ParserEventType.STAGE_AFFIX)
    async def on_map_affix(self, event: StageAffixEvent):
        """Capture map affixes - only store the first affix event per map."""
        logger.debug(f"🗺️ Received STAGE_AFFIX event - current_map_id: {self.current_map_id}, current_affixes: {self.current_affixes is not None}")
        
        if self.current_affixes is None:
            # Convert AffixModel instances to dicts for JSON storage
            self.current_affixes = [
                {"affix_id": affix.affix_id, "description": affix.description}
                for affix in event.affixes
            ]
            logger.info(f"🗺️ Captured {len(self.current_affixes)} affixes")
        else:
            logger.debug(f"🗺️ Ignoring subsequent affix event (already captured {len(self.current_affixes)} affixes)")

    @event_handler(ParserEventType.GAME_VIEW)
    async def on_game_view(self, event: GameViewEvent):
        """Capture pre-enter inventory snapshot when MysteryAreaCtrl view is detected."""
        if event.view.endswith('MysteryAreaCtrl'):
            logger.debug(f"🗺️ MysteryAreaCtrl detected, capturing pre-enter inventory snapshot")
            inventory_event = await self.request_and_wait(
                RequestInventoryEvent(timestamp=datetime.now()),
                ServiceEventType.INVENTORY_SNAPSHOT,
                timeout=1.0
            )
            self.pre_enter = inventory_event.snapshot if inventory_event else None
            if self.pre_enter:
                logger.debug(f"🗺️ Pre-enter snapshot captured - {len(self.pre_enter.data)} items")

    @event_handler(ParserEventType.EXIT_LEVEL, ParserEventType.ENTER_LEVEL, ParserEventType.GAME_PAUSE)
    async def handle_event(self, event: ExitLevelEvent | EnterLevelEvent | GamePauseEvent):
        if event.type == ParserEventType.ENTER_LEVEL:
            map_id = str(event.map) if event.map else event.level_id
            if  not self.current_map_id or (self.current_map_id < 1000 and event.level_id >= 1000):
                await self.start_map(event.level_id, event.level_uid, event.level_type)
                logger.debug(f"🗺️ Entered new level: {map_id}, State: {self.state}")
            elif self.current_map_id == event.level_id:
                logger.debug(f"🗺️ Re-entered current level: {map_id}, State: {self.state}")
            elif event.level_id < 1000:
                await self.end_map()
                logger.debug(f"🗺️ Entered level: {map_id}, State: {self.state}")

    @event_handler(ServiceEventType.MAP_STATS)
    async def on_map_stats(self, event: MapStatsEvent):
        """Save map completion statistics to database."""
        player = await self.get_player()
        if not player:
            logger.debug("🗺️ Ignoring map stats - no player")
            return
        
        # Calculate items gained
        items_gained = sum(1 for delta in event.item_changes.values() if delta > 0)
        
        # Get map info
        map_info = self.current_map
        
        # Get current farming session from SessionService
        farming_session = await self._get_current_farming_session()
        
        try:
            map_completion = await MapCompletion.create(
                player=player,
                session=farming_session,
                map_id=self.current_map_id or 0,
                map_name=map_info.name if map_info else None,
                map_difficulty=map_info.difficulty if map_info else None,
                started_at=self.map_start_time or datetime.now(),
                completed_at=event.timestamp,
                duration=event.duration,
                currency_gained=event.currency_gained,
                exp_gained=event.exp_gained,
                items_gained=items_gained
            )
            
            # Save affixes if present
            await self._save_affixes(map_completion)
            
            # Save individual items gained/lost
            await self._save_item_changes(map_completion, event.item_changes)
            
            # Save consumed items (entry items)
            if self.consumed_items:
                consumed_dict = {item.item_id: -item.quantity for item in self.consumed_items}
                await self._save_item_changes(map_completion, consumed_dict, consumed=True)

            # Serialize map completion like GET endpoint would return it
            map_record = {
                "id": map_completion.id,
                "player_name": player.name,
                "session_id": farming_session.id if farming_session else None,
                "map_id": map_completion.map_id,
                "map_name": map_completion.map_name,
                "map_difficulty": map_completion.map_difficulty,
                "started_at": map_completion.started_at.isoformat(),
                "completed_at": map_completion.completed_at.isoformat(),
                "duration": map_completion.duration,
                "currency_gained": map_completion.currency_gained,
                "exp_gained": map_completion.exp_gained,
                "items_gained": map_completion.items_gained,
                "description": map_completion.description
            }
            
            # Publish map record event
            record_event = MapRecordEvent(
                timestamp=datetime.now(),
                map_record=map_record
            )
            await self.publish(record_event)
            
            logger.info(f"🗺️ Saved map completion: {map_info.name if map_info else 'Unknown'} - {event.duration:.2f}s, {event.currency_gained:.2f} currency, {items_gained} items")
        except Exception as e:
            logger.error(f"🗺️ Failed to save map completion: {e}")
            logger.trace(e)

    async def _get_current_farming_session(self) -> Optional[Session]:
        """Get current farming session from SessionService via events."""
        from Oracle.services.events.service_event import ServiceEvent
        from Oracle.services.events.session_events import SessionSnapshotEvent
        
        try:
            # Request session snapshot via event
            request_event = ServiceEvent(
                timestamp=datetime.now(),
                type=ServiceEventType.REQUEST_SESSION
            )
            
            # Wait for response with 1 second timeout
            response = await self.request_and_wait(
                request_event,
                ServiceEventType.SESSION_SNAPSHOT,
                timeout=1.0
            )
            
            if response and isinstance(response, SessionSnapshotEvent):
                # If we have an active session, fetch it from database
                if response.is_active and response.session_id:
                    return await Session.get_or_none(id=response.session_id)
        except Exception as e:
            logger.debug(f"🗺️ Could not get current session: {e}")
        
        return None

    async def startup(self):
        """Initialize map service."""
        self._price_db = await PriceDB.instance()
        logger.info(f"🗺️ MapService initialized - State: {self.state}")

    async def shutdown(self):
        logger.info("🗺️ MapService shutdown")