"""Every derived char offset slices back to the quoted span it came from.

The adapter turns a *quoted string* into ``[start, end]``. If that arithmetic is off, the offsets look
fine and the citation-faithfulness metric reports a model as mis-citing — a fabricated finding about a
candidate, caused by us. So the round trip is asserted on all 127 rows, with an independent normaliser.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from eval.gold.adapter import SpanDecodeError, decode_span, normalize_text

from .conftest import EXPECTED

# An INDEPENDENT implementation of the gold's documented normalisation (curly quotes, dashes, NBSP,
# whitespace collapse). Written from the audit note rather than imported, so agreement with
# ``normalize_text`` means the rule is right and not merely self-consistent.
_FOLD = {
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-", 0x2212: "-",
    0x00A0: " ", 0x2007: " ", 0x202F: " ", 0x2009: " ",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_FOLD)).strip()


def _records(adapted: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every adapted record that carries a ``doc_ref`` — all 127 of them, positive and negative."""
    out = {c["gold_id"]: c for c in adapted["claims"]}
    for block in adapted["negative_gold"].values():
        out |= {r["gold_id"]: r for r in block["rows"]}
    out |= {r["gold_id"]: r
            for r in adapted["excluded_from_scoring"]["attribute_rows"]["rows"]}
    return out


def test_every_row_carries_a_doc_ref(adapted: dict[str, Any]) -> None:
    assert len(_records(adapted)) == EXPECTED["rows"]


def test_offsets_slice_back_to_the_quoted_span(
    raw_gold: dict[str, Any], adapted: dict[str, Any], texts_by_path: dict[str, str],
) -> None:
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    byte_exact = 0
    for gold_id, record in _records(adapted).items():
        ref = record["doc_ref"]
        text = texts_by_path[ref["file"]]
        start, end = ref["span"]
        assert 0 <= start < end <= len(text), f"{gold_id}: span out of bounds"
        sliced = text[start:end]
        quoted = by_row[gold_id]["doc_ref_span"]
        assert _norm(sliced) == _norm(quoted), f"{gold_id}: slice does not match the quote"
        assert normalize_text(sliced) == normalize_text(quoted), f"{gold_id}: adapter normaliser"
        if sliced == quoted:
            byte_exact += 1
    assert byte_exact == EXPECTED["spans_byte_exact"]


def test_the_three_non_byte_exact_spans_are_whitespace_only(
    raw_gold: dict[str, Any], adapted: dict[str, Any], texts_by_path: dict[str, str],
) -> None:
    """The 124/127 gap is whitespace collapse in the fixed-width customs table — nothing else."""
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    inexact = []
    for gold_id, record in _records(adapted).items():
        ref = record["doc_ref"]
        text = texts_by_path[ref["file"]]
        start, end = ref["span"]
        if text[start:end] != by_row[gold_id]["doc_ref_span"]:
            inexact.append(gold_id)
            # identical once whitespace is collapsed, and identical with whitespace *removed*, which is
            # what makes "whitespace only" a claim rather than a hope
            assert (re.sub(r"\s+", "", text[start:end])
                    == re.sub(r"\s+", "", by_row[gold_id]["doc_ref_span"]))
    assert sorted(inexact) == ["d05-r08", "d05-r20", "d05-r24"]


def test_offsets_start_on_the_line_the_gold_states(
    raw_gold: dict[str, Any], adapted: dict[str, Any], texts_by_path: dict[str, str],
) -> None:
    """A second, independent handle on the same offsets: the gold's own line number agrees, 125/125."""
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    for gold_id, record in _records(adapted).items():
        ref = record["doc_ref"]
        text = texts_by_path[ref["file"]]
        line = text.count("\n", 0, ref["span"][0]) + 1
        assert line == by_row[gold_id]["doc_ref_line"], f"{gold_id}: line {line}"


def test_doc_ref_file_is_the_cited_document(
    raw_gold: dict[str, Any], adapted: dict[str, Any],
) -> None:
    paths = {d["doc_id"]: d["path"] for d in raw_gold["documents"]}
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    for gold_id, record in _records(adapted).items():
        assert record["doc_ref"]["file"] == paths[by_row[gold_id]["doc_id"]]
        assert record["source_id"] == by_row[gold_id]["doc_id"]


def test_duplicate_quote_is_disambiguated_by_line() -> None:
    """The two rows whose quote occurs twice resolve by line, not by "first occurrence wins"."""
    text = "alpha\nthe same quote\nbravo\nthe same quote\n"
    first = decode_span(text, "the same quote", 2)
    second = decode_span(text, "the same quote", 4)
    assert first != second
    assert text[first[0]:first[1]] == text[second[0]:second[1]] == "the same quote"
    assert text.count("\n", 0, second[0]) + 1 == 4


def test_a_quote_that_is_not_in_the_document_raises() -> None:
    with pytest.raises(SpanDecodeError):
        decode_span("the document says one thing", "it says something else", 1)


def test_an_empty_quote_raises() -> None:
    with pytest.raises(SpanDecodeError):
        decode_span("anything", "   ", 1)


def test_normalisation_is_idempotent_and_folds_what_it_documents() -> None:
    raw = "“HQ‑9–P”  says   the\nreport"
    once = normalize_text(raw)
    assert once == normalize_text(once)
    assert once == '"HQ-9-P" says the report'
