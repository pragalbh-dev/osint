"""Dedup + claim-ID tests — the within-doc restatement collapse and the deterministic ID pass.

Every test is pure and offline (no LLM/geocoder/clock/RNG). The load-bearing behaviours asserted:
a within-doc restatement collapses to **one** claim with **many** ``DocRef`` spans; the same stated
(s, p, o) in **two different documents** is **never** merged; grouping keeps different
polarity/kind/asserts apart; and ``assign_claim_ids`` mints **byte-stable** IDs regardless of input
order (with row/line/image locators + index disambiguation).
"""

from __future__ import annotations

import random

from chanakya.ingest.dedup import assign_claim_ids, dedup_within_doc
from chanakya.schemas import ClaimRecord, DocRef, EntityDescriptor, Triple


def _triple_claim(
    *,
    source_id: str = "src-a",
    file: str = "d01.txt",
    subj: str = "hq-9",
    pred: str = "based-at",
    obj: str = "site-7",
    span: tuple[int, int] = (0, 10),
    line: int | None = 1,
    row: int | None = None,
    region: str | None = None,
    kind: str = "observation",
    polarity: str = "positive",
    premises: list[str] | None = None,
    claim_id: str = "tmp",
) -> ClaimRecord:
    """Build a relationship ``ClaimRecord`` with a single-span ``DocRef`` (a concise test factory)."""
    return ClaimRecord(
        claim_id=claim_id,
        source_id=source_id,
        doc_ref=DocRef(file=file, span=span, line=line, row=row, region=region),
        kind=kind,  # type: ignore[arg-type]
        polarity=polarity,  # type: ignore[arg-type]
        asserts="relationship",
        payload=Triple(subject=subj, predicate=pred, object=obj),
        premises=premises or [],
    )


# ── within-doc restatement collapse ────────────────────────────────────────────────────────────

def test_restatement_within_doc_collapses_to_one_claim_two_docrefs() -> None:
    first = _triple_claim(span=(0, 20), line=1, claim_id="a")
    echo = _triple_claim(span=(50, 70), line=3, claim_id="b")  # same assertion, later in the doc

    out = dedup_within_doc([first, echo])

    assert len(out) == 1
    refs = out[0].doc_refs()
    assert len(refs) == 2
    assert [r.span for r in refs] == [(0, 20), (50, 70)]  # sorted by span offset

    assigned = assign_claim_ids(out, doc_id="d01")
    assert len(assigned) == 1
    assert len(assigned[0].doc_refs()) == 2  # the two spans survive ID assignment


def test_three_restatements_collapse_to_one() -> None:
    claims = [
        _triple_claim(span=(80, 90), line=5),
        _triple_claim(span=(0, 10), line=1),
        _triple_claim(span=(40, 50), line=3),
    ]
    out = dedup_within_doc(claims)
    assert len(out) == 1
    assert [r.span for r in out[0].doc_refs()] == [(0, 10), (40, 50), (80, 90)]


def test_normalized_restatement_collapses_on_case_and_whitespace() -> None:
    a = _triple_claim(subj="HQ-9", pred="based-at", obj="Site-7", span=(0, 10))
    b = _triple_claim(subj="hq-9", pred="based-at", obj="site-7  ", span=(30, 40))
    out = dedup_within_doc([a, b])
    assert len(out) == 1  # lexical normalisation merges the surface variants


def test_merged_docrefs_sorted_regardless_of_input_order() -> None:
    late = _triple_claim(span=(50, 70), line=3)
    early = _triple_claim(span=(0, 20), line=1)
    out = dedup_within_doc([late, early])  # input order reversed from span order
    assert [r.span for r in out[0].doc_refs()] == [(0, 20), (50, 70)]


def test_dedup_does_not_mutate_inputs() -> None:
    a = _triple_claim(span=(0, 20))
    b = _triple_claim(span=(50, 70))
    dedup_within_doc([a, b])
    assert isinstance(a.doc_ref, DocRef) and a.doc_ref.span == (0, 20)
    assert isinstance(b.doc_ref, DocRef) and b.doc_ref.span == (50, 70)


# ── never cross-doc, never resolution ────────────────────────────────────────────────────────────

