import datetime as dt

import pytest

from temporal_paradox_resolver import commitment as engine
from temporal_paradox_resolver.models import DecisionRecord, Doubt, to_iso

T0 = dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc)


def days(n: float) -> dt.datetime:
    return T0 + dt.timedelta(days=n)


@pytest.fixture
def record() -> DecisionRecord:
    return DecisionRecord(
        choice="Take the startup offer over the bank",
        chosen="Startup",
        values_ranked=["growth", "autonomy", "money"],
        alternatives=[
            {"name": "Startup", "pros": ["learning"], "cons": ["risk"]},
            {"name": "Bank", "pros": ["salary"], "cons": ["slow"]},
        ],
        reasoning="I learn fastest where I own real problems.",
    )


def doubt(text="x", at=0, new=True, value="growth", severity=5, energy=8, stress=2) -> Doubt:
    return Doubt(text=text, is_new_information=new, affects_value=value, severity=severity,
                 energy_level=energy, stress_level=stress, timestamp=to_iso(days(at)))


def committed(record, conviction=7, cooling=30, tripwires=()):
    return engine.commit(record, conviction=conviction, tripwires=tripwires, cooling_days=cooling, now=T0)


# --- scoring ---------------------------------------------------------------
def test_new_information_about_top_value_in_clear_state_gets_full_weight(record):
    s = engine.score_doubt(doubt(at=0), record, now=days(0))
    assert s.score == 5.0


def test_old_news_is_heavily_discounted(record):
    s = engine.score_doubt(doubt(new=False), record, now=days(0))
    assert s.score == pytest.approx(1.25)


def test_lower_ranked_values_weigh_less(record):
    assert engine.score_doubt(doubt(value="money"), record, now=days(0)).score == pytest.approx(5 / 3, rel=1e-3)


def test_doubts_from_an_exhausted_mind_count_half(record):
    assert engine.score_doubt(doubt(energy=2), record, now=days(0)).score == 2.5
    assert engine.score_doubt(doubt(stress=9), record, now=days(0)).score == 2.5


def test_doubts_fade_with_time(record):
    assert engine.score_doubt(doubt(at=0), record, now=days(60)).score == pytest.approx(2.5)


# --- holding ---------------------------------------------------------------
def test_a_fresh_commitment_holds(record):
    v = engine.evaluate(committed(record), record, now=days(1))
    assert v.decision == engine.HOLD
    assert not v.can_reverse


def test_one_terrible_night_never_breaks_a_decision(record):
    c = committed(record)
    for i in range(10):  # ten panicked doubts in one evening, all re-arguing known trade-offs
        engine.log_doubt(c, doubt(text=f"panic {i}", at=40, new=False, energy=2, stress=9))
    v = engine.evaluate(c, record, now=days(40))
    assert v.decision == engine.HOLD


def test_a_single_strong_new_doubt_is_not_enough(record):
    c = committed(record, conviction=1, cooling=0)
    engine.log_doubt(c, doubt(at=40, severity=5))
    v = engine.evaluate(c, record, now=days(40))
    assert v.decision != engine.RECONSIDER
    assert any("at least 2" in r for r in v.reasons)


def test_evidence_must_persist_over_a_week(record):
    c = committed(record, conviction=1, cooling=0)
    for i in range(4):
        engine.log_doubt(c, doubt(text=f"d{i}", at=40 + i * 0.5))
    v = engine.evaluate(c, record, now=days(42))
    assert v.decision != engine.RECONSIDER
    assert any("persist" in r for r in v.reasons)


def test_strong_persistent_new_evidence_unlocks_review(record):
    c = committed(record, conviction=5)   # bar = 6 + 6 = 12
    for at in (35, 40, 45):
        engine.log_doubt(c, doubt(text=f"new fact on day {at}", at=at))
    v = engine.evaluate(c, record, now=days(45))
    assert v.decision == engine.RECONSIDER, v.reasons


