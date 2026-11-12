"""LLM Simulation Engine using Google Gemini.

This module takes a stored DecisionRecord and an alternate choice name,
builds a prompt, and returns a "what-if" narrative from the Gemini LLM.
It also supports generating pros‑cons, a personal conclusion, and a goal‑plan.

Prerequisites:
    pip install google-genai
    export GEMINI_API_KEY='YOUR_KEY_HERE'
"""

import json
import os
from typing import Optional, Dict, List

from google import genai
from temporal_paradox_resolver.models import DecisionRecord
from temporal_paradox_resolver.store import DecisionStore

# ---------------------------------------------------------------------------
# Setup: read API key from environment
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable not set. "
        "Add it to your shell or .env file, e.g.: "
        "export GEMINI_API_KEY='YOUR_KEY_HERE'"
)
client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Prompt templates – keep in sync with the architecture doc
# ---------------------------------------------------------------------------
SIMULATION_PROMPT = """You are a personal decision‑simulation engine.

CHOICE: {choice}
VALUES RANKED: {values_ranked}
CONSIDERED ALTERNATIVES: {alternatives}

The user is now asking: "If I had chosen {alternate_name} instead, what would my life look like today?"

Using only the information above (no external data unless provided), craft a concise (150‑word) "what‑if" narrative that includes:
- Likely current location / job / relationship status
- The primary gain they would have experienced
- The primary trade‑off or loss
- How this aligns with their ranked values

Keep it grounded in the supplied data. Do not hallucinate details beyond what is reasonably inferable.
"""

PROS_CONS_PROMPT = """Given the following decision context, list 3 plausible pros and 3 cons for the alternative the user did NOT choose.

VALUES RANKED: {values_ranked}
CONTEXT: {context}
CHOICE: {choice}
ALTERNATIVES: {alternatives}
THE USER CHOSE: {chosen_name}

Provide the output in this exact format (no extra heading or prose outside the blocks):

Pros:
- <pro 1>
- <pro 2>
- <pro 3>

Cons:
- <con 1>
- <con 2>
- <con 3>

Keep each pro/concise and grounded in the supplied data. Do not invent details beyond what is reasonably inferable.
"""

CONCLUSION_PROMPT = """Based on the values ranked {values_ranked} and the gains/losses listed in the following "what‑if" narrative, write a brief personal recommendation (1‑2 sentences) that the user can consider.

NARRATIVE:
{narrative}

Keep the recommendation uplifting but neutral. Do not add any extra text outside the 1‑2 sentence recommendation.
"""

GOAL_PLAN_PROMPT = """Translate the top‑ranked value (“{top_value}”) into a {horizon_months}-month action plan with {num_milestones} concrete monthly milestones.

If top_value is not provided, use the first value in the values_ranked list.

The user’s decision context: {choice}
Values ranked: {values_ranked}

Format the output as a simple list:

Month 1: <concrete milestone>
Month 2: <concrete milestone>
Month 3: <concrete milestone>
…

Keep each milestone specific, measurable, and realistic given the decision context. Do not exceed {num_milestones} months.
"""

MOTIVATIONAL_TAGLINE = """Prepend a short motivational tagline (max 30 words) to the following "what‑if" narrative. The tagline should be uplifting but neutral, e.g., "💡 Remember: every choice teaches you more about what you truly value."

NARRATIVE:
{narrative}

Return only the tagline on its own line, then a blank line, then the narrative. Do not add any commentary.
"""


# ---------------------------------------------------------------------------
# Core simulation functions
# ---------------------------------------------------------------------------
def simulate_alternative(record: DecisionRecord, alternate_name: str) -> Optional[str]:
    """Ask Gemini to generate a what‑if narrative for the given decision.

    Args:
        record: The original DecisionRecord captured at decision time.
        alternate_name: The name of the alternative the user is curious about
                        (e.g. "Job B (remote, lower salary)").

    Returns:
        The LLM-generated narrative string, or None if something goes wrong.
    """
    try:
        prompt = SIMULATION_PROMPT.format(
            choice=record.choice,
            values_ranked=json.dumps(record.values_ranked, ensure_ascii=False),
            alternatives=json.dumps(record.alternatives, ensure_ascii=False),
            alternate_name=alternate_name,
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash", contents=prompt
        )

        # Gemini returns a response object with a .text attribute
        narrative = getattr(response, "text", None)
        if narrative is None:
            # Fallback: convert to string
            narrative = str(response)

        return narrative.strip() if narrative else None

    except Exception as e:
        print(f"⚠️  Simulation error: {e}")
        return None


