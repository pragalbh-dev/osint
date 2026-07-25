"""The gating preconditions — pass/fail to win, and UNKNOWN blocking just as hard as FAIL."""

from __future__ import annotations

from eval.extraction.gates import (
    evaluate_gates,
    gate_key_present,
    gate_keyless_equals_live,
    gate_non_negotiable_floor,
    gate_pinned_model_id,
    gate_vlm_imagery,
)
from eval.extraction.metrics import MetricValue

from .fixtures import bakeoff_config


def _candidate(**overrides):
    cfg = bakeoff_config()
    return cfg.candidates[0].model_copy(update=overrides), cfg


# ── VLM imagery: the locked path ──────────────────────────────────────────────────────────────────

def test_a_text_only_candidate_is_disqualified_not_downweighted() -> None:
    cand, _ = _candidate(multimodal="none")
    gate = gate_vlm_imagery(cand, image_calls_ok=0, image_calls_total=0)
    assert gate.status == "FAIL" and "disqualifier" in gate.detail
    assert gate.blocks_winning


def test_an_unexercised_vlm_path_is_unknown_and_still_blocks() -> None:
    """A gate nobody ran is not a gate anybody passed."""
    cand, _ = _candidate()
    gate = gate_vlm_imagery(cand, image_calls_ok=0, image_calls_total=0)
    assert gate.status == "UNKNOWN" and gate.blocks_winning


def test_a_demonstrated_vlm_path_passes() -> None:
    cand, _ = _candidate()
    assert gate_vlm_imagery(cand, image_calls_ok=2, image_calls_total=2).status == "PASS"


def test_a_failing_image_call_fails_the_gate() -> None:
    cand, _ = _candidate()
    assert gate_vlm_imagery(cand, image_calls_ok=1, image_calls_total=2).status == "FAIL"


# ── KEYLESS == LIVE ───────────────────────────────────────────────────────────────────────────────

def test_a_client_outside_the_shipped_ingest_path_cannot_freeze_the_seed() -> None:
    cand, cfg = _candidate(client_module="eval.extraction.gpt_client")
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


# ── optional non-negotiable floors ────────────────────────────────────────────────────────────────

def test_no_floor_configured_means_no_gate_at_all() -> None:
    metric = MetricValue.measured("citation_faithfulness", 0.1)
    assert gate_non_negotiable_floor(metric, None) is None


def test_a_configured_floor_gates_the_non_negotiable_metric() -> None:
    low = MetricValue.measured("citation_faithfulness", 0.42)
    assert gate_non_negotiable_floor(low, 0.90).status == "FAIL"
    high = MetricValue.measured("citation_faithfulness", 0.95)
    assert gate_non_negotiable_floor(high, 0.90).status == "PASS"


def test_an_unmeasured_metric_under_a_floor_is_unknown() -> None:
    missing = MetricValue.unavailable("citation_faithfulness", "no char-addressable citation")
    assert gate_non_negotiable_floor(missing, 0.90).status == "UNKNOWN"


# ── the whole report ──────────────────────────────────────────────────────────────────────────────

def test_eligibility_requires_every_gate_to_pass(monkeypatch) -> None:
    cand, cfg = _candidate()
    monkeypatch.setenv(cand.key_env, "x")
    blocked = evaluate_gates(cand, cfg, image_calls_ok=0, image_calls_total=0)
    assert not blocked.eligible and [g.name for g in blocked.blocking] == ["vlm_imagery_path"]
    clean = evaluate_gates(cand, cfg, image_calls_ok=1, image_calls_total=1)
    assert clean.eligible
