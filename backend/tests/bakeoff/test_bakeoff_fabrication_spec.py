"""RK-BAKEOFF gate 5 — **fabrication is measured, and it is not tradeable against a higher F1.**

Plan §8 scored criteria: "citation faithfulness (**non-negotiable**) … the extract-only-stated discipline
(**non-negotiable**)". CLAUDE.md's one hard rule: "Fabricated or hallucinated assessments in evidence-sparse
cases are **disqualifying**", and "every claim/node is one-click traceable to its exact source".

This is the gate where the bake-off can betray the whole project. The other five properties protect the
*measurement*; this one protects what is being measured for. The chosen model becomes the producer that
re-extracts and re-freezes the graded oracle — so a model that asserts things its document does not say
does not merely score badly, it writes ungrounded claims into the evidence layer, where every downstream
credibility score, confirmed/probable split and cited answer inherits them **as if sourced**. There is no
later stage that catches it: the fabrication arrives wearing a citation.

Two failure modes, and the second is the subtle one:

1. **Fabrication is not measured at all.** A scorer that only checks whether the cited span *exists*, or
   that assumes the model cited honestly, cannot see the difference between a claim the document supports
   and one it does not. Faithfulness has to be established by slicing the span back out of the document
   and checking it carries the claim (G4).
2. **Fabrication is measured, then averaged away.** If citation faithfulness is one weighted line among
   several, a model can be materially *worse* at telling the truth and still win on F1. That is exactly the
   trade the project forbids. A non-negotiable that participates in a weighted sum is not a
   non-negotiable — it is a price. So the requirement is structural: a primary-metric lead must not buy off
   a materially worse fabrication or faithfulness score.

Note the deliberate asymmetry with gate 3 (gating preconditions): fabrication is a *scored* criterion in
plan §8, not a listed gating precondition, so this gate does not demand outright disqualification. It
demands only that the trade cannot be made — the lead does not purchase the win.
"""

from __future__ import annotations

from tests.bakeoff._bakeoff_contract_spec import (
    candidate,
    claim,
    clean_runs,
    do_faithfulness,
    do_match,
    do_scorecard,
    ref_scorecard,
    reference_score_faithfulness,
    why,
)

MIN_MARGIN = 0.03

DOCS = {
    "d01": "Rahwali garrison: an HQ-9/P battery with its HT-233 engagement radar was photographed on 3 May.",
}

# The span is real, IN BOUNDS, and slices back — but it says nothing about Sargodha or any S-400.
#
# The end offset is len(DOCS["d01"]), not one past it. The original fixture asked for (0, 96) against a
# 95-character document, and the shipped harness counts an out-of-bounds citation as unfaithful — which
# is correct, and is kept: a span that does not exist in the document is provenance that does not
# resolve, and one-click traceability to an exact source is what makes this system's output admissible
# at all. Python's forgiving slice is a language accident, not a licence. So the FIXTURE was wrong, not
# the check; correcting it here preserves the anti-vacuity property this test was written to hold.
_SPAN = (0, len(DOCS["d01"]))
SUPPORTED = claim("HQ-9/P", "supplies-component", "HT-233", "d01", _SPAN)
FABRICATED = claim("S-400", "based-at", "Sargodha", "d01", _SPAN)


def _rate(res) -> float:
    return float(getattr(res, "rate", getattr(res, "faithfulness", 0.0)))


def _unfaithful(res):
    return list(getattr(res, "unfaithful", getattr(res, "violations", [])) or [])


# ── the gate: fabrication must be visible ─────────────────────────────────────────────────────────

def test_a_claim_its_span_does_not_support_is_counted_unfaithful():
    res = do_faithfulness([SUPPORTED, FABRICATED], DOCS)
    assert _rate(res) < 1.0, why(
        f"FABRICATION-INVISIBLE: faithfulness scored {_rate(res)} for a prediction set in which one claim "
        "('S-400 based-at Sargodha') cites a span that mentions neither S-400 nor Sargodha. The span "
        "exists and slices back cleanly — so a checker that only verifies the offsets are valid sees "
        "nothing wrong. Faithfulness must be established by reading the span, or the extract-only-stated "
        "discipline is unmeasured and the winner may be the most fluent inventor in the field."
    )
    assert _unfaithful(res), why(
        "FABRICATION-UNLOCATED: the rate dropped but the offending claim is not named. A scorecard that "
        "says 'faithfulness 0.5' without pointing at which claim was invented cannot be audited, and the "
        "human in the loop this system is built around has nothing to adjudicate."
    )


