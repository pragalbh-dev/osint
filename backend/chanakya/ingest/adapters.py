"""Explicit pre-append **value normalizers** — the parse/geo/calendar work that turns a raw stated
string into an F0 ``values.py`` object (``DateValue`` / ``Location`` / ``Quantity``), run **once at
extraction time, upstream of ``store.append``**.

Why these live here and are *plain functions*, never pydantic validators (gate G1): a validator on
``Location``/``Date`` would re-fire its network geocode / DMS parse on **every** ``rebuild()`` reload
of the frozen evidence log — non-deterministic, slow, and a hidden network dependency inside the
rebuild call-path. So F0 froze the *shapes* (``values.py``) and left the *filling* to INGEST: the
extractor calls these adapters, the resolved slots are frozen onto the ``ClaimRecord``, and
``rebuild()`` only ever reads them. Nothing here branches on a subject/anchor or the ontology
instance content (gate G9) — a coordinate is a coordinate regardless of who deploys the battery.

Three normalizers, one per structured payload slot (``values.py`` §4.2):

* :func:`normalize_date` — a stated date string (or an LLM coarse-label dict) → ``ExactDate`` /
  ``LabelDate`` / ``Period``. Exact ISO (with a calendar clamp, ``2024-11-31`` → ``-30``), a coarse
  label (``"Q4 2021"``, ``"2016"``), an interval, or a relative phrase (``"last week"``) resolved
  against ``report_time``. Calendar-only, deterministic, offline.
* :func:`normalize_location` — **Stage A of location normalization** (md/13 §2): the deterministic
  coordinate canonicaliser (DD / DMS / MGRS / UTM / map-URL → WGS84) plus a geocode of a toponym or a
  relative bearing-and-distance ref. The **Rahwali beat** (a ``"~10 km NW of Gujranwala"`` ref) is
  parsed to distance+bearing, the anchor geocoded, and a great-circle offset applied — the offset is
  the canonical coord, the anchor is kept as a candidate. ``resolved_place_ref`` is left ``None``:
  place *resolution* (Stage B, gazetteer match + distinct-from) is RESOLVE's, at rebuild.
* :func:`normalize_quantity` — a count / range / measure string (``"~6 TELs"``, ``"90-110m"``,
  ``"40–150 km"``) → an evidence-graded ``Quantity`` carrying its ``count_state``.

The ``geocoder`` is **injectable** (default: a lazily-constructed geopy Nominatim) so tests run fully
offline against a fake and the demo's frozen bundles never hit the network at replay time.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from chanakya.schemas.config_models import PlaceEntry
from chanakya.schemas.values import (
    CountState,
    DateValue,
    ExactDate,
    GeocodeCandidate,
    LabelDate,
    Location,
    Period,
    PrecisionClass,
    Quantity,
    SurfaceFormat,
    canonical_iso_bounds,
)

# A single date value the interval branch composes from (``Period.start``/``end`` are these).
DateSpec = ExactDate | LabelDate

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
# Approx / hedge markers shared by the date and quantity parsers (source states uncertainty).
_APPROX_RE = re.compile(
    r"~|≈|±|\bapprox(?:\.|imately)?\b|\broughly\b|\baround\b|\babout\b|\bcirca\b|\bca\.?\b|"
    r"\best(?:\.|imated)?\b|\bnearly\b|\bover\b|\bunder\b|\bat least\b|\bup to\b",
    re.IGNORECASE,
)


# ── Dates ────────────────────────────────────────────────────────────────────────────────────────

_SPELLED = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a dozen": 12, "dozen": 12,
}


def _clamp_iso(year: int, month: int, day: int) -> str:
    """``(y, m, d)`` → a valid ``YYYY-MM-DD``, clamping an over-run day to the month's last day.

    The non-negotiable ``2024-11-31 → 2024-11-30`` (and ``2021-02-30 → 2021-02-28``) — a stated but
    calendar-invalid day is *clamped*, never dropped and never fabricated forward into the next month.
    """
    month = min(max(month, 1), 12)
    last = calendar.monthrange(year, month)[1]
    day = min(max(day, 1), last)
    return f"{year:04d}-{month:02d}-{day:02d}"


_ISO_RE = re.compile(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*$")
_YM_RE = re.compile(r"^\s*(\d{4})[-/](\d{1,2})\s*$")
_YEAR_RE = re.compile(r"^\s*(\d{4})\s*$")
_Q_RE = re.compile(r"^\s*(?:q([1-4])[\s/-]*(\d{4})|(\d{4})[\s/-]*q([1-4]))\s*$", re.IGNORECASE)
_H_RE = re.compile(
    r"^\s*(?:h([12])[\s/-]*(\d{4})|(\d{4})[\s/-]*h([12])|"
    r"(first|second|1st|2nd)\s+half\s+(?:of\s+)?(\d{4}))\s*$",
    re.IGNORECASE,
)
_EARLYLATE_RE = re.compile(r"^\s*(early|mid|late)\s+(\d{4})\s*$", re.IGNORECASE)
_MONTHYEAR_RE = re.compile(rf"^\s*({_MONTH_ALT})\.?\s+(\d{{4}})\s*$", re.IGNORECASE)


def _parse_iso_exact(s: str) -> ExactDate | None:
    """A fully-specified explicit calendar date (``YYYY-MM-DD`` / slash / dot) → clamped ``ExactDate``."""
    m = _ISO_RE.match(s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mo <= 12:
        return None
    return ExactDate(iso_date=_clamp_iso(y, mo, d), raw=s.strip(), boundary_source="explicit")


def _parse_coarse_label(s: str) -> LabelDate | None:
    """A coarse-granularity label the LLM emits verbatim (``"Q4 2021"``, ``"H1 2020"``, ``"2016"``)."""
    raw = s.strip()
    m = _Q_RE.match(s)
    if m:
        q = int(m.group(1) or m.group(4))
        y = int(m.group(2) or m.group(3))
        return LabelDate(raw=raw, granularity="quarter", year=y, quarter=q)
    m = _H_RE.match(s)
    if m:
        if m.group(1) or m.group(3):
            h = int(m.group(1) or m.group(4))
            y = int(m.group(2) or m.group(3))
        else:  # "first/second half of YYYY"
            h = 1 if m.group(5).lower() in {"first", "1st"} else 2
            y = int(m.group(6))
        return LabelDate(raw=raw, granularity="half", year=y, half=h)
    m = _EARLYLATE_RE.match(s)
    if m:
        # "early YYYY" → H1, "late YYYY" → H2, "mid YYYY" → whole year (deliberately coarse, not a guess).
        word, y = m.group(1).lower(), int(m.group(2))
        if word == "early":
            return LabelDate(raw=raw, granularity="half", year=y, half=1)
        if word == "late":
            return LabelDate(raw=raw, granularity="half", year=y, half=2)
        return LabelDate(raw=raw, granularity="year", year=y)
    m = _MONTHYEAR_RE.match(s)
    if m:
        return LabelDate(raw=raw, granularity="month", year=int(m.group(2)),
                         month=_MONTHS[m.group(1).lower()])
    m = _YM_RE.match(s)
    if m:
        mo = int(m.group(2))
        if 1 <= mo <= 12:
            return LabelDate(raw=raw, granularity="month", year=int(m.group(1)), month=mo)
    m = _YEAR_RE.match(s)
    if m:
        y = int(m.group(1))
        if 1900 <= y <= 2100:
            return LabelDate(raw=raw, granularity="year", year=y)
    return None


def _parse_full_explicit(s: str, report_time: DateValue | None) -> DateSpec | None:
    """A free-form explicit date (``"17 July 2014"``, ``"July 17, 2014"``) via a *field-detecting* parse.

    ``dateutil`` is parsed twice against two sentinel defaults; a field that differs between the two was
    **not** stated by the source — so we never fabricate a day-of-month the source didn't give (all-
    optional / anti-fabrication). Missing year with a month+day present is resolved against
    ``report_time`` (flagged ``boundary_source="relative"``); missing month → coarser ``LabelDate``.
    """
    try:
        from dateutil import parser as _dtp
    except ImportError:  # pragma: no cover - dateutil is a hard dep
        return None
    try:
        d1 = _dtp.parse(s, default=dt.datetime(1999, 1, 1), fuzzy=False)
        d2 = _dtp.parse(s, default=dt.datetime(2000, 2, 2), fuzzy=False)
    except (ValueError, OverflowError):
        return None
    has_year, has_month, has_day = d1.year == d2.year, d1.month == d2.month, d1.day == d2.day
    raw = s.strip()
    if has_year and has_month and has_day:
        return ExactDate(iso_date=_clamp_iso(d1.year, d1.month, d1.day), raw=raw,
                         boundary_source="explicit")
    if has_year and has_month:
        return LabelDate(raw=raw, granularity="month", year=d1.year, month=d1.month)
    if has_year:
        return LabelDate(raw=raw, granularity="year", year=d1.year)
    if has_month and has_day:
        anchor = _anchor(report_time)
        if anchor is not None:
            return ExactDate(iso_date=_clamp_iso(anchor.year, d1.month, d1.day), raw=raw,
                             boundary_source="relative")
    return None


def _parse_point(s: str, report_time: DateValue | None) -> DateSpec | None:
    """A single date token → ``ExactDate``/``LabelDate`` (ISO clamp → coarse label → free-form)."""
    return (
        _parse_iso_exact(s)
        or _parse_coarse_label(s)
        or _parse_full_explicit(s, report_time)
    )


_RANGE_RE = re.compile(
    r"^\s*(?:from\s+|between\s+)?(.+?)\s*(?:–|—|-|\bto\b|\bthrough\b|\bthru\b|\band\b|\buntil\b)\s*(.+?)\s*$",
    re.IGNORECASE,
)
_ASOF_RE = re.compile(r"^\s*(?:as of|since|as at|effective)\s+(.+?)\s*$", re.IGNORECASE)


def _parse_range(s: str, report_time: DateValue | None) -> Period | None:
    """An interval (``"2016-2019"``, ``"March 2016 to June 2018"``, ``"between X and Y"``) → a range."""
    m = _RANGE_RE.match(s)
    if not m:
        return None
    lhs, rhs = m.group(1).strip(), m.group(2).strip()
    start, end = _parse_point(lhs, report_time), _parse_point(rhs, report_time)
    if start is None and end is None:
        return None
    return Period(period_type="range", start=start, end=end)


def _parse_as_of(s: str, report_time: DateValue | None) -> Period | None:
    """An anchored ``"as of <date>"`` / ``"since <date>"`` → a single-anchor ``Period``."""
    m = _ASOF_RE.match(s)
    if not m:
        return None
    point = _parse_point(m.group(1).strip(), report_time)
    if point is None:
        return None
    return Period(period_type="as_of", as_of=point)


def _anchor(report_time: DateValue | None) -> dt.date | None:
    """The concrete anchor date a relative phrase resolves against — ``report_time``'s latest bound."""
    if report_time is None:
        return None
    lo, hi = canonical_iso_bounds(report_time)
    iso = hi or lo
    if not iso:
        return None
    try:
        return dt.date.fromisoformat(iso)
    except ValueError:
        return None


