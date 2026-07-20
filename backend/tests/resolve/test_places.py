"""Location-resolution acceptance tests (md/13; RESOLVE.md §8 acceptance criteria)."""

from __future__ import annotations

from typing import Any

from chanakya.resolve import resolve
from chanakya.resolve.places import resolve_place
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import PlaceEntry
from tests.resolve._helpers import entity, mk_config

# The C policy (config/resolution.yaml): a basing site snaps to a pad or a site, never a terminal.
SITE_CLASSES = {"basing_site": ["pad", "site"]}
MARKERS = [",", "~", "/", " km "]

# The gazetteer anchors these tests need (a slice of config/places.yaml).
NURKHAN = PlaceEntry(
    place_id="pl_nurkhan", canonical_name="PAF Base Nur Khan, Rawalpindi", kind="airbase",
    precision_class="site", canonical_dd=(33.61639, 73.09972), icao="OPRN",
    aliases=["PAF Base Nur Khan", "Nur Khan Airbase", "OPRN"],  # "Chaklala" WITHHELD
)
RAHWALI = PlaceEntry(
    place_id="pl_rahwali", canonical_name="Rahwali Airfield / Cantonment, Gujranwala", kind="airfield",
    precision_class="site", canonical_dd=(32.239, 74.131), aliases=["Rahwali", "Rahwali Cantonment"],
)
PORT_QASIM = PlaceEntry(
    place_id="pl_port_qasim", canonical_name="Port Muhammad Bin Qasim", kind="seaport",
    precision_class="terminal", canonical_dd=(24.767, 67.333), locode="PKBQM",
    aliases=["Port Qasim", "Bin Qasim"], distinct_from=["pl_karachi_port"],
)
KARACHI_PORT = PlaceEntry(
    place_id="pl_karachi_port", canonical_name="Port of Karachi (Keamari)", kind="seaport",
    precision_class="terminal", canonical_dd=(24.835, 66.982), locode="PKKHI",
    aliases=["Karachi Port", "Keamari"], distinct_from=["pl_port_qasim"],
)
KARACHI_AD = PlaceEntry(
    place_id="pl_karachi_ad", canonical_name="Karachi Army Air Defence site (notional, Malir area)",
    kind="sam_site", precision_class="pad", canonical_dd=(24.9012, 67.2034), aliases=["Malir AD area"],
)
RADII = {"pad": 500.0, "site": 1500.0, "terminal": 3000.0, "district": 5000.0, "city": 15000.0}

# A Nominatim geocode of the bare parent city "Karachi" — ~3.4 km from the Keamari container terminal,
# i.e. inside the terminal class's HITL multiplier. This is the RES-5 mis-snap, reproduced.
KARACHI_CITY_POINT = (24.8607, 67.0011)


def _bundle(places: list[PlaceEntry], **gates: Any) -> Any:
    return mk_config(
        places=places, proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0, **gates
    )


def _cfg(places: list[PlaceEntry], **gates: Any) -> ResolveConfig:
    return ResolveConfig.from_bundle(_bundle(places, **gates))


def _frozen_location(lat: float | None, lon: float | None, raw: str, confidence: float | None) -> dict:
    """An INGEST-frozen ``Location`` as it rides on an entity's ``coordinates`` attr."""
    candidates = []
    if lat is not None and lon is not None and confidence is not None:
        candidates = [{"lat": lat, "lon": lon, "confidence": confidence, "source": "nominatim"}]
    return {
        "raw": raw, "surface_format": "toponym", "wgs84_lat": lat, "wgs84_lon": lon,
        "geocode_candidates": candidates,
    }


# ── AC: Karachi-Port (Keamari) ≠ Port-Qasim (Bin Qasim) stays distinct (~35 km) ─────────────────

def test_two_karachi_ports_resolve_distinct() -> None:
    cfg = _cfg([PORT_QASIM, KARACHI_PORT])
    qasim = resolve_place("Port Qasim", (24.767, 67.333), cfg)
    keamari = resolve_place("Karachi Port", (24.835, 66.982), cfg)
    assert qasim.place_id == "pl_port_qasim"
    assert keamari.place_id == "pl_karachi_port"  # ~35 km ≫ terminal radius ⇒ never fused

    bundle = mk_config(places=[PORT_QASIM, KARACHI_PORT], proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0)
    part = resolve(
        [
            entity("site_qasim", "basing_site", "Port Qasim", coordinates=[24.767, 67.333], precision_class="terminal"),
            entity("site_keamari", "basing_site", "Karachi Port", coordinates=[24.835, 66.982], precision_class="terminal"),
        ],
        bundle,
    )
    pairs = {frozenset(p) for p in part.distinct_from}
    assert frozenset({"site_qasim", "site_keamari"}) in pairs
    assert part.same_as == []


