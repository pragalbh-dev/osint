"""Every scored line, plus the rule that a metric with no substrate reports nothing rather than zero."""

from __future__ import annotations

import pytest

from eval.extraction.matcher import match_claims
from eval.extraction.metrics import (
    NO_CLUSTERING,
    MetricValue,
    citation_faithfulness,
    coref_binding,
    cost_metric,
    discriminator_metrics,
    extract_only_stated,
    graph_recall,
    kind_tagging,
    latency_metric,
    structured_output_reliability,
    surface_metrics,
    tally_discriminators,
)
from eval.extraction.policy import Pricing
from eval.extraction.recording import CallRecord

from .fixtures import POLICY, entity, triple

DOC = (
    "North Ridge Foundry supplies the Type-7 Coupler to the Eastvale Pumping Station. "
    "The station is operated by the Regional Water Board."
)
TEXTS = {"doc1.txt": DOC}


# ── the MetricValue invariant ─────────────────────────────────────────────────────────────────────

def test_unavailable_metric_can_never_carry_a_number() -> None:
    with pytest.raises(ValueError, match="never publish a number"):
        MetricValue(name="x", value=0.0, status="unavailable", reason="no substrate")
    with pytest.raises(ValueError, match="needs a reason"):
        MetricValue(name="x", value=None, status="unavailable")
    with pytest.raises(ValueError, match="no value"):
        MetricValue(name="x", value=None, status="measured")


def test_a_zero_denominator_reports_unavailable_not_zero() -> None:
    metric = kind_tagging(match_claims([], [], POLICY))
    assert metric.status == "unavailable" and metric.value is None


# ── surface ───────────────────────────────────────────────────────────────────────────────────────

def test_surface_metrics_report_precision_recall_f1() -> None:
    gold = [triple("g1", "North Ridge Foundry", "Type-7 Coupler")]
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler")]
    values = surface_metrics(match_claims(gold, got, POLICY))
    assert values["surface_f1"].value == pytest.approx(1.0)


def test_extracting_nothing_scores_recall_zero_but_precision_undefined() -> None:
    gold = [triple("g1", "North Ridge Foundry", "Type-7 Coupler")]
    values = surface_metrics(match_claims(gold, [], POLICY))
    assert values["surface_recall"].value == 0.0
    assert values["surface_precision"].status == "unavailable"


def test_an_empty_gold_slice_is_unavailable_not_perfect() -> None:
    values = surface_metrics(match_claims([], [triple("c1", "A", "B")], POLICY))
    assert all(v.status == "unavailable" for v in values.values())


# ── citation faithfulness ─────────────────────────────────────────────────────────────────────────

def test_a_claim_citing_the_right_span_is_faithful() -> None:
    span = (0, DOC.index("Station") + len("Station"))
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler", span=span)]
    metric = citation_faithfulness(got, TEXTS, POLICY)
    assert metric.value == pytest.approx(1.0)


def test_a_claim_citing_a_span_that_does_not_contain_it_is_unfaithful() -> None:
    span = (DOC.index("The station"), len(DOC))
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler", span=span)]
    assert citation_faithfulness(got, TEXTS, POLICY).value == pytest.approx(0.0)


def test_an_out_of_bounds_span_is_a_failure_not_an_excuse() -> None:
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler", span=(5000, 5100))]
    metric = citation_faithfulness(got, TEXTS, POLICY)
    assert metric.value == pytest.approx(0.0)
    assert metric.detail["span_out_of_bounds"]


def test_a_faithful_but_dehyphenated_designator_is_not_reported_as_fabrication() -> None:
    """The identifier rule has to reach the grounding lane, and this is where it matters most.

    ``citation_faithfulness`` and ``extract_only_stated`` are the two metrics this bake-off declares
    non-negotiable. Under the prose reading, a model that wrote ``Type7`` where the document says ``Type-7``
    was scored as citing text that does not contain its claim — a FALSE fabrication finding against a model
    that quoted the page correctly. Measured on the real slice documents at the declared 0.85 floor, the
    prose reading scored five such surfaces 0.75–0.83 (absent) where the designator reading scores 1.00.
    """
    span = (0, DOC.index("Station") + len("Station"))
    got = [triple("c1", "North Ridge Foundry", "Type7", span=span)]
    assert citation_faithfulness(got, TEXTS, POLICY).value == pytest.approx(1.0)
    prose = POLICY.model_copy(update={"identifier_policy": "prose"})
    assert citation_faithfulness(got, TEXTS, prose).value == pytest.approx(0.0)


