import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.map_loaded import MapLoadedEvent


# Example log line:
# [2025.11.26-20.05.36:998][406]GameLog: Display: [Game] SceneLevelMgr@ OpenMainWorld END! InMainLevelPath = /Game/Art/Maps/01SD/XZ_YuJinZhiXiBiNanSuo200/XZ_YuJinZhiXiBiNanSuo200
MAP_LOADED_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]"
    r"GameLog: Display: \[Game\] SceneLevelMgr@ OpenMainWorld END! InMainLevelPath = (.+)"
)


class MapLoadedParser(ParserBase):
    __PARSER__ = {
        "name": "MapLoadedParser",
        "version": "0.0.1",
        "description": "Parses map loaded and ready events"
    }
    """
    Parser for map loaded events.
    Emits MapLoadedEvent when a main world map is fully loaded.
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = MAP_LOADED_RE.search(line)
        if not m:
            return

        ts_str, map_path = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = MapLoadedEvent(
            timestamp=timestamp,
            map_path=map_path.strip()
        )

        await self._emit(event)