# ── AC: the withheld "Chaklala" alias is EARNED via ICAO OPRN / geodesic proximity ──────────────

def test_chaklala_earned_via_icao_and_proximity() -> None:
    cfg = _cfg([NURKHAN])
    # "Chaklala" is not a seeded alias, so a bare toponym cannot resolve it (must be earned).
    assert resolve_place("Chaklala", None, cfg).place_id is None
    # Earned by ICAO OPRN co-reference …
    assert resolve_place("OPRN", None, cfg).place_id == "pl_nurkhan"
    # … or by geodesic proximity to the site (within the 1.5 km site radius).
    near = resolve_place("Chaklala", (33.617, 73.100), cfg)
    assert near.place_id == "pl_nurkhan" and near.via == "proximity"


# ── AC: DMS ≡ relative-form both resolve to one site (the corroboration unification) ────────────

def test_rahwali_two_surface_forms_resolve_to_one_site() -> None:
    cfg = _cfg([RAHWALI])
    dms = resolve_place("32°14′20″N 074°07′52″E", (32.239, 74.131), cfg)  # coord frozen by INGEST
    relative = resolve_place("Rahwali Cantonment", (32.240, 74.130), cfg)  # ~10 km NW of Gujranwala
    assert dms.place_id == "pl_rahwali"
    assert relative.place_id == "pl_rahwali"


# ── AC: bare "Karachi" (parent-city) is NOT snapped to a terminal/pad ───────────────────────────

def test_bare_karachi_is_not_snapped_to_a_terminal() -> None:
    cfg = _cfg([PORT_QASIM, KARACHI_PORT])
    # A bare parent-city toponym with no frozen coord matches no gazetteer alias ("Karachi" is
    # deliberately not an alias) ⇒ unresolved → an analyst decides (metro), never a terminal.
    assert resolve_place("Karachi", None, cfg).place_id is None
    # Even with a nearby city-ish coord it is at most a HITL candidate — NEVER auto-snapped.
    assert resolve_place("Karachi", (24.86, 67.01), cfg).band != "auto"


# ── the gazetteer is open-world: a coord far from everything mints a new place (no match) ───────

def test_unknown_place_is_not_force_snapped() -> None:
    cfg = _cfg([NURKHAN, RAHWALI])
    match = resolve_place("Somewhere Else", (10.0, 10.0), cfg)  # nowhere near the gazetteer
    assert match.place_id is None and match.band == "none"


# ── RES-5 gate (a): an air-defence site is never pulled into a port TERMINAL ────────────────────

def test_air_defence_site_is_not_pulled_into_a_port_terminal() -> None:
    places = [PORT_QASIM, KARACHI_PORT, KARACHI_AD]
    # Ungated (pre-P3.5): a bare-city geocode 3.4 km from Keamari is inside the terminal class's HITL
    # multiplier, so "Army Air Defence Centre" was pulled into a container terminal. The bug.
    ungated = resolve_place("Army Air Defence Centre", KARACHI_CITY_POINT, _cfg(places))
    assert ungated.place_id == "pl_karachi_port" and ungated.via == "proximity"

    # Gated: a basing site may take a pad or a site — a terminal is not a candidate at any distance.
    gated = resolve_place(
        "Army Air Defence Centre",
        KARACHI_CITY_POINT,
        _cfg(places, place_allowed_precision_classes=SITE_CLASSES),
        entity_type="basing_site",
    )
    assert gated.place_id is None  # matches nothing → keeps its own coord as an honest pin


def test_class_gate_leaves_the_compatible_anchor_reachable() -> None:
    """The gate removes the wrong class, not proximity matching itself (jitter absorption survives)."""
    cfg = _cfg([PORT_QASIM, KARACHI_PORT, KARACHI_AD], place_allowed_precision_classes=SITE_CLASSES)
    near_pad = resolve_place("some AD site", (24.9015, 67.2036), cfg, entity_type="basing_site")
    assert near_pad.place_id == "pl_karachi_ad" and near_pad.band == "auto"


