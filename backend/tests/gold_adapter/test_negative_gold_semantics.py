"""The check that decides whether the bake-off is honest.

A hypothetical PERFECT model — one emitting exactly the positive gold and nothing else — must score 1.0
recall. If the 40 negative rows are loaded as positives instead, that model is capped at 65/127 ≈ 0.51,
and every candidate is charged ~0.49 recall for a loader artefact. That is the whole reason the adapter
exists, so it is measured here rather than argued.

Two ceilings, and they are NOT the same number — keeping them apart is the point:

* **65/127 ≈ 0.512** — a candidate emitting only what the extraction pipeline can express. This is the
  honest statement of what the adapter is worth, because the 22 attribute rows are excluded from scoring
  precisely on the grounds that the pipeline cannot express an attribute as a claim.
* **87/127 ≈ 0.685** — a candidate that *additionally* emitted all 22 attribute rows. A real candidate
  cannot reach this, so quoting it alone understates the artefact by ~0.17 recall.

Both ceilings are *derived from the census* below rather than pinned as decimals: the 2026-07-26 gold
repair moved them (from 0.520 and 0.696) without touching anything they are used to argue, and a
re-derivable ratio cannot rot that way a second time.

Two layers, on purpose:

* the **arithmetic** layer runs always and needs nothing but the adapted file — the denominators are what
  they are;
* the **scorer** layer runs the real ``eval.extraction`` matcher and metrics when they are present in the
  checkout (they land with the impl hand's branch), so the claim is verified against the code that will
  actually produce the numbers, not against a re-implementation of it.
"""

from __future__ import annotations

from typing import Any

import pytest

from eval.gold.adapter import (
    NEGATIVE_GOLD_SEMANTICS,
    EmittedSpan,
    identity_over_read,
    precision_exclusions,
    trap_avoidance,
)

from .conftest import EXPECTED

NEGATIVE_ROWS = (EXPECTED["not_a_claim"] + EXPECTED["anti_coref"]
                 + EXPECTED["ambiguous"] + EXPECTED["unmodelled"])


# ── the arithmetic: what each denominator is, and what the naive one would have been ───────────────

def test_the_recall_denominator_is_the_positive_gold_only(adapted: dict[str, Any]) -> None:
    assert adapted["reconciliation"]["scored_recall_denominator"] == EXPECTED["claims"] == 65
    # 40, not the 38 frozen on 2026-07-25: the 2026-07-26 gold repair appended two ANTI_COREF
    # prohibition rows. The emittable count is unchanged at 87 — both rows are negative gold.
    assert NEGATIVE_ROWS == 40
    assert EXPECTED["rows"] - NEGATIVE_ROWS == 87


def test_a_perfect_model_is_not_capped(adapted: dict[str, Any]) -> None:
    """Recall 65/65 = 1.00 through the adapter, against both naive ceilings.

    ``expressible`` is the ceiling that describes a real candidate (≈0.512); ``with_attributes`` is the
    ceiling for one that also emitted the 22 unexpressible attribute rows (≈0.685). Asserting both stops
    either being quoted as "the" naive number.
    """
    adapted_recall = EXPECTED["claims"] / adapted["reconciliation"]["scored_recall_denominator"]
    expressible = EXPECTED["claims"] / EXPECTED["rows"]
    with_attributes = (EXPECTED["rows"] - NEGATIVE_ROWS) / EXPECTED["rows"]
    assert adapted_recall == 1.0
    # was 0.520 / 0.696 over 125 rows; the 2026-07-26 repair added two negative rows to the naive
    # denominator without adding anything a candidate can score, so both ceilings fall slightly.
    assert round(expressible, 3) == 0.512
    assert round(with_attributes, 3) == 0.685
    # the artefact is ~0.49 for a candidate emitting only what the pipeline can produce
    assert adapted_recall - expressible > 0.47
    assert adapted_recall - with_attributes > 0.30


def test_no_negative_row_reaches_the_claims_array(adapted: dict[str, Any]) -> None:
    """The one thing that would silently reintroduce the cap."""
    negative_ids = {r["gold_id"] for block in adapted["negative_gold"].values()
                    for r in block["rows"]}
    claim_ids = {c["gold_id"] for c in adapted["claims"]}
    assert negative_ids & claim_ids == set()
    assert len(negative_ids) == NEGATIVE_ROWS


