from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from Oracle.parsing.parsers.events import ParserEvent, ParserEventType


@dataclass
class AffixModel:
    """Represents a single map affix ID and description."""
    affix_id: int
    description: Optional[str] = ""


@dataclass(kw_only=True)
class StageAffixEvent(ParserEvent):
    """Represents a group of affixes applied to a map stage."""
    affixes: list[AffixModel]
    level_id: Optional[int] = None
    type: ParserEventType = ParserEventType.STAGE_AFFIX

    def __repr__(self):
        return (
            f"<StageAffixEvent {len(self.affixes)} affixes "
            f"@ {self.timestamp.isoformat()}>"
            f"@ {self.level_id}" if self.level_id is not None else ""
        )
