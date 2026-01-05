"""Maps API router - handles map completion endpoints."""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from Oracle.database.models import MapCompletion, MapCompletionItem
from Oracle.tooling.logger import Logger

logger = Logger("MapsRouter")
router = APIRouter(
    prefix="/maps",
    tags=["maps"],
    responses={
        404: {"description": "Map not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "",
    summary="List map completions",
    description="""
    Get a paginated list of map completions with advanced filtering options.
    
    **Filters:**
    - Player name
    - Map name (contains)
    - Difficulty (comma-separated list)
    - Minimum currency/exp/items gained
    
    **Sorting:**
    - Any field with ascending/descending order
    """,
    response_description="Paginated list of map completions"
)
async def get_maps(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    player_name: Optional[str] = Query(None, description="Filter by player name"),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[int] = Query(None, description="Sort order: 1 for asc, -1 for desc"),
    map_name_filter: Optional[str] = Query(None, description="Filter by map name (contains)"),
    difficulty_filter: Optional[str] = Query(None, description="Filter by difficulties (comma-separated)"),
    min_currency: Optional[float] = Query(None, description="Minimum currency gained"),
    min_exp: Optional[float] = Query(None, description="Minimum EXP gained"),
    min_items: Optional[int] = Query(None, description="Minimum items gained"),
    session_id: Optional[int] = Query(None, description="Filter by session ID")
):
    """Get map completions with pagination, sorting, and filtering."""
    try:
        # Build query
        query = MapCompletion.all()
        
        # Apply player filter if provided
        if player_name:
            query = query.filter(player__name=player_name)
        
        # Apply session filter if provided
        if session_id is not None:
            query = query.filter(session_id=session_id)
        
        # Apply map name filter (contains)
        if map_name_filter:
            query = query.filter(map_name__icontains=map_name_filter)
        
        # Apply difficulty filter (multiple values)
        if difficulty_filter:
            difficulties = [d.strip() for d in difficulty_filter.split(",")]
            query = query.filter(map_difficulty__in=difficulties)
        
        # Apply numeric filters
        if min_currency is not None:
            query = query.filter(currency_gained__gte=min_currency)
        
        if min_exp is not None:
            query = query.filter(exp_gained__gte=min_exp)
        
        if min_items is not None:
            query = query.filter(items_gained__gte=min_items)
        
        # Apply sorting
        if sort_field:
            order_prefix = "-" if sort_order == -1 else ""
            query = query.order_by(f"{order_prefix}{sort_field}")
        else:
            # Default sort by completed_at descending
            query = query.order_by("-completed_at")
        
        # Get total count (after filters)
        total = await query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        maps = await query.offset(offset).limit(page_size).prefetch_related("player", "affixes__affix")
        
        # Serialize results
        results = []
        for map_completion in maps:
            # Serialize affixes
            affixes_list = [
                {
                    "affix_id": map_affix.affix.affix_id,
                    "description": map_affix.affix.description
                }
                for map_affix in map_completion.affixes
            ]
            
            results.append({
                "id": map_completion.id,
                "player_name": map_completion.player.name if map_completion.player else None,
                "map_id": map_completion.map_id,
                "map_name": map_completion.map_name,
                "map_difficulty": map_completion.map_difficulty,
                "affixes": affixes_list,
                "started_at": map_completion.started_at.isoformat(),
                "completed_at": map_completion.completed_at.isoformat(),
                "duration": map_completion.duration,
                "currency_gained": map_completion.currency_gained,
                "exp_gained": map_completion.exp_gained,
                "items_gained": map_completion.items_gained,
                "description": map_completion.description
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error fetching maps: {e}")
        return {"error": str(e)}, 500


@router.get(
    "/{map_id}",
    summary="Get map details",
    description="Retrieve detailed information about a specific map completion by ID."
)
async def get_map_detail(map_id: int):
    """Get detailed information about a specific map completion."""
    try:
        map_completion = await MapCompletion.get_or_none(id=map_id).prefetch_related("player", "affixes__affix")
        
        if not map_completion:
            return {"error": "Map not found"}, 404
        
        # Serialize affixes
        affixes_list = [
            {
                "affix_id": map_affix.affix.affix_id,
                "description": map_affix.affix.description
            }
            for map_affix in map_completion.affixes
        ]
        
        return {
            "id": map_completion.id,
            "player_name": map_completion.player.name if map_completion.player else None,
            "map_id": map_completion.map_id,
            "map_name": map_completion.map_name,
            "map_difficulty": map_completion.map_difficulty,
            "affixes": affixes_list,
            "started_at": map_completion.started_at.isoformat(),
            "completed_at": map_completion.completed_at.isoformat(),
            "duration": map_completion.duration,
            "currency_gained": map_completion.currency_gained,
            "exp_gained": map_completion.exp_gained,
            "items_gained": map_completion.items_gained,
            "description": map_completion.description
        }
    except Exception as e:
        logger.error(f"Error fetching map detail: {e}")
        return {"error": str(e)}, 500


class MapUpdateRequest(BaseModel):
    """Request model for updating map completion."""
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Great loot run! High currency drops"
            }
        }


@router.patch(
    "/{map_id}",
    summary="Update map",
    description="Update a map completion's description or notes."
)
async def update_map(map_id: int, update_data: MapUpdateRequest):
    """Update a specific map completion (e.g., description)."""
    try:
        map_completion = await MapCompletion.get_or_none(id=map_id)
        
        if not map_completion:
            return {"error": "Map not found"}, 404
        
        # Update fields if provided
        if update_data.description is not None:
            map_completion.description = update_data.description
        
        await map_completion.save()
        
        return {
            "id": map_completion.id,
            "description": map_completion.description,
            "message": "Map updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating map: {e}")
        return {"error": str(e)}, 500


@router.delete(
    "/{map_id}",
    summary="Delete map",
    description="Delete a specific map completion record.",
    status_code=status.HTTP_200_OK
)
async def delete_map(map_id: int):
    """Delete a specific map completion."""
    from Oracle.database.models import Session
    try:
        map_completion = await MapCompletion.get_or_none(id=map_id)
        
        if not map_completion:
            return {"error": "Map not found"}, 404
        
        # Get the session before deleting the map
        session_id = map_completion.session_id
        
        # Delete the map
        await map_completion.delete()
        
        # Update session stats after deletion
        if session_id:
            session = await Session.get_or_none(id=session_id)
            if session:
                # Recalculate session stats from remaining maps
                remaining_maps = await MapCompletion.filter(session_id=session_id).all()
                
                total_maps = len(remaining_maps)
                total_currency = sum(m.currency_gained or 0 for m in remaining_maps)
                total_exp = sum(m.exp_gained or 0 for m in remaining_maps)
                
                # Calculate duration and rates
                if total_maps > 0:
                    total_duration_seconds = sum(m.duration or 0 for m in remaining_maps)
                    total_hours = total_duration_seconds / 3600 if total_duration_seconds > 0 else 0
                    
                    session.total_maps = total_maps
                    session.total_currency_delta = total_currency
                    session.total_exp_delta = total_exp
                    session.currency_per_hour = total_currency / total_hours if total_hours > 0 else 0
                    session.currency_per_map = total_currency / total_maps
                else:
                    # No maps left in session
                    session.total_maps = 0
                    session.total_currency_delta = 0
                    session.total_exp_delta = 0
                    session.currency_per_hour = 0
                    session.currency_per_map = 0
                
                await session.save()
        
        return {"message": f"Map {map_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting map: {e}")
        return {"error": str(e)}, 500


@router.get(
    "/{map_id}/items",
    summary="Get map items",
    description="Retrieve all item changes in a specific map completion. Use consumed=true for entry items."
)
async def get_map_items(map_id: int, consumed: bool = False):
    """Get all item changes in a specific map completion."""
    try:
        # Check if map exists
        map_completion = await MapCompletion.get_or_none(id=map_id)
        if not map_completion:
            return {"error": "Map not found"}, 404
        
        # Get items based on consumed flag
        items = await MapCompletionItem.filter(map_completion_id=map_id, consumed=consumed).prefetch_related("item")
        
        results = []
        for map_item in items:
            if consumed:
                # For consumed items, return positive quantity
                results.append({
                    "id": map_item.item.item_id,
                    "name": map_item.item.name,
                    "category": map_item.item.category,
                    "quantity": abs(map_item.delta),
                    "total_price": abs(map_item.total_price)
                })
            else:
                # For regular items, return delta
                results.append({
                    "id": map_item.item.item_id,
                    "name": map_item.item.name,
                    "category": map_item.item.category,
                    "delta": map_item.delta,
                    "total_price": map_item.total_price
                })
        
        return results
    except Exception as e:
        logger.error(f"Error fetching map items: {e}")
        return {"error": str(e)}, 500
