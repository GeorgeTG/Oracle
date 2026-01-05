"""Async price database utility for item pricing."""

import json
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from Oracle.database.models import PriceDataBaseRevision, PriceSource, Item
from Oracle.parsing.utils.item_db import item_lookup
from Oracle.services.event_bus import EventBus
from Oracle.services.events import ServiceEventType, ItemDataChangedEvent
from Oracle.tooling.config import Config
from Oracle.tooling.logger import Logger
from Oracle.tooling.paths import get_base_path
from Oracle.tooling.singleton import Singleton


logger = Logger("PriceDB")


@Singleton
class PriceDB:
    """Async singleton class for item price lookups with caching."""
    
    def __init__(self):
        """Initialize the price database."""
        self._cache: Dict[int, float] = {}
        self._loaded: bool = False
        self._event_bus: Optional[EventBus] = None
        
        logger.info("💰 PriceDB instance created")
    
    async def initialize(self):
        """Initialize async components (called by Singleton decorator)."""
        # Get EventBus singleton instance
        self._event_bus = await EventBus.instance()
        
        # Subscribe to item data changes
        await self._event_bus.subscribe(
            self._on_item_data_changed,
            ServiceEventType.ITEM_DATA_CHANGED
        )
        logger.debug("💰 PriceDB event handlers registered")
    
    async def refresh_pricelist(self) -> bool:
        """
        Refresh price list from remote source, fallback to local if failed.
        
        Returns:
            True if prices were loaded successfully, False otherwise
        """
        config = Config()
        price_db_config = config.get("price_db")
        remote_url = price_db_config.get("url")
        
        # Try to fetch from remote first
        if remote_url:
            logger.info(f"💰 Attempting to fetch prices from remote: {remote_url}")
            success = await self._load_remote_prices(remote_url)
            if success:
                await self._save_revision(PriceSource.REMOTE)
                return True
            logger.warning(f"💰 Failed to fetch from remote, falling back to local")
        
        # Fallback to local prices
        logger.info("💰 Loading prices from local file")
        success = await self._load_local_prices()
        if success:
            await self._save_revision(PriceSource.LOCAL)
        return success
    
    async def _load_remote_prices(self, url: str) -> bool:
        """
        Load prices from remote URL.
        
        Args:
            url: Remote URL to fetch price data from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"💰 Remote fetch failed with status {response.status}")
                        return False
                    
                    data = await response.json()
                    
                    # Parse and cache prices
                    self._cache.clear()
                    for item_id_str, item_data in data.items():
                        try:
                            item_id = int(item_id_str)
                            price = float(item_data.get("price", 0.0))
                            self._cache[item_id] = price
                        except (ValueError, TypeError) as e:
                            logger.warning(f"💰 Invalid price data for item {item_id_str}: {e}")
                    
                    logger.info(f"💰 Loaded {len(self._cache)} item prices from remote")
                    self._loaded = True
                    return True
                    
        except aiohttp.ClientError as e:
            logger.error(f"💰 HTTP error fetching remote prices: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"💰 JSON decode error: {e}")
        except Exception as e:
            logger.error(f"💰 Unexpected error fetching remote prices: {e}")
        
        return False
    
    async def _load_local_prices(self) -> bool:
        """Load prices from local price_table.json file.
        Only loads if file has been modified since last LOCAL revision.
        Updates Item table with prices during load.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            price_file = get_base_path() / "price_table.json"
            
            if not price_file.exists():
                logger.warning(f"💰 Price table not found at {price_file}")
                return False
            
            # Get file modification time (make it naive to match database timestamps)
            file_stat = price_file.stat()
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Check latest LOCAL revision
            latest_local_revision = await PriceDataBaseRevision.filter(
                source=PriceSource.LOCAL
            ).order_by('-timestamp').first()
            
            if latest_local_revision:
                # Convert database timestamp (UTC) to local naive datetime for comparison
                revision_time = latest_local_revision.timestamp
                if revision_time.tzinfo is not None:
                    # Convert UTC to local time, then make naive
                    revision_time = revision_time.astimezone().replace(tzinfo=None)
                
                logger.debug(f"💰 Latest LOCAL revision: {latest_local_revision.timestamp}, comparing with file mtime: {file_mtime}")
                
                # Only load if file is newer than last revision
                if file_mtime <= revision_time:
                    logger.info(f"💰 Local price file unchanged since last load ({revision_time})")
                    # Load from database instead
                    await self._load_prices_from_db()
                    return False
            
            # Load from file
            logger.info(f"💰 Loading prices from file (modified: {file_mtime})")
            with open(price_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert string keys to integers and extract prices
            self._cache.clear()
            
            for item_id_str, item_data in data.items():
                try:
                    item_id = int(item_id_str)
                    price = float(item_data.get("price", 0.0))
                    
                    # Get name and category from item_db
                    item_info = item_lookup(item_id)
                    name = item_info.get("name")
                    category = item_info.get("type")
                    
                    # Cache the price
                    self._cache[item_id] = price
                    
                    # Update or create item in database
                    item = await Item.get_or_none(item_id=item_id)
                    if item:
                        # Update existing item
                        item.price = price
                        if name:
                            item.name = name
                        if category:
                            item.category = category
                        await item.save()
                    else:
                        # Create new item
                        await Item.create(
                            item_id=item_id,
                            name=name,
                            category=category,
                            price=price
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(f"💰 Invalid price data for item {item_id_str}: {e}")
            
            logger.info(f"💰 Loaded {len(self._cache)} item prices from local file and updated database")
            self._loaded = True
            return True
            
        except Exception as e:
            logger.error(f"💰 Failed to load local price table: {e}")
            return False
    
    async def _load_prices_from_db(self):
        """Load prices from Item table into cache."""
        items = await Item.all()
        
        for item in items:
            if item.price > 0:
                self._cache[item.item_id] = item.price
        
        logger.info(f"💰 Loaded {len(self._cache)} prices from database")
        self._loaded = True
    
    async def _save_revision(self, source: str):
        """
        Save a price database revision record.
        
        Args:
            source: Source of the price data (PriceSource.LOCAL or PriceSource.REMOTE)
        """
        try:
            await PriceDataBaseRevision.create(
                source=source,
                item_count=len(self._cache)
            )
            logger.info(f"💰 Saved price DB revision: {source}, {len(self._cache)} items")
        except Exception as e:
            logger.error(f"💰 Failed to save price DB revision: {e}")
    
    def get_price(self, item_id: int) -> float:
        """
        Get the price for an item ID.
        
        Args:
            item_id: The item ID to look up
            
        Returns:
            The price of the item, or 0.0 if not found
        """
        if not self._loaded:
            logger.warning("💰 Price DB not loaded yet, returning 0.0")
            return 0.0
        
        price = self._cache.get(item_id)
        if price is None:
            logger.debug(f"💰 Item {item_id} not found in price table")
            return 0.0
        return price
    
    async def reload(self):
        """Reload prices by calling refresh_pricelist."""
        self._cache.clear()
        self._loaded = False
        await self.refresh_pricelist()
    
    async def _on_item_data_changed(self, event: ItemDataChangedEvent):
        """
        Handle item data changed event.
        Updates the price cache when an item is modified via API.
        
        Args:
            event: ItemDataChangedEvent containing updated item data
        """
        if event.price is not None and event.price >= 0:
            self._cache[event.item_id] = event.price
            logger.info(f"💰 Updated cache for item {event.item_id}: {event.name} -> {event.price}")
        else:
            # If price is removed or invalid, remove from cache
            if event.item_id in self._cache:
                del self._cache[event.item_id]
                logger.info(f"💰 Removed item {event.item_id} from cache")
