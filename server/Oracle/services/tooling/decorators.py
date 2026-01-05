# Oracle/services/tooling/decorators.py

from functools import wraps
from typing import Union

from Oracle.parsing.parsers.events.parser_event_type import ParserEventType
from Oracle.services.events.service_event import ServiceEventType


def event_handler(*event_types: Union[ServiceEventType, ParserEventType]):
    """
    Unified decorator that marks a method as an event handler.
    The handler will auto-subscribe to the specified event types.
    Works for both ServiceEvents and ParserEvents.
    
    Usage:
        @event_handler(ServiceEventType.REQUEST_INVENTORY)
        async def on_request_inventory(self, event):
            ...
            
        @event_handler(ParserEventType.BAG_MODIFY, ParserEventType.ITEM_CHANGE)
        async def on_inventory_change(self, event):
            ...
    """
    def decorator(func):
        func._event_types = event_types
        
        @wraps(func)
        async def wrapper(self, event):
            if event_types and event.type not in event_types:
                return
            return await func(self, event)
        return wrapper
    return decorator



