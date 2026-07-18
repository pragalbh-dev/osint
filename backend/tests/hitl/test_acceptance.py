"""HITL acceptance — the session's six criteria + the gates it must keep green (sessions/HITL.md).

All run against **F0's golden fixtures + store + ``rebuild()``** (not sibling code). Where a stubbed
sibling (RESOLVE/SCORE) means the *recompute* itself can't be exercised here, the test asserts the
decision-log state + the ``effects`` shape the sibling will consume; full consumption is re-verified
end-to-end at EVAL.
"""

from __future__ import annotations

from chanakya.hitl import (
    bind_writeback,
    build_integrity_flag_item,
    build_merge_item,
    build_status_override_item,
    dispose,
    order_queue,
    should_escalate,
)
from chanakya.hitl.triage import STAR_TYPES
from chanakya.schemas import ClaimRecord, ReviewContext
from chanakya.store import DecisionLog
from chanakya.view import rebuild
from tests.fixtures import loaders

_EDGE = "e:mfr_foundry:supplies-component:comp_gizmo"


def _cfg():
    return loaders.golden_config_store().snapshot()


def _edge_status(view, edge_id: str = _EDGE):
    return next((e.status for e in view.edges if e.id == edge_id), None)


def _confirmed_answer(view) -> list[str]:
    """A stand-in 'downstream answer': the edges an analyst would report as confirmed."""
    return sorted(e.id for e in view.edges if e.status == "confirmed")


# ── criterion 1: G12 — a status override propagates on rebuild and changes a downstream answer ────

def test_g12_status_override_propagates_and_changes_the_answer() -> None:
    cfg = _cfg()
    dl = DecisionLog()

    # analyst promotes the supplies-component edge → confirmed
    promote = build_status_override_item(item_id="sov", subject_ref=_EDGE, current_status=None, ts="t")
    dispose(promote, "promote", bind_writeback(promote, dl, ts="t"))
    after_promote = rebuild(loaders.golden_evidence_log(), dl, cfg)
    assert _edge_status(after_promote) == "confirmed"
    assert _EDGE in _confirmed_answer(after_promote)  # the answer now reports it

    # analyst rejects (forced demote) → confirmed→probable, and the answer changes
    reject = build_status_override_item(item_id="sov2", subject_ref=_EDGE, current_status="confirmed", ts="t")
    dispose(reject, "reject", bind_writeback(reject, dl, ts="t"))
    after_reject = rebuild(loaders.golden_evidence_log(), dl, cfg)
    assert _edge_status(after_reject) == "probable"  # dropped off "confirmed"
    assert _EDGE not in _confirmed_answer(after_reject)  # downstream answer changed


# ── criterion 2: a merge accept grows the alias table; a split reverses it (append-only) ──────────

def test_merge_accept_grows_alias_table_and_split_reverses() -> None:
    dl = DecisionLog()
    merge = build_merge_item(
        item_id="mrg", candidate_a={"id": "var_a", "name": "A"}, candidate_b={"id": "var_b", "name": "B"},
        signals=[{"signal": "name-attr", "weight": 0.3, "value": 0.8}], merge_score=0.6, band="needs-you", ts="t",
    )
    dispose(merge, "accept", bind_writeback(merge, dl, ts="t"))
    rec_accept = dl.replay()[0]
    # the effect carries the same-as + alias pair in the shape RESOLVE reads on the next rebuild
    assert rec_accept.effects["grow_alias"]["same_as"] == ["var_a", "var_b"]
    assert rec_accept.effects["grow_alias"]["alias"] == {"canonical": "var_a", "surface": "B"}

    # a later split reverses the accept — a *new appended record*, never an edit/delete (gate G3)
    split_card = build_merge_item(
        item_id="mrg-split", candidate_a={"id": "var_a", "name": "A"}, candidate_b={"id": "var_b", "name": "B"},
        signals=[], merge_score=0.6, band="needs-you", ts="t2", prior_merge_event=rec_accept.event_id,
    )
    dispose(split_card, "split", bind_writeback(split_card, dl, ts="t2"))
    assert dl.count() == 2  # both records present
    assert dl.replay()[0].effects["grow_alias"]["same_as"] == ["var_a", "var_b"]  # accept unchanged
    assert dl.replay()[1].effects["split_merge"]["reverses"] == rec_accept.event_id


# ── criterion 3: decision replay is deterministic (G2-style over HITL records) ────────────────────

