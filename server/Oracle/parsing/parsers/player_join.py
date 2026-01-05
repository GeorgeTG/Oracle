import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.player_join import PlayerJoinEvent
from Oracle.tooling.logger import Logger

logger = Logger("PlayerJoinParser")


# Example log line:
# [2025.12.10-15.30.45:123][456]GameLog: Display: [Game] SwitchBattleAreaUtil:_JoinFight Eryndor#7291:1100
# Note: There might be a space after the bracket: [ 23]GameLog or [944]GameLog
PLAYER_JOIN_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\s*\d+\]\s*"
    r"GameLog: Display: \[Game\]\s+SwitchBattleAreaUtil:_JoinFight\s+([^:]+):(\d+)"
)


class PlayerJoinParser(ParserBase):
    __PARSER__ = {
        "name": "PlayerJoinParser",
        "version": "0.0.1",
        "description": "Parses player join and session start events"
    }
    """
    Parses player join events.
    Example: [Game] SwitchBattleAreaUtil:_JoinFight Eryndor#7291:1100
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str) -> None:
        match = PLAYER_JOIN_RE.search(line)
        if not match:
            return

        ts_str, player_name, mode_str = match.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = PlayerJoinEvent(
            timestamp=timestamp,
            player_name=player_name,
            mode=int(mode_str)
        )
        
        await self._emit(event)
