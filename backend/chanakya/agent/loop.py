"""The bounded ReAct loop (spine/09; master §4.5).

:func:`run_react_loop` — a plain ``think → act → observe`` loop (no framework). The LLM plans and emits tool
calls; the deterministic dispatcher runs each tool and feeds the structured result back; the model reads it
and, when satisfied, stops. **All counting/filtering/materiality/analysis is in the tools** — the model
never tallies in its head, and a judgement computed across many hops (a critical-dependency assessment, an
origin/supply trace, a single-point-of-failure scan) is delegated to the one ``graph_analyze`` tool
(:mod:`chanakya.agent.analyses`) rather than special-cased here. Bounds: a hard iteration cap and top-k/hop
caps enforced *inside* the tools.

The loop produces an :class:`AgentTrace` (the tool calls + their results); :mod:`chanakya.agent.assemble`
turns a trace into the cited ``AskAnswer``, so citations are a *by-product of the computation*, not model
prose. The shared ranking/supplier-link helpers below (``_chokepoint_rank``, ``_supplier_links``,
``_typed_anchor``, ``assertable_statuses``) are reused by the deterministic analyses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from chanakya.schemas import RefusalPayload

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

How to read this graph's assessments:
- Every node and edge carries a STATUS. confirmed = independent credible sources agree, briefable as fact. probable = one good look, or an inferred/attribution layer — usable, but call it probable. possible = weak or a single low-grade source — you may name it but must not rest a finding on it. insufficient / indeterminate / UNKNOWN = a Known Gap, NOT a "no" — report what is missing and when coverage is due, never a confident negative.
- Rest a finding only on confirmed or probable links. A weaker link is still worth naming — say it was weighed and not carried, with its source — but the assessment must not depend on it.
- observed = seen or measured directly; inferred = concluded from other facts. Keep the two distinct.
When answering needs a judgement computed across several hops or many nodes — a critical-dependency assessment, an origin or supply trace, a single-point-of-failure scan — call graph_analyze with the analysis type that fits, rather than assembling it by hand. For questions with no matching analysis type, compose the primitive tools.
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


# ── shared scripted helpers (reused by the deterministic analyses in analyses.py) ───────────────

def _call(ctx: ToolContext, trace: AgentTrace, tool: str, params: dict[str, Any]) -> dict[str, Any]:
    result = run_tool(ctx, tool, params)
    trace.calls.append(RecordedCall(name=_bare(tool), input=dict(params), result=result))
    return result


def _typed_anchor(ctx: ToolContext, anchors: list[str], node_type: str) -> str | None:
    """The first lens anchor whose RESOLVED node type matches — typed from the graph, not a string prefix."""
    for a in anchors:
        n = ctx.nodes_by_id.get(a)
        if n is not None and n.type == node_type:
            return a
    return None


def _chokepoint_rank(ctx: ToolContext, match: dict[str, Any]) -> tuple[float, int, str]:
    """Sort key for the nominated chokepoint components — best first under ``min()``.

    Ordering, in priority: (1) highest **assessed node confidence** — an id sort would hand the flagship
    trace whichever node happened to sort first, which on the real graph is a weaker, single-source
    component; (2) among equally-confident candidates, the one whose supporting evidence is the most
    *explanatory* (longest cited document span — a full sourced sentence beats a bare name-drop, so the
    analyst clicking the citation lands on prose that justifies the pick); (3) node id, so the choice is
    byte-stable across runs. Nothing here is graph-specific — no node is named.
    """
    node_id = str(match.get("node_id", ""))
    node = ctx.nodes_by_id.get(node_id)
    conf = node.confidence.assertion_confidence if (node is not None and node.confidence) else None
    claim_ids = list(match.get("claim_ids") or (node.claim_ids if node is not None else []))
    span_len = 0
    for cid in claim_ids:
        claim = ctx.claims.get(cid)
        span = getattr(getattr(claim, "doc_ref", None), "span", None)
        if span and len(span) == 2:
            span_len += max(0, int(span[1]) - int(span[0]))
    return (-(conf or 0.0), -span_len, node_id)


def assertable_statuses(ctx: ToolContext) -> tuple[str, ...]:
    """The assessed statuses an answer may **rest a link on**, strongest first — from config, never a literal.

    ``credibility.assertable_status`` (see ``config/credibility.yaml``). Empty/absent ⇒ an empty tuple,
    which fails **closed**: nothing is assertable on status grounds, so the trace degrades to the honest
    scoped refusal rather than silently reverting to "walk whatever is there".
    """
    declared = getattr(ctx.config.credibility, "assertable_status", None) or []
    return tuple(str(s) for s in declared)


@dataclass(frozen=True)
class SupplierLink:
    """One candidate "X is made/supplied by Y" link, **carrying the status of the edge that claims it**.

    The whole point of the type: the old path took the first neighbour of the right *node* type and threw
    the *edge* away, so a link the system itself had already rated ``insufficient`` was walked as though it
    were a finding (T3b §5). Status travels with the candidate from here on.
    """

    node_id: str
    edge_id: str
    edge_type: str
    status: str | None
    confidence: float | None
    claim_ids: tuple[str, ...]

    def rank(self, band: tuple[str, ...]) -> tuple[int, float, str]:
        """Sort key, best first: position in the configured band → higher confidence → id (byte-stable)."""
        try:
            tier = band.index(self.status) if self.status is not None else len(band)
        except ValueError:
            tier = len(band)
        return (tier, -(self.confidence or 0.0), self.node_id)


def _supplier_links(
    ctx: ToolContext, trace: AgentTrace, node_id: str, lane: str | None, want_type: str
) -> list[SupplierLink]:
    """Every ``want_type`` neighbour of ``node_id`` on ``lane`` — **with** the claiming edge's status.

    Deliberately unfiltered. Filtering here would be the wrong fix for the defect it repairs: a supplier
    attribution that is dropped at the gather step is indistinguishable, in the answer, from one that was
    never published — which is precisely how a planted false attribution wins. The corpus's
    ``d23_cpmiec_false_attribution`` must be *seen, rated and named*, not quietly skipped. The partition
    into carried vs weighed-and-not-carried happens downstream, on the record, and both halves are printed.
    """
    params: dict[str, Any] = {"node_id": node_id}
    if lane:
        params["edge_types"] = [lane]
    result = _call(ctx, trace, "graph_neighbors", params)
    links: list[SupplierLink] = []
    for nb in result.get("neighbours", []):
        neighbour = ctx.nodes_by_id.get(nb.get("neighbour_id", ""))
        if neighbour is None or neighbour.type != want_type:
            continue
        edge = ctx.edges_by_id.get(nb.get("edge_id", ""))
        conf = edge.confidence.assertion_confidence if (edge is not None and edge.confidence) else None
        links.append(
            SupplierLink(
                node_id=str(nb["neighbour_id"]),
                edge_id=str(nb.get("edge_id", "")),
                edge_type=str(nb.get("edge_type", lane or "")),
                status=nb.get("status"),
                confidence=conf,
                claim_ids=tuple(nb.get("claim_ids", []) or []),
            )
        )
    band = assertable_statuses(ctx)
    return sorted(links, key=lambda link: link.rank(band))


def _name(ctx: ToolContext, node_id: str) -> str:
    n = ctx.nodes_by_id.get(node_id)
    return n.name if (n is not None and n.name) else node_id


def _names(ctx: ToolContext, node_ids: list[str]) -> str:
    """Comma-joined human names for analyst-facing prose — an id that resolves reads as its name, one
    that does not falls back to the id itself. Never a Python container repr (R-9)."""
    return ", ".join(_name(ctx, i) for i in node_ids)