def _exact(day: dt.date, raw: str) -> ExactDate:
    return ExactDate(iso_date=day.isoformat(), raw=raw, boundary_source="relative")


def _range(a: dt.date, b: dt.date, raw: str) -> Period:
    return Period(period_type="range", start=_exact(a, raw), end=_exact(b, raw), approximate=True)


def _quarter_bounds(day: dt.date) -> tuple[dt.date, dt.date]:
    q = (day.month - 1) // 3
    sm = 3 * q + 1
    em = sm + 2
    return dt.date(day.year, sm, 1), dt.date(day.year, em, calendar.monthrange(day.year, em)[1])


_REL_HINT_RE = re.compile(
    r"\b(today|now|currently|yesterday|tonight|this (?:week|month|quarter|year)|"
    r"last (?:week|month|year)|recent|recently|lately|ago)\b",
    re.IGNORECASE,
)
_AGO_RE = re.compile(r"(\d+)\s+(day|week|month|year)s?\s+ago", re.IGNORECASE)


def _parse_relative(s: str, report_time: DateValue | None) -> DateValue | None:
    """A relative phrase (``"last week"``, ``"3 days ago"``, ``"recently"``) resolved to a ``Period``.

    Marked ``approximate=True`` (a relative window, not a stated instant) except a single-day anchor
    (``"yesterday"``, ``"N days ago"``) which resolves to an ``ExactDate`` flagged ``relative``.
    Unresolvable without a ``report_time`` anchor → ``None`` (never a fabricated date).
    """
    low = s.lower()
    if not _REL_HINT_RE.search(low):
        return None
    anchor = _anchor(report_time)
    if anchor is None:
        return None
    raw = s.strip()

    m = _AGO_RE.search(low)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if unit == "day":
            return _exact(anchor - dt.timedelta(days=n), raw)
        if unit == "week":
            mid = anchor - dt.timedelta(days=7 * n)
            return _range(mid - dt.timedelta(days=3), mid + dt.timedelta(days=3), raw)
        if unit == "month":
            return _range(anchor - dt.timedelta(days=30 * n + 15),
                          anchor - dt.timedelta(days=30 * n - 15), raw)
        return _range(dt.date(anchor.year - n, 1, 1), dt.date(anchor.year - n, 12, 31), raw)

    if "today" in low or "now" in low or "currently" in low or "tonight" in low:
        return _exact(anchor, raw)
    if "yesterday" in low:
        return _exact(anchor - dt.timedelta(days=1), raw)
    if "last week" in low:
        return _range(anchor - dt.timedelta(days=13), anchor - dt.timedelta(days=7), raw)
    if "last month" in low:
        first_this = anchor.replace(day=1)
        last_prev = first_this - dt.timedelta(days=1)
        return _range(last_prev.replace(day=1), last_prev, raw)
    if "last year" in low:
        return _range(dt.date(anchor.year - 1, 1, 1), dt.date(anchor.year - 1, 12, 31), raw)
    if "this week" in low:
        monday = anchor - dt.timedelta(days=anchor.weekday())
        return _range(monday, monday + dt.timedelta(days=6), raw)
    if "this month" in low:
        first = anchor.replace(day=1)
        return _range(first, first.replace(day=calendar.monthrange(anchor.year, anchor.month)[1]), raw)
    if "this quarter" in low:
        a, b = _quarter_bounds(anchor)
        return _range(a, b, raw)
    if "this year" in low:
        return _range(dt.date(anchor.year, 1, 1), dt.date(anchor.year, 12, 31), raw)
    # "recently" / "lately" / "in recent weeks" — a trailing ~30-day window up to the report.
    return _range(anchor - dt.timedelta(days=30), anchor, raw)


