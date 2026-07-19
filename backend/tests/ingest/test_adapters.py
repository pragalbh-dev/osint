"""Adapter tests — the deterministic, offline pre-append normalizers (INGEST value objects).

Every test here is network-free: the geocoder is a scripted fake (Nominatim is never constructed),
so these double as the guarantee that keyless ingest + the frozen bundles replay without a network.
The load-bearing behaviours asserted: the ``2024-11-31 → -30`` calendar clamp, the coarse-label →
ISO-bounds path, relative-date resolution against ``report_time``, the multi-format coordinate
canonicaliser (DD / DMS / MGRS / UTM / URL / packed-NOTAM / decimal-minute NAVAREA), the **Rahwali
beat** (bearing-and-distance offset), and ``resolved_place_ref`` staying ``None`` (RESOLVE's slot).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from geopy.distance import geodesic

from chanakya.ingest import adapters
from chanakya.ingest.adapters import (
    normalize_date,
    normalize_location,
    normalize_quantity,
)
from chanakya.schemas.values import (
    ExactDate,
    LabelDate,
    Location,
    Period,
    Quantity,
    canonical_iso_bounds,
)


class _FakeGeocoder:
    """A scripted, offline stand-in for geopy Nominatim: substring-match a name → fixed coords."""

    def __init__(self, table: dict[str, tuple[float, float, str]]) -> None:
        self._table = table

    def geocode(self, query: str) -> SimpleNamespace | None:
        for key, (lat, lon, addr) in self._table.items():
            if key.lower() in query.lower():
                return SimpleNamespace(latitude=lat, longitude=lon, address=addr)
        return None


_REPORT = ExactDate(iso_date="2021-11-15")  # a pinned report_time anchor for relative-date tests


# ── Dates ────────────────────────────────────────────────────────────────────────────────────────

def test_exact_iso_clamps_invalid_day() -> None:
    d = normalize_date("2024-11-31")
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2024-11-30"  # November has 30 days — clamped, never rolled to December
    assert d.boundary_source == "explicit"


def test_exact_iso_clamps_february() -> None:
    d = normalize_date("2021-02-30")
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2021-02-28"


def test_exact_iso_valid_passthrough() -> None:
    d = normalize_date("2021-11-02")
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2021-11-02"


def test_full_explicit_date() -> None:
    d = normalize_date("17 July 2014")
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2014-07-17"


def test_label_dict_fast_path() -> None:
    d = normalize_date(None, label={"granularity": "quarter", "year": 2021, "quarter": 4})
    assert isinstance(d, LabelDate)
    assert d.granularity == "quarter"
    assert canonical_iso_bounds(d) == ("2021-10-01", "2021-12-31")


def test_coarse_quarter_text() -> None:
    d = normalize_date("Q4 2021")
    assert isinstance(d, LabelDate)
    assert (d.granularity, d.quarter, d.year) == ("quarter", 4, 2021)


def test_coarse_half_text() -> None:
    d = normalize_date("H1 2020")
    assert isinstance(d, LabelDate)
    assert (d.granularity, d.half) == ("half", 1)


def test_coarse_year_bounds() -> None:
    d = normalize_date("2016")
    assert isinstance(d, LabelDate)
    assert canonical_iso_bounds(d) == ("2016-01-01", "2016-12-31")


def test_coarse_month_year() -> None:
    d = normalize_date("July 2014")
    assert isinstance(d, LabelDate)
    assert (d.granularity, d.year, d.month) == ("month", 2014, 7)


def test_interval_year_range() -> None:
    d = normalize_date("2016-2019")
    assert isinstance(d, Period)
    assert d.period_type == "range"
    assert canonical_iso_bounds(d) == ("2016-01-01", "2019-12-31")


def test_as_of_anchor() -> None:
    d = normalize_date("as of 2021")
    assert isinstance(d, Period)
    assert d.period_type == "as_of"
    assert canonical_iso_bounds(d) == ("2021-01-01", "2021-12-31")


def test_relative_last_week_resolves_and_is_approximate() -> None:
    d = normalize_date("last week", report_time=_REPORT)
    assert isinstance(d, Period)
    assert d.approximate is True
    lo, hi = canonical_iso_bounds(d)
    assert lo is not None and hi is not None and lo < hi
    # window sits before the report date
    assert hi <= "2021-11-15"


def test_relative_yesterday_is_exact() -> None:
    d = normalize_date("yesterday", report_time=_REPORT)
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2021-11-14"
    assert d.boundary_source == "relative"


def test_relative_n_days_ago() -> None:
    d = normalize_date("3 days ago", report_time=_REPORT)
    assert isinstance(d, ExactDate)
    assert d.iso_date == "2021-11-12"


def test_relative_without_report_time_is_unresolvable() -> None:
    assert normalize_date("last week") is None


def test_unparseable_date_returns_none() -> None:
    assert normalize_date("sometime soon-ish, maybe") is None


def test_blank_and_none_date() -> None:
    assert normalize_date("   ") is None
    assert normalize_date(None) is None


# ── Locations ──────────────────────────────────────────────────────────────────────────────────

def test_decimal_degrees() -> None:
    loc = normalize_location("24.7869, 67.3410")
    assert isinstance(loc, Location)
    assert loc.surface_format == "DD"
    assert loc.wgs84_lat == pytest.approx(24.7869)
    assert loc.wgs84_lon == pytest.approx(67.3410)
    assert loc.precision_class == "pad"
    assert loc.resolved_place_ref is None  # RESOLVE's slot, never INGEST's


def test_dms_seconds() -> None:
    loc = normalize_location("32°14′20″N 074°07′52″E")
    assert loc is not None
    assert loc.surface_format == "DMS"
    assert loc.wgs84_lat == pytest.approx(32.23889, abs=1e-4)
    assert loc.wgs84_lon == pytest.approx(74.13111, abs=1e-4)
    assert loc.precision_class == "pad"


def test_mgrs_grid_resolves_to_nur_khan() -> None:
    loc = normalize_location("43S CT 23715 21242")
    assert loc is not None
    assert loc.surface_format == "MGRS"
    # 43S CT 23715 21242 is the PAF Base Nur Khan reference (public/real coord)
    assert loc.wgs84_lat == pytest.approx(33.6164, abs=1e-3)
    assert loc.wgs84_lon == pytest.approx(73.0997, abs=1e-3)


def test_utm_parses_to_finite_wgs84() -> None:
    loc = normalize_location("43R 331000E 3720000N")
    assert loc is not None
    assert loc.surface_format == "UTM"
    assert loc.wgs84_lat == pytest.approx(33.6064, abs=1e-2)
    assert loc.wgs84_lon == pytest.approx(73.1784, abs=1e-2)


def test_maps_url() -> None:
    loc = normalize_location("https://maps.google.com/?q=24.79,67.34")
    assert loc is not None
    assert loc.surface_format == "url"
    assert loc.wgs84_lat == pytest.approx(24.79)
    assert loc.wgs84_lon == pytest.approx(67.34)


def test_navarea_decimal_minutes() -> None:
    loc = normalize_location("34-29.00N 120-29.00W")
    assert loc is not None
    assert loc.surface_format == "DMS"
    assert loc.wgs84_lat == pytest.approx(34.4833, abs=1e-3)
    assert loc.wgs84_lon == pytest.approx(-120.4833, abs=1e-3)  # W hemisphere → negative


def test_notam_packed_dms() -> None:
    loc = normalize_location("495355N 0380155E")
    assert loc is not None
    assert loc.surface_format == "DMS"
    assert loc.wgs84_lat == pytest.approx(49.8986, abs=1e-3)
    assert loc.wgs84_lon == pytest.approx(38.0319, abs=1e-3)


def test_toponym_geocoded_and_proposes_alias() -> None:
    gc = _FakeGeocoder({"Rahwali": (32.239, 74.131, "Rahwali, Punjab, PK")})
    loc = normalize_location("Rahwali airfield", geocoder=gc)
    assert loc is not None
    assert loc.surface_format == "toponym"
    assert loc.wgs84_lat == pytest.approx(32.239)
    assert loc.proposed_alias == "Rahwali airfield"
    assert loc.geocode_candidates[0].source == "nominatim"
    assert loc.resolved_place_ref is None


def test_relative_bearing_offset_rahwali_beat() -> None:
    # The load-bearing beat: "~10 km NW of Gujranwala" → geocode Gujranwala, offset NW 10 km.
    gc = _FakeGeocoder({"Gujranwala": (32.157, 74.19, "Gujranwala, Punjab, PK")})
    loc = normalize_location("~10 km NW of Gujranwala", geocoder=gc)
    assert loc is not None
    assert loc.surface_format == "relative"
    # NW of the anchor: latitude increases, longitude decreases
    assert loc.wgs84_lat > 32.157
    assert loc.wgs84_lon < 74.19
    # the canonical coord is the OFFSET point, ~10 km great-circle from the anchor
    assert geodesic((32.157, 74.19), (loc.wgs84_lat, loc.wgs84_lon)).km == pytest.approx(10.0, abs=0.1)
    assert loc.proposed_alias == "Gujranwala"
    # the anchor is retained as a candidate for auditability
    sources = {c.source for c in loc.geocode_candidates}
    assert sources == {"coord-parse", "nominatim"}
    assert loc.resolved_place_ref is None


def test_toponym_without_geocoder_keeps_stated_form(monkeypatch: pytest.MonkeyPatch) -> None:
    # No geocoder + default disabled (offline) → the stated name is preserved for RESOLVE, no coords.
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)
    loc = normalize_location("Some Unknown Place")
    assert loc is not None
    assert loc.surface_format == "toponym"
    assert loc.wgs84_lat is None
    assert loc.proposed_alias == "Some Unknown Place"


def test_relative_without_geocoder_keeps_stated_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)
    loc = normalize_location("~12 km NNW of Nowhere")
    assert loc is not None
    assert loc.surface_format == "relative"
    assert loc.wgs84_lat is None
    assert loc.proposed_alias == "Nowhere"


def test_forced_surface_format_overrides_sniffer() -> None:
    # Caller-supplied format hint wins over the deterministic sniff.
    loc = normalize_location("32°14′20″N 074°07′52″E", surface_format="DMS")
    assert loc is not None and loc.surface_format == "DMS"


def test_blank_location_returns_none() -> None:
    assert normalize_location("   ") is None
    assert normalize_location(None) is None


# ── Quantities ─────────────────────────────────────────────────────────────────────────────────

def test_measure_with_approx() -> None:
    q = normalize_quantity("~125 km")
    assert isinstance(q, Quantity)
    assert q.value == pytest.approx(125.0)
    assert q.unit == "km"
    assert q.approx is True


def test_count_with_state_and_unit_singularized() -> None:
    q = normalize_quantity("a battalion of ~6 TELs", count_state="fielded")
    assert isinstance(q, Quantity)
    assert q.value == pytest.approx(6.0)
    assert q.unit == "TEL"
    assert q.count_state == "fielded"
    assert q.approx is True


def test_plain_count() -> None:
    q = normalize_quantity("2 systems")
    assert isinstance(q, Quantity)
    assert q.value == pytest.approx(2.0)
    assert q.unit == "system"
    assert q.approx is False


def test_range_hyphen() -> None:
    q = normalize_quantity("90-110m")
    assert isinstance(q, Quantity)
    assert q.min == pytest.approx(90.0)
    assert q.max == pytest.approx(110.0)
    assert q.unit == "m"


def test_range_endash() -> None:
    q = normalize_quantity("40–150 km engagement bracket")
    assert isinstance(q, Quantity)
    assert q.min == pytest.approx(40.0)
    assert q.max == pytest.approx(150.0)
    assert q.unit == "km"


def test_invalid_count_state_ignored() -> None:
    q = normalize_quantity("2 systems", count_state="bogus")
    assert isinstance(q, Quantity)
    assert q.count_state is None


def test_spelled_count() -> None:
    q = normalize_quantity("a dozen missiles")
    assert isinstance(q, Quantity)
    assert q.value == pytest.approx(12.0)


def test_quantity_without_number_returns_none() -> None:
    assert normalize_quantity("several launchers") is None
    assert normalize_quantity("") is None
    assert normalize_quantity(None) is None


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The two-stage geocoder — gazetteer coordinate-cache (offline, exact-match) → Nominatim open world.
# INGEST freezes COORDINATES; identity (resolved_place_ref) stays RESOLVE's. See the RESOLVE note
# (tmp/conv/INGEST-locations-gazetteer-vs-nominatim.md) + md/13.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

from chanakya import settings  # noqa: E402
from chanakya.config.store import ConfigStore  # noqa: E402
from chanakya.ingest.adapters import (  # noqa: E402
    ChainedGeocoder,
    GazetteerGeocoder,
    build_geocoder,
    gazetteer_key,
)
from chanakya.schemas.config_models import PlaceEntry  # noqa: E402


@pytest.fixture(scope="module")
def real_config() -> object:
    """The live config bundle (real ``config/places.yaml`` gazetteer + transliteration rules)."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