def test_same_spo_two_docs_not_merged_and_get_distinct_ids() -> None:
    a = _triple_claim(source_id="src-a", file="da.txt", span=(0, 20))
    b = _triple_claim(source_id="src-b", file="db.txt", span=(0, 20))  # identical assertion, other doc

    out = dedup_within_doc([a, b])
    assert len(out) == 2  # different documents → never merged

    ids_a = assign_claim_ids([c for c in out if c.source_id == "src-a"], doc_id="da")
    ids_b = assign_claim_ids([c for c in out if c.source_id == "src-b"], doc_id="db")
    assert ids_a[0].claim_id.startswith("da-")
    assert ids_b[0].claim_id.startswith("db-")
    assert ids_a[0].claim_id != ids_b[0].claim_id


def test_different_predicate_not_merged() -> None:
    a = _triple_claim(pred="based-at", span=(0, 10))
    b = _triple_claim(pred="inducted-into", span=(20, 30))
    assert len(dedup_within_doc([a, b])) == 2


# ── grouping respects the discriminants ───────────────────────────────────────────────────────────

def test_grouping_respects_polarity() -> None:
    pos = _triple_claim(polarity="positive", span=(0, 10))
    neg = _triple_claim(polarity="negative", span=(30, 40))
    assert len(dedup_within_doc([pos, neg])) == 2


def test_grouping_respects_kind() -> None:
    observed = _triple_claim(kind="observation", span=(0, 10))
    inferred = _triple_claim(kind="inference", premises=["d01-l9"], span=(30, 40))
    assert len(dedup_within_doc([observed, inferred])) == 2


def test_grouping_respects_asserts() -> None:
    relationship = _triple_claim(span=(0, 10))
    entity = ClaimRecord(
        claim_id="tmp",
        source_id="src-a",
        doc_ref=DocRef(file="d01.txt", span=(30, 40), line=3),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name="site-7"),
    )
    assert len(dedup_within_doc([relationship, entity])) == 2


def test_inference_with_different_premises_not_merged() -> None:
    a = _triple_claim(kind="inference", premises=["d01-l1"], span=(0, 10))
    b = _triple_claim(kind="inference", premises=["d01-l2"], span=(30, 40))
    assert len(dedup_within_doc([a, b])) == 2  # different derivation → distinct claims


# ── deterministic ID assignment ─────────────────────────────────────────────────────────────────

def test_ids_byte_stable_across_shuffled_input() -> None:
    claims = [
        _triple_claim(pred="based-at", span=(0, 10), line=1),
        _triple_claim(pred="inducted-into", span=(20, 30), line=2),
        _triple_claim(pred="equips", span=(40, 50), line=3),
        _triple_claim(pred="supplies-component", span=(60, 70), line=4),
    ]
    baseline = [c.claim_id for c in assign_claim_ids(claims, doc_id="d05")]

    reversed_ids = [c.claim_id for c in assign_claim_ids(list(reversed(claims)), doc_id="d05")]
    shuffled = list(claims)
    random.Random(1234).shuffle(shuffled)
    shuffled_ids = [c.claim_id for c in assign_claim_ids(shuffled, doc_id="d05")]

    assert baseline == reversed_ids == shuffled_ids
    assert baseline == ["d05-l1", "d05-l2", "d05-l3", "d05-l4"]
    assert len(set(baseline)) == len(baseline)  # all unique


def test_locator_row_vs_line() -> None:
    row_claim = _triple_claim(file="d05.txt", span=(0, 5), row=12, line=12)
    line_claim = _triple_claim(file="d02.txt", span=(0, 5), line=3, row=None)
    assert assign_claim_ids([row_claim], doc_id="d05")[0].claim_id == "d05-row12"
    assert assign_claim_ids([line_claim], doc_id="d02")[0].claim_id == "d02-l3"


def test_duplicate_locator_gets_index() -> None:
    # Two *distinct* assertions that happen to cite the same line → the second is disambiguated.
    a = _triple_claim(pred="based-at", span=(0, 10), line=3)
    b = _triple_claim(pred="equips", span=(11, 20), line=3)
    ids = {c.claim_id for c in assign_claim_ids([a, b], doc_id="d02")}
    assert ids == {"d02-l3", "d02-l3-2"}


def test_image_region_locator() -> None:
    image_claim = _triple_claim(file="d07.png", span=None, line=None, row=None, region="full")
    assert assign_claim_ids([image_claim], doc_id="d07")[0].claim_id == "d07-full"


def test_assign_does_not_mutate_inputs() -> None:
    claim = _triple_claim(span=(0, 10), line=1, claim_id="tmp")
    assign_claim_ids([claim], doc_id="d01")
    assert claim.claim_id == "tmp"  # a fresh copy is stamped; the input keeps its placeholder
