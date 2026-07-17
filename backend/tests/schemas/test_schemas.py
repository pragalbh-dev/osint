"""Unit tests for the frozen schema surface (values, discriminated payload, claim validation, ids)."""

from __future__ import annotations

import pytest

from chanakya.schemas import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    ExactDate,
    LabelDate,
    Location,
    Period,
    Quantity,
    Triple,
    canonical_iso_bounds,
    is_claim_id,
    make_claim_id,
)


def test_make_claim_id() -> None:
    assert make_claim_id("d05", "row12") == "d05-row12"
    assert make_claim_id("d02", "l3", index=2) == "d02-l3-2"
    assert is_claim_id("d05-row12") and not is_claim_id("D05_row12!")
    with pytest.raises(ValueError):
        make_claim_id("d05", "row 12!")


def test_label_date_bounds_are_pure_calendar_math() -> None:
    assert canonical_iso_bounds(LabelDate(granularity="quarter", year=2021, quarter=4)) == ("2021-10-01", "2021-12-31")
    assert canonical_iso_bounds(LabelDate(granularity="month", year=2024, month=2)) == ("2024-02-01", "2024-02-29")
    assert canonical_iso_bounds(LabelDate(granularity="half", year=2020, half=2)) == ("2020-07-01", "2020-12-31")
    assert canonical_iso_bounds(ExactDate(iso_date="2022-03-01")) == ("2022-03-01", "2022-03-01")
    assert canonical_iso_bounds(None) == (None, None)


def test_period_bounds() -> None:
    p = Period(period_type="range", start=ExactDate(iso_date="2021-01-01"), end=ExactDate(iso_date="2021-12-31"))
    assert canonical_iso_bounds(p) == ("2021-01-01", "2021-12-31")
    a = Period(period_type="as_of", as_of=LabelDate(granularity="year", year=2019))
    assert canonical_iso_bounds(a) == ("2019-01-01", "2019-12-31")


def test_discriminated_payload_round_trip() -> None:
    c = ClaimRecord(
        claim_id="d1-l1", source_id="s", doc_ref=DocRef(file="f", span=(0, 5)),
        kind="observation", asserts="relationship",
        payload=Triple(subject="a", predicate="based-at", object="b"),
    )
    reparsed = ClaimRecord.model_validate_json(c.model_dump_json())
    assert type(reparsed.payload).__name__ == "Triple"
    assert reparsed.doc_refs()[0].span == (0, 5)


def test_asserts_payload_mismatch_rejected() -> None:
    with pytest.raises(ValueError):
        ClaimRecord(claim_id="x-1", source_id="s", doc_ref=DocRef(file="f"),
                    kind="observation", asserts="entity",
                    payload=Triple(subject="a", predicate="b", object="c"))


def test_retraction_and_inference_require_their_fields() -> None:
    with pytest.raises(ValueError):
        ClaimRecord(claim_id="r-1", source_id="s", doc_ref=DocRef(file="f"),
                    kind="retraction", asserts="entity",
                    payload=EntityDescriptor(entity_type="t", name="n"))
    with pytest.raises(ValueError):
        ClaimRecord(claim_id="i-1", source_id="s", doc_ref=DocRef(file="f"),
                    kind="inference", asserts="entity",
                    payload=EntityDescriptor(entity_type="t", name="n"))


def test_value_objects_carry_raw_and_canonical_slots() -> None:
    loc = Location(raw="~20 km NW of Sargodha", surface_format="relative", precision_class="site")
    assert loc.wgs84_lat is None and loc.resolved_place_ref is None  # canonical slots filled later by INGEST/RESOLVE
    q = Quantity(min=8, max=12, unit="TEL", count_state="fielded", approx=True)
    assert q.count_state == "fielded" and q.approx
