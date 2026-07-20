"""The bounded ReAct loop + fixed hero path (spine/09 bounds; deterministic given the client)."""

from __future__ import annotations

from chanakya.agent.assemble import assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import AgentTrace, RecordedCall, run_fixed_hero_path, run_react_loop
from chanakya.schemas import ConfigBundle
from chanakya.schemas.config_models import SubjectsConfig

from .mock_llm import final, planner, tool_turn


def _relens(config: ConfigBundle, anchors: list[str]) -> ConfigBundle:
    """The same bundle with the hero lens re-anchored — exercises the no-basing-site refusal branch."""
    lens = config.subjects.subjects[0].model_copy(update={"anchors": anchors})
    return config.model_copy(update={"subjects": SubjectsConfig(subjects=[lens])})


def test_errored_calls_are_invisible_to_builders(view, claims, config) -> None:
    """AS-1: an error-shaped result must fall through to the refusal path, never reach a builder as a
    success payload. The exact crasher was a failed get_node (no 'node_id' key) → KeyError."""
    ctx = ToolContext.build(view, claims, config)
    trace = AgentTrace(question="q")
    trace.calls.append(
        RecordedCall(name="get_node", input={"node_id": "nope"}, result={"error": "no node", "suggestion": "x"})
    )
    assert trace.last("get_node") is None                    # ok-filtered by default
    assert trace.last("get_node", ok_only=False) is not None  # still reachable when asked
    assert len(trace.failures()) == 1
    ans = assemble_answer(trace, ctx)                         # must NOT raise KeyError
    assert ans.answer is None and ans.refusal is not None


def test_free_loop_runs_tools_and_records_the_trace(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    llm = planner(
        tool_turn("graph_find_entity", {"text": "HT-233"}),
        tool_turn("graph_neighbors", {"node_id": "comp_ht233", "edge_types": ["supplies-component"]}),
        final(),
    )
    trace = run_react_loop(ctx, "Who manufactures HT-233?", llm)
    assert trace.terminated == "end_turn"
    assert [c.name for c in trace.calls] == ["find_entity", "neighbors"]
    a = assemble_answer(trace, ctx)
    assert a.answer is not None and "d21-l2" in a.citations  # the supplies-component edge's claim


def test_loop_respects_hard_iteration_cap(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    # A planner that never stops calling a tool — the cap must halt it.
    never_stops = planner(*[tool_turn("graph_get_node", {"node_id": "comp_ht233"}, call_id=f"t{i}") for i in range(20)])
    trace = run_react_loop(ctx, "loop forever", never_stops, max_iters=3)
    assert trace.terminated == "max_iters"
    assert len(trace.calls) == 3


def test_fixed_hero_path_builds_the_full_chain(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    trace = run_fixed_hero_path(ctx, "trace ... chokepoint")
    path = trace.last("find_paths")
    assert path is not None
    assert [h["edge"] for h in path.result["hops"]] == ["based-at", "inducted-into", "equips", "supplies-component"]
    # it also gathers the chokepoint via query_graph and checks sufficiency (the non-negotiable)
    assert trace.last("query_graph") is not None
    assert trace.last("check_sufficiency") is not None


def test_missing_basing_anchor_refuses_in_analyst_prose(view, claims, config) -> None:
    """R-9: the refusal body is read by an analyst — it must name entities, not print a Python list
    repr or an internal lens id. Anchors that resolve are rendered as their node names, comma-joined."""
    ctx = ToolContext.build(view, claims, _relens(config, ["unit_paad", "var_hq9p"]))
    trace = run_fixed_hero_path(ctx, "trace ... chokepoint")

    assert trace.refusal is not None
    reason = trace.refusal.reason
    assert "Pakistan Army Air Defence — HQ-9/P Regiment, HQ-9P" in reason  # names, comma-joined
    assert "lens-hq9p-pk" not in reason        # no internal lens id in analyst-facing text
    assert "[" not in reason and "'" not in reason  # no Python container/str repr
    # the machine-readable ids still travel in `missing` (the UI resolves them to names itself)
    assert trace.refusal.missing == ["unit_paad", "var_hq9p"]


def test_unresolved_anchor_refusal_names_what_is_absent(view, claims, config) -> None:
    """The other branch: an anchor the rebuilt view does not hold at all. Still no repr, no lens id —
    an id with no node falls back to itself rather than being dressed up as a name."""
    ctx = ToolContext.build(view, claims, _relens(config, ["unit_paad", "site_not_in_view"]))
    trace = run_fixed_hero_path(ctx, "trace ... chokepoint")

    assert trace.refusal is not None
    reason = trace.refusal.reason
    assert "not present in the rebuilt view: site_not_in_view" in reason
    assert "lens-hq9p-pk" not in reason
    assert "[" not in reason and "'" not in reason
    assert trace.refusal.missing == ["site_not_in_view"]
