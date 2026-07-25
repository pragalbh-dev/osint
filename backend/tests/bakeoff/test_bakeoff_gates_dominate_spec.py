"""RK-BAKEOFF gate 3 — **gating preconditions are pass/fail to WIN, never weighted in.**

Plan §8, verbatim: "**Gating preconditions (a candidate must satisfy these to WIN — they are not weighted
score lines)**":

* **VLM imagery path preserved (locked).** "A text-only-strong primary that would drop the VLM path is
  **disqualified**, not merely down-weighted (re-litigating a locked demo capability is out of bounds)."
* **KEYLESS≡LIVE restorable.** The primary "must be **installed and successfully live-extract inside the
  shipped image** AND be the producer that **freezes the seed bundles** (so keyless == live *by
  construction*). A capability-winner that can't run live in the image does not restore the invariant."
* **Pinned model id.** "Evaluate and freeze a **concrete pinned** Gemini version, not the floating
  ``-latest`` alias … a floating seed producer breaks KEYLESS≡LIVE and reproducibility."

Why weighting is the failure mode, not an approximation of it. A weight says "this costs you 10% of your
score" — so a model good enough on the scored criteria buys the exemption back and wins anyway. But these
three are not qualities, they are *admissibility*: a winner that cannot read imagery deletes a locked demo
capability; a winner that cannot run live in the shipped image leaves keyless boot diverging from the live
system with no way to reconcile them; a winner pinned to ``-latest`` freezes a seed whose producer can
change under it, which breaks reproducibility for everyone downstream, silently and later. None of that is
recoverable by being 3 F1 points better. The gate must therefore be structurally undefeatable by score —
which is what the "absurd lead" test below actually proves.

**And it must be named.** A candidate silently dropped from contention teaches the next reader nothing;
the failure has to appear in the artifact with the precondition that failed.
"""

from __future__ import annotations

import pytest

from tests.bakeoff._bakeoff_contract_spec import (
    candidate,
    clean_runs,
    do_gates,
    do_scorecard,
    ref_scorecard,
    reference_evaluate_gates,
    why,
)

MIN_MARGIN = 0.03

CLEAN = candidate("clean", model_id="opus-4-8-20260101", runs=clean_runs([0.60, 0.61, 0.605]))

GATE_BREAKERS = {
    "vlm_dropped": (
        dict(vlm_capable=False),
        "VLM-IMAGERY: the locked in-scope VLM imagery path would be dropped",
    ),
    "not_live_in_image": (
        dict(live_in_shipped_image=False),
        "KEYLESS-EQ-LIVE: the model cannot live-extract inside the shipped image",
    ),
    "not_bundle_producer": (
        dict(freezes_seed_bundles=False),
        "KEYLESS-EQ-LIVE: the model is not the producer that freezes the seed bundles",
    ),
    "floating_model_id": (
        dict(model_id="gemini-flash-latest"),
        "PINNED-ID: the model id is a floating alias, not a pinned version",
    ),
}


def _breaker(kind: str, f1: list[float]):
    kwargs, _ = GATE_BREAKERS[kind]
    base = dict(model_id="breaker-1.0", runs=clean_runs(f1))
    base.update(kwargs)
    return candidate(kind, **base)


def _failures(report) -> list[str]:
    return [str(x) for x in (getattr(report, "failures", None) or getattr(report, "reasons", None) or [])]


# ── the gate: each precondition, evaluated ────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", sorted(GATE_BREAKERS))
def test_each_gating_precondition_is_actually_evaluated(kind):
    _, expected = GATE_BREAKERS[kind]
    report = do_gates(_breaker(kind, [0.80, 0.81, 0.805]))
    passed = getattr(report, "passed", None)
    assert passed is False, why(
        f"GATE-NOT-EVALUATED [{kind}]: the harness reported passed={passed!r} for a candidate that "
        f"violates a hard precondition — {expected}. A gate that is declared but never checked is worse "
        "than no gate: it puts a reassuring green tick on the exact failure it was written to catch."
    )
    assert _failures(report), why(
        f"GATE-FAILURE-UNNAMED [{kind}]: the candidate failed but the report names no reason. "
        f"Expected something naming: {expected}. An unnamed disqualification is unauditable — the next "
        "reader cannot tell a hard block from a bug in the harness."
    )