def test_class_gate_does_not_disarm_the_two_ports_trap() -> None:
    """Both ports must still RESOLVE (by name/hard-ID) for the gazetteer's distinct_from to veto them.

    The gate is scoped to the proximity path precisely so that stated identity still lands: a document
    naming "Karachi Port" is not making an inference from distance, it is naming the place.
    """
    bundle = _bundle(
        [PORT_QASIM, KARACHI_PORT], place_allowed_precision_classes=SITE_CLASSES,
        toponym_descriptive_markers=MARKERS,
    )
    part = resolve(
        [
            entity("site_qasim", "basing_site", "Port Qasim", coordinates=[24.767, 67.333]),
            entity("site_keamari", "basing_site", "Karachi Port", coordinates=[24.835, 66.982]),
        ],
        bundle,
    )
    assert frozenset({"site_qasim", "site_keamari"}) in {frozenset(p) for p in part.distinct_from}
    assert part.same_as == []
    assert part.place_refs["site_qasim"].place_id == "pl_port_qasim"
    assert part.place_refs["site_keamari"].place_id == "pl_karachi_port"


# ── RES-5 gate (b): a vague geocode is not snapped into a precise pad ───────────────────────────

def test_low_confidence_geocode_is_not_snapped_into_a_pad() -> None:
    cfg = _cfg([KARACHI_AD], place_allowed_precision_classes=SITE_CLASSES, place_min_geocode_confidence=0.6)
    near = (24.9015, 67.2036)  # well inside the 500 m pad radius
    vague = resolve_place("central Punjab", near, cfg, entity_type="basing_site", geocode_confidence=0.2)
    assert vague.place_id is None  # a fuzzy regional point never becomes a precise pad fix

    confident = resolve_place("a site", near, cfg, entity_type="basing_site", geocode_confidence=1.0)
    assert confident.place_id == "pl_karachi_ad"

    # An UNSTATED confidence is unknown, not low — RESOLVE does not invent doubt INGEST never expressed.
    unstated = resolve_place("a site", near, cfg, entity_type="basing_site")
    assert unstated.place_id == "pl_karachi_ad"


def test_vague_geocode_stays_an_honest_pin_end_to_end() -> None:
    bundle = _bundle(
        [KARACHI_AD], place_allowed_precision_classes=SITE_CLASSES, place_min_geocode_confidence=0.6,
        toponym_descriptive_markers=MARKERS,
    )
    part = resolve(
        [
            entity(
                "site_vague", "basing_site", "fenced compound near a PAF airbase",
                coordinates=_frozen_location(24.9015, 67.2036, "central Punjab", 0.2),
            ),
        ],
        bundle,
    )
    assert part.place_refs == {}  # no ref, no merge, nothing written to the gazetteer


# ── RES-5: the toponym slot is a place NAME, not the entity's descriptive display string ────────

def test_descriptive_display_name_is_not_used_as_a_toponym() -> None:
    """A display string reciting an admin hierarchy still resolves — on its COORD, not on its name."""
    bundle = _bundle(
        [KARACHI_AD], place_allowed_precision_classes=SITE_CLASSES, toponym_descriptive_markers=MARKERS,
    )
    part = resolve(
        [
            entity(
                "site_malir", "basing_site", "Malir District, Karachi, Sindh Province, Pakistan",
                coordinates=_frozen_location(24.9012, 67.2034, "24.9012 N, 67.2034 E", 1.0),
            ),
        ],
        bundle,
    )
    ref = part.place_refs["site_malir"]
    assert ref.place_id == "pl_karachi_ad" and ref.via == "proximity" and ref.band == "auto"


# ── RES-3 (P3.4): the match is PERSISTED, with the evidence that earned it ──────────────────────

def test_place_ref_carries_the_distance_and_band_that_earned_it() -> None:
    bundle = _bundle(
        [RAHWALI, KARACHI_AD], place_allowed_precision_classes=SITE_CLASSES,
        toponym_descriptive_markers=MARKERS,
    )
    part = resolve(
        [
            entity("site_rahwali", "basing_site", "Rahwali Cantonment", coordinates=[32.2395, 74.1305]),
            entity("site_far", "basing_site", "an unnamed compound", coordinates=[10.0, 10.0]),
        ],
        bundle,
    )
    ref = part.place_refs["site_rahwali"]
    assert ref.place_id == "pl_rahwali" and ref.band == "auto"
    assert ref.distance_m is not None and ref.distance_m < RADII["site"]
    # A mention that matched no curated anchor gets NO ref — an honest pin, never an auto-minted place.
    assert "site_far" not in part.place_refs


