"""Location resolution — the **same** machinery over the gazetteer, not a new subsystem (md/13, RESOLVE §8).

Coord-canonicalisation + geocoding are INGEST's (frozen onto the claim); RESOLVE **consumes** the frozen
WGS84 coords + toponyms and matches them to ``config/places.yaml`` nodes by *toponym/alias/hard-ID match +
geodesic proximity* (per-``precision_class`` radii) through the same auto/HITL/keep-separate bands. Pure +
offline — ``geopy.distance.geodesic`` is math, no network (gate G1). The gazetteer is an **open-world**
prior: a coord beyond ``multiplier × radius`` of everything mints a *new* place, it is never force-snapped.

Traps handled: Karachi-Port ≠ Port-Qasim (~35 km + mutual ``distinct_from``); bare "Karachi" (parent-city,
matches no node → HITL, never snapped to a terminal/pad); the **earned** "Chaklala" → ``pl_nurkhan`` via
ICAO ``OPRN`` co-reference or geodesic proximity, even though the alias is withheld from the seed.
"""

from __future__ import annotations

from dataclasses import dataclass

from geopy.distance import geodesic

from chanakya.schemas import PlaceEntry, pair_key

from .aliases import AliasIndex
from .cluster import ResolveResult
from .entities import Entity, EntityGraph, unordered_pairs
from .normalize import normalize
from .rconfig import ResolveConfig

Coords = tuple[float, float]


@dataclass
class PlaceMatch:
    place_id: str | None  # None ⇒ no gazetteer match (a new/open-world place)
    band: str  # "auto" | "hitl" | "none"
    distance_m: float | None = None
    via: str = ""  # "hard-id" | "toponym" | "proximity" | ""


def parse_coords(value: object) -> Coords | None:
    """Read a frozen WGS84 coord from an attr: (lat, lon) tuple/list, or a dict with wgs84_lat/lon."""
    if isinstance(value, (list, tuple)):
        try:
            lat, lon = value
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None
    if isinstance(value, dict):
        lat, lon = value.get("wgs84_lat", value.get("lat")), value.get("wgs84_lon", value.get("lon"))
        if lat is not None and lon is not None:
            try:
                return float(lat), float(lon)
            except (TypeError, ValueError):
                return None
    return None


def _toponym_matches(toponym: str, place: PlaceEntry, cfg: ResolveConfig) -> bool:
    n = normalize(toponym, cfg.transliteration)
    if not n:
        return False
    forms = [place.canonical_name, *place.aliases]
    return any(normalize(f, cfg.transliteration) == n for f in forms)


def _hard_id_matches(toponym: str, place: PlaceEntry, cfg: ResolveConfig) -> bool:
    n = normalize(toponym, cfg.transliteration)
    return bool((place.icao and normalize(place.icao, cfg.transliteration) == n)
                or (place.locode and normalize(place.locode, cfg.transliteration) == n))


def resolve_place(toponym: str, coords: Coords | None, cfg: ResolveConfig) -> PlaceMatch:
    """Match a location mention to a gazetteer node via hard-ID / toponym / geodesic proximity + bands."""
    best: PlaceMatch = PlaceMatch(place_id=None, band="none")
    for place in cfg.places.places:
        radius = cfg.proximity_radius_m(place.precision_class or "") if place.precision_class else None
        dist = None
        if coords is not None and place.canonical_dd is not None:
            dist = geodesic(coords, tuple(place.canonical_dd)).meters

        # 1. a unique hard-ID (ICAO/LOCODE) is decisive — earns even a withheld toponym (Chaklala→OPRN).
        if _hard_id_matches(toponym, place, cfg):
            return PlaceMatch(place.place_id, "auto", dist, "hard-id")

        # 2. toponym/alias match: auto if no coord contradicts, else fall through to proximity.
        if _toponym_matches(toponym, place, cfg):
            if dist is None or (radius is not None and dist <= radius):
                return PlaceMatch(place.place_id, "auto", dist, "toponym")

        # 3. geodesic proximity (the earned-merge path when the toponym is unknown).
        if dist is not None and radius is not None:
            mult = cfg.place_hitl_multiplier
            if dist <= radius:
                cand = PlaceMatch(place.place_id, "auto", dist, "proximity")
            elif mult is not None and dist <= radius * mult:
                cand = PlaceMatch(place.place_id, "hitl", dist, "proximity")
            else:
                cand = PlaceMatch(None, "none", dist, "")
            if cand.place_id is not None and (best.distance_m is None or (cand.distance_m or 0) < best.distance_m):
                best = cand
    return best