# ── gazetteer_key: the exact normaliser, pinned byte-identical to RESOLVE's normalize() ───────────

def test_gazetteer_key_matches_resolve_normalize_spec() -> None:
    # These outputs are RESOLVE's chanakya.resolve.normalize.normalize() spec (transliterate → casefold
    # → collapse non-alnum runs → strip). Pinned so an INGEST/RESOLVE key drift is caught (RESOLVE note).
    assert gazetteer_key("PAF Base Nur Khan") == "paf base nur khan"
    assert gazetteer_key("  Port   Qasim  ") == "port qasim"
    assert gazetteer_key("OPRN") == "oprn"
    assert gazetteer_key("Bin Qasim Port!!") == "bin qasim port"
    assert gazetteer_key("") == ""
    # transliteration rule applied longest-first, then punctuation collapsed.
    assert gazetteer_key("红旗-9", {"红旗": "Hongqi"}) == "hongqi 9"


# ── GazetteerGeocoder: EXACT match only, over the real seed ───────────────────────────────────────

def test_gazetteer_exact_match_seeded_name_returns_canonical_dd(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    hit = gaz.geocode("PAF Base Nur Khan")
    assert hit is not None
    assert hit.latitude == pytest.approx(33.61639) and hit.longitude == pytest.approx(73.09972)
    assert hit.source == "gazetteer"


def test_gazetteer_matches_hard_ids_icao_and_locode(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    assert gaz.geocode("OPRN").latitude == pytest.approx(33.61639)  # Nur Khan ICAO
    assert gaz.geocode("PKBQM").latitude == pytest.approx(24.767)   # Port Qasim LOCODE


def test_gazetteer_normalises_before_matching(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    # casefold + punctuation collapse: a noisy surface form still exact-matches a seeded alias.
    assert gaz.geocode("  port   qasim ") is not None
    assert gaz.geocode("PAF BASE NUR KHAN") is not None


def test_gazetteer_withheld_alias_chaklala_does_not_match(real_config: object) -> None:
    # "Chaklala" is deliberately absent from the seed (the earned-merge demo) — must NOT hit here.
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    assert gaz.geocode("Chaklala") is None
    assert gaz.geocode("PAF Base Chaklala") is None


def test_gazetteer_unseeded_name_returns_none(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    assert gaz.geocode("Some Unknown Place") is None


def test_gazetteer_skips_places_without_coords() -> None:
    places = [PlaceEntry(place_id="p1", canonical_name="No Coord Place", aliases=["NCP"])]
    gaz = GazetteerGeocoder(places, {})
    assert gaz.geocode("No Coord Place") is None


# ── ChainedGeocoder: gazetteer first, Nominatim fallback ──────────────────────────────────────────

def test_chained_geocoder_prefers_gazetteer_then_falls_back(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    fake_nominatim = _FakeGeocoder({"Gujranwala": (32.157, 74.19, "Gujranwala, Punjab, PK")})
    chain = ChainedGeocoder([gaz, fake_nominatim])

    seeded = chain.geocode("PAF Base Nur Khan")  # gazetteer wins
    assert seeded.source == "gazetteer" and seeded.latitude == pytest.approx(33.61639)

    open_world = chain.geocode("Gujranwala")  # not seeded → Nominatim fallback
    assert open_world is not None and open_world.latitude == pytest.approx(32.157)
    assert getattr(open_world, "source", "nominatim") == "nominatim"  # fake has no source attr

    assert chain.geocode("Nowhere At All") is None


def test_chained_geocoder_filters_none_geocoders(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    chain = ChainedGeocoder([None, gaz, None])
    assert chain.geocode("OPRN") is not None


# ── build_geocoder + normalize_location integration ───────────────────────────────────────────────

def test_build_geocoder_offline_is_gazetteer_only(real_config: object) -> None:
    geocoder = build_geocoder(real_config, online=False)
    assert geocoder.geocode("PAF Base Nur Khan") is not None  # seeded, offline
    assert geocoder.geocode("Gujranwala") is None             # open world needs Nominatim (offline → miss)


def test_normalize_location_via_gazetteer_freezes_coord_and_source(real_config: object) -> None:
    gaz = GazetteerGeocoder(real_config.places.places, real_config.resolution.transliteration)
    loc = normalize_location("PAF Base Nur Khan", geocoder=gaz)
    assert isinstance(loc, Location)
    assert loc.wgs84_lat == pytest.approx(33.61639) and loc.wgs84_lon == pytest.approx(73.09972)
    assert loc.geocode_candidates[0].source == "gazetteer"
    assert loc.resolved_place_ref is None  # identity stays RESOLVE's, at rebuild
