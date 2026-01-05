from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import AsyncGenerator, Optional

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.game_view import GameViewEvent


# Example logs:
# [..] PageStack@ CurRunView = 3216_SettingCtrl
# [..] PageStack@                  CurRunView == 1321_FightCtrl Calling OnLeaveHide!
GAME_VIEW_RE = re.compile(
    r"CurRunView\s*=?=?\s*(?P<view>\w+)"
)

class GameViewParser(ParserBase):
    __PARSER__ = {
        "name": "GameViewParser",
        "version": "0.0.1",
        "description": "Parses UI view and menu changes"
    }
    """
    Streams game view changes: (e.g. FightCtrl, PCBagCtrl, SettingCtrl)
    Follows same async streaming pattern as ItemChangeParser.
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_view: Optional[str] = None

    async def feed_line(self, line: str) -> None:
        match = GAME_VIEW_RE.search(line)
        if not match:
            return

        view = match.group("view")

        # Ignore duplicates - don't spam
        if view == self._last_view:
            return

        self._last_view = view

        event = GameViewEvent(
            view=view,
            timestamp=datetime.utcnow(),
        )

        await self._emit(event)
