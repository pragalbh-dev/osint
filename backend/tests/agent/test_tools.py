"""Tests for the seven deterministic ``graph_*`` tools — the analytical engine ASK's answers rest on.

These assert the acceptance-critical behaviours directly on the tool layer (before any LLM): the
did-you-mean disambiguation, the hero path, HT-233 landing in the ``indeterminate`` partition (never a
match for "sole-source"), observed-vs-inferred read from ``kind``, the reasoned refusal, and determinism.
"""

from __future__ import annotations

from chanakya.agent.context import ToolContext
from chanakya.agent.tools import run_tool
from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView


def _ctx(view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle) -> ToolContext:
    return ToolContext.build(view, claims, config)


# ── find_entity ──────────────────────────────────────────────────────────────────────────────

def test_find_entity_exact_and_alias(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "HQ-9/P"})
    assert r["resolved"] is True
    assert r["candidates"][0]["node_id"] == "var_hq9p"
    # config-alias resolves too (HT233 is a table alias of HT-233)
    r2 = run_tool(ctx, "graph_find_entity", {"text": "HT233"})
    assert r2["candidates"][0]["node_id"] == "comp_ht233"


def test_find_entity_did_you_mean_fires_on_hq9p(view, claims, config) -> None:
    """Acceptance: the 'did you mean' error fires on HQ9P (no silent wrong bind)."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "HQ9P"})
    assert "error" in r
    assert "did you mean" in r["error"].lower()
    assert "HQ-9/P" in r["error"]


def test_find_entity_surfaces_distinct_from(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "HQ-9/P"})
    sibs = r["candidates"][0]["distinct_from"]
    assert any(s["node_id"] == "var_hq9be" for s in sibs)


def test_find_entity_type_hint_filters(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "CASIC", "type_hint": "manufacturer"})
    assert r["candidates"][0]["node_id"] == "mfr_casic"


# ── get_node / neighbors ──────────────────────────────────────────────────────────────────────

def test_get_node_carries_materiality_and_provenance(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_get_node", {"node_id": "comp_ht233"})
    assert r["materiality"]["chokepoint_status"] == "candidate"
    assert r["materiality"]["substitutability_state"] == "UNKNOWN"
    assert r["claim_ids"]


def test_get_node_unknown_id_is_actionable(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_get_node", {"node_id": "nope"})
    assert "error" in r and r["suggestion"]


def test_neighbors_typed_and_paginated(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_neighbors", {"node_id": "unit_paad", "direction": "both"})
    assert r["total"] >= 2  # based-at + inducted-into
    for nb in r["neighbours"]:
        assert nb["claim_ids"]  # supporting claim ids per edge
    # pagination is stable
    p0 = run_tool(ctx, "graph_neighbors", {"node_id": "unit_paad", "limit": 1, "offset": 0})
    p1 = run_tool(ctx, "graph_neighbors", {"node_id": "unit_paad", "limit": 1, "offset": 1})
    assert p0["neighbours"][0]["edge_id"] != p1["neighbours"][0]["edge_id"]


def test_neighbors_edge_type_filter(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_neighbors", {"node_id": "unit_paad", "edge_types": ["based-at"]})
    assert all(nb["edge_type"] == "based-at" for nb in r["neighbours"])


# ── find_paths (the flagship trace) ─────────────────────────────────────────────────────────────

def test_find_paths_hero_chain(view, claims, config) -> None:
    """Acceptance: the hero query traces based-at → inducted-into → equips → manufactures, citing a
    real claim at each hop (answer_key edge names)."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_paths", {"src": "site_karachi", "dst": "mfr_casic"})
    edge_types = [h["edge"] for h in r["hops"]]
    assert edge_types == ["based-at", "inducted-into", "equips", "manufactures"]
    for h in r["hops"]:
        assert h["claim_ids"], f"hop {h['edge']} has no citation"
    assert r["hop_count"] == 4


