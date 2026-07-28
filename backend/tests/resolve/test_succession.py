"""Stage 3B-i — the succession-classification core (``resolve/succession.py``).

These tests are written **purely against the published contract**, before/without reading the
implementation (``resolve/succession.py`` and ``view/supersede.py`` are deliberately NOT read).
They assert what *correct* behaviour IS, not what any observed output happens to be.

Contract under test::

    classify_succession(claims: list[AttrClaim]) -> SuccessionResult(status, ordered, current)
    attribute_succession(entity, attr) == classify_succession(entity.attr_history.get(attr, []))

* ``status`` ∈ {"single", "ordered", "contradiction", "unorderable"}
* ``ordered`` is the claims sorted oldest→newest
* ``current`` is the newest claim, or ``None``

Case map (each maps to a numbered contract bullet):

1. empty input                          → ``test_empty_input_is_single``
2. one claim                            → ``test_single_claim_is_single``
3. many claims, all the SAME value      → ``test_all_same_value_is_single_not_succession``
4. clean succession (distinct/orderable)→ ``test_clean_succession_is_ordered``
5. contradiction (simultaneous values)  → ``test_simultaneous_distinct_values_is_contradiction``
6. unorderable (a distinct value undated)→ ``test_undated_distinct_value_is_unorderable``
7. attribute_succession delegates       → ``test_attribute_succession_delegates`` /
                                           ``test_attribute_succession_missing_attr_is_empty``
determinism (shuffled → same result)    → ``test_*_is_order_independent``

Corpus-independent; uses the real ``AttrClaim`` + real date value types; no clock/RNG (fixed
permutations only).
"""

from __future__ import annotations

import pytest

from chanakya.resolve.entities import AttrClaim, Entity
from chanakya.resolve.succession import attribute_succession, classify_succession
from chanakya.schemas import ExactDate, LabelDate, Period

# ── builders (real value types; no parsing/clock/RNG) ─────────────────────────────────────────


def _exact(iso: str) -> ExactDate:
    return ExactDate(iso_date=iso)


def _year(y: int) -> LabelDate:
    return LabelDate(granularity="year", year=y)


def _range(start_iso: str, end_iso: str) -> Period:
    return Period(period_type="range", start=_exact(start_iso), end=_exact(end_iso))


def _claim(
    cid: str,
    value: object,
    event: object | None = None,
    report: object | None = None,
) -> AttrClaim:
    return AttrClaim(value=value, claim_id=cid, event_time=event, report_time=report)


def _ids(result: object) -> list[str]:
    """The claim_ids of ``result.ordered`` (its oldest→newest sequence)."""
    return [c.claim_id for c in result.ordered]


# ── (1) empty input ───────────────────────────────────────────────────────────────────────────


def test_empty_input_is_single() -> None:
    result = classify_succession([])
    assert result.status == "single"
    assert list(result.ordered) == []
    assert result.current is None


# ── (2) one claim ─────────────────────────────────────────────────────────────────────────────


def test_single_claim_is_single() -> None:
    only = _claim("cA", "config-A", event=_exact("2020-01-01"), report=_exact("2020-02-01"))
    result = classify_succession([only])
    assert result.status == "single"
    assert list(result.ordered) == [only]
    assert result.current is only


def test_single_undated_claim_is_still_single() -> None:
    # A lone claim with no dates cannot be "unorderable" (nothing to order it against): it is single.
    only = _claim("cA", "config-A")
    result = classify_succession([only])
    assert result.status == "single"
    assert list(result.ordered) == [only]
    assert result.current is only


# ── (3) many claims, all the SAME value → single (agreement is not a succession) ────────────────


def test_all_same_value_is_single_not_succession() -> None:
    a = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    b = _claim("cB", "config-A", event=_exact("2022-01-01"), report=_exact("2022-02-01"))
    c = _claim("cC", "config-A", event=_exact("2024-01-01"), report=_exact("2024-02-01"))

    result = classify_succession([a, b, c])

    # Three agreeing claims are NOT a succession — no value ever changed.
    assert result.status == "single"
    # current is the NEWEST claim.
    assert result.current is c
    assert result.current.claim_id == "cC"
    # ordered is still oldest→newest.
    assert _ids(result) == ["cA", "cB", "cC"]


def test_all_same_value_is_order_independent() -> None:
    a = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    b = _claim("cB", "config-A", event=_exact("2022-01-01"), report=_exact("2022-02-01"))
    c = _claim("cC", "config-A", event=_exact("2024-01-01"), report=_exact("2024-02-01"))

    for perm in ([c, b, a], [b, a, c], [c, a, b]):
        result = classify_succession(perm)
        assert result.status == "single"
        assert _ids(result) == ["cA", "cB", "cC"]
        assert result.current.claim_id == "cC"


# ── (4) clean succession → ordered ──────────────────────────────────────────────────────────────


def test_clean_succession_is_ordered() -> None:
    # Three DISTINCT values at DISTINCT, well-separated, orderable times.
    a = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    b = _claim("cB", "config-B", event=_exact("2022-01-01"), report=_exact("2022-02-01"))
    c = _claim("cC", "config-C", event=_exact("2024-01-01"), report=_exact("2024-02-01"))

    result = classify_succession([a, b, c])

    assert result.status == "ordered"
    # ordered is oldest→newest.
    assert _ids(result) == ["cA", "cB", "cC"]
    # current is the newest value's claim.
    assert result.current is c
    assert result.current.claim_id == "cC"
    assert result.current.value == "config-C"
    # current is exactly the tail of the ordered series.
    assert result.current is result.ordered[-1]


