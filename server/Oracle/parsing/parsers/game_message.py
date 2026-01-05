import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.game_message import GameMessageEvent


# Example log line:
# [2025.11.26-20.14.26:204][192]GameLog: Display: [Game] MsgMgr@:Show MsgValue = Switched to another pact configuration plan (Normal)
GAME_MESSAGE_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]"
    r"GameLog: Display: \[Game\] MsgMgr@:Show MsgValue = (.+)"
)


class GameMessageParser(ParserBase):
    __PARSER__ = {
        "name": "GameMessageParser",
        "version": "0.0.1",
        "description": "Parses in-game messages and notifications"
    }
    """
    Parser for in-game system messages.
    Emits GameMessageEvent when the game displays a message to the player.
    """

    def __init__(self):
        super().__init__()

    async def feed_line(self, line: str):
        m = GAME_MESSAGE_RE.search(line)
        if not m:
            return

        ts_str, message = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = GameMessageEvent(
            timestamp=timestamp,
            message=message.strip()
        )

        await self._emit(event)
