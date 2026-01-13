"""Sessions API router - handles farming session endpoints."""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, Field

from Oracle.services.events.session_events import SessionControlEvent, SessionControlAction
from Oracle.events import EventBus

from Oracle.database.models import Session, MapCompletion, MarketTransaction, MapCompletionItem

from Oracle.tooling.logger import Logger

logger = Logger("SessionsRouter")
router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"}
    }
)


async def calculate_session_currency(session: Session) -> dict:
    """Calculate session currency including market transactions."""
    # Get all market transactions for this session
    transactions = await MarketTransaction.filter(session_id=session.id).prefetch_related("item")
    
    # Get PriceDB instance
    from Oracle.market import PriceDB
    price_db = await PriceDB.instance()
    
    # Calculate total market currency (items sold/gained)
    market_currency = 0.0
    for tx in transactions:
        price = price_db.get_price(tx.item.item_id) if tx.item else 0.0
        
        if tx.action == "gained":
            market_currency += price * tx.quantity
        elif tx.action == "lost":
            market_currency -= price * tx.quantity
    
    # Total currency is maps + market
    total_currency = session.total_currency_delta + market_currency
    
    # Calculate currency per hour
    duration_hours = 0.0
    if session.ended_at:
        duration = (session.ended_at - session.started_at).total_seconds() / 3600.0
        duration_hours = duration
    elif session.is_active:
        # Use timezone-aware datetime for comparison
        now = datetime.now(timezone.utc) if session.started_at.tzinfo else datetime.now()
        duration = (now - session.started_at).total_seconds() / 3600.0
        duration_hours = duration
    
    currency_per_hour = total_currency / duration_hours if duration_hours > 0 else 0.0
    
    return {
        "total_currency": total_currency,
        "currency_per_hour": currency_per_hour,
        "market_currency": market_currency,
        "maps_currency": session.total_currency_delta
    }


class SessionUpdateRequest(BaseModel):
    """Request to update session title and/or description."""
    title: Optional[str] = Field(None, description="New title for the session")
    description: Optional[str] = Field(None, description="New description for the session")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Morning Farming Session",
                "description": "Morning farming session - focused on red maps"
            }
        }


@router.post(
    "",
    summary="Create new session",
    description="Create a new farming session by sending a SESSION_CONTROL event with NEXT action.",
    status_code=status.HTTP_202_ACCEPTED
)
async def create_session(request: Request):
    """Create a new farming session via event bus."""
    try:
        # Get EventBus singleton instance
        event_bus = await EventBus.instance()
        
        # Create and publish SessionControlEvent with NEXT action
        # This will atomically close current session and start new one
        event = SessionControlEvent(
            timestamp=datetime.now(),
            action=SessionControlAction.NEXT,
            player_name=None  # Service will use cached player name
        )
        
        logger.info(f"Publishing SessionControlEvent: {event}")
        await event_bus.publish(event)
        
        return {
            "status": "accepted",
            "message": "Session control event published"
        }
    except Exception as e:
        logger.error(f"Error publishing session control event: {e}")
        return {"error": str(e)}, 500


@router.get(
    "/active",
    summary="Get active session",
    description="Retrieve the currently active farming session with the last 10 completed maps."
)
async def get_active_session():
    """Get the currently active session with recent maps."""
    try:
        # Get the most recent active session (in case there are multiple)
        session = await Session.filter(is_active=True).order_by("-started_at").first()
        
        if not session:
            logger.debug("No active session found")
            return {"session": None}
        
        logger.debug(f"Found active session: {session.id} for player {session.player_name}")
        
        # Get recent maps for this session (last 10)
        maps = await MapCompletion.filter(session_id=session.id).order_by("-completed_at").limit(10)
        
        logger.debug(f"Found {len(maps)} maps for session {session.id}")
        
        # Calculate currency with market transactions
        currency_calc = await calculate_session_currency(session)
        
        maps_data = []
        for map_completion in maps:
            maps_data.append({
                "id": map_completion.id,
                "map_name": map_completion.map_name,
                "map_difficulty": map_completion.map_difficulty,
                "completed_at": map_completion.completed_at.isoformat(),
                "duration": map_completion.duration,
                "currency_gained": map_completion.currency_gained,
                "exp_gained": map_completion.exp_gained,
                "description": map_completion.description
            })
        
        return {
            "session": {
                "id": session.id,
                "player_name": session.player_name,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "total_maps": session.total_maps,
                "total_currency_delta": currency_calc["total_currency"],
                "currency_per_hour": currency_calc["currency_per_hour"],
                "currency_per_map": session.currency_per_map,
                "title": session.title or f"Session #{session.id}",
                "description": session.description,
                "is_active": session.is_active,
                "duration_seconds": (session.ended_at - session.started_at).total_seconds() if session.ended_at else (datetime.now(timezone.utc) if session.started_at.tzinfo else datetime.now() - session.started_at).total_seconds(),
                "maps_currency": currency_calc["maps_currency"],
                "market_currency": currency_calc["market_currency"],
                "maps": maps_data
            }
        }
    except Exception as e:
        logger.error(f"Error fetching active session: {e}")
        return {"error": str(e)}, 500


