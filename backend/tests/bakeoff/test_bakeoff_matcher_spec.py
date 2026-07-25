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

    **Thresholds re-calibrated at integration (.50/.99, was .80/.99), and the reason is a finding.** The
    shipped matcher scores this exact pair at **0.5455**, so the original pair sat *below both* thresholds
    and could never straddle — the gate was red for a mis-calibrated fixture, not an inert rule. The claim
    pair is deliberately unchanged; only the brackets moved, so the property still proves itself on the
    author's own example.

    Why 0.5455, and why it matters beyond this test: ``normalize_surface`` rewrites ``-_/`` to a SPACE
    (right for predicates — ``supplies-component`` ≡ ``supplies component``), which turns "HT-233" into
    two tokens while "HT233" stays one; ``token_sort_ratio`` then compares "ht 233" against "ht233" and
    penalises the split hard. This corpus's most important surfaces are exactly that shape — HQ-9/P,
    HT-233, FD-2000, HQ-9BE — so under the shipped default a legitimate de-hyphenated variant is scored a
    NON-match. That depresses recall for every candidate equally and adds run-to-run variance.

    It is pinned below rather than fixed here: choosing the kernel/normaliser is a measurement-policy call
    that changes every number the bake-off produces, and the implementer explicitly referred it to whoever
    owns the labeled gold. Tuning it here — from one synthetic pair, by someone who has now read the gold
    — is the exact failure the matcher's own docstring warns against.
    """
    gold = [claim("HQ-9/P echo", "supplies-component", "HT-233", "d01", (10, 60))]
    pred = [claim("HQ-9/P echo", "supplies-component", "HT233", "d01", (10, 60))]  # near-miss surface
    lenient = do_match(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.50))
    strict = do_match(gold, pred, rule=dict(DEFAULT_RULE, surface_threshold=0.99))
    assert lenient.recall > strict.recall, why(
        f"MATCHER-RULE-INERT: 'HT233' vs 'HT-233' scored recall={lenient.recall} at threshold .50 and "
        f"{strict.recall} at .99 — the configured leniency changed nothing. Either the rule argument is "
        "ignored (the harness advertises a control it does not have) or the match is exact-only and the "
        "'fuzzy surface alignment' plan §8 asks for does not exist, which hides every real difference in "
        "surface handling between the candidates."
    )


def test_hyphenation_variants_are_scored_a_nonmatch_by_the_shipped_default():
    """Pins the finding above as an asserted fact, so it cannot regress quietly in either direction.

    This is NOT an endorsement — a de-hyphenated designator *is* the same claim to any analyst, and the
    shipped default calls it a miss. The assertion exists so that whoever re-tunes the match policy sees
    this go red and makes the change deliberately, rather than discovering afterwards that every recall
    number in the bake-off moved.
    """
    gold = [claim("HQ-9/P foxtrot", "supplies-component", "HT-233", "d01", (10, 60))]
    pred = [claim("HQ-9/P foxtrot", "supplies-component", "HT233", "d01", (10, 60))]
    assert do_match(gold, pred).recall == 0.0, (
        "The shipped match policy now ACCEPTS a de-hyphenated designator variant. That is very likely an "
        "improvement, but it moves every recall/F1 number this bake-off produces, so it must be a "
        "deliberate re-tuning against a labeled sample — re-baseline the scorecard, then update this test."
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
