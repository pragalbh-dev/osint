"""Tests for the seven deterministic ``graph_*`` tools — the analytical engine ASK's answers rest on.

These assert the acceptance-critical behaviours directly on the tool layer (before any LLM): the
did-you-mean disambiguation, the hero path, HT-233 landing in the ``indeterminate`` partition (never a
match for "sole-source"), observed-vs-inferred read from ``kind``, the reasoned refusal, and determinism.
"""

from __future__ import annotations

from chanakya.agent.context import ToolContext
from chanakya.agent.tools import run_tool
from chanakya.schemas import ClaimRecord, ConfigBundle, EvidenceTemplate, GraphView


def _ctx(view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle) -> ToolContext:
    return ToolContext.build(view, claims, config)


# ── find_entity ──────────────────────────────────────────────────────────────────────────────

def test_find_entity_exact_by_name(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "CASIC"})
    assert r["resolution"] == "exact" and r["resolved"] is True
    assert r["candidates"][0]["node_id"] == "mfr_casic"
    # config-alias table resolves too (HT233 → HT-233, via the squashed/alias tier)
    r2 = run_tool(ctx, "graph_find_entity", {"text": "HT233"})
    assert r2["candidates"][0]["node_id"] == "comp_ht233"


def test_find_entity_near_miss_returns_candidates_for_hq9p(view, claims, config) -> None:
    """AS-6: node is named 'HQ-9P'; the query 'HQ-9/P' RESOLVES via the punctuation-squashed key to a
    ranked near-miss candidate (not a raise, not a wrong bind). This is the hero-anchor fix."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "HQ-9/P"})
    assert r["resolution"] == "near_miss"
    assert r["candidates"][0]["node_id"] == "var_hq9p"
    assert "error" not in r
    # the candidate is self-describing (why it matched + look-alike siblings)
    assert r["candidates"][0]["why"]["matched_surface"]
    assert r["candidates"][0]["type"] == "variant"


def test_find_entity_alias_index_bug_fixed_fd2000(view, claims, config) -> None:
    """AS-6 (b): the alias-table entry 'HQ-9/P'→[…FD-2000] must attach even though NO node is named
    'HQ-9/P' (the node is 'HQ-9P') — the old name-equality rule dropped the whole class."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "FD-2000"})
    assert "error" not in r
    assert r["candidates"][0]["node_id"] == "var_hq9p"


def test_find_entity_surfaces_distinct_from(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "HQ-9/P"})
    sibs = r["candidates"][0]["distinct_from"]
    assert any(s["node_id"] == "var_hq9be" for s in sibs)


def test_find_entity_no_match_is_resolution_none_with_error(view, claims, config) -> None:
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_entity", {"text": "zzzznonsense-designator"})
    assert r["resolution"] == "none"
    assert "error" in r and r["suggestion"]


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
    """Acceptance: the hero query traces based-at → inducted-into → equips → supplies-component, citing a
    real claim at each hop (Mfr→Component is `supplies-component`, Phase-1 tightened `manufactures`)."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_find_paths", {"src": "site_karachi", "dst": "mfr_casic"})
    edge_types = [h["edge"] for h in r["hops"]]
    assert edge_types == ["based-at", "inducted-into", "equips", "supplies-component"]
    for h in r["hops"]:
        assert h["claim_ids"], f"hop {h['edge']} has no citation"
    assert r["hop_count"] == 4


def test_find_paths_default_whitelist_excludes_resolution_lane(view, claims, config) -> None:
    """AS-4: with no explicit whitelist, find_paths defaults to the ontology's traversable relations —
    a path through the distinct-from resolution lane (a NON-identity assertion) is not a fact chain."""
    ctx = _ctx(view, claims, config)
    # var_hq9p and var_hq9be are joined ONLY by distinct-from → default whitelist finds no path.
    r = run_tool(ctx, "graph_find_paths", {"src": "var_hq9p", "dst": "var_hq9be"})
    assert "error" in r
    # explicitly widening the whitelist to distinct-from re-enables it (the tool default, not a hack).
    r2 = run_tool(ctx, "graph_find_paths", {"src": "var_hq9p", "dst": "var_hq9be", "edge_whitelist": ["distinct-from"]})
    assert r2["hops"][0]["edge"] == "distinct-from"


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


def test_check_sufficiency_unknown_id_raises(view, claims, config) -> None:
    """AS-3: an unknown id is a LOOKUP FAILURE (like every sibling tool), not a fabricated
    'insufficient evidence' verdict about a phantom node."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_check_sufficiency", {"scope": "comp_does_not_exist"})
    assert "error" in r and r["suggestion"]


def test_check_sufficiency_accepts_a_gap_id(view, claims, config) -> None:
    """AS-3 caveat: a KnownGap.id is itself a valid scope (a gap id is not a node/edge id) — it must
    still return the reasoned insufficiency, not raise."""
    ctx = _ctx(view, claims, config)
    r = run_tool(ctx, "graph_check_sufficiency", {"scope": "gap:comp_ht233:sole_source"})
    assert "error" not in r
    assert r["sufficient"] is False
    assert r["known_gap"] is not None


def test_refusal_template_fires_for_dict_shaped_require(view, claims, config) -> None:
    """AS-5: the config/templates.yaml `require` shape is a list of {slot: {…}} DICTS. The matcher must
    read that shape (the old str-vs-dict compare was always False → every authored template was dead)."""
    from chanakya.agent.tools import _render_refusal

    ctx = _ctx(view, claims, config)
    # isolate the dict-entry shape (the real config/templates.yaml shape) so we prove IT fires.
    ctx.config.templates.templates = [
        EvidenceTemplate(
            assertion_type="based-at",
            require={"any_of": [{"imagery_confirmation": {"within_days": 365}},
                               {"independent_text_groups": {"min": 2}}]},
            on_fail="insufficient_evidence",
            refusal_template="Cannot confirm basing of {subject}: missing {missing_slots}. Next coverage due {next_coverage_due}.",
        )
    ]
    out = _render_refusal(ctx, "unit_paad", ["imagery_confirmation"], "2026-09-01")
    assert out == "Cannot confirm basing of unit_paad: missing imagery_confirmation. Next coverage due 2026-09-01."


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
