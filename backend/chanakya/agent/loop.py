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

from chanakya.schemas import KnownGap, RefusalPayload

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

    @property
    def ok(self) -> bool:
        """True unless the tool returned an error dict — the ONE discriminant at the type-erased boundary.

        ``run_tool`` returns a union (success payload | ``{error, suggestion}``) and nothing else carries
        the tag, so every downstream reader must go through this (spine/09 AS-1). An error-shaped result
        must fall through to the honest-refusal path, never be read as a success payload.
        """
        return "error" not in self.result


@dataclass
class AgentTrace:
    """The record the answer is assembled from — deterministic given the tool layer."""

    question: str
    sub_questions: list[str] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)
    final_text: str = ""
    terminated: str = "unknown"  # "end_turn" | "max_iters" | "fixed" | "error"
    # An explicit, first-class honest refusal set by a scripted path when the chain cannot be built —
    # assembled verbatim (naming the actual unresolved input), never inferred from a positive builder.
    refusal: RefusalPayload | None = None

    def last(self, tool: str, ok_only: bool = True) -> RecordedCall | None:
        """The most recent call to ``tool`` — SUCCESSFUL ones only by default (AS-1). A failed call is
        never handed to a builder that reads success fields; pass ``ok_only=False`` to see failures."""
        for c in reversed(self.calls):
            if c.name == tool and (c.ok or not ok_only):
                return c
        return None

    def all_of(self, tool: str, ok_only: bool = True) -> list[RecordedCall]:
        return [c for c in self.calls if c.name == tool and (c.ok or not ok_only)]

    def failures(self) -> list[RecordedCall]:
        """Every tool call that returned an error dict (for honest-refusal construction / diagnostics)."""
        return [c for c in self.calls if not c.ok]


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


def _refuse(
    trace: AgentTrace,
    missing: list[str],
    reason: str,
    *,
    next_due: str | None = None,
    known_gap: dict[str, Any] | None = None,
) -> AgentTrace:
    """Stamp a first-class honest refusal on the trace and return it (the scripted short-circuit).

    The reason names the *actual* unresolved input; ``missing`` is populated. No hardcoded/phantom id is
    ever substituted — a step that did not resolve becomes a named gap, never a guessed answer (AS-2).
    """
    kg = None
    if isinstance(known_gap, dict) and known_gap.get("id"):
        kg = KnownGap(
            id=known_gap["id"],
            what_missing=known_gap.get("what_missing", ""),
            observability_ceiling=known_gap.get("observability_ceiling", "confirmable"),
            next_coverage_due=known_gap.get("next_coverage_due"),
            related_ref=known_gap.get("related_ref"),
            missing_slots=list(known_gap.get("missing_slots", [])),
        )
    trace.refusal = RefusalPayload(
        missing=list(missing), next_coverage_due=next_due, known_gap=kg, reason=reason
    )
    trace.terminated = "fixed"
    return trace


def _top_candidate(fe_result: dict[str, Any]) -> str | None:
    """The bindable node id from a find_entity result — top candidate iff exact/near_miss (never fuzzy/
    ambiguous/none). Consumes the result the old path discarded (AS-2)."""
    if fe_result.get("error") or fe_result.get("resolution") not in ("exact", "near_miss"):
        return None
    cands = fe_result.get("candidates") or []
    return cands[0]["node_id"] if cands else None


def _typed_anchor(ctx: ToolContext, anchors: list[str], node_type: str) -> str | None:
    """The first lens anchor whose RESOLVED node type matches — typed from the graph, not a string prefix."""
    for a in anchors:
        n = ctx.nodes_by_id.get(a)
        if n is not None and n.type == node_type:
            return a
    return None


