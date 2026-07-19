"""Smoke tests for the Wave-1 stage stubs — each is trivially correct so the skeleton runs today.

These also pin the frozen stage *shapes* a Wave-1 session fills. When a session lands, it replaces the
stub body and updates the relevant assertion here (it must keep the signature).
"""

from __future__ import annotations

from chanakya.credibility import assign_status, group_by_independence, score_claims
from chanakya.materiality import precompute
from chanakya.observe import evaluate
from chanakya.resolve import resolve
from chanakya.schemas import AssertionInput, ClaimRecord, ConfigBundle, GraphView
from chanakya.sufficiency import check
from tests.fixtures import loaders

CFG = ConfigBundle()


def test_resolve_stub_is_identity_matching_fixture() -> None:
    fx = loaders.per_stage("resolution_partition")
    claims = [ClaimRecord.model_validate(r) for r in fx["input_claims"]]
    part = resolve(claims, CFG)
    got = {cid: rr.model_dump(exclude_none=True) for cid, rr in part.resolved_ref.items()}
    assert got == fx["expected_identity"]["resolved_ref"]
    assert part.same_as == [] and part.distinct_from == []


def test_credibility_shapes() -> None:
    # SCORE stages are live now (not stubs): no claims → no credibilities; claim ids with no bodies
    # can't be grouped (fail-closed); an empty assertion pools to 0.0 → possible (never fabricated).
    assert score_claims([], {}, CFG) == {}
    assert group_by_independence(["a", "b"], {}, {}, CFG) == []  # unknown claims → no groups
    assessments = assign_status([AssertionInput(element_id="e1", element_kind="edge")], CFG)
    assert assessments["e1"].assertion_confidence == 0.0
    assert assessments["e1"].status == "possible"


def test_sufficiency_and_materiality_and_observe_stubs() -> None:
    suff = check(AssertionInput(element_id="e1", element_kind="edge"), {}, CFG)
    assert suff.satisfied and suff.missing_slots == []
    view = GraphView()
    assert precompute(view, CFG) is view  # identity
    assert evaluate(None, view, CFG) == []  # fires nothing


def test_full_rebuild_runs_with_stubs() -> None:
    view = loaders.golden_view()
    assert view.nodes and view.edges  # end-to-end skeleton produces a non-empty view
