"""Unit tests for the append-only logs: append/query/replay/seed_from/count + deterministic order."""

from __future__ import annotations

import json

from chanakya.schemas import ClaimRecord, DocRef, Triple
from chanakya.store import DecisionLog, EvidenceLog
from tests.fixtures import loaders


def _claim(cid: str, obj: str) -> ClaimRecord:
    return ClaimRecord(claim_id=cid, source_id="s", doc_ref=DocRef(file="f"),
                       kind="observation", asserts="relationship",
                       payload=Triple(subject="a", predicate="p", object=obj))


def test_append_replay_preserves_insertion_order() -> None:
    log = EvidenceLog()
    for i in range(5):
        log.append(_claim(f"c-{i}", f"o{i}"))
    assert [c.claim_id for c in log.replay()] == ["c-0", "c-1", "c-2", "c-3", "c-4"]
    assert log.count() == 5


def test_query_by_record_id() -> None:
    log = EvidenceLog()
    log.append(_claim("c-1", "x"))
    log.append(_claim("c-2", "y"))
    assert [c.payload.object for c in log.query("c-2")] == ["y"]
    assert log.query("missing") == []


def test_seed_from_json_array_and_jsonl(tmp_path) -> None:
    rows = [_claim("c-1", "x").model_dump(mode="json"), _claim("c-2", "y").model_dump(mode="json")]

    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps(rows))
    log_a = EvidenceLog()
    assert log_a.seed_from(arr) == 2 and log_a.count() == 2

    jsonl = tmp_path / "log.jsonl"
    jsonl.write_text("\n".join(json.dumps(r) for r in rows))
    log_b = EvidenceLog()
    assert log_b.seed_from(jsonl) == 2 and [c.claim_id for c in log_b.replay()] == ["c-1", "c-2"]


def test_golden_logs_seed_deterministically() -> None:
    ev = loaders.golden_evidence_log()
    assert [c.claim_id for c in ev.replay()] == [c.claim_id for c in loaders.golden_claims()]
    dl = DecisionLog()
    dl.seed_from(loaders.GOLDEN / "decision_log.json")
    assert dl.count() == 2
