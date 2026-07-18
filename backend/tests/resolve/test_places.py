"""Location-resolution acceptance tests (md/13; RESOLVE.md §8 acceptance criteria)."""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.places import resolve_place
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import PlaceEntry
from tests.resolve._helpers import entity, mk_config

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
RADII = {"pad": 500.0, "site": 1500.0, "terminal": 3000.0, "district": 5000.0, "city": 15000.0}


def _cfg(places: list[PlaceEntry]) -> ResolveConfig:
    return ResolveConfig.from_bundle(
        mk_config(places=places, proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0)
    )


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