def _label_from_dict(label: dict[str, object]) -> LabelDate | None:
    """Build a ``LabelDate`` from an LLM-emitted coarse-label dict (its structured fast-path)."""
    gran = label.get("granularity")
    year = label.get("year")
    if gran not in ("year", "half", "quarter", "month", "day") or not isinstance(year, int):
        return None

    def _int(key: str) -> int | None:
        v = label.get(key)
        return v if isinstance(v, int) else None

    raw = str(label.get("raw", "")) if label.get("raw") is not None else ""
    try:
        return LabelDate(
            raw=raw, granularity=gran, year=year,
            quarter=_int("quarter"), half=_int("half"), month=_int("month"), day=_int("day"),
        )
    except ValueError:
        return None


def normalize_date(
    raw: str | None,
    *,
    label: dict[str, object] | None = None,
    report_time: DateValue | None = None,
) -> DateValue | None:
    """Normalize a stated date to an F0 ``DateValue`` — pure, offline, calendar-only, deterministic.

    Order of resolution: an explicit LLM ``label`` dict → a relative phrase (needs ``report_time``) →
    an interval → an ``"as of"`` anchor → a single point (ISO-clamp → coarse label → free-form). An
    unparseable / evidence-absent string returns ``None`` — the caller emits no date rather than a
    fabricated one (the anti-fabrication discipline, applied to a slot).
    """
    if label is not None:
        ld = _label_from_dict(label)
        if ld is not None:
            return ld
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    # Point *before* interval so a hyphenated ISO date (``2024-11-31``) is a clamped date, not a range;
    # the interval/anchor branches are only reached once a whole-string point parse has failed.
    return (
        _parse_relative(s, report_time)
        or _parse_point(s, report_time)
        or _parse_as_of(s, report_time)
        or _parse_range(s, report_time)
    )


# ── Locations ──────────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class GeocodeResult(Protocol):
    """The minimal shape a geocoder returns — structurally satisfied by a geopy ``Location``."""

    latitude: float
    longitude: float
    address: str


@runtime_checkable
class Geocoder(Protocol):
    """A place-name → coordinate resolver. Injectable so tests stay offline; default is Nominatim."""

    def geocode(self, query: str) -> GeocodeResult | None: ...


def _default_geocoder() -> Geocoder | None:
    """Lazily construct a geopy Nominatim client (network at call-time only, never at import)."""
    try:
        from geopy.geocoders import Nominatim
    except ImportError:  # pragma: no cover - geopy is a hard dep
        return None
    return Nominatim(user_agent="chanakya-osint-ingest")


# ── the two-stage geocoder: gazetteer coordinate-cache → Nominatim open world ─────────────────────
#
# INGEST produces COORDINATES; RESOLVE produces IDENTITY (the 2026-07-19 RESOLVE coordination note).
# So the gazetteer here is a strict, offline **coordinate cache**: an exact-match mention → the seeded
# node's ``canonical_dd``, frozen onto the claim's ``Location`` (``resolved_place_ref`` still left
# ``None`` — picking the canonical node, the geodesic proximity, and the distinct-from traps are
# RESOLVE's, at rebuild). Gazetteer-first is what makes the demo anchors' coordinates byte-stable
# offline (G2); Nominatim covers the open world for everything the seed does not name.