# ── the gate: gates dominate score ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", sorted(GATE_BREAKERS))
def test_gate_failing_candidate_cannot_win(kind):
    _, expected = GATE_BREAKERS[kind]
    sc = do_scorecard([CLEAN, _breaker(kind, [0.80, 0.81, 0.805])], min_margin=MIN_MARGIN)
    assert sc.winner != kind, why(
        f"GATE-BYPASSED [{kind}]: the harness named {sc.winner!r} the winner on score, but that "
        f"candidate fails a hard precondition — {expected}. Plan §8 makes these pass/fail *to win*, not "
        "weighted score lines. Picking it hands the oracle to a model that cannot legally hold it."
    )


@pytest.mark.parametrize("kind", sorted(GATE_BREAKERS))
def test_an_absurd_score_lead_still_cannot_buy_the_gate(kind):
    """The proof that the gate is structural, not a large weight: make the lead unbeatable."""
    _, expected = GATE_BREAKERS[kind]
    sc = do_scorecard([CLEAN, _breaker(kind, [0.998, 0.999, 0.9985])], min_margin=MIN_MARGIN)
    assert sc.winner != kind, why(
        f"GATE-IS-A-WEIGHT [{kind}]: with a near-perfect .999 F1 against a .605 rival, the gate-failing "
        f"candidate won anyway — so the precondition ({expected}) is priced, not enforced. Any weight, "
        "however heavy, is a price a good enough model can pay; admissibility cannot be bought."
    )


@pytest.mark.parametrize("kind", sorted(GATE_BREAKERS))
def test_disqualification_appears_in_the_scorecard_text(kind):
    sc = do_scorecard([CLEAN, _breaker(kind, [0.998, 0.999, 0.9985])], min_margin=MIN_MARGIN)
    text = sc.text()
    assert any(k in text for k in ("disqualif", "gating", "precondition", "cannot win", "ineligible")), why(
        f"SILENT-DISQUALIFICATION [{kind}]: the top-scoring candidate was excluded but the scorecard "
        "never says a gating precondition blocked it. A reader comparing the numbers would conclude the "
        f"harness is broken, or quietly override it. Verdict text was: {text[:400]!r}"
    )


def test_the_shipped_floating_gemini_alias_is_rejected_as_a_seed_producer():
    """The pinned-id gate must bite on the alias that is actually in the tree today."""
    from chanakya.ingest.client import DEFAULT_GEMINI_MODEL

    report = do_gates(candidate("gemini", model_id=DEFAULT_GEMINI_MODEL,
                                runs=clean_runs([0.90, 0.91, 0.905])))
    assert getattr(report, "passed", None) is False, why(
        f"PINNED-ID-GATE-INERT: {DEFAULT_GEMINI_MODEL!r} — the alias currently wired as the extraction "
        "default — passed the gating check. That alias is a live-resilience fallback; freezing seed "
        "bundles with it means the producer of the frozen seed can change under us, which breaks "
        "KEYLESS≡LIVE and reproducibility later and silently. The gate has to catch the real string, "
        "not a synthetic '-latest' in a fixture."
    )


def test_all_candidates_blocked_yields_no_winner():
    """Gates dominating means the honest outcome can be 'nobody is admissible'."""
    cands = [_breaker("vlm_dropped", [0.90, 0.91, 0.905]),
             _breaker("floating_model_id", [0.92, 0.93, 0.925])]
    sc = do_scorecard(cands, min_margin=MIN_MARGIN)
    assert sc.winner is None, why(
        f"GATE-FALLBACK-TO-BEST: every candidate failed a hard precondition, yet the harness still named "
        f"{sc.winner!r}. 'The least inadmissible' is not a winner; the honest output is no winner plus "
        "the named blocks."
    )


# ── positive controls ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", sorted(GATE_BREAKERS))
def test_positive_control_reference_blocks_each_precondition(kind):
    report = reference_evaluate_gates(_breaker(kind, [0.80, 0.81, 0.805]))
    assert report.passed is False and report.failures
    sc = ref_scorecard([CLEAN, _breaker(kind, [0.998, 0.999, 0.9985])], min_margin=MIN_MARGIN)
    assert sc.winner != kind
    assert "disqualif" in sc.text() or "gating" in sc.text()


def test_positive_control_reference_admits_a_clean_candidate():
    report = reference_evaluate_gates(CLEAN)
    assert report.passed is True and report.failures == ()
