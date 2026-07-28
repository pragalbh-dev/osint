"""RULING 3 — preflight and the real run judge the imagery gate on the same evidence, through one function.

The defect: ``preflight`` read the recorded ``vlm-probe`` evidence, and the real run's ``evaluate_gates``
took no evidence at all — it judged the imagery gate purely on the standalone-image calls that run happened
to make. So preflight could print PASS for all three candidates and the run could then return
``NO_ELIGIBLE_CANDIDATE``. A green light followed by a silent disqualification is the exact trap this project
keeps getting bitten by.

The fix is structural rather than a second read: :func:`eval.extraction.vlm_probe.observations_for` is the
only way to build the gate's input, :func:`eval.extraction.gates.gate_vlm_imagery` is the only thing that
turns it into a status, and both entry points resolve their evidence through
:func:`eval.extraction.vlm_probe.resolve_evidence`. The run is then simply preflight *plus* whatever image
calls it made itself — so it can only ever know more.

Offline throughout: every test supplies its own evidence mapping rather than reading the operator's recorded
artefact, because a test whose verdict depends on whether somebody ran the probe this afternoon is not a test.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters
from chanakya.ingest.lane import DocInput
from eval.extraction import vlm_probe
from eval.extraction.gates import ImageryObservations, gate_vlm_imagery
from eval.extraction.runner import BakeoffInputs, preflight, run_bakeoff
from eval.extraction.vlm_probe import ImageryEvidence, observations_for, resolve_evidence

from .fixtures import (
    RoutedScriptedClient,
    bakeoff_config,
    write_adapted_gold,
    write_sub_oracle,
)

DOC_TEXT = "North Ridge Foundry supplies the Type-7 Coupler to the Eastvale Pumping Station.\n"

PAYLOAD: dict[str, Any] = {
    "manufacturers": [{"name": "North Ridge Foundry",
                       "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture
def pipeline_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _inputs(tmp_path, pipeline_config, *, with_image: bool) -> BakeoffInputs:
    gold = write_adapted_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
         "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 47]}},
    ])
    oracle = write_sub_oracle(tmp_path / "oracle.json",
                              [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"}], [])
    docs = [DocInput(raw=DOC_TEXT, source_id="doc1", source_type="curated-register", file="doc1.txt",
                     format_hint="prose_claim")]
    if with_image:
        docs.append(DocInput(raw=b"\x89PNG\r\n\x1a\nnot-a-real-frame", source_id="frame1",
                             source_type="geoint-imagery", file="frame1.png"))
    return BakeoffInputs(docs=docs, config=pipeline_config, gold_path=gold, sub_oracle_path=oracle,
                         out_dir=tmp_path / "bundles", concurrency=2)


def _factory(candidate, run_index):
    return RoutedScriptedClient(PAYLOAD, {}, model_id=candidate.model_id)


def _evidence(config, **overrides: Any) -> dict[str, ImageryEvidence]:
    """A PASS record for every declared candidate, pinned to its declared model id."""
    records = {
        c.id: ImageryEvidence(candidate_id=c.id, model_id=c.model_id, image="frame.png",
                              calls_ok=1, calls_total=1, recorded_at="2026-07-25T00:00:00+00:00")
        for c in config.candidates
    }
    records.update(overrides)
    return records


def _imagery_status(report) -> str:
    return next(g.status for g in report.gates if g.name == "vlm_imagery_path")


# ── the asymmetry itself ──────────────────────────────────────────────────────────────────────────

def test_a_green_preflight_is_not_followed_by_a_silent_disqualification(tmp_path, pipeline_config) -> None:
    """The regression, stated as the operator experiences it: preflight says ELIGIBLE on recorded evidence,
    then a run whose slice contains no image at all must NOT come back NO_ELIGIBLE_CANDIDATE."""
    config = bakeoff_config()
    evidence = _evidence(config)

    reports = preflight(config, require_key=False, evidence=evidence)
    assert all(_imagery_status(r) == "PASS" for r in reports)
    assert all(r.eligible for r in reports)

    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=False), config, _factory,
                         require_key=False, evidence=evidence)
    assert all(s.runs[0].image_calls_total == 0 for s in result.scores), "premise: the run made no image call"
    assert all(_imagery_status(s.gates) == "PASS" for s in result.scores)
    assert result.verdict.kind != "NO_ELIGIBLE_CANDIDATE"


def test_without_the_evidence_both_paths_block_together(tmp_path, pipeline_config) -> None:
    """The symmetry has to hold in the blocking direction too, or the fix is just optimism."""
    config = bakeoff_config()
    reports = preflight(config, require_key=False, evidence={})
    assert all(_imagery_status(r) == "UNKNOWN" for r in reports)

    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=False), config, _factory,
                         require_key=False, evidence={})
    assert all(_imagery_status(s.gates) == "UNKNOWN" for s in result.scores)
    assert result.verdict.kind == "NO_ELIGIBLE_CANDIDATE"


@pytest.mark.parametrize("evidence_kind", ["pass", "none", "stale-pin", "failed"])
def test_the_run_reaches_the_same_imagery_status_as_preflight_on_the_same_evidence(
        tmp_path, pipeline_config, evidence_kind: str) -> None:
    """The property, not one example: with no image call of its own, the run's imagery gate IS preflight's."""
    config = bakeoff_config()
    if evidence_kind == "pass":
        evidence = _evidence(config)
    elif evidence_kind == "none":
        evidence = {}
    elif evidence_kind == "stale-pin":
        evidence = {c.id: ImageryEvidence(candidate_id=c.id, model_id="a-pin-it-no-longer-names",
                                          image="frame.png", calls_ok=1, calls_total=1,
                                          recorded_at="2026-07-25T00:00:00+00:00")
                    for c in config.candidates}
    else:
        evidence = {c.id: ImageryEvidence(candidate_id=c.id, model_id=c.model_id, image="frame.png",
                                          calls_ok=0, calls_total=1,
                                          recorded_at="2026-07-25T00:00:00+00:00",
                                          error="BadRequestError: no image support")
                    for c in config.candidates}

    dry = {r.candidate_id: _imagery_status(r)
           for r in preflight(config, require_key=False, evidence=evidence)}
    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=False), config, _factory,
                         require_key=False, evidence=evidence)
    live = {s.candidate_id: _imagery_status(s.gates) for s in result.scores}
    assert live == dry


# ── staleness is preserved, and a run's own call is not inheritance ────────────────────────────────

def test_a_stale_record_contributes_nothing_and_the_gate_drops_back_to_unknown() -> None:
    """Re-pin a model or bump the probe version and the evidence goes stale to UNKNOWN, never inherited."""
    config = bakeoff_config()
    candidate = config.candidates[0]
    fresh, record = observations_for(candidate, evidence=_evidence(config))
    assert (fresh.calls_ok, fresh.calls_total) == (1, 1) and record is not None

    repinned = candidate.model_copy(update={"model_id": "a-newly-pinned-version"})
    stale, record = observations_for(repinned, evidence=_evidence(config))
    assert (stale.calls_ok, stale.calls_total) == (0, 0) and record is None
    assert gate_vlm_imagery(repinned, stale).status == "UNKNOWN"

    bumped = {candidate.id: ImageryEvidence(
        candidate_id=candidate.id, model_id=candidate.model_id, image="frame.png", calls_ok=1,
        calls_total=1, recorded_at="2026-07-25T00:00:00+00:00",
        probe_version=vlm_probe.PROBE_VERSION - 1)}
    old_probe, _ = observations_for(candidate, evidence=bumped)
    assert gate_vlm_imagery(candidate, old_probe).status == "UNKNOWN"


def test_a_runs_own_image_call_stands_in_for_a_stale_record(tmp_path, pipeline_config) -> None:
    """Not inheritance: a call made *in this run* is first-hand evidence for the model actually being run.
    Stale evidence contributes nothing, and the run's own successful call is what carries the gate."""
    config = bakeoff_config()
    stale = {c.id: ImageryEvidence(candidate_id=c.id, model_id="an-old-pin", image="frame.png",
                                   calls_ok=1, calls_total=1, recorded_at="2026-07-25T00:00:00+00:00")
             for c in config.candidates}
    assert all(_imagery_status(r) == "UNKNOWN"
               for r in preflight(config, require_key=False, evidence=stale))

    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=True), config, _factory,
                         require_key=False, evidence=stale)
    for score in result.scores:
        assert score.runs[0].image_calls_total >= 1
        gate = next(g for g in score.gates.gates if g.name == "vlm_imagery_path")
        assert gate.status == "PASS" and "this run" in gate.detail


