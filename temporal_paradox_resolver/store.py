"""SQLite storage for decisions and their commitments.

Each row holds the object as JSON, so the schema can grow without migrations.
Databases created by the first version of the project (a column-per-field
``decisions`` table) are imported automatically on first open.
"""

from __future__ import annotations

import json
import sqlite3
from typing import List, Optional

from .models import Commitment, DecisionRecord

DEFAULT_DB = "decisions.db"


class DecisionStore:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = db_path
        # check_same_thread=False lets Streamlit reuse the connection across reruns.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    # -- setup -------------------------------------------------------------
    def _init_db(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS decision_records (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS commitments (
                decision_id TEXT PRIMARY KEY REFERENCES decision_records(id),
                payload TEXT NOT NULL
            );
            """
        )
        self._import_legacy()
        self._conn.commit()

    def _import_legacy(self) -> None:
        exists = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='decisions'"
        ).fetchone()
        if not exists:
            return
        for row in self._conn.execute("SELECT * FROM decisions").fetchall():
            data = dict(row)
            for key in ("values_ranked", "alternatives", "context", "tags"):
                try:
                    data[key] = json.loads(data.get(key) or "null") or ([] if key != "context" else {})
                except (TypeError, ValueError):
                    data[key] = [] if key != "context" else {}
            record = DecisionRecord.from_dict(data)
            self._conn.execute(
                "INSERT OR IGNORE INTO decision_records (id, timestamp, payload) VALUES (?, ?, ?)",
                (record.id, record.timestamp, json.dumps(record.to_dict())),
            )

    # -- decisions ---------------------------------------------------------
    def add(self, record: DecisionRecord) -> DecisionRecord:
        self._conn.execute(
            "INSERT INTO decision_records (id, timestamp, payload) VALUES (?, ?, ?)",
            (record.id, record.timestamp, json.dumps(record.to_dict())),
        )
        self._conn.commit()
        return record

    def get(self, record_id: str) -> Optional[DecisionRecord]:
        """Fetch by full id or by a unique id prefix (handy on the command line)."""
        if not record_id.strip():
            return None
        rows = self._conn.execute(
            "SELECT payload FROM decision_records WHERE id LIKE ? || '%'", (record_id,)
        ).fetchall()
        if len(rows) != 1:
            return None
        return DecisionRecord.from_dict(json.loads(rows[0]["payload"]))

    def list_all(self) -> List[DecisionRecord]:
        rows = self._conn.execute(
            "SELECT payload FROM decision_records ORDER BY timestamp DESC"
        ).fetchall()
        return [DecisionRecord.from_dict(json.loads(r["payload"])) for r in rows]

    # -- commitments -------------------------------------------------------
    def save_commitment(self, commitment: Commitment) -> Commitment:
        self._conn.execute(
            "INSERT INTO commitments (decision_id, payload) VALUES (?, ?) "
            "ON CONFLICT(decision_id) DO UPDATE SET payload = excluded.payload",
            (commitment.decision_id, json.dumps(commitment.to_dict())),
        )
        self._conn.commit()
        return commitment

    def get_commitment(self, decision_id: str) -> Optional[Commitment]:
        row = self._conn.execute(
            "SELECT payload FROM commitments WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        return Commitment.from_dict(json.loads(row["payload"])) if row else None

    # -- export ------------------------------------------------------------
    def export(self) -> List[dict]:
        out = []
        for record in self.list_all():
            commitment = self.get_commitment(record.id)
            out.append({"decision": record.to_dict(),
                        "commitment": commitment.to_dict() if commitment else None})
        return out

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DecisionStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