def test_negative_rows_are_not_shaped_like_claims(adapted: dict[str, Any]) -> None:
    """A negative record must be unloadable as a claim even if someone points the loader at it."""
    for block in adapted["negative_gold"].values():
        for row in block["rows"]:
            assert "form" not in row, "a negative row carrying a form could be loaded as gold"
            assert "class" in row and "surfaces" in row


def test_attribute_rows_are_excluded_and_named(adapted: dict[str, Any]) -> None:
    """S2: excluded from scoring *and* carrying the reason — never silently absent."""
    block = adapted["excluded_from_scoring"]["attribute_rows"]
    assert len(block["rows"]) == EXPECTED["attribute_rows"]
    assert "attribute" in block["reason"].lower()
    assert "22" in block["reason"], "the reason must name the size of what it excludes"
    assert all("form" not in r for r in block["rows"])


# ── each class is scored per its own meaning, and says whether that is wired ───────────────────────

def test_each_class_declares_a_distinct_scoring_role(adapted: dict[str, Any]) -> None:
    roles = {name: block["scoring_role"] for name, block in adapted["negative_gold"].items()}
    assert roles == {
        "not_a_claim": "penalise_emission",
        "anti_coref": "penalise_binding",
        "ambiguous": "penalise_identity_assertion",
        "unmodelled": "neutral_exclude",
    }
    assert len(set(roles.values())) == 4, "two classes sharing a role means one was conflated"


def test_every_class_leaves_the_recall_denominator(adapted: dict[str, Any]) -> None:
    for block in adapted["negative_gold"].values():
        assert block["recall_denominator"] == "excluded"


def test_precision_exclusions_declare_whether_they_are_wired(adapted: dict[str, Any]) -> None:
    """The conflation this file exists to prevent: claiming an exclusion the harness does not perform."""
    for name, block in adapted["negative_gold"].items():
        assert "precision_exclusion_automatic" in block, name
        assert "harness_hook" in block, name
    assert NEGATIVE_GOLD_SEMANTICS["not_a_claim"]["precision_exclusion_automatic"].startswith("n/a")
    for name in ("anti_coref", "ambiguous", "unmodelled"):
        assert NEGATIVE_GOLD_SEMANTICS[name]["precision_exclusion_automatic"].startswith("NO"), name


def test_the_binding_classes_refuse_to_publish_a_zero(adapted: dict[str, Any]) -> None:
    """anti_coref is S3-dependent; its instruction must be UNAVAILABLE, never 0.00."""
    assert "UNAVAILABLE" in adapted["negative_gold"]["anti_coref"]["how_to_score"]
    assert "never 0.00" in adapted["negative_gold"]["anti_coref"]["how_to_score"]


def test_the_two_row_class_forbids_a_rate(adapted: dict[str, Any]) -> None:
    how = adapted["negative_gold"]["ambiguous"]["how_to_score"]
    assert "N=2" in how and "never rank" in how


# ── the hooks: emitting a trap costs the candidate; reading correctly does not ─────────────────────

def _emissions(adapted: dict[str, Any], bucket: str, *, matched: bool = False,
               predicate: str | None = None) -> list[EmittedSpan]:
    """One emitted claim per row of ``bucket``, sitting exactly on that row's span."""
    return [
        EmittedSpan(key=f"cand-{row['gold_id']}", file=row["doc_ref"]["file"],
                    span=tuple(row["doc_ref"]["span"]), matched=matched, predicate=predicate)
        for row in adapted["negative_gold"][bucket]["rows"]
    ]


def test_a_silent_model_scores_a_perfect_trap_rate(adapted: dict[str, Any]) -> None:
    result = trap_avoidance(adapted, [])
    assert result["traps"] == EXPECTED["not_a_claim"] == 11
    assert result["hit"] == 0
    assert result["rate"] == 1.0


def test_a_model_that_emits_the_traps_is_penalised(adapted: dict[str, Any]) -> None:
    result = trap_avoidance(adapted, _emissions(adapted, "not_a_claim"))
    assert result["hit"] == 11
    assert result["avoided"] == 0
    assert result["rate"] == 0.0
    assert len(result["hits_by_trap"]) == 11


