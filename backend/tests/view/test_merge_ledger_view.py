"""Stage 2 (D4) — the merge-corroboration ledger, rendered ADDITIVELY on the resolution surfaces.

The candidate ``same-as`` edge and the confirmed ``resolved_from`` audit entry each grow an
``identity_ledger`` BESIDE the existing ``breakdown`` — never replacing it. The ledger is recorded
only when a signal actually corroborated the merge, so a degenerate breakdown leaves the surfaces
byte-identical to before Stage 2 (the frozen ``_merge_provenance`` shape is preserved).
"""

from __future__ import annotations

from chanakya.schemas import NodeView, Partition, pair_key
from chanakya.view.pipeline import _merge_provenance, _resolution_edges


def test_candidate_edge_carries_the_ledger_beside_the_breakdown() -> None:
    ck = pair_key("x", "y")
    part = Partition(
        candidates=[("x", "y")],
        merge_confidence={ck: 0.72},
        merge_breakdown={ck: {"attribute": 0.9, "relational": 0.1, "temporal_consistency": 1.0, "source_asserted": 0.0, "total": 0.72}},
    )
    (edge,) = _resolution_edges({"x", "y"}, part)
    assert edge.attrs["breakdown"]["total"] == 0.72  # existing field kept
    ledger = edge.attrs["identity_ledger"]
    assert [e["signal"] for e in ledger] == ["attribute", "relational", "temporal_consistency"]


def test_confirmed_resolved_from_gains_the_ledger_when_signals_corroborate() -> None:
    nodes = {"canon": NodeView(id="canon", type="variant", claim_ids=["d1-l1"])}
    key = pair_key("member", "canon")
    part = Partition(
        same_as=[("member", "canon")],
        merge_confidence={key: 0.91},
        merge_breakdown={key: {"attribute": 1.0, "relational": 0.5, "temporal_consistency": 1.0, "source_asserted": 0.0, "total": 0.91}},
    )
    _merge_provenance(nodes, part)
    entry = nodes["canon"].attrs["resolved_from"][0]
    assert entry["breakdown"]["total"] == 0.91  # existing field kept
    assert [e["signal"] for e in entry["identity_ledger"]] == ["attribute", "relational", "temporal_consistency"]


def test_resolved_from_stays_byte_identical_for_a_degenerate_breakdown() -> None:
    """Proves the pre-Stage-2 ``resolved_from`` shape is preserved: no ledger key when nothing fired."""
    nodes = {"canon": NodeView(id="canon", type="variant", claim_ids=["d1-l1"])}
    key = pair_key("member", "canon")
    part = Partition(
        same_as=[("member", "canon")],
        merge_confidence={key: 0.91},
        merge_breakdown={key: {"total": 0.91}},
    )
    _merge_provenance(nodes, part)
    entry = nodes["canon"].attrs["resolved_from"][0]
    assert "identity_ledger" not in entry
    assert entry == {"merged_ref": "member", "merge_confidence": 0.91, "breakdown": {"total": 0.91}}