# The gazetteer EXACT-match key normaliser. This MUST stay byte-identical to RESOLVE's
# ``chanakya.resolve.normalize.normalize()`` so INGEST's coordinate-cache key and RESOLVE's
# identity-match key can never drift (RESOLVE note 2026-07-19: "reuse it, don't re-implement, so keys
# can't drift"). RESOLVE is unmerged (its package ships only an identity stub on this branch), so it
# cannot be imported yet — this is a deliberate, spec-pinned copy; when RESOLVE lands, dedupe both to
# one shared module. ``tests/ingest/test_adapters.py`` pins the exact outputs so a drift is caught.
_GAZ_NON_ALNUM = re.compile("[^0-9a-z一-鿿Ѐ-ӿ؀-ۿऀ-ॿ]+")


def _gaz_transliterate(text: str, rules: dict[str, str]) -> str:
    """Apply script→latin substitution rules (longest key first) — RESOLVE ``transliterate`` twin."""
    out = text
    for src in sorted(rules, key=len, reverse=True):
        if src in out:
            out = out.replace(src, rules[src])
    return out


def gazetteer_key(name: str, rules: dict[str, str] | None = None) -> str:
    """Canonical comparison form for the exact gazetteer lookup — RESOLVE ``normalize`` twin.

    transliterate (config rules) → casefold → collapse every non-alphanumeric run to one space → strip.
    An empty / unsupported-script name normalises to ``""`` (treated as non-matching everywhere).
    """
    t = _gaz_transliterate(name, rules or {}).casefold()
    return _GAZ_NON_ALNUM.sub(" ", t).strip()


@dataclass
class GazetteerHit:
    """A gazetteer coordinate hit — structurally a :class:`GeocodeResult`, plus a ``source`` tag.

    A plain (non-frozen) dataclass so its fields are settable attributes and it therefore *structurally*
    satisfies the :class:`GeocodeResult` protocol (a frozen dataclass's read-only fields would not).
    """

    latitude: float
    longitude: float
    address: str
    source: str = "gazetteer"


class GazetteerGeocoder:
    """Offline EXACT-match coordinate cache over ``config/places.yaml`` (RESOLVE note 2026-07-19).

    :meth:`geocode` returns a node's ``canonical_dd`` **iff** the normalised mention exactly equals the
    node's normalised ``canonical_name``, a normalised seeded ``alias``, or a hard-ID (``icao`` /
    ``locode``). **No fuzzy, no proximity, no nearest** — those are RESOLVE's at rebuild. It reads ONLY
    ``canonical_name`` / ``aliases`` / ``icao`` / ``locode`` / ``canonical_dd``; never
    ``proximity_radius_m`` / ``distinct_from`` (RESOLVE-only knobs). A withheld alias (e.g. "Chaklala",
    deliberately absent from the seed for the earned-merge demo) therefore never hits here — it falls to
    Nominatim / stays raw, and RESOLVE earns it later. Fully deterministic; no network, no clock.
    """

    def __init__(self, places: Iterable[PlaceEntry], rules: dict[str, str] | None = None) -> None:
        self._rules = dict(rules or {})
        # normalised key → (lat, lon, canonical_name). First seeded form wins on a key collision, in
        # config order, so the index is deterministic. canonical_dd-less nodes are skipped (no coord).
        self._index: dict[str, tuple[float, float, str]] = {}
        for place in places:
            if place.canonical_dd is None:
                continue
            lat, lon = place.canonical_dd
            forms = [place.canonical_name, *place.aliases]
            forms += [hid for hid in (place.icao, place.locode) if hid]
            for form in forms:
                key = gazetteer_key(form, self._rules)
                if key:
                    self._index.setdefault(key, (float(lat), float(lon), place.canonical_name))

    def geocode(self, query: str) -> GeocodeResult | None:
        hit = self._index.get(gazetteer_key(query, self._rules))
        if hit is None:
            return None
        lat, lon, name = hit
        return GazetteerHit(latitude=lat, longitude=lon, address=name)


class ChainedGeocoder:
    """Try each geocoder in order; the first non-``None`` hit wins (gazetteer cache → Nominatim)."""

    def __init__(self, geocoders: Iterable[Geocoder | None],
                 confidences: Mapping[str, float] | None = None) -> None:
        self._geocoders = [g for g in geocoders if g is not None]
        # Carried on the geocoder so ``normalize_location`` picks the live config up through the one
        # seam it already has injected — no extra plumbing through every transform + the emitter.
        self.confidences: dict[str, float] = dict(confidences or GEOCODE_CONFIDENCE_DEFAULTS)

    def geocode(self, query: str) -> GeocodeResult | None:
        for geocoder in self._geocoders:
            hit = geocoder.geocode(query)
            if hit is not None:
                return hit
        return None


class _CachingGeocoder:
    """A within-run cache + polite wrapper around a live geocoder (Nominatim etiquette).

    Deduplicates identical queries within one recorder run (so re-mentions of the same place hit the
    network once) and, when geopy's ``RateLimiter`` is available, throttles to ≤1 request/second — the
    Nominatim usage policy. Only the keyed recorder ever constructs this; tests inject fakes/None.
    """

    def __init__(self, inner: Geocoder, *, min_delay_seconds: float = 1.0) -> None:
        self._cache: dict[str, GeocodeResult | None] = {}
        try:
            from geopy.extra.rate_limiter import RateLimiter

            self._geocode = RateLimiter(inner.geocode, min_delay_seconds=min_delay_seconds)
        except ImportError:  # pragma: no cover - geopy is a hard dep
            self._geocode = inner.geocode

    def geocode(self, query: str) -> GeocodeResult | None:
        if query not in self._cache:
            self._cache[query] = self._geocode(query)
        return self._cache[query]


