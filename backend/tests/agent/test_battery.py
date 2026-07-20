"""Wide query battery (sessions/ASK.md acceptance): the 10 spine/09 taxonomy shapes + adversarial/edge
phrasings, each **answered with per-hop citations or refused as insufficient — never fabricated**.

Breadth is served by *composing* the seven tools (spine/09), not by a tool per question. Every case is
driven offline by a scripted planner (or the deterministic fixed hero path); the coverage verdict is
asserted here and recorded in the PR handoff.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from chanakya.agent import ask
from chanakya.agent.client import LLMClient

from .mock_llm import final, planner, tool_turn

HERO_Q = "trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint"


@dataclass
class Case:
    id: str
    shape: str
    question: str
    llm: LLMClient | None
    expect: str  # "answered" | "refused"
    contains: str | None = None  # optional substring the answer must include


def battery_cases() -> list[Case]:
    """Fresh planners per call (ScriptedClient is stateful)."""
    return [
        Case("point-lookup", "1 point lookup", "What is HT-233?",
             planner(tool_turn("graph_find_entity", {"text": "HT-233"}, "a"),
                     tool_turn("graph_get_node", {"node_id": "comp_ht233"}, "b"), final()), "answered"),
        Case("one-hop", "2 one-hop neighbourhood", "Who manufactures HT-233?",
             planner(tool_turn("graph_find_entity", {"text": "HT-233"}, "a"),
                     tool_turn("graph_neighbors", {"node_id": "comp_ht233", "edge_types": ["supplies-component"]}, "b"),
                     final()), "answered"),
        Case("multi-hop", "3 multi-hop path (flagship)", HERO_Q, None, "answered", contains="chokepoint_status=candidate"),
        Case("filtered", "4 filtered / spatial", "Which components equip HQ-9/P?",
             planner(tool_turn("graph_query_graph", {"pattern": "component", "anchor": "var_hq9p", "constraints": []}, "a"),
                     final()), "answered"),
        Case("aggregate", "5 structural predicate + aggregation", "Which components have fewer than 3 chokepoints?",
             planner(tool_turn("graph_query_graph",
                               {"pattern": "component", "constraints": [{"attr": "chokepoint_count", "op": "<", "value": 3}],
                                "aggregate": {"op": "count"}}, "a"), final()), "answered"),
        Case("status", "6 status / corroboration", "Is the Karachi basing confirmed, and on what evidence?",
             planner(tool_turn("graph_get_node", {"node_id": "site_karachi"}, "a"),
                     tool_turn("graph_get_evidence", {"ref_id": "e:unit_paad:based-at:site_karachi"}, "b"),
                     final()), "answered"),
        Case("gap", "7 gap / insufficiency", "What do we NOT know about HT-233's supplier?",
             planner(tool_turn("graph_check_sufficiency", {"scope": "comp_ht233"}, "a"), final()), "refused"),
        Case("temporal", "8 temporal / change (monitoring)", "Is the Rahwali basing still current or stale?",
             planner(tool_turn("graph_get_node", {"node_id": "site_rahwali"}, "a"), final()), "answered", contains="stale"),
        Case("reverse", "9 reverse / dependency-inversion", "Given CASIC, what fielded systems depend on it?",
             planner(tool_turn("graph_find_entity", {"text": "CASIC"}, "a"),
                     tool_turn("graph_neighbors", {"node_id": "mfr_casic", "direction": "both"}, "b"), final()), "answered"),
        Case("ranking", "10 comparative / ranking", "Rank HQ-9/P components by chokepoint count.",
             planner(tool_turn("graph_query_graph",
                               {"pattern": "component", "constraints": [{"attr": "chokepoint_count", "op": ">=", "value": 0}],
                                "aggregate": {"op": "rank", "attr": "chokepoint_count"}}, "a"), final()), "answered"),
        # adversarial / edge phrasings
        Case("misspelling", "adversarial: misspelling (no silent wrong bind)", "HQ9P supplier?",
             planner(tool_turn("graph_find_entity", {"text": "HQ9P"}, "a"), final()), "refused"),
        Case("absence-trap", "adversarial: absence ≠ negative", "Is HT-233 a confirmed sole-source?",
             planner(tool_turn("graph_query_graph",
                               {"pattern": "component",
                                "constraints": [{"attr": "substitutability_state", "op": "=", "value": "known-sole-source"}]}, "a"),
                     final()), "answered", contains="INDETERMINATE"),
    ]


def _assert_never_fabricated(case: Case, a, claims) -> None:
    if case.expect == "answered":
        assert a.answer is not None and a.refusal is None, f"{case.id}: expected an answer"
        assert a.citations, f"{case.id}: answer has no citations"
        assert all(c in claims for c in a.citations), f"{case.id}: cites a claim not in the evidence log"
        for h in a.hops:
            assert h.claim_ids, f"{case.id}: hop {h.edge} is a naked assertion"
        if case.contains:
            assert case.contains in a.answer, f"{case.id}: answer missing '{case.contains}'"
    else:
        assert a.answer is None and a.refusal is not None, f"{case.id}: expected a refusal, got an answer"


@pytest.mark.parametrize("case", battery_cases(), ids=lambda c: c.id)
def test_battery_case_answered_or_refused_never_fabricated(case: Case, view, claims, config) -> None:
    a = ask(case.question, view, config, llm=case.llm, claims=claims)
    _assert_never_fabricated(case, a, claims)


def test_battery_covers_the_taxonomy(view, claims, config) -> None:
    """Coverage verdict: ≥10 spine/09 shapes exercised; every case honours the invariant."""
    cases = battery_cases()
    shapes = {c.shape for c in cases}
    taxonomy_shapes = {s for s in shapes if s[0].isdigit()}
    assert len(taxonomy_shapes) >= 10, f"only {len(taxonomy_shapes)} taxonomy shapes covered"
    for case in cases:
        a = ask(case.question, view, config, llm=case.llm, claims=claims)
        _assert_never_fabricated(case, a, claims)
