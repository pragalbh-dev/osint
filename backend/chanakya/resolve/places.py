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

from collections.abc import Mapping
from dataclasses import dataclass

from geopy.distance import geodesic

from chanakya.schemas import PlaceEntry, pair_key

from .aliases import AliasIndex
from .cluster import ResolveResult
from .entities import Entity, EntityGraph, unordered_pairs
from .geo import LOCATION_ATTRS, Coords, location_attr, parse_coords
from .normalize import normalize
from .rconfig import ResolveConfig

# ``LOCATION_ATTRS`` / ``location_attr`` / ``parse_coords`` now live in ``.geo`` (the scorer needs them
# too and cannot import this module without a cycle) and are re-exported here so every existing
# ``resolve.places`` reader keeps working unchanged.
__all__ = [
    "LOCATION_ATTRS",
    "Coords",
    "LocationMention",
    "PlaceMatch",
    "augment",
    "location_attr",
    "parse_coords",
    "place_distinct_pairs",
    "place_matches",
    "resolve_place",
]


@dataclass
class PlaceMatch:
    place_id: str | None  # None ⇒ no gazetteer match (a new/open-world place)
    band: str  # "auto" | "hitl" | "none"
    distance_m: float | None = None
    via: str = ""  # "hard-id" | "toponym" | "proximity" | ""


@dataclass(frozen=True)
class LocationMention:
    """What an entity says about *where* it is — the input side of a gazetteer match.

    Split out from the entity so the two RES-5 gates have something to gate on: the ``toponym`` is a
    place **name** (not the entity's descriptive display string), and ``geocode_confidence`` is how
    much INGEST trusted the frozen coordinate it derived. Both are read, never invented.
    """

    toponym: str
    coords: Coords | None
    geocode_confidence: float | None = None


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


def _proximity_allowed(
    place: PlaceEntry, cfg: ResolveConfig, entity_type: str | None, geocode_confidence: float | None
) -> bool:
    """May this mention be *pulled* onto this anchor by distance alone? (RES-5 — the two gates.)

    The type-scaled radii are a **jitter-absorption** mechanism: a coordinate a few hundred metres off
    is the same pad. Without a compatibility gate around it, jitter absorption becomes *garbage*
    absorption — an "Army Air Defence Centre" 4.5 km from the Port of Karachi was being pulled into a
    container terminal. Two gates keep it honest, and both are statements about the world, so both live
    in config (gate G6); an unset knob leaves the path exactly as it was.

    1. **Class compatibility** — what a given entity type may snap to (a basing site takes a pad or a
       site; never a terminal, never a whole district). No policy declared for the type ⇒ no constraint.
    2. **The mention's own geocode confidence** — a vague regional geocode ("central Punjab") must not
       be snapped into a precise pad. A candidate with *no* stated confidence is UNKNOWN, not low:
       RESOLVE does not invent doubt INGEST never expressed, and gate 1 still applies to it.

    Deliberately scoped to the *proximity* path. A hard-ID (ICAO/LOCODE) or an exact toponym/alias match
    is a statement of identity, not an inference from distance — gating those would also disarm the
    Karachi-Port ≠ Port-Qasim trap, which needs both ports to resolve before it can veto them apart.
    """
    allowed = cfg.place_allowed_precision_classes(entity_type)
    if allowed is not None and (place.precision_class or "") not in allowed:
        return False
    floor = cfg.place_min_geocode_confidence
    return floor is None or geocode_confidence is None or geocode_confidence >= floor


def resolve_place(
    toponym: str,
    coords: Coords | None,
    cfg: ResolveConfig,
    *,
    entity_type: str | None = None,
    geocode_confidence: float | None = None,
) -> PlaceMatch:
    """Match a location mention to a gazetteer node via hard-ID / toponym / geodesic proximity + bands.

    ``entity_type``/``geocode_confidence`` are the RES-5 gates on the proximity path (see
    :func:`_proximity_allowed`); omitted ⇒ ungated, i.e. exactly the pre-P3.5 behaviour.
    """
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

        # 3. geodesic proximity (the earned-merge path when the toponym is unknown) — gated (RES-5).
        if dist is not None and radius is not None and _proximity_allowed(place, cfg, entity_type, geocode_confidence):
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


