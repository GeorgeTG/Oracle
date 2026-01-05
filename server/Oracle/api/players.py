"""Players API router - handles player-related endpoints."""
from typing import List
from fastapi import APIRouter

from Oracle.database.models import Session
from Oracle.tooling.logger import Logger

logger = Logger("PlayersRouter")
router = APIRouter(
    prefix="/players",
    tags=["players"],
    responses={
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "",
    summary="Get all players",
    description="Get a list of all unique player names from sessions."
)
async def get_players():
    """Get all unique player names from sessions."""
    try:
        # Get all unique player names from sessions
        sessions = await Session.all().distinct().values_list("player_name", flat=True)
        
        # Filter out None/empty values and sort
        players = sorted([name for name in sessions if name])
        
        logger.debug(f"Found {len(players)} unique players")
        
        return {
            "players": players,
            "total": len(players)
        }
    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        return {"error": str(e)}, 500
