"""Value objects carried on the claim payload — **shapes F0-freezes; adapters INGEST owns**.

Three payload fields carry structure that needs normalization (master §4.2). F0 freezes the
*shapes + canonical slots*; the *normalization adapters* (Nominatim geocode, label→ISO, DMS→WGS84)
are INGEST-owned and run **at extraction, pre-append — never as on-instantiation validators**
(a validator would fire the network/parse on every ``rebuild()`` reload → break gate G1). So the
models here do **zero** network/parse work; ``raw`` + canonical slots coexist, and INGEST fills
the canonical slots once, upstream of the append.

* ``Date`` — adapted from the ``DateSpec``/``Period`` pattern (calendar-only; no fiscal machinery).
  A point date is ``ExactDate`` or ``LabelDate``; an interval is ``Period``. ``canonical_iso_bounds``
  is a **pure, offline** helper (stdlib calendar math) SCORE reads for freshness/ordering — safe in
  the rebuild call-path.
* ``Location`` — raw stated string(s) + surface hint, plus the canonical WGS84 form + geocode
  candidates + a proposed place alias (frozen by INGEST; ``resolved_place_ref`` filled by RESOLVE).
* ``Quantity`` — evidence-graded ranges with a ``count_state`` (ordered≠delivered≠fielded).
"""

from __future__ import annotations

import calendar
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ── Dates ────────────────────────────────────────────────────────────────────────────────────

Granularity = Literal["year", "half", "quarter", "month", "day"]
# Provenance of the ISO boundaries: stated verbatim / derived from a coarse label /
# resolved from a relative phrase against report_time / a bare model guess (flagged, low trust).
BoundarySource = Literal["explicit", "derived_from_label", "relative", "model_guess"]


class _DateBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExactDate(_DateBase):
    """A resolved point date. ``iso_date`` is ``YYYY-MM-DD`` (INGEST clamps 2024-11-31 → -30)."""

    kind: Literal["exact"] = "exact"
    iso_date: str
    raw: str = ""
    boundary_source: BoundarySource = "explicit"


class LabelDate(_DateBase):
    """A coarse-granularity label the LLM emits ("Q4 2021", "2016"). INGEST derives the ISO bounds."""

    kind: Literal["label"] = "label"
    raw: str = ""
    granularity: Granularity
    year: int
    quarter: int | None = None  # 1–4 when granularity == quarter
    half: int | None = None  # 1–2 when granularity == half
    month: int | None = None  # 1–12 when granularity == month/day
    day: int | None = None  # 1–31 when granularity == day
    boundary_source: BoundarySource = "derived_from_label"


DateSpec = ExactDate | LabelDate


class Period(_DateBase):
    """An interval ``event_time`` — ``as_of`` (a single anchor) or ``range`` (start..end).

    ``approximate`` marks circa/reported/relative-derived intervals (master §4.2 relative form).
    """

    kind: Literal["period"] = "period"
    period_type: Literal["as_of", "range"]
    as_of: DateSpec | None = None
    start: DateSpec | None = None
    end: DateSpec | None = None
    approximate: bool = False


# Any date-valued field on a claim. Discriminated on ``kind`` so unions parse unambiguously.
DateValue = ExactDate | LabelDate | Period


def _label_bounds(d: LabelDate) -> tuple[str, str]:
    """(start_iso, end_iso) for a coarse label — pure calendar arithmetic, no parsing."""
    y = d.year
    if d.granularity == "year":
        return f"{y:04d}-01-01", f"{y:04d}-12-31"
    if d.granularity == "half":
        h = d.half or 1
        return (f"{y:04d}-01-01", f"{y:04d}-06-30") if h == 1 else (f"{y:04d}-07-01", f"{y:04d}-12-31")
    if d.granularity == "quarter":
        q = d.quarter or 1
        sm = 3 * (q - 1) + 1
        em = sm + 2
        return f"{y:04d}-{sm:02d}-01", f"{y:04d}-{em:02d}-{calendar.monthrange(y, em)[1]:02d}"
    if d.granularity == "month":
        m = d.month or 1
        return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    # day
    m, day = d.month or 1, d.day or 1
    return f"{y:04d}-{m:02d}-{day:02d}", f"{y:04d}-{m:02d}-{day:02d}"


def canonical_iso_bounds(value: DateValue | None) -> tuple[str | None, str | None]:
    """Resolve any date value to ``(earliest_iso, latest_iso)`` — **pure, offline, rebuild-safe**.

    SCORE reads this for freshness (age from the latest bound) and supersede ordering. Returns
    ``(None, None)`` when a value is missing or a label is under-specified. Never parses ``raw`` —
    only the structured slots INGEST already resolved.
    """
    if value is None:
        return None, None
    if isinstance(value, ExactDate):
        return value.iso_date, value.iso_date
    if isinstance(value, LabelDate):
        return _label_bounds(value)
    # Period
    if value.period_type == "as_of" and value.as_of is not None:
        lo, hi = canonical_iso_bounds(value.as_of)
        return lo, hi
    lo = canonical_iso_bounds(value.start)[0] if value.start is not None else None
    hi = canonical_iso_bounds(value.end)[1] if value.end is not None else None
    return lo, hi


