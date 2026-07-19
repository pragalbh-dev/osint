"""Offline raise-only LLM candidate proposer tests (spine/08 §3.11) — all LLM mocked, offline."""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import Entity
from chanakya.resolve.propose import propose_candidates
from tests.resolve._helpers import entity, mk_config

# The gated proposer config: fire only on high-alias-risk types that are orphan/thin-block.
PROPOSER_CFG = dict(
    high_alias_risk_types=["variant", "component", "unit", "manufacturer"],
    orphan_block_threshold_k=2,
    llm_candidate_gen={"max_calls_per_rebuild": 20, "batch_per_orphan": True, "log_skips": True},
)


def _mock_llm(mapping: dict[str, list[str]]):
    def llm(orphan: Entity, shortlist: list[Entity]) -> list[str]:
        return mapping.get(orphan.eid, [])
    return llm


def test_proposer_fires_on_orphan_alias_risk_entity() -> None:
    cfg = mk_config(**PROPOSER_CFG)
    # comp_ht233 is an orphan component (no deterministic candidate shares its block) — the LLM path.
    claims = [entity("comp_ht233", "component", "HT-233", functional_role="engagement_fire_control")]
    run = propose_candidates(claims, cfg, now="2026-07-18T00:00:00Z", llm=_mock_llm({"comp_ht233": ["H-200"]}))
    assert run.fired == ["comp_ht233"]
    assert len(run.records) == 1
    rec = run.records[0]
    assert rec.type == "merge_proposal" and rec.decision["raise_only"] is True
    assert rec.context["cited_claims"]  # cited to the orphan's claims


def test_proposer_skips_well_covered_and_wrong_type() -> None:
    cfg = mk_config(**PROPOSER_CFG)
    claims = [
        # components sharing a name token ⇒ each has ≥ k deterministic candidates → NOT orphan → skip
        entity("comp_a", "component", "HT-233 alpha"),
        entity("comp_b", "component", "HT-233 beta"),
        entity("comp_c", "component", "HT-233 gamma"),
        # a source is not a high-alias-risk type → skip
        entity("src_x", "source", "Some Registry"),
    ]
    run = propose_candidates(claims, cfg, now="2026-07-18T00:00:00Z", llm=_mock_llm({}))
    assert run.fired == []
    assert set(run.skipped) == {"comp_a", "comp_b", "comp_c", "src_x"}


def test_proposer_respects_budget_cap() -> None:
    cfg = mk_config(
        high_alias_risk_types=["component"],
        orphan_block_threshold_k=2,
        llm_candidate_gen={"max_calls_per_rebuild": 1},
    )
    claims = [
        entity("comp_1", "component", "Alpha"),
        entity("comp_2", "component", "Bravo"),
        entity("comp_3", "component", "Charlie"),
    ]
    run = propose_candidates(claims, cfg, now="t", llm=_mock_llm({}))
    assert len(run.fired) == 1  # budget = 1 call; the rest are logged as skipped, not silently dropped
    assert len(run.skipped) == 2


def test_proposer_dormant_when_unconfigured() -> None:
    cfg = mk_config()  # no high_alias_risk_types / orphan_k
    run = propose_candidates([entity("comp_x", "component", "X")], cfg, now="t", llm=_mock_llm({"comp_x": ["Y"]}))
    assert run.records == [] and run.fired == []


def test_proposed_pair_is_raise_only_when_consumed() -> None:
    # End-to-end: the frozen merge_proposal, fed to resolve(), lifts the pair into HITL — never auto.
    cfg = mk_config(**PROPOSER_CFG)
    claims = [
        entity("comp_ht233", "component", "HT-233"),
        entity("comp_h200", "component", "H-200"),
    ]
    run = propose_candidates(claims, cfg, now="t", llm=_mock_llm({"comp_h200": ["comp_ht233"]}))
    part = resolve(claims, cfg, decisions=run.records)
    assert frozenset({"comp_h200", "comp_ht233"}) in {frozenset(p) for p in part.candidates}
    assert part.same_as == []  # the raised orphan alias reaches the analyst, never auto-merges
