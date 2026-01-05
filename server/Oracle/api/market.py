"""Market API router - handles market transaction endpoints."""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from Oracle.database.models import MarketTransaction
from Oracle.tooling.logger import Logger

logger = Logger("MarketRouter")
router = APIRouter(
    prefix="/market",
    tags=["market"],
    responses={
        404: {"description": "Transaction not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "",
    summary="List market transactions",
    description="""
    Get a paginated list of market transactions with advanced filtering options.
    
    **Filters:**
    - Player name
    - Action (bought/sold/obtained)
    - Item name (contains)
    - Minimum quantity
    
    **Sorting:**
    - Any field with ascending/descending order
    """,
    response_description="Paginated list of market transactions"
)
async def get_market_transactions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    player_name: Optional[str] = Query(None, description="Filter by player name"),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[int] = Query(None, description="Sort order: 1 for asc, -1 for desc"),
    action_filter: Optional[str] = Query(None, description="Filter by action (bought/sold/obtained)"),
    item_name_filter: Optional[str] = Query(None, description="Filter by item name (contains)"),
    min_quantity: Optional[int] = Query(None, description="Minimum quantity"),
    session_id: Optional[int] = Query(None, description="Filter by session ID")
):
    """Get market transactions with pagination, sorting, and filtering."""
    try:
        # Build query
        query = MarketTransaction.all()
        
        # Apply player filter if provided
        if player_name:
            query = query.filter(player__name=player_name)
        
        # Apply session filter if provided
        if session_id is not None:
            query = query.filter(session_id=session_id)
        
        # Apply action filter
        if action_filter:
            query = query.filter(action=action_filter)
        
        # Apply item name filter (contains)
        if item_name_filter:
            query = query.filter(item__name__icontains=item_name_filter)
        
        # Apply numeric filters
        if min_quantity is not None:
            query = query.filter(quantity__gte=min_quantity)
        
        # Apply sorting
        if sort_field:
            order_prefix = "-" if sort_order == -1 else ""
            query = query.order_by(f"{order_prefix}{sort_field}")
        else:
            # Default sort by timestamp descending
            query = query.order_by("-timestamp")
        
        # Get total count (after filters)
        total = await query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        transactions = await query.offset(offset).limit(page_size).prefetch_related("player", "item", "session")
        
        # Serialize results
        results = []
        for transaction in transactions:
            results.append({
                "id": transaction.id,
                "player_name": transaction.player.name if transaction.player else None,
                "timestamp": transaction.timestamp.isoformat(),
                "item_id": transaction.item.id if transaction.item else None,
                "item_name": transaction.item.name if transaction.item else None,
                "quantity": transaction.quantity,
                "action": transaction.action,
                "session_id": transaction.session.id if transaction.session else None,
                "session_title": transaction.session.title if transaction.session and transaction.session.title else None
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error retrieving market transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve market transactions: {str(e)}"
        )


@router.get(
    "/{transaction_id}",
    summary="Get market transaction details",
    description="Get detailed information about a specific market transaction.",
    response_description="Market transaction details"
)
async def get_transaction_detail(transaction_id: int):
    """Get detailed info about a specific transaction."""
    try:
        transaction = await MarketTransaction.get_or_none(id=transaction_id).prefetch_related("player", "item", "session")
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        return {
            "id": transaction.id,
            "player_name": transaction.player.name if transaction.player else None,
            "timestamp": transaction.timestamp.isoformat(),
            "item_id": transaction.item.id if transaction.item else None,
            "item_name": transaction.item.name if transaction.item else None,
            "item_category": transaction.item.category if transaction.item else None,
            "item_rarity": transaction.item.rarity if transaction.item else None,
            "quantity": transaction.quantity,
            "action": transaction.action,
            "session_id": transaction.session.id if transaction.session else None,
            "session_title": transaction.session.title if transaction.session and transaction.session.title else None,
            "session_started": transaction.session.started_at.isoformat() if transaction.session else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transaction: {str(e)}"
        )
