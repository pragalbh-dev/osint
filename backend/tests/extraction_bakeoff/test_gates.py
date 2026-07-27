"""The gating preconditions — pass/fail to win, and UNKNOWN blocking just as hard as FAIL."""

from __future__ import annotations

from eval.extraction.gates import (
    ImageryObservations,
    dry_gates,
    evaluate_gates,
    gate_key_present,
    gate_keyless_equals_live,
    gate_non_negotiable,
    gate_pinned_model_id,
    gate_vlm_imagery,
    non_negotiable_gate_names,
)
from eval.extraction.metrics import MetricValue

from .fixtures import bakeoff_config


def _candidate(**overrides):
    cfg = bakeoff_config()
    return cfg.candidates[0].model_copy(update=overrides), cfg


# ── VLM imagery: the locked path ──────────────────────────────────────────────────────────────────

def test_a_text_only_candidate_is_disqualified_not_downweighted() -> None:
    cand, _ = _candidate(multimodal="none")
    gate = gate_vlm_imagery(cand, ImageryObservations())
    assert gate.status == "FAIL" and "disqualifier" in gate.detail
    assert gate.blocks_winning


def test_an_unexercised_vlm_path_is_unknown_and_still_blocks() -> None:
    """A gate nobody ran is not a gate anybody passed."""
    cand, _ = _candidate()
    gate = gate_vlm_imagery(cand, ImageryObservations())
    assert gate.status == "UNKNOWN" and gate.blocks_winning


def test_a_demonstrated_vlm_path_passes() -> None:
    cand, _ = _candidate()
    assert gate_vlm_imagery(cand, ImageryObservations(2, 2, ("this run 2/2",))).status == "PASS"


def test_a_failing_image_call_fails_the_gate() -> None:
    cand, _ = _candidate()
    assert gate_vlm_imagery(cand, ImageryObservations(1, 2, ("this run 1/2",))).status == "FAIL"


# ── KEYLESS == LIVE ───────────────────────────────────────────────────────────────────────────────

def test_a_client_outside_the_shipped_ingest_path_cannot_freeze_the_seed() -> None:
    # Any module outside `chanakya.ingest` does it; the gate is a placement check, not an import.
    # (This was `eval.extraction.gpt_client` until that client was promoted onto the shipped path.)
    cand, cfg = _candidate(client_module="eval.extraction.some_candidate_client")
    gate = gate_keyless_equals_live(cand, cfg)
    assert gate.status == "FAIL" and "freezes the seed bundles" in gate.detail


def test_a_missing_sdk_fails_the_live_gate() -> None:
    cand, cfg = _candidate(sdk_module="a_module_that_does_not_exist_anywhere")
    gate = gate_keyless_equals_live(cand, cfg)
    assert gate.status == "FAIL" and "does not import" in gate.detail


def test_a_candidate_that_would_not_freeze_the_seed_fails() -> None:
    cand, cfg = _candidate(freezes_seed=False)
    assert gate_keyless_equals_live(cand, cfg).status == "FAIL"


def test_a_shipped_seed_producing_client_passes() -> None:
    cand, cfg = _candidate()
    assert gate_keyless_equals_live(cand, cfg).status == "PASS"


# ── pinned model id ───────────────────────────────────────────────────────────────────────────────

def test_a_floating_alias_fails_the_pinned_gate() -> None:
    cand, cfg = _candidate(model_id="gemini-flash-latest")
    gate = gate_pinned_model_id(cand, cfg)
    assert gate.status == "FAIL" and "floating-alias" in gate.detail


def test_a_config_placeholder_is_unknown_not_pass() -> None:
    cand, cfg = _candidate(model_id="REPLACE-WITH-PINNED-GPT-VERSION")
    assert gate_pinned_model_id(cand, cfg).status == "UNKNOWN"


def test_a_concrete_version_passes() -> None:
    cand, cfg = _candidate(model_id="gemini-2.9-flash-20260401")
    assert gate_pinned_model_id(cand, cfg).status == "PASS"


# ── exercisability ────────────────────────────────────────────────────────────────────────────────

