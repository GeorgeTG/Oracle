import asyncio
from datetime import datetime, timedelta
from typing import Set, Tuple

from Oracle.parsing.parsers.events import ParserEventType
from Oracle.parsing.parsers.events.bag_modify import BagModifyEvent
from Oracle.parsing.parsers.events.item_change import ItemChangeEvent
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.parsing.parsers.events.game_view import GameViewEvent

from Oracle.services.event_bus import EventBus
from Oracle.services.events.inventory import RequestInventoryEvent, InventorySnapshotEvent, InventoryUpdateEvent
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.events.session_events import PlayerChangedEvent, SessionRestoreEvent
from Oracle.services.model import InventoryItem, InventorySnapshot, Inventory
from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling import event_handler

from Oracle.database.models import Player, InventoryItem as DBInventoryItem, Item
from Oracle.tooling.logger import Logger
from Oracle.tooling.config import Config


logger = Logger("InventoryService")


class InventoryService(ServiceBase):
    """Service that maintains current inventory state."""
    
    __SERVICE__ = {
        "name": "InventoryService",
        "version": "0.0.1",
        "description": "Maintains current inventory state and provides snapshots",
        "requires": {}
    }

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.inventory = Inventory()
        self._lock = asyncio.Lock()
        self._dirty_slots: Set[Tuple[int, int]] = set()
        self._last_change: datetime = datetime.now()
        self._config = Config()
        logger.info("🧱 InventoryService initialized")

    async def load_inventory(self, player_name: str) -> Inventory:
        """
        Load inventory from database for the given player.
        If no inventory exists, creates a new empty one.
        
        Args:
            player_name: Name of the player to load inventory for
            
        Returns:
            Inventory: Loaded or newly created inventory
        """
        async with self._lock:
            player = await self.get_player(player_name)
            
            if not player:
                logger.warning(f"🧱 Could not get/create player: {player_name}")
                self.inventory = Inventory()
                return self.inventory
            
            # Load all inventory items for this player
            db_items = await DBInventoryItem.filter(player=player).prefetch_related("item")
            
            if not db_items:
                logger.info(f"🧱 No inventory found for {player_name}, creating new")
                self.inventory = Inventory()
                return self.inventory
            
            # Reconstruct inventory from database
            self.inventory = Inventory()
            for db_item in db_items:
                self.inventory.change_item(
                    page=db_item.page,
                    slot=db_item.slot,
                    item_id=db_item.item.item_id,  # Use item_id field, not database id
                    quantity=db_item.quantity,
                    name=db_item.item.name,
                    category=db_item.item.category
                )
            
            logger.info(f"🧱 Loaded inventory for {player_name} with {len(self.inventory.slots)} items")
            return self.inventory

    async def persist_dirty_inventory(self):
        """Persist dirty inventory slots to database."""
        player_name = self.get_player_name()
        if not player_name:
            logger.warning("🧱 Cannot persist inventory: no player name")
            return
        
        player = await self.get_player(player_name)
        if not player:
            logger.warning(f"🧱 Cannot persist inventory: player {player_name} not found")
            return
        
        # Copy dirty slots while holding lock, then clear
        async with self._lock:
            if not self._dirty_slots:
                return
            dirty_slots = list(self._dirty_slots)
            self._dirty_slots.clear()
        
        logger.debug(f"🧱 Persisting {len(dirty_slots)} dirty slots")
        
        for page, slot in dirty_slots:
            key = (page, slot)
            
            # Check if slot exists in current inventory
            if key in self.inventory.slots:
                item_data = self.inventory.slots[key]
                
                # Get or create Item in database (using item_id, not id)
                db_item = await Item.get_or_none(item_id=item_data.item_id)
                if not db_item:
                    # Create the item if it doesn't exist
                    db_item = await Item.create(
                        item_id=item_data.item_id,
                        name=item_data.name,
                        category=item_data.category
                    )
                    logger.debug(f"🧱 Created new item in database: {item_data.item_id} - {item_data.name}")
                
                # Update or create InventoryItem
                db_inventory_item = await DBInventoryItem.get_or_none(
                    player=player,
                    page=page,
                    slot=slot
                )
                
                if db_inventory_item:
                    # Update existing
                    db_inventory_item.item = db_item
                    db_inventory_item.quantity = item_data.quantity
                    await db_inventory_item.save()
                else:
                    # Create new
                    await DBInventoryItem.create(
                        player=player,
                        item=db_item,
                        page=page,
                        slot=slot,
                        quantity=item_data.quantity
                    )
            else:
                # Slot is empty, delete from database if exists
                db_inventory_item = await DBInventoryItem.get_or_none(
                    player=player,
                    page=page,
                    slot=slot
                )
                if db_inventory_item:
                    await db_inventory_item.delete()
        
        logger.info(f"🧱 Saved {len(dirty_slots)} inventory changes")

    @event_handler(ServiceEventType.REQUEST_INVENTORY)
    async def on_inventory_request(self, event: RequestInventoryEvent):
        """Handle inventory snapshot requests."""
        snapshot = None

        async with self._lock:
            snapshot = InventorySnapshotEvent(
                timestamp=datetime.now(),
                snapshot=InventorySnapshot.from_inventory(self.inventory)
            )

        if snapshot:
            await self.publish(snapshot)

    @event_handler(ServiceEventType.PLAYER_CHANGED)
    async def on_player_change(self, event: PlayerChangedEvent):
        """Handle player change - load inventory from database."""
        logger.info(f"🧱 Player changed: {event.new_player}, loading inventory")
        await self.load_inventory(event.new_player)
        await self.publish(InventoryUpdateEvent(
            timestamp=datetime.now(),
            inventory=self.inventory
        ))

    @event_handler(ServiceEventType.SESSION_RESTORE)
    async def on_session_restore(self, event: SessionRestoreEvent):
        """Handle session restore - load inventory from database."""
        logger.info(f"🧱 Restoring session for {event.player_name}, loading inventory")
        await self.load_inventory(event.player_name)
        await self.publish(InventoryUpdateEvent(
            timestamp=datetime.now(),
            inventory=self.inventory
        ))

    @event_handler(ParserEventType.GAME_VIEW)
    async def on_game_view(self, event: GameViewEvent):
        """Handle game view changes - persist inventory when entering combat."""
        if "FightCtrl" in event.view:
            logger.debug("🧱 Menus closed, persisting inventory")
            await self.persist_dirty_inventory()

    @event_handler(ParserEventType.BAG_MODIFY, ParserEventType.ITEM_CHANGE)
    async def handle_event(self, event: BagModifyEvent | ItemChangeEvent):
        if event.type == ParserEventType.BAG_MODIFY:
            async with self._lock:
                self.inventory.change_item(
                    event.page,
                    event.slot,
                    event.item_id,
                    event.quantity,
                    event.name,
                    event.category
                )
                # Mark slot as dirty
                self._dirty_slots.add((event.page, event.slot))

            logger.debug(f"🧱 Updated slot P@{event.page}:S@{event.slot} -> {event.item_id}:{event.quantity}")

        elif event.type == ParserEventType.ITEM_CHANGE:
            async with self._lock:
                self.inventory.change_item(
                    event.page,
                    event.slot,
                    event.item_id,
                    event.amount,
                    event.name,
                    event.category
                )
                # Mark slot as dirty
                self._dirty_slots.add((event.page, event.slot))

            logger.debug(f"🧱 Updated slot P@{event.page}:S@{event.slot} -> {event.item_id}:{event.amount}")
        
        # Check if we should persist
        update_interval = self._config.get_value("inventory", "update_interval", 5)
        time_since_last = (datetime.now() - self._last_change).total_seconds()
        self._last_change = datetime.now()
        
        if self._dirty_slots and time_since_last >= update_interval:
            await self.persist_dirty_inventory()


    async def startup(self):
        """Initialize inventory service."""
        pass

    async def shutdown(self):
        """Shutdown inventory service - persist any remaining dirty slots."""
        logger.info("🧱 Shutting down, persisting remaining inventory changes")
        await self.persist_dirty_inventory()