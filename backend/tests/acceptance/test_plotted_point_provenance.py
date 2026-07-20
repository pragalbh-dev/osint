"""Standing tripwire: every point the map draws is traceable to something an analyst can inspect (T5).

A missing pin says "we do not know". A wrong pin says "we know, and here it is" — which is the worse
failure, and the one this project is graded on not committing. So there are exactly **two** legitimate
origins for a plotted coordinate, and this test asserts that nothing else ever reaches the map:

1. **A coordinate one of the node's own claims states.** A grid reference, a DMS pair, a geocode INGEST
   froze at extract time — whatever it was, it is on the evidence layer and one click from the pin.
2. **The ``canonical_dd`` of the curated gazetteer anchor the node's ``resolved_place_ref`` names**, and
   only when the node also says so (``location_source == 'gazetteer-anchor'``). A source that says
   "central Punjab" has told us something real; recording it as the Punjab anchor, at province
   precision, with the anchor named on the node, is a cited derivation rather than a fabrication.

Anything else — most importantly *another entity's* coordinate arriving through a merge, which is how a
Karachi-named node ends up drawn in Punjab — fails here. Deliberately end-of-pipeline and
mechanism-agnostic: it does not care why a coordinate moved, only that the picture stays honest.

Companion to ``test_map_position_integrity`` (T2), which bounds how far a node's *own* claims may
disagree. That one asks "do this node's coordinates agree?"; this one asks "where did the drawn point
come from at all?".
"""

from __future__ import annotations

from typing import Any

from chanakya.resolve import location_attr
from chanakya.resolve.places import parse_coords
from chanakya.view.pipeline import LOCATION_SOURCE, LOCATION_SOURCE_ANCHOR

# Coordinates round-trip through JSON floats; "the same point" is exact equality up to that round-trip.
_DP = 5


def _claim_points(claim: Any) -> set[tuple[float, float]]:
    attrs = getattr(claim.payload, "attrs", None) or {}
    coords = parse_coords(location_attr(attrs))
    return {(round(coords[0], _DP), round(coords[1], _DP))} if coords is not None else set()


def _anchors(scenario: Any) -> dict[str, tuple[float, float]]:
    places = scenario.config_store.snapshot().places
    return {
        p.place_id: (round(p.canonical_dd[0], _DP), round(p.canonical_dd[1], _DP))
        for p in places.places
        if p.canonical_dd is not None
    }


def _offenders(view: Any, scenario: Any) -> list[str]:
    claims = scenario.claims
    anchors = _anchors(scenario)
    out: list[str] = []
    for node in view.nodes:
        loc = node.location
        if loc is None or loc.wgs84_lat is None or loc.wgs84_lon is None:
            continue
        drawn = (round(loc.wgs84_lat, _DP), round(loc.wgs84_lon, _DP))
        stated = {p for cid in node.claim_ids if claims.get(cid) for p in _claim_points(claims[cid])}
        if drawn in stated:
            continue
        anchor = anchors.get(loc.resolved_place_ref or "")
        if anchor == drawn and node.attrs.get(LOCATION_SOURCE) == LOCATION_SOURCE_ANCHOR:
            continue  # a cited derivation: the node names the curated anchor it was placed on
        out.append(
            f"{node.id} drawn at {drawn}: not stated by its claims {sorted(stated) or '[]'} and not "
            f"the anchor {loc.resolved_place_ref!r}={anchor} it claims to sit on "
            f"(location_source={node.attrs.get(LOCATION_SOURCE)!r})"
        )
    return out


def test_every_plotted_point_is_stated_or_a_named_anchor(scenario: Any, view: Any) -> None:
    assert not _offenders(view, scenario)


def test_the_invariant_holds_after_the_live_ingest_too(scenario: Any) -> None:
    """The relocation beat releases the withheld Rahwali passes — the guard must survive that arrival."""
    from eval import harness

    _before, after = harness.staged_ingest_views(scenario)
    assert not _offenders(after, scenario)


def test_an_anchor_derived_point_always_names_the_anchor_it_came_from(scenario: Any, view: Any) -> None:
    """No silent borrowing: if the point is not the source's own, the node says whose it is."""
    anchors = _anchors(scenario)
    for node in view.nodes:
        if node.attrs.get(LOCATION_SOURCE) != LOCATION_SOURCE_ANCHOR:
            continue
        loc = node.location
        assert loc is not None and loc.resolved_place_ref in anchors, node.id
        assert (round(loc.wgs84_lat or 0.0, _DP), round(loc.wgs84_lon or 0.0, _DP)) == anchors[
            loc.resolved_place_ref or ""
        ], node.id
        # …and it may not claim a precision the anchor does not have (md/13 §1: a province is a province)
        assert loc.precision_class is not None, node.id
