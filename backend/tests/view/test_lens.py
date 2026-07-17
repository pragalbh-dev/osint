"""Unit tests for subject-lens scoping (N-hop reachability + materiality filter)."""

from __future__ import annotations

from chanakya.schemas import MaterialityAttrs, SubjectLens
from chanakya.view import apply_lens
from tests.fixtures import loaders


def test_hop_bound_scopes_the_graph() -> None:
    view = loaders.golden_view()
    ids_1 = {n.id for n in apply_lens(view, SubjectLens(subject_id="s", anchors=["unit_acme"], max_hops=1)).nodes}
    ids_2 = {n.id for n in apply_lens(view, SubjectLens(subject_id="s", anchors=["unit_acme"], max_hops=2)).nodes}
    assert "comp_gizmo" in ids_1 and "mfr_foundry" not in ids_1
    assert "mfr_foundry" in ids_2  # supplier reached at 2 hops (unit → component → manufacturer)


def test_edges_survive_only_when_both_endpoints_do() -> None:
    view = loaders.golden_view()
    scoped = apply_lens(view, SubjectLens(subject_id="s", anchors=["unit_acme"], max_hops=1))
    ids = {n.id for n in scoped.nodes}
    assert all(e.source in ids and e.target in ids for e in scoped.edges)
    assert scoped.meta["subject"] == "s"


def test_materiality_filter_keeps_unknown_but_drops_low() -> None:
    view = loaders.golden_view()
    # Tag one node as low-materiality; anchors are always kept, unknown attrs pass.
    for n in view.nodes:
        if n.id == "site_north":
            n.materiality = MaterialityAttrs(chokepoint_count=0)
    lens = SubjectLens(subject_id="s", anchors=["unit_acme"], max_hops=2,
                       materiality_filter={"min_chokepoint_count": 1})
    ids = {n.id for n in apply_lens(view, lens).nodes}
    assert "site_north" not in ids  # explicitly low → dropped
    assert "site_south" in ids and "unit_acme" in ids  # unknown / anchor → kept
