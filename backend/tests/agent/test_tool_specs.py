"""Tool-hygiene acceptance (sessions/ASK.md): strict schemas, when-NOT-to-use clauses, input_examples on
query_graph, typed params, and every spec matching a real dispatcher function."""

from __future__ import annotations

from chanakya.agent.tool_specs import tool_specs
from chanakya.agent.tools import _FUNCS


def test_seven_namespaced_strict_tools() -> None:
    specs = tool_specs()
    assert len(specs) == 7
    for s in specs:
        assert s["name"].startswith("graph_")
        assert s["strict"] is True
        assert s["input_schema"]["additionalProperties"] is False
        # every spec maps to a real dispatcher function
        assert s["name"][len("graph_"):] in _FUNCS


def test_descriptions_have_when_not_to_use() -> None:
    for s in tool_specs():
        desc = s["description"].lower()
        assert "do not use" in desc or "do not" in desc, f"{s['name']} lacks a when-NOT-to-use clause"
        # 3–4 sentence descriptions, not one-liners
        assert desc.count(".") >= 2


def test_query_graph_has_input_examples() -> None:
    qg = next(s for s in tool_specs() if s["name"] == "graph_query_graph")
    assert qg["input_examples"]
    for ex in qg["input_examples"]:
        assert "pattern" in ex


def test_typed_params_use_node_id_not_node() -> None:
    for s in tool_specs():
        props = s["input_schema"]["properties"]
        assert "node" not in props  # typed as node_id/src/dst/ref_id/scope, never bare 'node'
