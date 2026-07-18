"""The bounded ReAct loop + the deterministic fixed hero path (spine/09; master §4.5).

Two execution modes over the same tools:

* :func:`run_react_loop` — a plain ``think → act → observe`` loop (no framework). The LLM plans and emits
  tool calls; the deterministic dispatcher runs each tool and feeds the structured result back; the model
  reads it and, when satisfied, stops. **All counting/filtering/materiality is in the tools** — the model
  never tallies in its head. Bounds: a hard iteration cap and top-k/hop caps enforced *inside* the tools.
* :func:`run_fixed_hero_path` — the near-fixed ``link → gather → query_graph → cite`` plan for the flagship
  query, run as a scripted tool sequence with **no LLM at all**. This is the reproducibility story and the
  keyless / network-safety path; the recorded LLM transcript replays the *same* tool sequence via a
  :class:`~chanakya.agent.client.ScriptedClient`.

Both produce an :class:`AgentTrace` (the tool calls + their results); :mod:`chanakya.agent.assemble` turns a
trace into the cited ``AskAnswer``, so citations are a *by-product of the computation*, not model prose.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .client import LLMClient
from .context import ToolContext
from .tool_specs import tool_specs
from .tools import run_tool

HARD_ITERATION_CAP = 8  # spine/09 bound; the hop/top-k caps live inside the tools

SYSTEM_PROMPT = """\
You are an OSINT analysis agent answering questions over a curated, provenance-tracked knowledge graph.

Rules you must follow:
- You are a PLANNER. Every set operation, count, filter, path, and materiality lookup is done by the
  graph_* tools — never tally, compare, or judge substitutability in your own head. Call a tool.
- Resolve every entity mention with graph_find_entity before using it; never invent a node_id.
- Cite as you go: after establishing a hop or a fact, you may call graph_get_evidence for its claim IDs.
- When a result is empty or lands in an "indeterminate" partition, call graph_check_sufficiency — return
  a reasoned "insufficient evidence" (what is missing + when coverage is due), NEVER a confident negative
  and NEVER a fabricated answer. UNKNOWN substitutability is a Known Gap, not "no substitute".
