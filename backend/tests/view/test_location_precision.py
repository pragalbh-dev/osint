"""How a node gets a point on the map, and how honestly it is described (T5; md/13 §1).

Three separate questions, tested separately because they can each fail on their own:

1. **Coverage** — a stated toponym that names a curated anchor ends up with a coordinate. Before T5
   ten of the twelve located entities in the corpus carried none, so the map drew three pins.
2. **Precision** — the class the node claims is the finer of what the surface form pinned and what
   the anchor is known to, and the uncertainty radius that goes with it comes from config, never a
   literal. Drawing "central Punjab" as a pad-sharp dot is the fabrication this system may not commit.
3. **Refusal** — a place the gazetteer does not know stays unplotted. "Insufficient evidence to
   place" is a legitimate output; a nudged-to-the-nearest-number coordinate is not.
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    PlaceEntry,
    ResolvedRef,
)
from chanakya.view.pipeline import (
    LOCATION_SOURCE,
    LOCATION_SOURCE_ANCHOR,
    LOCATION_SOURCE_STATED,
    LOCATION_UNCERTAINTY_RADIUS_M,
    rebuild,
)
from tests.resolve._helpers import mk_config

RADII = {"pad": 500.0, "site": 1500.0, "terminal": 3000.0, "district": 5000.0,
         "city": 15000.0, "province": 150000.0}
MARKERS = [",", "~", "/", " km "]

NURKHAN = PlaceEntry(
    place_id="pl_nurkhan", canonical_name="PAF Base Nur Khan, Rawalpindi", kind="airbase",
    precision_class="site", canonical_dd=(33.61639, 73.09972), icao="OPRN",
    aliases=["PAF Base Nur Khan"],
)
PUNJAB = PlaceEntry(
    place_id="pl_punjab_pk", canonical_name="Punjab province, Pakistan", kind="province",
    precision_class="province", canonical_dd=(31.1471, 72.7097), aliases=["central Punjab"],
)
KARACHI_AD = PlaceEntry(
    place_id="pl_karachi_ad", canonical_name="Karachi Army Air Defence site", kind="sam_site",
    precision_class="pad", canonical_dd=(24.9012, 67.2034), aliases=["Malir AD area"],
)


class _Log:
    def __init__(self, rows: list[ClaimRecord]) -> None:
        self._rows = rows

    def replay(self) -> list[ClaimRecord]:
        return list(self._rows)


_n = {"i": 0}


def _entity(eid: str, name: str, **attrs: Any) -> ClaimRecord:
    _n["i"] += 1
    return ClaimRecord(
        claim_id=f"c{_n['i']}",
        source_id="src-t",
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name=name, attrs=attrs),
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def _loc(raw: str, *, lat: float | None = None, lon: float | None = None,
         precision: str | None = None, alias: str | None = None) -> dict[str, Any]:
    return {"raw": raw, "surface_format": "toponym", "wgs84_lat": lat, "wgs84_lon": lon,
            "precision_class": precision, "proposed_alias": alias or raw, "geocode_candidates": []}


def _config(places: list[PlaceEntry]) -> Any:
    return mk_config(
        places=places, proximity_radius_m=RADII, place_proximity_hitl_multiplier=3.0,
        place_allowed_precision_classes={"basing_site": ["pad", "site"]},
        toponym_descriptive_markers=MARKERS, place_bind_on_curated_toponym=True,
        place_identity_precision_classes=["pad", "site", "terminal"],
    )


def _view(claims: list[ClaimRecord], places: list[PlaceEntry]) -> dict[str, Any]:
    view = rebuild(_Log(claims), _Log([]), _config(places))
    return {n.id: n for n in view.nodes}


# ── 1. coverage: a curated toponym with no coordinate becomes a plotted point ───────────────────

def test_a_named_place_with_no_coordinate_adopts_the_anchor() -> None:
    nodes = _view([_entity("s1", "PAF Base Nur Khan", coordinates=_loc("PAF Base Nur Khan"))],
                  [NURKHAN])
    loc = nodes["s1"].location
    assert loc is not None
    assert (loc.wgs84_lat, loc.wgs84_lon) == (33.61639, 73.09972)
    assert loc.resolved_place_ref == "pl_nurkhan"
    assert loc.precision_class == "site"                     # the anchor's class, not a guess
    assert loc.raw == "PAF Base Nur Khan"                    # the source's own words are untouched
    assert nodes["s1"].attrs[LOCATION_SOURCE] == LOCATION_SOURCE_ANCHOR
    assert nodes["s1"].attrs[LOCATION_UNCERTAINTY_RADIUS_M] == 1500.0


def test_the_adopted_point_is_labelled_as_derived_not_as_stated() -> None:
    """The whole bi-level bargain: the evidence layer keeps "central Punjab", the knowledge layer
    says where we drew it and how wide the doubt is. A reader must be able to tell the two apart."""
    nodes = _view([_entity("s1", "fenced compound near a PAF airbase",
                           coordinates=_loc("central Punjab"))], [PUNJAB])
    node = nodes["s1"]
    assert node.attrs[LOCATION_SOURCE] == LOCATION_SOURCE_ANCHOR
    assert node.attrs[LOCATION_UNCERTAINTY_RADIUS_M] == 150000.0
    assert node.location is not None and node.location.precision_class == "province"


# ── 2. precision: the finer of the two statements, and never coarser than the source gave ──────

def test_a_stated_coordinate_keeps_its_own_point_and_is_labelled_stated() -> None:
    nodes = _view(
        [_entity("s1", "Nur Khan emplacement",
                 coordinates=_loc("grid", lat=33.6164, lon=73.0997, precision="pad"))],
        [NURKHAN],
    )
    loc = nodes["s1"].location
    assert loc is not None and (loc.wgs84_lat, loc.wgs84_lon) == (33.6164, 73.0997)
    assert nodes["s1"].attrs[LOCATION_SOURCE] == LOCATION_SOURCE_STATED


def test_resolving_to_a_coarser_anchor_never_downgrades_a_grid_reference() -> None:
    """A 5-digit grid is a pad. Binding it to the airbase it sits on must not blur it to `site`."""
    nodes = _view(
        [_entity("s1", "PAF Base Nur Khan",
                 coordinates=_loc("PAF Base Nur Khan", lat=33.6164, lon=73.0997, precision="pad"))],
        [NURKHAN],
    )
    loc = nodes["s1"].location
    assert loc is not None and loc.precision_class == "pad"
    assert nodes["s1"].attrs[LOCATION_UNCERTAINTY_RADIUS_M] == 500.0


def test_resolving_to_a_finer_anchor_upgrades_an_understated_surface_form() -> None:
    """The Karachi case: a 4-decimal pair buried in prose parses as a degree-scale DMS and lands as
    `city`. It resolves onto a pad the analyst curated, and the finer of the two is the honest one."""
    nodes = _view(
        [_entity("s1", "Malir AD area",
                 coordinates=_loc("Malir AD area", lat=24.9012, lon=67.2034, precision="city"))],
        [KARACHI_AD],
    )
    loc = nodes["s1"].location
    assert loc is not None and loc.precision_class == "pad"
    assert nodes["s1"].attrs[LOCATION_UNCERTAINTY_RADIUS_M] == 500.0


# ── 3. refusal: an unknown place stays unplotted, and keeps saying what the source said ─────────

def test_an_uncurated_place_is_left_unplotted_rather_than_nudged() -> None:
    nodes = _view(
        [_entity("s1", "garrison in China's western military district",
                 coordinates=_loc("China's western military district"))],
        [NURKHAN, PUNJAB, KARACHI_AD],
    )
    loc = nodes["s1"].location
    assert loc is not None
    assert loc.wgs84_lat is None and loc.wgs84_lon is None   # nothing invented
    assert loc.resolved_place_ref is None
    assert loc.raw == "China's western military district"    # still visible as a known-but-unplaced
    assert LOCATION_SOURCE not in nodes["s1"].attrs


def test_no_gazetteer_means_no_stamping_at_all() -> None:
    """Empty config ⇒ the pre-T5 view, byte-for-byte (gate G2)."""
    view = rebuild(_Log([_entity("s1", "Anywhere", coordinates=_loc("Anywhere"))]), _Log([]), mk_config())
    node = view.nodes[0]
    assert node.location is not None and node.location.wgs84_lat is None
    assert LOCATION_SOURCE not in node.attrs and LOCATION_UNCERTAINTY_RADIUS_M not in node.attrs