def test_find_paths_respects_hop_cap(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_paths", {"src": "site_karachi", "dst": "mfr_casic", "max_hops": 2})
    assert "error" in r  # 4-hop chain unreachable within 2


# ── query_graph (the honesty fork) ──────────────────────────────────────────────────────────────

def test_query_graph_ht233_is_indeterminate_not_match_for_sole_source(view, claims, config) -> None:
    """The disqualifying line: a 'known-sole-source' filter must put HT-233 (UNKNOWN) in the
    indeterminate partition, NEVER in matches (absence of evidence ≠ evidence of absence)."""
    ctx = _ctx(view, claims, config)
    r = run_tool(
        ctx,
        "graph_query_graph",
        {
            "pattern": "component",
            "constraints": [{"attr": "substitutability_state", "op": "=", "value": "known-sole-source"}],
        },
    )
    match_ids = [m["node_id"] for m in r["matches"]]
    indet_ids = [m["node_id"] for m in r["indeterminate"]]
    assert "comp_ht233" not in match_ids
    assert "comp_ht233" in indet_ids
    assert r["match_count"] == 0


def test_query_graph_candidate_chokepoint_filter(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(
        ctx,
        "graph_query_graph",
        {"pattern": "component", "constraints": [{"attr": "chokepoint_status", "op": "=", "value": "candidate"}]},
    )
    assert [m["node_id"] for m in r["matches"]] == ["comp_ht233"]


def test_query_graph_aggregate_count(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(
        ctx,
        "graph_query_graph",
        {"pattern": "component", "constraints": [{"attr": "chokepoint_count", "op": "<", "value": 3}],
         "aggregate": {"op": "count"}},
    )
    assert r["aggregate"]["result"] == r["match_count"]


# ── get_evidence (observed-vs-inferred from kind) ────────────────────────────────────────────────

def test_get_evidence_observed_vs_inferred(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    # equips edge is backed by an inference claim → 'inferred'
    r = run_tool(ctx, "graph_get_evidence", {"ref_id": "e:comp_ht233:equips:var_hq9p"})
    assert r["indicators"][0]["observed_or_inferred"] == "inferred"
    # based-at edge is imagery → 'observed'
    r2 = run_tool(ctx, "graph_get_evidence", {"ref_id": "e:unit_paad:based-at:site_karachi"})
    assert r2["indicators"][0]["observed_or_inferred"] == "observed"
    assert r2["indicators"][0]["source"]["url"]  # one-click-to-source


# ── check_sufficiency (the refusal engine) ──────────────────────────────────────────────────────

def test_check_sufficiency_planted_gap(view, claims, config) -> None:
    """Acceptance: a planted-gap scope returns a reasoned insufficiency with missing_slots +
    next_coverage_due (a Known Gap), not a guess."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_check_sufficiency", {"scope": "comp_ht233"})
    assert r["sufficient"] is False
    assert r["missing_slots"]
    assert r["next_coverage_due"] == "2026-09-01"
    assert r["known_gap"] is not None
    assert "insufficient evidence" in r["reason"].lower()


def test_check_sufficiency_never_observable(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_check_sufficiency", {"scope": "var_hq9p"})
    # var_hq9p has a never-observable gap (magazine depth)
    assert r["sufficient"] is False
    assert r["observability_ceiling"] == "never-observable"


# ── determinism + dispatcher hygiene ─────────────────────────────────────────────────────────────

def test_tool_results_are_deterministic(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    call = {"pattern": "component", "constraints": [{"attr": "status", "op": "=", "value": "confirmed"}]}
    a = run_tool(ctx, "graph_query_graph", dict(call))
    b = run_tool(ctx, "graph_query_graph", dict(call))
    assert a == b


def test_unknown_tool_and_missing_params(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    assert "error" in run_tool(ctx, "graph_frobnicate", {})
    r = run_tool(ctx, "graph_get_node", {})
    assert "error" in r and "node_id" in r["error"]
