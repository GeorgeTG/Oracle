"""Inventory API router - handles inventory endpoints."""
from typing import Optional
from fastapi import APIRouter, Query

from Oracle.database.models import InventoryItem
from Oracle.parsing.utils.item_db import item_lookup
from Oracle.tooling.logger import Logger

logger = Logger("InventoryRouter")
router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    responses={
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "",
    summary="Get inventory",
    description="""Retrieve player inventory organized by player name, page, and slots.
    
    Returns a hierarchical structure: player -> page -> slots with item details.
    """
)
async def get_inventory(
    player_name: Optional[str] = Query(None, description="Filter by player name")
):
    """Get inventory organized by player -> page -> slot with item details."""
    try:
        # Build query
        query = InventoryItem.all().prefetch_related("player", "item")
        
        # Apply player filter if provided
        if player_name:
            query = query.filter(player__name=player_name)
        
        # Get all inventory items ordered by player, page, slot
        items = await query.order_by("player__name", "page", "slot")
        
        # Organize data: player_name -> page -> slots[]
        inventory_tree = {}
        
        for inv_item in items:
            player = inv_item.player.name if inv_item.player else "Unknown"
            page = inv_item.page
            
            # Initialize player if not exists
            if player not in inventory_tree:
                inventory_tree[player] = {}
            
            # Initialize page if not exists
            if page not in inventory_tree[player]:
                inventory_tree[player][page] = []
            
            # Add slot data with item name lookup
            item_name = "Unknown Item"
            if inv_item.item:
                # Try to get name from Item model first
                if inv_item.item.name:
                    item_name = inv_item.item.name
                else:
                    # Fallback to item_db lookup
                    lookup_result = item_lookup(inv_item.item.item_id)
                    item_name = lookup_result.get("name") or f"Item #{inv_item.item.item_id}"
            
            inventory_tree[player][page].append({
                "slot": inv_item.slot,
                "item_name": item_name,
                "item_id": inv_item.item.item_id if inv_item.item else None,
                "quantity": inv_item.quantity,
                "timestamp": inv_item.timestamp.isoformat()
            })
        
        return {
            "inventory": inventory_tree
        }
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}")
        return {"error": str(e)}, 500
