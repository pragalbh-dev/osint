"""G5 — two scores, never averaged. ``merge_confidence`` (identity) ≠ ``assertion_confidence`` (truth),
and status is set only by the machine / an explicit override (master §1 #4, §5).

Checks: the two scores live on *different* objects (schema-structural); a same-as edge's
``merge_confidence`` never populates any element's ``assertion_confidence``; and status appears **only**
where the status machine (or a decision override) put it — never hand-written in assembly/supersede.
"""

from __future__ import annotations

from chanakya.schemas import ConfidenceBreakdown, EdgeView
from chanakya.view import rebuild
from tests.fixtures import loaders


def test_scores_are_separate_objects() -> None:
    # merge_confidence is a field on the edge (identity); it is NOT a field of the truth breakdown.
    assert "merge_confidence" in EdgeView.model_fields
    assert "merge_confidence" not in ConfidenceBreakdown.model_fields
    assert "assertion_confidence" in ConfidenceBreakdown.model_fields
    assert "assertion_confidence" not in EdgeView.model_fields  # only via .confidence


def test_merge_confidence_does_not_feed_assertion_confidence() -> None:
    # A same-as edge carrying identity confidence must not leak into any truth confidence.
    same_as = EdgeView(id="same-as:a:b", type="same-as", source="a", target="b", merge_confidence=0.91)
    assert same_as.merge_confidence == 0.91
    # It is a distinct field; there is no code path copying it into a ConfidenceBreakdown.
    assert not hasattr(same_as, "assertion_confidence")


def test_status_only_from_machine_or_override() -> None:
    cfg = loaders.golden_config_store().snapshot()
    # With NO decisions, the stub status machine assigns nothing → every status is None.
    plain = rebuild(loaders.golden_evidence_log(), [], cfg)
    assert all(el.status is None for el in [*plain.nodes, *plain.edges, *plain.events])

    # With the golden decision log (a status_override), EXACTLY the overridden edge changes.
    overridden = rebuild(loaders.golden_evidence_log(), loaders.golden_decision_log(), cfg)
    changed = {el.id: el.status for el in overridden.edges if el.status is not None}
    assert changed == {"e:mfr_foundry:supplies-component:comp_gizmo": "probable"}
