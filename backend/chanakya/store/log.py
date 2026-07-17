"""Append-only event logs on SQLite (spine/08 §1; master §4.2).

Two properties are load-bearing and enforced structurally, not by convention:

* **Append-only (gate G3).** The API surface exposes ``append``/``query``/``replay``/``seed_from`` —
  **no ``update`` or ``delete``**. Belt-and-braces, SQLite ``BEFORE UPDATE/DELETE`` triggers
  ``RAISE(ABORT)`` so even a raw SQL mutation fails. A correction is an *appended* retraction claim,
  never an edit.
* **Deterministic replay (gate G2).** ``replay()`` returns records in insertion order (an
  autoincrement ``seq``), so ``rebuild()`` over the same log is byte-identical every time.

Boot reads the baked baseline via ``seed_from``; runtime ``append`` writes to a container-local copy
(master §4). In-memory (``:memory:``) is used by tests; a keyed connection is held open for its life.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pydantic import BaseModel

from chanakya.schemas import ClaimRecord, DecisionRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id  TEXT NOT NULL,
    payload    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_record_id ON events(record_id);
CREATE TRIGGER IF NOT EXISTS trg_events_no_update
    BEFORE UPDATE ON events
    BEGIN SELECT RAISE(ABORT, 'append-only log: UPDATE is forbidden'); END;
CREATE TRIGGER IF NOT EXISTS trg_events_no_delete
    BEFORE DELETE ON events
    BEGIN SELECT RAISE(ABORT, 'append-only log: DELETE is forbidden'); END;
"""


class AppendOnlyLog[R: BaseModel]:
    """A generic append-only log of pydantic records, keyed by a per-record id field."""

    def __init__(self, model: type[R], id_field: str, db_path: str | Path = ":memory:") -> None:
        self._model = model
        self._id_field = id_field
        self._db_path = str(db_path)
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        # Held open for the log's life (needed for :memory:; fine single-process at demo scale).
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── writes (append is the ONLY mutation) ─────────────────────────────────────────────────

    def append(self, record: R) -> None:
        """Append one record. No update/delete counterpart exists — that is the point (G3)."""
        rid = getattr(record, self._id_field)
        self._conn.execute(
            "INSERT INTO events(record_id, payload) VALUES (?, ?)",
            (rid, record.model_dump_json()),
        )
        self._conn.commit()

    def append_many(self, records: list[R]) -> None:
        for r in records:
            self.append(r)

    def seed_from(self, path: str | Path) -> int:
        """Load a JSON array (or JSONL) of records and append each. Returns the count appended.

        This is the baked-baseline boot path; deterministic because it preserves file order.
        """
        path = Path(path)
        text = path.read_text().strip()
        if not text:
            return 0
        rows = [json.loads(line) for line in text.splitlines()] if text[0] != "[" else json.loads(text)
        records = [self._model.model_validate(row) for row in rows]
        self.append_many(records)
        return len(records)

    # ── reads ─────────────────────────────────────────────────────────────────────────────────

    def replay(self) -> list[R]:
        """All records in insertion order — the deterministic input to ``rebuild()`` (G2)."""
        cur = self._conn.execute("SELECT payload FROM events ORDER BY seq ASC")
        return [self._model.model_validate_json(payload) for (payload,) in cur.fetchall()]

    def query(self, record_id: str | None = None) -> list[R]:
        """Filter by ``record_id`` (else all), still in insertion order."""
        if record_id is None:
            return self.replay()
        cur = self._conn.execute(
            "SELECT payload FROM events WHERE record_id = ? ORDER BY seq ASC", (record_id,)
        )
        return [self._model.model_validate_json(payload) for (payload,) in cur.fetchall()]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def close(self) -> None:
        self._conn.close()


class EvidenceLog(AppendOnlyLog[ClaimRecord]):
    """The evidence log: append-only ``ClaimRecord`` claims (the unit of analysis)."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        super().__init__(ClaimRecord, "claim_id", db_path)


class DecisionLog(AppendOnlyLog[DecisionRecord]):
    """The decision log: append-only ``DecisionRecord`` adjudications + system events."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        super().__init__(DecisionRecord, "event_id", db_path)
