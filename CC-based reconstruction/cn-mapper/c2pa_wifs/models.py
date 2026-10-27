"""Shared result types for the classification pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import List, Optional


class Category(str, Enum):
    NO_MANIFEST = "no_manifest"
    UNSUPPORTED_TOOL = "unsupported_tool"
    SAME = "same"
    SIMILAR = "similar"
    NONE_IN_DB = "none_in_db"


@dataclass
class ClassificationRecord:
    image: str
    category: Category
    message: str
    tool: Optional[str] = None
    preset_names: List[str] = field(default_factory=list)
    matching_actions: int = 0
    total_actions: int = 0
    active_total_actions: int = 0
    extra_actions: int = 0
    match_percentage: float = 0.0
    shortlist: List[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        return d