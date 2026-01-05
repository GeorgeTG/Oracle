import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.game_pause import GamePauseEvent


# Example log lines:
# [2025.11.26-20.02.28:877][586]GameLog: Display: [Game] UGameMgr::RemovePausedForUI()
# [2025.11.26-20.02.33:692][200]GameLog: Display: [Game] UGameMgr::AddGamePausedForUI()
GAME_PAUSE_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]"
    r"GameLog: Display: \[Game\] UGameMgr::(AddGamePausedForUI|RemovePausedForUI)\(\)"
)


class GamePauseParser(ParserBase):
    __PARSER__ = {
        "name": "GamePauseParser",
        "version": "0.0.1",
        "description": "Parses game pause/resume events"
    }
    """
    Parser for game pause/unpause events.
    Emits GamePauseEvent when game is paused or unpaused via UI.
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = GAME_PAUSE_RE.search(line)
        if not m:
            return

        ts_str, action = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        # AddGamePausedForUI means game is paused, RemovePausedForUI means unpaused
        is_paused = action == "AddGamePausedForUI"

        event = GamePauseEvent(
            timestamp=timestamp,
            is_paused=is_paused
        )

        await self._emit(event)
