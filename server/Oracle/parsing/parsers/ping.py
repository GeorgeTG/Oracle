import re
from asyncio import Event
from datetime import datetime
from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.ping import PingEvent

PING_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}):\d+\]\[\d+\]GameLog: Display: \[Game\] TCP Ping Result: (\d+)"
)


class PingParser(ParserBase):
    __PARSER__ = {
        "name": "PingParser",
        "version": "0.0.1",
        "description": "Parses network ping events"
    }
    def __init__(self):
        self._items = []
        self._event = Event()

    async def feed_line(self, line: str):
        m = PING_RE.search(line)
        if not m:
            return
        
        ts_str, ping_str = m.groups()
        ts = datetime.strptime(ts_str, "%Y.%m.%d-%H.%M.%S")
        
        ev = PingEvent(timestamp=ts, ping=int(ping_str))
        self._items.append(ev)
        self._event.set()

    async def results(self):
        while True:
            await self._event.wait()
            while self._items:
                yield self._items.pop(0)
            self._event.clear()
