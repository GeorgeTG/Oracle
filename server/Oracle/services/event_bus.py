# Oracle/services/event_bus.py
import asyncio
import traceback
from typing import Callable, Awaitable, List, Dict, Union
from collections import defaultdict

from Oracle.tooling.singleton import Singleton
from Oracle.tooling.logger import Logger
from Oracle.services.events.service_event import ServiceEvent, ServiceEventType
from Oracle.parsing.parsers.events import ParserEvent
from Oracle.parsing.parsers.events.parser_event_type import ParserEventType

logger = Logger("EventBus")

# Type alias for any event
Event = Union[ServiceEvent, ParserEvent]
EventType = Union[ServiceEventType, ParserEventType]
Subscriber = Callable[[Event], Awaitable[None]]

@Singleton
class EventBus():
    def __init__(self):
        # Single subscriber dict for both event types
        self._subscribers: Dict[EventType, List[Subscriber]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, callback: Subscriber, event_type: EventType):
        """Subscribe a callback to a specific event type (ServiceEvent or ParserEvent)."""
        async with self._lock:
            self._subscribers[event_type].append(callback)
        # Get class name if it's a bound method
        class_name = callback.__self__.__class__.__name__ if hasattr(callback, '__self__') else ''
        method_name = f"{class_name}.{callback.__name__}" if class_name else callback.__name__
        logger.debug(f"📝 Subscribed {method_name} to {event_type}")

    async def unsubscribe(self, callback: Subscriber, event_type: EventType):
        """Unsubscribe a callback from a specific event type."""
        async with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                # Get class name if it's a bound method
                class_name = callback.__self__.__class__.__name__ if hasattr(callback, '__self__') else ''
                method_name = f"{class_name}.{callback.__name__}" if class_name else callback.__name__
                logger.debug(f"🗑️ Unsubscribed {method_name} from {event_type}")

    async def publish(self, event: Event):
        """Publish an event (ServiceEvent or ParserEvent) to all subscribers of its type in parallel."""
        async with self._lock:
            subscribers = list(self._subscribers.get(event.type, []))
        
        if not subscribers:
            return
        
        logger.debug(f"📨 Publishing {event.type} to {len(subscribers)} subscriber(s)")
        
        # Run all subscribers in parallel
        async def call_subscriber(subscriber):
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
