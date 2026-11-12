"""Data models for the Temporal Paradox Resolver."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class DecisionRecord:
    """Immutable-ish record of a major decision captured at the moment of choice."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: dt.datetime.utcnow().isoformat() + "Z")
    choice: str = ""
    values_ranked: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "choice": self.choice,
            "values_ranked": self.values_ranked,
            "alternatives": self.alternatives,
            "context": self.context,
            "notes": self.notes,
            "tags": self.tags,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DecisionRecord":
        # Ensure backward‑compatible defaults
        return DecisionRecord(
            id=d.get("id", ""),
            timestamp=d.get("timestamp", dt.datetime.utcnow().isoformat() + "Z"),
            choice=d.get("choice", ""),
            values_ranked=d.get("values_ranked", []),
            alternatives=d.get("alternatives", []),
            context=d.get("context", {}),
            notes=d.get("notes", ""),
            tags=d.get("tags", []),
        )