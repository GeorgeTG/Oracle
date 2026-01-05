# Oracle/events/event_bus.py
import asyncio
from typing import Callable, Awaitable, List, Dict, TypeAlias, Any, TypeVar
from collections import defaultdict
from enum import Enum

from Oracle.tooling.singleton import SingletonMixin
from Oracle.tooling.logger import Logger
from Oracle.events.base_event import Event

logger = Logger("EventBus")

EventT = TypeVar('EventT', bound=Event[Any])

Subscriber: TypeAlias = Callable[[Event[Any]], Awaitable[None]]

class EventBus(SingletonMixin):
    def __init__(self):
        # Single subscriber dict for both event types
        self._subscribers: Dict[Enum, List[Subscriber]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Async initialization if needed."""
        logger.info("🚏 EventBus initialized")

    async def subscribe(
        self, 
        callback: Callable[[EventT], Awaitable[None]], 
        event_type: Enum
    ) -> None:
        """Subscribe a callback to a specific event type."""
        async with self._lock:
            self._subscribers[event_type].append(callback)  # type: ignore
        # Get class name if it's a bound method
        class_name = callback.__self__.__class__.__name__ if hasattr(callback, '__self__') else ''
        method_name = f"{class_name}.{callback.__name__}" if class_name else callback.__name__
        logger.debug(f"📝 Subscribed {method_name} to {event_type}")

    async def unsubscribe(
        self, 
        callback: Callable[[EventT], Awaitable[None]], 
        event_type: Enum
    ) -> None:
        """Unsubscribe a callback from a specific event type."""
        async with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback) # type: ignore
                # Get class name if it's a bound method
                class_name = callback.__self__.__class__.__name__ if hasattr(callback, '__self__') else ''
                method_name = f"{class_name}.{callback.__name__}" if class_name else callback.__name__
                logger.debug(f"🗑️ Unsubscribed {method_name} from {event_type}")

    async def publish(self, event: Event[Any]):
        """Publish an event to all subscribers of its type in parallel."""
        async with self._lock:
            subscribers = list(self._subscribers.get(event.type, []))
        
        if not subscribers:
            return
        
        logger.debug(f"📨 Publishing {event.type} to {len(subscribers)} subscriber(s)")
        
        # Run all subscribers in parallel
        async def call_subscriber(subscriber: Subscriber):
            try:
                await subscriber(event)
            except Exception as e:
                # Get class name if it's a bound method
                class_name = subscriber.__self__.__class__.__name__ if hasattr(subscriber, '__self__') else ''
                method_name = f"{class_name}.{subscriber.__name__}" if class_name else subscriber.__name__
                logger.error(f"Error in subscriber {method_name}: {e}")
                logger.trace(e)
        
        await asyncio.gather(*[call_subscriber(sub) for sub in subscribers], return_exceptions=True)

    async def shutdown(self):
        """Clear all subscribers during shutdown."""
        logger.info("🔌 Clearing all event subscribers")
        self._subscribers.clear()
