# Oracle/parsing/parsers/maps/difficulty.py

from enum import Enum
from typing import List


class OrderedEnumMixin:
    """Mixin to add ordered list functionality to Enums."""
    
    @classmethod
    def to_list(cls) -> List['Difficulty']:
        """Return ordered list of enum values."""
        return list(cls)
    
    @classmethod
    def index_of(cls, value: 'Difficulty') -> int:
        """Get the index of an enum value in the ordered list."""
        return cls.to_list().index(value)


class Difficulty(OrderedEnumMixin, str, Enum):
    """Map difficulty tiers in descending order (hardest to easiest)."""
    T8_PLUS = "T8+"
    T8_2 = "T8_2"
    T8_1 = "T8_1"
    T8_0 = "T8_0"
    T7_2 = "T7_2"
    T7_1 = "T7_1"
    T7_0 = "T7_0"
    T6 = "T6"
    T5 = "T5"
    T4 = "T4"
    T3 = "T3"
    T2 = "T2"
    T1 = "T1"
    DS = "DS"
    
    def __str__(self) -> str:
        return self.value
