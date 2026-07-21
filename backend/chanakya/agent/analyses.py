"""Deterministic multi-hop *analyses* — the general analysis capability behind ``graph_analyze``.

The bounded ReAct planner decides *when* an analytical question needs a judgement computed across many
hops/nodes (a critical-dependency assessment, an origin/supply trace, a single-point-of-failure scan) and
calls the one ``graph_analyze`` tool; **this module is where that judgement is actually computed** — in
plain Python over the indexed view, never in the model's head. It replaces the old hardcoded "hero path":
no query is special-cased here, the subject is a parameter, and the flagship trace is just one call of the
general ``supply_chain`` analysis.

Two invariants make the results safe to hand back to the model and to cite:

* **status labels only** — an analysis may consult ``assertion_confidence`` to *rank* internally (which
  chokepoint is best-evidenced, which variant a subject most likely belongs to), but the returned payload
  exposes only status labels (``confirmed`` / ``probable`` / ``candidate`` / ``UNKNOWN`` …), names, and
  **claim ids**. A numeric confidence is never returned to the model.
* **cite-preserving** — every element carries the claim ids behind it (materiality's ``contributing_refs``
  filtered to real claims, falling back to the node's own claims), so the assembled answer's citations are
  a by-product of the computation, and UNKNOWN is always surfaced as a Known Gap, never a confident "no".

Determinism: the analyses call the deterministic tool FUNCTIONS from :mod:`chanakya.agent.tools` directly
(no ``run_tool``, no recorded trace) and reuse the loop's ranking/supplier-link helpers. Given the same
view they return the same result. ``graph_analyze`` dispatches here via :func:`analyze`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # avoid an import cycle at module load (tools imports this module)
    from chanakya.agent.context import ToolContext

_ANALYSES = ("chokepoint", "supply_chain", "sole_source")


# ── shared element helpers (no tool/loop imports — pure reads over the view) ─────────────────────

def _evidence_claims(ctx: ToolContext, node: Any) -> list[str]:
    """The claim ids that back an element — materiality's ``contributing_refs`` (which carry edge ids too)
    filtered to real CLAIMS, falling back to the node's own claim ids. A citation MUST resolve to a claim
    or the validator flags ``citation_missing`` and withholds the whole answer."""
    mat = node.materiality
    refs = [r for r in (list(mat.contributing_refs) if mat else []) if r in ctx.claims]
    if not refs:
        refs = [c for c in node.claim_ids if c in ctx.claims]
    return refs


def _element(ctx: ToolContext, node: Any) -> dict[str, Any]:
    """One node as a status-labelled element — names + status labels + claim ids, never a confidence number."""
    mat = node.materiality
    return {
        "node_id": node.id,
        "name": ctx.display_name(node.id),
        "type": node.type,
        "status": node.status,
        "chokepoint_status": mat.chokepoint_status if mat is not None else None,
        "substitutability_state": mat.substitutability_state if mat is not None else None,
        "claim_ids": list(node.claim_ids),
    }


def _known_gap(ctx: ToolContext, node_id: str) -> dict[str, Any] | None:
    """The Known Gap hanging off ``node_id`` (by ``related_ref`` or the materiality gap id), as a dict."""
    target = f"gap:chokepoint:{node_id}"
    for g in ctx.view.known_gaps:
        if g.related_ref == node_id or g.id == target:
            return {
                "id": g.id,
                "what_missing": g.what_missing,
                "observability_ceiling": g.observability_ceiling,
                "next_coverage_due": g.next_coverage_due,
                "related_ref": g.related_ref,
                "missing_slots": list(g.missing_slots),
            }
    return None


# ── internal ranking / scoping helpers (may read confidence INTERNALLY, never return it) ─────────

def _active_lens(ctx: ToolContext) -> Any:
    """The lens in force for this view — the one named in ``view.meta['subject_lens']`` if present,
    otherwise the first configured lens. A supply trace walks its ``trace_lanes`` and anchors on its
    basing site; ``None`` when no lens is configured (then the analysis falls back to the variant)."""
    subs = ctx.config.subjects
    lens_id = (ctx.view.meta or {}).get("subject_lens")
    lens = subs.as_map().get(lens_id) if lens_id else None
    if lens is None and subs.subjects:
        lens = subs.subjects[0]
    return lens


def _variant_rank(ctx: ToolContext, match: dict[str, Any]) -> tuple[float, str]:
    """Best-first sort key for the variant a subject belongs to — highest assessed node confidence, then
    node id (byte-stable). Confidence is used only to CHOOSE; it is never put in the returned result."""
    node = ctx.nodes_by_id.get(str(match.get("node_id", "")))
    conf = node.confidence.assertion_confidence if (node is not None and node.confidence) else None
    return (-(conf or 0.0), str(match.get("node_id", "")))


def _chokepoint_pool(ctx: ToolContext, anchor_id: str) -> list[dict[str, Any]]:
    """The nominated chokepoint components (confirmed OR candidate) near ``anchor_id``, ranked best-first
    by the loop's shared :func:`_chokepoint_rank` — the same ordering the flagship trace used."""
    import chanakya.agent.tools as tools
    from chanakya.agent.loop import _chokepoint_rank

    res = tools.query_graph(
        ctx, pattern="component", anchor=anchor_id,
        constraints=[{"attr": "chokepoint_status", "op": "!=", "value": "none"}],
    )
    pool = list(res.get("matches", [])) + list(res.get("indeterminate", []))
    return sorted(pool, key=lambda m: _chokepoint_rank(ctx, m))


