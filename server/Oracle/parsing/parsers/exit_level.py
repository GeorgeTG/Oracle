from __future__ import annotations
import asyncio
import re
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.exit_level import ExitLevelEvent

# Matches: [2025.11.25-22.21.53:442]
TIMESTAMP_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})]"
)

EXIT_RE = re.compile(r"UGameMgr::ExitLevel\(\)")


class ExitLevelParser(ParserBase):
    __PARSER__ = {
        "name": "ExitLevelParser",
        "version": "0.0.1",
        "description": "Parses level/map exit events"
    }

    def __init__(self):
        super().__init__()  # Initialize ParserBase with asyncio.Queue

    async def feed_line(self, line: str):
        if not EXIT_RE.search(line):
            return

        m_ts = TIMESTAMP_RE.search(line)
        if not m_ts:
            return

        date_str, time_str, ms_str = m_ts.groups()
        timestamp = datetime.strptime(
            f"{date_str} {time_str}.{ms_str}",
            "%Y.%m.%d %H.%M.%S.%f"
        )

        event = ExitLevelEvent(timestamp=timestamp)
        await self._emit(event)
