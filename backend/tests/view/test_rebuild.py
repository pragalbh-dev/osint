"""Unit tests for the rebuild orchestrator over the golden fixtures (retraction, assembly, meta)."""

from __future__ import annotations

from chanakya.view import view_to_json
from tests.fixtures import loaders


def test_golden_view_matches_expected_file() -> None:
    view = loaders.golden_view()
    assert view_to_json(view) + "\n" == loaders.expected_view_json()


def test_assembly_shapes() -> None:
    view = loaders.golden_view()
    assert {n.id for n in view.nodes} == {"unit_acme", "comp_gizmo", "mfr_foundry", "site_north", "site_south"}
    edge_ids = {e.id for e in view.edges}
    assert "e:unit_acme:fields:comp_gizmo" in edge_ids
    assert "e:mfr_foundry:supplies-component:comp_gizmo" in edge_ids
    assert len(view.events) == 1 and view.events[0].event_type == "TransferEvent"


def test_retraction_removes_phantom_node_and_edge() -> None:
    view = loaders.golden_view()
    assert not any("phantom" in n.id for n in view.nodes)
    assert not any("phantom" in e.id for e in view.edges)


def test_meta_is_deterministic_and_clockless() -> None:
    view = loaders.golden_view()
    assert view.meta == {
        "config_version": 1, "node_count": 5, "edge_count": 4, "event_count": 1, "known_gap_count": 0,
    }


def test_supersede_in_golden_view() -> None:
    view = loaders.golden_view()
    edges = {e.id: e for e in view.edges}
    assert edges["e:unit_acme:based-at:site_north"].superseded_by == "e:unit_acme:based-at:site_south"
    assert edges["e:unit_acme:based-at:site_south"].supersedes == "e:unit_acme:based-at:site_north"
