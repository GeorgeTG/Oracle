from dataclasses import dataclass
from datetime import datetime
from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class ExitLevelEvent(ParserEvent):
    type: ParserEventType = ParserEventType.EXIT_LEVEL

    def __repr__(self):
        ts = self.timestamp.isoformat()
        return f"<ExitLevelEvent @ {ts}>"
