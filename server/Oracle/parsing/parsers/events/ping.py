from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class PingEvent(ParserEvent):
    ping: int
    type: ParserEventType = ParserEventType.PING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "ping": self.ping,
            "type": self.type,
        }

    def __repr__(self) -> str:
        return f"<PingEvent ping={self.ping} @ {self.timestamp.isoformat()}>"
