"""Market tracking service - monitors auction house activity."""
from datetime import datetime
from typing import Optional

from Oracle.services.service_base import ServiceBase
from Oracle.services.events.market_events import MarketActionEvent, MarketAction, MarketTransactionEvent
from Oracle.services.tooling.decorators import event_handler
from Oracle.parsing.parsers.events.game_view import GameViewEvent
from Oracle.parsing.parsers.events.item_change import ItemChangeEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType
from Oracle.services.events.service_event import ServiceEventType
from Oracle.database.models import MarketTransaction, Session, Item
from Oracle.tooling.logger import Logger
from Oracle.services.events.inventory import RequestInventoryEvent
from Oracle.services.model.inventory_model import Inventory

logger = Logger("MarketService")


class MarketService(ServiceBase):
    """Service for tracking market (auction house) activity."""
    
    __SERVICE__ = {
        "name": "MarketService",
        "version": "0.0.1",
        "description": "Tracks auction house activity and item transactions",
        "requires": {}
    }
    
    def __init__(self, event_bus):
        super().__init__(event_bus)
        
        self._market_open = False
        self._inventory : Optional[Inventory] = None
        
        self._total_quantity: int = 0
        self._last_event: Optional[ItemChangeEvent] = None
        
    async def startup(self):
        """Start the service."""
        logger.info("🏪 MarketService started")
    
    async def shutdown(self):
        """Shutdown the service."""
        self._market_open = False
        logger.info("🏪 MarketService shutdown")

    async def _handle_open(self):
        """Handle market open event."""
        event  = await self.request_and_wait(
            RequestInventoryEvent(timestamp=datetime.now()),
            ServiceEventType.INVENTORY_SNAPSHOT,
            timeout=1.0
        )
        # Extract the Inventory from the snapshot and make a copy
        self._inventory = event.snapshot.data.copy()

    async def _handle_close(self):
        """Handle market close event."""
        # Flush any pending transactions
        if self._total_quantity != 0:
            await self._save_transaction(
                item_id=self._last_event.item_id,
                name=self._last_event.name,
                category=self._last_event.category,
                quantity=self._total_quantity,
                action="gained" if self._total_quantity > 0 else "lost"
            )

        self._inventory = None
        self._total_quantity = 0
        self._last_event = None
    
    async def _save_transaction(self, item_id: int, name: str, category: str, quantity: int, action: str) -> None:
        """Save market transaction to database and publish event."""
        try:
            # Get or create the item
            item = await Item.get_or_none(item_id=item_id)
            if not item:
                # Create item if it doesn't exist
                item = await Item.create(
                    item_id=item_id,
                    name=name,
                    category=category
                )
            
            transaction = await MarketTransaction.create(
                session_id=self.get_session_id(),
                timestamp=datetime.now(),
                item=item,
                quantity=quantity,
                action=action
            )
            
            # Publish transaction event
            tx_event = MarketTransactionEvent(
                timestamp=datetime.now(),
                item_id=item_id,
                quantity=quantity,
                action=action,
                transaction_id=transaction.id,
                session_id=self.get_session_id()
            )
            await self.publish(tx_event)
            
            logger.debug(f"🏪 Saved market transaction {transaction.id}")
            
        except Exception as e:
            logger.error(f"Failed to save market transaction: {e}")

    
    @event_handler(ParserEventType.GAME_VIEW)
    async def on_game_view(self, event: GameViewEvent):
        """Handle game view changes to detect market open/close."""
        # Check if the AuctionHouse is being opened
        if "Confirm" in event.view:
            # Ignore confirmation dialogs
            return
        if "AuctionHouse" in event.view:
            if not self._market_open:
                self._market_open = True

                logger.info("🏪 Market opened")
                await self._handle_open()
                
                # Publish market open event
                market_event = MarketActionEvent(
                    action=MarketAction.OPEN,
                    timestamp=datetime.now()
                )
                await self.publish(market_event)
            else:
                # Check for pending transactions, if time has passed flush them
                if self._last_event and self._total_quantity != 0:
                    time_diff = (datetime.now() - self._last_event.timestamp).total_seconds()
                    if time_diff > 1:
                        await self._save_transaction(
                            item_id=self._last_event.item_id,
                            name=self._last_event.name,
                            category=self._last_event.category,
                            quantity=self._total_quantity,
                            action="gained" if self._total_quantity > 0 else "lost"
                        )
                        self._total_quantity = 0
        else:
            # Any other view means market was closed
            if self._market_open:
                self._market_open = False
                logger.info("🏪 Market closed")

                await self._handle_close()

                # Publish market close event
                market_event = MarketActionEvent(
                    action=MarketAction.CLOSE,
                    timestamp=datetime.now()
                )
                await self.publish(market_event)
    
    @event_handler(ParserEventType.ITEM_CHANGE)
    async def on_item_change(self, event: ItemChangeEvent):
        """Handle item changes while market is open."""
        if not self._market_open or not self._inventory:
            return
        
        logger.debug(f"🏪 Detected item change during market open: {event.item_id} ({event.action}) {event.page}:{event.slot} Qty:{event.amount}")
        
        # Update the specific slot and get the total delta for this item_id
        quantity_delta = self._inventory.change_item(
            page=event.page,
            slot=event.slot,
            item_id=event.item_id,
            quantity=event.amount,
            name=event.name,
            category=event.category
        )
        
        # Determine action and actual quantity transacted
        if quantity_delta > 0:
            action = "gained"
            quantity = abs(quantity_delta)
        elif quantity_delta < 0:
            action = "lost"
            quantity = abs(quantity_delta)
        else:
            # No change in quantity, skip
            logger.debug(f"🏪 No quantity change for item {event.item_id}, skipping")
            return
        
        logger.info(f"🏪 Market transaction: {action} {quantity}x {event.name} (delta: {quantity_delta:+d})")

        # Batch multiple changes of the same item within short time frame
        if self._last_event and self._last_event.item_id == event.item_id:
            # Same item, accumulate the delta
            self._total_quantity += quantity_delta
            self._last_event = event
        else:
            # Different item or first transaction
            # Flush any pending transaction from previous item
            if self._last_event and self._total_quantity != 0:
                await self._save_transaction(
                    item_id=self._last_event.item_id,
                    name=self._last_event.name,
                    category=self._last_event.category,
                    quantity=abs(self._total_quantity),
                    action="gained" if self._total_quantity > 0 else "lost"
                )
            
            # Start batching for new item
            self._total_quantity = quantity_delta
            self._last_event = event
