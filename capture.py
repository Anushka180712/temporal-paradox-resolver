"""Decision‑capture prompt flow for the Temporal Paradox Resolver."""

from typing import List, Dict, Any
import json
import uuid
import datetime as dt

from .models import DecisionRecord
from .store import DecisionStore


def _prompt(prompt_text: str, default: str = "") -> str:
    user_input = input(f"{prompt_text} [{default}]: ").strip()
    return user_input if user_input else default


def _prompt_int(prompt_text: str, min_val: int = 1, max_val: int = 10) -> int:
    while True:
        val = input(f"{prompt_text} [{min_val}-{max_val}]: ").strip()
        try:
            iv = int(val)
            if min_val <= iv <= max_val:
                return iv
            print(f"Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("Invalid integer. Try again.")


def capture_decision() -> DecisionRecord:
    """Interactively capture a decision record from the user."""

    print("\n=== Capture a New Decision ===")

    choice = _prompt("Describe the decision you're making (your exact words)")
    if not choice:
        choice = " (unspecified)"

    print("\nValues you're ranking (type one per line, press Enter twice when done):")
    values: List[str] = []
    while True:
        line = input("> ").strip()
        if line == "":
            break
        values.append(line)

    print("\nAlternatives considered (for each: name, then pros, then cons, each section terminated by an empty line):")
    alternatives: List[Dict[str, Any]] = []
    while True:
        name = input("  Alternative name (or leave blank to finish): ").strip()
        if not name:
            break
        pros_lines: List[str] = []
        print("    Pros (one per line, empty line when done):")
        while True:
            pl = input("      ").strip()
            if pl == "":
                break
            pros_lines.append(pl)
        cons_lines: List[str] = []
        print("    Cons (one per line, empty line when done):")
        while True:
            cl = input("      ").strip()
            if cl == "":
                break
            cons_lines.append(cl)
        alternatives.append({
            "name": name,
            "pros": pros_lines,
            "cons": cons_lines,
        })

    print("\nContext (press Enter after each, or type 'skip' to move on):")
    time_of_day = input("  Time of day (morning/afternoon/evening): ").strip() or "unspecified"
    energy_level = _prompt_int("  Energy level (1-10)", 1, 10)
    stressors_input = input("  Stressors (comma-separated, or skip): ").strip()
    stressors = [s.strip() for s in stressors_input.split(",") if s.strip()] if stressors_input else []

    notes = _prompt("  Any additional notes (free‑form)")

    tags_input = input("  Tags (comma-separated, e.g., career,2024,major): ").strip()
    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []

    record = DecisionRecord(
        id=str(uuid.uuid4()),
        timestamp=dt.datetime.utcnow().isoformat() + "Z",
        choice=choice,
        values_ranked=values,
        alternatives=alternatives,
        context={
            "time_of_day": time_of_day,
            "energy_level": energy_level,
            "stressors": stressors,
        },
        notes=notes,
        tags=tags,
    )

    # Persist to SQLite
    store = DecisionStore(db_path="my_decisions.db")
    store.add(record)
    store.close()

    print(f"\n✅ Decision captured and saved (ID: {record.id[:8]}…)")
    return record


def main():
    record = capture_decision()
    # Quick demo: print the stored dict
    print("\n--- Captured Record Summary ---")
    print(f"Choice: {record.choice}")
    print(f"Values ranked: {record.values_ranked}")
    print(f"Alternatives count: {len(record.alternatives)}")
    print(f"Tags: {record.tags}")
    print(f"Timestamp: {record.timestamp}")


if __name__ == "__main__":
    main()