def test_place_refs_are_keyed_by_the_post_merge_node_id() -> None:
    """Two mentions of one anchor fuse; the surviving node is the one that carries the ref."""
    bundle = _bundle(
        [RAHWALI], place_allowed_precision_classes=SITE_CLASSES, toponym_descriptive_markers=MARKERS,
    )
    part = resolve(
        [
            entity("site_a", "basing_site", "Rahwali", coordinates=[32.239, 74.131]),
            entity("site_b", "basing_site", "Rahwali Cantonment", coordinates=[32.2395, 74.1305]),
        ],
        bundle,
    )
    canonical = {part.entity_canonical.get(e, e) for e in ("site_a", "site_b")}
    assert len(canonical) == 1
    assert set(part.place_refs) == canonical
    assert next(iter(part.place_refs.values())).place_id == "pl_rahwali"


# ── P3.6: an EXACT curated-alias toponym binds without a coordinate ─────────────────────────────

def _named_only(eid: str, name: str, raw: str | None = None) -> Any:
    """A place-type mention with a display name and **no usable point** — the ``site_rawalpindi`` shape.

    ``raw`` reproduces the real corpus case: INGEST froze an MGRS grid string as a ``toponym`` surface
    form, so the canonicaliser never ran and ``wgs84_lat/lon`` stayed null. The entity therefore holds a
    ``Location`` with no coordinate at all.
    """
    if raw is None:
        return entity(eid, "basing_site", name)
    return entity(eid, "basing_site", name, coordinates=_frozen_location(None, None, raw, None))


def test_curated_alias_binds_without_a_coordinate() -> None:
    """"PAF Base Nur Khan" is a SEEDED alias — naming it is stated identity, not an inference."""
    bundle = _bundle(
        [NURKHAN, RAHWALI], place_allowed_precision_classes=SITE_CLASSES,
        toponym_descriptive_markers=MARKERS, place_bind_on_curated_toponym=True,
    )
    mgrs = "Grid: 43S CT 23715 21242 (MGRS, WGS84)"  # frozen as a `toponym`, so no point was ever derived
    part = resolve([_named_only("site_rawalpindi", "PAF Base Nur Khan", mgrs)], bundle)
    ref = part.place_refs["site_rawalpindi"]
    assert ref.place_id == "pl_nurkhan"
    assert ref.band == "auto" and ref.via == "toponym"
    assert ref.distance_m is None  # no coordinate exists to measure — the name alone carried the match


def test_curated_alias_binding_is_off_unless_configured() -> None:
    """Absent knob ⇒ pre-P3.6 behaviour: no coordinate, no hard ID, no binding (gate G2)."""
    bundle = _bundle([NURKHAN], place_allowed_precision_classes=SITE_CLASSES, toponym_descriptive_markers=MARKERS)
    part = resolve([_named_only("site_rawalpindi", "PAF Base Nur Khan")], bundle)
    assert part.place_refs == {}


def test_chaklala_is_still_unearnable_by_string_lookup() -> None:
    """The withheld earned-merge trap survives P3.6: only SEEDED forms are consulted.

    "Chaklala" / "PAF Base Chaklala" / "RAF Chaklala" are deliberately absent from ``config/places.yaml``.
    Because the new path is exact-match-against-curated-forms (no fuzzy, no substring, no proximity), a
    Chaklala-named mention with no coordinate binds to nothing — it must still be *earned* through ICAO
    ``OPRN`` co-reference or geodesic proximity, which is the whole point of withholding it.
    """
    bundle = _bundle(
        [NURKHAN], place_allowed_precision_classes=SITE_CLASSES, toponym_descriptive_markers=MARKERS,
        place_bind_on_curated_toponym=True,
    )
    part = resolve(
        [
            _named_only("site_chaklala", "Chaklala"),
            _named_only("site_paf_chaklala", "PAF Base Chaklala"),
            _named_only("site_raf_chaklala", "RAF Chaklala"),
        ],
        bundle,
    )
    assert part.place_refs == {}  # no name-only route into pl_nurkhan
    # …and the earned routes are untouched: the ICAO co-reference still lands it.
    cfg = _cfg([NURKHAN], place_bind_on_curated_toponym=True)
    assert resolve_place("Chaklala", None, cfg).place_id is None
    assert resolve_place("OPRN", None, cfg).place_id == "pl_nurkhan"


