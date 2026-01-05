import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.transition_style import TransitionStyleEvent


# Example log line:
# [2025.11.29-02.06.37:287][970]GameLog: Display: [Game] TransitionMgr@ShowTransition TransitionStyle = S12TransitionBlackItem
TRANSITION_STYLE_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\s*\d+\]"
    r"GameLog: Display: \[Game\] TransitionMgr@ShowTransition TransitionStyle = (\S+)"
)


class TransitionStyleParser(ParserBase):
    __PARSER__ = {
        "name": "TransitionStyleParser",
        "version": "0.0.1",
        "description": "Parses screen transition style events"
    }
    """
    Parser for screen transition style events.
    Emits TransitionStyleEvent when a screen transition is shown.
    """

    def __init__(self):
        self._queue: list[TransitionStyleEvent] = []
        self._event = asyncio.Event()

    async def feed_line(self, line: str):
        m = TRANSITION_STYLE_RE.search(line)
        if not m:
            return

        ts_str, transition_style = m.groups()
        timestamp = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")

        event = TransitionStyleEvent(
            timestamp=timestamp,
            transition_style=transition_style.strip()
        )

        self._queue.append(event)
        self._event.set()

    async def results(self) -> AsyncGenerator[TransitionStyleEvent, None]:
        while True:
            await self._event.wait()
            while self._queue:
                yield self._queue.pop(0)
            self._event.clear()
