"""RK-BAKEOFF gate 4 — **the claim matcher's leniency is explicit, configurable and stable.**

Plan §8 asks for "a **claim-matcher + scorecard**: fuzzy surface/span alignment → precision/recall/F1 over
claims". The word doing the damage is *fuzzy*. Every number in this bake-off — every F1, every margin, the
noise band itself — is produced by this one function. So the matcher is not a helper; it is the ruler. A
ruler needs three properties, or the comparison it feeds is void:

* **Stable.** Same gold, same predictions, same answer — every time, in any order, with no memory between
  calls. A matcher carrying state across invocations (a "seen" set, a cache keyed on surface, a lazily
  populated alias table) silently makes whichever candidate is scored *second* look worse. That is an
  ordering artefact indistinguishable from a real capability gap, and it would decide the bake-off.
* **One-to-one.** A gold claim may be satisfied by at most one prediction and vice versa. Many-to-one
  greedy matching lets one lucky prediction cover several gold rows — recall inflates, and precision can
  exceed 1.0, which is the tell.
* **Explicit and configurable.** The leniency threshold has to be readable and settable. "Fuzzy" that
  nobody can inspect means no reader can tell whether "HT-233" matching "HT-233 radar" was generosity or a
  bug — and two candidates scored under different implicit leniencies were never compared at all.

The stability test is the one that matters most and looks least interesting; it is the failure that leaves
no trace in the output.

**Test-data hygiene.** Each test below uses its own claim surfaces. A stateful matcher must be caught by
the test that names statefulness, not accidentally masked (or accidentally exposed) by residue from the
test that ran before it — otherwise these gates would pass or fail depending on collection order.
"""

from __future__ import annotations

import random

from tests.bakeoff._bakeoff_contract_spec import (
    DEFAULT_RULE,
    claim,
    do_match,
    match_view,
    reference_match_claims,
    why,
)


def _triples(tag: str):
    """Three gold claims and three predictions (two hits, one wrong object), namespaced by ``tag``."""
    gold = [
        claim(f"HQ-9/P {tag}", "supplies-component", f"HT-233 {tag}", "d01", (10, 60)),
        claim(f"CASIC {tag}", "manufactures", f"HQ-9 {tag}", "d01", (70, 120)),
        claim(f"8 AD Bn {tag}", "based-at", f"Rahwali {tag}", "d02", (0, 44)),
    ]
    pred = [
        gold[0],
        gold[1],
        claim(f"8 AD Bn {tag}", "based-at", f"Sargodha {tag}", "d02", (0, 44)),  # wrong object
    ]
    return gold, pred


def _prf(res) -> tuple[float, float, float]:
    return (round(res.precision, 9), round(res.recall, 9), round(res.f1, 9))


# ── the gate ──────────────────────────────────────────────────────────────────────────────────────

def test_matcher_is_stable_across_invocations():
    gold, pred = _triples("alpha")
    first = do_match(gold, pred)
    second = do_match(gold, pred)
    assert _prf(first) == _prf(second), why(
        f"MATCHER-UNSTABLE: the same gold and the same predictions scored {_prf(first)} then "
        f"{_prf(second)}. The matcher is carrying state between calls, so whichever candidate is scored "
        "second is penalised for nothing. Every F1, margin and noise band in this bake-off comes out of "
        "this function; if it drifts, the comparison is void and the drift is invisible in the report."
    )
    assert sorted(first.pairs) == sorted(second.pairs), why(
        f"MATCHER-UNSTABLE-PAIRS: the matched pairs changed between identical invocations "
        f"({sorted(first.pairs)} then {sorted(second.pairs)}) even where the aggregate happened to "
        "agree — the alignment a human would audit is not reproducible."
    )


def test_matcher_is_order_independent():
    gold, pred = _triples("bravo")
    base = do_match(gold, pred)
    rng = random.Random(20260725)
    for _ in range(4):
        g, p = list(gold), list(pred)
        rng.shuffle(g)
        rng.shuffle(p)
        shuffled = do_match(g, p)
        assert _prf(shuffled) == _prf(base), why(
            f"MATCHER-ORDER-DEPENDENT: re-presenting the *same* claim sets scored {_prf(base)} then "
            f"{_prf(shuffled)}. Either the alignment depends on the accident of which claim the model's "
            "tool call emitted first, or the matcher remembers previous calls. Both make the score a "
            "function of the harness's bookkeeping rather than of the extraction."
        )


