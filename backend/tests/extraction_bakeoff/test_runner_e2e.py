"""The orchestration end to end — N runs, a bundle per run, a rebuild per run, one comparative verdict.

Entirely offline: the client is injected, so no candidate is ever built, no key is read and no API call
is made. The documents and the labeled inputs are invented (a fictional infrastructure domain); the
pipeline underneath them is the real ``chanakya`` extraction and ``rebuild()``, because a bake-off
measured on a scorer-local imitation of the pipeline would measure the imitation.
"""

from __future__ import annotations

import json

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters
from chanakya.ingest.lane import DocInput
from eval.extraction.runner import BakeoffInputs, preflight, run_bakeoff

from .fixtures import (
    RoutedScriptedClient,
    bakeoff_config,
    negative_row,
    write_adapted_gold,
    write_claim_gold,
    write_sub_oracle,
)

DOC_TEXT = (
    "North Ridge Foundry supplies the Type-7 Coupler to the Eastvale Pumping Station.\n"
    "The station is operated by the Regional Water Board.\n"
)

FULL_PAYLOAD = {
    "manufacturers": [{"name": "North Ridge Foundry",
                       "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
    "components": [{"name": "Type-7 Coupler", "component_class": "coupler",
                    "source_quote": "the Type-7 Coupler"}],
    "relations": [{"relation": "supplies-component", "subject": "North Ridge Foundry",
                   "object": "Type-7 Coupler",
                   "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
}

#: A weaker extraction: it misses the relationship and invents a component the document never names.
WEAK_PAYLOAD = {
    "manufacturers": [{"name": "North Ridge Foundry",
                       "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
    "components": [{"name": "Harbourline Turbine Set",
                    "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No adapter may reach the network — the bake-off must be runnable on a keyless machine."""
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture
def pipeline_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


@pytest.fixture
def inputs(tmp_path, pipeline_config) -> BakeoffInputs:
    gold = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
         "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 47]},
         "kind": "observation"},
        {"gold_id": "g2", "source_id": "doc1", "form": "entity", "entity_type": "component",
         "name": "Type-7 Coupler", "doc_ref": {"file": "doc1.txt", "span": [29, 47]},
         "kind": "observation"},
        {"gold_id": "g3", "source_id": "doc1", "form": "triple", "subject": "North Ridge Foundry",
         "predicate": "supplies-component", "object": "Type-7 Coupler",
         "doc_ref": {"file": "doc1.txt", "span": [0, 47]}, "kind": "observation"},
    ])
    oracle = write_sub_oracle(
        tmp_path / "oracle.json",
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"},
         {"id": "n2", "type": "component", "name": "Type-7 Coupler"}],
        [{"type": "supplies-component", "source": "n1", "target": "n2"}],
    )
    docs = [
        DocInput(raw=DOC_TEXT, source_id="doc1", source_type="curated-register", file="doc1.txt",
                 format_hint="prose_claim"),
        DocInput(raw=b"\x89PNG\r\n\x1a\nnot-a-real-frame", source_id="frame1",
                 source_type="geoint-imagery", file="frame1.png"),
    ]
    return BakeoffInputs(docs=docs, config=pipeline_config, gold_path=gold, sub_oracle_path=oracle,
                         out_dir=tmp_path / "bundles", concurrency=2)


def _factory(payload_by_candidate: dict[str, dict]):
    def factory(candidate, run_index):
        return RoutedScriptedClient(payload_by_candidate[candidate.id], {},
                                    model_id=candidate.model_id)
    return factory


# ── the happy path: a real separation ─────────────────────────────────────────────────────────────

def test_a_full_bakeoff_runs_offline_and_separates_a_clearly_better_extractor(inputs) -> None:
    config = bakeoff_config()
    result = run_bakeoff(
        inputs, config,
        _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
        require_key=False,
    )
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    beta = next(s for s in result.scores if s.candidate_id == "beta")

    assert alpha.eligible_to_win and beta.eligible_to_win
    # Recall is perfect: the strong extractor found every gold claim. Precision is not, and correctly so
    # — the imagery lane also emits a site observation the gold slice does not label, and the matcher
    # counts an unlabeled claim as unmatched rather than quietly forgiving it.
    assert alpha.series["surface_recall"].mean == pytest.approx(1.0)
    assert beta.series["surface_f1"].mean is not None
    assert alpha.series["surface_f1"].mean is not None
    assert beta.series["surface_f1"].mean < alpha.series["surface_f1"].mean
    assert result.verdict.kind == "WINNER" and result.verdict.winner == "alpha"


def test_the_vlm_gate_passes_only_because_an_image_call_was_actually_exercised(inputs) -> None:
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    vlm = next(g for g in alpha.gates.gates if g.name == "vlm_imagery_path")
    assert vlm.status == "PASS" and "standalone-image calls returned" in vlm.detail
    assert alpha.runs[0].image_calls_total >= 1


def test_every_run_leaves_a_traceable_bundle(inputs) -> None:
    config = bakeoff_config()
    run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                require_key=False)
    for candidate in ("alpha", "beta"):
        for run in range(1, config.replication.runs_per_candidate + 1):
            bundle = inputs.out_dir / candidate / f"run-{run:02d}" / "doc1.json"
            assert bundle.exists(), f"missing bundle for {candidate} run {run}"
            rows = json.loads(bundle.read_text())
            assert isinstance(rows, list)
            assert all("claim_id" in r and "doc_ref" in r for r in rows)


def test_the_fabricated_component_shows_up_on_the_extract_only_stated_line(inputs) -> None:
    """The weak extractor names a component the document never mentions — that is the fabrication line."""
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    beta = next(s for s in result.scores if s.candidate_id == "beta")
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    assert beta.series["extract_only_stated"].mean is not None
    assert alpha.series["extract_only_stated"].mean is not None
    assert beta.series["extract_only_stated"].mean < alpha.series["extract_only_stated"].mean


def test_graph_recall_is_measured_against_the_supplied_sub_oracle(inputs) -> None:
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    assert alpha.series["graph_node_recall"].mean == pytest.approx(1.0)
    assert alpha.series["graph_edge_recall"].mean == pytest.approx(1.0)


def test_coref_binding_on_a_dormant_channel_is_unmeasured_never_a_zero(inputs) -> None:
    """Top-weighted. With extraction pass 2 dormant nothing binds, and that must read as NOT MEASURED for
    everyone — a zero would be a score neither candidate earned, and a tie neither of them made."""
    from eval.extraction.metrics import NO_CLUSTERING

    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    for score in result.scores:
        series = score.series["coref_binding"]
        assert series.status == "unavailable" and series.values == ()
        assert any("coref_cluster labels" in r or r == NO_CLUSTERING for r in series.reasons)


# ── the negative gold, end to end through the real pipeline ───────────────────────────────────────

@pytest.fixture
def inputs_with_traps(tmp_path, pipeline_config) -> BakeoffInputs:
    """The same slice, but the gold declares the opening sentence's span a ``not_a_claim`` TRAP.

    The weak extractor invents a component and cites that sentence for it; the strong one emits only claims
    that pair with positive gold. A matched claim is exempt, so this separates the two on the fabrication line
    using the real extraction path rather than a hand-built claim set.
    """
    gold = write_adapted_gold(
        tmp_path / "gold_traps.json",
        [{"gold_id": "g1", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
          "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 47]}},
         {"gold_id": "g2", "source_id": "doc1", "form": "entity", "entity_type": "component",
          "name": "Type-7 Coupler", "doc_ref": {"file": "doc1.txt", "span": [29, 47]}},
         {"gold_id": "g3", "source_id": "doc1", "form": "triple", "subject": "North Ridge Foundry",
          "predicate": "supplies-component", "object": "Type-7 Coupler",
          "doc_ref": {"file": "doc1.txt", "span": [0, 47]}}],
        {"not_a_claim": [negative_row("t1", (0, 47))]},
    )
    oracle = write_sub_oracle(
        tmp_path / "oracle_traps.json",
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"}], [])
    docs = [DocInput(raw=DOC_TEXT, source_id="doc1", source_type="curated-register", file="doc1.txt",
                     format_hint="prose_claim")]
    return BakeoffInputs(docs=docs, config=pipeline_config, gold_path=gold, sub_oracle_path=oracle,
                         out_dir=tmp_path / "bundles_traps", concurrency=2)


def test_the_fabrication_line_is_measured_end_to_end_and_separates_the_two(inputs_with_traps) -> None:
    config = bakeoff_config()
    result = run_bakeoff(inputs_with_traps, config,
                         _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False, evidence={})
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    beta = next(s for s in result.scores if s.candidate_id == "beta")

    assert alpha.series["trap_avoidance"].mean == pytest.approx(1.0)
    assert beta.series["trap_avoidance"].mean == pytest.approx(0.0)
    hit = beta.runs[0].metrics["trap_avoidance"].detail["hits_by_trap"]
    assert "t1" in hit


def test_the_fabrication_line_never_enters_the_weighted_composite(inputs_with_traps) -> None:
    """It is a veto. A measured trap line that quietly joined the composite would be tradeable again."""
    config = bakeoff_config()
    result = run_bakeoff(inputs_with_traps, config,
                         _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False, evidence={})
    assert config.weight_for("trap_avoidance") == 0.0
    assert "trap_avoidance" not in result.verdict.composite_weights


def test_a_slice_with_no_typed_negatives_reports_the_trap_line_unmeasured(inputs) -> None:
    """The default fixture gold carries no ``negative_gold`` block, and that must read as NOT MEASURED for
    everyone — never a flattering 1.0 that would look like three clean candidates."""
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False, evidence={})
    for score in result.scores:
        series = score.series["trap_avoidance"]
        assert series.status == "unavailable" and series.values == ()


# ── the anti-fabrication path: identical candidates must not be ranked ─────────────────────────────

def test_two_identical_extractors_produce_no_measured_difference(inputs) -> None:
    """The single most important end-to-end assertion in the harness."""
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": FULL_PAYLOAD}),
                         require_key=False)
    assert result.verdict.kind == "NO_MEASURED_DIFFERENCE"
    assert result.verdict.winner is None
    assert set(result.verdict.tied) == {"alpha", "beta"}


def test_an_unexercisable_candidate_is_recorded_not_dropped(inputs) -> None:
    config = bakeoff_config()

    def factory(candidate, run_index):
        return None if candidate.id == "beta" else RoutedScriptedClient(FULL_PAYLOAD, {})

    result = run_bakeoff(inputs, config, factory, require_key=False)
    beta = next(s for s in result.scores if s.candidate_id == "beta")
    assert beta.exercised is False and "NOT measured" in beta.not_exercised_reason
    assert result.verdict.kind == "SOLE_ELIGIBLE_CANDIDATE"
    assert result.verdict.winner is None
    assert "not a" in result.verdict.statement or "default" in result.verdict.statement


def test_under_replication_is_refused_end_to_end(inputs) -> None:
    config = bakeoff_config(replication={"runs_per_candidate": 2, "min_runs_for_ranking": 3})
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    assert result.verdict.kind == "INSUFFICIENT_REPLICATION" and result.verdict.winner is None


def test_determinism_is_scored_and_a_steady_extractor_scores_one(inputs) -> None:
    config = bakeoff_config()
    result = run_bakeoff(inputs, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                         require_key=False)
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    assert alpha.series["determinism"].mean == pytest.approx(1.0)


def test_a_wobbling_extractor_scores_below_one_on_determinism(inputs) -> None:
    """A candidate whose output changes run to run is measured as less stable — the reason N>1 exists."""
    config = bakeoff_config()
    payloads = [FULL_PAYLOAD, WEAK_PAYLOAD, FULL_PAYLOAD]

    def factory(candidate, run_index):
        if candidate.id == "alpha":
            return RoutedScriptedClient(payloads[(run_index - 1) % len(payloads)], {})
        return RoutedScriptedClient(FULL_PAYLOAD, {})

    result = run_bakeoff(inputs, config, factory, require_key=False)
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    beta = next(s for s in result.scores if s.candidate_id == "beta")
    assert alpha.series["determinism"].mean is not None
    assert alpha.series["determinism"].mean < 1.0
    assert beta.series["determinism"].mean == pytest.approx(1.0)


def test_a_wobbling_candidates_variance_widens_the_required_margin(inputs) -> None:
    """Variance is not decoration: an unstable candidate is harder to separate, by construction."""
    config = bakeoff_config()
    payloads = [FULL_PAYLOAD, WEAK_PAYLOAD, FULL_PAYLOAD]

    def factory(candidate, run_index):
        if candidate.id == "alpha":
            return RoutedScriptedClient(payloads[(run_index - 1) % len(payloads)], {})
        return RoutedScriptedClient(FULL_PAYLOAD, {})

    result = run_bakeoff(inputs, config, factory, require_key=False)
    alpha = next(s for s in result.scores if s.candidate_id == "alpha")
    assert alpha.series["surface_f1"].stdev is not None
    assert alpha.series["surface_f1"].stdev > 0.0


# ── preflight ─────────────────────────────────────────────────────────────────────────────────────

def test_preflight_judges_every_dry_gate_without_spending_anything() -> None:
    # `evidence={}` is passed explicitly, not left to the default: the default reads the operator's real
    # recorded imagery evidence off disk, and a test whose verdict depends on whether somebody ran the
    # probe this afternoon is not a test.
    reports = preflight(bakeoff_config(), require_key=False, evidence={})
    assert len(reports) == 2
    for report in reports:
        statuses = {g.name: g.status for g in report.gates}
        assert statuses["vlm_imagery_path"] == "UNKNOWN"     # nothing exercised — cannot be a PASS
        assert statuses["keyless_equals_live"] == "PASS"
        assert statuses["pinned_model_id"] == "PASS"
        assert not report.eligible


def test_preflight_honours_recorded_imagery_evidence_but_not_a_stale_pin() -> None:
    """The imagery gate is the one gate inspection cannot judge, so it is judged on a recorded probe — and
    a record for a model id the candidate no longer names is treated as absent, never inherited."""
    from eval.extraction.vlm_probe import ImageryEvidence

    config = bakeoff_config()
    alpha, beta = config.candidates
    evidence = {
        alpha.id: ImageryEvidence(candidate_id=alpha.id, model_id=alpha.model_id, image="frame.png",
                                  calls_ok=1, calls_total=1, recorded_at="2026-07-25T00:00:00+00:00"),
        beta.id: ImageryEvidence(candidate_id=beta.id, model_id="some-other-pin", image="frame.png",
                                 calls_ok=1, calls_total=1, recorded_at="2026-07-25T00:00:00+00:00"),
    }
    statuses = {
        r.candidate_id: {g.name: g.status for g in r.gates}
        for r in preflight(config, require_key=False, evidence=evidence)
    }
    assert statuses[alpha.id]["vlm_imagery_path"] == "PASS"
    assert statuses[beta.id]["vlm_imagery_path"] == "UNKNOWN"


# ── the coref precondition ────────────────────────────────────────────────────────────────────────

def test_a_required_coref_metric_refuses_before_any_budget_is_spent(inputs) -> None:
    """`coref_binding` is top-weighted and declared required in the shipped config, and extraction pass 2
    ships OFF. The refusal has to happen up front: paying for N runs per candidate and *then* reporting
    INSUFFICIENT_CRITERIA buys a measurement that was structurally impossible before the first call."""
    from eval.extraction.coref_channel import FLAG, CorefChannelDormant

    config = bakeoff_config(required_metrics=["coref_binding"])
    spent: list[str] = []

    def factory(candidate, run_index):
        spent.append(candidate.id)
        return RoutedScriptedClient(FULL_PAYLOAD, {})

    with pytest.raises(CorefChannelDormant) as excinfo:
        run_bakeoff(inputs, config, factory, require_key=False)
    assert FLAG in str(excinfo.value)                    # it names the flag rather than flipping it
    assert "Do not re-weight it to zero" in str(excinfo.value)
    assert spent == []                                   # not one client was ever built


def test_with_both_halves_of_the_substrate_present_the_required_metric_no_longer_blocks(
        inputs, pipeline_config, tmp_path) -> None:
    """The block lifts by turning the channel on and labelling the slice — never by dropping the criterion.

    Both halves are needed: the model-facing channel (``cluster_coreferences``, flag-gated) and cluster
    labels in the gold. With either missing the run refuses up front; with both present it proceeds."""
    from dataclasses import replace

    from eval.extraction import coref_channel

    live_config = coref_channel.with_channel_on(pipeline_config)
    channel = coref_channel.inspect(live_config)
    assert channel.measurable
    assert channel.tool_name == "cluster_coreferences"
    assert channel.cluster_field == "clusters[].member_ids"

    labeled_gold = write_claim_gold(tmp_path / "gold_labeled.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
         "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 47]},
         "kind": "observation", "coref_cluster": "c1"},
        {"gold_id": "g2", "source_id": "doc1", "form": "entity", "entity_type": "component",
         "name": "Type-7 Coupler", "doc_ref": {"file": "doc1.txt", "span": [29, 47]},
         "kind": "observation", "coref_cluster": "c2"},
    ])

    config = bakeoff_config(required_metrics=["coref_binding"])
    result = run_bakeoff(replace(inputs, config=live_config, gold_path=labeled_gold), config,
                         _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}), require_key=False)
    assert result.scores
    # The scripted double answers pass 2 with a payload carrying no clusters, so nothing is bound and the
    # metric still reports NOT MEASURED — with the honest reason, and never a zero.
    reasons = result.scores[0].series["coref_binding"].reasons or ()
    assert any("NO CLUSTERING" in r for r in reasons)


def test_a_required_coref_metric_refuses_on_an_unlabeled_slice(inputs, pipeline_config) -> None:
    """The gold half of the same precondition, end to end: a live channel scored against a slice with no
    cluster labels is still an impossible measurement, and still refused before any budget is spent."""
    from dataclasses import replace

    from eval.extraction import coref_channel

    config = bakeoff_config(required_metrics=["coref_binding"])
    live = replace(inputs, config=coref_channel.with_channel_on(pipeline_config))
    with pytest.raises(coref_channel.CorefChannelDormant, match="no coref_cluster labels"):
        run_bakeoff(live, config, _factory({"alpha": FULL_PAYLOAD, "beta": WEAK_PAYLOAD}),
                    require_key=False)
