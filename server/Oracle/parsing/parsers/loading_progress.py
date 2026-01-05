from __future__ import annotations
import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.loading_progress import LoadingProgressEvent


TIMESTAMP_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})]"
)

LOADING_RE = re.compile(
    r"Loading@\s+P=(\d+),S=([A-Za-z]+)\s+(\d+)%"
)


class LoadingProgressParser(ParserBase):
    __PARSER__ = {
        "name": "LoadingProgressParser",
        "version": "0.0.1",
        "description": "Parses loading screen progress events"
    }

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str) -> None:
        m_ts = TIMESTAMP_RE.search(line)
        m = LOADING_RE.search(line)
        if not m or not m_ts:
            return

        date_str, time_str, ms_str = m_ts.groups()
        timestamp = datetime.strptime(
            f"{date_str} {time_str}.{ms_str}",
            "%Y.%m.%d %H.%M.%S.%f"
        )

        primary_str, secondary_type, secondary_str = m.groups()

        model = LoadingProgressEvent(
            timestamp=timestamp,
            primary=int(primary_str),
            secondary_type=secondary_type,
            secondary_progress=int(secondary_str),
        )

        await self._emit(model)
