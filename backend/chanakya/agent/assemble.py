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


def _refusal_from_analysis(r: dict) -> RefusalPayload:
    """A first-class :class:`RefusalPayload` from an analysis's ``refusal`` block (kind defaults to
    ``evidence`` — an analysis refusal is a statement about the world's evidence, not the system)."""
    kg = r.get("known_gap")
    known_gap = (
        KnownGap(
            id=kg["id"],
            what_missing=kg.get("what_missing", ""),
            observability_ceiling=kg.get("observability_ceiling", "confirmable"),
            next_coverage_due=kg.get("next_coverage_due"),
            related_ref=kg.get("related_ref"),
            missing_slots=list(kg.get("missing_slots", [])),
        )
        if kg
        else None
    )
    return RefusalPayload(
        kind="evidence",
        missing=list(r.get("missing_slots", [])),
        next_coverage_due=r.get("next_coverage_due"),
        known_gap=known_gap,
        reason=r.get("reason", "insufficient evidence to assess"),
    )


def _from_analyze(trace: AgentTrace, ctx: ToolContext) -> _Built | None:
    """The general-analysis builder (``graph_analyze``): render a chokepoint / supply_chain / sole_source
    result into cited sentences, mirroring the primitive builders' citation discipline exactly.

    A non-null ``refusal`` on the result becomes a first-class :attr:`AgentTrace.refusal` (and returns
    ``None``, so :func:`assemble_answer` re-checks and emits the honest refusal rather than a positive body).
    """
    call = trace.last("analyze")
    if call is None:
        return None
    r = call.result
    analysis = r.get("analysis")
    if r.get("sub_questions"):
        trace.sub_questions = list(r["sub_questions"])
    if r.get("refusal"):
        trace.refusal = _refusal_from_analysis(r["refusal"])
        return None

    built = _Built()
    if analysis == "chokepoint":
        _render_chokepoint(built, ctx, r)
    elif analysis == "supply_chain":
        _render_supply_chain(built, ctx, r)
    elif analysis == "sole_source":
        _render_sole_source(built, ctx, r)
    return built if built.sentences else None


def _cite_ok(ctx: ToolContext, claim_ids: list[str]) -> list[str]:
    """Keep only claim ids that resolve to a real claim (G4) — a sentence citing none is never emitted."""
    return [c for c in claim_ids if c in ctx.claims]


def _emit_hops(built: _Built, ctx: ToolContext, hops: list) -> None:
    """Emit an analysis's internal traversal as the FIRST sentences — one cited hop line per step, in the
    same per-hop format as ``_from_paths`` — so the answer's hop-timeline shows how the finding was reached.
    A hop with no resolvable claim is dropped (G4), keeping ``built.hops`` and the leading sentences aligned
    for the frontend (which reads the first ``len(hops)`` lines as the timeline) and the citation validator."""
    for hop in hops:
        cids = _cite_ok(ctx, list(hop.get("claim_ids", [])))
        if not cids:
            continue
        oi = _kind_of(ctx, cids)
        built.hops.append(
            AnswerHop(
                step=len(built.hops) + 1, edge=hop["edge"], src=hop["src"], dst=hop["dst"],
                claim_ids=cids, observed_or_inferred=oi,
            )
        )
        built.sentences.append(_sentence(f"{_hop_clause(ctx, hop)} — {hop.get('status')}, {oi}", cids))
        built.citations.extend(c for c in cids if c not in built.citations)


def _render_chokepoint(built: _Built, ctx: ToolContext, r: dict) -> None:
    _emit_hops(built, ctx, r.get("hops", []))  # the "how this was traced" timeline first …
    leading = r.get("leading")
    if leading:
        cites = _cite_ok(ctx, list(leading.get("claim_ids", [])))
        if cites:
            gap = leading.get("known_gap")
            gap_clause = f" {gap['what_missing']}" if gap and gap.get("what_missing") else ""
            built.sentences.append(
                _sentence(
                    f"{DERIVED_METRIC_PREFIX} {_name(ctx, leading['node_id'])} — "
                    f"chokepoint_status={leading.get('chokepoint_status')}, "
                    f"substitutability={leading.get('substitutability_state')}.{gap_clause}",
                    cites,
                )
            )
            built.citations.extend(c for c in cites if c not in built.citations)
    for other in r.get("also_nominated", []):
        cites = _cite_ok(ctx, list(other.get("claim_ids", [])))
        if not cites:
            continue
        built.sentences.append(
            _sentence(
                f"{_name(ctx, other['node_id'])} — also nominated "
                f"({other.get('chokepoint_status')}, {other.get('status')})",
                cites,
            )
        )
        built.citations.extend(c for c in cites if c not in built.citations)