def _geocode_confidence(value: object) -> float | None:
    """How much INGEST trusted the coordinate it froze — ``None`` when it recorded no opinion.

    Prefers the candidate the canonical WGS84 point was actually taken from, else the best-stated
    candidate. Read-only: RESOLVE never re-geocodes and never scores a geocode itself (gate G1).
    """
    if not isinstance(value, Mapping):
        return None
    candidates = value.get("geocode_candidates")
    if not isinstance(candidates, (list, tuple)):
        return None
    lat, lon = value.get("wgs84_lat"), value.get("wgs84_lon")
    best: float | None = None
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        stated = candidate.get("confidence")
        if stated is None:
            continue
        confidence = float(stated)
        if lat is not None and candidate.get("lat") == lat and candidate.get("lon") == lon:
            return confidence
        best = confidence if best is None else max(best, confidence)
    return best


def _reads_as_a_name(text: str, cfg: ResolveConfig) -> bool:
    """Is this string a place **name**, or a *description of where something is*? (RES-5.)

    "Rahwali airfield" names a place; "Malir District, Karachi, Sindh Province, Pakistan" recites an
    admin hierarchy and "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area" is a
    bearing-and-distance sentence. Matching the second kind against gazetteer aliases is noise at best,
    so a display string carrying a configured descriptive marker is not usable as a toponym. No markers
    configured ⇒ every name is accepted ⇒ pre-P3.5 behaviour, byte-identical (gates G2/G6).
    """
    markers = cfg.toponym_descriptive_markers
    if not markers:
        return True
    lowered = text.lower()
    return not any(marker.lower() in lowered for marker in markers)


def _toponym_of(ent: Entity, cfg: ResolveConfig) -> str:
    """The entity's **toponym slot**: an explicit frozen toponym, else a name-shaped display string,
    else INGEST's frozen ``proposed_alias``. Empty ⇒ this mention resolves on coordinates/hard-ID only.

    The order matters. ``attrs.toponym`` is the analyst/extractor stating the place name outright and
    always wins. The display name comes next because it is what the document called the thing — but only
    when it reads as a name. The proposed alias is last: it is a *proposal* INGEST made (LLM/Nominatim),
    useful when the display string is descriptive, but not something to prefer over a real name.
    """
    explicit = ent.attrs.get("toponym")
    if explicit:
        return str(explicit)
    if _reads_as_a_name(ent.name, cfg):
        return ent.name
    value = location_attr(ent.attrs)
    proposed = value.get("proposed_alias") if isinstance(value, Mapping) else None
    if proposed and _reads_as_a_name(str(proposed), cfg):
        return str(proposed)
    return ""


def _names_a_curated_anchor(toponym: str, cfg: ResolveConfig) -> bool:
    """Is this string, exactly, a **curated** ``canonical_name``/alias in ``config/places.yaml``? (P3.6.)

    Exact only — the same normalised-equality test the toponym path itself uses (:func:`_toponym_matches`):
    no fuzzy scoring, no substring/containment, no proximity. "PAF Base Nur Khan" is a seeded alias of
    ``pl_nurkhan`` and binds; "Sargodha", "central Punjab" and "Karachi air defence sector" name no
    curated anchor and bind to nothing, staying honest un-anchored pins. Because only **seeded** forms
    are consulted, the deliberately withheld earned-merge traps ("Chaklala" / "PAF Base Chaklala" /
    "RAF Chaklala"; Rahwali's relative-bearing form) remain unearnable by string lookup — they must
    still be earned through ICAO co-reference or geodesic proximity.
    """
    return bool(toponym) and any(_toponym_matches(toponym, place, cfg) for place in cfg.places.places)