- Stop as soon as you have enough evidence to answer; do not loop past what the question needs.
Keep any prose terse — the final cited answer is assembled deterministically from your tool calls.
"""


@dataclass
class RecordedCall:
    """One tool invocation in the trace: what was called, with what, and the structured result."""

    name: str  # bare tool name (no graph_ prefix)
    input: dict[str, Any]
    result: dict[str, Any]


@dataclass
class AgentTrace:
    """The record the answer is assembled from — deterministic given the tool layer."""

    question: str
    sub_questions: list[str] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)
    final_text: str = ""
    terminated: str = "unknown"  # "end_turn" | "max_iters" | "fixed" | "error"

    def last(self, tool: str) -> RecordedCall | None:
        for c in reversed(self.calls):
            if c.name == tool:
                return c
        return None

    def all_of(self, tool: str) -> list[RecordedCall]:
        return [c for c in self.calls if c.name == tool]


# ── free ReAct loop ─────────────────────────────────────────────────────────────────────────

def _bare(name: str) -> str:
    return name[len("graph_") :] if name.startswith("graph_") else name


def run_react_loop(
    ctx: ToolContext,
    question: str,
    llm: LLMClient,
    *,
    max_iters: int = HARD_ITERATION_CAP,
) -> AgentTrace:
    """Drive the LLM ↔ tools loop to a stop, recording every tool call. Deterministic given ``llm``."""
    trace = AgentTrace(question=question)
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    tools = tool_specs()

    for _ in range(max_iters):
        resp = llm.run_turn(system=SYSTEM_PROMPT, messages=messages, tools=tools)
        if resp.stop_reason != "tool_use" or not resp.tool_calls:
            trace.final_text = resp.text
            trace.terminated = "end_turn"
            return trace

        # Echo the assistant turn (text + tool_use blocks) back into the history.
        assistant_content: list[dict[str, Any]] = []
        if resp.text:
            assistant_content.append({"type": "text", "text": resp.text})
        for tc in resp.tool_calls:
            assistant_content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
        messages.append({"role": "assistant", "content": assistant_content})

        # Run each tool, record it, and feed a tool_result block back.
        tool_results: list[dict[str, Any]] = []
        for tc in resp.tool_calls:
            result = run_tool(ctx, tc.name, tc.input)
            trace.calls.append(RecordedCall(name=_bare(tc.name), input=dict(tc.input), result=result))
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tc.id, "content": json.dumps(result, sort_keys=True)}
            )
        messages.append({"role": "user", "content": tool_results})

    trace.terminated = "max_iters"
    return trace


# ── fixed hero path (deterministic, no LLM) ────────────────────────────────────────────────────

HERO_SUB_QUESTIONS = [
    "Which deployed HQ-9/P battery are we tracing, and where is it based?",
    "Which unit operates it, and which variant was inducted into that unit?",
    "Which component is the fire-control chokepoint on that variant, and who manufactures it?",
    "Is that supplier a confirmed sole-source, or an unresolved Known Gap?",
]


def _call(ctx: ToolContext, trace: AgentTrace, tool: str, params: dict[str, Any]) -> dict[str, Any]:
    result = run_tool(ctx, tool, params)
    trace.calls.append(RecordedCall(name=_bare(tool), input=dict(params), result=result))
    return result


def run_fixed_hero_path(ctx: ToolContext, question: str, subject_id: str = "lens-hq9p-pk") -> AgentTrace:
    """The scripted ``link → gather → query_graph → cite`` plan for the flagship trace — no LLM.

    Discovers the chokepoint component and its maker analytically (via the tools), builds the full
    basing→origin path, cites each hop, and checks sufficiency on the component so HT-233 lands as a
    CANDIDATE with its Known Gap — never a confirmed sole-source.
    """
    trace = AgentTrace(question=question, sub_questions=list(HERO_SUB_QUESTIONS), terminated="fixed")
    lens = ctx.config.subjects.as_map().get(subject_id)
    anchors = list(lens.anchors) if lens else ["unit_paad", "site_karachi"]
    site = next((a for a in anchors if a.startswith("site")), anchors[-1])
    variant_anchor = next((a for a in anchors if a.startswith("unit") or a.startswith("var")), anchors[0])

    # link: resolve the variant the question names.
    _call(ctx, trace, "graph_find_entity", {"text": "HQ-9/P", "type_hint": "variant"})

    # gather + query_graph: find the (candidate-or-confirmed) chokepoint component near the subject.
    chokepoints = _call(
        ctx,
        trace,
        "graph_query_graph",
        {
            "pattern": "component",
            "anchor": variant_anchor,
            "constraints": [{"attr": "chokepoint_status", "op": "!=", "value": "none"}],
        },
    )
    pool = chokepoints.get("matches", []) + chokepoints.get("indeterminate", [])
    comp_id = pool[0]["node_id"] if pool else "comp_ht233"

    # who makes it → the origin/destination anchor for the trace.
    makers = _call(ctx, trace, "graph_neighbors", {"node_id": comp_id, "edge_types": ["manufactures"]})
    mfr_id = next((n["neighbour_id"] for n in makers.get("neighbours", [])), "mfr_casic")

    # find_paths: the flagship basing → origin chain.
    _call(ctx, trace, "graph_find_paths", {"src": site, "dst": mfr_id})

    # cite: pull evidence for each hop edge.
    path = trace.last("find_paths")
    if path and "hops" in path.result:
        for hop in path.result["hops"]:
            _call(ctx, trace, "graph_get_evidence", {"ref_id": hop["edge_id"]})

    # non-negotiable: is the chokepoint a confirmed sole-source, or a Known Gap?
    _call(ctx, trace, "graph_get_node", {"node_id": comp_id})
    _call(ctx, trace, "graph_check_sufficiency", {"scope": comp_id})
    return trace