def _render_supply_chain(built: _Built, ctx: ToolContext, r: dict) -> None:
    # hops — mirror _from_paths exactly (status + observed/inferred inline; per-hop AnswerHop).
    for i, hop in enumerate(r.get("hops", []), start=1):
        cids = list(hop.get("claim_ids", []))
        oi = _kind_of(ctx, cids)
        built.hops.append(
            AnswerHop(step=i, edge=hop["edge"], src=hop["src"], dst=hop["dst"], claim_ids=cids, observed_or_inferred=oi)
        )
        built.sentences.append(_sentence(f"{_hop_clause(ctx, hop)} — {hop.get('status')}, {oi}", cids))
    built.citations = list(dict.fromkeys(cid for h in built.hops for cid in h.claim_ids))

    # the chokepoint as a rebuild-derived metric line (its open supplier gap appended verbatim).
    ck = r.get("chokepoint")
    if ck:
        refs = _cite_ok(ctx, list(ck.get("claim_ids", [])))
        if refs:
            gap = f" {ck['gap_reason']}".rstrip() if ck.get("gap_reason") else ""
            built.sentences.append(
                _sentence(
                    f"{DERIVED_METRIC_PREFIX} {_name(ctx, ck['node_id'])} — "
                    f"chokepoint_status={ck.get('chokepoint_status')}, "
                    f"substitutability={ck.get('substitutability_state')}.{gap}",
                    refs,
                )
            )
            built.citations.extend(c for c in refs if c not in built.citations)

    # the weighed-and-not-carried links (below-band, printed and cited — never hidden).
    walked = {str(h["edge_id"]) for h in r.get("hops", []) if h.get("edge_id")}
    for w in r.get("weighed_not_carried", []):
        if str(w.get("edge_id", "")) in walked:
            continue
        cites = _cite_ok(ctx, list(w.get("claim_ids", [])))
        if not cites:
            continue
        hop = {"src": w["src"], "dst": w["dst"], "edge": w["edge"], "edge_id": w.get("edge_id", "")}
        built.sentences.append(
            _sentence(
                f"{WEIGHED_NOT_CARRIED_PREFIX} {_hop_clause(ctx, hop)} — {w.get('status')}; below the "
                f"assertable band, so the assessment above does not rest on it",
                cites,
            )
        )
        built.citations.extend(c for c in cites if c not in built.citations)


def _render_sole_source(built: _Built, ctx: ToolContext, r: dict) -> None:
    _emit_hops(built, ctx, r.get("hops", []))  # the traversal to the primary dependency, timeline first …
    for el in r.get("confirmed", []):
        cites = _cite_ok(ctx, list(el.get("claim_ids", [])))
        if not cites:
            continue
        built.sentences.append(_sentence(f"{_name(ctx, el['node_id'])} — sole-source ({el.get('status')})", cites))
        built.citations.extend(c for c in cites if c not in built.citations)
    for el in r.get("candidates", []):
        cites = _cite_ok(ctx, list(el.get("claim_ids", [])))
        if not cites:
            continue
        gap = el.get("known_gap") or {}
        what = gap.get("what_missing") or "substitutability is UNKNOWN — a Known Gap"
        built.sentences.append(_sentence(f"{_name(ctx, el['node_id'])} — candidate sole-source; {what}", cites))
        built.citations.extend(c for c in cites if c not in built.citations)


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


