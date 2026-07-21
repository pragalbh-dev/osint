"""The seven deterministic ``graph_*`` tools (spine/09, master §4.5) — the analytical engine.

**The one load-bearing principle:** the LLM plans; *these* tools compute. Every set operation, count,
filter, intersection, and materiality lookup happens here, in plain Python over the indexed view — the
model never tallies chokepoints or judges substitutability "in its head". That is what makes the search
both powerful *and* auditable: each tool returns matches **with the claim IDs** that back them, so the
answer's citations are a by-product of the computation, not a post-hoc decoration.

Determinism: stable sorts, an explicit ``indeterminate`` partition (``UNKNOWN`` is never dropped and never
counted as a negative — the disqualifying line), and no LLM/network/clock. Breadth comes from *composing*
these seven (spine/09 taxonomy), not from a tool per question — ``query_graph`` is the generalist.

Public surface: the ``graph_*`` functions + :func:`run_tool` (the dispatcher the loop calls) + the tool
JSON schemas in ``tool_specs`` (imported for the LLM tool-calling API).
"""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz, process

from chanakya.schemas import DateValue, EdgeView, NodeView, canonical_iso_bounds

from . import analyses
from .context import ToolContext, normalize, squash

# ── tuning knobs (agent-local; gate G6 scopes credibility/resolve/materiality/observe, not agent) ──
DEFAULT_TOP_K = 3          # spine/09 beam ≈ 3
MAX_HOPS_CAP = 4           # spine/09 hop cap ≈ 4 (basing→induction→equips→origin)
FUZZY_SUGGEST_CUTOFF = 60  # rapidfuzz WRatio (0–100): below this we don't even suggest
_MATERIALITY_ATTRS = {"chokepoint_status", "chokepoint_count", "substitutability_state"}
_UNKNOWN = "UNKNOWN"


