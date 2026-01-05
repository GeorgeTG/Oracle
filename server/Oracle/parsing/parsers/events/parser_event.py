from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from Oracle.parsing.parsers.events.parser_event_type import ParserEventType


@dataclass
class ParserEvent:
    """Base class for all parser events."""
    timestamp: datetime
    type: ParserEventType
    
    def to_dict(self) -> dict:
        return {
            k: str(v) if isinstance(v, ParserEventType) else v
            for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{k}={repr(v)}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({fields})"