def build_geocoder(
    config: object, *, online: bool = True, nominatim: Geocoder | None = None
) -> ChainedGeocoder:
    """Assemble the two-stage geocoder from the live config: gazetteer coord-cache → Nominatim.

    ``online=True`` (the keyed recorder / live ingest) appends a within-run-cached Nominatim after the
    gazetteer; ``online=False`` yields a gazetteer-only, fully-offline, byte-stable geocoder (tests +
    the deterministic seed path). Reads ``config.places.places`` + ``config.resolution.transliteration``
    only — never a subject/anchor (gate G9). Never called inside ``rebuild()`` (gate G1).
    """
    places = getattr(getattr(config, "places", None), "places", []) or []
    rules = getattr(getattr(config, "resolution", None), "transliteration", {}) or {}
    chain: list[Geocoder | None] = [GazetteerGeocoder(places, rules)]
    if online:
        live = nominatim if nominatim is not None else _default_geocoder()
        chain.append(_CachingGeocoder(live) if live is not None else None)
    return ChainedGeocoder(chain, geocode_confidences(config))


# Compass point → azimuth degrees (clockwise from true north), for the relative-offset math.
_BEARINGS = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5, "E": 90.0, "ESE": 112.5, "SE": 135.0,
    "SSE": 157.5, "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5, "W": 270.0,
    "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}
_UNIT_KM = {"km": 1.0, "kilometre": 1.0, "kilometer": 1.0, "kilometres": 1.0, "kilometers": 1.0,
            "nm": 1.852, "nmi": 1.852, "m": 0.001, "metre": 0.001, "meter": 0.001,
            "metres": 0.001, "meters": 0.001, "mi": 1.609344, "mile": 1.609344, "miles": 1.609344}

_REL_LOC_RE = re.compile(
    r"(?:~|≈|about|approx\.?|roughly|around)?\s*(?P<dist>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>km|kilometres?|kilometers?|nmi?|mi|miles?|m|metres?|meters?)\s+"
    r"(?P<bearing>NNE|NNW|ENE|ESE|SSE|SSW|WNW|WSW|NE|NW|SE|SW|N|S|E|W)\s+of\s+(?P<anchor>.+)",
    re.IGNORECASE,
)
_URL_COORD_RES = [
    re.compile(r"[?&](?:q|ll|query|center|sll|daddr)=(-?\d+\.\d+)[,%2C]+(-?\d+\.\d+)", re.IGNORECASE),
    re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)"),
    re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)"),
]
_DD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*°?\s*([NnSs])?\s*[,;/ ]\s*(-?\d+(?:\.\d+)?)\s*°?\s*([EeWw])?\s*$"
)
# A military grid reference, matched ANYWHERE in the string — a source states it in prose ("Grid: 43S
# CT 23715 21242 (MGRS, WGS84)"), not as a bare token, and an anchored match silently drops it.
# Strict on purpose so ordinary prose can never be coerced into a grid:
#   zone 1-60 · latitude band C-X (I/O never used) · 100 km square col A-Z / row A-V (I/O never used) ·
#   an even, equal-length easting/northing digit run · not glued to surrounding alphanumerics.
_MGRS_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-z])"
    r"(?P<zone>\d{1,2})\s*(?P<band>[C-HJ-NP-X])\s*"
    r"(?P<square>[A-HJ-NP-Z][A-HJ-NP-V])\s*"
    r"(?P<digits>\d{1,10}(?:\s+\d{1,5})?)"
    r"(?![0-9A-Za-z])",
    re.IGNORECASE,
)
_UTM_RE = re.compile(
    r"^\s*(\d{1,2})\s*([C-X])\s+(\d+(?:\.\d+)?)\s*(?:m?E)?\s+(\d+(?:\.\d+)?)\s*(?:m?N)?\s*$",
    re.IGNORECASE,
)
# A DMS component: a digit-anchored numeric body (so a word like "North" never matches) optionally
# followed by unit/separator glyphs, then the hemisphere letter. Covers °′″, hyphen-decimal-minute
# (NAVAREA ``34-29.00N``) and packed NOTAM (``495355N``) alike.
_DMS_LAT_RE = re.compile(r"(\d[\d°′″'\".:\-\s]*\d|\d)[°′″'\"]*\s*([NnSs])")
_DMS_LON_RE = re.compile(r"(\d[\d°′″'\".:\-\s]*\d|\d)[°′″'\"]*\s*([EeWw])")
# A sexagesimal marker: a degree/minute/second glyph, or a digit-separated minute field (NAVAREA
# ``34-29.00N``, ``32:14:20N``). Its ABSENCE is what makes ``24.9012 N, 67.2034 E`` unambiguously
# decimal-degrees rather than a degrees-only DMS — which matters, because the DD branch derives
# ``precision_class`` from the stated decimal places (4 dp ≈ 10 m → ``pad``, not ``city``).
_DMS_MARKER_RE = re.compile(r"[°′″]|\d\s*['\"]|\d\s*[-:]\s*\d")

# Formats whose value comes from parsing the string itself (vs. geocoding a name).
COORD_FORMATS: frozenset[str] = frozenset(("DD", "DMS", "MGRS", "UTM", "url"))
SURFACE_FORMATS: frozenset[str] = COORD_FORMATS | {"toponym", "relative"}

# The confidence stamped on a ``GeocodeCandidate``, by how the coordinate was obtained. Config-driven
# (``places.geocode_confidence``; gate G6 — no bare literals at the call sites) so an analyst can
# retune how much a Nominatim hit on a vague regional phrase is worth relative to a parsed grid.
# A *parsed* coordinate is the source's own statement; a gazetteer hit is a curated exact-match; a
# Nominatim hit on free text ("central Punjab") is a guess at a centroid — they must not read alike.
GEOCODE_CONFIDENCE_DEFAULTS: dict[str, float] = {
    "coord-parse": 1.0,
    "gazetteer": 0.9,
    "relative-offset": 0.5,
    "nominatim": 0.4,
}


def geocode_confidences(config: object) -> dict[str, float]:
    """The per-source geocode-confidence table from live config, over the built-in defaults."""
    override = getattr(getattr(config, "places", None), "geocode_confidence", None) or {}
    return {**GEOCODE_CONFIDENCE_DEFAULTS, **{k: float(v) for k, v in dict(override).items()}}