def test_vague_names_still_bind_to_nothing_without_a_coordinate() -> None:
    """A mention that does not EXACTLY state a curated form matches nothing and stays an honest pin."""
    bundle = _bundle(
        [NURKHAN, RAHWALI, KARACHI_AD, KARACHI_PORT], place_allowed_precision_classes=SITE_CLASSES,
        toponym_descriptive_markers=MARKERS, place_bind_on_curated_toponym=True,
    )
    part = resolve(
        [
            _named_only("site_sargodha", "Sargodha"),          # a town the gazetteer never curated
            _named_only("site_cpunjab", "central Punjab"),      # a region, not a place node
            _named_only("site_kad_sector", "Karachi air defence sector"),  # bare parent city + a descriptor
            _named_only("site_punjab", "Punjab"),
        ],
        bundle,
    )
    assert part.place_refs == {}


def test_curated_alias_binding_still_obeys_the_distinct_from_veto() -> None:
    """Two ports named (not measured) still resolve apart — the gazetteer veto is not bypassed."""
    bundle = _bundle(
        [PORT_QASIM, KARACHI_PORT], place_allowed_precision_classes=SITE_CLASSES,
        toponym_descriptive_markers=MARKERS, place_bind_on_curated_toponym=True,
    )
    part = resolve([_named_only("site_qasim", "Port Qasim"), _named_only("site_keamari", "Karachi Port")], bundle)
    assert part.place_refs["site_qasim"].place_id == "pl_port_qasim"
    assert part.place_refs["site_keamari"].place_id == "pl_karachi_port"
    assert frozenset({"site_qasim", "site_keamari"}) in {frozenset(p) for p in part.distinct_from}
    assert part.same_as == []


def test_no_gazetteer_means_no_place_refs() -> None:
    """The golden/empty-config path is untouched — no gazetteer, no refs, no view change (gate G2)."""
    part = resolve([entity("site_x", "basing_site", "Anywhere", coordinates=[1.0, 1.0])], mk_config())
    assert part.place_refs == {}


# ── T5: a STATED location that names a curated anchor is read, even when it is not the display name ──
#
# The map showed three pins because ten located entities never reached the gazetteer at all. Their
# display names are descriptions of things ("a fenced compound near a PAF airbase"), and the actual
# place statement lives on the frozen Location — where it was being discarded for containing a comma
# or a slash. The descriptive-marker filter is right about display strings and wrong about a
# `Location.raw`, which is a location statement by construction; an EXACT match against a name an
# analyst curated is not an inference from anything.

PUNJAB = PlaceEntry(
    place_id="pl_punjab_pk", canonical_name="Punjab province, Pakistan", kind="province",
    precision_class="province", canonical_dd=(31.1471, 72.7097),
    aliases=["Punjab", "central Punjab", "Punjab Province, Pakistan"],
)
KARACHI_METRO = PlaceEntry(
    place_id="pl_karachi_metro", canonical_name="Karachi (metropolitan area)", kind="city",
    precision_class="city", canonical_dd=(24.8607, 67.0011), aliases=["Karachi", "Karachi outskirts"],
    distinct_from=["pl_karachi_ad"],
)
ATTOCK = PlaceEntry(
    place_id="pl_attock", canonical_name="Attock Cantonment", kind="town", precision_class="city",
    canonical_dd=(33.7660, 72.3600), aliases=["Attock Cantt area", "Kala Chitta / Attock Cantt area"],
)
AREA_RADII = {**RADII, "province": 150000.0}
POINT_IDENTITY = ["pad", "site", "terminal"]


def _stated(eid: str, name: str, raw: str, *, alias: str | None = None) -> Any:
    """A mention whose display name describes a THING and whose Location states the PLACE."""
    loc = _frozen_location(None, None, raw, None)
    loc["proposed_alias"] = alias if alias is not None else raw
    return entity(eid, "basing_site", name, coordinates=loc)


