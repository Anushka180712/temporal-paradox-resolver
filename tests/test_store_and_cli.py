import json
import sqlite3

import pytest

from temporal_paradox_resolver import commitment as engine
from temporal_paradox_resolver import llm
from temporal_paradox_resolver.cli import main, parse_alternative
from temporal_paradox_resolver.models import DecisionRecord, Doubt
from temporal_paradox_resolver.store import DecisionStore


def test_round_trip(tmp_path):
    db = str(tmp_path / "t.db")
    with DecisionStore(db) as store:
        r = store.add(DecisionRecord(choice="Move to Pune", chosen="Pune", values_ranked=["family"]))
        c = engine.commit(r, conviction=8, tripwires=["Parents need me home"])
        engine.log_doubt(c, Doubt(text="Rent is high", is_new_information=True))
        store.save_commitment(c)
    with DecisionStore(db) as store:
        assert store.get(r.id[:8]).chosen == "Pune"
        loaded = store.get_commitment(r.id)
        assert loaded.conviction == 8
        assert loaded.doubts[0].text == "Rent is high"
        assert loaded.tripwires[0].condition == "Parents need me home"
        assert store.export()[0]["commitment"]["decision_id"] == r.id


def test_imports_databases_from_the_first_version(tmp_path):
    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE decisions (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, choice TEXT NOT NULL,
        values_ranked TEXT NOT NULL, alternatives TEXT NOT NULL, context TEXT NOT NULL, notes TEXT,
        tags TEXT NOT NULL, created_at TEXT)""")
    conn.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,NULL)",
                 ("abc-1", "2024-05-01T10:00:00Z", "Job A", '["money"]', "[]", "{}", "", '["career"]'))
    conn.commit()
    conn.close()
    with DecisionStore(db) as store:
        [r] = store.list_all()
        assert r.choice == "Job A" and r.values_ranked == ["money"] and r.tags == ["career"]


def test_parse_alternative():
    assert parse_alternative("Bank | salary; stability | slow") == {
        "name": "Bank", "pros": ["salary", "stability"], "cons": ["slow"]}
    assert parse_alternative("Gap year") == {"name": "Gap year", "pros": [], "cons": []}


def test_cli_end_to_end(tmp_path, capsys):
    db = ["--db", str(tmp_path / "cli.db")]
    main(db + ["capture", "--choice", "Study CS at a state college", "--chosen", "State college",
               "--values", "learning, money, family", "--alt", "State college | cheap | less brand",
               "--alt", "Private college | brand | expensive", "--conviction", "8",
               "--tripwire", "I fail two courses in a semester", "--cooling-days", "14"])
    out = capsys.readouterr().out
    assert "Committed at 8/10 with 1 tripwire(s)" in out

    with DecisionStore(db[1]) as store:
        rid = store.list_all()[0].id[:8]

    main(db + ["doubt", rid, "My friend at the private college got an internship", "--value", "learning"])
    out = capsys.readouterr().out
    assert "Doubt logged" in out and "Verdict: HOLD" in out

    with pytest.raises(SystemExit) as err:
        main(db + ["reverse", rid, "--reason", "I want what my friend has, it looks better there."])
    assert err.value.code == 2
    assert "Not reversed" in capsys.readouterr().out

    main(db + ["trip", rid, "1", "--evidence", "Failed DSA and OS"])
    assert "RECONSIDER" in capsys.readouterr().out
    main(db + ["reverse", rid, "--reason", "Two failed courses: this program is not working for me."])
    assert "Reversed and recorded" in capsys.readouterr().out

    main(db + ["export"])
    data = json.loads(capsys.readouterr().out)
    assert data[0]["commitment"]["status"] == "reversed"


def test_llm_features_work_offline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = DecisionRecord(choice="x", chosen="A", values_ranked=["calm"], reasoning="quiet life",
                       alternatives=[{"name": "A"}, {"name": "B", "pros": ["fun"], "cons": ["chaos"]}])
    assert "fun" in llm.what_if(r, "B")
    assert "quiet life" in llm.defend_past_self(r, "B looks fun")
    assert llm.goal_plan(r).count("Month") == 3
