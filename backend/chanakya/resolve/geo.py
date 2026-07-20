"""Where an entity *says* it is — the one reader of a frozen coordinate, shared by the scorer and
the gazetteer matcher.

These three helpers used to live in :mod:`chanakya.resolve.places`, which imports :mod:`.cluster`;
:mod:`.scoring` is imported *by* ``cluster``, so the scorer could not reach them without a cycle. They
are pure functions of an attrs mapping and belong to neither side, so they live here and ``places``
re-exports them — "where the coordinate lives" is still stated exactly once (md/13 §2).

Nothing here geocodes, matches a gazetteer, or invents a position: it reads the WGS84 point INGEST
already froze onto the claim, or reports that there is none.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from geopy.distance import geodesic

from .entities import Entity

Coords = tuple[float, float]

# The attr slots INGEST may freeze a canonical ``Location`` into, best-first. One list, shared with the
# view assembly, so "where the coordinate lives" is stated once rather than re-guessed per reader.
LOCATION_ATTRS: tuple[str, ...] = ("coordinates", "wgs84", "location")


def location_attr(attrs: Mapping[str, Any]) -> Any:
    """The frozen-location value on an entity's attrs, whichever of :data:`LOCATION_ATTRS` INGEST used."""
    for key in LOCATION_ATTRS:
        value = attrs.get(key)
        if value:
            return value
    return None


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


def entity_coords(entity: Entity) -> Coords | None:
    """The WGS84 point this entity's own claims froze onto it, or ``None`` if it states no coordinate.

    Never a gazetteer coordinate and never a guess — an entity that only names a toponym has no point
    here, and "no point" must read as *unknown*, never as "somewhere else".
    """
    return parse_coords(location_attr(entity.attrs))


def separation_km(a: Entity, b: Entity) -> float | None:
    """Geodesic km between two entities' own frozen coordinates; ``None`` if either states none.

    Pure math (``geopy.distance.geodesic``) — offline, no network, gate G1.
    """
    ca, cb = entity_coords(a), entity_coords(b)
    if ca is None or cb is None:
        return None
    return float(geodesic(ca, cb).km)
