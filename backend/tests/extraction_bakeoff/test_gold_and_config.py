"""The labeled-input contracts and the shipped config — both must fail loudly rather than guess.

The scorer's author never opens the real gold or sub-oracle, so the *contract* is what stands in for
them. A loader that shrugged off an unrecognised shape would report every model as scoring zero, which
looks like a result and is not one.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from chanakya import settings
from eval.extraction.gold import load_claim_gold, load_sub_oracle
from eval.extraction.policy import load_bakeoff_config

from .fixtures import write_claim_gold, write_sub_oracle

# ── claim gold ────────────────────────────────────────────────────────────────────────────────────

def test_claim_gold_round_trips_the_declared_shape(tmp_path) -> None:
    path = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "triple", "polarity": "positive",
         "subject": "North Ridge Foundry", "predicate": "supplies-component",
         "object": "Type-7 Coupler", "doc_ref": {"file": "doc1.txt", "span": [0, 40]},
         "kind": "observation", "coref_cluster": "c1",
         "discriminators": {"operator": "the Regional Water Board"}},
        {"gold_id": "g2", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
         "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 19]}},
        {"gold_id": "g3", "source_id": "doc1", "form": "event", "event_type": "TransferEvent",
         "participants": ["North Ridge Foundry", "Eastvale Pumping Station"]},
    ])
    claims = load_claim_gold(path)
    assert [c.key for c in claims] == ["g1", "g2", "g3"]
    assert claims[0].roles == {"subject": "North Ridge Foundry", "object": "Type-7 Coupler"}
    assert claims[0].refs[0].span == (0, 40)
    assert claims[1].entity_type == "manufacturer"
    assert set(claims[2].roles) == {"participant:0", "participant:1"}


def test_an_absent_discriminator_reads_as_unstated_and_is_gradable(tmp_path) -> None:
    path = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "entity", "name": "X", "entity_type": "org",
         "discriminators": {"operator": "someone"}},
    ])
    disc = load_claim_gold(path)[0].discriminators
    assert disc["operator"] == "someone"
    assert disc["geography"] is None and disc["time"] is None


def test_a_wrong_schema_version_raises_rather_than_guessing(tmp_path) -> None:
    path = tmp_path / "gold.json"
    path.write_text(json.dumps({"schema_version": "something-else/9", "claims": []}))
    with pytest.raises(ValueError, match="Refusing to guess"):
        load_claim_gold(path)


def test_a_discriminator_slot_outside_a7_raises(tmp_path) -> None:
    path = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "d", "form": "entity", "name": "X",
         "discriminators": {"colour": "blue"}},
    ])
    with pytest.raises(ValueError, match="outside A7"):
        load_claim_gold(path)


def test_duplicate_gold_ids_raise(tmp_path) -> None:
    path = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "d", "form": "entity", "name": "X"},
        {"gold_id": "g1", "source_id": "d", "form": "entity", "name": "Y"},
    ])
    with pytest.raises(ValueError, match="duplicate gold_id"):
        load_claim_gold(path)


def test_an_unknown_form_raises(tmp_path) -> None:
    path = write_claim_gold(tmp_path / "gold.json",
                            [{"gold_id": "g1", "source_id": "d", "form": "quadruple"}])
    with pytest.raises(ValueError, match="expected one of"):
        load_claim_gold(path)


# ── sub-oracle ────────────────────────────────────────────────────────────────────────────────────

def test_sub_oracle_resolves_endpoints_by_id_and_inline(tmp_path) -> None:
    path = write_sub_oracle(
        tmp_path / "oracle.json",
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"},
         {"id": "n2", "type": "component", "name": "Type-7 Coupler"}],
        [{"type": "supplies-component", "source": "n1", "target": "n2"},
         {"type": "supplies-component", "source": {"type": "manufacturer", "name": "North Ridge Foundry"},
          "target": "n2"}],
    )
    oracle = load_sub_oracle(path)
    assert len(oracle.nodes) == 2 and len(oracle.edges) == 2
    assert oracle.edges[0].source.name == "North Ridge Foundry"


def test_an_endpoint_outside_the_node_set_raises(tmp_path) -> None:
    path = write_sub_oracle(
        tmp_path / "oracle.json",
        [{"id": "n1", "type": "manufacturer", "name": "A"}],
        [{"type": "supplies-component", "source": "n1", "target": "n_missing"}],
    )
    with pytest.raises(ValueError, match="not declared in 'nodes'"):
        load_sub_oracle(path)


def test_sub_oracle_schema_version_is_enforced(tmp_path) -> None:
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps({"schema_version": "answer-key/1.0", "nodes": [], "edges": []}))
    with pytest.raises(ValueError, match="Refusing to guess"):
        load_sub_oracle(path)


# ── the shipped config ────────────────────────────────────────────────────────────────────────────

def test_the_shipped_bakeoff_config_loads_and_declares_the_disciplines() -> None:
    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert cfg.replication.runs_per_candidate >= cfg.replication.min_runs_for_ranking
    assert cfg.replication.min_runs_for_ranking >= 2
    assert cfg.margin.min_absolute > 0 and cfg.margin.noise_multiplier > 0
    # The three candidates are a fixed decision, so what is asserted is the SHAPE of the field, not the
    # version strings: three declared candidates, one per provider, none text-only. Pinning the ids here
    # instead would mean a re-pin — a thing this bake-off is expected to do — shows up as a failing test
    # rather than as a new measurement. The pinned-id discipline is enforced where it belongs, by
    # `gate_pinned_model_id` against `gates.floating_alias_patterns`.
    providers = sorted(c.provider for c in cfg.candidates)
    assert providers == ["anthropic", "google", "openai"]
    assert len({c.id for c in cfg.candidates}) == 3
    assert not any(c.multimodal == "none" for c in cfg.candidates)   # text-only is a disqualifier
    # A NON-NEGOTIABLE IS A VETO, NEVER ALSO A PRICE. Every metric named in `non_negotiable_floors` must
    # carry ZERO composite weight, because a weight is something a good-enough model can outbid: a
    # candidate far enough ahead on recall could buy past a worse fabrication record and then re-freeze the
    # graded oracle. The config used to argue exactly this under `trap_avoidance` and then weight the other
    # two non-negotiables at 4.5 each — which also double-counted, since citation faithfulness strictly
    # contains extract-only-stated. Asserted here so the doctrine cannot quietly reverse.
    assert cfg.non_negotiable_metrics, "the bake-off must declare at least one non-negotiable"
    for name in cfg.non_negotiable_metrics:
        assert cfg.weight_for(name) == 0.0, (
            f"{name} is declared non-negotiable AND weighted {cfg.weight_for(name)} in the composite. A "
            "non-negotiable inside a composite is only a heavy weight, and any weight is a price."
        )
    # ...and every non-negotiable is still REPORTED and still vetoes, so dropping the weight is not the
    # same as dropping the criterion.
    assert set(cfg.non_negotiable_metrics) >= {"citation_faithfulness", "extract_only_stated",
                                               "trap_avoidance"}


def test_every_shipped_candidate_carries_a_concretely_pinned_model_id() -> None:
    """Discipline 1: a floating alias may never be measured, because the frozen seed would stop equalling
    what live produces. Asserted through the gate itself, so config and gate can never drift apart."""
    from eval.extraction.gates import gate_pinned_model_id

    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    for candidate in cfg.candidates:
        gate = gate_pinned_model_id(candidate, cfg)
        assert gate.status == "PASS", f"{candidate.id}: {gate.detail}"


def test_the_top_weighted_criterion_is_still_declared_required() -> None:
    """`coref_binding` is top-weighted and blocks the verdict. Dropping it from `required_metrics` to make
    a run go green is the one move that turns an honest gap into a silent one, so the config is held to it
    here rather than trusted to a comment."""
    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert "coref_binding" in cfg.required_metrics
    assert cfg.weights["coref_binding"] == max(cfg.weights.values())


def test_no_candidate_ships_with_an_invented_price() -> None:
    """A fabricated price would be a fabricated benchmark line — cost stays UNPRICED until a human fills it."""
    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert all(c.pricing is None for c in cfg.candidates)


def test_an_unknown_knob_is_an_error_not_a_silent_default(tmp_path) -> None:
    path = tmp_path / "bakeoff.yaml"
    path.write_text(
        "schema_version: rk-bakeoff/1.0\n"
        "replication: {runs_per_candidate: 3, min_runs_for_ranking: 3}\n"
        "margin: {min_absolute: 0.03, noise_multiplier: 2.0, mrgin_typo: 1}\n"
        "gates: {floating_alias_patterns: [], production_client_package: x}\n"
        "weights: {}\nmatch_policy: {role_min_similarity: 0.7, pair_min_similarity: 0.8, "
        "span_iou_floor: 0.3, span_bonus_weight: 0.15, grounding_similarity: 0.85}\ncandidates: []\n"
    )
    with pytest.raises(ValidationError, match="mrgin_typo"):
        load_bakeoff_config(path)