def test_cooling_period_blocks_ordinary_evidence(record):
    c = committed(record, conviction=5, cooling=60)
    for at in (35, 40, 45):
        engine.log_doubt(c, doubt(text=f"d{at}", at=at))
    v = engine.evaluate(c, record, now=days(45))
    assert v.decision == engine.WATCH
    assert any("cooling period" in r for r in v.reasons)


def test_watch_when_evidence_is_building(record):
    c = committed(record, conviction=5)
    engine.log_doubt(c, doubt(at=40, severity=4))
    engine.log_doubt(c, doubt(at=41, severity=4))
    v = engine.evaluate(c, record, now=days(41))
    assert v.decision == engine.WATCH


# --- tripwires -------------------------------------------------------------
def test_tripwire_overrides_cooling_period(record):
    c = committed(record, tripwires=["The company loses its funding"])
    engine.trigger_tripwire(c, "1", "Series A fell through", now=days(3))
    v = engine.evaluate(c, record, now=days(3))
    assert v.decision == engine.RECONSIDER
    assert "funding" in v.reasons[0]


def test_unknown_tripwire_raises(record):
    with pytest.raises(KeyError):
        engine.trigger_tripwire(committed(record), "7")


# --- hysteresis ------------------------------------------------------------
def test_reaffirming_raises_the_bar_and_clears_answered_doubts(record):
    c = committed(record, conviction=5)
    for at in (35, 40, 45):
        engine.log_doubt(c, doubt(text=f"d{at}", at=at))
    before = engine.threshold(c)
    engine.reaffirm(c, "Thought it through, still right.", now=days(46))
    assert engine.threshold(c) == pytest.approx(before * 1.25)
    v = engine.evaluate(c, record, now=days(47))
    assert v.decision == engine.HOLD
    assert v.evidence == 0


def test_the_same_evidence_cannot_flip_it_back_after_reaffirming(record):
    c = committed(record, conviction=5)
    for at in (35, 40, 45):
        engine.log_doubt(c, doubt(text=f"d{at}", at=at))
    engine.reaffirm(c, now=days(46))
    for at in (50, 55, 60):   # the same amount of evidence again
        engine.log_doubt(c, doubt(text=f"again {at}", at=at))
    assert engine.evaluate(c, record, now=days(60)).decision == engine.WATCH


def test_reaffirming_spends_triggered_tripwires(record):
    c = committed(record, tripwires=["Manager leaves"])
    engine.trigger_tripwire(c, "1", now=days(5))
    engine.reaffirm(c, now=days(6))
    assert engine.evaluate(c, record, now=days(7)).decision == engine.HOLD


# --- reversing -------------------------------------------------------------
def test_reverse_is_refused_while_held(record):
    c = committed(record)
    with pytest.raises(engine.CommitmentLocked) as err:
        engine.reverse(c, record, "I just feel like it today, honestly, a lot.", now=days(2))
    assert err.value.verdict.decision == engine.HOLD
    assert c.status == "committed"


def test_reverse_needs_a_written_reason(record):
    c = committed(record, tripwires=["Startup shuts down"])
    engine.trigger_tripwire(c, "1", now=days(2))
    with pytest.raises(ValueError):
        engine.reverse(c, record, "meh", now=days(2))


def test_reverse_after_tripwire(record):
    c = committed(record, tripwires=["Startup shuts down"])
    engine.trigger_tripwire(c, "1", "Doors closed on Friday", now=days(2))
    engine.reverse(c, record, "The company no longer exists, so the decision is void.", now=days(2))
    assert c.status == "reversed"
    assert c.history[-1].kind == "reversed"
    with pytest.raises(ValueError):
        engine.log_doubt(c, doubt())


def test_reminder_quotes_the_past_self(record):
    c = engine.commit(record, conviction=9, anchor="Future me: you were not naive.",
                      tripwires=["Burnout for 3 months"], now=T0)
    text = engine.reminder(c, record, now=days(10))
    assert "not naive" in text and "Burnout" in text and "growth, autonomy, money" in text
