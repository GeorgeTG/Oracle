"""Price database utility for item pricing."""

import json
from pathlib import Path
from typing import Optional, Dict
from Oracle.tooling.paths import get_base_path
from Oracle.tooling.logger import Logger

logger = Logger("PriceDB")


class PriceDB:
    """Singleton class for item price lookups with caching."""
    
    _instance: Optional["PriceDB"] = None
    _cache: Dict[int, float] = {}
    _loaded: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the price database."""
        if not self._loaded:
            self._load_prices()
    
    def _load_prices(self):
        """Load prices from price_table.json."""
        try:
            price_file = get_base_path() / "price_table.json"
            
            if not price_file.exists():
                logger.warning(f"Price table not found at {price_file}")
                self._loaded = True
                return
            
            with open(price_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert string keys to integers and extract prices
            for item_id_str, item_data in data.items():
                try:
                    item_id = int(item_id_str)
                    price = float(item_data.get("price", 0.0))
                    self._cache[item_id] = price
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid price data for item {item_id_str}: {e}")
            
            logger.info(f"💰 Loaded {len(self._cache)} item prices from {price_file}")
            self._loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load price table: {e}")
            self._loaded = True
    
    def get_price(self, item_id: int) -> float:
        """
        Get the price for an item ID.
        
        Args:
            item_id: The item ID to look up
            
        Returns:
            The price of the item, or 0.0 if not found
        """
        price = self._cache.get(item_id)
        if price is None:
            logger.warning(f"⚠️ Item {item_id} not found in price table")
            return 0.0
        return price
    
    def reload(self):
        """Reload prices from the file."""
        self._cache.clear()
        self._loaded = False
        self._load_prices()


def get_price(item_id: int) -> float:
    """
    Get the price for an item ID.
    
    Args:
        item_id: The item ID to look up
        
    Returns:
        The price of the item, or 0.0 if not found
    """
    db = PriceDB()
    return db.get_price(item_id)
