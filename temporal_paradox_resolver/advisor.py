"""An honest, unbiased second opinion while you are deciding.

The tone is: "It's okay to choose this. Before you lock it in, you should know
this." The advisor never tells you what to pick. It checks the draft decision
for the common traps (a one-sided comparison, no downsides named, choosing
from fear or exhaustion, other people's voices, sunk costs, false urgency,
over- or under-confidence, no exit conditions) and points out the strongest
case for the option you are leaving behind, so the choice you lock in is one
you made with open eyes.

The checks are deterministic and work offline. With a Gemini key you can also
ask for an outside view written by the model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Sequence

from . import llm
from .models import DecisionRecord


@dataclass
class Point:
    icon: str
    title: str
    detail: str


@dataclass
class Advice:
    opening: str
    points: List[Point] = field(default_factory=list)
    other_side: List[str] = field(default_factory=list)
    ready: bool = True

    @property
    def summary(self) -> str:
        if self.ready:
            return "✅ This looks like a clear-eyed decision. You're ready to commit."
        return "🧭 Nothing here says don't choose it. Just look at the points above before you lock it in."


def _has(text: str, words: Sequence[str]) -> List[str]:
    lowered = text.lower()
    return [w for w in words if re.search(rf"\b{re.escape(w)}", lowered)]


OTHERS = ["parents", "mom", "dad", "family wants", "everyone", "people say", "friends think", "they want",
          "expected", "supposed to", "society", "relatives", "log kya"]
SUNK = ["already spent", "already invested", "wasted", "sunk", "years into", "come this far", "can't waste"]
FEAR = ["scared", "afraid", "fear", "safe option", "play it safe", "risky", "anxious", "worried"]
URGENT = ["now or never", "hurry", "last chance", "deadline", "right now", "immediately", "quickly"]


def review(
    record: DecisionRecord,
    conviction: int = 7,
    tripwires: Sequence[str] = (),
    energy_level: int = 6,
    stress_level: int = 4,
) -> Advice:
    chosen_name = record.chosen.strip() or "this"
    chosen = next((a for a in record.alternatives
                   if str(a.get("name", "")).strip().lower() == chosen_name.lower()), None) or {}
    others = record.unchosen()
    advice = Advice(opening=f"It's okay to choose {chosen_name}. Before you lock it in, here's what you should know:")
    warn = lambda icon, title, detail: advice.points.append(Point(icon, title, detail))  # noqa: E731

    # 1. Is the comparison fair?
    if not others:
        warn("⚖️", "Only one option", "A decision needs at least one real alternative, even if it's 'stay as I am'.")
    for alt in others:
        alt_pros, my_pros = len(alt.get("pros", [])), len(chosen.get("pros", []))
        if not alt.get("pros"):
            warn("⚖️", f"No good points written for {alt['name']}",
                 f"If you can't name anything good about {alt['name']}, you may have decided before you compared. "
                 "Give it a fair hearing: what would someone who chose it say?")
        elif alt_pros > my_pros:
            warn("⚖️", f"{alt['name']} has more good points on paper",
                 f"You listed {alt_pros} for {alt['name']} and {my_pros} for {chosen_name}. "
                 "That's fine if your reasons weigh more, but be sure they do.")
    if not chosen.get("cons"):
        warn("🙈", f"No downsides listed for {chosen_name}",
             "Every option has costs. Naming them now means they won't surprise you, or shake you, later.")

    # 2. Does it serve what you said matters?
    if record.values_ranked:
        top = record.values_ranked[0]
        text = " ".join([record.reasoning, *chosen.get("pros", [])])
        if not _has(text, [w for w in re.findall(r"[a-zA-Z]{4,}", top.lower())] or [top.lower()]):
            warn("🎯", f"Does it serve '{top}'?",
                 f"You said '{top}' matters most, but your reasons for {chosen_name} don't mention it. "
                 "Check that this choice actually moves your #1 value forward.")
    else:
        warn("🎯", "No values ranked", "Without knowing what matters most, it's hard to judge any option. Rank 2-3 values.")
    if not record.reasoning.strip():
        warn("✍️", "No reason written", "Write one or two sentences on why. Your future self will need them on hard days.")

    # 3. Where is the decision coming from?
    words = " ".join([record.choice, record.reasoning])
    if _has(words, OTHERS):
        warn("👥", "Whose decision is this?",
             "Your reasons mention what other people want or expect. Their view matters, but you're the one who "
             "lives with this. Make sure it's yours.")
    if _has(words, SUNK):
        warn("🕳️", "Sunk cost",
             "Time or money already spent is gone either way. Decide on what each option gives you from here on.")
    if _has(words, FEAR):
        warn("😨", "Is fear choosing?",
             "Choosing the safer path can be wise. Just check you're moving toward something, not only away from a fear.")
    if _has(words, URGENT):
        warn("⏰", "Is the hurry real?",
             "Pressure to decide fast is a classic trap. If you can, ask for a day. If the deadline is real, that's okay too.")
    if energy_level <= 3 or stress_level >= 8:
        warn("😴", "You're exhausted or overwhelmed right now",
             "Big decisions made in this state are harder to trust later. If you can, sleep on it and come back.")

    # 4. Confidence and exits
    if conviction >= 10:
        warn("🔭", "100% sure?", "Total certainty can hide blind spots. What would have to be true for this to go wrong?")
    elif conviction <= 4:
        warn("🔍", "You're not very sure",
             "That's honest. Consider what one piece of information would raise your confidence, and get it first.")
    if not [t for t in tripwires if t.strip()]:
        warn("🚩", "No 'I'll reconsider if...' conditions",
             "Write at least one. It lets you stay firm through ordinary doubts, because you'll know exactly what would count.")

    # 5. The strongest case for the road not taken
    for alt in others:
        if alt.get("pros"):
            advice.other_side.append(f"Choosing {chosen_name} means giving up what {alt['name']} offered: "
                                     + ", ".join(alt["pros"]) + ".")
    serious = {"👥", "😴", "🙈", "🎯", "⚖️"}
    advice.ready = not any(p.icon in serious for p in advice.points)
    return advice


def outside_view(record: DecisionRecord) -> str:
    """An unbiased outside view from the model, or the offline review as text."""
    answer = llm.generate(
        "You are a calm, unbiased decision advisor. You do not pick for the user and you do not flatter them. "
        "In under 180 words: start with 'It's okay to choose <their choice>.' Then name the 2-3 most important "
        "things they should know before committing: likely blind spots, biases visible in their reasoning, the "
        "strongest honest case for the option they are not choosing, and one question to ask themselves. "
        "End with one sentence on what would make this a decision they can stand behind.\n\n"
        f"DECISION: {record.choice}\nCHOSEN: {record.chosen}\nWHY: {record.reasoning}\n"
        f"VALUES RANKED: {record.values_ranked}\nOPTIONS: {record.alternatives}"
    )
    if answer:
        return answer
    advice = review(record)
    parts = [advice.opening] + [f"{p.icon} {p.title}: {p.detail}" for p in advice.points] + advice.other_side
    return "\n\n".join(parts + [advice.summary])