def generate_pros_cons(record: DecisionRecord, alternate_name: str) -> Optional[str]:
    """Ask Gemini to generate 3 pros and 3 cons for the alternative not chosen.

    Args:
        record: The original DecisionRecord.
        alternate_name: The name of the alternative the user is asking about.

    Returns:
        A formatted string with Pros: and Cons: blocks, or None on error.
    """
    try:
        # Determine which alternative is the "chosen" one vs the "other"
        chosen = None
        other = None
        for alt in record.alternatives:
            if alt["name"].lower() == alternate_name.lower():
                chosen = alt
            else:
                other = alt

        if not chosen or not other:
            print("⚠️  Could not match alternate_name to stored alternatives.")
            return None

        prompt = PROS_CONS_PROMPT.format(
            values_ranked=json.dumps(record.values_ranked, ensure_ascii=False),
            context=json.dumps(record.context, ensure_ascii=False),
            choice=record.choice,
            alternatives=json.dumps(record.alternatives, ensure_ascii=False),
            chosen_name=chosen["name"],
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash", contents=prompt
        )

        # The model is expected to return the exact format; strip safely.
        text = getattr(response, "text", None)
        if text is None:
            text = str(response)

        return text.strip()

    except Exception as e:
        print(f"⚠️  Pros‑Cons generation error: {e}")
        return None


def generate_conclusion(record: DecisionRecord, narrative: str) -> Optional[str]:
    """Ask Gemini for a brief personal recommendation based on values and narrative.

    Args:
        record: The original DecisionRecord.
        narrative: The "what‑if" narrative generated by simulate_alternative.

    Returns:
        A 1‑2 sentence recommendation, or None on error.
    """
    try:
        prompt = CONCLUSION_PROMPT.format(
            values_ranked=json.dumps(record.values_ranked, ensure_ascii=False),
            narrative=narrative,
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash", contents=prompt
        )

        text = getattr(response, "text", None)
        if text is None:
            text = str(response)

        # Return just the recommendation sentences (may contain extra whitespace).
        return text.strip()

    except Exception as e:
        print(f"⚠️  Conclusion generation error: {e}")
        return None


def generate_goal_plan(
    record: DecisionRecord,
    top_value: str = "",
    horizon_months: int = 6,
    num_milestones: int = 3,
) -> Optional[str]:
    """Ask Gemini to produce a month‑by‑month action plan for the top‑ranked value.

    Args:
        record: The original DecisionRecord.
        top_value: The value to base the plan on. If empty, the first in values_ranked is used.
        horizon_months: Number of months for the plan (default 6).
        num_milestones: How many monthly milestones to list (default 3).

    Returns:
        A string with "Month 1:", "Month 2:", etc., or None on error.
    """
    try:
        values = record.values_ranked
        if not top_value and values:
            top_value = values[0]
        if not top_value:
            print("⚠️  No top_value provided and no values ranked.")
            return None

        prompt = GOAL_PLAN_PROMPT.format(
            top_value=top_value,
            horizon_months=horizon_months,
            num_milestones=num_milestones,
            choice=record.choice,
            values_ranked=json.dumps(values, ensure_ascii=False),
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash", contents=prompt
        )

        text = getattr(response, "text", None)
        if text is None:
            text = str(response)

        return text.strip()

    except Exception as e:
        print(f"⚠️  Goal‑plan generation error: {e}")
        return None


def add_motivational_tagline(narrative: str) -> str:
    """Prepend a short motivational tagline to a narrative.

    Args:
        narrative: The "what‑if" narrative string.

    Returns:
        A string beginning with the tagline on its own line, a blank line, then the narrative.
    """
    tagline = "💡 Remember: every choice teaches you more about what you truly value."
    # Ensure tagline is not longer than 30 words (~30 words safe)
    tagline = " ".join(tagline.split()[:30])
    return f"{tagline}\n\n{narrative}"