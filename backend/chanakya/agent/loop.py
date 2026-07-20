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
    "Which unit operates it, and which variant does that unit field?",
    "Who builds that system — and which component is the fire-control chokepoint on it?",
    "Is the chokepoint's own supplier a confirmed sole-source, or an unresolved Known Gap?",
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
        unresolved = [a for a in anchors if a not in ctx.nodes_by_id]
        # Analyst-facing prose names *entities*, never a Python list repr or an internal lens id
        # (R-9). The machine-readable ids still travel in `missing`, which the UI resolves itself.
        if unresolved:
            detail = f"these anchors are not present in the rebuilt view: {_names(ctx, unresolved)}"
        elif anchors:
            detail = f"its anchors resolve, but none of them is a basing site: {_names(ctx, anchors)}"
        else:
            detail = "the lens declares no anchors at all"
        return _refuse(
            trace, unresolved or anchors or ["basing_site_anchor"],
            f"The current subject lens has no basing site to anchor the basing→origin trace — {detail}.",
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
    comp_id = min(pool, key=lambda m: _chokepoint_rank(ctx, m))["node_id"]

    # Who makes it. Two lanes, both derived from the ontology, never a literal:
    #   1. the chokepoint COMPONENT's own maker — the canonical Manufacturer→Component edge
    #      (supplies-component; Phase-1 tightened 'manufactures' to Manufacturer→Variant);
    #   2. failing that, the SYSTEM's origin maker — Manufacturer→Variant on the resolved variant.
    #
    # A candidate is carried only if the edge that claims it is inside the configured assertable band
    # (credibility.assertable_status). This is the T3b §5 defect: the old code took the first
    # manufacturer-typed neighbour with no regard for edge status, and so walked the corpus's planted
    # `insufficient` CPMIEC attribution as if it were the answer. Everything gathered is kept on the trace
    # either way — the rejected candidates are printed as "weighed and not carried", with their status and
    # citation, so the trap is surfaced rather than hidden (see `_supplier_links`).
    band = assertable_statuses(ctx)
    comp_maker_edge = ctx.lane.canonical_edge("manufacturer", "component") if ctx.lane else None
    component_links = _supplier_links(ctx, trace, comp_id, comp_maker_edge, "manufacturer")
    carried = [link for link in component_links if link.status in band]

    origin_links: list[SupplierLink] = []
    if not carried:
        # Climb from the part to the system: "who supplies this radar" has no assertable answer, but
        # "who builds the system it sits in" is a different — and here far better evidenced — assertion.
        # This is not a substitute answer for the first question: the component-level supplier stays an
        # open Known Gap and is reported as one. It is the next honest link in the same dependency chain.
        origin_edge = ctx.lane.canonical_edge("manufacturer", "variant") if ctx.lane else None
        origin_links = _supplier_links(ctx, trace, variant_id, origin_edge, "manufacturer")
        carried = [link for link in origin_links if link.status in band]
    mfr_id = carried[0].node_id if carried else None

    # find_paths: the flagship basing → origin chain, walked on the lens's declared traversal lanes (a
    # subject is anchors + a traversal pattern). When no maker link clears the band, still trace basing →
    # the chokepoint COMPONENT — the chain the evidence does support — and report the missing supplier as
    # the gap. Refusing outright would throw away a fully-sourced multi-hop answer to punish a known unknown.
    dst = mfr_id if mfr_id is not None else comp_id
    path_params: dict[str, Any] = {"src": site, "dst": dst}
    if lens is not None and lens.trace_lanes:
        path_params["edge_whitelist"] = list(lens.trace_lanes)
    _call(ctx, trace, "graph_find_paths", path_params)
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
            # No assertable maker link AND no basing→component path either — name both, not just the
            # maker gap. When maker links WERE found but all fell below the assertable band, say so in
            # those words: "none was found" and "one was found and is too weak to carry" are different
            # intelligence, and collapsing them would hide the very attribution the analyst must see.
            edge_name = comp_maker_edge or "manufacturer→component"
            fp = trace.last("find_paths", ok_only=False)
            detail = (fp.result.get("error") if fp is not None else None) or "no path found"
            weighed = [link for link in (*component_links, *origin_links) if link.status not in band]
            if weighed:
                rejected = ", ".join(
                    f"{_name(ctx, link.node_id)} ({link.status})" for link in weighed
                )
                maker_clause = (
                    f"every maker link on {cname} falls below the assertable band "
                    f"({', '.join(band) or 'none declared'}): {rejected}"
                )
            else:
                maker_clause = f"the rebuilt view has no {edge_name} edge to a manufacturer"
            reason = suff.get("reason") or (
                f"Traced the fire-control chokepoint to {cname}, but {maker_clause}, and no path connects "
                f"the basing site {_name(ctx, site)} to {cname} either: {detail}."
            )
            missing = missing or [f"{edge_name}:{comp_id}", f"path:{site}->{comp_id}"]
        return _refuse(trace, missing, reason, next_due=suff.get("next_coverage_due"), known_gap=suff.get("known_gap"))
    return trace


def _name(ctx: ToolContext, node_id: str) -> str:
    n = ctx.nodes_by_id.get(node_id)
    return n.name if (n is not None and n.name) else node_id


def _names(ctx: ToolContext, node_ids: list[str]) -> str:
    """Comma-joined human names for analyst-facing prose — an id that resolves reads as its name, one
    that does not falls back to the id itself. Never a Python container repr (R-9)."""
    return ", ".join(_name(ctx, i) for i in node_ids)
