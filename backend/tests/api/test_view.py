"""``GET /view`` — rebuilt graph JSON (product/03 B) + subject-lens scoping (§4.3, G10)."""

from __future__ import annotations

from chanakya.schemas import GraphView


def test_view_returns_rebuilt_graph_conforming_to_frozen_model(golden_client) -> None:
    r = golden_client.get("/view")
    assert r.status_code == 200
    body = r.json()
    # Body validates against F0's frozen GraphView (the contract the SPA also binds to).
    view = GraphView.model_validate(body)
    assert len(view.nodes) >= 1
    assert body["meta"]["node_count"] == len(view.nodes)
    # Every node is traceable (G4): ≥1 claim id.
    assert all(n.claim_ids for n in view.nodes)


def test_view_subject_lens_scopes_and_drops_distractors(hero_client) -> None:
    full = GraphView.model_validate(hero_client.get("/view").json())
    scoped = GraphView.model_validate(hero_client.get("/view", params={"subject": "lens-hq9p-pk"}).json())

    full_ids = {n.id for n in full.nodes}
    scoped_ids = {n.id for n in scoped.nodes}

    # The disconnected stale distractors (Rahwali / HQ-9B squadron) must not leak into the lens.
    assert {"site_rahwali", "unit_hq9b"} <= full_ids
    assert not ({"site_rahwali", "unit_hq9b"} & scoped_ids)
    # The hero chain + anchors survive.
    assert {"unit_paad", "site_karachi", "var_hq9p", "comp_ht233", "mfr_casic"} <= scoped_ids
    assert len(scoped_ids) < len(full_ids)
    assert scoped.meta.get("subject") == "lens-hq9p-pk"


def test_view_unknown_subject_returns_actionable_404(hero_client) -> None:
    r = hero_client.get("/view", params={"subject": "lens-does-not-exist"})
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["subject"] == "lens-does-not-exist"
    assert "lens-hq9p-pk" in detail["available_subjects"]  # tells the caller what IS valid
