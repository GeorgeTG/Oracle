"""Base event class for all Oracle events."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TypeVar, Generic


EventTypeT = TypeVar('EventTypeT', bound=Enum)


@dataclass(kw_only=True)
class Event(Generic[EventTypeT]):
    """Base class for all events with generic event type."""
    timestamp: datetime
    type: EventTypeT
    
    def to_dict(self) -> dict:
        """Convert event to dictionary representation."""
        return {
            k: str(v) if isinstance(v, Enum) else v
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def __repr__(self) -> str:
        """String representation of the event."""
        fields = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({fields})"


__all__ = ['Event', 'EventTypeT']
