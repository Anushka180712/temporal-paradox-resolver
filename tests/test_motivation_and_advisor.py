import datetime as dt

from temporal_paradox_resolver import advisor, commitment as engine, motivation
from temporal_paradox_resolver.models import DecisionRecord

T0 = dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc)


def record(**kw):
    base = dict(
        choice="Which job to take", chosen="Startup", values_ranked=["growth", "money"],
        alternatives=[{"name": "Startup", "pros": ["fast growth", "ownership"], "cons": ["risk"]},
                      {"name": "Bank", "pros": ["salary"], "cons": ["slow growth"]}],
        reasoning="I want growth more than comfort right now.",
    )
    base.update(kw)
    return DecisionRecord(**base)


def test_streak_counts_consecutive_days_and_survives_until_tonight(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = record()
    c = engine.commit(r, now=T0)
    for d in (1, 2, 3):
        motivation.check_in(c, 4, f"win {d}", today=dt.date(2026, 1, d))
    assert motivation.streak(c, dt.date(2026, 1, 3)) == 3
    assert motivation.streak(c, dt.date(2026, 1, 4)) == 3   # not checked in yet today
    assert motivation.streak(c, dt.date(2026, 1, 5)) == 0
    motivation.check_in(c, 5, "better win", today=dt.date(2026, 1, 3))
    assert len(c.checkins) == 3 and c.checkins[-1].win == "better win"


def test_daily_message_uses_their_own_reasons_and_marks_milestones(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = record()
    c = engine.commit(r, anchor="You chose growth on purpose.", now=T0)
    m = motivation.daily_message(r, c, today=dt.date(2026, 1, 8))
    assert m.days_held == 7 and m.milestone == 7 and m.next_milestone == 14
    assert "7 days" in m.title
    assert "I want growth more than comfort right now." in m.why
    assert any("slow growth" in w for w in m.why)        # what they chose not to live with
    assert "You chose growth on purpose." in m.why
    messages = {motivation.daily_message(r, c, today=dt.date(2026, 2, d)).message for d in range(1, 15)}
    assert len(messages) > 3                               # it changes from day to day
    assert motivation.daily_message(r, c, today=dt.date(2026, 2, 1)).message == \
        motivation.daily_message(r, c, today=dt.date(2026, 2, 1)).message


def test_a_balanced_decision_is_ready():
    a = advisor.review(record(), conviction=7, tripwires=["Company runs out of money"])
    assert a.opening.startswith("It's okay to choose Startup.")
    assert a.ready, [p.title for p in a.points]
    assert any("salary" in s for s in a.other_side)


def test_advisor_flags_one_sided_and_pressured_decisions():
    r = record(
        reasoning="My parents expect it and I already invested two years, I'm scared of the other one.",
        alternatives=[{"name": "Startup", "pros": ["ownership"], "cons": []},
                      {"name": "Bank", "pros": [], "cons": ["boring"]}],
    )
    a = advisor.review(r, conviction=10, tripwires=[], energy_level=2)
    titles = " | ".join(p.title for p in a.points)
    for expected in ["No good points written for Bank", "No downsides listed", "Whose decision",
                     "Sunk cost", "fear", "exhausted", "100% sure", "reconsider if"]:
        assert expected in titles, expected
    assert not a.ready


def test_advisor_checks_top_value_alignment():
    r = record(reasoning="The office is close to home.",
               alternatives=[{"name": "Startup", "pros": ["near home"], "cons": ["risk"]},
                             {"name": "Bank", "pros": ["salary"], "cons": ["far"]}])
    assert any("serve 'growth'" in p.title for p in advisor.review(r, tripwires=["x"]).points)


def test_outside_view_offline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert advisor.outside_view(record()).startswith("It's okay to choose Startup.")
