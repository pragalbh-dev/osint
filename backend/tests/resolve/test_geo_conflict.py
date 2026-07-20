"""The geographic compatibility veto on entity same-as (T2 — "Karachi drawn in Gujranwala").

Why this file exists. ``merge_score`` compares names, attributes and neighbourhoods; not one of those
signals knows that Karachi and Gujranwala are ~1,060 km apart. On the frozen corpus that produced a queue
of ``same-as`` candidates between Karachi air-defence sites and *central Punjab* ones, scoring ~0.63-0.80
purely on shared wording plus one shared neighbour (every basing site of the same unit has an identical
one-edge neighbourhood, so the relational term saturates at 1.0). Nothing there is geographic.

The damage lands on the MAP: ``view/pipeline._assemble`` gives a merged node the location of whichever
of its claims came first, so fusing two sites redraws one of them at the other's coordinate — an entity
teleporting across the country, which is worse than a missing pin because it reads as knowledge.

So a stated coordinate is now a hard rail: two entities that each carry their own WGS84 point and sit
further apart than ``entity_geo_conflict_max_km`` are never merged and never even queued. Absence still
means unknown — a toponym-only mention states no point and is never vetoed by distance.
"""

from __future__ import annotations

from typing import Any

from chanakya.resolve import resolve
from chanakya.resolve.entities import Entity
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import geo_conflict_km, has_hard_conflict
from tests.resolve._helpers import entity, mk_config, triple

# Real WGS84 anchors from config/places.yaml — the two ends of the reported bug.
KARACHI_AD = (24.9012, 67.2034)  # pl_karachi_ad, Malir area, Sindh
RAHWALI = (32.239, 74.131)  # pl_rahwali, Gujranwala District, Punjab — ~1,060 km north
GEO_GATE = {"default": 100.0, "basing_site": 25.0}  # the shipped config/resolution.yaml rows


def _frozen(lat: float, lon: float, raw: str) -> dict[str, Any]:
    """An INGEST-frozen ``Location`` as it rides on an entity's ``coordinates`` attr."""
    return {
        "raw": raw,
        "surface_format": "DMS",
        "wgs84_lat": lat,
        "wgs84_lon": lon,
        "geocode_candidates": [{"lat": lat, "lon": lon, "confidence": 1.0, "source": "coord-parse"}],
    }


def _sites_sharing_one_unit(a_attrs: dict[str, Any], b_attrs: dict[str, Any]) -> list[Any]:
    """Two basing sites with near-identical wording and the SAME single neighbour.

    This is the exact shape the corpus produces: ``attribute`` high on shared wording and ``relational``
    a perfect 1.0 because each site's whole neighbourhood is one ``based-at`` edge from the same unit.
    Without the geographic rail that lands in the analyst's merge queue.

    The two edges carry *different* ``edge_instance`` keys on purpose: sharing one instance would make
    the pair co-objects of a single relocation slot, which the scorer already treats as anti-identity
    evidence. These are two separately-reported sites, which is precisely the ungated case.
    """
    return [
        entity("site_a", "basing_site", "Karachi air defence sector", **a_attrs),
        entity("site_b", "basing_site", "central Punjab air defence sector", **b_attrs),
        entity("unit_paad", "unit", "Pakistan Army Air Defence"),
        triple("unit_paad", "based-at", "site_a", edge_instance="based-at:unit_paad:a"),
        triple("unit_paad", "based-at", "site_b", edge_instance="based-at:unit_paad:b"),
    ]


# ── the regression: an entity may not teleport across the country ───────────────────────────────

def test_karachi_and_punjab_sites_are_never_merged_or_queued() -> None:
    """~1,060 km apart with both coordinates stated ⇒ vetoed outright: no merge, no review card."""
    claims = _sites_sharing_one_unit(
        {"coordinates": _frozen(*KARACHI_AD, "24.9012 N, 67.2034 E")},
        {"coordinates": _frozen(*RAHWALI, "32°14′20″N 074°07′52″E")},
    )
    part = resolve(claims, mk_config(entity_geo_conflict_max_km=GEO_GATE))
    assert part.same_as == []  # never fused — the map can never draw one at the other's point
    assert part.candidates == []  # not even a question: a geographic impossibility is not adjudicable
    assert part.entity_canonical == {}


