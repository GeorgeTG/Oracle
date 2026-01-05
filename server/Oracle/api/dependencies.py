"""FastAPI dependency injection functions."""
from Oracle.parsing.router import Router
from Oracle.services.event_bus import EventBus
from Oracle.services.service_manager import ServiceManager


async def get_event_bus() -> EventBus:
    """Get the EventBus singleton instance."""
    return await EventBus.instance()


async def get_router() -> Router:
    """Get the Router singleton instance."""
    event_bus = await EventBus.instance()
    return await Router.instance(event_bus)


async def get_service_manager() -> ServiceManager:
    """Get the ServiceManager singleton instance."""
    event_bus = await EventBus.instance()
    return await ServiceManager.instance(event_bus)
