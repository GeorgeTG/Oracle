from __future__ import annotations
import re
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional

from Oracle.parsing.parsers.parser_base import ParserBase
from Oracle.parsing.parsers.events.stage_affix import StageAffixEvent, AffixModel


TIMESTAMP_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):(\d{3})]"
)

ENTER_LEVEL_RE = re.compile(
    r"EnterLevel\((\d+)\)"
)

AFFIX_LIST_START_RE = re.compile(
    r"AffixInfos"
)

DANGER_NUMBERS_RE = re.compile(
    r"\+DangerNumbers"
)

AFFIX_ID_RE = re.compile(
    r"\+Id\s*\[(\d+)\]"
)

DESCRIPTION_RE = re.compile(
    r"\+Description\s*\[(.*?)\]"
)

AFFIX_LIST_END_RE = re.compile(
    r"OnEnterAreaEnd\(\)"
)


class StageAffixParser(ParserBase):
    __PARSER__ = {
        "name": "StageAffixParser",
        "version": "0.0.1",
        "description": "Parses stage modifiers and affixes"
    }
    """
    Detects map affix lists:
    - Start: "AffixInfos"
    - Collect: Each +DangerNumbers block with +Id and +Description
    - End: "OnEnterAreaEnd()"
    Emits: StageAffixEvent(timestamp, level_id, [AffixModel...])
    """

    def __init__(self):
        super().__init__()

        self._pending_affixes: list[AffixModel] = []
        self._current_level_id: Optional[int] = None
        self._collecting_affixes: bool = False
        self._block_timestamp: Optional[datetime] = None
        self._current_affix_id: Optional[int] = None
        self._current_description: Optional[str] = None

    async def feed_line(self, line: str) -> None:
        # Level ID detection
        m_level = ENTER_LEVEL_RE.search(line)
        if m_level:
            self._current_level_id = int(m_level.group(1))

        # Detect timestamp
        ts = None
        m_ts = TIMESTAMP_RE.search(line)
        if m_ts:
            date_str, time_str, ms_str = m_ts.groups()
            ts = datetime.strptime(
                f"{date_str} {time_str}.{ms_str}",
                "%Y.%m.%d %H.%M.%S.%f"
            )

        # Start collecting affixes (AffixInfos)
        if AFFIX_LIST_START_RE.search(line):
            self._collecting_affixes = True
            self._pending_affixes = []
            self._block_timestamp = ts
            self._current_affix_id = None
            self._current_description = None
            return

        # End of affix collection (OnEnterAreaEnd)
        if AFFIX_LIST_END_RE.search(line):
            if self._collecting_affixes:
                # Save last affix if exists
                if self._current_affix_id is not None:
                    self._pending_affixes.append(
                        AffixModel(
                            affix_id=self._current_affix_id,
                            description=self._current_description
                        )
                    )
                
                # Emit event if we have affixes
                if self._pending_affixes and self._current_level_id and self._block_timestamp:
                    model = StageAffixEvent(
                        timestamp=self._block_timestamp,
                        level_id=self._current_level_id,
                        affixes=self._pending_affixes.copy()
                    )
                    await self._emit(model)

                # Reset state
                self._collecting_affixes = False
                self._pending_affixes = []
                self._block_timestamp = None
                self._current_affix_id = None
                self._current_description = None
            return

        # Ignore if not collecting affixes
        if not self._collecting_affixes:
            return

        # New affix block (+DangerNumbers)
        if DANGER_NUMBERS_RE.search(line):
            # Save previous affix if exists
            if self._current_affix_id is not None:
                self._pending_affixes.append(
                    AffixModel(
                        affix_id=self._current_affix_id,
                        description=self._current_description
                    )
                )
            # Reset for new affix
            self._current_affix_id = None
            self._current_description = None
            return

        # Collect Description
        m_desc = DESCRIPTION_RE.search(line)
        if m_desc:
            self._current_description = m_desc.group(1)
            return

        # Collect ID
        m_id = AFFIX_ID_RE.search(line)
        if m_id:
            self._current_affix_id = int(m_id.group(1))
            return
