"""The Commitment Engine: once a decision is made, hold it.

The "temporal paradox" this project resolves is the argument between two
versions of you: the past self who made a decision calmly, with all the
information available at the time, and the present self who is doubting it,
often tired, stressed, or replaying a trade-off that was already weighed.

The engine sides with the past self by default. The present self wins only by
bringing *new* evidence that is strong, about something you actually care
about, felt in a clear state of mind, and persistent over time. Or by tripping
a condition the past self wrote down in advance.

Every verdict is deterministic and explained line by line. No LLM is involved,
so the same history always produces the same answer.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .models import (
    STATUS_COMMITTED,
    STATUS_REVERSED,
    Commitment,
    DecisionRecord,
    Doubt,
    Event,
    Tripwire,
    parse_iso,
    to_iso,
    utcnow,
)

HOLD = "HOLD"
WATCH = "WATCH"
RECONSIDER = "RECONSIDER"

MIN_REVERSAL_REASON = 40  # characters


class CommitmentLocked(Exception):
    """Raised when someone tries to reverse a decision the engine is holding."""

    def __init__(self, verdict: "Verdict"):
        self.verdict = verdict
        super().__init__(
            f"Decision is locked ({verdict.decision}). " + " ".join(verdict.reasons)
        )


@dataclass(frozen=True)
class Policy:
    """Every number the engine uses, in one place, so it can be tuned openly."""

    base_threshold: float = 6.0          # evidence needed at conviction 0
    per_conviction: float = 1.2          # extra evidence needed per conviction point
    reaffirm_multiplier: float = 1.25    # each reaffirmation makes the lock 25% harder
    old_news_weight: float = 0.25        # a doubt that is not new information
    unranked_value_weight: float = 0.5   # a doubt about something you did not rank
    tired_or_stressed_weight: float = 0.5   # energy <= 3 or stress >= 8
    strained_weight: float = 0.75           # energy <= 5 or stress >= 6
    half_life_days: float = 60.0         # a doubt that is not repeated fades
    min_new_info_doubts: int = 2         # one bad day is never enough
    min_persistence_days: int = 7        # the case must hold up for at least a week
    watch_ratio: float = 0.6             # evidence this close to the bar earns a WATCH
    cooling_override_ratio: float = 2.0  # what it takes to break the cooling period


DEFAULT_POLICY = Policy()


@dataclass
class DoubtScore:
    doubt: Doubt
    score: float
    factors: List[str]


@dataclass
class Verdict:
    decision: str
    evidence: float
    threshold: float
    reasons: List[str]
    days_committed: int
    cooling_days_left: int
    scored_doubts: List[DoubtScore] = field(default_factory=list)
    triggered_tripwires: List[Tripwire] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.evidence / self.threshold if self.threshold else 0.0

    @property
    def can_reverse(self) -> bool:
        return self.decision == RECONSIDER


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def value_weight(record: DecisionRecord, value: str, policy: Policy = DEFAULT_POLICY) -> Tuple[float, str]:
    """Top-ranked value weighs 1.0; the last ranked value weighs 1/n."""
    ranked = [v.strip().lower() for v in record.values_ranked]
    wanted = value.strip().lower()
    if wanted and wanted in ranked:
        n = len(ranked)
        rank = ranked.index(wanted)
        return (n - rank) / n, f"touches your #{rank + 1} value '{record.values_ranked[rank]}'"
    if wanted:
        return policy.unranked_value_weight, f"'{value}' was not one of your ranked values"
    return policy.unranked_value_weight, "not tied to any ranked value"


def score_doubt(
    doubt: Doubt,
    record: DecisionRecord,
    now: Optional[dt.datetime] = None,
    policy: Policy = DEFAULT_POLICY,
) -> DoubtScore:
    now = now or utcnow()
    factors: List[str] = [f"severity {doubt.severity}/5"]
    score = float(doubt.severity)

    if doubt.is_new_information:
        factors.append("new information (full weight)")
    else:
        score *= policy.old_news_weight
        factors.append(f"already known when you decided (x{policy.old_news_weight})")

    weight, why = value_weight(record, doubt.affects_value, policy)
    score *= weight
    factors.append(f"{why} (x{weight:.2f})")

    if doubt.energy_level <= 3 or doubt.stress_level >= 8:
        score *= policy.tired_or_stressed_weight
        factors.append(f"logged while exhausted or overwhelmed (x{policy.tired_or_stressed_weight})")
    elif doubt.energy_level <= 5 or doubt.stress_level >= 6:
        score *= policy.strained_weight
        factors.append(f"logged while strained (x{policy.strained_weight})")

    age_days = max(0.0, (now - parse_iso(doubt.timestamp)).total_seconds() / 86400)
    if age_days >= 1:
        decay = math.pow(0.5, age_days / policy.half_life_days)
        score *= decay
        factors.append(f"{age_days:.0f} days old (x{decay:.2f})")

    return DoubtScore(doubt=doubt, score=round(score, 3), factors=factors)


def threshold(commitment: Commitment, policy: Policy = DEFAULT_POLICY) -> float:
    base = policy.base_threshold + policy.per_conviction * commitment.conviction
    return round(base * math.pow(policy.reaffirm_multiplier, commitment.reaffirmations), 3)


def _last_review(commitment: Commitment) -> Optional[dt.datetime]:
    reviews = [parse_iso(e.timestamp) for e in commitment.history if e.kind == "reaffirmed"]
    return max(reviews) if reviews else None


def live_doubts(commitment: Commitment) -> List[Doubt]:
    """Doubts logged since the last reaffirmation. Older ones were already answered."""
    cutoff = _last_review(commitment)
    if cutoff is None:
        return list(commitment.doubts)
    return [d for d in commitment.doubts if parse_iso(d.timestamp) > cutoff]


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------
def evaluate(
    commitment: Commitment,
    record: DecisionRecord,
    now: Optional[dt.datetime] = None,
    policy: Policy = DEFAULT_POLICY,
) -> Verdict:
    now = now or utcnow()
    locked_at = parse_iso(commitment.locked_at)
    days_committed = max(0, (now - locked_at).days)
    cooling_left = max(0, commitment.cooling_days - days_committed)
    bar = threshold(commitment, policy)

    if commitment.status == STATUS_REVERSED:
        return Verdict(RECONSIDER, 0.0, bar, ["This decision has already been reversed."],
                       days_committed, 0)

    scored = [score_doubt(d, record, now, policy) for d in live_doubts(commitment)]
    evidence = round(sum(s.score for s in scored), 3)
    tripped = [t for t in commitment.tripwires if t.triggered and not t.spent]

    def verdict(decision: str, reasons: List[str]) -> Verdict:
        return Verdict(decision, evidence, bar, reasons, days_committed, cooling_left, scored, tripped)

    # 1. Conditions your past self agreed to always win.
    if tripped:
        names = "; ".join(f"'{t.condition}'" for t in tripped)
        return verdict(RECONSIDER, [
            f"A tripwire you set in advance has been triggered: {names}.",
            "You agreed, while calm, that this is a real reason to look again. "
            "Review the decision honestly, then reaffirm or reverse it.",
        ])

    # 2. Otherwise the present self has to make a case.
    qualifying = [s for s in scored if s.doubt.is_new_information and s.score > 0]
    reasons: List[str] = [
        f"Evidence against the decision: {evidence:.1f} of the {bar:.1f} needed "
        f"(conviction {commitment.conviction}/10"
        + (f", reaffirmed {commitment.reaffirmations}x" if commitment.reaffirmations else "")
        + ")."
    ]
    blockers: List[str] = []

    if evidence < bar:
        blockers.append("The evidence has not reached the bar.")
    if len(qualifying) < policy.min_new_info_doubts:
        blockers.append(
            f"Only {len(qualifying)} doubt(s) bring new information; at least "
            f"{policy.min_new_info_doubts} are needed. Re-arguing known trade-offs does not count."
        )
    if qualifying:
        times = [parse_iso(s.doubt.timestamp) for s in qualifying]
        span = (max(times) - min(times)).days
    else:
        span = 0
    if span < policy.min_persistence_days:
        blockers.append(
            f"The new evidence spans {span} day(s); it must persist for at least "
            f"{policy.min_persistence_days} days. Feelings that fade were not reasons."
        )
    if cooling_left and evidence < bar * policy.cooling_override_ratio:
        blockers.append(
            f"You are in your {commitment.cooling_days}-day cooling period ({cooling_left} day(s) left). "
            f"Only evidence of {bar * policy.cooling_override_ratio:.1f} or a tripwire can break it."
        )

    if not blockers:
        return verdict(RECONSIDER, reasons + [
            "The case is strong, new, about what you value, and has lasted. "
            "This is a real reason to review the decision."
        ])

    reasons += blockers
    if evidence >= bar * policy.watch_ratio:
        return verdict(WATCH, reasons + [
            "Hold the decision, but pay attention: the evidence is building. "
            "Keep logging doubts honestly rather than acting on them."
        ])
    return verdict(HOLD, reasons + ["Hold the decision. Your past self had good reasons."])


# ---------------------------------------------------------------------------
# Actions that change a commitment
# ---------------------------------------------------------------------------
def commit(
    record: DecisionRecord,
    conviction: int = 7,
    anchor: str = "",
    tripwires: Sequence[str] = (),
    cooling_days: int = 30,
    now: Optional[dt.datetime] = None,
) -> Commitment:
    stamp = to_iso(now or utcnow())
    c = Commitment(
        decision_id=record.id,
        conviction=conviction,
        anchor=anchor.strip(),
        cooling_days=cooling_days,
        tripwires=[Tripwire(condition=t.strip()) for t in tripwires if t.strip()],
        locked_at=stamp,
    )
    c.history.append(Event("committed", f"Locked at conviction {c.conviction}/10.", stamp))
    return c


def log_doubt(commitment: Commitment, doubt: Doubt) -> Commitment:
    _require_active(commitment)
    commitment.doubts.append(doubt)
    commitment.history.append(Event("doubt", doubt.text, doubt.timestamp))
    return commitment


def trigger_tripwire(
    commitment: Commitment, which: str, evidence: str = "", now: Optional[dt.datetime] = None
) -> Tripwire:
    """Mark a tripwire as triggered. ``which`` is its id, id prefix, or 1-based number."""
    _require_active(commitment)
    wire = find_tripwire(commitment, which)
    stamp = to_iso(now or utcnow())
    wire.triggered, wire.triggered_at, wire.evidence, wire.spent = True, stamp, evidence.strip(), False
    commitment.history.append(Event("tripwire", f"{wire.condition} :: {wire.evidence}", stamp))
    return wire


def find_tripwire(commitment: Commitment, which: str) -> Tripwire:
    which = str(which).strip()
    if which.isdigit() and 1 <= int(which) <= len(commitment.tripwires):
        return commitment.tripwires[int(which) - 1]
    matches = [t for t in commitment.tripwires if t.id.startswith(which)]
    if len(matches) != 1:
        raise KeyError(f"No single tripwire matches '{which}'.")
    return matches[0]


def reaffirm(commitment: Commitment, note: str = "", now: Optional[dt.datetime] = None) -> Commitment:
    """Choose the decision again. Answered doubts stop counting and the lock gets harder."""
    _require_active(commitment)
    stamp = to_iso(now or utcnow())
    for wire in commitment.tripwires:
        if wire.triggered:
            wire.spent = True
    commitment.reaffirmations += 1
    commitment.history.append(Event(
        "reaffirmed",
        (note.strip() or "Chose this again.")
        + f" Reaffirmed {commitment.reaffirmations}x; the bar to change it is now higher.",
        stamp,
    ))
    return commitment


def reverse(
    commitment: Commitment,
    record: DecisionRecord,
    reason: str,
    now: Optional[dt.datetime] = None,
    policy: Policy = DEFAULT_POLICY,
) -> Commitment:
    """Change the decision. Only possible when the engine says RECONSIDER."""
    _require_active(commitment)
    now = now or utcnow()
    result = evaluate(commitment, record, now, policy)
    if not result.can_reverse:
        raise CommitmentLocked(result)
    if len(reason.strip()) < MIN_REVERSAL_REASON:
        raise ValueError(
            f"Write down why you are changing course (at least {MIN_REVERSAL_REASON} characters). "
            "Your future self deserves the same honesty you are asking of your past self."
        )
    commitment.status = STATUS_REVERSED
    commitment.history.append(Event("reversed", reason.strip(), to_iso(now)))
    return commitment


def reminder(commitment: Commitment, record: DecisionRecord, now: Optional[dt.datetime] = None) -> str:
    """What your past self wants you to read before you act on a doubt."""
    now = now or utcnow()
    days = max(0, (now - parse_iso(commitment.locked_at)).days)
    lines = [f"You chose: {record.chosen or record.choice}", f"You have held this for {days} day(s)."]
    if record.values_ranked:
        lines.append("What mattered most, in order: " + ", ".join(record.values_ranked))
    if record.reasoning:
        lines.append(f"Why you chose it: {record.reasoning}")
    lines.append(f"How sure you were: {commitment.conviction}/10")
    if commitment.anchor:
        lines.append(f"Your note to yourself: \"{commitment.anchor}\"")
    active = [t.condition for t in commitment.tripwires if not t.triggered]
    if active:
        lines.append("You agreed to reconsider only if: " + "; ".join(active))
    return "\n".join(lines)


def _require_active(commitment: Commitment) -> None:
    if commitment.status != STATUS_COMMITTED:
        raise ValueError("This decision has already been reversed; capture a new one instead.")