def test_a_matched_claim_is_never_a_trap_hit(adapted: dict[str, Any]) -> None:
    """d20-r13's trap span overlaps positive claim d20-r14's, so ``matched`` has to be load-bearing.

    Without it, a model that emitted d20-r14 *correctly* is charged with falling for a trap — the harness
    fabricating a fabrication finding.
    """
    honest = _emissions(adapted, "not_a_claim", matched=True)
    assert trap_avoidance(adapted, honest)["hit"] == 0
    # and the overlap that makes this necessary is real
    trap = next(r for r in adapted["negative_gold"]["not_a_claim"]["rows"]
                if r["gold_id"] == "d20-r13")
    overlapping = [
        c["gold_id"] for c in adapted["claims"]
        if c["doc_ref"]["file"] == trap["doc_ref"]["file"]
        and min(c["doc_ref"]["span"][1], trap["doc_ref"]["span"][1])
        > max(c["doc_ref"]["span"][0], trap["doc_ref"]["span"][0])
    ]
    assert overlapping == ["d20-r14"]


def test_traps_are_addressed_by_span_not_by_document(adapted: dict[str, Any]) -> None:
    """A claim in the same document but elsewhere is not a trap hit."""
    row = adapted["negative_gold"]["not_a_claim"]["rows"][0]
    elsewhere = EmittedSpan(key="cand-x", file=row["doc_ref"]["file"], span=(0, 1))
    result = trap_avoidance(adapted, [elsewhere])
    assert result["hit"] == 0 or row["doc_ref"]["span"][0] == 0


def test_only_an_identity_assertion_over_read_counts(adapted: dict[str, Any]) -> None:
    """S7: silence is right, a same-as is wrong, and an ordinary claim over the span is neither."""
    assert identity_over_read(adapted, [])["over_read"] == 0
    asserted = identity_over_read(adapted, _emissions(adapted, "ambiguous", predicate="same-as"))
    assert asserted["pairs"] == EXPECTED["ambiguous"] == 2
    assert asserted["over_read"] == 2
    ordinary = identity_over_read(adapted, _emissions(adapted, "ambiguous", predicate="observed-at"))
    assert ordinary["over_read"] == 0, "a non-identity claim over an ambiguous span is not an error"


def test_precision_exclusions_cover_the_neutral_classes(adapted: dict[str, Any]) -> None:
    """One class at a time, so a cross-class span overlap cannot flatter the count."""
    for bucket, expected in (("unmodelled", EXPECTED["unmodelled"]),
                             ("anti_coref", EXPECTED["anti_coref"])):
        result = precision_exclusions(adapted, _emissions(adapted, bucket))
        assert len(result["by_class"][bucket]) == expected, bucket
    ordinary = precision_exclusions(adapted, _emissions(adapted, "ambiguous", predicate="observed-at"))
    assert len(ordinary["by_class"]["ambiguous"]) == EXPECTED["ambiguous"]


def test_a_trap_emission_is_never_excused(adapted: dict[str, Any]) -> None:
    emitted = (_emissions(adapted, "unmodelled") + _emissions(adapted, "anti_coref")
               + _emissions(adapted, "not_a_claim")
               + _emissions(adapted, "ambiguous", predicate="observed-at"))
    result = precision_exclusions(adapted, emitted)
    trap_keys = {e.key for e in _emissions(adapted, "not_a_claim")}
    assert trap_keys & set(result["exclude_from_precision_denominator"]) == set(), \
        "a trap emission must keep costing precision"