@router.get(
    "",
    summary="List sessions",
    description="Get a paginated list of farming sessions with optional player filtering."
)
async def get_sessions(
    player_name: Optional[str] = Query(None, description="Filter by player name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get farming sessions with optional player filter."""
    try:
        # Build query
        query = Session.all()
        
        # Apply player filter if provided
        if player_name:
            query = query.filter(player_name=player_name)
        
        # Order by started_at descending (most recent first)
        query = query.order_by("-started_at")
        
        # Get total count
        total = await query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        sessions = await query.offset(offset).limit(page_size)
        
        # Serialize results
        results = []
        for session in sessions:
            results.append({
                "id": session.id,
                "player_name": session.player_name,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "total_maps": session.total_maps,
                "total_currency_delta": session.total_currency_delta,
                "currency_per_hour": session.currency_per_hour,
                "currency_per_map": session.currency_per_map,
                "title": session.title or f"Session #{session.id}",
                "description": session.description,
                "is_active": session.ended_at is None
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return {"error": str(e)}, 500


@router.patch(
    "/{session_id}",
    summary="Update session",
    description="Update a farming session's title and/or description."
)
async def update_session(session_id: int, update_data: SessionUpdateRequest):
    """Update a session's title and/or description."""
    try:
        session = await Session.get_or_none(id=session_id)
        
        if not session:
            return {"error": "Session not found"}, 404
        
        # Update title if provided
        if update_data.title is not None:
            session.title = update_data.title if update_data.title else None
        
        # Update description if provided
        if update_data.description is not None:
            session.description = update_data.description if update_data.description else None
        
        await session.save()
        
        return {
            "id": session.id,
            "player_name": session.player_name,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "total_maps": session.total_maps,
            "total_currency_delta": session.total_currency_delta,
            "currency_per_hour": session.currency_per_hour,
            "currency_per_map": session.currency_per_map,
            "title": session.title,
            "description": session.description
        }
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return {"error": str(e)}, 500


@router.get(
    "/{session_id}",
    summary="Get session details",
    description="Get detailed information about a specific session including maps, market transactions, and items."
)
async def get_session_details(session_id: int):
    """Get detailed session information with all related data."""
    try:
        session = await Session.get_or_none(id=session_id)
        
        if not session:
            return {"error": "Session not found"}, 404
        
        # Calculate currency with market transactions
        currency_calc = await calculate_session_currency(session)
        
        # Get all maps for this session
        maps = await MapCompletion.filter(session_id=session.id).order_by("-completed_at")
        
        maps_data = []
        for map_completion in maps:
            # Get items for this map
            map_items = await MapCompletionItem.filter(
                map_completion_id=map_completion.id
            ).prefetch_related("item")
            
            items_data = []
            for map_item in map_items:
                if map_item.item:
                    items_data.append({
                        "item_id": map_item.item.item_id,
                        "name": map_item.item.name,
                        "delta": map_item.delta,
                        "total_price": map_item.total_price
                    })
            
            maps_data.append({
                "id": map_completion.id,
                "map_name": map_completion.map_name,
                "map_difficulty": map_completion.map_difficulty,
                "started_at": map_completion.started_at.isoformat(),
                "completed_at": map_completion.completed_at.isoformat(),
                "duration": map_completion.duration,
                "currency_gained": map_completion.currency_gained,
                "exp_gained": map_completion.exp_gained,
                "items_gained": map_completion.items_gained,
                "description": map_completion.description,
                "items": items_data
            })
        
        # Get all market transactions for this session
        transactions = await MarketTransaction.filter(
            session_id=session.id
        ).prefetch_related("item").order_by("-timestamp")
        
        # Get PriceDB instance
        from Oracle.market import PriceDB
        price_db = await PriceDB.instance()
        
        market_data = []
        for tx in transactions:
            if tx.item:
                price = price_db.get_price(tx.item.item_id)
                total_value = price * tx.quantity
                
                market_data.append({
                    "id": tx.id,
                    "timestamp": tx.timestamp.isoformat(),
                    "item_id": tx.item.item_id,
                    "item_name": tx.item.name,
                    "quantity": tx.quantity,
                    "action": tx.action,
                    "unit_price": price,
                    "total_value": total_value
                })
        
        # Calculate duration
        duration_seconds = 0
        if session.ended_at:
            duration_seconds = (session.ended_at - session.started_at).total_seconds()
        elif session.is_active:
            now = datetime.now(timezone.utc) if session.started_at.tzinfo else datetime.now()
            duration_seconds = (now - session.started_at).total_seconds()
        
        return {
            "id": session.id,
            "player_name": session.player_name,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": duration_seconds,
            "is_active": session.is_active,
            "title": session.title or f"Session #{session.id}",
            "description": session.description,
            "total_maps": session.total_maps,
            "total_currency": currency_calc["total_currency"],
            "maps_currency": currency_calc["maps_currency"],
            "market_currency": currency_calc["market_currency"],
            "currency_per_hour": currency_calc["currency_per_hour"],
            "currency_per_map": session.currency_per_map,
            "maps": maps_data,
            "market_transactions": market_data
        }
    except Exception as e:
        logger.error(f"Error fetching session details: {e}")
        return {"error": str(e)}, 500

