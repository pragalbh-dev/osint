"""The bounded ReAct loop (spine/09 bounds; deterministic given the client)."""

from __future__ import annotations

from chanakya.agent.assemble import assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import AgentTrace, RecordedCall, run_react_loop

from .mock_llm import final, planner, tool_turn


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


def test_free_loop_reaches_supply_chain_via_graph_analyze(view, claims, config) -> None:
    """The flagship trace is no longer special-cased: the planner reaches it by calling graph_analyze.
    The one analyze call carries the whole multi-hop chain + the chokepoint, assembled into a cited answer."""
    ctx = ToolContext.build(view, claims, config)
    llm = planner(tool_turn("graph_analyze", {"subject_id": "site_karachi", "analysis": "supply_chain"}), final())
    trace = run_react_loop(ctx, "trace ... chokepoint", llm)
    assert trace.terminated == "end_turn"
    assert trace.last("analyze") is not None
    a = assemble_answer(trace, ctx)
    assert a.refusal is None and a.answer is not None
    assert [h.edge for h in a.hops] == ["based-at", "inducted-into", "equips", "supplies-component"]
    # the chokepoint is still named, still labelled candidate, and its open gap stated (the non-negotiable)
    assert "chokepoint_status=candidate" in a.answer
    assert "insufficient evidence to assess" in a.answer.lower()