def test_overlapping_negative_spans_do_not_excuse_a_trap(adapted: dict[str, Any]) -> None:
    """The classes are annotated on overlapping spans, so precedence has to be decided, not assumed.

    A single emitted claim placed on a trap span that also overlaps an ``unmodelled`` span must stay in
    the precision denominator: the trap is the stronger fact about it.
    """
    trap = adapted["negative_gold"]["not_a_claim"]["rows"][0]
    same_doc = [r for r in adapted["negative_gold"]["unmodelled"]["rows"]
                if r["doc_ref"]["file"] == trap["doc_ref"]["file"]]
    assert same_doc, "no unmodelled row shares a document with this trap: the test would be vacuous"
    lo = min([trap["doc_ref"]["span"][0]] + [r["doc_ref"]["span"][0] for r in same_doc])
    hi = max([trap["doc_ref"]["span"][1]] + [r["doc_ref"]["span"][1] for r in same_doc])
    both = EmittedSpan(key="cand-both", file=trap["doc_ref"]["file"], span=(lo, hi))

    result = precision_exclusions(adapted, [both])
    assert result["by_class"]["unmodelled"] == []
    assert result["also_a_trap_hit_so_not_excused"] == ["cand-both"]
    assert trap_avoidance(adapted, [both])["hit"] >= 1


def test_an_identity_over_read_is_not_also_excused(adapted: dict[str, Any]) -> None:
    """One error scored once: an over-read is penalised by its own metric, so it stays in precision."""
    emitted = _emissions(adapted, "ambiguous", predicate="distinct-from")
    result = precision_exclusions(adapted, emitted)
    assert result["by_class"]["ambiguous"] == []


# ── the same claims, measured through the real scorer ──────────────────────────────────────────────

def _policy(**overrides: Any) -> Any:
    """The bake-off's declared match policy, pinned to the values in ``config/bakeoff.yaml``.

    Pinned rather than loaded so this test measures the ADAPTER: if someone later slackens the config, the
    loader-artefact proof must not quietly start measuring the new leniency instead. The identifier knobs
    are named for the same reason — they were decided on 2026-07-25 and they move every recall number in
    the bake-off, so this proof must state which setting it was measured under rather than inherit it.
    """
    from eval.extraction.policy import MatchPolicy

    declared: dict[str, Any] = dict(
        similarity="token_sort_ratio", require_same_form=True, require_same_polarity=True,
        predicate_policy="normalized", entity_type_policy="normalized",
        identifier_policy="designator_aware", identifier_agreement="nested_or_equal",
        role_min_similarity=0.70, pair_min_similarity=0.80, span_policy="bonus",
        span_iou_floor=0.30, span_bonus_weight=0.15, grounding_similarity=0.85,
    )
    return MatchPolicy(**{**declared, **overrides})


@pytest.fixture
def scorer() -> Any:
    """The impl hand's scorer, or a skip. Lands in the same checkout once bakeoff/rk-impl merges."""
    pytest.importorskip(
        "eval.extraction.matcher",
        reason="eval.extraction (the bake-off scorer) is not in this checkout yet — it arrives with "
               "bakeoff/rk-impl. The arithmetic proof above does not depend on it.",
    )
    import eval.extraction.gold as gold_mod
    import eval.extraction.matcher as matcher_mod
    import eval.extraction.surface as surface_mod

    return gold_mod, matcher_mod, surface_mod


def _write(path: Any, claims: list[dict[str, Any]]) -> Any:
    import json

    path.write_text(json.dumps({"schema_version": "rk-bakeoff-claim-gold/1.0", "claims": claims}),
                    encoding="utf-8")
    return path


def test_scorer_loads_the_adapted_gold(scorer: Any, adapted: dict[str, Any], tmp_path: Any) -> None:
    gold_mod, _, _ = scorer
    loaded = gold_mod.load_claim_gold(_write(tmp_path / "gold.json", adapted["claims"]))
    assert len(loaded) == EXPECTED["claims"]
    assert {g.form for g in loaded} == {"triple", "entity", "event"}


