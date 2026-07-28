"""The alignment rule — because the matcher's leniency IS the measurement.

These tests pin the *policy*, not a score: that a negation never matches its assertion, that a claim
which nails one role and invents the other is a different claim rather than a half-credit, that the
alignment is one-to-one and deterministic, and that each knob in the policy actually moves the result.
"""

from __future__ import annotations

from eval.extraction.matcher import identifiers_agree, match_claims, similarity
from eval.extraction.surface import identifier_tokens, normalize_designator, normalize_surface

from .fixtures import POLICY, entity, triple


def test_normalisation_ignores_case_separators_and_punctuation() -> None:
    assert normalize_surface("North-Ridge  Foundry, Ltd.") == "north ridge foundry ltd"
    assert normalize_surface(None) == ""


# ── the identifier rule (decided 2026-07-25 against the labeled gold; see config/bakeoff.yaml) ─────

def test_designator_normalisation_glues_identifiers_and_leaves_prose_split() -> None:
    """Punctuation inside a letters-and-digits token is typographic; everywhere else it is a boundary."""
    assert normalize_designator("XT-455/B") == "xt455b"
    assert normalize_designator("HARBOURLINE-4A9 assembly") == "harbourline4a9 assembly"
    assert normalize_designator("North-Ridge Foundry") == "north ridge foundry"   # prose: untouched
    assert normalize_designator("supplies-component") == "supplies component"     # predicates: untouched
    assert normalize_designator("2024-11") == "2024 11"                           # a date is not an id
    assert normalize_designator(None) == ""
    assert identifier_tokens("the XT-455 coupler") == frozenset({"xt455"})
    assert identifier_tokens("the coupler") == frozenset()


def test_a_dehyphenated_designator_is_the_same_claim() -> None:
    gold = [triple("g1", "North Ridge Foundry", "XT-455")]
    got = [triple("c1", "North Ridge Foundry", "XT455")]
    assert len(match_claims(gold, got, POLICY).pairs) == 1
    prose = POLICY.model_copy(update={"identifier_policy": "prose"})
    assert match_claims(gold, got, prose).pairs == ()


def test_a_sibling_designator_is_vetoed_however_close_the_surfaces_are() -> None:
    """The tightening half. A fuzzy floor cannot separate XT-455 from XT-455A — a veto can."""
    gold = [triple("g1", "North Ridge Foundry", "XT-455 Coupler")]
    got = [triple("c1", "North Ridge Foundry", "XT-455A Coupler")]
    result = match_claims(gold, got, POLICY)
    assert result.pairs == ()
    assert result.rejections.get("identifier") == 1
    # …and it really is the veto doing it, not the floor: the surfaces score well above it.
    assert similarity("XT-455 Coupler", "XT-455A Coupler", POLICY) > POLICY.role_min_similarity
    lenient = POLICY.model_copy(update={"identifier_agreement": "ignore"})
    assert len(match_claims(gold, got, lenient).pairs) == 1


def test_the_veto_is_nested_and_not_prefix_tolerant() -> None:
    """Nested, so a surface may carry a designator its counterpart omits — the real case in the labeled
    gold is ``the FT-2000`` against ``the FT-2000 (sometimes rendered FT-2000A)``. NOT prefix-tolerant, so a
    family designator is not silently its own variant."""
    assert identifiers_agree("the XT-455", "the XT-455, rendered XT-455B", POLICY)
    assert identifiers_agree("the XT-455 coupler", "the coupler", POLICY)   # prose side has no designator
    assert not identifiers_agree("XT-455", "XT-455B", POLICY)
    assert not identifiers_agree("XT-4", "XT-455", POLICY)


def test_the_designator_reading_can_only_raise_a_score() -> None:
    """Max-of-two-readings, not a replacement: nothing that matched under prose stops matching."""
    prose = POLICY.model_copy(update={"identifier_policy": "prose"})
    for a, b in (("XT-455", "XT455"), ("the XT-455", "XT-455"), ("A Foundry", "A Foundry Ltd"),
                 ("Type-7 Coupler", "Type-7 Coupler assembly"), ("C Works", "Invented Works")):
        assert similarity(a, b, POLICY) >= similarity(a, b, prose)


def test_exact_claim_matches_and_scores_one() -> None:
    gold = [triple("g1", "North Ridge Foundry", "Type-7 Coupler")]
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler")]
    result = match_claims(gold, got, POLICY)
    assert len(result.pairs) == 1
    assert result.precision == 1.0 and result.recall == 1.0 and result.f1 == 1.0


def test_negation_never_matches_the_assertion() -> None:
    """A denial is not a sloppy version of the claim — for this project it is the opposite fact."""
    gold = [triple("g1", "North Ridge Foundry", "Type-7 Coupler")]
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler", polarity="negative")]
    result = match_claims(gold, got, POLICY)
    assert result.pairs == ()
    assert result.rejections.get("polarity") == 1


