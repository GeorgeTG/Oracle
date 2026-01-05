from __future__ import annotations
from dataclasses import dataclass

from Oracle.parsing.parsers.events.parser_event_type import ParserEventType
from Oracle.events.base_event import Event


@dataclass(kw_only=True)
class ParserEvent(Event[ParserEventType]):
    """Base class for all parser events."""
    pass