def test_two_value_succession_is_ordered() -> None:
    early = _claim("cE", "config-early", event=_exact("2018-05-01"), report=_exact("2018-06-01"))
    late = _claim("cL", "config-late", event=_exact("2023-05-01"), report=_exact("2023-06-01"))

    result = classify_succession([early, late])

    assert result.status == "ordered"
    assert _ids(result) == ["cE", "cL"]
    assert result.current is late


def test_clean_succession_is_order_independent() -> None:
    a = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    b = _claim("cB", "config-B", event=_exact("2022-01-01"), report=_exact("2022-02-01"))
    c = _claim("cC", "config-C", event=_exact("2024-01-01"), report=_exact("2024-02-01"))

    # Fixed permutations (no RNG): the classification and ordering must be invariant to input order.
    for perm in ([c, b, a], [b, c, a], [a, c, b]):
        result = classify_succession(perm)
        assert result.status == "ordered"
        assert _ids(result) == ["cA", "cB", "cC"]
        assert result.current.claim_id == "cC"


# ── (5) contradiction → two distinct values valid simultaneously ────────────────────────────────


@pytest.mark.parametrize(
    ("event_x", "report_x", "event_y", "report_y"),
    [
        # identical point dates
        (_exact("2022-06-01"), _exact("2022-07-01"), _exact("2022-06-01"), _exact("2022-07-01")),
        # both dated the SAME year (coarse label)
        (_year(2022), _exact("2023-01-01"), _year(2022), _exact("2023-01-01")),
        # both stated over the SAME closed interval
        (_range("2020-01-01", "2021-12-31"), None, _range("2020-01-01", "2021-12-31"), None),
    ],
)
def test_simultaneous_distinct_values_is_contradiction(
    event_x: object,
    report_x: object,
    event_y: object,
    report_y: object,
) -> None:
    x = _claim("cX", "config-X", event=event_x, report=report_x)
    y = _claim("cY", "config-Y", event=event_y, report=report_y)

    result = classify_succession([x, y])

    # Two DIFFERENT values whose validity coincides cannot be ordered into a succession.
    assert result.status == "contradiction"
    # No single "current" value when the evidence contradicts itself.
    assert result.current is None
    # All claims are retained in ``ordered`` (order among simultaneous claims not asserted).
    assert {c.claim_id for c in result.ordered} == {"cX", "cY"}


def test_contradiction_is_order_independent() -> None:
    x = _claim("cX", "config-X", event=_exact("2022-06-01"), report=_exact("2022-07-01"))
    y = _claim("cY", "config-Y", event=_exact("2022-06-01"), report=_exact("2022-07-01"))

    for perm in ([x, y], [y, x]):
        result = classify_succession(perm)
        assert result.status == "contradiction"
        assert result.current is None
        assert {c.claim_id for c in result.ordered} == {"cX", "cY"}


# ── (6) unorderable → a distinct value that cannot be placed on the timeline ─────────────────────


def test_undated_distinct_value_is_unorderable() -> None:
    dated = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    # A DISTINCT value with NO usable date (both time axes None) — it cannot be placed.
    undated = _claim("cB", "config-B", event=None, report=None)

    result = classify_succession([dated, undated])

    assert result.status == "unorderable"
    # No defensible "current" when a distinct value cannot be located in time.
    assert result.current is None
    # Every input claim is still carried in ``ordered`` (position of the undated one not asserted).
    assert {c.claim_id for c in result.ordered} == {"cA", "cB"}


def test_unorderable_is_order_independent() -> None:
    dated = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    undated = _claim("cB", "config-B", event=None, report=None)

    for perm in ([dated, undated], [undated, dated]):
        result = classify_succession(perm)
        assert result.status == "unorderable"
        assert result.current is None
        assert {c.claim_id for c in result.ordered} == {"cA", "cB"}


# ── (7) attribute_succession delegates to classify_succession ───────────────────────────────────


def _entity() -> Entity:
    return Entity(eid="e1", etype="widget", name="W1")


def test_attribute_succession_delegates() -> None:
    a = _claim("cA", "config-A", event=_exact("2019-01-01"), report=_exact("2019-02-01"))
    b = _claim("cB", "config-B", event=_exact("2022-01-01"), report=_exact("2022-02-01"))
    c = _claim("cC", "config-C", event=_exact("2024-01-01"), report=_exact("2024-02-01"))
    claims = [a, b, c]

    ent = _entity()
    ent.attr_history["config"] = claims

    via_attr = attribute_succession(ent, "config")
    via_list = classify_succession(claims)

    # The contract: attribute_succession(ent, attr) == classify_succession(ent.attr_history[attr]).
    assert via_attr == via_list
    # And it is the meaningful (non-trivial) classification, not accidentally trivialised.
    assert via_attr.status == "ordered"
    assert [x.claim_id for x in via_attr.ordered] == ["cA", "cB", "cC"]
    assert via_attr.current.claim_id == "cC"


def test_attribute_succession_delegates_on_contradiction() -> None:
    x = _claim("cX", "config-X", event=_exact("2022-06-01"), report=_exact("2022-07-01"))
    y = _claim("cY", "config-Y", event=_exact("2022-06-01"), report=_exact("2022-07-01"))
    claims = [x, y]

    ent = _entity()
    ent.attr_history["config"] = claims

    assert attribute_succession(ent, "config") == classify_succession(claims)
    assert attribute_succession(ent, "config").status == "contradiction"


def test_attribute_succession_missing_attr_is_empty() -> None:
    # A missing attribute resolves the same as an empty claim list → the "single" empty result.
    ent = _entity()  # no attr_history entries

    via_attr = attribute_succession(ent, "does-not-exist")
    via_empty = classify_succession([])

    assert via_attr == via_empty
    assert via_attr.status == "single"
    assert list(via_attr.ordered) == []
    assert via_attr.current is None
