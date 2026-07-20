"""Assemble an :class:`AskAnswer` from an :class:`~chanakya.agent.loop.AgentTrace` (spine/09; product/03 E).

The answer text is built **deterministically from the tool results**, not from the model's prose — so every
sentence is anchored to the claim IDs the tools returned and the citations are a by-product of the
computation (spine/09: "intelligence lives in the plan and the tools, never in the model aggregating raw
nodes"). Observed-vs-inferred is read structurally from each claim's ``kind``. Breadth comes from covering
the query shapes (multi-hop path, filtered set, 1-hop neighbourhood, point lookup) with the *same* citation
discipline; a genuinely empty / unmet result routes to a first-class refusal — never a fabricated answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from chanakya.schemas import AnswerHop, AskAnswer, KnownGap, RefusalPayload

from .context import ToolContext
from .loop import AgentTrace

# Sentence-class markers shared with the entailment validator. Two sentence classes assert something no
# single cited claim can *entail* by construction, so they must NOT be sent to the NLI judge (they keep
# deterministic citation validation — cited, citation exists, counts real):
#   * DERIVED_METRIC — a value COMPUTED at rebuild() (chokepoint_status, substitutability). Its citations
#     are the contributing evidence, not statements of the metric; no claim "entails" a derived number.
#   * WEIGHED_NOT_CARRIED — a link the answer traversed, rated below the assertable band, and REJECTED. It
#     reports the dismissal of the claim it cites; a claim can never entail its own rejection.
# The validator matches these prefixes, so they are defined here (where the sentences are built) and
# imported there — the two modules already share the sentence↔hop index contract.
DERIVED_METRIC_PREFIX = "Chokepoint:"
WEIGHED_NOT_CARRIED_PREFIX = "Weighed and not carried:"


@dataclass
class _Built:
    """An assembled positive answer body before it becomes an AskAnswer."""

    sentences: list[str] = field(default_factory=list)
    hops: list[AnswerHop] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


def _name(ctx: ToolContext, node_id: str) -> str:
    """The analyst-facing name of a node (registry display name → resolved name → id). Never the raw id
    when anything better exists: an internal id in a sentence is a graph dump, not an answer. The id stays
    on the structured payload (``AnswerHop.src``/``dst``) for the UI and the citation layer."""
    return ctx.display_name(node_id)


def _kind_of(ctx: ToolContext, claim_ids: list[str]) -> str:
    """Observed unless any supporting claim is an inference (structural, from ClaimRecord.kind)."""
    for cid in claim_ids:
        c = ctx.claims.get(cid)
        if c is not None and c.kind == "inference":
            return "inferred"
    return "observed"


# Sentence-case the leading token only when it is an all-lowercase word — i.e. a display name that
# declares a leading article ("the PAF HQ-9B fire unit"). Designators are left alone: "HQ-9/P" and
# "iDEX" do not match (the run must be lowercase up to a word boundary), so no name is ever corrupted.
_LEADING_WORD = re.compile(r"^[a-z]+\b")


def _sentence(text: str, cites: list[str]) -> str:
    if _LEADING_WORD.match(text):
        text = text[0].upper() + text[1:]
    return f"{text} [{', '.join(cites)}]" if cites else text


def _hop_clause(ctx: ToolContext, hop: dict) -> str:
    """One hop as a natural clause driven by the relation's MEANING, not its identifier.

    The wording is analyst-authored config — ``edge_phrasing`` in ``config/templates.yaml``, alongside the
    refusal copy, because it is PRESENTATION (the ontology stays the semantic contract, and no phrase
    literal belongs in this module). It is read in the direction the trace actually walked: a path is
    traversed bidirectionally, so a hop is often entered at the object end and must read ``inverse``
    ("Rahwali airfield **is the basing site of** the unit"), not forward. An edge with no declared phrasing
    degrades to the bare edge name — an analyst-added edge still renders. Rendering only: the edge,
    endpoints, status and citations are untouched.
    """
    src, dst, edge_type = hop["src"], hop["dst"], hop["edge"]
    edge = ctx.edges_by_id.get(hop.get("edge_id", ""))
    forward = edge is None or edge.source == src  # did the walk follow the edge's stored direction?
    subject_node = ctx.nodes_by_id.get(edge.source if edge is not None else src)
    phrase = ctx.config.templates.edge_clause(
        edge_type, forward=forward, from_type=subject_node.type if subject_node else None
    )
    if phrase is None:
        return f"{_name(ctx, src)} — {edge_type} → {_name(ctx, dst)}"
    return f"{_name(ctx, src)} {phrase} {_name(ctx, dst)}"


# ── per-shape builders (return None when the shape isn't present / is empty) ────────────────────

def _weighed_not_carried(trace: AgentTrace, ctx: ToolContext, walked: set[str]) -> list[tuple[str, list[str]]]:
    """Links the trace gathered, rated **below the assertable band**, and did not rest the answer on.

    These are printed, never dropped. A supplier attribution that is silently filtered out is
    indistinguishable — to the analyst reading the answer — from one that was never published, which is
    exactly how a planted false attribution wins (the corpus's ``d23`` CPMIEC conflation, refuted by
    ``d22``). So the honest handling is: traverse it, rate it, name it, cite it, and say it is not carried.

    Reads the *recorded* ``neighbors`` results, so it is generic over any trace that expanded a
    neighbourhood — nothing here knows about a particular node, edge or document. The band comes from
    ``credibility.assertable_status``; with no band declared nothing is reported as rejected (there is no
    bar to have failed). Edges already walked as hops are skipped: a hop states its own status inline.
    """
    band = set(getattr(ctx.config.credibility, "assertable_status", None) or [])
    if not band:
        return []
    out: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for call in trace.all_of("neighbors"):
        pivot = str(call.input.get("node_id") or call.result.get("node_id") or "")
        for nb in call.result.get("neighbours", []):
            edge_id = str(nb.get("edge_id", ""))
            if not edge_id or edge_id in walked or edge_id in seen or nb.get("status") in band:
                continue
            cites = [c for c in nb.get("claim_ids", []) if c in ctx.claims]
            if not cites:  # G4: a sentence without a resolvable claim behind it is never emitted
                continue
            seen.add(edge_id)
            hop = {
                "src": pivot,
                "dst": nb["neighbour_id"],
                "edge": nb["edge_type"],
                "edge_id": edge_id,
            }
            out.append(
                (
                    f"{WEIGHED_NOT_CARRIED_PREFIX} {_hop_clause(ctx, hop)} — {nb.get('status')}; below the "
                    f"assertable band, so the assessment above does not rest on it",
                    cites,
                )
            )
    return out


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
        # status + observed/inferred stay on every hop: confirmed-vs-probable and observed-vs-inferred are
        # structural (spine/01, /04), so they survive the prose pass — terser, never dropped.
        built.sentences.append(_sentence(f"{_hop_clause(ctx, hop)} — {hop.get('status')}, {oi}", cids))
    built.citations = list(dict.fromkeys(cid for h in built.hops for cid in h.claim_ids))

    node_call = trace.last("get_node")
    if node_call is not None and node_call.result.get("materiality"):
        mat = node_call.result["materiality"]
        comp_id = node_call.result["node_id"]
        # ``contributing_refs`` carries claim ids AND edge ids by design (schemas/view.py MaterialityAttrs),
        # but a citation must resolve to a real CLAIM or ``validate_answer`` flags citation_missing and the
        # whole positive answer is withheld as a refusal. Keep only the refs that are claims; fall back to
        # the node's own claim ids when materiality contributed none.
        raw_refs = list(mat.get("contributing_refs") or []) or list(node_call.result.get("claim_ids", []))
        refs = [r for r in raw_refs if r in ctx.claims]
        if not refs:
            refs = [c for c in node_call.result.get("claim_ids", []) if c in ctx.claims]
        suff = next((c for c in trace.all_of("check_sufficiency") if c.result.get("sufficient") is False), None)
        gap = f" {suff.result.get('reason', '')}".rstrip() if suff else ""
        built.sentences.append(
            _sentence(
                f"{DERIVED_METRIC_PREFIX} {_name(ctx, comp_id)} — chokepoint_status={mat.get('chokepoint_status')}, "
                f"substitutability={mat.get('substitutability_state')}.{gap}",
                refs,
            )
        )
        built.citations.extend(c for c in refs if c not in built.citations)

    # The rejected half of the same evidence. Appended AFTER the hops (and after the chokepoint line) so
    # sentence index still aligns with hop index for the citation validator's per-hop support check.
    walked = {str(h.get("edge_id", "")) for h in call.result["hops"]}
    for sentence, cites in _weighed_not_carried(trace, ctx, walked):
        built.sentences.append(_sentence(sentence, cites))
        built.citations.extend(c for c in cites if c not in built.citations)
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
        built.sentences.append(_sentence(f"{_name(ctx, m['node_id'])} matches the criteria", cids))
        built.citations.extend(c for c in cids if c not in built.citations)
    for m in indet:
        cids = list(m.get("claim_ids", []))
        attrs = ", ".join(str(x.get("attr")) for x in m.get("indeterminate_on", []))
        built.sentences.append(
            _sentence(
                f"{_name(ctx, m['node_id'])} is INDETERMINATE on {attrs} — a Known Gap, not a negative",
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
        # a neighbour IS a one-hop trace — render it with the same relation phrasing as a path hop.
        hop = {"src": pivot, "dst": nb["neighbour_id"], "edge": nb["edge_type"], "edge_id": nb.get("edge_id", "")}
        built.sentences.append(_sentence(f"{_hop_clause(ctx, hop)} — {nb.get('status')}", cids))
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
        _sentence(f"{_name(ctx, r['node_id'])} is a {r.get('type')} — {r.get('status')}{extra}", cids)
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
    # An explicit scripted refusal (the hero path could not build the chain) wins over the builders — it
    # names the actual unresolved input, so we never let a positive builder paper over a broken chain (AS-2).
    if trace.refusal is not None:
        return AskAnswer(
            question=trace.question,
            sub_questions=list(trace.sub_questions),
            answer=None,
            refusal=trace.refusal,
        )
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