def _mgrs_token(s: str) -> str | None:
    """The packed, upper-cased MGRS token embedded in ``s`` — or ``None`` if the shape isn't a grid.

    Shape-only: it says "this text states a military grid reference", not "this grid is real". A
    malformed grid (bad zone, unequal easting/northing, odd digit count) is **rejected here** rather
    than coerced into a coordinate — the caller then treats the string as an ordinary toponym.
    """
    for m in _MGRS_TOKEN_RE.finditer(s):
        if not 1 <= int(m.group("zone")) <= 60:
            continue
        parts = m.group("digits").split()
        if len(parts) == 2:
            if len(parts[0]) != len(parts[1]) or len(parts[0]) > 5:
                continue
        elif len(parts[0]) % 2 or len(parts[0]) > 10:
            continue
        return (m.group("zone") + m.group("band") + m.group("square") + "".join(parts)).upper()
    return None


def detect_surface_format(raw: str, declared: str | None = None) -> SurfaceFormat:
    """The **shape is authoritative**; ``declared`` (the extractor's label) is only a hint.

    Same principle the edge re-lane applies to relations — the endpoints decide the lane, the model's
    verb is advisory. An LLM that calls ``"Grid: 43S CT 23715 21242 (MGRS, WGS84)"`` a *toponym* sends
    it down the geocode path, where a grid can never resolve, and the exact coordinate is lost; the
    mirror bug (a place name labelled ``MGRS``) sends a name into a parser that can never match it.
    Classifying off the string itself removes both failure modes. ``declared`` survives only when the
    shape yields nothing *and* the declared format's own parser succeeds on the string.
    """
    fmt, parsed = _shape_of(raw)
    if parsed is None and declared in COORD_FORMATS and declared != fmt:
        alt = _COORD_PARSERS[declared](raw)
        if alt is not None:
            return declared  # type: ignore[return-value]
    return fmt


def _absolute_shapes(
    s: str,
) -> Iterator[tuple[SurfaceFormat, tuple[float, float, PrecisionClass] | None]]:
    """Every **absolute** coordinate shape ``s`` exhibits, most-specific first, each with its parse.

    Most-specific first is what keeps the loose shapes honest: a packed NOTAM ``495355N`` also matches
    the decimal-degree pattern, so DMS is offered before DD; a grid reference outranks both. Yielding
    (rather than returning) lets the caller skip a shape that *looked* like a coordinate but did not
    parse, when a better-supported reading of the same string exists.
    """
    if _mgrs_token(s) is not None:
        yield "MGRS", _parse_mgrs(s)
    if _UTM_RE.match(s):
        yield "UTM", _parse_utm(s)
    if _DMS_MARKER_RE.search(s):
        yield "DMS", _parse_dms(s)
    elif _DMS_LAT_RE.search(s) and _DMS_LON_RE.search(s):
        dd = _parse_dd(s)  # no sexagesimal marker anywhere → a hemisphere-suffixed DD pair
        yield ("DD", dd) if dd is not None else ("DMS", _parse_dms(s))
    else:
        dd = _parse_dd(s)
        if dd is not None or _DD_RE.match(s):
            yield "DD", dd


def _shape_of(s: str) -> tuple[SurfaceFormat, tuple[float, float, PrecisionClass] | None]:
    """Classify ``s`` by shape and, where the shape is a coordinate, parse it in the same pass.

    Returning the parse alongside the label is what makes the classification *verified*: a format is
    only claimed when either its parser succeeded or the shape is unmistakable-but-unparseable (a
    well-formed grid the ``mgrs`` lib rejects), never on a guess.

    **Precedence is explicit and ordered — an absolute fix outranks a relative one.** Sources state a
    position the way a human writes it: the exact reference *and* a landmark gloss, in one breath
    ("Grid: 43S CT 23715 21242 (MGRS, WGS84), ~1.5 km NE of the main Nur Khan runway threshold"). That
    string is an absolute fix with a descriptive tail, not a relative fix; reading the tail as the
    format throws away the only exact coordinate in the sentence and leaves the site unplottable. So:

    1. a map **URL** (the whole string is a link, nothing else can be true of it);
    2. a parseable **absolute coordinate** anywhere in the string — grid, UTM, DMS, decimal degrees;
    3. **relative-position language** (``<dist> <bearing> of <anchor>``) — the fallback, and the only
       reading left when no coordinate is actually recoverable;
    4. otherwise a **toponym**.

    The one concession at (2): a shape that *looks* like a coordinate but does not parse loses to a
    relative phrase that does. Relative prose carries bare numbers ("12-15 km NE of Sargodha" trips
    the sexagesimal-separator pattern), and an unparseable label would strand the string with no
    coordinate at all — where the relative branch can still geocode the anchor and offset it.
    """
    low = s.strip().lower()
    if low.startswith(("http://", "https://", "geo:")) or "maps." in low or "/@" in s:
        return "url", _parse_url(s)
    relative = _REL_LOC_RE.search(s) is not None
    for fmt, parsed in _absolute_shapes(s):
        if parsed is not None or not relative:
            return fmt, parsed
    if relative:
        return "relative", None
    return "toponym", None


def _precision_from_dd(lat_str: str, lon_str: str) -> PrecisionClass:
    """Coordinate stated-resolution → precision class (a *source-axis* precision, not node semantics).

    INGEST cannot know a node's semantic precision (that's a subject/ontology fact RESOLVE owns); it
    can say how tightly the *surface form* pinned the point. ≥4 decimals ≈ ≤~10 m → ``pad``; 2-3 dp ≈
    site scale → ``site``; coarser → ``city``.
    """
    dp = max(len((lat_str.split(".") + [""])[1]), len((lon_str.split(".") + [""])[1]))
    if dp >= 4:
        return "pad"
    if dp >= 2:
        return "site"
    return "city"


