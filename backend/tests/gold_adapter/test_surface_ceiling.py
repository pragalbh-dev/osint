"""S12 — the slice's own ceiling on absolute recall, reported rather than corrected.

16 of the 65 scored claims carry a role surface that appears nowhere in their document: the gold labels a
*resolved* subject ("HQ-9/P" where the sentence says only "was formally inducted…"), or an annotator's
composition ("The missile itself / the HQ-9/P"). Those rows can only be matched through the matcher's
fuzzy tolerance, so a scorecard that reads absolute recall against 1.00 is over-reporting the gap.

This is a LABELLING observation, not a defect the adapter fixes — stripping the annotator sugar would
truncate the surfaces that genuinely are document text ("transporter-erector-launchers (TELs)").
"""

from __future__ import annotations

from typing import Any

from eval.gold.adapter import normalize_text

from .conftest import EXPECTED


def test_the_ceiling_is_stated_in_the_file(adapted: dict[str, Any]) -> None:
    block = adapted["surface_verbatimness"]
    assert block["scored_claims"] == EXPECTED["claims"]
    assert block["all_role_surfaces_verbatim_in_own_span"] == 34
    assert block["all_role_surfaces_verbatim_somewhere_in_document"] == 49
    assert len(block["rows_with_a_surface_absent_from_the_whole_document"]) == 16
    assert "ceiling" in block["reading"].lower()


def test_the_counts_are_recomputable_from_the_file_and_the_corpus(
    adapted: dict[str, Any], texts_by_path: dict[str, str],
) -> None:
    """No threshold, no judgement: exact substring under the gold's own normalisation."""
    block = adapted["surface_verbatimness"]
    in_span = 0
    absent_from_doc: list[str] = []
    for claim in adapted["claims"]:
        ref = claim["doc_ref"]
        text = texts_by_path[ref["file"]]
        span = normalize_text(text[ref["span"][0]:ref["span"][1]])
        document = normalize_text(text)
        if claim["form"] == "triple":
            values = [claim["subject"], claim["object"]]
        elif claim["form"] == "entity":
            values = [claim["name"]]
        else:
            values = list(claim["participants"])
        surfaces = [normalize_text(v) for v in values if v and v.strip() and v.strip() != "-"]
        if all(s in span for s in surfaces):
            in_span += 1
        if not all(s in document for s in surfaces):
            absent_from_doc.append(claim["gold_id"])
    assert in_span == block["all_role_surfaces_verbatim_in_own_span"]
    assert sorted(absent_from_doc) == sorted(
        block["rows_with_a_surface_absent_from_the_whole_document"])


def test_rows_absent_from_the_span_are_a_superset(adapted: dict[str, Any]) -> None:
    block = adapted["surface_verbatimness"]
    in_span = set(block["rows_with_a_surface_absent_from_their_span"])
    in_doc = set(block["rows_with_a_surface_absent_from_the_whole_document"])
    assert in_doc <= in_span, "a surface absent from the document cannot be present in its own span"


def test_labels_are_not_rewritten(raw_gold: dict[str, Any], adapted: dict[str, Any]) -> None:
    """The adapter never edits a label: every claim's surfaces are the row's, character for character."""
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    for claim in adapted["claims"]:
        row = by_row[claim["gold_id"]]
        if claim["form"] == "triple":
            assert claim["subject"] == row["subject_surface"]
            assert claim["object"] == row["object_surface"]
            assert claim["predicate"] == row["predicate"]
        elif claim["form"] == "entity":
            assert claim["name"] == row["subject_surface"]
            assert claim["entity_type"] == row["object_surface"]
        assert claim["polarity"] == row["polarity"]
        assert claim["attributes"]["gold_predicate"] == row["predicate"]
