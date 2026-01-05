from dataclasses import dataclass
from datetime import datetime
from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass(kw_only=True)
class LoadingProgressEvent(ParserEvent):
    primary: int
    secondary_type: str
    secondary_progress: int
    type: ParserEventType = ParserEventType.LOADING_PROGRESS