def test_matcher_is_one_to_one():
    """A document that states the same triple twice must not let one prediction cover both."""
    gold = [claim("Nur Khan charlie", "hosts", "TEL-4 charlie", "d03", (10, 60)),
            claim("Nur Khan charlie", "hosts", "TEL-4 charlie", "d03", (200, 250))]
    pred = [claim("Nur Khan charlie", "hosts", "TEL-4 charlie", "d03", (10, 60))]
    res = do_match(gold, pred)
    assert res.precision <= 1.0 and res.recall <= 1.0, why(
        f"MATCHER-DOUBLE-COUNTS: precision={res.precision}, recall={res.recall} for one prediction "
        "against two gold rows. A score above 1.0 is the tell that one prediction was credited against "
        "several gold claims — many-to-one greedy matching. It inflates whichever model repeats itself."
    )
    gold_idx = [i for i, _ in res.pairs]
    pred_idx = [j for _, j in res.pairs]
    assert len(set(gold_idx)) == len(gold_idx) and len(set(pred_idx)) == len(pred_idx), why(
        f"MATCHER-NOT-INJECTIVE: pairs {res.pairs} reuse a gold or prediction index. The alignment must "
        "be a matching, not a covering, or recall stops meaning 'how much of the document was found'."
    )


def test_matcher_leniency_is_introspectable():
    gold, pred = _triples("delta")
    res = do_match(gold, pred)
    rule = res.rule
    described = rule() if callable(rule) else rule
    assert described, why(
        "MATCHER-RULE-OPAQUE: the match result exposes no rule/describe() — the leniency that produced "
        "every number in the scorecard is undocumented. A reader cannot tell whether a near-miss surface "
        "counted as a hit, so they cannot tell whether the winner won on extraction quality or on the "
        "matcher's generosity."
    )


def test_matcher_leniency_is_configurable_and_actually_bites():
    """A `rule` argument the matcher ignores is worse than none — it advertises control it lacks.

    **Fixture re-pointed 2026-07-25, and the reason is the finding this file used to pin.** The original
    fixture straddled on 'HT-233' vs 'HT233', which the then-shipped kernel scored 0.5455 — a non-match for
    a designator variant any analyst calls the same thing. The gold owner has since decided the identifier
    rule against the labeled sample (``config/bakeoff.yaml`` → ``identifier_policy``), so that pair scores
    1.0000 and can no longer straddle anything.

    The property under test is unchanged, and it was never about hyphens: a configured surface threshold
    must change the alignment. It is now proved on the added-qualifier case the config's own note names —
    "Type-7 Coupler" vs "Type-7 Coupler assembly", 0.7568 — which stays genuinely fuzzy under every
    identifier setting and is therefore a stable home for this gate.
    """
    gold = [claim("Type-7 Coupler echo", "supplies-component", "Type-7 Coupler", "d01", (10, 60))]
    pred = [claim("Type-7 Coupler echo", "supplies-component", "Type-7 Coupler assembly", "d01", (10, 60))]
    lenient = do_match(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.50))
    strict = do_match(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.99))
    assert lenient.recall > strict.recall, why(
        f"MATCHER-RULE-INERT: an added qualifier scored recall={lenient.recall} at threshold .50 and "
        f"{strict.recall} at .99 — the configured leniency changed nothing. Either the rule argument is "
        "ignored (the harness advertises a control it does not have) or the match is exact-only and the "
        "'fuzzy surface alignment' plan §8 asks for does not exist, which hides every real difference in "
        "surface handling between the candidates."
    )


