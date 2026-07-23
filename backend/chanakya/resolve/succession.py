"""Succession classification over a single attribute's retained value series (Stage 3B-i).

Given the role-agnostic ``Entity.attr_history[attr]`` series (``resolve/entities.py``, Stage 3-prep —
every claim-asserted value for one attribute, time-ordered), decide **what the series *is*** as a matter
of pure temporal shape:

* a **single** settled value (no conflict, or one value corroborated many times),
* a clean **ordered** succession (the value changed over time, and the distinct values line up with no two
  *different* values true at the same/overlapping time — a state change we could later promote),
* a **contradiction** (two different values asserted over intersecting time on a single-valued slot), or
* an **unorderable** set (≥2 distinct values but a value carries no usable date, so the set can't be
  placed in time at all).

This reuses — one stage earlier, on *attribute values* rather than *edge targets* — the interval machinery
``view/supersede.py`` runs over a functional edge instance (``_interval``/``_relation`` there). Same reasoning:
the interval a value is asserted over is the **union** across its claims (a late restatement widens the
interval into overlap → contradiction, never a silent "newest"); an undated value makes the whole set
``unorderable`` rather than being guessed at (D-P4.4 iii).

One **deliberate divergence** from ``supersede`` on the vague-equal case: this core follows its own contract —
two different values whose intervals *overlap **or are equal*** (coarse or exact) are a **contradiction**; and
``unorderable`` is reserved strictly for a value that carries **no usable date** at all. (``supersede``, in its
edge-nomination context, instead routes two vague-identical intervals to a HITL ``candidate``; that is a
richer downstream routing decision, not a classification, and is out of scope here.)

**Pure, deterministic, additive.** No clock / RNG / parse (reuses the offline ``canonical_iso_bounds``) — safe
in the ``rebuild()`` call-path (gates G1/G2). It makes **no** resolution decision: no scoring, veto, banding,
merge, or Partition change happens here. Nothing consumes this yet; Stage 3B-ii is the first reader. The
sibling ``view/supersede.py`` is left untouched — a later cleanup may unify the two; not now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chanakya.resolve.entities import AttrClaim, Entity, _attr_history_sort_key, unordered_pairs
from chanakya.schemas import canonical_iso_bounds

# Status strings (the classification result) — also the internal pair-relation vocabulary, since a pair's
# relation maps one-to-one onto the set-level status it induces. Kept as named constants (strings, not
# scoring numbers — gate G6) so the test surface and Stage 3B-ii bind to the same tokens.
SINGLE, ORDERED, CONTRADICTION, UNORDERABLE = "single", "ordered", "contradiction", "unorderable"


@dataclass(frozen=True)
class SuccessionResult:
    """The temporal verdict on one attribute's value series.

    ``ordered`` is always the full input sorted oldest→newest (best-effort, deterministic) — empty only for
    an empty input. ``current`` is the newest value **when well-defined** (``single``/``ordered``), else
    ``None`` (a contradiction or an unorderable set has no single current value).
    """

    status: str  # one of: SINGLE | ORDERED | CONTRADICTION | UNORDERABLE
    ordered: list[AttrClaim]  # the claims sorted oldest → newest (deterministic; empty if input empty)
    current: AttrClaim | None  # the newest value when well-defined, else None


def _interval(claims: list[AttrClaim]) -> tuple[str, str] | None:
    """The ``event_time`` **interval** these claims assert a value over — the **union** of their bounds,
    or ``None`` when any claim is undated / only half-bounded (mirrors ``supersede._interval``).

    ``None`` ⇒ "no usable date" (D-P4.4 iii: *missing* is unorderable, never guessed). Taking the union
    (not ``max``) means a late restatement of an old value widens that value's interval into overlap →
    contradiction, rather than silently making the old value look "newest".
    """
    bounds = [canonical_iso_bounds(c.event_time) for c in claims]
    if any(lo is None or hi is None for lo, hi in bounds):
        return None
    return min(lo for lo, _ in bounds if lo), max(hi for _, hi in bounds if hi)


def _relation(older: tuple[str, str], newer: tuple[str, str]) -> str:
    """Classify a pair of **dated** value-intervals, given ``older`` sorts at or before ``newer``.

    * **disjoint, older strictly earlier** (``older_hi < newer_lo``) → ``ORDERED`` (a clean state change)
    * **anything else** — the intervals overlap, touch, or are equal → ``CONTRADICTION``: two different
      values asserted over intersecting/identical time on a single-valued slot cannot be a succession.

    Per this core's contract ("intervals overlap **or are equal** → contradiction"), an *equal* interval —
    coarse (both "2025") or exact (both "2025-03-27") — is a contradiction, not something to route to the
    analyst. ``unorderable`` is reserved for the strictly *undated* case, short-circuited upstream in
    :func:`classify_succession`. (This is the intentional divergence from ``supersede._relation`` noted in
    the module docstring.)
    """
    (_, o_hi), (n_lo, _) = older, newer
    return ORDERED if o_hi < n_lo else CONTRADICTION


def _distinct_value_intervals(ordered: list[AttrClaim]) -> list[tuple[str, str] | None]:
    """Group the (already-sorted) claims by DISTINCT asserted value and return each value's interval.

    Grouping is by ``==`` on the raw value (no normalization — that would be a resolution decision, out of
    scope): many claims asserting the same value collapse to one group. Order follows first appearance in
    the oldest→newest series; the caller compares the groups pairwise, so the group order is immaterial.
    """
    groups: list[tuple[Any, list[AttrClaim]]] = []
    for c in ordered:
        for value, members in groups:
            if value == c.value:
                members.append(c)
                break
        else:
            groups.append((c.value, [c]))
    return [_interval(members) for _, members in groups]


def classify_succession(claims: list[AttrClaim]) -> SuccessionResult:
    """Classify one attribute's value series into SINGLE / ORDERED / CONTRADICTION / UNORDERABLE.

    Pure function of the input list. ``ordered`` is always the input sorted oldest→newest; only ``status``
    and ``current`` vary. An undated distinct value makes the whole set ``unorderable`` *first* (it can't be
    placed on the timeline at all); once every distinct value is dated, a single overlapping/equal pair is
    enough to make the series a ``contradiction``, and only a fully disjoint set is a clean ``ordered``
    succession.
    """
    ordered = sorted(claims, key=_attr_history_sort_key)
    newest = ordered[-1] if ordered else None

    intervals = _distinct_value_intervals(ordered)

    # ≤1 distinct value (0/1 claim, or many claims all asserting the same value): a settled single value.
    if len(intervals) <= 1:
        return SuccessionResult(status=SINGLE, ordered=ordered, current=newest)

    # ≥2 distinct values. If any distinct value has no usable date, the set can't be placed in time at all.
    if any(iv is None for iv in intervals):
        return SuccessionResult(status=UNORDERABLE, ordered=ordered, current=None)

    # All distinct values are dated: any overlapping/equal pair breaks the succession into a contradiction.
    dated = [iv for iv in intervals if iv is not None]  # the None guard above narrows the whole list
    for a, b in unordered_pairs(dated):
        older, newer = sorted((a, b))  # older sorts at/before newer — the order _relation expects
        if _relation(older, newer) == CONTRADICTION:
            return SuccessionResult(status=CONTRADICTION, ordered=ordered, current=None)

    # every distinct value is temporally disjoint from every other → a clean succession.
    return SuccessionResult(status=ORDERED, ordered=ordered, current=newest)


def attribute_succession(entity: Entity, attr: str) -> SuccessionResult:
    """Convenience: classify an entity's retained series for ``attr`` (empty series ⇒ SINGLE / no current)."""
    return classify_succession(entity.attr_history.get(attr, []))
