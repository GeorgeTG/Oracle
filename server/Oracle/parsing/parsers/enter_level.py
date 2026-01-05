from __future__ import annotations
import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional
from enum import Enum

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.enter_level import EnterLevelEvent
from Oracle.parsing.parsers.maps import get_map_by_id
from Oracle.tooling.logger import Logger

logger = Logger("EnterLevelParser")


# FSM States for parsing the 3-line EnterLevel sequence
class ParseState(Enum):
    IDLE = 0
    GOT_ENTER = 1
    GOT_LEVEL_INFO = 2


# Regex patterns for the 3-line sequence
# Line 1: [timestamp]GameLog: Display: [Game] LevelMgr@ EnterLevel
ENTER_LEVEL_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})\].*GameLog: Display: \[Game\] LevelMgr@ EnterLevel$"
)

# Line 2: [timestamp]GameLog: Display: [Game] LevelMgr@ LevelUid, LevelType, LevelId = 1121002 3 5302
# OR: [timestamp]GameLog: Display: [Game] LeevelLinkData： 1121102 3 5314
LEVEL_INFO_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})\].*GameLog: Display: \[Game\] LevelMgr@ LevelUid, LevelType, LevelId = (\d+) (\d+) (\d+)"
)
LEVEL_INFO_ALT_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})\].*GameLog: Display: \[Game\] LeevelLinkData[：:]\s*(\d+)\s+(\d+)\s+(\d+)"
)

# Line 3: [timestamp]GameLog: Display: [Game] LevelMgr@:LevelPath, Model = <path> <model>
LEVEL_PATH_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})\].*GameLog: Display: \[Game\] LevelMgr@:LevelPath, Model = (.+)"
)


class EnterLevelParser(ParserBase):
    __PARSER__ = {
        "name": "EnterLevelParser",
        "version": "0.0.1",
        "description": "Parses level/map entry events"
    }

    def __init__(self):
        super().__init__()  # Initialize ParserBase with asyncio.Queue
        
        # FSM state
        self._state = ParseState.IDLE
        self._timestamp: Optional[datetime] = None
        self._level_uid: Optional[int] = None
        self._level_type: Optional[int] = None
        self._level_id: Optional[int] = None
        
        # Counter for failed state transitions
        self._non_idle_counter = 0
        
        # Timestamp of when we entered non-IDLE state (for timeout)
        self._state_entered_at: Optional[datetime] = None
        self._state_timeout_seconds = 2.0  # Reset if stuck for more than 5 seconds

    def _reset_fsm(self):
        """Reset FSM to IDLE state and clear data."""
        self._state = ParseState.IDLE
        self._timestamp = None
        self._level_uid = None
        self._level_type = None
        self._level_id = None
        self._non_idle_counter = 0
        self._state_entered_at = None

    async def feed_line(self, line: str) -> None:
        # Check for timeout if we're stuck in non-IDLE state
        if self._state != ParseState.IDLE and self._state_entered_at is not None:
            elapsed = (datetime.now() - self._state_entered_at).total_seconds()
            if elapsed > self._state_timeout_seconds:
                logger.warning(
                    f'[EnterLevelParser] Timeout reset - stuck in {self._state.name} '
                    f'for {elapsed:.1f}s (limit: {self._state_timeout_seconds}s)'
                )
                self._reset_fsm()
                # Continue processing this line from IDLE state
        
        # Increment counter if we're not in IDLE state
        if self._state != ParseState.IDLE:
            self._non_idle_counter += 1
            
            # Force reset if counter reaches 6
            if self._non_idle_counter >= 6:
                self._reset_fsm()
                return
        
        # State machine for 3-line parsing
        if self._state == ParseState.IDLE:
            m = ENTER_LEVEL_RE.search(line)
            if m:
                date_str, time_str, ms_str = m.groups()
                self._timestamp = datetime.strptime(
                    f"{date_str} {time_str}.{ms_str}",
                    "%Y.%m.%d %H.%M.%S.%f"
                )
                self._state = ParseState.GOT_ENTER
                self._non_idle_counter = 0
                self._state_entered_at = datetime.now()  # Track when we entered this state
        
        elif self._state == ParseState.GOT_ENTER:
            # Try both regex patterns for LEVEL_INFO
            m = LEVEL_INFO_RE.search(line)
            if not m:
                m = LEVEL_INFO_ALT_RE.search(line)
            
            if m:
                date_str, time_str, ms_str, uid, ltype, lid = m.groups()
                self._level_uid = int(uid)
                self._level_type = int(ltype)
                self._level_id = int(lid)
                self._state = ParseState.GOT_LEVEL_INFO
            else:
                # Ignore lines that don't match - just continue waiting for LEVEL_INFO
                pass
        
        elif self._state == ParseState.GOT_LEVEL_INFO:
            m = LEVEL_PATH_RE.search(line)
            if m:
                # We got all 3 lines, create event
                event = EnterLevelEvent(
                    timestamp=self._timestamp,
                    level_id=self._level_id,
                    level_uid=self._level_uid,
                    level_type=self._level_type,
                    map=get_map_by_id(self._level_id)
                )
                
                # Use ParserBase's _emit method with asyncio.Queue
                await self._emit(event)
                
                # Reset FSM (successful parse)
                self._reset_fsm()
            else:
                # Ignore lines that don't match LEVEL_PATH - continue waiting
                pass