def test_decision_replay_is_deterministic() -> None:
    cfg = _cfg()
    records = []
    for item_id, opt in (("a", "promote"), ("b", "demote")):
        card = build_status_override_item(item_id=item_id, subject_ref=_EDGE, current_status=None, ts="t")
        log = DecisionLog()
        dispose(card, opt, bind_writeback(card, log, ts="t"))
        records.extend(log.replay())

    j1 = rebuild(loaders.golden_evidence_log(), records, cfg).model_dump_json()
    j2 = rebuild(loaders.golden_evidence_log(), records, cfg).model_dump_json()
    assert j1 == j2  # byte-identical across runs — HITL records introduce no nondeterminism


# ── criterion 4: an analyst integrity flag propagates to all co-referring claims of one origin ────

def _co_referring_log() -> list[ClaimRecord]:
    """Two claims from two apparent sources sharing one origin, co-referring to the SAME edge."""
    base = {"kind": "observation", "asserts": "relationship",
            "payload": {"form": "triple", "subject": "unit_x", "predicate": "based-at", "object": "site_y"},
            "event_time": {"kind": "exact", "iso_date": "2024-01-01"},
            "resolved_ref": {"edge_instance": "based-at:unit_x"}}
    return [
        ClaimRecord.model_validate({**base, "claim_id": "co1", "source_id": "src-a", "doc_ref": {"file": "a.txt", "row": 1}}),
        ClaimRecord.model_validate({**base, "claim_id": "co2", "source_id": "src-b", "doc_ref": {"file": "b.txt", "row": 1}}),
    ]


def test_integrity_flag_propagates_to_every_echo_of_the_origin() -> None:
    cfg = _cfg()
    evidence = _co_referring_log()
    element = "e:unit_x:based-at:site_y"

    before = rebuild(evidence, [], cfg)
    edge_before = next(e for e in before.edges if e.id == element)
    assert sorted(edge_before.claim_ids) == ["co1", "co2"]  # ≥2 co-referring claims on one element
    assert not (edge_before.confidence and edge_before.confidence.integrity_flags)

    dl = DecisionLog()
    flag = build_integrity_flag_item(
        item_id="ig", primary_origin_id="origin-fake", affected_element=element,
        co_referring_claims=["co1", "co2"], ts="t",
    )
    dispose(flag, "flag", bind_writeback(flag, dl, ts="t"))

    after = rebuild(evidence, dl, cfg)
    edge_after = next(e for e in after.edges if e.id == element)
    # the flag reached the element every co-referring claim supports — no per-claim fan-out
    assert "analyst-flagged-inauthentic" in edge_after.confidence.integrity_flags
    rec = dl.replay()[0]
    assert rec.type == "integrity_flag" and rec.subject_ref == "origin-fake"
    assert rec.effects["flag_origin"]["co_referring_claims"] == ["co1", "co2"]


# ── criterion 5: ★ items pinned regardless of a hostile LLM rank; the gate is untouchable ─────────

def test_star_items_pinned_and_llm_cannot_move_the_boundary() -> None:
    star = build_status_override_item(item_id="star", subject_ref=_EDGE, current_status=None)
    m = build_merge_item(item_id="plain", candidate_a={"id": "a", "name": "A"},
                         candidate_b={"id": "b", "name": "B"}, signals=[], merge_score=0.6, band="needs-you")
    m.pinned = False  # a non-pinned merge for contrast
    hostile = ["plain", "star"]  # rank tries to put the plain item first
    ordered = order_queue([m, star], frozen_rank=hostile)
    assert ordered[0].item_id == "star"  # ★ stays pinned to the top

    assert set(STAR_TYPES) == {"merge", "status-override", "alert-disposition"}
    # the escalate/auto boundary is deterministic — the LLM rank has no bearing on it
    assert should_escalate(ReviewContext(confidence=0.3)) is True


# ── criterion 6 (gates): G1 no LLM/network on the disposing path; G3 append-only; G4 traceability ──

def test_g1_no_llm_or_network_imports_on_the_disposing_path() -> None:
    from tests.gates import _srcscan

    banned = {"anthropic", "httpx", "requests"}
    for path in _srcscan.package_py_files("hitl"):
        mods = _srcscan.imported_modules(path)
        leaked = {m for m in mods if any(m == b or m.startswith(b + ".") for b in banned)}
        assert not leaked, f"{path.name} imports {leaked} on the disposing path (G1)"


def test_g3_store_is_append_only() -> None:
    assert not hasattr(DecisionLog, "update")
    assert not hasattr(DecisionLog, "delete")


def test_g4_traceability_preserved_after_a_decision() -> None:
    cfg = _cfg()
    dl = DecisionLog()
    card = build_status_override_item(item_id="sov", subject_ref=_EDGE, current_status=None, ts="t")
    dispose(card, "promote", bind_writeback(card, dl, ts="t"))
    view = rebuild(loaders.golden_evidence_log(), dl, cfg)
    for el in [*view.nodes, *view.edges]:
        assert el.claim_ids, f"{el.id} lost its claim provenance (G4)"
