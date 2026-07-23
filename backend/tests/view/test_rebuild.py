"""Unit tests for the rebuild orchestrator over the golden fixtures (retraction, assembly, meta)."""

from __future__ import annotations

import pytest

from chanakya.view import view_to_json
from tests.fixtures import loaders


@pytest.mark.xfail(
    strict=True,
    reason="expected_view.json pending regeneration: temporal history now SURFACED on the wire "
    "(target output, previously exclude=True) — data-refresh ledger §A.",
)
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
    # known_gap_count == 1: with the SCORE stages live, materiality flags comp_gizmo a *candidate*
    # chokepoint (sole-source in-degree, substitutability UNKNOWN) → a first-class Known Gap.
    # edge_count == 5: the 4 asserted edges + the DRAWN `supersedes` edge the promoted relocation
    # renders between the two basing sites (D-P4.11).
    assert view.meta == {
        "config_version": 1, "node_count": 5, "edge_count": 5, "event_count": 1, "known_gap_count": 1,
    }


def test_supersede_in_golden_view() -> None:
    view = loaders.golden_view()
    edges = {e.id: e for e in view.edges}
    old = edges["e:unit_acme:based-at:site_north"]
    assert old.superseded_by == "e:unit_acme:based-at:site_south"
    assert edges["e:unit_acme:based-at:site_south"].supersedes == "e:unit_acme:based-at:site_north"
    # The consequence the demo turns on: the retired position reads *history* (stale), not an evidence gap.
    assert old.status == "stale"
    # ...and the relocation is visible as its own edge, citing the claims on BOTH sides of the move.
    drawn = edges["e:site_south:supersedes:site_north"]
    assert drawn.type == "supersedes" and set(drawn.claim_ids) == {"d17-l1", "d19-l1"}
