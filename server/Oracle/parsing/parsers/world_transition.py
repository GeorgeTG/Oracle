import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.world_transition import WorldTransitionEvent


# Example log lines:
# [2025.11.26-20.04.52:426][228]GameLog: Display: [Game] PageApplyBase@ BackFlow4 IsSwitchingSubWorldToMainWorld = false
# [2025.11.26-20.04.57:010][746]GameLog: Display: [Game] PageApplyBase@ BackFlow0 IsSwitchingSubWorldToMainWorld = true
WORLD_TRANSITION_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]"
    r"GameLog: Display: \[Game\] PageApplyBase@ BackFlow(\d+) IsSwitchingSubWorldToMainWorld = (true|false)"
)


class WorldTransitionParser(ParserBase):
    __PARSER__ = {
        "name": "WorldTransitionParser",
        "version": "0.0.1",
        "description": "Parses world/zone transition events"
    }
    """
    Parser for world transition events (BackFlow).
    Emits WorldTransitionEvent when switching between SubWorld and MainWorld.
    """

    def __init__(self):
        self._queue: list[WorldTransitionEvent] = []
        self._event = asyncio.Event()

    async def feed_line(self, line: str):
        m = WORLD_TRANSITION_RE.search(line)
        if not m:
            return

        ts_str, back_flow_step_str, is_switching_str = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = WorldTransitionEvent(
            timestamp=timestamp,
            back_flow_step=int(back_flow_step_str),
            is_switching_to_main_world=is_switching_str == "true"
        )

        self._queue.append(event)
        self._event.set()

    async def results(self) -> AsyncGenerator[WorldTransitionEvent, None]:
        while True:
            await self._event.wait()
            while self._queue:
                yield self._queue.pop(0)
            self._event.clear()