def _dms_to_decimal(token: str, hemi: str) -> float | None:
    """One hemisphere-terminated component (``32°14′20″``, ``34-29.00``, packed ``495355``) → decimal."""
    body = token.strip().strip("°′″'\".:- ")
    packed = re.fullmatch(r"\d{4,7}", body)  # NOTAM packed DDMM(SS) / DDDMM(SS), no separators
    if packed:
        is_lat = hemi.upper() in "NS"
        digits = body
        deg_len = 2 if is_lat else 3
        deg = float(int(digits[:deg_len]))
        rest = digits[deg_len:]
        minutes = float(int(rest[:2])) if len(rest) >= 2 else 0.0
        seconds = float(int(rest[2:4])) if len(rest) >= 4 else 0.0
        val = deg + minutes / 60 + seconds / 3600
    else:
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", body)]
        if not nums:
            return None
        deg = nums[0]
        minutes = nums[1] if len(nums) > 1 else 0.0
        seconds = nums[2] if len(nums) > 2 else 0.0
        val = deg + minutes / 60 + seconds / 3600
    return -val if hemi.upper() in "SW" else val


def _dms_precision(s: str) -> PrecisionClass:
    """DMS resolution → precision: seconds present → pad; minute-only → site; degree-only → city."""
    if re.search(r"\d{6,7}[NnSsEeWw]", s) or re.search(r"[′'.:\- ]\s*\d+\s*[″\"]", s):
        return "pad"
    if re.search(r"\d[°:\- ]\s*\d", s):
        return "site"
    return "city"


