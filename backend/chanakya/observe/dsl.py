"""The observable condition DSL — value-level operators + field access + the geo predicate.

A tripwire condition is composed from operators over fields that **already exist** on the rebuilt
view (node/edge raw attrs + SCORE-precomputed materiality metrics + ``Location``). Because it only
reads existing view fields, adding an observable is a config edit, never code (spine/09 honest
boundary). Nothing scoring-shaped is hardcoded here: thresholds arrive as the config's ``value``,
severities from the observable, hop bounds/radii from the trigger — so gate **G6** stays green. No
LLM/network import lives in this package; ``geopy.distance`` is pure great-circle math (offline).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from geopy.distance import geodesic

from chanakya.schemas import EdgeView, EventView, NodeView

Element = NodeView | EdgeView | EventView

# Sentinel for "field absent" — kept distinct from a stored ``None`` so ``exists`` and the threshold
# operators can tell "we looked and it wasn't there" from "present but null" (never drop UNKNOWN as if
# it were a finding — spine/09 / criterion #10).
MISSING: Any = object()


def resolve_field(element: Element, path: str) -> Any:
    """Read a dotted ``path`` off a view element (pydantic attr → dict key), or ``MISSING``.

    Examples: ``target`` (edge target id), ``status``, ``attrs.occupancy_state``,
    ``materiality.chokepoint_count``, ``location.resolved_place_ref``. Any absent segment yields
    ``MISSING`` — the caller decides how UNKNOWN participates (comparisons treat it as not-satisfied;
    ``exists``/``not_exists`` report it honestly).
    """
    cur: Any = element
    for seg in path.split("."):
        if cur is MISSING or cur is None:
            return MISSING
        nxt = getattr(cur, seg, MISSING)
        if nxt is MISSING and isinstance(cur, dict):
            nxt = cur.get(seg, MISSING)
        cur = nxt
    return cur


def _num(x: Any) -> float | None:
    """Coerce to ``float`` for a threshold compare, or ``None`` if not a real number (UNKNOWN → no fire)."""
    if isinstance(x, bool) or x is MISSING or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _threshold(op: Callable[[float, float], bool]) -> Callable[[Any, Any], bool]:
    def run(actual: Any, expected: Any) -> bool:
        a, b = _num(actual), _num(expected)
        return a is not None and b is not None and op(a, b)

    return run


# The operator set (spine/09): equality / threshold / exists. "Crossing" (state-change) is a
# delta-level *mode* (evaluator.py), not a value op. Token names match the ``query_graph`` constraint
# vocabulary so the DSL and the retrieval tools speak one language. These are pure comparators; every
# number they compare arrives from config, never from here (G6).
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: a is not MISSING and a == b,
    "ne": lambda a, b: a is not MISSING and a != b,
    "lt": _threshold(lambda a, b: a < b),
    "le": _threshold(lambda a, b: a <= b),
    "gt": _threshold(lambda a, b: a > b),
    "ge": _threshold(lambda a, b: a >= b),
    "exists": lambda a, _b: a is not MISSING and a is not None,
    "not_exists": lambda a, _b: a is MISSING or a is None,
}


def evaluate_condition(element: Element, field: str, op: str, value: Any = None) -> bool:
    """Apply one ``op`` over ``element.<field>`` vs ``value``. Unknown op raises (fail loud, not silent)."""
    if op not in OPERATORS:
        raise ValueError(f"unknown observable operator {op!r}; expected one of {sorted(OPERATORS)}")
    return OPERATORS[op](resolve_field(element, field), value)


def within_area(node: NodeView, area: dict[str, Any]) -> bool | None:
    """Is ``node``'s WGS84 point inside ``area`` = ``{center:[lat,lon], radius_km}``? ``None`` if no coord.

    Great-circle distance via ``geopy`` (offline math — no geocoding/network). The radius comes from
    the observable config (``area['radius_km']``), never a literal (G6). This is the geofence primitive
    the location seam is built on; the demo does **not** wire a geofence tripwire (roadmap).
    """
    loc = node.location
    if loc is None or loc.wgs84_lat is None or loc.wgs84_lon is None:
        return None
    center = area.get("center")
    radius_km = area.get("radius_km")
    if not center or radius_km is None:
        return None
    dist_km = geodesic((loc.wgs84_lat, loc.wgs84_lon), (center[0], center[1])).km
    return bool(dist_km <= radius_km)