def _location_of(ent: Entity) -> tuple[str, Coords | None] | None:
    """Extract (toponym, coords) from an entity that carries a frozen location; None if it has none."""
    coords = parse_coords(ent.attrs.get("coordinates") or ent.attrs.get("wgs84") or ent.attrs.get("location"))
    toponym = str(ent.attrs.get("toponym") or ent.name)
    icao = ent.attrs.get("icao") or ent.attrs.get("locode")
    if coords is None and not icao:
        return None  # nothing to resolve against the gazetteer
    return (str(icao) if (icao and not coords) else toponym), coords


def _place_of(graph: EntityGraph, cfg: ResolveConfig) -> dict[str, PlaceMatch]:
    """Resolve every place-type entity that carries a location to a gazetteer node (place_id + band)."""
    place_types = cfg.place_entity_types
    out: dict[str, PlaceMatch] = {}
    for eid, ent in sorted(graph.entities.items()):
        if ent.etype not in place_types:
            continue  # only entities whose identity IS a place participate in place resolution
        loc = _location_of(ent)
        if loc is None:
            continue
        match = resolve_place(loc[0], loc[1], cfg)
        if match.place_id is not None:
            out[eid] = match
    return out


def place_distinct_pairs(graph: EntityGraph, cfg: ResolveConfig) -> set[frozenset[str]]:
    """Entity pairs whose gazetteer places are mutually ``distinct_from`` → a **hard veto**.

    Computed BEFORE ``resolve_entities`` so the Karachi-Port ≠ Port-Qasim trap vetoes an *entity*-level
    merge too (two ports that share a shipping neighbourhood must still never fuse), not merely surface
    as an edge afterwards. Folded into the veto set, so it also blocks transitive fusion in ``finalise``.
    """
    if not cfg.places.places or not cfg.scorable:
        return set()
    distinct_places = _distinct_place_pairs(cfg)
    place_of = _place_of(graph, cfg)
    out: set[frozenset[str]] = set()
    for a, b in unordered_pairs(sorted(place_of)):
        if frozenset((place_of[a].place_id, place_of[b].place_id)) in distinct_places:
            out.add(frozenset((a, b)))
    return out


def augment(
    result: ResolveResult, graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, veto: set[frozenset[str]]
) -> None:
    """Fuse **place-type** mentions of one gazetteer node; emit same_as / candidates (not distinct).

    Location resolution is about PLACE identity: two place-type mentions of one gazetteer node are the
    same place. It never fuses a non-place entity (a unit is *located at* a base, it is not the base),
    never fuses two distinct co-located assets (different types), and **honours the veto + learned
    ``barred``** (co-location ≠ identity — a confident wrong merge corrupts the ORBAT, spine/03). The
    gazetteer ``distinct_from`` trap is enforced upstream as a hard veto (:func:`place_distinct_pairs`),
    so it is not re-emitted here. Raw pairs only; ``finalise`` builds the flat canonical map. No-op when
    the gazetteer is empty (F0's golden config) → golden unchanged (gate G2).
    """
    if not cfg.places.places or not cfg.scorable:
        return

    place_of = _place_of(graph, cfg)
    trans = cfg.transliteration

    def barred(a: str, b: str) -> bool:
        return frozenset((a, b)) in veto or alias_idx.barred(
            normalize(graph.entities[a].name, trans), normalize(graph.entities[b].name, trans)
        )

    for a, b in unordered_pairs(sorted(place_of)):
        ma, mb = place_of[a], place_of[b]
        key = pair_key(a, b)
        if ma.place_id != mb.place_id or graph.entities[a].etype != graph.entities[b].etype or barred(a, b):
            continue  # different places / different types / vetoed apart → not a place merge
        if ma.band == "auto" and mb.band == "auto":
            result.same_as.append((a, b))  # two mentions of one place (Rahwali DMS ≡ relative form)
            result.merge_confidence[key] = 1.0
            result.merge_breakdown[key] = {"place": 1.0, "total": 1.0}
        elif "hitl" in (ma.band, mb.band):
            result.candidates.append((a, b))
            result.merge_confidence[key] = cfg.hitl_low
            result.merge_breakdown[key] = {"place": cfg.hitl_low, "total": cfg.hitl_low}


def _distinct_place_pairs(cfg: ResolveConfig) -> set[frozenset[str]]:
    out: set[frozenset[str]] = set()
    for place in cfg.places.places:
        for other in place.distinct_from:
            out.add(frozenset((place.place_id, other)))
    return out
