"""S12 — the slice's own ceiling on absolute recall, reported rather than corrected.

Some scored claims carry a role surface that appears nowhere in their cited document, so they can only be
matched through the matcher's fuzzy tolerance; a scorecard that reads absolute recall against 1.00 is
over-reporting the gap by that much. The adapter's job is to *state* the ceiling in the adapted file, and
the surviving tests here check that what it states is recomputable from the corpus rather than asserted.

The ceiling's SIZE is deliberately not pinned in this module. It is a moving property of the labelling —
the 2026-07-26 gold repair shrank it substantially by rewriting annotator-composed surfaces back to
document text — and the gold declares its own current figures under ``ceilings`` →
``2_verbatim_extractability``, which is the right single home for them.

RETIRED 2026-07-27 — ``test_the_ceiling_is_stated_in_the_file``
───────────────────────────────────────────────────────────────
That test pinned the ceiling at 34 in-span / 49 in-document / 16 absent, and its premise was that those 16
rows were "a LABELLING observation, not a defect the adapter fixes". The 2026-07-26 repair fixed exactly
that: it corrected 14 of the 16 against the document and moved the other 2 out of the scored set. So the
test was not merely stale in its numbers — its stated reason for existing had become false. It is deleted
rather than bumped, because re-baselining it would have preserved a narrative the repair refuted. The
finding, and what the repair did about it, live in ``tmp/conv/RK-BAKEOFF-DIAGNOSIS.md`` and in the gold's
own 2026-07-26 audit-log entry.
"""

from __future__ import annotations

from typing import Any

from eval.gold.adapter import normalize_text


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
