import json
from typing import Dict, Mapping, Optional
from Oracle.tooling.paths import get_config_path

ITEM_DB: Dict[str, Dict[str, Optional[str]]] = {}


def load_items():
    """Load item names from price_table.json (fallback for initial load)."""
    global ITEM_DB
    path = get_config_path("price_table.json")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            price_data = json.load(f)
            ITEM_DB = {
                str(base_id): {
                    "name": item_data.get("name"),
                    "type": item_data.get("category")
                }
                for base_id, item_data in price_data.items()
            }
    else:
        ITEM_DB = {}


async def load_items_from_db():
    """Load item names from database (preferred method)."""
    global ITEM_DB
    from Oracle.database.models import Item

    items = await Item.all()
    ITEM_DB = {
        str(item.item_id): {
            "name": item.name,
            "type": item.category
        }
        for item in items
    }


def update_item(item_id: int, name: Optional[str] = None, category: Optional[str] = None):
    """Update a single item in the cache."""
    global ITEM_DB
    key = str(item_id)
    if key not in ITEM_DB:
        ITEM_DB[key] = {"name": None, "type": None}
    if name is not None:
        ITEM_DB[key]["name"] = name
    if category is not None:
        ITEM_DB[key]["type"] = category


def item_lookup(base_id: int) -> Mapping[str, Optional[str]]:
    if not ITEM_DB:
        load_items()
    return ITEM_DB.get(str(base_id), {"name": None, "type": None})
