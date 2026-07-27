"""RULING 1 — the precision denominator excludes the spans the gold declares NEUTRAL.

The defect: precision was ``matched / everything emitted``, so an unpaired emission cost the candidate
whatever span it sat on. The labeled slice declares three classes of span at which emitting a claim is
*correct reading* — ``unmodelled`` (the ontology cannot express the sentence), ``anti_coref`` (a true
sentence whose two mentions must stay unbound) and a non-identity claim over an ``ambiguous`` pair — and
charging those is not a small unfairness: it scales with how much of a document a model reads, so it does
not cancel between candidates and systematically favours the terser extractor, on ``surface_f1`` at weight
3.0. Same defect class as the composite-direction bug this harness already fixed.

These tests are on invented fixtures (this scorer is corpus-blind). The measurement on the *real* labeled
slice — perfect / verbose-but-honest / fabricating, before and after — lives in
``tests/gold_adapter/test_precision_exclusions_measured.py``, which is where the gold may be read.
"""

from __future__ import annotations

import pytest

from eval.extraction.matcher import match_claims
from eval.extraction.metrics import surface_metrics, trap_avoidance
from eval.extraction.negative_gold import NO_OVERLAP, emitted_spans, load_negative_gold

from .fixtures import POLICY, negative_row, triple, write_adapted_gold, write_claim_gold

# One document, four kinds of span. Offsets are the only thing that matters here.
GOLD_SPAN = (0, 40)
UNMODELLED_SPAN = (100, 140)
ANTI_COREF_SPAN = (200, 240)
AMBIGUOUS_SPAN = (300, 340)
TRAP_SPAN = (400, 440)


@pytest.fixture
def negative(tmp_path):
    """A slice declaring one row of each negative class, plus one positive claim to pair against."""
    path = write_adapted_gold(
        tmp_path / "gold.json",
        [{"gold_id": "g1", "source_id": "doc1", "form": "triple", "subject": "North Ridge Foundry",
          "predicate": "supplies-component", "object": "Type-7 Coupler",
          "doc_ref": {"file": "doc1.txt", "span": list(GOLD_SPAN)}}],
        {
            "unmodelled": [negative_row("n_unmod", UNMODELLED_SPAN)],
            "anti_coref": [negative_row("n_anti", ANTI_COREF_SPAN)],
            "ambiguous": [negative_row("n_ambig", AMBIGUOUS_SPAN)],
            "not_a_claim": [negative_row("n_trap", TRAP_SPAN)],
        },
    )
    return load_negative_gold(path)


def _emit(key: str, span: tuple[int, int], *, predicate: str = "supplies-component"):
    """An emission the matcher can never pair: real span, surfaces no gold claim carries."""
    return triple(key, f"Invented Subject {key}", f"Invented Object {key}", predicate,
                  file="doc1.txt", span=span)


GOLD_CLAIM = triple("g1", "North Ridge Foundry", "Type-7 Coupler", file="doc1.txt", span=GOLD_SPAN)


def _score(emitted, negative):
    match = match_claims([GOLD_CLAIM], list(emitted), POLICY)
    spans = emitted_spans(list(emitted), match, negative)
    match = match.with_precision_exclusions(negative.excluded_keys(spans))
    return match, surface_metrics(match), trap_avoidance(negative, spans)


# ── the three candidates the ruling asks about ────────────────────────────────────────────────────

def test_a_perfect_model_scores_precision_one(negative) -> None:
    match, values, traps = _score([GOLD_CLAIM], negative)
    assert values["surface_precision"].value == pytest.approx(1.0)
    assert values["surface_recall"].value == pytest.approx(1.0)
    assert match.precision_exclusions == ()          # nothing to exclude: nothing was unpaired
    assert traps.value == pytest.approx(1.0)         # silent at the trap


def test_a_verbose_but_honest_model_is_no_longer_charged_for_reading_the_document(negative) -> None:
    """The three neutral spans leave the denominator, so reading more of the document costs nothing."""
    emitted = [GOLD_CLAIM, _emit("e_unmod", UNMODELLED_SPAN), _emit("e_anti", ANTI_COREF_SPAN),
               _emit("e_ambig", AMBIGUOUS_SPAN)]
    match, values, traps = _score(emitted, negative)

    unwired = len(match.pairs) / match.extracted_total          # what the old denominator would give
    assert unwired == pytest.approx(0.25)
    assert values["surface_precision"].value == pytest.approx(1.0)
    assert match.precision_denominator == 1
    assert set(match.precision_exclusions) == {"e_unmod", "e_anti", "e_ambig"}
    assert traps.value == pytest.approx(1.0)                    # it never touched the trap


def test_a_fabricating_model_is_still_penalised_and_is_not_excused_by_the_exclusion(negative) -> None:
    """The whole risk of Ruling 1: an exclusion that leaked into ``not_a_claim`` would excuse fabrication."""
    emitted = [GOLD_CLAIM, _emit("e_trap", TRAP_SPAN)]
    match, values, traps = _score(emitted, negative)

    assert match.precision_exclusions == ()                     # the trap span is never neutral
    assert values["surface_precision"].value == pytest.approx(0.5)
    assert traps.value == pytest.approx(0.0)                    # 0 of 1 traps avoided
    assert traps.detail["hits_by_trap"] == {"n_trap": ["e_trap"]}