def test_the_identifier_rule_cannot_launder_a_fabrication() -> None:
    """Gluing removes punctuation *inside* a letters-and-digits token, so an invented surface only becomes
    groundable if the document already states the same string in another rendering — which is what
    "grounded" means. An invented designator stays ungrounded on both lanes."""
    span = (0, DOC.index("Station") + len("Station"))
    got = [triple("c1", "North Ridge Foundry", "XT455", span=span)]
    assert citation_faithfulness(got, TEXTS, POLICY).value == pytest.approx(0.0)
    assert extract_only_stated(got, TEXTS, POLICY).value == pytest.approx(0.0)


def test_an_unsourced_claim_counts_against_faithfulness() -> None:
    got = [triple("c1", "North Ridge Foundry", "Type-7 Coupler", file="")]
    metric = citation_faithfulness(got, TEXTS, POLICY)
    assert metric.value == pytest.approx(0.0)
    assert metric.detail["unsourced"] == ["c1"]


def test_image_refs_are_excluded_and_reported_never_silently_passed() -> None:
    got = [triple("c1", "Something", "Somewhere", file="frame.png", span=None)]
    metric = citation_faithfulness(got, TEXTS, POLICY)
    assert metric.status == "unavailable"
    assert metric.detail["not_char_addressable"] == ["c1"]


def test_an_injected_judge_replaces_the_lexical_proxy() -> None:
    got = [triple("c1", "Wholly Different", "Other Thing", span=(0, 40))]
    metric = citation_faithfulness(got, TEXTS, POLICY, judge=lambda claim, text: True)
    assert metric.value == pytest.approx(1.0)
    assert metric.detail["method"] == "entailment-judge"


# ── extract-only-stated (the fabrication line) ────────────────────────────────────────────────────

def test_a_claim_about_something_absent_from_the_document_is_unsupported() -> None:
    got = [
        triple("c1", "North Ridge Foundry", "Type-7 Coupler"),
        triple("c2", "Sunmarket Holdings", "Ballistic Interceptor"),
    ]
    metric = extract_only_stated(got, TEXTS, POLICY)
    assert metric.value == pytest.approx(0.5)
    assert metric.detail["unsupported"] == ["c2"]


def test_claims_with_no_text_source_are_reported_as_ungradable() -> None:
    got = [triple("c1", "Anything", "At All", file="frame.png")]
    metric = extract_only_stated(got, TEXTS, POLICY)
    assert metric.status == "unavailable"
    assert metric.detail["ungradable_no_text_source"] == ["c1"]


# ── structured output ─────────────────────────────────────────────────────────────────────────────

def _call(payload: dict | None, *, error: str | None = None,
          offered: tuple[str, ...] = ("orgs",)) -> CallRecord:
    return CallRecord(lane="text", tool_name="t", offered_fields=offered, payload=payload,
                      latency_s=0.1, error=error)


def test_structured_output_counts_failures_and_invented_fields() -> None:
    calls = [
        _call({"orgs": []}),
        _call({"orgs": [], "totally_made_up": 1}),
        _call(None, error="RuntimeError: no tool call"),
    ]
    metric = structured_output_reliability(calls)
    assert metric.value == pytest.approx(1 / 3)
    assert metric.detail["invented_top_level_fields"] == {"t": ["totally_made_up"]}


def test_a_schema_with_no_declared_properties_cannot_accuse_anyone() -> None:
    metric = structured_output_reliability([_call({"anything": 1}, offered=())])
    assert metric.value == pytest.approx(1.0)


# ── A7 discriminators ─────────────────────────────────────────────────────────────────────────────