def _area_bundle(places: list[PlaceEntry], **gates: Any) -> Any:
    return mk_config(
        places=places, proximity_radius_m=AREA_RADII, place_proximity_hitl_multiplier=3.0,
        place_allowed_precision_classes=SITE_CLASSES, toponym_descriptive_markers=MARKERS,
        place_bind_on_curated_toponym=True, **gates,
    )


def test_stated_location_binds_when_the_display_name_is_a_description() -> None:
    bundle = _area_bundle([PUNJAB, KARACHI_METRO, ATTOCK],
                          place_identity_precision_classes=POINT_IDENTITY)
    part = resolve(
        [
            # raw carries a comma → the descriptive filter used to throw the whole statement away
            _stated("site_node", "air defence node in vicinity of a PAF base", "Punjab Province, Pakistan"),
            _stated("site_compound", "fenced compound near a PAF airbase", "central Punjab"),
            # a relative-bearing form: INGEST froze the ANCHOR as proposed_alias; the anchor is curated
            _stated("site_depot", "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area",
                    "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area",
                    alias="Kala Chitta / Attock Cantt area"),
            # the parent-city catch-all: the display name is descriptive, the alias is the metro
            _stated("site_aadc", "Army Air Defence Centre, Karachi", "Karachi", alias="Karachi"),
        ],
        bundle,
    )
    assert part.place_refs["site_node"].place_id == "pl_punjab_pk"
    assert part.place_refs["site_compound"].place_id == "pl_punjab_pk"
    assert part.place_refs["site_depot"].place_id == "pl_attock"
    assert part.place_refs["site_aadc"].place_id == "pl_karachi_metro"
    for ref in part.place_refs.values():
        assert ref.band == "auto" and ref.via == "toponym"  # a curated NAME, never a distance guess


def test_an_uncurated_stated_location_still_binds_to_nothing() -> None:
    """The widening is exact-match only: an area the analyst never curated is still unplottable."""
    bundle = _area_bundle([PUNJAB, KARACHI_METRO], place_identity_precision_classes=POINT_IDENTITY)
    part = resolve(
        [_stated("site_cn", "garrison in China's western military district",
                 "China's western military district")],
        bundle,
    )
    assert part.place_refs == {}


# ── T5: an AREA anchor resolves, and never constitutes identity ─────────────────────────────────

def test_sharing_a_province_never_fuses_two_entities() -> None:
    """Two batteries both reported "in Punjab" are two unknowns, not one battery."""
    bundle = _area_bundle([PUNJAB], place_identity_precision_classes=POINT_IDENTITY)
    part = resolve(
        [
            _stated("site_a", "air defence node A", "Punjab Province, Pakistan"),
            _stated("site_b", "fenced compound B", "central Punjab"),
        ],
        bundle,
    )
    assert part.place_refs["site_a"].place_id == "pl_punjab_pk"  # both still RESOLVE …
    assert part.place_refs["site_b"].place_id == "pl_punjab_pk"
    assert part.same_as == [] and part.candidates == []          # … and are never fused
    assert part.entity_canonical.get("site_b", "site_b") == "site_b"


def test_two_mentions_of_one_SITE_do_still_fuse() -> None:
    """The gate is about area anchors only — a pad/site/terminal anchor still merges as it always did."""
    bundle = _area_bundle([RAHWALI], place_identity_precision_classes=POINT_IDENTITY)
    part = resolve(
        [
            entity("site_r1", "basing_site", "Rahwali", coordinates=[32.239, 74.131]),
            entity("site_r2", "basing_site", "Rahwali Cantonment", coordinates=[32.2395, 74.1312]),
        ],
        bundle,
    )
    assert {frozenset(p) for p in part.same_as} == {frozenset({"site_r1", "site_r2"})}


def test_identity_gate_absent_leaves_the_old_behaviour(  ) -> None:
    """No policy configured ⇒ unconstrained, byte-for-byte the pre-T5 path (gate G2)."""
    bundle = _area_bundle([PUNJAB])  # note: no place_identity_precision_classes
    part = resolve(
        [
            _stated("site_a", "air defence node A", "Punjab Province, Pakistan"),
            _stated("site_b", "fenced compound B", "central Punjab"),
        ],
        bundle,
    )
    assert {frozenset(p) for p in part.same_as} == {frozenset({"site_a", "site_b"})}
