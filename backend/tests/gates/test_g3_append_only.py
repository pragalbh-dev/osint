"""G3 — append-only store. No UPDATE/DELETE; claims immutable; retraction is an appended claim (§5).

Three checks: the log API surface has no mutating methods; a *raw* SQL UPDATE/DELETE is refused by the
triggers (belt-and-braces); and a retraction round-trips (appended, replayed, and excluded from the
rebuilt view — never a physical delete).
"""

from __future__ import annotations

import sqlite3

import pytest

from chanakya.schemas import ClaimRecord, DocRef, Triple
from chanakya.store import DecisionLog, EvidenceLog
from chanakya.view import rebuild
from tests.fixtures import loaders


def test_no_mutating_methods_on_the_api() -> None:
    for cls in (EvidenceLog, DecisionLog):
        names = {n for n in dir(cls) if not n.startswith("_")}
        assert not (names & {"update", "delete", "remove", "edit", "set", "pop"}), cls.__name__


def test_raw_sql_update_and_delete_are_refused() -> None:
    log = EvidenceLog()
    log.append(ClaimRecord(claim_id="c-1", source_id="s", doc_ref=DocRef(file="f"),
                           kind="observation", asserts="relationship",
                           payload=Triple(subject="a", predicate="p", object="b")))
    conn = log._conn  # reach past the API to prove even raw SQL can't mutate
    with pytest.raises(sqlite3.Error):
        conn.execute("UPDATE events SET payload = '{}' WHERE record_id = 'c-1'")
    with pytest.raises(sqlite3.Error):
        conn.execute("DELETE FROM events WHERE record_id = 'c-1'")


def test_retraction_round_trips_and_excludes_the_target() -> None:
    ev = loaders.golden_evidence_log()
    # The golden log contains d05-bogus and a retraction (d05-retract) targeting it.
    replayed_ids = {c.claim_id for c in ev.replay()}
    assert {"d05-bogus", "d05-retract"} <= replayed_ids  # both physically present (append-only)

    view = rebuild(ev, loaders.golden_decision_log(), loaders.golden_config_store().snapshot())
    # …but the retracted assertion is absent from the rebuilt view.
    assert not any("phantom" in n.id for n in view.nodes)
    assert not any("phantom" in e.id for e in view.edges)