GOLD_ENTITY = entity(
    "g1", "North Ridge Foundry",
    discriminators={"operator": "the Regional Water Board", "geography": None,
                    "designation": None, "time": None},
)


def test_a_stated_discriminator_carried_through_is_captured() -> None:
    payload = {"manufacturers": [{"name": "North Ridge Foundry",
                                  "context": {"operator": "the Regional Water Board"}}]}
    tally = tally_discriminators([payload], [GOLD_ENTITY], POLICY)
    assert tally.captured == 1 and tally.missed == 0 and tally.fabricated == 0
    assert tally.correct_abstention == 3
    values = discriminator_metrics(tally)
    assert values["discriminator_capture"].value == pytest.approx(1.0)
    assert values["discriminator_fabrication_avoidance"].value == pytest.approx(1.0)


def test_inventing_an_unstated_discriminator_is_counted_as_fabrication() -> None:
    payload = {"manufacturers": [{"name": "North Ridge Foundry",
                                  "context": {"operator": "the Regional Water Board",
                                              "geography": "somewhere the source never said"}}]}
    tally = tally_discriminators([payload], [GOLD_ENTITY], POLICY)
    assert tally.fabricated == 1
    assert discriminator_metrics(tally)["discriminator_fabrication_avoidance"].value == \
        pytest.approx(2 / 3)


def test_a_missing_stated_discriminator_is_a_miss_not_a_fabrication() -> None:
    payload = {"manufacturers": [{"name": "North Ridge Foundry"}]}
    tally = tally_discriminators([payload], [GOLD_ENTITY], POLICY)
    assert tally.missed == 1 and tally.fabricated == 0
    assert discriminator_metrics(tally)["discriminator_capture"].value == pytest.approx(0.0)


def test_mentions_that_align_to_no_gold_claim_are_reported_not_graded() -> None:
    payload = {"manufacturers": [{"name": "Some Other Entity", "context": {"operator": "x"}}]}
    tally = tally_discriminators([payload], [GOLD_ENTITY], POLICY)
    assert tally.ungradable_mentions == 1
    assert discriminator_metrics(tally)["discriminator_capture"].status == "unavailable"


def test_the_mention_walk_finds_nested_mentions_in_any_format() -> None:
    payload = {"tender": {"oem": {"name": "North Ridge Foundry",
                                  "context": {"operator": "the Regional Water Board"}}}}
    assert tally_discriminators([payload], [GOLD_ENTITY], POLICY).captured == 1


# ── coref: implemented; the substrate shipped, so "unavailable" now means nobody bound ───────────

def test_coref_binding_reports_no_clustering_not_a_number() -> None:
    gold = [entity("g1", "North Ridge Foundry", coref_cluster="c1")]
    got = [entity("c1", "North Ridge Foundry")]          # nothing was bound → referent_id None
    metric = coref_binding(match_claims(gold, got, POLICY))
    assert metric.status == "unavailable" and metric.value is None
    assert metric.reason == NO_CLUSTERING


def test_coref_binding_computes_bcubed_once_referents_exist() -> None:
    """The metric is real, not a stub: give it referent ids and it scores."""
    gold = [entity("g1", "North Ridge Foundry", coref_cluster="A"),
            entity("g2", "the Foundry", coref_cluster="A")]
    got = [entity("c1", "North Ridge Foundry", referent_id="ref:doc1-1"),
           entity("c2", "the Foundry", referent_id="ref:doc1-1")]
    metric = coref_binding(match_claims(gold, got, POLICY))
    assert metric.status == "measured" and metric.value == pytest.approx(1.0)


def test_coref_binding_penalises_a_wrong_split() -> None:
    gold = [entity("g1", "North Ridge Foundry", coref_cluster="A"),
            entity("g2", "the Foundry", coref_cluster="A")]
    got = [entity("c1", "North Ridge Foundry", referent_id="ref:doc1-1"),
           entity("c2", "the Foundry", referent_id="ref:doc1-2")]
    metric = coref_binding(match_claims(gold, got, POLICY))
    assert metric.status == "measured" and metric.value is not None and metric.value < 1.0


