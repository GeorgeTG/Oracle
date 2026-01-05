"""
Cross-platform file monitoring with asyncio support and aggressive polling.
Uses ProcessPoolExecutor for non-blocking file I/O.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

from Oracle.tooling.logger import Logger

logger = Logger("NotifyReader")

def _read_file_info(filepath: str, position: int) -> dict:
    """
    Read file info and new lines, detecting truncation/rotation.
    Runs in executor to avoid blocking event loop.
    
    Args:
        filepath: Path to file
        position: Current file position
        
    Returns:
        Dict with: lines, new_position, file_size, inode, exists, truncated
    """
    result = {
        'lines': [],
        'new_position': position,
        'file_size': 0,
        'inode': None,
        'exists': False,
        'truncated': False
    }
    
    try:
        # Get file stats
        stat = os.stat(filepath)
        result['exists'] = True
        result['file_size'] = stat.st_size
        result['inode'] = stat.st_ino
        
        # Detect truncation (file size smaller than our position)
        if stat.st_size < position:
            result['truncated'] = True
            position = 0  # Reset to beginning
        
        # Read new lines
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(position)
            for line in f:
                result['lines'].append(line.rstrip('\n\r'))
            result['new_position'] = f.tell()
            
    except FileNotFoundError:
        result['exists'] = False
    except Exception:
        # File might be locked temporarily
        pass
    
    return result


class NotifyReader:
    """
    Asynchronous file reader with non-blocking polling.
    Uses ThreadPoolExecutor for file I/O to avoid blocking the event loop.
    """
    
    def __init__(self, filepath: Path | str, poll_interval: float = 0.05):
        """
        Initialize the notify reader.
        
        Args:
            filepath: Path to the file to monitor
            poll_interval: Polling interval in seconds (default 50ms for low latency)
        """
        self.filepath = Path(filepath).resolve()
        self.poll_interval = poll_interval
        self._position = 0
        self._last_inode = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="NotifyReader")
        self._stop_event = asyncio.Event()
        
    async def stop(self):
        """Stop following the file."""
        self._stop_event.set()
        self._executor.shutdown(wait=False)
        
    async def follow(self) -> AsyncIterator[str]:
        """
        Follow the file and yield new lines as they are written.
        Uses non-blocking I/O via executor.
        
        Yields:
            New lines from the file
        """
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        loop = asyncio.get_event_loop()
        
        try:
            # Seek to end of file without reading existing content
            info = await loop.run_in_executor(
                self._executor,
                _read_file_info,
                str(self.filepath),
                0
            )
            
            # Start from end of file
            self._position = info['file_size']
            self._last_inode = info['inode']
            
            # Poll for new content
            while not self._stop_event.is_set():
                await asyncio.sleep(self.poll_interval)
                
                # Read file info and new lines
                info = await loop.run_in_executor(
                    self._executor,
                    _read_file_info,
                    str(self.filepath),
                    self._position
                )
                
                if not info['exists']:
                    # File was deleted, wait for it to reappear
                    continue
                
                # Detect file rotation (inode changed)
                if self._last_inode and info['inode'] != self._last_inode:
                    # File was rotated, start from beginning
                    self._position = 0
                    self._last_inode = info['inode']
                    # Re-read from beginning
                    info = await loop.run_in_executor(
                        self._executor,
                        _read_file_info,
                        str(self.filepath),
                        0
                    )
                elif info['truncated']:
                    # File was truncated, position already reset in executor
                    self._last_inode = info['inode']
                
                # Update position
                self._position = info['new_position']
                
                # Yield new lines
                for line in info['lines']:
                    yield line
        finally:
            self._executor.shutdown(wait=False)


async def follow_file(filepath: Path | str, poll_interval: float = 0.05) -> AsyncIterator[str]:
    """
    Convenience function to follow a file with aggressive polling.
    
    Args:
        filepath: Path to the file to monitor
        poll_interval: Polling interval in seconds (default 50ms)
    
    Yields:
        New lines from the file
    
    Example:
        async for line in follow_file("game.log"):
            print(f"New line: {line}")
    """
    reader = NotifyReader(filepath, poll_interval)
    async for line in reader.follow():
        yield line