def _has_explicit_validity_interval(value: DateValue | None) -> bool:
    """True only for a **closed** ``Period`` range — an explicitly *stated* start..end validity window.

    A point/coarse date (``ExactDate``/``LabelDate``) or an ``as_of`` period is a *when-true* anchor, not
    a "valid until": it says the value held around then, never that it stopped holding then. So it does
    **not** bound validity from above — the report date does (see :func:`report_bounded_validity`).
    """
    return isinstance(value, Period) and value.period_type == "range" and value.end is not None


def report_bounded_validity(
    event_time: DateValue | None, report_time: DateValue | None
) -> tuple[str | None, str | None]:
    """``(valid_from, valid_until)`` for a value — **report_time is an upper bound on validity** (D7, §1B).

    Pure, offline, rebuild-safe (reads only :func:`canonical_iso_bounds`; no clock/parse — G1). A value
    asserted true at ``event_time`` is presumed valid only up to when its source could still vouch for it
    — its report date. So:

    * ``valid_from``  = the lower bound of ``event_time`` (the stated validity **anchor**), else ``None``.
    * ``valid_until`` = ``event_time``'s **explicit** upper bound when it states a closed validity interval
      (a ``Period`` ``range`` with an ``end``); otherwise ``report_time``'s upper bound. ``None`` when
      neither axis is available.

    This only **records** the coupling. No ordering / supersede / staleness decision is made here — that
    logic (the succession core) is deferred to Stage 3B, which consumes this data.
    """
    ev_lo, ev_hi = canonical_iso_bounds(event_time)
    _, rep_hi = canonical_iso_bounds(report_time)
    valid_from = ev_lo
    explicit_end = ev_hi if _has_explicit_validity_interval(event_time) else None
    valid_until = explicit_end if explicit_end is not None else rep_hi
    return valid_from, valid_until


# ── Locations ────────────────────────────────────────────────────────────────────────────────

# Coarsest identity a place node needs (md/13; matches config/places.yaml precision_class).
# Ordered coarsest-last. ``province`` is the admin-level-1 rung the corpus forced open: sources really
# do say "central Punjab" / "Sindh province, Pakistan", and the only two honest renderings of that are
# an area envelope or nothing at all — calling it a ``city`` would draw a ~150 km uncertainty as a
# 15 km one, i.e. assert a precision no source stated.
PrecisionClass = Literal["pad", "site", "terminal", "district", "city", "province"]
# How the location was stated in the source (drives the coord-canonicaliser branch in INGEST).
SurfaceFormat = Literal["DD", "DMS", "MGRS", "UTM", "url", "toponym", "relative"]


class GeocodeCandidate(BaseModel):
    """One WGS84 candidate for an ambiguous place — INGEST freezes these so keyless ingest is offline."""

    model_config = ConfigDict(extra="forbid")
    lat: float
    lon: float
    label: str | None = None
    source: str | None = None  # "coord-parse" | "nominatim" | "gazetteer"
    confidence: float | None = None


class Location(BaseModel):
    """Stated location + the canonical WGS84 form INGEST resolves; ``resolved_place_ref`` is RESOLVE's."""

    model_config = ConfigDict(extra="forbid")
    raw: str | list[str]
    surface_format: SurfaceFormat | None = None
    # Canonical stored form (filled by the INGEST Location adapter, pre-append):
    wgs84_lat: float | None = None
    wgs84_lon: float | None = None
    geocode_candidates: list[GeocodeCandidate] = []
    precision_class: PrecisionClass | None = None
    # A place-name/alias INGEST proposes (LLM/Nominatim), frozen for RESOLVE to adjudicate at rebuild.
    proposed_alias: str | None = None
    # Filled by RESOLVE (place-resolution against the gazetteer) at rebuild — not by INGEST.
    resolved_place_ref: str | None = None


# ── Quantities ───────────────────────────────────────────────────────────────────────────────

# Kept separate on purpose: SIPRI counts *deliveries*, a tender implies *ordered*, imagery shows
# *fielded* — never collapse them (master §4.2; C/01 evidence-graded ranges).
CountState = Literal["ordered", "delivered", "fielded", "nominal", "combat-ready"]


class Quantity(BaseModel):
    """An evidence-graded quantity: a point ``value`` or a ``min``/``max`` range, plus count-state."""

    model_config = ConfigDict(extra="forbid")
    value: float | None = None
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    count_state: CountState | None = None
    approx: bool = False