_BUILDERS = (_from_analyze, _from_paths, _from_query_graph, _from_neighbors, _from_get_node, _from_get_evidence)


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

    # An unresolved NAMED subject is a sharper gap than "no path found": the reason should name the query
    # that failed to bind, and — when the linker offered look-alikes — say they are DISTINCT entities, not
    # the one asked about. A find_entity result with ``resolved is False`` (resolution near_miss / ambiguous
    # / none: a candidate list, or nothing, but never a bind) is exactly that. Prefer the LAST such attempt.
    # ``ok_only=False`` because a ``resolution == none`` result carries an ``error`` key (ok is False), and
    # that no-match case is precisely the gap we want to name honestly.
    unresolved = next(
        (c for c in reversed(trace.calls) if c.name == "find_entity" and c.result.get("resolved") is False),
        None,
    )
    if unresolved is not None:
        r = unresolved.result
        query = str(r.get("query") or "").strip()
        closest = [str(c.get("name")) for c in r.get("candidates", []) if c.get("name")][:2]
        if closest:
            look_alikes = " / ".join(f"'{n}'" for n in closest)
            reason = (
                f"No entity matching '{query}' is in the current evidence — the closest matches "
                f"({look_alikes}) are distinct entities, not the one asked about. This subject isn't "
                f"established yet; ingest the evidence that would name it."
            )
        else:
            reason = (
                f"No entity matching '{query}' is in the current evidence. This subject isn't established "
                f"yet; ingest the evidence that would name it."
            )
        return RefusalPayload(missing=[query or "unresolved_subject"], reason=reason)

    return RefusalPayload(
        missing=["supporting_evidence"],
        reason="Insufficient evidence to assess: no supporting path or indicators were found for this query.",
    )


def _refusal_hops(trace: AgentTrace, ctx: ToolContext) -> tuple[list[AnswerHop], list[str]]:
    """The partial trace a refusal DID establish — the hops from the best hop source (the last
    ``graph_analyze`` result's ``hops``, else the last ``find_paths`` ``hops``) — built with the SAME
    citation discipline as a positive answer: claim ids filtered to real claims (G4), observed/inferred
    read structurally, and a hop whose claims don't resolve dropped. Returned so a refusal can show "how
    far this got" beside the gap **without ever asserting a positive finding** — these are only edges the
    agent actually traced, each cited to a real claim; the refusal verdict stays the message."""
    analyze_call = trace.last("analyze")
    source_hops: list = list(analyze_call.result.get("hops") or []) if analyze_call is not None else []
    if not source_hops:
        fp = trace.last("find_paths")
        source_hops = list(fp.result.get("hops") or []) if fp is not None else []
    hops: list[AnswerHop] = []
    citations: list[str] = []
    for hop in source_hops:
        cids = _cite_ok(ctx, list(hop.get("claim_ids", [])))
        if not cids:  # G4: a hop with no resolvable claim behind it is dropped, never shown uncited
            continue
        hops.append(
            AnswerHop(
                step=len(hops) + 1, edge=hop["edge"], src=hop["src"], dst=hop["dst"],
                claim_ids=cids, observed_or_inferred=_kind_of(ctx, cids),
            )
        )
        citations.extend(c for c in cids if c not in citations)
    return hops, citations


def _as_refusal(trace: AgentTrace, ctx: ToolContext, refusal: RefusalPayload | None = None) -> AskAnswer:
    """A first-class refusal that still CARRIES whatever partial trace the agent established: the hops it
    did walk, cited to real claims, so the UI can show how far it got beside the gap. ``refusal`` falls
    back to the one already set on the trace (an explicit / analysis-promoted refusal)."""
    hops, citations = _refusal_hops(trace, ctx)
    return AskAnswer(
        question=trace.question,
        sub_questions=list(trace.sub_questions),
        hops=hops,
        answer=None,
        citations=citations,
        observed_claims=[c for c in citations if _kind_of(ctx, [c]) == "observed"],
        inferred_claims=[c for c in citations if _kind_of(ctx, [c]) == "inferred"],
        refusal=refusal or trace.refusal,
    )


def assemble_answer(trace: AgentTrace, ctx: ToolContext) -> AskAnswer:
    """Build the cited answer for whatever shape the trace covers, or a first-class refusal."""
    # An explicit scripted refusal (a broken chain) wins over the builders — it names the actual unresolved
    # input, so we never let a positive builder paper over it (AS-2).
    if trace.refusal is not None:
        return _as_refusal(trace, ctx)
    for builder in _BUILDERS:
        built = builder(trace, ctx)
        # A builder (e.g. _from_analyze) may promote an analysis-level refusal to a first-class one; honour
        # it immediately rather than falling through to a weaker positive shape or a generic refusal.
        if trace.refusal is not None:
            return _as_refusal(trace, ctx)
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
    return _as_refusal(trace, ctx, _refusal(trace))
