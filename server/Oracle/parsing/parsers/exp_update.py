import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.exp_update import ExpUpdateEvent


# Example log line:
# [2025.11.26-20.14.26:268][200]GameLog: Display: [Game] ExpMgr@UpdateExp Percent:10272028 97
EXP_UPDATE_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]"
    r"GameLog: Display: \[Game\] ExpMgr@UpdateExp Percent:(\d+) (\d+)"
)


class ExpUpdateParser(ParserBase):
    __PARSER__ = {
        "name": "ExpUpdateParser",
        "version": "0.0.1",
        "description": "Parses experience point updates"
    }
    """
    Parser for experience/level update events.
    Emits ExpUpdateEvent when character exp or level changes.
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = EXP_UPDATE_RE.search(line)
        if not m:
            return

        ts_str, exp_percent_str, level_str = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = ExpUpdateEvent(
            timestamp=timestamp,
            experience=int(exp_percent_str),
            level=int(level_str)
        )

        await self._emit(event)
