"""Data models for the Temporal Paradox Resolver.

Three kinds of things live here:

* ``DecisionRecord``  - the snapshot of a choice, captured at the moment it was made.
* ``Commitment``      - the lock placed on that choice: how sure you were, what
  would make you reconsider (tripwires), and the doubts you have logged since.
* ``Doubt`` / ``Tripwire`` / ``Event`` - the pieces a commitment is built from.

Everything serialises to plain dicts so it can be stored as JSON.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def to_iso(moment: dt.datetime) -> str:
    return moment.astimezone(dt.timezone.utc).isoformat()


def parse_iso(value: str) -> dt.datetime:
    """Parse an ISO timestamp; naive or ``Z``-suffixed values are treated as UTC."""
    moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    return moment


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Decision snapshot
# ---------------------------------------------------------------------------
@dataclass
class DecisionRecord:
    """A major decision, frozen at the moment of choice."""

    choice: str
    chosen: str = ""
    values_ranked: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)
    timestamp: str = field(default_factory=lambda: to_iso(utcnow()))

    def alternative_names(self) -> List[str]:
        return [str(a.get("name", "")) for a in self.alternatives if a.get("name")]

    def unchosen(self) -> List[Dict[str, Any]]:
        chosen = self.chosen.strip().lower()
        return [a for a in self.alternatives if str(a.get("name", "")).strip().lower() != chosen]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DecisionRecord":
        return DecisionRecord(
            id=d.get("id") or new_id(),
            timestamp=d.get("timestamp") or to_iso(utcnow()),
            choice=d.get("choice", ""),
            chosen=d.get("chosen", ""),
            values_ranked=list(d.get("values_ranked", [])),
            alternatives=list(d.get("alternatives", [])),
            reasoning=d.get("reasoning", ""),
            context=dict(d.get("context", {})),
            notes=d.get("notes", ""),
            tags=list(d.get("tags", [])),
        )


# ---------------------------------------------------------------------------
# Commitment pieces
# ---------------------------------------------------------------------------
@dataclass
class Tripwire:
    """A condition, written while calm, under which you agree to reconsider.

    Example: "My manager leaves within the first six months" or
    "I have been unhappy at work for three months in a row".
    """

    condition: str
    id: str = field(default_factory=new_id)
    triggered: bool = False
    triggered_at: Optional[str] = None
    evidence: str = ""
    spent: bool = False        # set once a review has dealt with this trigger

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Tripwire":
        return Tripwire(
            condition=d.get("condition", ""),
            id=d.get("id") or new_id(),
            triggered=bool(d.get("triggered", False)),
            triggered_at=d.get("triggered_at"),
            evidence=d.get("evidence", ""),
            spent=bool(d.get("spent", False)),
        )


@dataclass
class Doubt:
    """A moment of second-guessing, logged instead of acted on.

    ``is_new_information`` is the most important field: was this fact unknown
    (or impossible to know) when you decided? Re-arguing a trade-off you already
    weighed is not new information.
    """

    text: str
    is_new_information: bool = False
    affects_value: str = ""
    severity: int = 3          # 1 (a nagging thought) .. 5 (a serious problem)
    energy_level: int = 6      # 1 (exhausted) .. 10 (fully rested)
    stress_level: int = 4      # 1 (calm) .. 10 (overwhelmed)
    id: str = field(default_factory=new_id)
    timestamp: str = field(default_factory=lambda: to_iso(utcnow()))

    def __post_init__(self) -> None:
        self.severity = _clamp(self.severity, 1, 5)
        self.energy_level = _clamp(self.energy_level, 1, 10)
        self.stress_level = _clamp(self.stress_level, 1, 10)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Doubt":
        return Doubt(
            text=d.get("text", ""),
            is_new_information=bool(d.get("is_new_information", False)),
            affects_value=d.get("affects_value", ""),
            severity=int(d.get("severity", 3)),
            energy_level=int(d.get("energy_level", 6)),
            stress_level=int(d.get("stress_level", 4)),
            id=d.get("id") or new_id(),
            timestamp=d.get("timestamp") or to_iso(utcnow()),
        )


@dataclass
class Event:
    """One line in a commitment's permanent history."""

    kind: str                  # committed | doubt | tripwire | reviewed | reaffirmed | reversed
    detail: str = ""
    timestamp: str = field(default_factory=lambda: to_iso(utcnow()))

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Event":
        return Event(kind=d.get("kind", ""), detail=d.get("detail", ""),
                     timestamp=d.get("timestamp") or to_iso(utcnow()))


STATUS_COMMITTED = "committed"
STATUS_REVERSED = "reversed"


@dataclass
class Commitment:
    """The lock on a decision."""

    decision_id: str
    conviction: int = 7                       # 1..10, how sure you were when you decided
    anchor: str = ""                          # a note to your future, doubting self
    cooling_days: int = 30                    # no reconsidering (bar tripwires) inside this window
    tripwires: List[Tripwire] = field(default_factory=list)
    doubts: List[Doubt] = field(default_factory=list)
    history: List[Event] = field(default_factory=list)
    reaffirmations: int = 0
    status: str = STATUS_COMMITTED
    locked_at: str = field(default_factory=lambda: to_iso(utcnow()))

    def __post_init__(self) -> None:
        self.conviction = _clamp(self.conviction, 1, 10)
        self.cooling_days = max(0, int(self.cooling_days))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Commitment":
        return Commitment(
            decision_id=d["decision_id"],
            conviction=int(d.get("conviction", 7)),
            anchor=d.get("anchor", ""),
            cooling_days=int(d.get("cooling_days", 30)),
            tripwires=[Tripwire.from_dict(t) for t in d.get("tripwires", [])],
            doubts=[Doubt.from_dict(x) for x in d.get("doubts", [])],
            history=[Event.from_dict(e) for e in d.get("history", [])],
            reaffirmations=int(d.get("reaffirmations", 0)),
            status=d.get("status", STATUS_COMMITTED),
            locked_at=d.get("locked_at") or to_iso(utcnow()),
        )


def _clamp(value: Any, low: int, high: int) -> int:
    return max(low, min(high, int(value)))
