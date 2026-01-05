import asyncio
from typing import AsyncGenerator, Optional


from Oracle.parsing.parsers.events import ParserEvent


class ParserBase:
    """
    Base class for all parsers.
    """
    def __init__(self) -> None:
        self._queue: asyncio.Queue[ParserEvent] = asyncio.Queue()
        self._running: bool = True

    def stop(self) -> None:
        """Tell the parser no more data will come"""
        self._running = False

    async def feed_line(self, line: str) -> None:
        """
        Should be implemented by subclasses.
        Called for every new log line to parse.
        """
        raise NotImplementedError

    async def _emit(self, obj: ParserEvent) -> None:
        """Push parsed model to the async queue"""
        await self._queue.put(obj)

    async def results(self) -> AsyncGenerator[ParserEvent, None]:
        """
        Async generator that yields parsed objects as they become available.
        Blocks waiting when none exist, until parser is stopped.
        """
        while self._running or not self._queue.empty():
            item: Optional[ParserEvent] = await self._queue.get()
            yield item
            self._queue.task_done()
