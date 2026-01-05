import os
import asyncio
from typing import AsyncGenerator

from Oracle.tooling.logger import Logger

logger = Logger("LogReader")

class LogReader:
    def __init__(self, path: str, start_at_end: bool = True, poll_interval: float = 0.1, wait_timeout: float = 300.0):
        self.path = path
        self.start_at_end = start_at_end
        self.poll_interval = poll_interval
        self.wait_timeout = wait_timeout  # Maximum time to wait for file (default 5 minutes)
        self._pos = 0
        self._running = False
        self._last_mtime = 0.0
        self._last_size = 0

    async def __aenter__(self):
        logger.info(f"Waiting for: {self.path} (timeout: {self.wait_timeout}s)")
        
        # Wait for file with timeout
        elapsed = 0.0
        wait_interval = 0.2
        while not os.path.exists(self.path):
            if elapsed >= self.wait_timeout:
                logger.error(f"Timeout waiting for file: {self.path}")
                raise TimeoutError(f"File not found after {self.wait_timeout}s: {self.path}")
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval
        
        logger.info(f"File found: {self.path}")
        self._last_mtime = os.path.getmtime(self.path)
        size = os.path.getsize(self.path)
        self._last_size = size
        self._pos = size if self.start_at_end else 0
        self._running = True
        logger.debug(f"Reading log @ {self._pos}")
        return self

    async def __aexit__(self, *exc):
        self._running = False
        logger.info("Closed")

    async def __aiter__(self) -> AsyncGenerator[str, None]:
        while self._running:
            try:
                # Check if file still exists
                if not os.path.exists(self.path):
                    logger.warning(f"Log file disappeared: {self.path}")
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                mtime = os.path.getmtime(self.path)
                current_size = os.path.getsize(self.path)
                should_read = False

                # Detect file truncation or recreation (game restart)
                if current_size < self._last_size:
                    logger.debug(f"Log file truncated or recreated (size: {self._last_size} -> {current_size})")
                    self._pos = 0
                    # Wait a bit for game to finish writing initial content
                    await asyncio.sleep(0.2)
                    # Re-check size after waiting
                    current_size = os.path.getsize(self.path)
                    mtime = os.path.getmtime(self.path)
                    self._last_size = current_size
                    self._last_mtime = mtime
                    should_read = True  # Force read after truncation
                    logger.info(f"Reading from start after truncation (new size: {current_size})")

                # Read new content if file was modified or size changed
                elif mtime != self._last_mtime or current_size != self._last_size:
                    should_read = True
                    self._last_mtime = mtime
                    self._last_size = current_size

                if should_read:
                    with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self._pos)
                        chunk = f.read()
                        self._pos = f.tell()

                    if chunk:
                        for line in chunk.splitlines():
                            if not self._running:  # Check before yielding
                                return
                            yield line.rstrip("\r\n")

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                # Task was cancelled, exit cleanly
                logger.debug("LogReader cancelled")
                self._running = False
                raise
            except Exception as e:
                logger.error(f"Error reading log: {e}")
                await asyncio.sleep(0.5)
