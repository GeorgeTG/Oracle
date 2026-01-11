# Oracle/parsing/router.py

import asyncio
import importlib
import os
import pkgutil
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events import ParserEvent
from Oracle.parsing.loaders import get_loader
from Oracle.events import EventBus
from Oracle.tooling.singleton import SingletonMixin
from Oracle.tooling.logger import Logger
from Oracle.tooling.config import Config
from Oracle.tooling.paths import get_base_path
from Oracle.parsing.parsers.events.loading_progress import LoadingProgressEvent

logger = Logger("Router")

class Router(SingletonMixin):
    """
    Main log event router.
    - Feeds log lines into all parsers
    - Collects parsed events and publishes to EventBus
    """

    def __init__(self, event_bus: EventBus):
        self.parsers: List[ParserBase] = []
        self.queue: asyncio.Queue[ParserEvent] = asyncio.Queue(maxsize=1000)
        self._condition = asyncio.Condition()
        self._event_bus = event_bus
        
        # Check if parser logging is enabled
        config = Config()
        parser_config = config.get("parser")
        self._parser_logging_enabled = parser_config.get("log", False)
        
        # Setup event logging with rotation only if enabled
        self._log_dir = get_base_path() / 'logs'
        self._max_file_size = 10 * 1024 * 1024  # 10MB
        self._max_files = 5
        self._current_log_file: Optional[Path] = None
        self._file_size = 0
        self._event_log_file = None
        
        if self._parser_logging_enabled:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            # TODO: Restore _get_log_file() method
            # self._get_log_file()  # Initialize log file
            logger.info("📝 Parser event logging enabled")
        else:
            logger.info("⚪ Parser event logging disabled")

        # Dynamically discover available parsers
        self._load_parsers()

        # Background tasks: each parser has a result drainer
        self._tasks = [
            asyncio.create_task(self._drain_parser(p))
            for p in self.parsers
        ]
        
        # Background task: publish events to EventBus
        self._publisher_task = asyncio.create_task(self._publish_events())

    async def _publish_events(self):
        """Background task: publish events from queue to EventBus."""
        try:
            while True:
                async with self._condition:
                    await self._condition.wait()
                
                while not self.queue.empty():
                    event = await self.queue.get()
                    
                    # Log event to file if enabled
                    if self._parser_logging_enabled:
                        parser_name = event.__class__.__module__.split('.')[-1]
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        log_line = f"[{timestamp}] [{parser_name}] - {event.__class__.__name__} - {event}\n"
                        self._write_event_log(log_line)
                    
                    await self._event_bus.publish(event)
        except Exception as e:
            logger.error(f"❌ _publish_events crashed: {e}")
            logger.trace(e)
        # Check if we need to rotate
        if self._current_log_file.exists():
            self._file_size = self._current_log_file.stat().st_size
            if self._file_size >= self._max_file_size:
                self._rotate_logs()
    
    def _rotate_logs(self):
        """Rotate log files when size limit is reached."""
        # Close current file
        if self._event_log_file:
            self._event_log_file.close()
        
        # Create new log file
        timestamp = datetime.now().strftime("%d_%m_%y_%H_%M_%S")
        self._current_log_file = self._log_dir / f"Oracle_Parser_{timestamp}.log"
        self._file_size = 0
        self._event_log_file = open(self._current_log_file, 'a', encoding='utf-8')
        
        # Clean up old log files
        log_files = sorted(self._log_dir.glob("Oracle_Parser_*.log"))
        if len(log_files) > self._max_files:
            for old_file in log_files[:-self._max_files]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
    
    def _write_event_log(self, log_line: str):
        """Write event log line and check for rotation."""
        if self._event_log_file:
            self._event_log_file.write(log_line)
            self._event_log_file.flush()
            self._file_size += len(log_line.encode('utf-8'))
            
            # Check if rotation needed
            if self._file_size >= self._max_file_size:
                self._rotate_logs()

    def _load_parsers(self):
        logger.info("Loading parsers...")
        self.parsers.clear()
        
        loader = get_loader()
        parser_classes = loader.load_parsers()
        
        for parser_class in parser_classes:
            try:
                version = getattr(parser_class, '__PARSER__', {}).get('version', 'unknown')
                logger.info(f"🛠️  Loaded parser: {parser_class.__name__} v{version}")
                self.parsers.append(parser_class())
            except Exception as e:
                logger.error(f"Failed to instantiate parser {parser_class.__name__}: {e}")
                logger.trace(e)
        
        logger.info(f"✅ Loaded {len(self.parsers)} parsers")

    async def feed_line(self, line: str) -> None:
        """
        Feed a log line to every parser.
        Parsers run independently — one failing does not affect the rest.
        """
        for p in self.parsers:
            try:
                await p.feed_line(line)
            except Exception as e:
                logger.error(f"Parser {p.__class__.__name__}: {e}")
                logger.trace(e)

    async def _drain_parser(self, parser: ParserBase) -> None:
        """
        Background task: listen to parser results stream.
        Each yielded ModelBase → queued and notifies consumers.
        """
        try:
            async for event in parser.results():
                await self.queue.put(event)  # Put without holding the lock
                async with self._condition:
                    self._condition.notify()
        except Exception as e:
            logger.error(f"❌ _drain_parser error for {parser.__class__.__name__}: {e}")
            logger.trace(e)

    def get_loaded_parsers(self) -> List[str]:
        """Return list of loaded parser class names."""
        return [p.__class__.__name__ for p in self.parsers]

    async def shutdown(self):
        """Shutdown router and cancel all background tasks."""
        logger.info("🛑 Shutting down Router...")
        
        # Cancel all parser drain tasks
        for task in self._tasks:
            task.cancel()
        
        # Cancel publisher task
        self._publisher_task.cancel()
        
        # Wait for all tasks to finish
        all_tasks = self._tasks + [self._publisher_task]
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error(f"Error during task shutdown: {result}")
        
        # Close log file
        if self._event_log_file:
            self._event_log_file.close()
            logger.debug("✅ Closed event log file")
        
        logger.info("✅ Router shutdown complete")

    async def drain_results(self) -> AsyncGenerator[ParserEvent, None]:
        """
        Stream ALL parsed events from ALL parsers as they appear.
        Suitable for WebSocket broadcast pipeline.
        """
        while True:
            async with self._condition:
                await self._condition.wait()

                while not self.queue.empty():
                    yield await self.queue.get()