def test_a_failure_anywhere_fails_the_gate_rather_than_being_averaged_out(tmp_path,
                                                                         pipeline_config) -> None:
    """Observations are summed, not chosen between: a failed probe plus a successful run is one of each, and
    a gate that took the better of the two would let a real provider failure disappear."""
    config = bakeoff_config()
    failed = {c.id: ImageryEvidence(candidate_id=c.id, model_id=c.model_id, image="frame.png",
                                    calls_ok=0, calls_total=1, recorded_at="2026-07-25T00:00:00+00:00",
                                    error="BadRequestError: no image support")
              for c in config.candidates}
    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=True), config, _factory,
                         require_key=False, evidence=failed)
    for score in result.scores:
        gate = next(g for g in score.gates.gates if g.name == "vlm_imagery_path")
        assert gate.status == "FAIL"
    assert result.verdict.kind == "NO_ELIGIBLE_CANDIDATE"


# ── one resolution rule, shared ───────────────────────────────────────────────────────────────────

def test_the_evidence_resolution_rule_is_one_function_and_distinguishes_none_from_empty(tmp_path) -> None:
    """``None`` means "read the recorded artefact"; an explicit ``{}`` means "nothing is verified". If one
    entry point defaulted to the file and the other to "nothing", the two would disagree by construction."""
    path = tmp_path / "evidence.json"
    record = ImageryEvidence(candidate_id="cand", model_id="pinned-1", image="frame.png", calls_ok=1,
                             calls_total=1, recorded_at="2026-07-25T00:00:00+00:00")
    vlm_probe.save_evidence({"cand": record}, path)

    assert resolve_evidence(None, path) == {"cand": record}
    assert resolve_evidence({}, path) == {}
    assert resolve_evidence(None, tmp_path / "absent.json") == {}


