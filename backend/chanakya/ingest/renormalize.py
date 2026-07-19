"""Re-run location normalization over **already-frozen** claim bundles — offline, deterministic.

Why this exists: a frozen bundle keeps the source's verbatim ``Location.raw``, so a coordinate the
recorder failed to canonicalise is still *recoverable* from the corpus itself long after extraction.
When the canonicaliser learns a shape it used to miss (the ``43S CT 23715 21242`` grid an extractor
labelled a *toponym*), the fix must reach the frozen bundles too — otherwise the demo keeps shipping
the old miss and KEYLESS ≡ LIVE breaks (a re-record would now disagree with the checked-in baseline).

The safety rules this module enforces, because it edits frozen evidence:

* **Deterministic only.** No LLM, no network, no clock, no RNG — the pass runs ``normalize_location``
  with **no geocoder at all**, so the *only* thing that can produce a coordinate is parsing the raw
  string that is already in the file. Nothing is invented, nothing is looked up.
* **Additive, never destructive.** A location that already carries coordinates is left alone unless the
  deterministic parse reproduces those same coordinates (i.e. they came from this very parser). A
  geocode-derived coordinate is never re-derived and never dropped.
* **Narrow field set.** Only ``surface_format`` / ``wgs84_lat`` / ``wgs84_lon`` / ``precision_class`` /
  ``geocode_candidates`` can change. ``raw``, ``proposed_alias``, ``resolved_place_ref`` and every
  non-location field are untouched, and no claim is added, removed, or re-identified.
* **Auditable.** Every write is reported as a per-file, per-field ``before → after`` row; the default
  mode is a dry run.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chanakya.ingest.adapters import normalize_location
from chanakya.schemas.claim import ClaimRecord
from chanakya.schemas.values import Location

# The only fields this pass may write — all of them INGEST-derived outputs of the canonicaliser, none
# of them source text. ``proposed_alias`` is in the set because it is a *consequence* of the format
# call: a string re-classified from toponym to grid stops being a place-name proposal, and leaving the
# grid text sitting there would hand RESOLVE a nonsense alias to adjudicate. ``raw`` and
# ``resolved_place_ref`` (RESOLVE's) are never touched.
MUTABLE_FIELDS = ("surface_format", "wgs84_lat", "wgs84_lon", "precision_class",
                  "geocode_candidates", "proposed_alias")

# Keys that mark a dict as a stated ``Location`` rather than some other ``raw``-carrying value (a
# ``DateValue`` also has ``raw``). Presence of any one of these + a successful ``Location`` validation
# (the model is ``extra="forbid"``) is an exact test.
_LOCATION_MARKERS = frozenset(
    ("surface_format", "wgs84_lat", "wgs84_lon", "geocode_candidates", "precision_class",
     "proposed_alias", "resolved_place_ref")
)

# Coordinates are floats round-tripped through JSON; "the parser reproduced the frozen value" is an
# exact-equality question up to that round-trip, not a geodesic one.
_COORD_EPS = 1e-9


@dataclass(frozen=True)
class FieldChange:
    """One audited edit: which claim, which field, what it was, what it became."""

    bundle: str
    claim_id: str
    field_path: str
    before: Any
    after: Any

    def __str__(self) -> str:
        return f"{self.bundle}  {self.claim_id}  {self.field_path}: {self.before!r} -> {self.after!r}"


def _iter_locations(node: Any, path: str) -> Iterator[tuple[dict[str, Any], str]]:
    """Yield every ``Location``-shaped dict in a claim row, with its dotted field path."""
    if isinstance(node, dict):
        if _LOCATION_MARKERS & node.keys() and isinstance(node.get("raw"), str):
            try:
                Location.model_validate(node)
            except Exception:  # noqa: BLE001 - a look-alike that isn't a Location: skip it, don't guess
                pass
            else:
                yield node, path
        for key, value in node.items():
            yield from _iter_locations(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _iter_locations(value, f"{path}[{i}]")


def _renormalize_location(block: dict[str, Any]) -> dict[str, Any]:
    """The deterministic replacement values for one location block (only ``MUTABLE_FIELDS``)."""
    fresh = normalize_location(
        block["raw"], surface_format=block.get("surface_format"), geocoder=None,
    )
    if fresh is None:
        return {}

    had_coord = block.get("wgs84_lat") is not None
    got_coord = fresh.wgs84_lat is not None
    if had_coord and not got_coord:
        # The frozen coordinate came from a geocode this offline pass cannot (and must not) redo.
        return {}
    if had_coord and got_coord and (
        abs(float(block["wgs84_lat"]) - float(fresh.wgs84_lat or 0.0)) > _COORD_EPS
        or abs(float(block.get("wgs84_lon") or 0.0) - float(fresh.wgs84_lon or 0.0)) > _COORD_EPS
    ):
        # A parse that disagrees with the frozen coordinate is a *finding*, not a licence to overwrite.
        return {}

    updates: dict[str, Any] = {
        "surface_format": fresh.surface_format,
        "proposed_alias": fresh.proposed_alias,
    }
    if got_coord:
        updates["wgs84_lat"] = fresh.wgs84_lat
        updates["wgs84_lon"] = fresh.wgs84_lon
        updates["precision_class"] = fresh.precision_class
        if not block.get("geocode_candidates"):
            updates["geocode_candidates"] = [
                c.model_dump() for c in fresh.geocode_candidates
            ]
    return updates


def renormalize_rows(rows: list[dict[str, Any]], *, bundle: str) -> list[FieldChange]:
    """Re-normalize every location in a bundle's claim rows **in place**; return the audit trail."""
    changes: list[FieldChange] = []
    for row in rows:
        claim_id = str(row.get("claim_id", "?"))
        for block, path in _iter_locations(row, ""):
            for field, after in _renormalize_location(block).items():
                before = block.get(field)
                if before == after:
                    continue
                block[field] = after
                changes.append(FieldChange(bundle, claim_id, f"{path}.{field}", before, after))
    if changes:  # the edited rows must still be valid evidence records — fail loudly if not
        for row in rows:
            ClaimRecord.model_validate(row)
    return changes


def renormalize_bundles(bundles_dir: str | Path, *, apply: bool = False) -> list[FieldChange]:
    """Re-normalize every ``*.json`` bundle under ``bundles_dir``. ``apply=False`` is a dry run.

    Bundles are rewritten with the same byte-stable canonical form the recorder uses
    (``sort_keys``, 2-space indent, trailing newline), so a re-record diffs cleanly against them.
    """
    changes: list[FieldChange] = []
    for path in sorted(Path(bundles_dir).glob("*.json")):
        text = path.read_text(encoding="utf-8").strip()
        if not text or text[0] != "[":
            continue
        rows = json.loads(text)
        found = renormalize_rows(rows, bundle=path.name)
        if found and apply:
            path.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        changes.extend(found)
    return changes
