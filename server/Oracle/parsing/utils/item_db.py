import json
from pathlib import Path
from Oracle.tooling.paths import get_config_path

ITEM_DB = {}

def load_items():
    """Load item names from price_table.json instead of en_id_table.json"""
    global ITEM_DB
    path = get_config_path("price_table.json")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            price_data = json.load(f)
            # Convert price_table format to item_db format
            # price_table has {base_id: {"name": "...", "category": "...", ...}}
            ITEM_DB = {
                str(base_id): {
                    "name": item_data.get("name"),
                    "type": item_data.get("category")
                }
                for base_id, item_data in price_data.items()
            }
    else:
        ITEM_DB = {}


def item_lookup(base_id: int) -> dict:
    if not ITEM_DB:
        load_items()
    return ITEM_DB.get(str(base_id), {"name": None, "type": None})