def test_perfect_model_scores_one_through_the_adapter(
    scorer: Any, adapted: dict[str, Any], tmp_path: Any,
) -> None:
    """THE measurement. Candidate == exactly the positive gold, under its own claim ids."""
    gold_mod, matcher_mod, surface_mod = scorer
    gold = gold_mod.load_claim_gold(_write(tmp_path / "gold.json", adapted["claims"]))
    candidate = [
        surface_mod.SurfaceClaim(
            key=f"cand-{i:03d}", source_id=g.source_id, form=g.form, polarity=g.polarity,
            roles=dict(g.roles), predicate=g.predicate, entity_type=g.entity_type, refs=g.refs,
        )
        for i, g in enumerate(gold)
    ]
    result = matcher_mod.match_claims(gold, candidate, _policy())
    assert result.recall == 1.0
    assert result.precision == 1.0
    assert len(result.pairs) == EXPECTED["claims"]
    assert result.missed_gold == ()

    # The 2026-07-25 identifier decision must NOT be what produces the 1.0 — a perfect model scores 1.0
    # under every setting of it, because a perfect model's surfaces are byte-identical to the gold's. If
    # this ever diverges, the identifier rule has started deciding the headline number instead of the
    # loader semantics this file exists to prove.
    for override in ({"identifier_policy": "prose"}, {"identifier_agreement": "ignore"},
                     {"identifier_policy": "prose", "identifier_agreement": "ignore"}):
        under = matcher_mod.match_claims(gold, candidate, _policy(**override))
        assert (under.recall, under.precision) == (1.0, 1.0), override


def test_the_naive_load_caps_the_same_model_at_070(
    scorer: Any, raw_gold: dict[str, Any], adapted: dict[str, Any], tmp_path: Any,
) -> None:
    """The counterfactual, measured: all 127 rows as positives.

    Two candidates, because the two ceilings are different claims about different models:

    * ``emittable`` (87 rows = 65 claims + 22 attribute rows) is the FLATTERING ceiling. Note what it
      credits — a model matching the 22 attribute rows, which the adapter excludes from scoring *on the
      grounds that the pipeline cannot express an attribute as a claim*. It describes a model that
      cannot exist, and it still lands under 0.70.
    * a candidate emitting only the 65 claim-shaped rows is the HONEST ceiling, the one that describes a
      real extractor, and it sits below the flattering one.

    Asserting both keeps the honest figure from being displaced by the flattering one.

    Both are asserted as RATIOS OVER THE CENSUS, not as the decimals they happened to be on 2026-07-25
    (0.696 / 0.520). The 2026-07-26 gold repair moved those decimals to 0.685 / 0.512 while leaving every
    claim this test makes intact — pinning the decimal turned a live proof into a stale one, so the
    property is what is pinned now.
    """
    gold_mod, matcher_mod, surface_mod = scorer
    paths = {d["doc_id"]: d["path"] for d in raw_gold["documents"]}
    naive: list[dict[str, Any]] = []
    for row in raw_gold["rows"]:
        # the mechanical encoding someone reaches for without an adapter. Note the polarity coercion:
        # 13 rows are labeled "unknown", which the scorer's loader refuses outright — the naive path
        # cannot even load without a second silent edit.
        polarity = row["polarity"] if row["polarity"] in ("positive", "negative") else "positive"
        prefix = row["predicate"].split(":", 1)[0]
        claim: dict[str, Any] = {"gold_id": row["row_id"], "source_id": row["doc_id"],
                                 "polarity": polarity,
                                 "doc_ref": {"file": paths[row["doc_id"]]}}
        if prefix == "ENTITY_EXISTS":
            claim |= {"form": "entity", "name": row["subject_surface"],
                      "entity_type": row["object_surface"]}
        elif prefix == "EVENT":
            claim |= {"form": "event", "event_type": row["predicate"].split(":", 1)[1],
                      "participants": [p.strip() for p
                                       in row["object_surface"].split(":", 1)[1].split(";")
                                       if p.strip()]}
        else:
            claim |= {"form": "triple", "subject": row["subject_surface"],
                      "predicate": row["predicate"], "object": row["object_surface"]}
        naive.append(claim)

    naive_gold = gold_mod.load_claim_gold(_write(tmp_path / "naive.json", naive))
    assert len(naive_gold) == EXPECTED["rows"]
    negative_prefixes = ("NOT_A_CLAIM", "ANTI_COREF", "AMBIGUOUS", "UNMODELLED")
    emittable = {r["row_id"] for r in raw_gold["rows"]
                 if not r["predicate"].startswith(negative_prefixes)}
    candidate = [
        surface_mod.SurfaceClaim(
            key=f"cand-{i:03d}", source_id=g.source_id, form=g.form, polarity=g.polarity,
            roles=dict(g.roles), predicate=g.predicate, entity_type=g.entity_type, refs=g.refs,
        )
        for i, g in enumerate(g for g in naive_gold if g.key in emittable)
    ]
    result = matcher_mod.match_claims(naive_gold, candidate, _policy())
    assert len(candidate) == EXPECTED["rows"] - NEGATIVE_ROWS == 87
    # THE headline: the flattering ceiling is exactly emittable-rows / all-rows, and even that stays
    # under 0.70. Stated as the ratio so a change to the census re-derives it instead of rotting it.
    assert result.recall == pytest.approx((EXPECTED["rows"] - NEGATIVE_ROWS) / EXPECTED["rows"])
    assert result.recall < 0.70

    # and the ceiling for a candidate emitting only what the pipeline can actually express
    claim_shaped = {c["gold_id"] for c in adapted["claims"]}
    expressible = [c for c in candidate if c.source_id and c.key in {
        f"cand-{i:03d}" for i, g in enumerate(g for g in naive_gold if g.key in emittable)
        if g.key in claim_shaped
    }]
    assert len(expressible) == EXPECTED["claims"] == 65
    real = matcher_mod.match_claims(naive_gold, expressible, _policy())
    assert real.recall == pytest.approx(EXPECTED["claims"] / EXPECTED["rows"])
    assert real.recall < result.recall, "the honest ceiling must sit BELOW the flattering one"
    # the artefact a real candidate actually suffers is ~0.49, not ~0.31
    assert 1.0 - real.recall > 0.47


