"""Optional language-model features (Google Gemini).

Nothing here is required. Without ``GEMINI_API_KEY`` (or without the
``google-genai`` package) every function returns a plain offline answer built
from the stored record, so the app always works. The commitment engine never
calls a model: verdicts stay deterministic.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from .models import DecisionRecord

DEFAULT_MODEL = "gemini-3.5-flash"

_client = None


def available() -> bool:
    if not os.getenv("GEMINI_API_KEY"):
        return False
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return False
    return True


def _generate(prompt: str) -> Optional[str]:
    global _client
    if not available():
        return None
    try:
        if _client is None:
            from google import genai

            _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = _client.models.generate_content(
            model=os.getenv("TPR_GEMINI_MODEL", DEFAULT_MODEL), contents=prompt
        )
        text = getattr(response, "text", None) or ""
        return text.strip() or None
    except Exception as exc:  # network, quota, bad key: fall back quietly
        print(f"[llm] falling back to offline answer: {exc}")
        return None


def _facts(record: DecisionRecord) -> str:
    return (
        f"DECISION: {record.choice}\n"
        f"CHOSEN: {record.chosen or '(not stated)'}\n"
        f"WHY: {record.reasoning or '(not stated)'}\n"
        f"VALUES RANKED: {json.dumps(record.values_ranked, ensure_ascii=False)}\n"
        f"ALTERNATIVES: {json.dumps(record.alternatives, ensure_ascii=False)}\n"
        f"CONTEXT: {json.dumps(record.context, ensure_ascii=False)}"
    )


def _find_alternative(record: DecisionRecord, name: str) -> dict:
    wanted = name.strip().lower()
    for alt in record.alternatives:
        if str(alt.get("name", "")).strip().lower() == wanted:
            return alt
    return {"name": name, "pros": [], "cons": []}


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
def what_if(record: DecisionRecord, alternate: str) -> str:
    """A grounded narrative of the timeline where you chose ``alternate``."""
    prompt = (
        "You are a personal decision-simulation engine. Use only the facts below.\n\n"
        f"{_facts(record)}\n\n"
        f'The user asks: "If I had chosen {alternate} instead, what would my life look like now?"\n'
        "Write about 150 words covering the likely situation today, the main gain, the main loss, "
        "and how it fits their ranked values. End with one sentence on what the chosen path gave "
        "them that this one would not. Do not invent facts that cannot be inferred."
    )
    answer = _generate(prompt)
    if answer:
        return answer
    alt = _find_alternative(record, alternate)
    gains = ", ".join(alt.get("pros", [])) or "nothing you wrote down"
    losses = ", ".join(alt.get("cons", [])) or "nothing you wrote down"
    top = record.values_ranked[0] if record.values_ranked else "what mattered most"
    return (
        f"In the timeline where you chose {alt['name']}, you would have gained: {gains}. "
        f"You would also have lived with: {losses}. "
        f"When you decided, your top value was {top}, and you judged "
        f"{record.chosen or 'your choice'} to serve it better. "
        "(Offline summary from your own notes; set GEMINI_API_KEY for a richer narrative.)"
    )


def defend_past_self(record: DecisionRecord, doubt: str) -> str:
    """Make the strongest honest case for the original decision against a doubt."""
    prompt = (
        "The user made the decision below and is now doubting it. Speak as their past self, "
        "who decided calmly. In under 120 words: (1) say whether the doubt is genuinely new "
        "information or a trade-off they already weighed, (2) make the strongest honest case "
        "for the original choice using their own values and reasons, (3) if the doubt really is "
        "serious and new, say so plainly instead of dismissing it.\n\n"
        f"{_facts(record)}\n\nDOUBT: {doubt}"
    )
    answer = _generate(prompt)
    if answer:
        return answer
    lines = [f"Before acting on \"{doubt}\", remember:"]
    if record.reasoning:
        lines.append(f"- You chose {record.chosen or 'this'} because: {record.reasoning}")
    if record.values_ranked:
        lines.append(f"- Your values, in order: {', '.join(record.values_ranked)}")
    for alt in record.unchosen():
        if alt.get("cons"):
            lines.append(f"- {alt['name']} came with: {', '.join(alt['cons'])}")
    lines.append("- Ask: did I know this when I decided? If yes, it is not a reason to switch.")
    return "\n".join(lines)


def goal_plan(record: DecisionRecord, months: int = 6, milestones: int = 3) -> str:
    """Turn the top-ranked value into concrete milestones that make the decision pay off."""
    top = record.values_ranked[0] if record.values_ranked else "the reason you chose this"
    prompt = (
        f"Turn the value '{top}' into a {months}-month plan with exactly {milestones} concrete, "
        "measurable milestones that help the user get the most out of the decision they made. "
        "Format each line as 'Month N: <milestone>'.\n\n" + _facts(record)
    )
    answer = _generate(prompt)
    if answer:
        return answer
    step = max(1, months // max(1, milestones))
    return "\n".join(
        f"Month {i * step}: one measurable step that moves '{top}' forward in your chosen path"
        for i in range(1, milestones + 1)
    )
