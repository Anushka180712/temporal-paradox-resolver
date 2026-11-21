"""Keep going: motivation built from your own reasons, plus daily check-ins.

Notes are passive. This module turns what you wrote when you decided into
something that comes back to you: a fresh message every day, milestones as you
hold the line, and a streak of check-ins with the small wins that prove the
decision is paying off.

Everything works offline. With a Gemini key, ``daily_message`` is rewritten by
the model in a warmer voice, still using only your own words and facts.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

from . import llm
from .models import CheckIn, Commitment, DecisionRecord, Event, parse_iso, to_iso, utcnow

MILESTONES = [1, 3, 7, 14, 21, 30, 60, 90, 100, 180, 365, 500, 730, 1000]


@dataclass
class Motivation:
    title: str
    message: str
    why: List[str]          # the reasons, in your own words
    days_held: int
    streak: int
    milestone: Optional[int]
    next_milestone: Optional[int]


def days_held(commitment: Commitment, today: dt.date) -> int:
    return max(0, (today - parse_iso(commitment.locked_at).date()).days)


def streak(commitment: Commitment, today: dt.date) -> int:
    """Consecutive days with a check-in, ending today (or yesterday, so it survives until tonight)."""
    days = {c.day for c in commitment.checkins}
    cursor = today if today.isoformat() in days else today - dt.timedelta(days=1)
    count = 0
    while cursor.isoformat() in days:
        count += 1
        cursor -= dt.timedelta(days=1)
    return count


def checked_in_today(commitment: Commitment, today: dt.date) -> bool:
    return any(c.day == today.isoformat() for c in commitment.checkins)


def check_in(commitment: Commitment, mood: int, win: str = "", today: Optional[dt.date] = None) -> CheckIn:
    """Record today's check-in (replacing an earlier one from the same day)."""
    today = today or utcnow().date()
    entry = CheckIn(day=today.isoformat(), mood=mood, win=win.strip())
    commitment.checkins = [c for c in commitment.checkins if c.day != entry.day] + [entry]
    commitment.history.append(Event("checkin", f"mood {entry.mood}/5" + (f", win: {entry.win}" if entry.win else ""),
                                    to_iso(dt.datetime.combine(today, dt.time(12), dt.timezone.utc))))
    return entry


def reasons(record: DecisionRecord, commitment: Commitment) -> List[str]:
    """Why you should keep going, gathered from what you wrote."""
    out: List[str] = []
    if record.reasoning:
        out.append(record.reasoning)
    chosen = next((a for a in record.alternatives
                   if str(a.get("name", "")).strip().lower() == record.chosen.strip().lower()), None)
    for pro in (chosen or {}).get("pros", []):
        out.append(f"{record.chosen} gives you: {pro}")
    for alt in record.unchosen():
        for con in alt.get("cons", []):
            out.append(f"You chose not to live with: {con} ({alt['name']})")
    if record.values_ranked:
        out.append(f"This is about what matters most to you: {record.values_ranked[0]}")
    if commitment.anchor:
        out.append(commitment.anchor)
    return out


def _templates(record: DecisionRecord, commitment: Commitment, held: int, why: List[str]) -> List[str]:
    choice = record.chosen or "this path"
    top = record.values_ranked[0] if record.values_ranked else "what matters to you"
    wins = [c.win for c in commitment.checkins if c.win]
    lines = [
        f"Day {held + 1} of {choice}. Every day you stay, you collect the benefits that only come to people who don't quit halfway.",
        f"You chose {choice} for {top}. That reason hasn't expired just because today is hard.",
        "Doubt is not a signal to switch. It's the normal price of every real choice. Pay it, and keep going.",
        f"The other path would have had hard days too. You just wouldn't be able to see them from here.",
        f"Small, steady steps toward {top} beat a perfect plan you keep restarting.",
        f"You decided with a clear head and {commitment.conviction}/10 certainty. Trust the person who did that work.",
    ]
    if why:
        lines += [f"Remember why: \"{w}\"" for w in why[:4]]
    if wins:
        lines.append(f"You've already got proof it's working. You wrote: \"{wins[-1]}\"")
    return lines


def daily_message(
    record: DecisionRecord,
    commitment: Commitment,
    today: Optional[dt.date] = None,
    use_ai: bool = True,
) -> Motivation:
    """Today's motivation. Changes every day; the same day always gives the same message offline."""
    today = today or utcnow().date()
    held = days_held(commitment, today)
    why = reasons(record, commitment)
    templates = _templates(record, commitment, held, why)
    pick = templates[(today.toordinal() + sum(map(ord, record.id))) % len(templates)]

    upcoming = min([m for m in MILESTONES if m > held], default=None)
    milestone = held if held in MILESTONES else None
    title = (f"🎉 {held} days of {record.chosen or 'your decision'}!" if milestone
             else f"Day {held + 1}: keep going" if held else "Day one. You've decided. Now begin.")

    message = pick
    if use_ai and llm.available():
        wins = "; ".join(c.win for c in commitment.checkins[-5:] if c.win) or "none yet"
        ai = llm.generate(
            "Write a short, warm, specific motivational message (2-3 sentences, no hashtags, no clichés) "
            "for someone sticking with a decision. Use only their own reasons below and speak directly to them. "
            "Be encouraging but honest; don't promise outcomes.\n\n"
            f"DECISION: {record.choice}\nCHOSEN: {record.chosen}\nDAYS HELD: {held}\n"
            f"THEIR REASONS: {why}\nRECENT WINS: {wins}"
        )
        if ai:
            message = ai
    return Motivation(title, message, why, held, streak(commitment, today), milestone, upcoming)