def test_a_dehyphenated_designator_matches_and_a_sibling_designator_does_not():
    """The identifier rule, pinned in BOTH directions so neither can drift quietly.

    This replaces the earlier assertion that a de-hyphenated designator scored a NON-match. That assertion
    was a tripwire — "whoever re-tunes the match policy must see this go red and make the change
    deliberately" — and it did its job: the gold owner made the call on 2026-07-25 against the labeled
    slice. The tripwire is re-armed here, pointing at the decided behaviour.

    Measured over the gold's own 247 distinct surfaces (full numbers, and the two costs, in
    ``config/bakeoff.yaml`` → ``identifier_policy``):

    * legitimate de-hyphenated designator variants below the role floor: **16 of 61 → 0 of 61**;
    * genuinely-different designator pairs conflated at the role floor: **40 of 684 → 0 of 684**. The prose
      kernel already merged HQ-9A into HQ-9B (0.80), HQ-9B into HQ-9BE (0.91) and two different GD numbers
      (0.95) — no edit-distance floor separates one changed character in a six-character designator, so
      designator disagreement is a veto rather than a score.

    Both halves are asserted because they trade against each other. Loosen the veto to recover an alias and
    you start merging sibling variants — the over-merge this project exists to prevent. Revert the glue and
    you re-impose a systematic recall loss on every candidate at once.
    """
    gold = [claim("HQ-9/P foxtrot", "supplies-component", "HT-233", "d01", (10, 60))]
    same = [claim("HQ-9/P foxtrot", "supplies-component", "HT233", "d01", (10, 60))]
    assert do_match(gold, same).recall == 1.0, (
        "MATCHER-SPLITS-DESIGNATORS: 'HT233' scored a non-match for 'HT-233'. That is the pre-2026-07-25 "
        "behaviour — hyphens rewritten to spaces split an identifier into tokens, and this corpus's key "
        "surfaces are all that shape (HQ-9/P, HQ-9BE, HT-233, FD-2000, S-400), so 16 of 61 legitimate "
        "variants in the labeled gold read as misses. Reverting depresses recall for every candidate at "
        "once and adds variance to a comparison already fighting non-determinism."
    )
    sibling = [claim("HQ-9/P foxtrot", "supplies-component", "HT-233A", "d01", (10, 60))]
    assert do_match(gold, sibling).recall == 0.0, (
        "MATCHER-MERGES-SIBLING-DESIGNATORS: 'HT-233A' was accepted as 'HT-233' (fuzzy score 0.91). A "
        "suffixed designator is a different variant — HQ-9B vs HQ-9BE, FT-2000 vs FT-2000A, S-400 vs "
        "S-300 — and conflating them is exactly the over-merge this project exists to prevent."
    )
    other_variant = [claim("HQ-9BE foxtrot", "supplies-component", "HT-233", "d01", (10, 60))]
    assert do_match(gold, other_variant).recall == 0.0, (
        "MATCHER-MERGES-SIBLING-DESIGNATORS (subject role): 'HQ-9BE' was accepted as 'HQ-9/P'. Those are "
        "two variants with two different operators, and the labeled sub-oracle carries an explicit "
        "distinct-from between them."
    )


# ── positive controls ─────────────────────────────────────────────────────────────────────────────

def test_positive_control_reference_matcher_is_stable_and_injective():
    gold, pred = _triples("ref")
    a = reference_match_claims(gold, pred)
    b = reference_match_claims(gold, pred)
    assert _prf(match_view(a)) == _prf(match_view(b))
    assert a.pairs == b.pairs
    assert a.precision == 2 / 3 and a.recall == 2 / 3

    dup = [claim("Nur Khan ref", "hosts", "TEL-4 ref", "d03", (10, 60)),
           claim("Nur Khan ref", "hosts", "TEL-4 ref", "d03", (200, 250))]
    one = reference_match_claims(dup, [claim("Nur Khan ref", "hosts", "TEL-4 ref", "d03", (10, 60))])
    assert one.precision == 1.0 and one.recall == 0.5


def test_positive_control_reference_rule_is_explicit_and_bites():
    gold = [claim("HQ-9/P ref", "supplies-component", "HT-233", "d01", (10, 60))]
    pred = [claim("HQ-9/P ref", "supplies-component", "HT233", "d01", (10, 60))]
    assert reference_match_claims(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.80)).recall == 1.0
    assert reference_match_claims(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.99)).recall == 0.0
    assert reference_match_claims(gold, pred).describe()


def test_positive_control_reference_matcher_is_order_independent():
    gold, pred = _triples("refshuffle")
    base = match_view(reference_match_claims(gold, pred))
    rng = random.Random(7)
    for _ in range(4):
        g, p = list(gold), list(pred)
        rng.shuffle(g)
        rng.shuffle(p)
        assert _prf(match_view(reference_match_claims(g, p))) == _prf(base)