def _parse_dd(s: str) -> tuple[float, float, PrecisionClass] | None:
    m = _DD_RE.match(s)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(3))
    if m.group(2) and m.group(2).upper() == "S":
        lat = -abs(lat)
    if m.group(4) and m.group(4).upper() == "W":
        lon = -abs(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon, _precision_from_dd(m.group(1), m.group(3))


def _parse_dms(s: str) -> tuple[float, float, PrecisionClass] | None:
    lat_m, lon_m = _DMS_LAT_RE.search(s), _DMS_LON_RE.search(s)
    if not lat_m or not lon_m:
        return None
    lat = _dms_to_decimal(lat_m.group(1), lat_m.group(2))
    lon = _dms_to_decimal(lon_m.group(1), lon_m.group(2))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon, _dms_precision(s)


def _parse_mgrs(s: str) -> tuple[float, float, PrecisionClass] | None:
    """Decode the grid reference stated anywhere in ``s`` (prose wrapper and all) → WGS84."""
    packed = _mgrs_token(s)
    if packed is None:
        return None
    try:
        import mgrs  # optional dep (REPORT); grid → WGS84
    except ImportError:
        return None
    digits = re.sub(r"^\d{1,2}[C-X][A-Z]{2}", "", packed)
    try:
        lat, lon = mgrs.MGRS().toLatLon(packed)
    except Exception:  # noqa: BLE001 - the mgrs lib raises bare errors on malformed grids
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    per_axis = len(digits) // 2
    precision: PrecisionClass = "pad" if per_axis >= 3 else "site" if per_axis == 2 else "city"
    return float(lat), float(lon), precision


def _parse_utm(s: str) -> tuple[float, float, PrecisionClass] | None:
    m = _UTM_RE.match(s)
    if not m:
        return None
    try:
        import utm  # optional dep (REPORT); zone/easting/northing → WGS84
    except ImportError:
        return None
    try:
        lat, lon = utm.to_latlon(float(m.group(3)), float(m.group(4)), int(m.group(1)),
                                 m.group(2).upper())
    except Exception:  # noqa: BLE001 - utm raises bare OutOfRange errors on invalid zones
        return None
    return float(lat), float(lon), "pad"


def _parse_url(s: str) -> tuple[float, float, PrecisionClass] | None:
    for rx in _URL_COORD_RES:
        m = rx.search(s)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, _precision_from_dd(m.group(1), m.group(2))
    return None


_COORD_PARSERS: dict[str, Callable[[str], tuple[float, float, PrecisionClass] | None]] = {
    "DD": _parse_dd, "DMS": _parse_dms, "MGRS": _parse_mgrs, "UTM": _parse_utm, "url": _parse_url,
}


def normalize_location(
    raw: str | None,
    *,
    surface_format: str | None = None,
    geocoder: Geocoder | None = None,
    confidences: Mapping[str, float] | None = None,
) -> Location | None:
    """Normalize a stated location — **Stage A** of the location system (md/13 §2), pre-resolution.

    Deterministic coordinate canonicalisation (DD / DMS incl. packed NOTAM + decimal-minute NAVAREA /
    MGRS / UTM / map-URL) freezes ``wgs84_lat/lon`` + a coordinate-resolution ``precision_class``. A
    toponym or a relative ``"<dist> <bearing> of <place>"`` ref is geocoded via the injected
    ``geocoder`` (the **Rahwali beat**: geocode the anchor, apply a great-circle offset — the offset is
    canonical, the anchor kept as a candidate). ``resolved_place_ref`` is always left ``None`` — place
    *resolution* against the gazetteer (Stage B, distinct-from) is RESOLVE's job at rebuild.

    A blank input → ``None``. An unresolvable but stated location still returns a ``Location`` carrying
    ``raw`` + ``surface_format`` (no coords) so the claim keeps its provenance for RESOLVE to try.

    ``surface_format`` is the extractor's **declared** label and is treated as a hint only: the string's
    own shape decides the branch (:func:`detect_surface_format`). A grid the model mislabelled a toponym
    still gets canonicalised; a place name it mislabelled a grid still gets geocoded.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None

    conf = {**GEOCODE_CONFIDENCE_DEFAULTS,
            **(getattr(geocoder, "confidences", None) or {}),
            **(confidences or {})}

    fmt, parsed = _shape_of(s)
    if parsed is None and surface_format in COORD_FORMATS and surface_format != fmt:
        # The shape yielded nothing; honour the declared format only if its parser actually works.
        alt = _COORD_PARSERS[surface_format](s)
        if alt is not None:
            fmt, parsed = surface_format, alt  # type: ignore[assignment]

    if parsed is not None:
        lat, lon, precision = parsed
        return Location(
            raw=s, surface_format=fmt, wgs84_lat=lat, wgs84_lon=lon,
            precision_class=precision,
            geocode_candidates=[GeocodeCandidate(lat=lat, lon=lon, source="coord-parse",
                                                 confidence=conf["coord-parse"])],
        )
    if fmt in COORD_FORMATS:
        # A coord we couldn't parse (missing optional dep, malformed) — keep the stated form for RESOLVE.
        return Location(raw=s, surface_format=fmt)

    if fmt == "relative":
        return _resolve_relative_location(s, geocoder, conf)
    return _resolve_toponym(s, geocoder, conf)


def _resolve_relative_location(s: str, geocoder: Geocoder | None,
                               conf: Mapping[str, float]) -> Location:
    """The Rahwali beat: parse ``<dist> <bearing> of <anchor>``, geocode anchor, offset great-circle."""
    m = _REL_LOC_RE.search(s)
    if not m:
        return Location(raw=s, surface_format="relative")
    anchor_name = m.group("anchor").strip().rstrip(".,;")
    gc = geocoder  # opt-in ONLY: no injected geocoder → offline (no network in the claim path; G1/G2)
    hit = gc.geocode(anchor_name) if gc is not None else None
    if hit is None:
        return Location(raw=s, surface_format="relative", proposed_alias=anchor_name)

    anchor_source = getattr(hit, "source", "nominatim")  # gazetteer coord-cache vs Nominatim open world
    dist_km = float(m.group("dist")) * _UNIT_KM[m.group("unit").lower()]
    bearing = _BEARINGS[m.group("bearing").upper()]
    try:
        from geopy.distance import distance as _distance
        from geopy.point import Point
    except ImportError:  # pragma: no cover - geopy is a hard dep
        return Location(raw=s, surface_format="relative", proposed_alias=anchor_name,
                        geocode_candidates=[GeocodeCandidate(
                            lat=hit.latitude, lon=hit.longitude, label=anchor_name,
                            source=anchor_source, confidence=conf.get(anchor_source))])
    dest = _distance(kilometers=dist_km).destination(Point(hit.latitude, hit.longitude), bearing)
    return Location(
        raw=s, surface_format="relative",
        wgs84_lat=float(dest.latitude), wgs84_lon=float(dest.longitude),
        proposed_alias=anchor_name,
        geocode_candidates=[
            GeocodeCandidate(lat=float(dest.latitude), lon=float(dest.longitude),
                             label=s, source="coord-parse",
                             confidence=conf["relative-offset"]),
            GeocodeCandidate(lat=hit.latitude, lon=hit.longitude, label=anchor_name,
                             source=anchor_source, confidence=conf.get(anchor_source)),
        ],
    )


def _resolve_toponym(s: str, geocoder: Geocoder | None, conf: Mapping[str, float]) -> Location:
    """Geocode a stated place name → freeze WGS84 + a candidate + the proposed alias (RESOLVE adjudicates)."""
    gc = geocoder  # opt-in ONLY: no injected geocoder → offline (no network in the claim path; G1/G2)
    hit = gc.geocode(s) if gc is not None else None
    if hit is None:
        return Location(raw=s, surface_format="toponym", proposed_alias=s)
    source = getattr(hit, "source", "nominatim")
    return Location(
        raw=s, surface_format="toponym",
        wgs84_lat=hit.latitude, wgs84_lon=hit.longitude, proposed_alias=s,
        geocode_candidates=[GeocodeCandidate(lat=hit.latitude, lon=hit.longitude,
                            label=getattr(hit, "address", None),
                            source=source, confidence=conf.get(source))],
    )


# ── Quantities ─────────────────────────────────────────────────────────────────────────────────

_COUNT_STATES: frozenset[str] = frozenset(
    ("ordered", "delivered", "fielded", "nominal", "combat-ready")
)
_UNIT_PLURALS = {
    "tels": "TEL", "systems": "system", "batteries": "battery", "launchers": "launcher",
    "vehicles": "vehicle", "units": "unit", "missiles": "missile", "rounds": "round",
    "sites": "site", "radars": "radar", "interceptors": "interceptor", "regiments": "regiment",
    "battalions": "battalion",
}
_MEASURE_UNITS = frozenset(("km", "m", "nm", "mi", "cm", "mm", "kg", "t", "km/h", "%", "°"))
_RANGE_QTY_RE = re.compile(
    r"(?P<lo>\d+(?:\.\d+)?)\s*[-–—]\s*(?P<hi>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z%°/][A-Za-z%°/\-]*)?"
)
_SINGLE_QTY_RE = re.compile(
    r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z%°/][A-Za-z%°/\-]*)?"
)


def _norm_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    low = unit.lower()
    if low in _MEASURE_UNITS:
        return low
    if low in _UNIT_PLURALS:
        return _UNIT_PLURALS[low]
    return unit


def _spelled_count(low: str) -> int | None:
    for word, n in _SPELLED.items():
        if re.search(rf"\b{re.escape(word)}\b", low):
            return n
    return None


def normalize_quantity(raw: str | None, *, count_state: str | None = None) -> Quantity | None:
    """Normalize a stated quantity to an evidence-graded ``Quantity`` (a point value or min/max range).

    Handles counts (``"2 systems"``, ``"a battalion of ~6 TELs"``), ranges (``"90-110m"``, ``"40–150
    km"``), and measures (``"~125 km"``). ``count_state`` (``ordered`` ≠ ``delivered`` ≠ ``fielded`` —
    never collapsed) is passed through when valid. ``~`` / ``approx`` / ``roughly`` set ``approx``.
    A string with no number → ``None`` (no fabricated count).
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    low = s.lower()
    approx = bool(_APPROX_RE.search(s))
    state: CountState | None = count_state if count_state in _COUNT_STATES else None  # type: ignore[assignment]

    m = _RANGE_QTY_RE.search(s)
    if m:
        return Quantity(min=float(m.group("lo")), max=float(m.group("hi")),
                        unit=_norm_unit(m.group("unit")), count_state=state, approx=approx)
    m = _SINGLE_QTY_RE.search(s)
    if m:
        return Quantity(value=float(m.group("val")), unit=_norm_unit(m.group("unit")),
                        count_state=state, approx=approx)

    spelled = _spelled_count(low)
    if spelled is not None:
        return Quantity(value=float(spelled), count_state=state, approx=approx)
    return None