def test_a_fully_supported_prediction_set_is_not_penalised():
    """Anti-vacuity: the faithfulness check must not simply fail everything."""
    res = do_faithfulness([SUPPORTED], DOCS)
    assert _rate(res) == 1.0, why(
        f"FAITHFULNESS-OVER-STRICT: a claim whose cited span states it outright scored {_rate(res)}. A "
        "check that penalises honest citation makes the metric noise, and a noisy non-negotiable gets "
        "quietly discounted by whoever reads the scorecard."
    )


def test_an_unsupported_claim_also_costs_precision():
    """Fabrication must cost on the claim scores too — never be a free extra."""
    res = do_match([SUPPORTED], [SUPPORTED, FABRICATED])
    assert res.precision < 1.0, why(
        f"FABRICATION-IS-FREE: precision was {res.precision} for a model that emitted one correct claim "
        "and one invention. If unmatched predictions cost nothing, the optimal strategy under this "
        "harness is to guess more — which is precisely the behaviour that must never be rewarded here."
    )


# ── the gate: fabrication must not be tradeable ───────────────────────────────────────────────────

def test_higher_f1_does_not_buy_off_a_worse_fabrication_rate():
    fabricator = candidate("fabricator", model_id="fab-1.0", runs={
        "claim_f1": [0.900, 0.901, 0.899],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.20, 0.21, 0.19],
    })
    honest = candidate("honest", model_id="honest-1.0", runs={
        "claim_f1": [0.800, 0.801, 0.799],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.0, 0.0, 0.0],
    })
    sc = do_scorecard([fabricator, honest], min_margin=MIN_MARGIN)
    assert sc.winner != "fabricator", why(
        "FABRICATION-TRADED-AWAY: the harness picked the model that invents claims in 20% of cases "
        "because it was 10 F1 points ahead. Plan §8 calls the extract-only-stated discipline "
        "non-negotiable; a non-negotiable that can be outweighed is a price. This winner would re-extract "
        "the graded oracle and write ungrounded claims into the evidence layer wearing valid citations — "
        "the exact failure the project defines as disqualifying."
    )


def test_higher_f1_does_not_buy_off_worse_citation_faithfulness():
    unfaithful = candidate("unfaithful", model_id="unf-1.0", runs={
        "claim_f1": [0.900, 0.901, 0.899],
        "citation_faithfulness": [0.70, 0.71, 0.69],
        "fabrication_rate": [0.0, 0.0, 0.0],
    })
    honest = candidate("honest", model_id="honest-1.0", runs={
        "claim_f1": [0.800, 0.801, 0.799],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.0, 0.0, 0.0],
    })
    sc = do_scorecard([unfaithful, honest], min_margin=MIN_MARGIN)
    assert sc.winner != "unfaithful", why(
        "CITATION-TRADED-AWAY: the model whose citations support its claims only 70% of the time won on "
        "F1. Traceability — every claim one click from its exact source — is what makes this system's "
        "output admissible at all; it is not a score line to be averaged against recall."
    )


def test_fabrication_rate_is_not_maximised_by_mistake():
    """A harness that treats every metric as higher-is-better inverts this one and rewards inventing."""
    low = candidate("low_fabrication", model_id="low-1.0", runs={
        "claim_f1": [0.800, 0.801, 0.799],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.0, 0.0, 0.0],
    })
    high = candidate("high_fabrication", model_id="high-1.0", runs={
        "claim_f1": [0.800, 0.801, 0.799],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.40, 0.41, 0.39],
    })
    sc = do_scorecard([low, high], min_margin=MIN_MARGIN)
    assert sc.winner != "high_fabrication", why(
        "POLARITY-INVERTED: with the two candidates tied on F1 and faithfulness, the harness preferred "
        "the one that fabricates 40% of the time. A scorer that assumes every metric is higher-is-better "
        "does not merely mis-rank — it actively selects for the behaviour the project exists to prevent."
    )


# ── positive controls ─────────────────────────────────────────────────────────────────────────────

def test_positive_control_reference_detects_and_locates_fabrication():
    res = reference_score_faithfulness([SUPPORTED, FABRICATED], DOCS)
    assert res.rate == 0.5 and res.unfaithful == (1,)
    assert reference_score_faithfulness([SUPPORTED], DOCS).rate == 1.0


def test_positive_control_reference_refuses_the_trade():
    fabricator = candidate("fabricator", model_id="fab-1.0", runs={
        "claim_f1": [0.900, 0.901, 0.899],
        "citation_faithfulness": [1.0, 1.0, 1.0],
        "fabrication_rate": [0.20, 0.21, 0.19],
    })
    honest = candidate("honest", model_id="honest-1.0", runs=clean_runs([0.800, 0.801, 0.799]))
    sc = ref_scorecard([fabricator, honest], min_margin=MIN_MARGIN)
    assert sc.winner != "fabricator"
    assert "not tradeable" in sc.text()