def _weighed_links(ctx: ToolContext, links: list[Any], pivot: str, band: tuple[str, ...]) -> list[dict[str, Any]]:
    """Supplier links the trace gathered but rated BELOW the assertable band — kept, never dropped, so a
    planted false attribution is *seen and named*, not silently filtered. Each carries the pivot it hangs
    off, its status, and its real claim ids (a link with no resolvable claim is dropped — G4)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for link in links:
        if link.status in band or link.edge_id in seen:
            continue
        cites = [c for c in link.claim_ids if c in ctx.claims]
        if not cites:
            continue
        seen.add(link.edge_id)
        out.append({
            "src": pivot, "dst": link.node_id, "edge": link.edge_type,
            "edge_id": link.edge_id, "status": link.status, "claim_ids": cites,
        })
    return out


def _trace_hops(ctx: ToolContext, src: str, dst: str) -> list[dict[str, Any]]:
    """The internal traversal from ``src`` to ``dst`` on the active lens's lanes, as hop dicts (same shape
    as supply_chain's hops). This is the "how this was traced" timeline every analysis shows behind its
    finding. Best-effort: no path (or ``src == dst``) ⇒ ``[]`` — the conclusion stands even when the
    traversal cannot be drawn, so a missing timeline never fails the analysis."""
    import chanakya.agent.tools as tools

    if src == dst:
        return []
    lens = _active_lens(ctx)
    lanes = list(lens.trace_lanes) if (lens is not None and lens.trace_lanes) else None
    try:
        fp = tools.find_paths(ctx, src=src, dst=dst, edge_whitelist=lanes)
    except tools.ToolError:
        return []
    return [
        {
            "src": h["src"], "dst": h["dst"], "edge": h["edge"], "edge_id": h["edge_id"],
            "claim_ids": list(h.get("claim_ids") or []), "status": h.get("status"),
        }
        for h in fp.get("hops", [])
    ]


# ── the three analyses ───────────────────────────────────────────────────────────────────────────

def _chokepoint(ctx: ToolContext, subject_id: str) -> dict[str, Any]:
    """The critical single-point-of-failure component near a subject: the best-evidenced leading nominee
    (with its Known Gap) plus the others also nominated. Empty pool ⇒ an honest insufficiency refusal."""
    name = ctx.display_name(subject_id)
    pool = _chokepoint_pool(ctx, subject_id)
    if not pool:
        return {
            "analysis": "chokepoint", "subject": subject_id, "subject_name": name,
            "leading": None, "also_nominated": [],
            "refusal": {
                "missing_slots": ["chokepoint_component"],
                "reason": (
                    f"No chokepoint component is currently identified near {name} — insufficient evidence "
                    f"to name a critical component."
                ),
                "next_coverage_due": None, "known_gap": None,
            },
        }
    leading_node = ctx.nodes_by_id[pool[0]["node_id"]]
    leading = _element(ctx, leading_node)
    leading["known_gap"] = _known_gap(ctx, leading_node.id)
    leading["claim_ids"] = _evidence_claims(ctx, leading_node)
    also_nominated: list[dict[str, Any]] = []
    for m in pool[1:]:
        n = ctx.nodes_by_id.get(m["node_id"])
        if n is None:
            continue
        el = _element(ctx, n)
        el["claim_ids"] = _evidence_claims(ctx, n)
        also_nominated.append(el)
    # the traversal that reached the leading component — the "how this was traced" timeline.
    hops = _trace_hops(ctx, subject_id, leading_node.id)
    return {
        "analysis": "chokepoint", "subject": subject_id, "subject_name": name,
        "hops": hops, "leading": leading, "also_nominated": also_nominated, "refusal": None,
    }


def _supply_chain(ctx: ToolContext, subject_id: str) -> dict[str, Any]:
    """Trace an observed system/unit/site back toward its origin maker, highlighting the chokepoint.

    Ports the flagship ``link → gather → query_graph → cite`` decision logic, but parameterised by the
    subject node instead of a hardcoded designator + lens id: resolve the variant the subject belongs to,
    find the chokepoint near it, carry the component's own maker if the claiming edge is inside the
    assertable band (else climb to the system's origin maker), and walk the lens's traversal lanes from the
    observed site to that terminus. When the chain cannot reach a carried maker/path, degrade to the SAME
    scoped honest refusal — name the chokepoint, name the supplier gap, carry the Known Gap — never a
    fabricated sole-source.
    """
    import chanakya.agent.tools as tools
    from chanakya.agent.loop import AgentTrace, _supplier_links, _typed_anchor, assertable_statuses

    subj = ctx.nodes_by_id[subject_id]
    name = ctx.display_name(subject_id)
    lens = _active_lens(ctx)

    def _refuse(
        missing: list[str], reason: str, *, due: str | None = None, kg: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "analysis": "supply_chain", "subject": subject_id, "subject_name": name,
            "hops": [], "chokepoint": None, "maker": None, "weighed_not_carried": [], "sub_questions": [],
            "refusal": {"missing_slots": missing, "reason": reason, "next_coverage_due": due, "known_gap": kg},
        }

    # 1. resolve the VARIANT the subject belongs to.
    if subj.type == "variant":
        variant_id: str | None = subject_id
    else:
        vres = tools.query_graph(ctx, pattern="variant", anchor=subject_id)
        vpool = list(vres.get("matches", [])) + list(vres.get("indeterminate", []))
        variant_id = min(vpool, key=lambda m: _variant_rank(ctx, m))["node_id"] if vpool else None
    if variant_id is None:
        return _refuse(["variant"], f"Could not find the system/variant that {name} belongs to in the rebuilt view.")
    variant_name = ctx.display_name(variant_id)

    # 2. resolve the OBSERVED SRC the path starts from.
    if subj.type in ("basing_site", "unit"):
        src = subject_id
    else:
        bs = _typed_anchor(ctx, list(lens.anchors), "basing_site") if lens else None
        src = bs if bs is not None else variant_id

    # 3. the chokepoint near the variant (same pool + ranking as the flagship trace).
    pool = _chokepoint_pool(ctx, variant_id)
    comp_id = pool[0]["node_id"] if pool else None
    comp_node = ctx.nodes_by_id.get(comp_id) if comp_id else None

    # 4. who makes it: the component's own maker if the claiming edge clears the band, else the system origin.
    band = assertable_statuses(ctx)
    scratch = AgentTrace(question="")  # a discardable scratchpad; only the returned links matter
    comp_maker_edge = ctx.lane.canonical_edge("manufacturer", "component") if ctx.lane else None
    component_links = _supplier_links(ctx, scratch, comp_id, comp_maker_edge, "manufacturer") if comp_id else []
    carried = [link for link in component_links if link.status in band]
    origin_links: list[Any] = []
    if not carried:
        origin_edge = ctx.lane.canonical_edge("manufacturer", "variant") if ctx.lane else None
        origin_links = _supplier_links(ctx, scratch, variant_id, origin_edge, "manufacturer")
        carried = [link for link in origin_links if link.status in band]
    mfr_id = carried[0].node_id if carried else None

    dst = mfr_id or comp_id
    if dst is None:
        return _refuse(
            ["variant_maker_or_chokepoint"],
            f"No component or origin maker could be identified to trace {name} back to in the rebuilt view.",
        )

    # the non-negotiable: is the chokepoint's own supplier a confirmed sole-source, or a Known Gap?
    sd: dict[str, Any] = tools.check_sufficiency(ctx, scope=comp_id) if comp_id else {}
    suff_unmet = sd.get("sufficient") is False

    # 5. walk the basing → origin chain on the lens's declared lanes.
    lanes = list(lens.trace_lanes) if (lens is not None and lens.trace_lanes) else None
    try:
        fp = tools.find_paths(ctx, src=src, dst=dst, edge_whitelist=lanes)
        hops = list(fp.get("hops") or [])
        path_error: str | None = None
    except tools.ToolError as exc:
        hops, path_error = [], exc.message

    # When the chain cannot be walked, degrade to the scoped honest refusal (name the actual failure).
    if not hops:
        cname = ctx.display_name(comp_id) if comp_id else name
        missing = list(sd.get("missing_slots") or []) if suff_unmet else []
        kg = sd.get("known_gap") if suff_unmet else None
        due = sd.get("next_coverage_due") if suff_unmet else None
        detail = path_error or "no path found"
        if mfr_id is not None:
            reason = (
                f"Traced the fire-control chokepoint to {cname} and its supplier {ctx.display_name(mfr_id)}, "
                f"but could not connect {ctx.display_name(src)} to that supplier in the rebuilt view: {detail}."
            )
            missing = missing or [f"path:{src}->{mfr_id}"]
        else:
            edge_name = comp_maker_edge or "manufacturer→component"
            below = [link for link in (*component_links, *origin_links) if link.status not in band]
            if below:
                rejected = ", ".join(f"{ctx.display_name(link.node_id)} ({link.status})" for link in below)
                maker_clause = (
                    f"every maker link on {cname} falls below the assertable band "
                    f"({', '.join(band) or 'none declared'}): {rejected}"
                )
            else:
                maker_clause = f"the rebuilt view has no {edge_name} edge to a manufacturer"
            reason = (sd.get("reason") if suff_unmet else None) or (
                f"Traced the fire-control chokepoint to {cname}, but {maker_clause}, and no path connects "
                f"{ctx.display_name(src)} to {cname} either: {detail}."
            )
            missing = missing or [f"{edge_name}:{comp_id}", f"path:{src}->{comp_id}"]
        return _refuse(missing, reason, due=due, kg=kg)

    # positive: the cited chain + the highlighted chokepoint + the below-band links, weighed and not carried.
    chokepoint = None
    if comp_node is not None:
        chokepoint = _element(ctx, comp_node)
        chokepoint["known_gap"] = _known_gap(ctx, comp_node.id)
        chokepoint["claim_ids"] = _evidence_claims(ctx, comp_node)
        chokepoint["gap_reason"] = sd.get("reason") if suff_unmet else None
    maker = _element(ctx, ctx.nodes_by_id[mfr_id]) if mfr_id else None
    weighed = _weighed_links(ctx, component_links, comp_id or variant_id, band) + _weighed_links(
        ctx, origin_links, variant_id, band
    )
    hops_out = [
        {
            "src": h["src"], "dst": h["dst"], "edge": h["edge"], "edge_id": h["edge_id"],
            "claim_ids": list(h.get("claim_ids") or []), "status": h.get("status"),
        }
        for h in hops
    ]
    sub_questions = [
        f"Which system/variant is {name} associated with, and where is it based?",
        "Which unit operates it, and which variant does that unit field?",
        f"Who builds {variant_name} — and which component is the critical dependency on it?",
        "Is that component's own supplier a confirmed sole-source, or an unresolved Known Gap?",
    ]
    return {
        "analysis": "supply_chain", "subject": subject_id, "subject_name": name,
        "hops": hops_out, "chokepoint": chokepoint, "maker": maker,
        "weighed_not_carried": weighed, "sub_questions": sub_questions, "refusal": None,
    }


def _sole_source(ctx: ToolContext, subject_id: str) -> dict[str, Any]:
    """Split a subject's component dependencies into CONFIRMED sole-source (no known alternate) and
    CANDIDATE sole-source (a nominated chokepoint whose substitutability is still UNKNOWN — a Known Gap).
    Both empty ⇒ an honest insufficiency refusal, never a confident "there is no single point of failure"."""
    import chanakya.agent.tools as tools

    name = ctx.display_name(subject_id)
    cres = tools.query_graph(
        ctx, pattern="component", anchor=subject_id,
        constraints=[{"attr": "substitutability_state", "op": "=", "value": "known-sole-source"}],
    )
    confirmed: list[dict[str, Any]] = []
    for m in cres.get("matches", []):
        n = ctx.nodes_by_id.get(m["node_id"])
        if n is None:
            continue
        el = _element(ctx, n)
        el["claim_ids"] = _evidence_claims(ctx, n)
        confirmed.append(el)

    dres = tools.query_graph(
        ctx, pattern="component", anchor=subject_id,
        constraints=[{"attr": "chokepoint_status", "op": "=", "value": "candidate"}],
    )
    candidates: list[dict[str, Any]] = []
    for m in dres.get("matches", []):
        n = ctx.nodes_by_id.get(m["node_id"])
        if n is None or n.materiality is None or n.materiality.substitutability_state != "UNKNOWN":
            continue
        el = _element(ctx, n)
        el["claim_ids"] = _evidence_claims(ctx, n)
        el["known_gap"] = _known_gap(ctx, n.id)
        candidates.append(el)

    refusal = None
    if not confirmed and not candidates:
        refusal = {
            "missing_slots": ["sole_source_component"],
            "reason": (
                f"No confirmed or candidate sole-source component is identified near {name} — insufficient "
                f"evidence to name a single-source dependency."
            ),
            "next_coverage_due": None, "known_gap": None,
        }
    # a scan can list many dependencies; keep the timeline clean by tracing only to the PRIMARY one
    # (a confirmed sole-source first, else the first candidate) rather than tangling one path per item.
    primary = (confirmed[0] if confirmed else candidates[0] if candidates else None)
    hops = _trace_hops(ctx, subject_id, primary["node_id"]) if primary else []
    return {
        "analysis": "sole_source", "subject": subject_id, "subject_name": name,
        "hops": hops, "confirmed": confirmed, "candidates": candidates, "refusal": refusal,
    }


# ── public dispatch ───────────────────────────────────────────────────────────────────────────

def analyze(ctx: ToolContext, subject_id: str, analysis: str) -> dict[str, Any]:
    """Run one precomputed multi-hop analysis for a resolved subject node (spine/09; C/01/02).

    ``analysis`` ∈ ``chokepoint`` | ``supply_chain`` | ``sole_source``. Error-shaped result (matching the
    other tools) when the subject id is unknown or the analysis name is out of range — the planner reads
    ``error`` + ``suggestion`` and adapts.
    """
    if subject_id not in ctx.nodes_by_id:
        return {"error": f"no node with id '{subject_id}'", "suggestion": "resolve the subject with find_entity first"}
    if analysis not in _ANALYSES:
        return {"error": f"unknown analysis '{analysis}'", "suggestion": "use one of: chokepoint, supply_chain, sole_source"}
    if analysis == "chokepoint":
        return _chokepoint(ctx, subject_id)
    if analysis == "supply_chain":
        return _supply_chain(ctx, subject_id)
    return _sole_source(ctx, subject_id)


def run_analysis(
    ctx: ToolContext, question: str, subject_id: str, analysis: str, *, sub_questions: list[str] | None = None
) -> Any:
    """Deterministic keyless driver: run one analysis and wrap it as a single-call ``AgentTrace`` the
    assembler can turn into a cited answer (or a first-class refusal). This is the reproducible worked-query
    path — the same general analysis the live planner reaches via ``graph_analyze``, with no LLM in the loop.
    """
    from chanakya.agent.loop import AgentTrace, RecordedCall

    result = analyze(ctx, subject_id, analysis)
    trace = AgentTrace(question=question, terminated="fixed")
    if sub_questions:
        trace.sub_questions = list(sub_questions)
    trace.calls.append(
        RecordedCall(name="analyze", input={"subject_id": subject_id, "analysis": analysis}, result=result)
    )
    return trace