def _location_of(ent: Entity, cfg: ResolveConfig) -> LocationMention | None:
    """Extract the location mention from an entity that can be placed at all; None if it cannot.

    An entity qualifies on any of three grounds: a frozen coordinate, a hard ID (ICAO/LOCODE), or —
    when the policy is enabled (:attr:`ResolveConfig.place_bind_on_curated_toponym`) — a toponym that
    exactly states a curated anchor's name. The third is *stated* identity, not an inference from
    distance, which is why it needs no coordinate to stand on: an analyst-curated name is evidence in
    its own right. It still passes through :func:`resolve_place`, so the gazetteer's ``distinct_from``
    veto (computed over the same match map) applies to it exactly as it does to every other match.
    """
    value = location_attr(ent.attrs)
    coords = parse_coords(value)
    icao = ent.attrs.get("icao") or ent.attrs.get("locode")
    toponym = str(icao) if (icao and not coords) else _toponym_of(ent, cfg)
    named = cfg.place_bind_on_curated_toponym and _names_a_curated_anchor(toponym, cfg)
    if coords is None and not icao and not named:
        return None  # nothing to resolve against the gazetteer
    return LocationMention(toponym=toponym, coords=coords, geocode_confidence=_geocode_confidence(value))


def place_matches(graph: EntityGraph, cfg: ResolveConfig) -> dict[str, PlaceMatch]:
    """Resolve every place-type entity that carries a location to a **curated** gazetteer anchor.

    The one place-resolution pass: its result feeds the distinct-from veto, the place-merge augment, and
    (P3.4) the ``Partition.place_refs`` write-back, so all three agree by construction. Entities that
    match no anchor are simply absent — they keep their own coordinate and stand as honest pins; nothing
    is ever minted into ``config/places.yaml`` (D-P3.3, analyst promotion only).
    """
    place_types = cfg.place_entity_types
    out: dict[str, PlaceMatch] = {}
    for eid, ent in sorted(graph.entities.items()):
        if ent.etype not in place_types:
            continue  # only entities whose identity IS a place participate in place resolution
        loc = _location_of(ent, cfg)
        if loc is None:
            continue
        match = resolve_place(
            loc.toponym, loc.coords, cfg, entity_type=ent.etype, geocode_confidence=loc.geocode_confidence
        )
        if match.place_id is not None:
            out[eid] = match
    return out


def place_distinct_pairs(
    graph: EntityGraph, cfg: ResolveConfig, place_of: dict[str, PlaceMatch] | None = None
) -> set[frozenset[str]]:
    """Entity pairs whose gazetteer places are mutually ``distinct_from`` → a **hard veto**.

    Computed BEFORE ``resolve_entities`` so the Karachi-Port ≠ Port-Qasim trap vetoes an *entity*-level
    merge too (two ports that share a shipping neighbourhood must still never fuse), not merely surface
    as an edge afterwards. Folded into the veto set, so it also blocks transitive fusion in ``finalise``.
    """
    if not cfg.places.places or not cfg.scorable:
        return set()
    distinct_places = _distinct_place_pairs(cfg)
    if place_of is None:
        place_of = place_matches(graph, cfg)
    out: set[frozenset[str]] = set()
    for a, b in unordered_pairs(sorted(place_of)):
        if frozenset((place_of[a].place_id, place_of[b].place_id)) in distinct_places:
            out.add(frozenset((a, b)))
    return out


def augment(
    result: ResolveResult,
    graph: EntityGraph,
    cfg: ResolveConfig,
    alias_idx: AliasIndex,
    veto: set[frozenset[str]],
    place_of: dict[str, PlaceMatch] | None = None,
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

    if place_of is None:
        place_of = place_matches(graph, cfg)
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
