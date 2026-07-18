"""The bounded ReAct loop + fixed hero path (spine/09 bounds; deterministic given the client)."""

from __future__ import annotations

from chanakya.agent.assemble import assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import run_fixed_hero_path, run_react_loop

from .mock_llm import final, planner, tool_turn


def test_free_loop_runs_tools_and_records_the_trace(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    llm = planner(
        tool_turn("graph_find_entity", {"text": "HT-233"}),
        tool_turn("graph_neighbors", {"node_id": "comp_ht233", "edge_types": ["manufactures"]}),
        final(),
    )
    trace = run_react_loop(ctx, "Who manufactures HT-233?", llm)
    assert trace.terminated == "end_turn"
    assert [c.name for c in trace.calls] == ["find_entity", "neighbors"]
    a = assemble_answer(trace, ctx)
    assert a.answer is not None and "d21-l2" in a.citations  # the manufactures edge's claim


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
    assert [h["edge"] for h in path.result["hops"]] == ["based-at", "inducted-into", "equips", "manufactures"]
    # it also gathers the chokepoint via query_graph and checks sufficiency (the non-negotiable)
    assert trace.last("query_graph") is not None
    assert trace.last("check_sufficiency") is not None
