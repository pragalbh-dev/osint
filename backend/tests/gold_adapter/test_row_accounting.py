"""Every one of the 127 labeled rows lands in exactly one bucket, and the buckets are the right sizes.

The failure this guards against is the one the project keeps hitting: a translation that quietly drops
rows and reports a clean-looking number over a shrunken denominator.

Pure fixture bookkeeping: every number below comes from ``EXPECTED``, which was re-derived against the
2026-07-26 gold repair. Nothing here is a measurement of a model.
"""

from __future__ import annotations

import collections
from typing import Any

import pytest

from eval.gold.adapter import ReconciliationError, adapt_claim_gold

from .conftest import EXPECTED

NEGATIVE_PREFIXES = ("NOT_A_CLAIM", "ANTI_COREF", "AMBIGUOUS", "UNMODELLED")


def _buckets(adapted: dict[str, Any]) -> dict[str, list[str]]:
    out = {
        "claims": [c["gold_id"] for c in adapted["claims"]],
        "attribute_rows": [r["gold_id"]
                           for r in adapted["excluded_from_scoring"]["attribute_rows"]["rows"]],
    }
    for name, block in adapted["negative_gold"].items():
        out[f"negative:{name}"] = [r["gold_id"] for r in block["rows"]]
    return out


def test_documents_and_rows(raw_gold: dict[str, Any], adapted: dict[str, Any]) -> None:
    assert len(adapted["docs"]) == EXPECTED["documents"]
    assert adapted["docs"] == [d["doc_id"] for d in raw_gold["documents"]]
    assert len(raw_gold["rows"]) == EXPECTED["rows"]


def test_every_row_lands_in_exactly_one_bucket(
    raw_gold: dict[str, Any], adapted: dict[str, Any],
) -> None:
    placed = [gid for ids in _buckets(adapted).values() for gid in ids]
    source = [r["row_id"] for r in raw_gold["rows"]]
    assert len(placed) == EXPECTED["rows"]
    assert len(set(placed)) == len(placed), "a row was placed in two buckets"
    assert sorted(placed) == sorted(source), "the placed set is not the source set"


def test_bucket_sizes(adapted: dict[str, Any]) -> None:
    sizes = {k: len(v) for k, v in _buckets(adapted).items()}
    assert sizes == {
        "claims": EXPECTED["claims"],
        "attribute_rows": EXPECTED["attribute_rows"],
        "negative:not_a_claim": EXPECTED["not_a_claim"],
        "negative:anti_coref": EXPECTED["anti_coref"],
        "negative:ambiguous": EXPECTED["ambiguous"],
        "negative:unmodelled": EXPECTED["unmodelled"],
    }


def test_bucketing_follows_the_predicate_prefix(
    raw_gold: dict[str, Any], adapted: dict[str, Any],
) -> None:
    """No row is bucketed on anything but its declared predicate prefix."""
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    for name, block in adapted["negative_gold"].items():
        for row in block["rows"]:
            prefix = by_row[row["gold_id"]]["predicate"].split(":", 1)[0]
            assert prefix in NEGATIVE_PREFIXES
            assert prefix.lower() == name
    for row in adapted["excluded_from_scoring"]["attribute_rows"]["rows"]:
        assert by_row[row["gold_id"]]["predicate"].startswith("ATTR:")
    for claim in adapted["claims"]:
        prefix = by_row[claim["gold_id"]]["predicate"].split(":", 1)[0]
        assert prefix not in NEGATIVE_PREFIXES and prefix != "ATTR"


def test_declared_counts_reproduce(adapted: dict[str, Any]) -> None:
    rec = adapted["reconciliation"]
    assert rec["source_rows"] == rec["placed_rows"] == EXPECTED["rows"]
    assert rec["scored_recall_denominator"] == EXPECTED["claims"]
    assert rec["negative_polarity_rows"] == EXPECTED["negative_polarity_rows"]
    assert rec["declared_counts_reproduced"] == {
        "documents": EXPECTED["documents"],
        "rows": EXPECTED["rows"],
        "not_a_claim_rows": EXPECTED["not_a_claim"],
        "anti_coref_rows": EXPECTED["anti_coref"],
        "unmodelled_rows": EXPECTED["unmodelled"],
        "coref_clusters": EXPECTED["coref_clusters"],
    }


def test_forms_are_decoded_not_guessed(raw_gold: dict[str, Any], adapted: dict[str, Any]) -> None:
    """The source gold has no ``form`` field; every form is decoded from the predicate prefix."""
    assert "form" not in set().union(*(set(r) for r in raw_gold["rows"]))
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    forms = collections.Counter(c["form"] for c in adapted["claims"])
    assert forms == {"triple": 36, "entity": 28, "event": 1}
    for claim in adapted["claims"]:
        predicate = by_row[claim["gold_id"]]["predicate"]
        if predicate.startswith("ENTITY_EXISTS"):
            assert claim["form"] == "entity"
        elif predicate.startswith("EVENT:"):
            assert claim["form"] == "event"
            assert claim["event_type"] == predicate.split(":", 1)[1]
        else:
            assert claim["form"] == "triple"
            assert claim["predicate"] == predicate


def test_identity_predicates_stay_literal(adapted: dict[str, Any]) -> None:
    """S4: ``same-as`` / ``distinct-from`` are triples with that predicate — what the pipeline emits."""
    identity = [c for c in adapted["claims"] if c.get("predicate") in ("same-as", "distinct-from")]
    assert len(identity) == 16
    assert all(c["form"] == "triple" for c in identity)


def test_a_dropped_row_raises(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> None:
    """The reconciliation is a real check, not a comment: break it and the adapter refuses."""
    tampered = dict(raw_gold)
    tampered["counts"] = dict(raw_gold["counts"]) | {"rows": 999}
    with pytest.raises(ReconciliationError):
        adapt_claim_gold(tampered, doc_texts)


def test_a_duplicate_row_id_raises(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> None:
    tampered = dict(raw_gold)
    tampered["rows"] = list(raw_gold["rows"]) + [raw_gold["rows"][0]]
    with pytest.raises(ReconciliationError):
        adapt_claim_gold(tampered, doc_texts)


def test_a_missing_document_text_raises(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> None:
    """No silent skip when a cited document cannot be read — that would drop rows invisibly."""
    partial = {k: v for k, v in doc_texts.items() if k != raw_gold["documents"][0]["doc_id"]}
    with pytest.raises(ReconciliationError):
        adapt_claim_gold(raw_gold, partial)


def test_the_wrong_schema_raises(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> None:
    tampered = dict(raw_gold) | {"schema_version": "some-other-gold/2.0"}
    with pytest.raises(ValueError, match="expected schema_version"):
        adapt_claim_gold(tampered, doc_texts)
