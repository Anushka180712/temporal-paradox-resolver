"""Natural‑language query interface for the Temporal Paradox Resolver.

This module helps parse a user's natural‑language question (e.g.
"If I had taken Job B instead of Job A, where would I be today?")
and extracts the relevant decision record and alternate choice name,
then delegates to the simulation engine.

Typical flow:
1. User types a question.
2. `parse_question` extracts the decision record ID (if referenced) and
   the alternate choice name.
3. The caller fetches the record from storage and calls
   `simulate_alternative` from `simulate.py`.
"""

import re
from typing import Tuple, Optional

from temporal_paradox_resolver.simulate import simulate_alternative
from temporal_paradox_resolver.store import DecisionStore
from temporal_paradox_resolver.models import DecisionRecord


# ---------------------------------------------------------------------------
# Very light parser for "what‑if" questions.
# Looks for patterns like:
#   "If I had chosen X instead"
#   "What if I had picked X"
#   "Compare X and Y"
# ---------------------------------------------------------------------------

# Keywords that signal a what‑if question
WHAT_IF_PATTERNS = [
    r"if.?i.?had.?chosen\s+(.+?)\s+instead",
    r"if.?i.?had.?picked.?(.+?)\s+instead",
    r"what.?if.?i.?had.?chosen\s+(.+?)(?:\?|$)",
    r"compare\s+(.+?)\s+to\s+(.+?)(?:\?|$)",
]

# Pattern to capture a decision ID like uuid or "record‑123"
ID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def extract_alternate_name(question: str) -> Optional[str]:
    """Try to extract the alternate choice name from a natural‑language question.

    Returns the cleaned alternate name string, or None if not found.
    """
    for pattern in WHAT_IF_PATTERNS:
        m = re.search(pattern, question, flags=re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Remove trailing garbage like "instead" or "?"
            name = name.replace("instead", "").strip("?.!,")
            if name:
                return name
    return None


def extract_record_id(question: str) -> Optional[str]:
    """Look for a UUID in the question; if found, use that record."""
    m = re.search(ID_PATTERN, question)
    if m:
        return m.group(0)
    return None


def parse_question(question: str, store: DecisionStore) -> Tuple[Optional[DecisionRecord], Optional[str]]:
    """Parse a user question and return (DecisionRecord, alternate_name).

    The function:
    - Checks for an explicit UUID → fetches that record.
    - Otherwise lists recent records and tries to infer which one is meant
      (simple heuristic: most recent record if only one exists).
    - Extracts the alternate choice name.

    Returns:
        (record, alternate_name) tuple. Either may be None if inference fails.
    """
    # 1️⃣ Check for explicit UUID
    uuid = extract_record_id(question)
    if uuid:
        record = store.get(uuid)
        if not record:
            print(f"❌ No decision record found with UUID {uuid}")
            return None, None
        # Now extract alternate name
        alt_name = extract_alternate_name(question)
        return record, alt_name

    # 2️⃣ No UUID → try to use the most recent record if only one exists
    records = store.list_all()
    if not records:
        print("❌ No decision records found. Capture a decision first.")
        return None, None

    if len(records) == 1:
        record = records[0]
        alt_name = extract_alternate_name(question)
        return record, alt_name

    # 3️⃣ Multiple records: ask user to specify (for now, just return the most recent)
    print(
        "⚠️  Multiple decision records found. Please specify which one by UUID or number.\n"
    )
    for i, r in enumerate(records, 1):
        print(f"  {i}. {r.choice[:60]}… ({r.timestamp})")
    return None, None


# ---------------------------------------------------------------------------
# High‑level helper: ask the LLM a what‑if question given a question string.
# ---------------------------------------------------------------------------
def answer_what_if(question: str, store: DecisionStore) -> Optional[str]:
    """Answer a natural‑language "what‑if" question.

    Args:
        question: User's question string, e.g.
                  "If I had chosen Job B instead of Job A, where would I be?"
        store: DecisionStore instance connected to the DB.

    Returns:
        The simulation narrative string, or None on failure.
    """
    record, alt_name = parse_question(question, store)
    if not record or not alt_name:
        return None

    # If the alternate name seems very generic, try to use the alternative's
    # stored name if available; otherwise fall back to the extracted string.
    if alt_name.lower() in ("the other option", "the alternative", "that one"):
        # Pick the first alternative that isn't the chosen one.
        # We'll assume the "choice" field mentions the picked option; for now,
        # just use the first stored alternative.
        if record.alternatives:
            alt_name = record.alternatives[0]["name"]
        else:
            return None

    narrative = simulate_alternative(record, alt_name)
    return narrative