def test_coref_without_gold_labels_is_unavailable_for_a_different_reason() -> None:
    gold = [entity("g1", "North Ridge Foundry")]
    got = [entity("c1", "North Ridge Foundry", referent_id="ref:doc1-1")]
    metric = coref_binding(match_claims(gold, got, POLICY))
    assert metric.status == "unavailable" and "coref_cluster labels" in metric.reason


# ── graph recall ──────────────────────────────────────────────────────────────────────────────────

def _view(nodes: list[tuple[str, str, str]], edges: list[tuple[str, str, str]]):
    from chanakya.schemas import GraphView

    return GraphView.model_validate({
        "nodes": [{"id": i, "type": t, "name": n} for i, t, n in nodes],
        "edges": [{"id": f"e{k}", "type": t, "source": s, "target": o}
                  for k, (t, s, o) in enumerate(edges)],
    })


def _oracle(tmp_path, nodes, edges):
    from eval.extraction.gold import load_sub_oracle

    from .fixtures import write_sub_oracle

    return load_sub_oracle(write_sub_oracle(tmp_path / "oracle.json", nodes, edges))


def test_graph_recall_matches_on_type_and_name_not_ids(tmp_path) -> None:
    oracle = _oracle(
        tmp_path,
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"},
         {"id": "n2", "type": "component", "name": "Type-7 Coupler"}],
        [{"type": "supplies-component", "source": "n1", "target": "n2"}],
    )
    view = _view([("mfr_x9", "manufacturer", "North Ridge Foundry"),
                  ("cmp_q2", "component", "Type-7 Coupler")],
                 [("supplies-component", "mfr_x9", "cmp_q2")])
    values = graph_recall(view, oracle, POLICY)
    assert values["graph_node_recall"].value == pytest.approx(1.0)
    assert values["graph_edge_recall"].value == pytest.approx(1.0)


def test_a_reversed_edge_is_reported_and_credited_to_nobody(tmp_path) -> None:
    oracle = _oracle(
        tmp_path,
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"},
         {"id": "n2", "type": "component", "name": "Type-7 Coupler"}],
        [{"type": "supplies-component", "source": "n1", "target": "n2"}],
    )
    view = _view([("a", "manufacturer", "North Ridge Foundry"), ("b", "component", "Type-7 Coupler")],
                 [("supplies-component", "b", "a")])
    values = graph_recall(view, oracle, POLICY)
    assert values["graph_edge_recall"].value == pytest.approx(0.0)
    assert values["graph_edge_recall"].detail["reversed_direction_not_credited"]


def test_an_empty_oracle_is_unavailable_not_perfect(tmp_path) -> None:
    oracle = _oracle(tmp_path, [], [])
    values = graph_recall(_view([], []), oracle, POLICY)
    assert values["graph_recall"].status == "unavailable"


# ── cost + latency ────────────────────────────────────────────────────────────────────────────────

def test_cost_is_unpriced_rather_than_zero_when_no_pricing_is_declared() -> None:
    metric = cost_metric({"input_tokens": 1000, "output_tokens": 500}, None)
    assert metric.status == "unavailable" and "UNPRICED" in metric.reason


def test_cost_is_unavailable_when_the_provider_reported_no_usage() -> None:
    metric = cost_metric(None, Pricing(input_per_mtok=1.0, output_per_mtok=2.0))
    assert metric.status == "unavailable" and metric.value is None


def test_cost_is_computed_when_both_usage_and_prices_exist() -> None:
    metric = cost_metric({"input_tokens": 1_000_000, "output_tokens": 500_000},
                         Pricing(input_per_mtok=3.0, output_per_mtok=15.0))
    assert metric.value == pytest.approx(3.0 + 7.5)
    assert metric.direction == "lower_is_better"


def test_latency_is_unavailable_when_no_call_was_made() -> None:
    assert latency_metric(0.0, 0).status == "unavailable"
    assert latency_metric(1.5, 3).value == pytest.approx(1.5)
