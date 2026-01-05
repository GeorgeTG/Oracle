"""
Fix item names in database using item_db lookup.
Updates all items that have NULL names or default "Item_XXX" names.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Oracle.database import init_db, close_db
from Oracle.database.models import Item
from Oracle.parsing.utils.item_db import load_items, item_lookup
from Oracle.tooling.paths import get_base_path
from Oracle.tooling.logger import Logger

logger = Logger("FixItemNames")


async def fix_item_names():
    """Fix all item names in database."""
    # Initialize database
    db_path = get_base_path() / "oracle.db"
    await init_db(str(db_path))
    logger.info(f"📦 Database initialized at {db_path}")
    
    # Load item database
    load_items()
    logger.info("📚 Item database loaded")
    
    # Get all items
    items = await Item.all()
    logger.info(f"🔍 Found {len(items)} items in database")
    
    updated_count = 0
    null_count = 0
    
    for item in items:
        needs_update = False
        new_name = None
        
        # Check if name is NULL or starts with "Item_"
        if item.name is None or item.name.startswith("Item_"):
            # Try to lookup from item_db
            lookup_result = item_lookup(item.item_id)
            db_name = lookup_result.get("name")
            
            if db_name:
                new_name = db_name
                needs_update = True
                logger.debug(f"✅ Item {item.item_id}: '{item.name}' -> '{new_name}'")
            else:
                # Set to NULL if not found in item_db
                if item.name is not None:
                    new_name = None
                    needs_update = True
                    null_count += 1
                    logger.debug(f"❌ Item {item.item_id}: '{item.name}' -> NULL (not in item_db)")
        
        if needs_update:
            item.name = new_name
            await item.save()
            updated_count += 1
    
    logger.info(f"✨ Updated {updated_count} items")
    logger.info(f"   - {updated_count - null_count} items got proper names")
    logger.info(f"   - {null_count} items set to NULL (not found in item_db)")
    
    # Close database
    await close_db()
    logger.info("✅ Done!")


if __name__ == "__main__":
    asyncio.run(fix_item_names())