def run_fixed_hero_path(ctx: ToolContext, question: str, subject_id: str = "lens-hq9p-pk") -> AgentTrace:
    """The scripted ``link → gather → query_graph → cite`` plan for the flagship trace — no LLM.

    A scripted *plan* computes over the live graph; it does **not** substitute the expected answer. Every
    id is resolved from the rebuilt view (anchors via find_entity, types via the node, the maker edge via
    the ontology's canonical Manufacturer→Component lane) — and any step that fails to resolve
    short-circuits to an HONEST refusal that names the actual unresolved input, never a hardcoded literal
    (spine/09 AS-2). The end-state on a graph where the chain cannot reach the origin maker is a *scoped*
    refusal on the chokepoint component (its supplier is a Known Gap), never a fabricated assessment.
    """
    trace = AgentTrace(question=question, sub_questions=list(HERO_SUB_QUESTIONS), terminated="fixed")
    lens = ctx.config.subjects.as_map().get(subject_id)
    anchors = list(lens.anchors) if lens else []

    # link: resolve the variant the question names — and CONSUME the result (the old path discarded it).
    fe = _call(ctx, trace, "graph_find_entity", {"text": "HQ-9/P", "type_hint": "variant"})
    variant_id = _top_candidate(fe)
    if variant_id is None:
        detail = fe.get("error") or f"resolution={fe.get('resolution')!r} (no bindable candidate)"
        hint = f" {fe.get('suggestion')}" if fe.get("suggestion") else ""
        return _refuse(trace, ["HQ-9/P"], f"Could not resolve the subject variant 'HQ-9/P' in the rebuilt view: {detail}.{hint}")

    # the basing site is a lens anchor typed basing_site — resolved from the graph, never an id prefix.
    site = _typed_anchor(ctx, anchors, "basing_site")
    if site is None:
        unresolved = [a for a in anchors if a not in ctx.nodes_by_id] or anchors or ["<no lens anchors>"]
        return _refuse(
            trace, unresolved,
            f"The subject lens '{subject_id}' has no basing_site anchor present in the rebuilt view "
            f"(anchors {anchors or 'none'} → unresolved {unresolved}); cannot anchor the basing→origin trace.",
        )

    # gather + query_graph: the (candidate-or-confirmed) chokepoint component near the resolved variant.
    chokepoints = _call(
        ctx, trace, "graph_query_graph",
        {"pattern": "component", "anchor": variant_id,
         "constraints": [{"attr": "chokepoint_status", "op": "!=", "value": "none"}]},
    )
    pool = chokepoints.get("matches", []) + chokepoints.get("indeterminate", [])
    if not pool:
        vname = _name(ctx, variant_id)
        return _refuse(
            trace, ["chokepoint_component"],
            f"No chokepoint component is currently identified near {vname} in the rebuilt view "
            f"(materiality has nominated none): insufficient evidence to name the fire-control chokepoint.",
        )
    comp_id = pool[0]["node_id"]

    # who makes it → the canonical Manufacturer→Component edge (supplies-component), derived from the
    # ontology, NOT the literal 'manufactures' (Phase-1 tightened that to Manufacturer→Variant).
    maker_edge = ctx.lane.canonical_edge("manufacturer", "component") if ctx.lane else None
    makers = _call(
        ctx, trace, "graph_neighbors",
        {"node_id": comp_id, **({"edge_types": [maker_edge]} if maker_edge else {})},
    )
    mfr_id: str | None = None
    for nb in makers.get("neighbours", []):
        m = ctx.nodes_by_id.get(nb.get("neighbour_id", ""))
        if m is not None and m.type == "manufacturer":
            mfr_id = nb["neighbour_id"]
            break

    # find_paths: the flagship basing → origin chain — only when the maker actually resolved.
    if mfr_id is not None:
        _call(ctx, trace, "graph_find_paths", {"src": site, "dst": mfr_id})
        path = trace.last("find_paths")
        if path is not None and path.result.get("hops"):
            for hop in path.result["hops"]:
                _call(ctx, trace, "graph_get_evidence", {"ref_id": hop["edge_id"]})

    # cite the chokepoint + the non-negotiable: confirmed sole-source, or a Known Gap? (comp_id exists.)
    _call(ctx, trace, "graph_get_node", {"node_id": comp_id})
    suff = _call(ctx, trace, "graph_check_sufficiency", {"scope": comp_id})

    # If the chain never reached the origin maker, degrade to an HONEST scoped refusal on the chokepoint —
    # naming the ACTUAL failure (the tool's own error), never a positive answer that hides the gap.
    path = trace.last("find_paths")
    if not (path is not None and path.result.get("hops")):
        cname = _name(ctx, comp_id)
        missing = list(suff.get("missing_slots") or [])
        if mfr_id is not None:
            # supplier resolved, but the basing→origin chain could not be traced — name the path failure.
            fp = trace.last("find_paths", ok_only=False)
            detail = fp.result.get("error") if fp is not None else "no path found"
            reason = (
                f"Traced the fire-control chokepoint to {cname} and its supplier {_name(ctx, mfr_id)}, but "
                f"could not connect the basing site {_name(ctx, site)} to that supplier in the rebuilt view: {detail}."
            )
            missing = missing or [f"path:{site}->{mfr_id}"]
        else:
            edge_name = maker_edge or "manufacturer→component"
            reason = suff.get("reason") or (
                f"Traced the fire-control chokepoint to {cname}, but the rebuilt view has no {edge_name} "
                f"edge to a manufacturer, so the component's origin maker is unresolved."
            )
            missing = missing or [f"{edge_name}:{comp_id}"]
        return _refuse(trace, missing, reason, next_due=suff.get("next_coverage_due"), known_gap=suff.get("known_gap"))
    return trace


def _name(ctx: ToolContext, node_id: str) -> str:
    n = ctx.nodes_by_id.get(node_id)
    return n.name if (n is not None and n.name) else node_id