class ToolError(Exception):
    """A recoverable, *actionable* tool error (spine/09 tool hygiene) — the dispatcher renders it as a
    structured ``{error, suggestion}`` the planner can act on, never a stack trace."""

    def __init__(self, message: str, suggestion: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion


# ── shared serialisers ─────────────────────────────────────────────────────────────────────────

def _iso(value: DateValue | None) -> str | None:
    """Latest ISO bound of any date value (pure, offline)."""
    return canonical_iso_bounds(value)[1]


def _attr_value(node: NodeView, attr: str) -> Any:
    """Resolve an attribute for a constraint: materiality attrs → status → raw per-type attrs."""
    if attr in _MATERIALITY_ATTRS:
        return getattr(node.materiality, attr) if node.materiality is not None else None
    if attr == "status":
        return node.status
    return node.attrs.get(attr)


def _node_brief(node: NodeView) -> dict[str, Any]:
    mat = node.materiality
    return {
        "node_id": node.id,
        "type": node.type,
        "name": node.name,
        "status": node.status,
        "claim_ids": list(node.claim_ids),
        "materiality": None
        if mat is None
        else {
            "chokepoint_status": mat.chokepoint_status,
            "chokepoint_count": mat.chokepoint_count,
            "substitutability_state": mat.substitutability_state,
            "contributing_refs": list(mat.contributing_refs),
        },
    }


def _edge_brief(ctx: ToolContext, edge: EdgeView, pivot: str) -> dict[str, Any]:
    other = ctx.other_end(edge, pivot)
    neighbour = ctx.nodes_by_id.get(other)
    return {
        "edge_id": edge.id,
        "edge_type": edge.type,
        "src": edge.source,
        "dst": edge.target,
        "neighbour_id": other,
        "neighbour_name": neighbour.name if neighbour else None,
        "neighbour_type": neighbour.type if neighbour else None,
        "status": edge.status,
        "claim_ids": list(edge.claim_ids),
        "freshness": None
        if edge.freshness is None
        else {"last_support_time": edge.freshness.last_support_time, "decay_factor": edge.freshness.decay_factor},
    }


def _resolve_claim(ctx: ToolContext, claim_id: str, credibility: float | None = None) -> dict[str, Any]:
    """Full provenance for one claim — the one-click-to-source payload feeding citations + the badge."""
    c = ctx.claims.get(claim_id)
    if c is None:
        return {"claim_id": claim_id, "available": False}
    src = ctx.sources.get(c.source_id)
    doc = c.doc_refs()[0]
    observed = {"observation": "observed", "inference": "inferred", "retraction": "retraction"}[c.kind]
    return {
        "claim_id": claim_id,
        "available": True,
        "kind": c.kind,
        "polarity": c.polarity,
        "observed_or_inferred": observed,  # STRUCTURAL — read from kind, never guessed
        "source": {
            "source_id": c.source_id,
            "source_type": src.source_type if src else None,
            "reliability_grade": src.reliability_grade if src else None,
            "bias_vector": src.bias_vector if src else None,
            "url": src.citation_url if src else None,
        },
        "event_time": _iso(c.event_time),
        "report_time": _iso(c.report_time),
        "doc_ref": {
            "file": doc.file,
            "span": list(doc.span) if doc.span else None,
            "row": doc.row,
            "page": doc.page,
            "region": doc.region,
        },
        "premises": list(c.premises),
        "credibility": credibility,
    }


# ── 1. find_entity ───────────────────────────────────────────────────────────────────────────

def _distinct_from(ctx: ToolContext, node_id: str) -> list[dict[str, Any]]:
    siblings: list[dict[str, Any]] = []
    for e in ctx.incident_edges(node_id, "both"):
        if e.type == "distinct-from":
            other = ctx.other_end(e, node_id)
            n = ctx.nodes_by_id.get(other)
            siblings.append({"node_id": other, "name": n.name if n else None, "via_claim_ids": list(e.claim_ids)})
    return siblings


def _aliases_of(ctx: ToolContext, node_id: str) -> list[str]:
    """The node's non-name surface forms (attr + config-table aliases), deduped, ≤5."""
    seen: list[str] = []
    for e in ctx.names:
        if e.node_id == node_id and e.kind != "name" and e.surface not in seen:
            seen.append(e.surface)
    return seen[:5]


def _candidate(ctx: ToolContext, node_id: str, score: float, matched_surface: str, how: str) -> dict[str, Any]:
    """A ranked find_entity candidate — self-describing: which surface matched, how it scored, and the
    distinct-from siblings the caller must not confuse it with (the look-alike traps)."""
    n = ctx.nodes_by_id.get(node_id)
    return {
        "node_id": node_id,
        "name": n.name if n else None,
        "type": n.type if n else None,
        "status": n.status if n else None,
        "claim_count": len(n.claim_ids) if n else 0,
        "score": round(float(score), 2),
        "why": {"matched_surface": matched_surface, "how": how},
        "aliases": _aliases_of(ctx, node_id),
        "distinct_from": _distinct_from(ctx, node_id),
    }


def _resolve_result(
    ctx: ToolContext, text: str, candidates: list[dict[str, Any]], resolution: str, *, auto_bindable: bool = True
) -> dict[str, Any]:
    """Assemble a find_entity result and decide ``resolved`` (auto-bind safety).

    Never auto-bind when the winner has more than one candidate (``ambiguous``), when a ``distinct-from``
    sibling of the winner is itself in the candidate set (a planted look-alike → structural veto), or on
    a fuzzy-only hit (``auto_bindable=False`` — suggest, never bind) — spine/09 AS-6.
    """
    if not candidates:
        return {"query": text, "resolution": "none", "resolved": False, "candidates": []}
    cand_ids = {c["node_id"] for c in candidates}
    winner = candidates[0]
    vetoed = bool({s["node_id"] for s in winner["distinct_from"]} & cand_ids)
    if len(candidates) > 1 and resolution in ("exact", "near_miss"):
        resolution = "ambiguous"
    resolved = auto_bindable and resolution in ("exact", "near_miss") and len(candidates) == 1 and not vetoed
    return {"query": text, "resolution": resolution, "resolved": resolved, "candidates": candidates}


def find_entity(ctx: ToolContext, text: str, type_hint: str | None = None) -> dict[str, Any]:
    """Entity linking → a RANKED CANDIDATE LIST (never a raise on a near-miss): exact → punctuation-
    squashed → blended fuzzy+BM25.

    ``resolution`` ∈ ``exact`` | ``near_miss`` | ``ambiguous`` | ``none``. Each candidate is
    self-describing (type/status/claim_count/why/aliases/distinct_from) so a near-miss is answered in
    one turn — the planner (or the fixed hero path) reads the top candidate instead of paying for a
    "did you mean" round-trip. An ``error`` key appears ONLY for ``resolution == none`` (spine/09 AS-6).
    """
    norm = normalize(text)
    sq = squash(text)

    def _keep(node_id: str) -> bool:
        n = ctx.nodes_by_id.get(node_id)
        return type_hint is None or (n is not None and n.type == type_hint)

    # tier 1 — exact by node NAME (punctuation kept). Alias/canonical surfaces are softer tiers below,
    # so an aliased canonical string never masquerades as an exact identity.
    exact_ids: list[str] = []
    for e in ctx.names:
        if e.kind == "name" and e.norm == norm and _keep(e.node_id) and e.node_id not in exact_ids:
            exact_ids.append(e.node_id)
    if exact_ids:
        cands = [_candidate(ctx, nid, 100.0, ctx.nodes_by_id[nid].name or nid, "name == query (exact)")
                 for nid in sorted(exact_ids)]
        return _resolve_result(ctx, text, cands, "exact")

    # tier 2 — punctuation-squashed on ANY surface (HQ-9/P ≡ HQ-9P; also catches exact aliases like HT233).
    squashed: dict[str, tuple[str, str]] = {}  # node_id → (surface, how)
    for e in ctx.names:
        if e.squashed and e.squashed == sq and _keep(e.node_id) and e.node_id not in squashed:
            squashed[e.node_id] = (e.surface, f"punctuation-squashed ({e.kind})")
    if squashed:
        cands = [_candidate(ctx, nid, 95.0, surf, how) for nid, (surf, how) in sorted(squashed.items())]
        return _resolve_result(ctx, text, cands, "near_miss")

    # tier 3 — blended fuzzy + BM25 (prebuilt), suggest-only (never auto-bind a fuzzy hit).
    keep_idx = [i for i, e in enumerate(ctx.names) if _keep(e.node_id)]
    if not keep_idx:
        return {
            "query": text, "resolution": "none", "resolved": False, "candidates": [],
            "error": f"no entity matches '{text}'", "suggestion": "broaden the term or drop type_hint",
        }
    scored: dict[str, tuple[float, str, str]] = {}  # node_id → (fuzzy_score, surface, how)
    choices = [ctx.names[i].norm for i in keep_idx]
    for _match, fscore, ci in process.extract(norm, choices, scorer=fuzz.WRatio, limit=len(choices)):
        e = ctx.names[keep_idx[ci]]
        cur = scored.get(e.node_id)
        if cur is None or fscore > cur[0]:
            scored[e.node_id] = (float(fscore), e.surface, f"fuzzy WRatio {fscore:.0f} on {e.kind}")
    bm = ctx.bm25_scores(norm)
    bm_by_node: dict[str, float] = {}
    for i in keep_idx:
        nid = ctx.names[i].node_id
        v = bm[i] if i < len(bm) else 0.0
        if v > bm_by_node.get(nid, 0.0):
            bm_by_node[nid] = v
    bm_max = max(bm_by_node.values(), default=0.0) or 1.0
    blended: dict[str, tuple[float, str, str]] = {}
    for nid, (fscore, surf, how) in scored.items():
        b = 100.0 * bm_by_node.get(nid, 0.0) / bm_max
        blended[nid] = (0.85 * fscore + 0.15 * b, surf, how)
    ranked = sorted(blended.items(), key=lambda kv: (-kv[1][0], kv[0]))
    top = [(nid, sc, surf, how) for nid, (sc, surf, how) in ranked if sc >= FUZZY_SUGGEST_CUTOFF][:DEFAULT_TOP_K]
    if not top:
        return {
            "query": text, "resolution": "none", "resolved": False, "candidates": [],
            "error": f"no match for '{text}'", "suggestion": "check the designator spelling",
        }
    cands = [_candidate(ctx, nid, sc, surf, how) for nid, sc, surf, how in top]
    return _resolve_result(ctx, text, cands, "near_miss", auto_bindable=False)


# ── 2. get_node ──────────────────────────────────────────────────────────────────────────────

def get_node(ctx: ToolContext, node_id: str) -> dict[str, Any]:
    """A node's attrs + provenance + precomputed materiality + status/freshness (spine/09)."""
    n = ctx.nodes_by_id.get(node_id)
    if n is None:
        raise ToolError(f"no node with id '{node_id}'", suggestion="call find_entity to resolve a name first")
    out = _node_brief(n)
    out["attrs"] = dict(n.attrs)
    out["freshness"] = (
        None
        if n.freshness is None
        else {
            "last_support_time": n.freshness.last_support_time,
            "half_life_days": n.freshness.half_life_days,
            "decay_factor": n.freshness.decay_factor,
        }
    )
    out["confidence"] = None if n.confidence is None else n.confidence.assertion_confidence
    out["sufficiency_satisfied"] = None if n.sufficiency is None else n.sufficiency.satisfied
    if n.location is not None:
        out["location"] = {"raw": n.location.raw, "lat": n.location.wgs84_lat, "lon": n.location.wgs84_lon}
    return out


# ── 3. neighbors ───────────────────────────────────────────────────────────────────────────

def neighbors(
    ctx: ToolContext,
    node_id: str,
    edge_types: list[str] | None = None,
    direction: str = "both",
    limit: int = DEFAULT_TOP_K,
    offset: int = 0,
) -> dict[str, Any]:
    """Typed, paginated top-k expansion — neighbours + supporting claim IDs per edge + edge freshness."""
    if node_id not in ctx.nodes_by_id:
        raise ToolError(f"no node with id '{node_id}'", suggestion="call find_entity first")
    if direction not in {"in", "out", "both"}:
        raise ToolError(f"bad direction '{direction}'", suggestion="use 'in', 'out', or 'both'")
    edges = ctx.incident_edges(node_id, direction)
    if edge_types:
        allow = set(edge_types)
        edges = [e for e in edges if e.type in allow]
    edges.sort(key=lambda e: (e.type, e.id))  # stable, deterministic
    total = len(edges)
    window = edges[offset : offset + max(limit, 0)]
    return {
        "node_id": node_id,
        "direction": direction,
        "total": total,
        "returned": len(window),
        "offset": offset,
        "has_more": offset + len(window) < total,
        "neighbours": [_edge_brief(ctx, e, node_id) for e in window],
    }


# ── 4. find_paths ────────────────────────────────────────────────────────────────────────────

def find_paths(
    ctx: ToolContext,
    src: str,
    dst: str,
    edge_whitelist: list[str] | None = None,
    max_hops: int = MAX_HOPS_CAP,
) -> dict[str, Any]:
    """Bounded multi-hop between two anchors — the flagship trace: the ordered triple+claim chain."""
    if src not in ctx.nodes_by_id:
        raise ToolError(f"no node with id '{src}'", suggestion="call find_entity to resolve src")
    if dst not in ctx.nodes_by_id:
        raise ToolError(f"no node with id '{dst}'", suggestion="call find_entity to resolve dst")
    hop_cap = min(max_hops, MAX_HOPS_CAP)
    # Default the traversable set from the ontology (spine/09 AS-4): a path is a chain of *relations*, so
    # exclude the symmetric resolution/evidence lanes (distinct-from asserts NON-identity; evidenced-by is
    # provenance) unless the caller explicitly widens it. This is the tool default, so the free ReAct loop
    # is covered too — never a literal edge list on any one query.
    if edge_whitelist:
        allow: set[str] | None = set(edge_whitelist)
    elif ctx.traversable:
        allow = set(ctx.traversable)
    else:
        allow = None  # empty/absent ontology → traverse all (no lane info to constrain by)

    # Deterministic BFS over the bidirectional graph; record the first (shortest) path per dst.
    best: list[dict[str, Any]] | None = None
    # frontier items: (current_node, path_edges)
    frontier: list[tuple[str, list[dict[str, Any]]]] = [(src, [])]
    visited = {src}
    depth = 0
    while frontier and depth < hop_cap and best is None:
        depth += 1
        nxt: list[tuple[str, list[dict[str, Any]]]] = []
        for node, path in frontier:
            incident = ctx.incident_edges(node, "both")
            incident.sort(key=lambda e: (e.type, e.id))
            for e in incident:
                if allow is not None and e.type not in allow:
                    continue
                other = ctx.other_end(e, node)
                hop = {
                    "edge": e.type,
                    "src": node,
                    "dst": other,
                    "edge_id": e.id,
                    "claim_ids": list(e.claim_ids),
                    "status": e.status,
                }
                new_path = [*path, hop]
                if other == dst:
                    best = new_path
                    break
                if other not in visited:
                    visited.add(other)
                    nxt.append((other, new_path))
            if best is not None:
                break
        frontier = nxt
    if best is None:
        raise ToolError(
            f"no path from '{src}' to '{dst}' within {hop_cap} hops",
            suggestion="widen edge_whitelist or raise max_hops (≤4), or check the anchors",
        )
    all_claims = sorted({cid for hop in best for cid in hop["claim_ids"]})
    return {"src": src, "dst": dst, "hops": best, "hop_count": len(best), "claim_ids": all_claims}


# ── 5. query_graph (the generalist) ────────────────────────────────────────────────────────────

def _reachable(ctx: ToolContext, anchor: str, max_hops: int) -> list[NodeView]:
    seen = {anchor}
    frontier = [anchor]
    for _ in range(min(max_hops, MAX_HOPS_CAP)):
        nxt = []
        for node in frontier:
            for e in ctx.incident_edges(node, "both"):
                other = ctx.other_end(e, node)
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
    return [ctx.nodes_by_id[nid] for nid in seen if nid in ctx.nodes_by_id]


def _eval_constraint(node: NodeView, c: dict[str, Any]) -> str:
    """Return 'match' | 'excluded' | 'indeterminate' for one constraint on one node."""
    attr = c.get("attr", "")
    op = c.get("op", "=")
    want: Any = c.get("value")
    val: Any = _attr_value(node, attr)
    if op == "exists":
        return "match" if (val is not None and val != _UNKNOWN) else "excluded"
    if op == "not_exists":
        return "match" if (val is None or val == _UNKNOWN) else "excluded"
    # value-bearing operators: missing/UNKNOWN data is *indeterminate*, never a silent negative.
    if val is None or val == _UNKNOWN:
        return "indeterminate"
    if op == "=":
        return "match" if str(val) == str(want) else "excluded"
    if op == "!=":
        return "match" if str(val) != str(want) else "excluded"
    if op == "in":
        return "match" if isinstance(want, list) and val in want else "excluded"
    try:
        lhs, rhs = float(val), float(want)
    except (TypeError, ValueError):
        return "excluded"
    ok = {"<": lhs < rhs, "<=": lhs <= rhs, ">": lhs > rhs, ">=": lhs >= rhs}.get(op)
    if ok is None:
        return "excluded"
    return "match" if ok else "excluded"


def query_graph(
    ctx: ToolContext,
    pattern: str,
    constraints: list[dict[str, Any]] | None = None,
    anchor: str | None = None,
    aggregate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Typed constraint filter over raw + materiality attrs — deterministic count/filter/intersect/rank.

    Returns matches **with claim IDs** and a separate ``indeterminate`` partition (any constrained attr
    that is UNKNOWN/absent) — UNKNOWN is never dropped and never counted as a negative.
    """
    constraints = constraints or []
    if anchor is not None and anchor not in ctx.nodes_by_id:
        raise ToolError(f"no anchor node '{anchor}'", suggestion="call find_entity to resolve the anchor")
    pool = _reachable(ctx, anchor, MAX_HOPS_CAP) if anchor else list(ctx.view.nodes)
    if pattern and pattern != "*":
        pool = [n for n in pool if n.type == pattern]

    matched_nodes: list[NodeView] = []
    indeterminate: list[dict[str, Any]] = []
    for n in sorted(pool, key=lambda x: x.id):
        verdicts = [(c, _eval_constraint(n, c)) for c in constraints]
        if any(v == "excluded" for _c, v in verdicts):
            continue
        undecided = [c for c, v in verdicts if v == "indeterminate"]
        if undecided:
            brief = _node_brief(n)
            brief["indeterminate_on"] = [
                {"attr": c.get("attr"), "op": c.get("op"), "value": c.get("value"),
                 "actual": _attr_value(n, c.get("attr", ""))}
                for c in undecided
            ]
            indeterminate.append(brief)
        else:
            matched_nodes.append(n)

    matches = [_node_brief(n) for n in matched_nodes]
    out: dict[str, Any] = {
        "pattern": pattern,
        "constraints": constraints,
        "matches": matches,
        "indeterminate": indeterminate,
        "match_count": len(matches),
        "indeterminate_count": len(indeterminate),
    }
    if aggregate:
        out["aggregate"] = _aggregate(matched_nodes, aggregate)
    return out


def _aggregate(nodes: list[NodeView], agg: dict[str, Any]) -> dict[str, Any]:
    op = agg.get("op", "count")
    if op == "count":
        return {"op": "count", "result": len(nodes)}
    attr = agg.get("attr", "")
    pairs = [(n.id, _attr_value(n, attr)) for n in nodes]
    numeric = [(nid, float(v)) for nid, v in pairs if isinstance(v, (int, float))]
    if op in {"min", "max"} and numeric:
        chosen = (min if op == "min" else max)(numeric, key=lambda kv: (kv[1], kv[0]))
        return {"op": op, "attr": attr, "node_id": chosen[0], "value": chosen[1]}
    if op == "rank":
        ranked = sorted(numeric, key=lambda kv: (-kv[1], kv[0]))
        return {"op": "rank", "attr": attr, "ranked": [{"node_id": nid, "value": v} for nid, v in ranked]}
    return {"op": op, "attr": attr, "result": None, "note": "no numeric values to aggregate"}


# ── 6. get_evidence ──────────────────────────────────────────────────────────────────────────

def get_evidence(ctx: ToolContext, ref_id: str) -> dict[str, Any]:
    """The exact indicator(s) behind a node/edge — source, date, span, credibility, corroboration set."""
    node = ctx.nodes_by_id.get(ref_id)
    edge = ctx.edges_by_id.get(ref_id)
    el = node or edge
    if el is None:
        raise ToolError(
            f"no node or edge with id '{ref_id}'",
            suggestion="get a valid id from find_entity, neighbors, or find_paths first",
        )
    per_claim = el.confidence.per_claim_credibility if el.confidence else {}
    indicators = [_resolve_claim(ctx, cid, per_claim.get(cid)) for cid in el.claim_ids]
    n_sources = len({i["source"]["source_id"] for i in indicators if i.get("available")})
    return {
        "ref_id": ref_id,
        "ref_kind": "node" if node is not None else "edge",
        "status": el.status,
        "indicators": indicators,
        "corroboration": {"n_sources": n_sources, "n_independent_groups": len(el.supporting_claims)},
        "opposing_claims": list(el.opposing_claims),
    }


# ── 7. check_sufficiency ─────────────────────────────────────────────────────────────────────

class _Blanks(dict):
    """A format mapping that blanks unknown placeholders instead of raising — so an analyst-authored
    template referencing an unexpected slot degrades to a gap in the string, never a crash (extra="allow"
    spirit; a raise would be the only failing surface)."""

    def __missing__(self, key: str) -> str:
        return ""


def _template_slots(require: dict[str, Any]) -> set[str]:
    """The slot NAMES a template requires, from ``all_of`` + ``any_of``.

    Each entry is either a ``{slot: {constraints}}`` dict (config/templates.yaml's real shape) or a bare
    ``slot`` string — the matcher must read both. The old code compared each *string* slot against the
    list of *dicts*, which was always False, so every analyst-authored template was unreachable dead code
    (spine/09 AS-5; CLAUDE.md names these templates as the mechanism enforcing the non-negotiable).
    """
    slots: set[str] = set()
    for entry in list(require.get("all_of", []) or []) + list(require.get("any_of", []) or []):
        if isinstance(entry, dict):
            slots.update(entry.keys())
        elif isinstance(entry, str):
            slots.add(entry)
    return slots


def _render_refusal(ctx: ToolContext, subject: str, missing: list[str], next_due: str | None) -> str:
    """Render the refusal from a config template (fill-in-the-blank; never regenerated prose — G8).

    Fires the first authored template whose required slots intersect ``missing``; both ``{missing}`` and
    ``{missing_slots}`` placeholders are supplied so the fixture and the shipped templates both render.

    With no derivable revisit date, ``{next_coverage_due}`` renders the config's
    ``unscheduled_coverage_phrase`` instead of a bare "unscheduled" — an untasked gap stated as the
    collection requirement it is, never an invented date (the date only ever comes from a source cadence).
    """
    missing_str = ", ".join(missing) if missing else "corroborating coverage"
    due = next_due or ctx.config.templates.unscheduled_coverage_phrase
    fmt = _Blanks(subject=subject, missing=missing_str, missing_slots=missing_str, next_coverage_due=due)
    missing_set = set(missing)
    for tmpl in ctx.config.templates.templates:
        if tmpl.refusal_template and (_template_slots(tmpl.require) & missing_set):
            return tmpl.refusal_template.format_map(fmt)
    return (
        f"Insufficient evidence to assess {subject}: missing {missing_str}. "
        f"Next coverage due {due}."
    )


def check_sufficiency(ctx: ToolContext, scope: str) -> dict[str, Any]:
    """The non-negotiable: empty ≠ "no". An unmet / empty scope → a reasoned Known Gap with
    ``missing_slots`` + ``next_coverage_due``, never a confident negative or a fabrication."""
    el = ctx.nodes_by_id.get(scope) or ctx.edges_by_id.get(scope)
    gaps = [g for g in ctx.view.known_gaps if g.related_ref == scope or g.id == scope]
    # Existence guard (AS-3): match every sibling id-taking tool — an unknown id is a LOOKUP FAILURE, not
    # a fabricated "insufficient evidence" verdict about a phantom node. A KnownGap.id is itself a valid
    # scope (a live gap id like ``gap:HQ-9/P`` is not a node/edge id), so accept it when `gaps` is non-empty.
    if el is None and not gaps:
        raise ToolError(
            f"no node, edge, or known-gap with id '{scope}'",
            suggestion="resolve a real id via find_entity / neighbors / find_paths first",
        )

    satisfied = el is not None and el.sufficiency is not None and el.sufficiency.satisfied and not gaps
    if satisfied:
        assert el is not None and el.sufficiency is not None
        return {
            "scope": scope,
            "sufficient": True,
            "status": el.status,
            "template_id": el.sufficiency.template_id,
        }

    gap = gaps[0] if gaps else None
    suff = el.sufficiency if el is not None else None
    missing = list(gap.missing_slots) if gap else (list(suff.missing_slots) if suff else [])
    next_due = gap.next_coverage_due if gap else (suff.next_coverage_due if suff else None)
    ceiling = gap.observability_ceiling if gap else (suff.ceiling if suff and suff.ceiling else "confirmable")
    known_gap = (
        {
            "id": gap.id,
            "what_missing": gap.what_missing,
            "observability_ceiling": gap.observability_ceiling,
            "next_coverage_due": gap.next_coverage_due,
            "related_ref": gap.related_ref,
            "missing_slots": list(gap.missing_slots),
        }
        if gap
        else None
    )
    return {
        "scope": scope,
        "sufficient": False,
        "known_gap": known_gap,
        "missing_slots": missing,
        "next_coverage_due": next_due,
        "observability_ceiling": ceiling,
        # the refusal is read by an ANALYST — name the subject, not its internal id (the id is already on
        # ``scope``/``known_gap.related_ref`` for the UI to key on).
        "reason": _render_refusal(ctx, ctx.display_name(scope), missing, next_due),
    }


# ── dispatcher ─────────────────────────────────────────────────────────────────────────────────

_REQUIRED: dict[str, list[str]] = {
    "find_entity": ["text"],
    "get_node": ["node_id"],
    "neighbors": ["node_id"],
    "find_paths": ["src", "dst"],
    "query_graph": ["pattern"],
    "get_evidence": ["ref_id"],
    "check_sufficiency": ["scope"],
    "analyze": ["subject_id", "analysis"],
}

_FUNCS = {
    "find_entity": find_entity,
    "get_node": get_node,
    "neighbors": neighbors,
    "find_paths": find_paths,
    "query_graph": query_graph,
    "get_evidence": get_evidence,
    "check_sufficiency": check_sufficiency,
    "analyze": analyses.analyze,
}


def run_tool(ctx: ToolContext, name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Validate + route a single tool call, returning a structured result or an actionable error dict.

    Never raises for a tool-level problem (bad name/params/no-match): the planner reads the ``error`` +
    ``suggestion`` and adapts. Tool names are namespaced ``graph_*`` on the wire; we strip the prefix.
    """
    bare = name[len("graph_") :] if name.startswith("graph_") else name
    fn = _FUNCS.get(bare)
    if fn is None:
        return {"error": f"unknown tool '{name}'", "suggestion": f"use one of: {', '.join(sorted(_FUNCS))}"}
    missing = [p for p in _REQUIRED.get(bare, []) if p not in params or params[p] in (None, "")]
    if missing:
        return {"error": f"{bare} missing required param(s): {', '.join(missing)}", "suggestion": "supply them"}
    try:
        return fn(ctx, **params)  # type: ignore[operator]
    except ToolError as exc:
        return {"error": exc.message, "suggestion": exc.suggestion}
    except TypeError as exc:  # unexpected kwarg / bad shape from the planner
        return {"error": f"{bare} bad arguments: {exc}", "suggestion": "check the tool's input schema"}
