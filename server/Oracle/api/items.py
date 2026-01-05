"""Items API router - handles item CRUD operations."""
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from Oracle.database.models import Item
from Oracle.services.event_bus import EventBus
from Oracle.services.events import ItemDataChangedEvent
from Oracle.tooling.logger import Logger

logger = Logger("ItemsRouter")
router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={
        404: {"description": "Item not found"},
        500: {"description": "Internal server error"}
    }
)


class ItemCreate(BaseModel):
    """Schema for creating a new item."""
    item_id: int
    name: Optional[str] = None
    category: Optional[str] = None
    rarity: Optional[str] = None
    price: float = 0.0


class ItemUpdate(BaseModel):
    """Schema for updating an item (all fields optional)."""
    name: Optional[str] = None
    category: Optional[str] = None
    rarity: Optional[str] = None
    price: Optional[float] = None


class ItemResponse(BaseModel):
    """Schema for item response."""
    id: int
    item_id: int
    name: Optional[str]
    category: Optional[str]
    rarity: Optional[str]
    price: float

    class Config:
        from_attributes = True


@router.get(
    "",
    summary="List all items",
    description="Get a list of all items with optional filtering.",
    response_model=List[ItemResponse]
)
async def get_items(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum items to return")
):
    """Get all items with optional filters."""
    try:
        query = Item.all()
        
        # Apply filters
        if category:
            query = query.filter(category=category)
        if min_price is not None:
            query = query.filter(price__gte=min_price)
        if max_price is not None:
            query = query.filter(price__lte=max_price)
        
        items = await query.limit(limit)
        
        return [ItemResponse.model_validate(item) for item in items]
    
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch items: {str(e)}"
        )


@router.get(
    "/export",
    summary="Export all items as JSON",
    description="Export all items in price_table.json format (without 'from' field)."
)
async def export_items(
    pretty: bool = Query(True, description="Format JSON with indentation for readability")
):
    """Export all items in price_table format."""
    try:
        items = await Item.all()
        
        # Build export dictionary
        export_data: Dict[str, Dict[str, Any]] = {}
        
        for item in items:
            item_data = {
                "name": item.name or "",
                "type": item.category or "",
                "price": float(item.price) if item.price else 0.0
            }
            
            # Add updated_at if available
            if hasattr(item, 'updated_at') and item.updated_at:
                item_data["updated_at"] = int(item.updated_at.timestamp())
            
            export_data[str(item.item_id)] = item_data
        
        # Format JSON based on pretty parameter
        if pretty:
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(export_data, ensure_ascii=False)
        
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=items_export.json"}
        )
    
    except Exception as e:
        logger.error(f"Failed to export items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export items: {str(e)}"
        )


@router.get(
    "/{item_id}",
    summary="Get item by ID",
    description="Get a specific item by its database ID or game item ID.",
    response_model=ItemResponse
)
async def get_item(
    item_id: int,
    byItemId: bool = Query(False, description="If true, treat item_id as game item_id instead of database id")
):
    """Get a specific item by database ID or game item ID."""
    try:
        if byItemId:
            # Search by game item_id
            item = await Item.get_or_none(item_id=item_id)
        else:
            # Search by database id
            item = await Item.get_or_none(id=item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with {'item_id' if byItemId else 'id'} {item_id} not found"
            )
        
        return ItemResponse.model_validate(item)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch item: {str(e)}"
        )


@router.get(
    "/by-game-id/{game_item_id}",
    summary="Get item by game item ID",
    description="Get a specific item by its game's internal item ID.",
    response_model=ItemResponse
)
async def get_item_by_game_id(game_item_id: int):
    """Get a specific item by game item ID."""
    try:
        item = await Item.get_or_none(item_id=game_item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with game_item_id {game_item_id} not found"
            )
        
        return ItemResponse.model_validate(item)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch item {game_item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch item: {str(e)}"
        )


@router.post(
    "",
    summary="Create new item",
    description="Create a new item in the database.",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_item(item_data: ItemCreate):
    """Create a new item."""
    try:
        # Check if item with same item_id already exists
        existing = await Item.get_or_none(item_id=item_data.item_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item with item_id {item_data.item_id} already exists"
            )
        
        # Create new item
        item = await Item.create(
            item_id=item_data.item_id,
            name=item_data.name,
            category=item_data.category,
            rarity=item_data.rarity,
            price=item_data.price
        )
        
        logger.info(f"Created item: {item.item_id} - {item.name}")
        return ItemResponse.model_validate(item)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}"
        )


@router.patch(
    "/{item_id}",
    summary="Update item",
    description="Update an existing item. Only provided fields will be updated.",
    response_model=ItemResponse
)
async def update_item(item_id: int, item_data: ItemUpdate):
    """Update an existing item."""
    try:
        item = await Item.get_or_none(id=item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        # Update only provided fields
        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        await item.save()
        
        logger.info(f"Updated item: {item.item_id} - {item.name}")
        
        # Publish event to update PriceDB cache
        event_bus = await EventBus.instance()
        await event_bus.publish(ItemDataChangedEvent(
            item_id=item.item_id,
            name=item.name,
            category=item.category,
            price=item.price
        ))
        
        return ItemResponse.model_validate(item)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item: {str(e)}"
        )


@router.delete(
    "/{item_id}",
    summary="Delete item",
    description="Delete an item from the database.",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_item(item_id: int):
    """Delete an item."""
    try:
        item = await Item.get_or_none(id=item_id)
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id {item_id} not found"
            )
        
        await item.delete()
        
        logger.info(f"Deleted item: {item.item_id} - {item.name}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}"
        )
