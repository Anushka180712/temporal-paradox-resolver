"""Command-line interface: ``tpr <command>`` (or ``python -m temporal_paradox_resolver``)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional, Sequence

from . import commitment as engine
from . import llm
from .models import Commitment, DecisionRecord, Doubt
from .store import DEFAULT_DB, DecisionStore

ICONS = {engine.HOLD: "HOLD", engine.WATCH: "WATCH", engine.RECONSIDER: "RECONSIDER"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _split(text: Optional[str], sep: str = ",") -> List[str]:
    return [part.strip() for part in (text or "").split(sep) if part.strip()]


def parse_alternative(spec: str) -> dict:
    """``"Name | pro; pro | con; con"`` -> {"name", "pros", "cons"}."""
    parts = [p.strip() for p in spec.split("|")]
    return {
        "name": parts[0],
        "pros": _split(parts[1] if len(parts) > 1 else "", ";"),
        "cons": _split(parts[2] if len(parts) > 2 else "", ";"),
    }


def _ask(prompt: str, default: str = "") -> str:
    shown = f" [{default}]" if default else ""
    answer = input(f"{prompt}{shown}: ").strip()
    return answer or default


def _ask_lines(prompt: str) -> List[str]:
    print(f"{prompt} (one per line, empty line to finish)")
    lines = []
    while True:
        line = input("  > ").strip()
        if not line:
            return lines
        lines.append(line)


def _ask_int(prompt: str, low: int, high: int, default: int) -> int:
    while True:
        raw = _ask(f"{prompt} ({low}-{high})", str(default))
        if raw.isdigit() and low <= int(raw) <= high:
            return int(raw)
        print(f"  Please enter a whole number from {low} to {high}.")


def _load(store: DecisionStore, decision_id: str) -> DecisionRecord:
    record = store.get(decision_id)
    if record is None:
        sys.exit(f"No single decision matches '{decision_id}'. Run `tpr list` to see ids.")
    return record


def _load_commitment(store: DecisionStore, record: DecisionRecord) -> Commitment:
    c = store.get_commitment(record.id)
    if c is None:
        sys.exit(f"Decision {record.id[:8]} is not committed yet. Run `tpr commit {record.id[:8]}`.")
    return c


def print_verdict(verdict: engine.Verdict, detailed: bool = False) -> None:
    filled = min(20, int(round(verdict.ratio * 20)))
    bar = "#" * filled + "." * (20 - filled)
    print(f"\nVerdict: {ICONS[verdict.decision]}   [{bar}] {verdict.evidence:.1f} / {verdict.threshold:.1f}")
    print(f"Held for {verdict.days_committed} day(s)"
          + (f", cooling period: {verdict.cooling_days_left} day(s) left" if verdict.cooling_days_left else ""))
    for reason in verdict.reasons:
        print(f"  - {reason}")
    if detailed and verdict.scored_doubts:
        print("\nHow each doubt was weighed:")
        for s in verdict.scored_doubts:
            print(f"  {s.score:5.2f}  {s.doubt.text}")
            print(f"         {'; '.join(s.factors)}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_capture(args, store: DecisionStore) -> None:
    interactive = not args.choice
    if interactive:
        print("\n=== Capture a decision ===")
        choice = _ask("What did you decide? (your own words)")
        alternatives = []
        print("Now list every option you weighed, including the one you picked.")
        while True:
            name = _ask("  Option name (empty to finish)")
            if not name:
                break
            alternatives.append({"name": name, "pros": _ask_lines("    Pros"), "cons": _ask_lines("    Cons")})
        chosen = _ask("Which option did you choose?", alternatives[0]["name"] if alternatives else "")
        values = _ask_lines("What matters most here? Rank it, most important first")
        reasoning = _ask("In one or two sentences, why this option?")
        context = {
            "energy_level": _ask_int("Energy right now", 1, 10, 6),
            "stressors": _split(_ask("Anything stressing you (comma-separated)")),
        }
        tags = _split(_ask("Tags (comma-separated)"))
    else:
        choice, chosen, reasoning = args.choice, args.chosen or "", args.reasoning or ""
        values = _split(args.values)
        alternatives = [parse_alternative(a) for a in args.alt or []]
        context, tags = {}, _split(args.tags)

    record = store.add(DecisionRecord(
        choice=choice, chosen=chosen, values_ranked=values, alternatives=alternatives,
        reasoning=reasoning, context=context, tags=tags,
    ))
    print(f"Saved decision {record.id[:8]}.")

    if args.no_commit:
        return
    if interactive:
        print("\n=== Lock it in ===")
        conviction = _ask_int("How sure are you", 1, 10, 7)
        anchor = _ask("A note to your future self, for the day you doubt this")
        tripwires = _ask_lines("Under what conditions WOULD you reconsider? Be specific")
        cooling = _ask_int("Cooling period in days (no reconsidering, bar tripwires)", 0, 365, 30)
    else:
        conviction, anchor, tripwires, cooling = args.conviction, args.anchor or "", args.tripwire or [], args.cooling_days
    c = store.save_commitment(engine.commit(record, conviction, anchor, tripwires, cooling))
    print(f"Committed at {c.conviction}/10 with {len(c.tripwires)} tripwire(s) "
          f"and a {c.cooling_days}-day cooling period.")


def cmd_commit(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    if store.get_commitment(record.id):
        sys.exit("This decision is already committed. Use `tpr reaffirm` to recommit.")
    c = engine.commit(record, args.conviction, args.anchor or "", args.tripwire or [], args.cooling_days)
    store.save_commitment(c)
    print(f"Committed {record.id[:8]} at {c.conviction}/10.")


def cmd_list(args, store: DecisionStore) -> None:
    records = store.list_all()
    if not records:
        print("No decisions yet. Start with `tpr capture`.")
        return
    for r in records:
        c = store.get_commitment(r.id)
        state = engine.evaluate(c, r).decision if c and c.status == "committed" else (c.status if c else "uncommitted")
        print(f"{r.id[:8]}  {r.timestamp[:10]}  {state:<11} {(r.chosen or r.choice)[:60]}")


def cmd_show(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    print(json.dumps(record.to_dict(), indent=2, ensure_ascii=False))
    c = store.get_commitment(record.id)
    if c:
        print("\n" + engine.reminder(c, record))
        print("\nHistory:")
        for e in c.history:
            print(f"  {e.timestamp[:16]}  {e.kind:<10} {e.detail}")
        if c.status == "committed":
            print_verdict(engine.evaluate(c, record))


def cmd_doubt(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    c = _load_commitment(store, record)
    print("\nBefore anything else, read what your past self wrote:\n")
    print(engine.reminder(c, record))
    engine.log_doubt(c, Doubt(
        text=args.text, is_new_information=args.new, affects_value=args.value or "",
        severity=args.severity, energy_level=args.energy, stress_level=args.stress,
    ))
    store.save_commitment(c)
    print("\nDoubt logged. It has been weighed, not acted on.")
    print_verdict(engine.evaluate(c, record))


def cmd_check(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    print_verdict(engine.evaluate(_load_commitment(store, record), record), detailed=True)


def cmd_trip(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    c = _load_commitment(store, record)
    wire = engine.trigger_tripwire(c, args.which, args.evidence or "")
    store.save_commitment(c)
    print(f"Tripwire triggered: {wire.condition}")
    print_verdict(engine.evaluate(c, record))


def cmd_reaffirm(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    c = engine.reaffirm(_load_commitment(store, record), args.note or "")
    store.save_commitment(c)
    print(f"Reaffirmed. The bar to change this decision is now {engine.threshold(c):.1f}.")


def cmd_reverse(args, store: DecisionStore) -> None:
    record = _load(store, args.id)
    c = _load_commitment(store, record)
    try:
        engine.reverse(c, record, args.reason or "")
    except engine.CommitmentLocked as locked:
        print("Not reversed. The engine is holding this decision.")
        print_verdict(locked.verdict)
        sys.exit(2)
    except ValueError as err:
        sys.exit(str(err))
    store.save_commitment(c)
    print("Reversed and recorded. Capture your new decision with `tpr capture` and commit to it.")


def cmd_whatif(args, store: DecisionStore) -> None:
    print(llm.what_if(_load(store, args.id), args.alternate))


def cmd_defend(args, store: DecisionStore) -> None:
    print(llm.defend_past_self(_load(store, args.id), args.text))


def cmd_plan(args, store: DecisionStore) -> None:
    print(llm.goal_plan(_load(store, args.id), args.months, args.milestones))


def cmd_export(args, store: DecisionStore) -> None:
    print(json.dumps(store.export(), indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def _commit_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--conviction", type=int, default=7, help="how sure you are, 1-10 (default 7)")
    p.add_argument("--anchor", help="a note to your future self")
    p.add_argument("--tripwire", action="append", help="a condition that would justify reconsidering (repeatable)")
    p.add_argument("--cooling-days", type=int, default=30, help="days before doubts alone can unlock it (default 30)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tpr", description="Temporal Paradox Resolver: decide once, then hold.")
    parser.add_argument("--db", default=os.getenv("TPR_DB", DEFAULT_DB), help="SQLite file (default: decisions.db or $TPR_DB)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("capture", help="record a decision and lock it in (interactive without --choice)")
    p.add_argument("--choice", help="the decision in your own words")
    p.add_argument("--chosen", help="name of the option you picked")
    p.add_argument("--values", help="ranked values, comma-separated, most important first")
    p.add_argument("--alt", action="append", help='an option: "Name | pro; pro | con; con" (repeatable)')
    p.add_argument("--reasoning", help="why you chose it")
    p.add_argument("--tags", help="comma-separated tags")
    p.add_argument("--no-commit", action="store_true", help="save without locking it")
    _commit_flags(p)
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("commit", help="lock an existing decision")
    p.add_argument("id")
    _commit_flags(p)
    p.set_defaults(func=cmd_commit)

    sub.add_parser("list", help="list decisions and their status").set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="full record, reminder, history, verdict")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("doubt", help="log a doubt instead of acting on it")
    p.add_argument("id")
    p.add_argument("text")
    p.add_argument("--new", action="store_true", help="this is information you did not have when you decided")
    p.add_argument("--value", help="which of your ranked values it touches")
    p.add_argument("--severity", type=int, default=3, help="1-5 (default 3)")
    p.add_argument("--energy", type=int, default=6, help="your energy right now, 1-10 (default 6)")
    p.add_argument("--stress", type=int, default=4, help="your stress right now, 1-10 (default 4)")
    p.set_defaults(func=cmd_doubt)

    p = sub.add_parser("check", help="ask the engine for a verdict, with every doubt's weight")
    p.add_argument("id")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("trip", help="mark a tripwire as triggered")
    p.add_argument("id")
    p.add_argument("which", help="tripwire number (1, 2, ...) or id prefix")
    p.add_argument("--evidence", help="what happened")
    p.set_defaults(func=cmd_trip)

    p = sub.add_parser("reaffirm", help="choose the decision again; the lock gets stronger")
    p.add_argument("id")
    p.add_argument("--note")
    p.set_defaults(func=cmd_reaffirm)

    p = sub.add_parser("reverse", help="change the decision (only when the engine says RECONSIDER)")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_reverse)

    p = sub.add_parser("whatif", help="simulate the timeline of an option you did not take")
    p.add_argument("id")
    p.add_argument("alternate")
    p.set_defaults(func=cmd_whatif)

    p = sub.add_parser("defend", help="hear your past self's case against a doubt")
    p.add_argument("id")
    p.add_argument("text")
    p.set_defaults(func=cmd_defend)

    p = sub.add_parser("plan", help="milestones that make your decision pay off")
    p.add_argument("id")
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--milestones", type=int, default=3)
    p.set_defaults(func=cmd_plan)

    sub.add_parser("export", help="dump everything as JSON").set_defaults(func=cmd_export)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    with DecisionStore(args.db) as store:
        try:
            args.func(args, store)
        except (KeyError, ValueError) as err:
            sys.exit(str(err).strip("'\""))


if __name__ == "__main__":
    main()
