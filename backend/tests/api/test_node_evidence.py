"""``GET /node/{id}`` (product/03 B) + ``GET /evidence/{id}`` (product/03 C: the provenance drawer)."""

from __future__ import annotations

from chanakya.schemas import NodeView, ProvenanceDrawer


def test_node_inspector_returns_frozen_nodeview(hero_client) -> None:
    r = hero_client.get("/node/comp_ht233")
    assert r.status_code == 200
    node = NodeView.model_validate(r.json())
    assert node.id == "comp_ht233" and node.type == "component"
    # The load-bearing case: HT-233 is a CANDIDATE chokepoint, never a confirmed sole-source.
    assert node.materiality is not None
    assert node.materiality.chokepoint_status == "candidate"
    assert node.materiality.substitutability_state == "UNKNOWN"


def test_node_unknown_id_actionable_404(hero_client) -> None:
    r = hero_client.get("/node/nope")
    assert r.status_code == 404
    assert r.json()["detail"]["id"] == "nope"


def test_evidence_drawer_independence_clusters_and_claim_to_docref(hero_client) -> None:
    # unit_paad is backed by two claims from different origins (imagery + official statement).
    r = hero_client.get("/evidence/unit_paad")
    assert r.status_code == 200
    drawer = ProvenanceDrawer.model_validate(r.json())

    assert drawer.subject_ref == "unit_paad"
    assert drawer.clusters, "drawer must carry independence-grouped clusters"
    clustered_ids = {cid for grp in drawer.clusters for cid in grp.claim_ids}
    assert {"d02-l3", "d17-img1"} <= clustered_ids

    # One-click-to-source: every clustered claim resolves to a full atom carrying its exact doc_ref.
    resolved = {c.claim_id: c for c in drawer.claims}
    assert clustered_ids <= set(resolved)
    for cid in clustered_ids:
        atom = resolved[cid]
        refs = atom.doc_refs()
        assert refs and refs[0].file  # a real file + locator to jump to
        # observed-vs-inferred is a first-class field on the atom, not inferred.
        assert atom.kind in {"observation", "inference", "retraction"}


def test_routes_match_ids_containing_slashes(hero_client) -> None:
    # Extraction mints descriptive ids that can contain "/" ("…Kala Chitta / Attock Cantt area").
    # %2F is decoded before routing, so a single-segment path param would 404 at the ROUTER —
    # the contract is that the handler sees the full id and answers, here with its structured 404.
    slash_id = "ent:basing_site:somewhere / nowhere area"
    r = hero_client.get(f"/evidence/{slash_id}")
    assert r.status_code == 404
    assert r.json()["detail"]["id"] == slash_id

    r = hero_client.get(f"/node/{slash_id}")
    assert r.status_code == 404
    assert r.json()["detail"]["id"] == slash_id


def test_evidence_works_for_edges_too(hero_client) -> None:
    # Edges are assessed elements as well — the drawer resolves them by id.
    edge_id = "e:comp_ht233:equips:var_hq9p"
    r = hero_client.get(f"/evidence/{edge_id}")
    assert r.status_code == 200
    drawer = ProvenanceDrawer.model_validate(r.json())
    assert drawer.subject_ref == edge_id
    assert drawer.claims  # the equips inference cites at least one claim


def test_evidence_names_the_registry_entry_behind_every_cited_source(hero_client) -> None:
    """"Who says so?" — a source id is an internal key, not an attribution.

    The drawer renders a source by CLASS + reliability grade, and those live only in
    ``config/sources.yaml``. Until now no GET route exposed them, so the UI had nothing to show but
    ``d17b_withheld_gap`` — a filename presented to an analyst as if it were a publisher.
    """
    drawer = ProvenanceDrawer.model_validate(hero_client.get("/evidence/unit_paad").json())
    cited = {c.source_id for c in drawer.claims}
    assert cited, "fixture must cite at least one source"
    # Only cited ids appear, and each entry is keyed by its own id — no invented attribution.
    assert set(drawer.sources) <= cited
    assert all(sid == entry.source_id for sid, entry in drawer.sources.items())
    assert "src-imagery-2024" in drawer.sources
    assert drawer.sources["src-imagery-2024"].source_type == "satellite"
    assert drawer.sources["src-imagery-2024"].reliability_grade == "B"


def test_evidence_omits_a_source_the_registry_does_not_know(hero_client, hero_state) -> None:
    """An unregistered source is ABSENT, never described — the UI then shows the bare id."""
    hero_state.config.set_section("sources", {"sources": []})
    drawer = ProvenanceDrawer.model_validate(hero_client.get("/evidence/unit_paad").json())
    assert drawer.claims  # still one-click-to-source
    assert drawer.sources == {}


def test_evidence_unknown_id_actionable_404(hero_client) -> None:
    r = hero_client.get("/evidence/ghost")
    assert r.status_code == 404
    assert r.json()["detail"]["id"] == "ghost"
