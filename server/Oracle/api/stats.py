"""Stats API router - handles statistics control endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, status

from Oracle.services.event_bus import EventBus
from Oracle.services.events.stats_events import StatsControlEvent, StatsControlAction
from Oracle.api.dependencies import get_event_bus
from Oracle.tooling.logger import Logger

logger = Logger("StatsRouter")
router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)


@router.post(
    "/reset",
    summary="Reset statistics",
    description="Reset all statistics tracking by publishing a restart event to the stats service.",
    status_code=status.HTTP_200_OK
)
async def reset_stats(event_bus: EventBus = Depends(get_event_bus)):
    """Reset stats tracking by publishing a RESTART control event."""
    await event_bus.publish(StatsControlEvent(
        timestamp=datetime.now(),
        action=StatsControlAction.RESTART
    ))
    logger.info("📊 Stats reset requested via API")
    return {"status": "OK", "message": "Stats reset command sent"}
