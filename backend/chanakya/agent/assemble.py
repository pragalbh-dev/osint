"""Assemble an :class:`AskAnswer` from an :class:`~chanakya.agent.loop.AgentTrace` (spine/09; product/03 E).

The answer text is built **deterministically from the tool results**, not from the model's prose — so every
sentence is anchored to the claim IDs the tools returned and the citations are a by-product of the
computation (spine/09: "intelligence lives in the plan and the tools, never in the model aggregating raw
nodes"). Observed-vs-inferred is read structurally from each claim's ``kind``. Breadth comes from covering
the query shapes (multi-hop path, filtered set, 1-hop neighbourhood, point lookup) with the *same* citation
discipline; a genuinely empty / unmet result routes to a first-class refusal — never a fabricated answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chanakya.schemas import AnswerHop, AskAnswer, KnownGap, RefusalPayload

from .context import ToolContext
from .loop import AgentTrace


@dataclass
class _Built:
    """An assembled positive answer body before it becomes an AskAnswer."""

    sentences: list[str] = field(default_factory=list)
    hops: list[AnswerHop] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


def _name(ctx: ToolContext, node_id: str) -> str:
    n = ctx.nodes_by_id.get(node_id)
    return n.name if n and n.name else node_id


def _kind_of(ctx: ToolContext, claim_ids: list[str]) -> str:
    """Observed unless any supporting claim is an inference (structural, from ClaimRecord.kind)."""
    for cid in claim_ids:
        c = ctx.claims.get(cid)
        if c is not None and c.kind == "inference":
            return "inferred"
    return "observed"


def _sentence(text: str, cites: list[str]) -> str:
    return f"{text} [{', '.join(cites)}]" if cites else text


# ── per-shape builders (return None when the shape isn't present / is empty) ────────────────────

def _from_paths(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    call = trace.last("find_paths")
    if call is None or not call.result.get("hops"):
        return None
    built = _Built()
    for i, hop in enumerate(call.result["hops"], start=1):
        cids = list(hop.get("claim_ids", []))
        oi = _kind_of(ctx, cids)
        built.hops.append(
            AnswerHop(step=i, edge=hop["edge"], src=hop["src"], dst=hop["dst"], claim_ids=cids, observed_or_inferred=oi)
        )
        built.sentences.append(
            _sentence(
                f"{_name(ctx, hop['src'])} is linked to {_name(ctx, hop['dst'])} via '{hop['edge']}' "
                f"(status: {hop.get('status')}, {oi})",
                cids,
            )
        )
    built.citations = list(dict.fromkeys(cid for h in built.hops for cid in h.claim_ids))

    node_call = trace.last("get_node")
    if node_call is not None and node_call.result.get("materiality"):
        mat = node_call.result["materiality"]
        comp_id = node_call.result["node_id"]
        refs = list(mat.get("contributing_refs") or node_call.result.get("claim_ids", []))
        suff = next((c for c in trace.all_of("check_sufficiency") if c.result.get("sufficient") is False), None)
        gap = f" — {suff.result.get('reason', '')}" if suff else ""
        built.sentences.append(
            _sentence(
                f"The chokepoint is {_name(ctx, comp_id)} ({comp_id}): chokepoint_status="
                f"{mat.get('chokepoint_status')}, substitutability={mat.get('substitutability_state')}{gap}",
                refs,
            )
        )
        built.citations.extend(c for c in refs if c not in built.citations)
    return built


def _from_query_graph(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    call = trace.last("query_graph")
    if call is None:
        return None
    matches = call.result.get("matches", [])
    indet = call.result.get("indeterminate", [])
    if not matches and not indet:
        return None  # genuinely empty → let the refusal path own it (empty ≠ "no")
    built = _Built()
    for m in matches:
        cids = list(m.get("claim_ids", []))
        built.sentences.append(_sentence(f"{_name(ctx, m['node_id'])} ({m['node_id']}) matches the criteria", cids))
        built.citations.extend(c for c in cids if c not in built.citations)
    for m in indet:
        cids = list(m.get("claim_ids", []))
        attrs = ", ".join(str(x.get("attr")) for x in m.get("indeterminate_on", []))
        built.sentences.append(
            _sentence(
                f"{_name(ctx, m['node_id'])} ({m['node_id']}) is INDETERMINATE on {attrs} — a Known Gap, "
                f"not a negative",
                cids,
            )
        )
        built.citations.extend(c for c in cids if c not in built.citations)
    return built


def _from_neighbors(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    call = trace.last("neighbors")
    if call is None or not call.result.get("neighbours"):
        return None
    pivot = call.input.get("node_id", call.result.get("node_id", ""))
    built = _Built()
    for nb in call.result["neighbours"]:
        cids = list(nb.get("claim_ids", []))
        built.sentences.append(
            _sentence(
                f"{_name(ctx, pivot)} — {nb['edge_type']} — {nb.get('neighbour_name') or nb['neighbour_id']} "
                f"(status: {nb.get('status')})",
                cids,
            )
        )
        built.citations.extend(c for c in cids if c not in built.citations)
    return built


def _from_get_node(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    call = trace.last("get_node")
    if call is None:
        return None
    r = call.result
    cids = list(r.get("claim_ids", []))
    extra = ""
    if r.get("materiality"):
        mat = r["materiality"]
        extra = (
            f"; chokepoint_status={mat.get('chokepoint_status')}, "
            f"substitutability={mat.get('substitutability_state')}"
        )
    built = _Built()
    built.sentences.append(
        _sentence(f"{_name(ctx, r['node_id'])} ({r['node_id']}) is a {r.get('type')} (status: {r.get('status')}){extra}", cids)
    )
    built.citations = list(dict.fromkeys(cids))
    return built


def _from_get_evidence(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    call = trace.last("get_evidence")
    if call is None or not call.result.get("indicators"):
        return None
    built = _Built()
    for ind in call.result["indicators"]:
        if not ind.get("available"):
            continue
        cid = ind["claim_id"]
        built.sentences.append(
            _sentence(
                f"Indicator {cid}: {ind.get('observed_or_inferred')} from source "
                f"{ind['source'].get('source_id')} (grade {ind['source'].get('reliability_grade')})",
                [cid],
            )
        )
        built.citations.append(cid)
    return built or None


_BUILDERS = (_from_paths, _from_query_graph, _from_neighbors, _from_get_node, _from_get_evidence)


# ── refusal ─────────────────────────────────────────────────────────────────────────────────

def _refusal(trace: AgentTrace) -> RefusalPayload:
    insuff = next((c for c in trace.all_of("check_sufficiency") if c.result.get("sufficient") is False), None)
    if insuff is not None:
        r = insuff.result
        kg = r.get("known_gap")
        known_gap = (
            KnownGap(
                id=kg["id"],
                what_missing=kg["what_missing"],
                observability_ceiling=kg["observability_ceiling"],
                next_coverage_due=kg.get("next_coverage_due"),
                related_ref=kg.get("related_ref"),
                missing_slots=list(kg.get("missing_slots", [])),
            )
            if kg
            else None
        )
        return RefusalPayload(
            missing=list(r.get("missing_slots", [])),
            next_coverage_due=r.get("next_coverage_due"),
            known_gap=known_gap,
            reason=r.get("reason", "insufficient evidence to assess"),
        )
    return RefusalPayload(
        missing=["supporting_evidence"],
        reason="Insufficient evidence to assess: no supporting path or indicators were found for this query.",
    )


def assemble_answer(trace: AgentTrace, ctx: ToolContext) -> AskAnswer:
    """Build the cited answer for whatever shape the trace covers, or a first-class refusal."""
    for builder in _BUILDERS:
        built = builder(trace, ctx)
        if built is not None and built.sentences:
            observed = [c for c in built.citations if _kind_of(ctx, [c]) == "observed"]
            inferred = [c for c in built.citations if _kind_of(ctx, [c]) == "inferred"]
            return AskAnswer(
                question=trace.question,
                sub_questions=list(trace.sub_questions),
                hops=built.hops,
                answer="\n".join(built.sentences),
                citations=built.citations,
                observed_claims=observed,
                inferred_claims=inferred,
            )
    return AskAnswer(
        question=trace.question,
        sub_questions=list(trace.sub_questions),
        answer=None,
        refusal=_refusal(trace),
    )