def test_emitting_the_traps_costs_precision_under_the_scorer(
    scorer: Any, adapted: dict[str, Any], tmp_path: Any,
) -> None:
    """A trap emission must be a false positive, never credited as a match, and never steal recall."""
    gold_mod, matcher_mod, surface_mod = scorer
    gold = gold_mod.load_claim_gold(_write(tmp_path / "gold.json", adapted["claims"]))
    clean = [
        surface_mod.SurfaceClaim(
            key=f"cand-{i:03d}", source_id=g.source_id, form=g.form, polarity=g.polarity,
            roles=dict(g.roles), predicate=g.predicate, entity_type=g.entity_type, refs=g.refs,
        )
        for i, g in enumerate(gold)
    ]
    traps = [
        surface_mod.SurfaceClaim(
            key=f"trap-{i:02d}", source_id=row["source_id"], form="entity", polarity="positive",
            roles={"name": row["surfaces"][0]}, entity_type="site",
            refs=(surface_mod.SpanRef(file=row["doc_ref"]["file"],
                                      span=tuple(row["doc_ref"]["span"])),),
        )
        for i, row in enumerate(adapted["negative_gold"]["not_a_claim"]["rows"])
    ]
    baseline = matcher_mod.match_claims(gold, clean, _policy())
    fell_for = matcher_mod.match_claims(gold, clean + traps, _policy())

    assert len(fell_for.pairs) == len(baseline.pairs) == EXPECTED["claims"]
    assert len(fell_for.unmatched_extracted) == EXPECTED["not_a_claim"]
    assert fell_for.recall == baseline.recall == 1.0
    assert fell_for.precision < baseline.precision
    assert round(fell_for.precision, 4) == round(65 / 76, 4)

    # and the typed class is what catches them: the existing fabrication metric does not, because the
    # trap text really is in the document.
    from eval.extraction.metrics import extract_only_stated

    doc_texts = {r["doc_ref"]["file"]: (
        __import__("pathlib").Path(__file__).resolve().parents[3] / r["doc_ref"]["file"]
    ).read_text(encoding="utf-8") for r in adapted["negative_gold"]["not_a_claim"]["rows"]}
    lexical = extract_only_stated(traps, doc_texts, _policy())
    assert lexical.value is not None and lexical.value > 0.5, (
        "if the lexical fabrication metric already caught these, the typed trap class would be "
        "redundant — it does not, which is why the class is carried"
    )
    hits = trap_avoidance(adapted, [
        EmittedSpan(key=t.key, file=t.refs[0].file, span=t.refs[0].span,
                    matched=t.key in {p.extracted.key for p in fell_for.pairs})
        for t in traps
    ])
    assert hits["hit"] == EXPECTED["not_a_claim"]
