"""Simple SQLite-backed storage for DecisionRecord objects."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional

from .models import DecisionRecord


class DecisionStore:
    """Wrap a SQLite database that stores immutable decision records."""

    def __init__(self, db_path: str = "decisions.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            # check_same_thread=False allows the connection to be used across threads,
            # which is necessary for Streamlit's multi‑threaded execution.
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                choice TEXT NOT NULL,
                values_ranked TEXT NOT NULL,
                alternatives TEXT NOT NULL,
                context TEXT NOT NULL,
                notes TEXT,
                tags TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()

    def add(self, record: DecisionRecord) -> None:
        """Insert a single DecisionRecord into the DB."""
        conn = self._get_conn()
        payload = record.to_dict()
        conn.execute(
            """
            INSERT INTO decisions (id, timestamp, choice, values_ranked, alternatives, context, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                payload["id"],
                payload["timestamp"],
                payload["choice"],
                json.dumps(payload["values_ranked"]),
                json.dumps(payload["alternatives"]),
                json.dumps(payload["context"]),
                payload.get("notes", ""),
                json.dumps(payload.get("tags", [])),
            ),
        )
        conn.commit()

    def get(self, record_id: str) -> Optional[DecisionRecord]:
        """Retrieve a DecisionRecord by its UUID string."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM decisions WHERE id = ?;", (record_id,)
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        # json columns need decoding
        data["values_ranked"] = json.loads(data["values_ranked"])
        data["alternatives"] = json.loads(data["alternatives"])
        data["context"] = json.loads(data["context"])
        data["tags"] = json.loads(data["tags"])
        return DecisionRecord.from_dict(data)

    def list_all(self) -> List[DecisionRecord]:
        """Return all stored records (newest first)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY timestamp DESC;"
        ).fetchall()
        records: List[DecisionRecord] = []
        for row in rows:
            data = dict(row)
            data["values_ranked"] = json.loads(data["values_ranked"])
            data["alternatives"] = json.loads(data["alternatives"])
            data["context"] = json.loads(data["context"])
            data["tags"] = json.loads(data["tags"])
            records.append(DecisionRecord.from_dict(data))
        return records

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None