def test_one_correct_role_and_one_invented_role_is_not_a_match() -> None:
    """Per-role floors, not a blended average: half a claim is a different claim."""
    gold = [triple("g1", "North Ridge Foundry", "Type-7 Coupler")]
    got = [triple("c1", "North Ridge Foundry", "Harbourline Turbine Set")]
    result = match_claims(gold, got, POLICY)
    assert result.pairs == ()
    assert result.recall == 0.0


def test_predicate_policy_normalized_vs_exact() -> None:
    gold = [triple("g1", "A Foundry", "B Coupler", predicate="supplies-component")]
    got = [triple("c1", "A Foundry", "B Coupler", predicate="Supplies Component")]
    assert len(match_claims(gold, got, POLICY).pairs) == 1
    strict = POLICY.model_copy(update={"predicate_policy": "exact"})
    assert match_claims(gold, got, strict).pairs == ()


def test_form_mismatch_is_inadmissible() -> None:
    gold = [entity("g1", "North Ridge Foundry")]
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler")]
    assert match_claims(gold, got, POLICY).pairs == ()


def test_entity_type_policy_can_be_ignored() -> None:
    gold = [entity("g1", "North Ridge Foundry", "manufacturer")]
    got = [entity("c1", "North Ridge Foundry", "trading_org")]
    assert match_claims(gold, got, POLICY).pairs == ()
    lenient = POLICY.model_copy(update={"entity_type_policy": "ignore"})
    assert len(match_claims(gold, got, lenient).pairs) == 1


def test_span_policy_require_rejects_a_disjoint_span() -> None:
    gold = [triple("g1", "A Foundry", "B Coupler", span=(0, 40))]
    got = [triple("c1", "A Foundry", "B Coupler", span=(400, 440))]
    assert len(match_claims(gold, got, POLICY).pairs) == 1        # bonus mode: spans do not gate
    strict = POLICY.model_copy(update={"span_policy": "require"})
    assert match_claims(gold, got, strict).pairs == ()
    assert match_claims(gold, got, strict).rejections.get("span_iou") == 1


def test_span_bonus_breaks_a_surface_tie_toward_the_right_citation() -> None:
    gold = [triple("g1", "A Foundry", "B Coupler", span=(10, 60))]
    got = [
        triple("far", "A Foundry", "B Coupler", span=(900, 950)),
        triple("near", "A Foundry", "B Coupler", span=(12, 58)),
    ]
    pairs = match_claims(gold, got, POLICY).pairs
    assert len(pairs) == 1 and pairs[0].extracted.key == "near"


def test_alignment_is_one_to_one() -> None:
    """Two identical extractions of one gold claim cannot both be credited."""
    gold = [triple("g1", "A Foundry", "B Coupler")]
    got = [triple("c1", "A Foundry", "B Coupler"), triple("c2", "A Foundry", "B Coupler")]
    result = match_claims(gold, got, POLICY)
    assert len(result.pairs) == 1
    assert result.precision == 0.5           # the duplicate is a false positive
    assert len(result.unmatched_extracted) == 1


def test_alignment_is_deterministic_under_input_reordering() -> None:
    gold = [triple("g1", "A Foundry", "B Coupler"), triple("g2", "C Works", "D Valve")]
    got = [triple("c1", "C Works", "D Valve"), triple("c2", "A Foundry", "B Coupler")]
    first = match_claims(gold, got, POLICY)
    second = match_claims(list(reversed(gold)), list(reversed(got)), POLICY)
    assert {(p.gold.key, p.extracted.key) for p in first.pairs} == \
           {(p.gold.key, p.extracted.key) for p in second.pairs}


def test_precision_recall_f1_on_a_mixed_run() -> None:
    gold = [triple("g1", "A Foundry", "B Coupler"), triple("g2", "C Works", "D Valve")]
    got = [triple("c1", "A Foundry", "B Coupler"), triple("c2", "Invented Works", "Invented Valve")]
    result = match_claims(gold, got, POLICY)
    assert result.precision == 0.5 and result.recall == 0.5 and result.f1 == 0.5
    assert [g.key for g in result.missed_gold] == ["g2"]


def test_empty_sides_are_flagged_degenerate_not_scored_as_perfect() -> None:
    assert match_claims([], [], POLICY).degenerate is True
    assert match_claims([], [], POLICY).f1 == 0.0


def test_default_similarity_rejects_a_hallucinated_name_sharing_one_token() -> None:
    """The reason the default is token_sort_ratio: token_set_ratio would credit this as a match."""
    gold = [entity("g1", "C Works")]
    got = [entity("c1", "Invented Works")]
    assert match_claims(gold, got, POLICY).pairs == ()
    lenient = POLICY.model_copy(update={"similarity": "token_set_ratio"})
    assert len(match_claims(gold, got, lenient).pairs) == 1


def test_similarity_handles_empty_operands() -> None:
    assert similarity(None, None, POLICY) == 1.0
    assert similarity("something", None, POLICY) == 0.0