def test_an_unexercisable_candidate_still_gets_the_recorded_imagery_verdict(tmp_path,
                                                                           pipeline_config) -> None:
    """The early-return path for "no client could be built" is a separate call into the gates, and it used to
    hardcode 0/0 image calls — a second place the evidence was dropped."""
    config = bakeoff_config()
    evidence = _evidence(config)

    def factory(candidate, run_index):
        return None if candidate.id == "beta" else RoutedScriptedClient(PAYLOAD, {})

    result = run_bakeoff(_inputs(tmp_path, pipeline_config, with_image=False), config, factory,
                         require_key=False, evidence=evidence)
    beta = next(s for s in result.scores if s.candidate_id == "beta")
    assert beta.exercised is False
    assert _imagery_status(beta.gates) == "PASS", (
        "the recorded evidence was dropped on the unexercisable path, so this candidate's imagery gate "
        "disagrees with the one preflight printed for it"
    )


def test_observations_are_the_only_way_into_the_gate() -> None:
    """A structural check: the gate takes one object, so a caller cannot supply half the observations. This
    is what makes the two entry points agree by construction rather than by both remembering to."""
    import inspect as _inspect

    params = list(_inspect.signature(gate_vlm_imagery).parameters)
    assert params == ["candidate", "imagery"]
    hints = _inspect.get_annotations(gate_vlm_imagery, eval_str=True)
    assert hints["imagery"] is ImageryObservations