def test_without_the_gate_the_same_pair_reaches_the_analyst() -> None:
    """The pre-fix behaviour, pinned: unset ⇒ the gate is off and the impossible pair is queued.

    This is what makes the rail load-bearing rather than decorative — the pair really does score into
    the HITL band on name + neighbourhood alone.
    """
    claims = _sites_sharing_one_unit(
        {"coordinates": _frozen(*KARACHI_AD, "24.9012 N, 67.2034 E")},
        {"coordinates": _frozen(*RAHWALI, "32°14′20″N 074°07′52″E")},
    )
    part = resolve(claims, mk_config())  # no entity_geo_conflict_max_km row at all
    queued = {frozenset(p) for p in part.candidates} | {frozenset(p) for p in part.same_as}
    assert frozenset({"site_a", "site_b"}) in queued


# ── the gate must not over-fire ─────────────────────────────────────────────────────────────────

def test_same_site_reported_twice_still_merges() -> None:
    """Two reports of one pad, ~600 m apart (coordinate jitter) — well inside the tolerance."""
    claims = _sites_sharing_one_unit(
        {"coordinates": _frozen(*RAHWALI, "32°14′20″N 074°07′52″E")},
        {"coordinates": _frozen(RAHWALI[0] + 0.005, RAHWALI[1], "32.244 N, 74.131 E")},
    )
    part = resolve(claims, mk_config(entity_geo_conflict_max_km=GEO_GATE))
    queued = {frozenset(p) for p in part.candidates} | {frozenset(p) for p in part.same_as}
    assert frozenset({"site_a", "site_b"}) in queued  # unchanged by the gate


def test_a_toponym_only_mention_is_never_vetoed_by_distance() -> None:
    """Absence is not disagreement: one side states no coordinate ⇒ unknown, so the pair stands.

    This is what keeps the veto out of the toponym-geocoding lane — it reads only points that INGEST
    already froze, and a mention that names a place without resolving it is untouched.
    """
    claims = _sites_sharing_one_unit(
        {"coordinates": _frozen(*KARACHI_AD, "24.9012 N, 67.2034 E")},
        {"coordinates": {"raw": "central Punjab", "surface_format": "toponym",
                         "wgs84_lat": None, "wgs84_lon": None, "geocode_candidates": []}},
    )
    part = resolve(claims, mk_config(entity_geo_conflict_max_km=GEO_GATE))
    queued = {frozenset(p) for p in part.candidates} | {frozenset(p) for p in part.same_as}
    assert frozenset({"site_a", "site_b"}) in queued


# ── the predicate itself ────────────────────────────────────────────────────────────────────────

def _entity(eid: str, etype: str, coords: tuple[float, float] | None) -> Entity:
    attrs = {"coordinates": _frozen(*coords, "x")} if coords else {}
    return Entity(eid=eid, etype=etype, name=eid, attrs=attrs)


def test_geo_conflict_km_reports_the_separation_and_respects_the_type_row() -> None:
    cfg = ResolveConfig.from_bundle(mk_config(entity_geo_conflict_max_km=GEO_GATE))
    a, b = _entity("a", "basing_site", KARACHI_AD), _entity("b", "basing_site", RAHWALI)
    km = geo_conflict_km(a, b, cfg)
    assert km is not None and 1000 < km < 1150  # the explanation the veto can be logged with
    # ...and the same pair typed as something the row does not cover falls back to `default` (100 km),
    # which 1,060 km still exceeds — the veto is not basing-site-only.
    assert geo_conflict_km(_entity("a", "manufacturer", KARACHI_AD),
                           _entity("b", "manufacturer", RAHWALI), cfg) is not None


def test_gate_unset_means_off() -> None:
    cfg = ResolveConfig.from_bundle(mk_config())
    assert cfg.geo_conflict_max_km("basing_site") is None
    assert geo_conflict_km(_entity("a", "basing_site", KARACHI_AD),
                           _entity("b", "basing_site", RAHWALI), cfg) is None


def test_hard_conflict_rail_sees_it_too() -> None:
    """The authoritative-coreference bootstrap reads ``has_hard_conflict`` — it must refuse this pair."""
    cfg = ResolveConfig.from_bundle(mk_config(entity_geo_conflict_max_km=GEO_GATE))
    assert has_hard_conflict(_entity("a", "basing_site", KARACHI_AD),
                             _entity("b", "basing_site", RAHWALI), cfg)
    assert not has_hard_conflict(_entity("a", "basing_site", RAHWALI),
                                 _entity("b", "basing_site", (RAHWALI[0] + 0.005, RAHWALI[1])), cfg)
