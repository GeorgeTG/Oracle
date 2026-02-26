from collections import deque
from datetime import datetime, timedelta

from Oracle.services.service_base import ServiceBase
from Oracle.services.tooling.decorators import event_handler
from Oracle.services.events.service_event import ServiceEventType
from Oracle.services.events.item_events import ItemObtainedEvent
from Oracle.services.events.overlay_events import OverlayInfoTextEvent
from Oracle.tooling.logger import Logger

logger = Logger("AchievementService")

# Ordered lowest to highest so we can fire progressively
THRESHOLDS = [
    (100,  "\U0001f5a8\ufe0f Printing", "info"),
    (200,  "\U0001f5a8\ufe0f Big Print", "warn"),
    (350,  "\U0001f5a8\ufe0f\U0001f5a8\ufe0f Mega Print", "warn"),
    (500,  "\U0001f525\U0001f5a8\ufe0f Huge Print", "warn"),
    (1000, "\U0001f525\U0001f5a8\ufe0f\U0001f525 GIGA PRINT", "danger"),
]

WINDOW_SECONDS = 5
DISPLAY_DURATION_MS = 5000


class AchievementService(ServiceBase):
    __SERVICE__ = {
        "name": "AchievementService",
        "version": "0.0.1",
        "description": "Detects loot explosions and sends celebratory overlay messages",
        "requires": {}
    }

    def __init__(self, event_bus):
        super().__init__(event_bus)
        self._recent_values: deque = deque()
        self._highest_fired: int = 0  # highest threshold value fired in current burst

    @event_handler(ServiceEventType.ITEM_OBTAINED)
    async def on_item_obtained(self, event: ItemObtainedEvent):
        if event.total_value <= 0:
            return

        now = datetime.now()

        # Prune old entries BEFORE adding new one
        cutoff = now - timedelta(seconds=WINDOW_SECONDS)
        while self._recent_values and self._recent_values[0][0] < cutoff:
            self._recent_values.popleft()

        # If window was empty before this item, reset the burst tracker
        if not self._recent_values:
            self._highest_fired = 0

        self._recent_values.append((now, event.total_value))

        # Sum window and check thresholds (lowest first, fire each new tier)
        window_total = sum(v for _, v in self._recent_values)
        for threshold, message, severity in THRESHOLDS:
            if window_total >= threshold and threshold > self._highest_fired:
                await self.publish(OverlayInfoTextEvent(
                    timestamp=now,
                    text=message,
                    severity=severity,
                    duration=DISPLAY_DURATION_MS,
                ))
                self._highest_fired = threshold
                logger.info(f"{message} ({window_total:.0f} fe in {WINDOW_SECONDS}s)")

    async def startup(self):
        logger.info("AchievementService started")

    async def shutdown(self):
        logger.info("AchievementService shutdown")
