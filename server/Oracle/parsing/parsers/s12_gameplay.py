import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.s12_gameplay import S12GameplayEvent


# Example log line:
# [2025.11.29-02.06.37:848][ 29]GameLog: Display: [Game] UGamePlayMgr::PlayS12GamePlayBGM layer=1
S12_GAMEPLAY_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\s*\d+\]"
    r"GameLog: Display: \[Game\] UGamePlayMgr::PlayS12GamePlayBGM layer=(\d+)"
)


class S12GameplayParser(ParserBase):
    __PARSER__ = {
        "name": "S12GameplayParser",
        "version": "0.0.1",
        "description": "Parses Season 12 specific gameplay events"
    }
    """
    Parser for S12 gameplay BGM events.
    Emits S12GameplayEvent when BGM layer changes.
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = S12_GAMEPLAY_RE.search(line)
        if not m:
            return

        ts_str, layer_str = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = S12GameplayEvent(
            timestamp=timestamp,
            layer=int(layer_str)
        )

        await self._emit(event)
