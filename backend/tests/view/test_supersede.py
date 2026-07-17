"""Unit tests for supersede-vs-contradict resolution (master §4.3 fixture requirement)."""

from __future__ import annotations

from chanakya.schemas import ClaimRecord, ConfigBundle, DocRef, ExactDate, ResolvedRef, Triple
from chanakya.store import EvidenceLog
from chanakya.view import rebuild

CFG = ConfigBundle()
INSTANCE = "based-at:unit_x"


def _based_at(cid: str, target: str, iso: str | None) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid, source_id="s", doc_ref=DocRef(file=cid),
        kind="observation", asserts="relationship",
        payload=Triple(subject="unit_x", predicate="based-at", object=target),
        event_time=ExactDate(iso_date=iso) if iso else None,
        resolved_ref=ResolvedRef(entity_id="unit_x", edge_instance=INSTANCE),
    )


def _rebuild(*claims: ClaimRecord):
    log = EvidenceLog()
    log.append_many(list(claims))
    view = rebuild(log, [], CFG)
    return {e.id: e for e in view.edges}


def test_newer_supersedes_older() -> None:
    edges = _rebuild(_based_at("c21", "site_a", "2021-01-01"), _based_at("c25", "site_b", "2025-01-01"))
    old, new = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert old.superseded_by == new.id
    assert new.supersedes == old.id
    assert not old.attrs.get("contradiction")


def test_same_time_different_target_is_a_contradiction() -> None:
    edges = _rebuild(_based_at("cA", "site_a", "2023-06-01"), _based_at("cB", "site_b", "2023-06-01"))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.attrs.get("contradiction") and b.attrs.get("contradiction")
    assert "cB" in a.opposing_claims and "cA" in b.opposing_claims
    assert a.superseded_by is None and b.superseded_by is None


def test_missing_time_yields_candidate_supersede() -> None:
    edges = _rebuild(_based_at("c1", "site_a", "2021-01-01"), _based_at("c2", "site_b", None))
    a, b = edges["e:unit_x:based-at:site_a"], edges["e:unit_x:based-at:site_b"]
    assert a.attrs.get("candidate_supersede") and b.attrs.get("candidate_supersede")
    # can't order → do NOT overwrite either position
    assert a.superseded_by is None and b.superseded_by is None


def test_same_target_is_plain_corroboration() -> None:
    edges = _rebuild(_based_at("c1", "site_a", "2021-01-01"), _based_at("c2", "site_a", "2023-01-01"))
    assert len(edges) == 1
    edge = edges["e:unit_x:based-at:site_a"]
    assert set(edge.claim_ids) == {"c1", "c2"}  # one edge, two corroborating claims
    assert edge.superseded_by is None and not edge.attrs.get("contradiction")