def test_a_missing_key_is_recorded_as_a_gate_not_a_silent_omission(monkeypatch) -> None:
    cand, _ = _candidate()
    monkeypatch.delenv(cand.key_env, raising=False)
    gate = gate_key_present(cand)
    assert gate.status == "FAIL" and "three-way measurement" in gate.detail
    monkeypatch.setenv(cand.key_env, "x")
    assert gate_key_present(cand).status == "PASS"


# ── the non-negotiable metrics ─────────────────────────────────────────────────────────────────────

def test_a_declared_non_negotiable_with_no_floor_still_has_to_be_measured() -> None:
    """The loophole this closes: with no absolute floor there used to be no gate at all, so a candidate
    whose fabrication line simply failed to measure sailed through on the lines that did. The *relative*
    veto cannot help — it has nothing to compare — so "we did not check whether it fabricates" would have
    been a pass."""
    measured = gate_non_negotiable("trap_avoidance", MetricValue.measured("trap_avoidance", 0.1), None)
    assert measured.status == "PASS" and "relative veto" in measured.detail

    unmeasured = gate_non_negotiable(
        "trap_avoidance", MetricValue.unavailable("trap_avoidance", "no traps declared"), None)
    assert unmeasured.status == "UNKNOWN" and unmeasured.blocks_winning

    never_scored = gate_non_negotiable("trap_avoidance", None, None)
    assert never_scored.status == "UNKNOWN" and never_scored.blocks_winning
    assert "traded away by absence" in never_scored.detail


def test_a_configured_floor_gates_the_non_negotiable_metric() -> None:
    low = MetricValue.measured("citation_faithfulness", 0.42)
    assert gate_non_negotiable("citation_faithfulness", low, 0.90).status == "FAIL"
    high = MetricValue.measured("citation_faithfulness", 0.95)
    assert gate_non_negotiable("citation_faithfulness", high, 0.90).status == "PASS"


def test_an_unmeasured_metric_under_a_floor_is_unknown() -> None:
    missing = MetricValue.unavailable("citation_faithfulness", "no char-addressable citation")
    assert gate_non_negotiable("citation_faithfulness", missing, 0.90).status == "UNKNOWN"


# ── the whole report ──────────────────────────────────────────────────────────────────────────────

def test_eligibility_requires_every_gate_to_pass(monkeypatch) -> None:
    cand, cfg = _candidate()
    monkeypatch.setenv(cand.key_env, "x")
    blocked = evaluate_gates(cand, cfg, imagery=ImageryObservations())
    assert not blocked.eligible and [g.name for g in blocked.blocking] == ["vlm_imagery_path"]
    clean = evaluate_gates(cand, cfg, imagery=ImageryObservations(1, 1, ("this run 1/1",)))
    assert clean.eligible


def test_the_non_negotiable_gates_are_the_ones_preflight_defers_and_it_can_name_them() -> None:
    """Preflight cannot judge a metric nobody has measured yet. The honest answer is to leave those gates
    out and *say which*, rather than inventing a verdict or dropping a blocking precondition in silence."""
    cand, cfg = _candidate()
    cfg = cfg.model_copy(update={"gates": cfg.gates.model_copy(
        update={"non_negotiable_floors": {"trap_avoidance": None}})})

    assert non_negotiable_gate_names(cfg) == ("non-negotiable:trap_avoidance",)
    dry = dry_gates(cand, cfg, imagery=ImageryObservations(1, 1, ("probe",)), require_key=False)
    assert "non-negotiable:trap_avoidance" not in {g.name for g in dry.gates}

    after_run = evaluate_gates(cand, cfg, imagery=ImageryObservations(1, 1, ("probe",)),
                               require_key=False)
    # The run knows MORE than preflight, which is the safe direction: the extra gate can only block.
    assert {g.name for g in dry.gates} < {g.name for g in after_run.gates}
    assert not after_run.eligible                      # unmeasured non-negotiable ⇒ UNKNOWN ⇒ blocks


def test_an_impossible_observation_count_is_rejected_rather_than_averaged_away() -> None:
    """More successful image calls than calls would let a real failure be washed out by arithmetic."""
    import pytest

    with pytest.raises(ValueError, match="not a possible observation"):
        ImageryObservations(calls_ok=2, calls_total=1)