def test_a_span_that_is_both_neutral_and_a_trap_is_charged_the_trap(tmp_path) -> None:
    """"The trap wins" — and it is charged once, by ``trap_avoidance``, not twice."""
    path = write_adapted_gold(
        tmp_path / "gold.json", [],
        {"unmodelled": [negative_row("n_unmod", (400, 440))],
         "not_a_claim": [negative_row("n_trap", (410, 430))]},
    )
    negative = load_negative_gold(path)
    emitted = [_emit("e_both", (415, 425))]
    match, values, traps = _score(emitted, negative)

    assert match.precision_exclusions == ()                     # NOT excused as unmodelled
    assert traps.value == pytest.approx(0.0)
    assert values["surface_precision"].value == pytest.approx(0.0)


# ── the invariants that keep the exclusion from becoming a free denominator shrink ─────────────────

def test_a_matched_claim_can_never_leave_the_precision_denominator() -> None:
    """Enforced in the constructor, not by convention: excluding a paired claim pushes precision past 1.0."""
    match = match_claims([GOLD_CLAIM], [GOLD_CLAIM], POLICY)
    with pytest.raises(ValueError, match="PAIRED with positive gold"):
        match.with_precision_exclusions(["g1"])


def test_an_exclusion_from_another_run_is_rejected() -> None:
    match = match_claims([GOLD_CLAIM], [_emit("e1", UNMODELLED_SPAN)], POLICY)
    with pytest.raises(ValueError, match="not in this alignment"):
        match.with_precision_exclusions(["a-key-from-some-other-run"])


def test_the_matcher_itself_stays_ignorant_of_negative_gold() -> None:
    """The semantics live on the gold side. A matcher that computed its own exclusions would be a second,
    private definition of "neutral", and the drift between the two would be invisible in every number."""
    match = match_claims([GOLD_CLAIM], [_emit("e1", UNMODELLED_SPAN)], POLICY)
    assert match.precision_exclusions == ()
    assert match.precision == pytest.approx(0.0)


# ── the guard: a join that finds nothing must not read as a flawless run ───────────────────────────

def test_a_file_namespace_mismatch_refuses_to_report_a_flattering_number(negative) -> None:
    """The nastiest failure available here: if our locators share no file with the labeled spans, every hook
    returns "no hits" — perfect trap avoidance, zero exclusions, indistinguishable from a clean run."""
    emitted = [triple("e1", "Invented", "Thing", file="a-different-document.txt", span=TRAP_SPAN)]
    match = match_claims([GOLD_CLAIM], emitted, POLICY)
    spans = emitted_spans(emitted, match, negative)
    traps = trap_avoidance(negative, spans)

    assert traps.status == "unavailable"
    assert traps.value is None
    assert NO_OVERLAP in traps.reason


def test_the_file_join_is_by_name_so_a_path_prefixed_gold_still_matches(tmp_path) -> None:
    """The gold cites repo-relative paths; the ingest lane cites whatever the driver put on DocInput.file.
    The file NAME is the only component guaranteed common, so that is the join key — one rule, both sides."""
    path = write_adapted_gold(
        tmp_path / "gold.json", [],
        {"not_a_claim": [negative_row("n_trap", TRAP_SPAN, file="corpus/scenarios/x/docs/doc1.txt")]},
    )
    negative = load_negative_gold(path)
    emitted = [_emit("e_trap", TRAP_SPAN)]                       # cites plain "doc1.txt"
    match = match_claims([], emitted, POLICY)
    spans = emitted_spans(emitted, match, negative)

    assert negative.alignment(spans).usable
    assert trap_avoidance(negative, spans).value == pytest.approx(0.0)


@pytest.mark.parametrize("declared", [False, True], ids=["no-block", "empty-block"])
def test_a_slice_with_no_typed_negatives_reports_the_fabrication_line_unmeasured(
        tmp_path, declared: bool) -> None:
    """Not a clean 1.0: a slice with no typed negatives has no fabrication line at all, and because
    ``trap_avoidance`` is a declared non-negotiable, unmeasured blocks a winner.

    Both shapes reach the same answer — a file with no ``negative_gold`` key, and one whose four buckets are
    present but empty. The second is the one that would otherwise look like a slice with a *clean* line.
    """
    path = (write_adapted_gold(tmp_path / "gold.json", [], None) if declared
            else write_claim_gold(tmp_path / "gold.json", []))
    negative = load_negative_gold(path)
    emitted = [_emit("e1", TRAP_SPAN)]
    match = match_claims([], emitted, POLICY)
    spans = emitted_spans(emitted, match, negative)

    assert negative.declared is declared
    assert trap_avoidance(negative, spans).status == "unavailable"
    assert negative.excluded_keys(spans) == ()


def test_a_negative_row_that_cannot_be_localised_raises_rather_than_stopping_silently(tmp_path) -> None:
    path = tmp_path / "gold.json"
    import json

    path.write_text(json.dumps({
        "schema_version": "rk-bakeoff-claim-gold/1.0", "claims": [],
        "negative_gold": {
            "not_a_claim": {"rows": [{"gold_id": "n1", "doc_ref": {"file": "doc1.txt"}}]},
            "anti_coref": {"rows": []}, "ambiguous": {"rows": []}, "unmodelled": {"rows": []},
        },
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="char offsets"):
        load_negative_gold(path)


def test_a_partial_negative_block_raises(tmp_path) -> None:
    """The adapter emits all four classes. A block missing one was hand-edited, and the scorer will not
    guess which rows were dropped — a missing class silently stops penalising a whole kind of error."""
    path = tmp_path / "gold.json"
    import json

    path.write_text(json.dumps({
        "schema_version": "rk-bakeoff-claim-gold/1.0", "claims": [],
        "negative_gold": {"not_a_claim": {"rows": []}},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing class"):
        load_negative_gold(path)
