"""Standing tripwire: nothing the map draws may sit somewhere its own evidence does not put it (T2).

The reported symptom was "Karachi appears as a node in Gujranwala" — an entity rendered ~1,000 km from
where its sources place it. That is a *worse* failure than an empty map: a missing pin says "we do not
know", a wrong pin says "we know, and here it is". It is also silent — nothing in the pipeline notices,
because ``view/pipeline._assemble`` simply takes the first claim's location for a node and the frontend
plots whatever the node carries (``viewToPins`` in ``frontend/src/api/adapters.ts``).

The single way a node can acquire a foreign coordinate is a merge that fused two entities which are not
in the same place. So this test asserts the invariant on the finished view, over the real frozen corpus:

    for every node the map would plot, every coordinate its own claims assert is the SAME place.

It is deliberately end-of-pipeline and mechanism-agnostic — it does not care *why* a coordinate moved
(bad resolver gate, bad merge card, bad extraction), only that the picture stays honest. The upstream
rail that prevents it is ``resolve.scoring.geo_conflict_km`` (see ``tests/resolve/test_geo_conflict.py``).
"""

from __future__ import annotations

from typing import Any

from geopy.distance import geodesic

from chanakya.resolve import location_attr
from chanakya.resolve.geo import parse_coords

# The tolerance is the shipped basing-site row of ``entity_geo_conflict_max_km``: two reports of one
# site may disagree by jitter, never by a city. Read from config so this test cannot drift from the gate.
FALLBACK_MAX_KM = 25.0


def _tolerance(scenario: Any) -> float:
    resolution = scenario.config_store.snapshot().resolution
    rows = getattr(resolution, "entity_geo_conflict_max_km", None) or {}
    return float(rows.get("basing_site", rows.get("default", FALLBACK_MAX_KM)))


def _claim_points(claim: Any) -> list[tuple[float, float]]:
    attrs = getattr(claim.payload, "attrs", None) or {}
    coords = parse_coords(location_attr(attrs))
    return [coords] if coords is not None else []


def test_no_node_is_drawn_away_from_its_own_evidence(scenario: Any, view: Any) -> None:
    """Every plotted node's claims agree on one place — no entity teleports across the country."""
    max_km = _tolerance(scenario)
    claims = scenario.claims
    offenders = []
    for node in view.nodes:
        points = [p for cid in node.claim_ids if cid in claims for p in _claim_points(claims[cid])]
        distinct = sorted({(round(lat, 5), round(lon, 5)) for lat, lon in points})
        if len(distinct) < 2:
            continue
        spread = max(geodesic(a, b).km for a in distinct for b in distinct)
        if spread > max_km:
            offenders.append((node.id, node.name, round(spread, 1), distinct))
    assert not offenders, (
        "node(s) carry mutually-incompatible coordinates — one of the places is being drawn at the "
        f"other's position (tolerance {max_km} km): {offenders}"
    )


def test_every_plotted_node_sits_on_a_coordinate_it_can_account_for(scenario: Any, view: Any) -> None:
    """The pin is not merely *plausible* — the node can name where the point came from.

    AMENDED at integration (orchestrator adjudication, 2026-07-20). The original form required the drawn
    point to equal a coordinate one of the node's OWN claims states. That was too strong: it forbids
    *any* gazetteer derivation however well cited, which outlaws the location-normalisation design in
    ``artifacts/md/13`` — where a stated toponym ("Sindh province") is resolved against an
    analyst-curated anchor precisely because no claim carries a coordinate. T5's toponym geocoding made
    that fire on the real corpus, so the invariant — not the code — was the thing that was wrong.

    A plotted coordinate must therefore be either
      (a) a point one of the node's own claims states, **or**
      (b) exactly the ``canonical_dd`` of the curated anchor named in ``location.resolved_place_ref``,
          and only when the node stamps ``location_source == 'gazetteer-anchor'``.

    This still closes the teleport this file exists to catch — *another entity's* coordinate is neither
    (a) nor (b). ``test_plotted_point_provenance.py`` asks the complementary question ("where did the
    drawn point come from at all?"); both files are kept deliberately.
    """
    claims = scenario.claims
    anchors = {
        p.place_id: (round(p.canonical_dd[0], 5), round(p.canonical_dd[1], 5))
        for p in scenario.config_store.snapshot().places.places
        if p.canonical_dd is not None
    }
    for node in view.nodes:
        loc = node.location
        if loc is None or loc.wgs84_lat is None or loc.wgs84_lon is None:
            continue
        drawn = (round(loc.wgs84_lat, 5), round(loc.wgs84_lon, 5))
        stated = {
            (round(lat, 5), round(lon, 5))
            for cid in node.claim_ids
            if claims.get(cid)
            for lat, lon in _claim_points(claims[cid])
        }
        if drawn in stated:
            continue
        # (b) — a cited derivation from a curated anchor the node itself names.
        source = (getattr(node, "attrs", None) or {}).get("location_source")
        anchor = anchors.get(loc.resolved_place_ref or "")
        assert source == "gazetteer-anchor" and anchor == drawn, (
            f"{node.id} is plotted at {drawn}, which neither its own claims assert "
            f"({sorted(stated) or 'none'}) nor matches the curated anchor it names "
            f"(resolved_place_ref={loc.resolved_place_ref!r}={anchor}, location_source={source!r})"
        )


def test_the_invariant_holds_after_the_live_ingest_too(scenario: Any) -> None:
    """The relocation beat releases the withheld Rahwali passes — the guard must survive that arrival."""
    from eval import harness

    _before, after = harness.staged_ingest_views(scenario)
    max_km = _tolerance(scenario)
    claims = scenario.claims
    for node in after.nodes:
        points = [p for cid in node.claim_ids if cid in claims for p in _claim_points(claims[cid])]
        distinct = sorted({(round(lat, 5), round(lon, 5)) for lat, lon in points})
        if len(distinct) < 2:
            continue
        spread = max(geodesic(a, b).km for a in distinct for b in distinct)
        assert spread <= max_km, f"{node.id} spans {spread:.1f} km after the live ingest: {distinct}"
