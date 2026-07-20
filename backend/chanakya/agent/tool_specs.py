"""Tool JSON schemas for the LLM tool-calling API (spine/09 tool hygiene; master §4.5).

Per Anthropic's *Writing effective tools*: **few, capable, namespaced** tools; 3–4-sentence descriptions
**with a when-NOT-to-use clause**; unambiguous **typed** params (``node_id`` not ``node``); ``strict``
schemas (``additionalProperties:false``); **``input_examples``** on ``query_graph`` (its constraint list is
nested/format-sensitive); and human-readable IDs on the wire. The functions live in :mod:`chanakya.agent.tools`;
these are just the wire schemas the planner sees. Breadth is served by *composing* the seven, not by adding
narrow tools — ``query_graph`` is the generalist over raw + precomputed materiality attrs.
"""

from __future__ import annotations

from typing import Any


def _spec(name: str, description: str, properties: dict[str, Any], required: list[str], **extra: Any) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "name": f"graph_{name}",
        "description": description.strip(),
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
    }
    schema.update(extra)
    return schema


_CONSTRAINT_ITEM = {
    "type": "object",
    "properties": {
        "attr": {"type": "string", "description": "attribute name: a raw attr, 'status', or a materiality "
                 "attr (chokepoint_status | chokepoint_count | substitutability_state)"},
        "op": {"type": "string", "enum": ["<", "<=", "=", "!=", ">", ">=", "in", "exists", "not_exists"]},
        # A type is MANDATORY here even though the value is polymorphic: the Anthropic API rejects the
        # whole tool list with "tools.N.custom: Schema type is missing" if any property omits it, which
        # takes the entire ReAct agent down the moment a key is present (keyless is unaffected, which is
        # why this survived — the flagship path never exercises it).
        "value": {
            "type": ["number", "string", "boolean", "array"],
            "items": {"type": ["number", "string", "boolean"]},
            "description": "the comparison value (number / string / list); omit for exists/not_exists",
        },
    },
    "required": ["attr", "op"],
    "additionalProperties": False,
}


TOOL_SPECS: list[dict[str, Any]] = [
    _spec(
        "find_entity",
        """
        Resolve a name/designator to candidate node IDs via the alias table + BM25 + fuzzy match, and
        surface any distinct-from siblings (e.g. HQ-9/P vs HQ-9BE) so a near-miss is an explicit
        disambiguation, never a silent wrong bind. Use this FIRST to turn any entity mention in the
        question into a node_id. Do NOT use it to fetch a node's attributes or neighbours (use get_node /
        neighbors) or when you already hold the node_id.
        """,
        {
            "text": {"type": "string", "description": "the name/designator to resolve, e.g. 'HQ-9/P'"},
            "type_hint": {"type": "string", "description": "optional node type to disambiguate, e.g. 'component'"},
        },
        ["text"],
    ),
    _spec(
        "get_node",
        """
        Return one node's attributes, provenance (claim IDs), precomputed materiality attrs, status and
        freshness. Use it once you hold a node_id and want its full detail or to read a materiality attr.
        Do NOT use it to enumerate relationships (use neighbors) or to resolve a name (use find_entity).
        """,
        {"node_id": {"type": "string", "description": "a resolved node id from find_entity/neighbors"}},
        ["node_id"],
    ),
    _spec(
        "neighbors",
        """
        Expand one node's typed relationships (paginated, top-k), returning each neighbour plus the
        supporting claim IDs and freshness for that edge. Use it to walk the graph one hop at a time or to
        list what connects to a node. Do NOT use it to find a full path between two known anchors (use
        find_paths) or to filter a whole node class by attribute (use query_graph).
        """,
        {
            "node_id": {"type": "string"},
            "edge_types": {"type": "array", "items": {"type": "string"},
                           "description": "optional whitelist of edge types to follow"},
            "direction": {"type": "string", "enum": ["in", "out", "both"], "description": "default 'both'"},
            "limit": {"type": "integer", "description": "top-k page size (default 3)"},
            "offset": {"type": "integer", "description": "pagination offset (default 0)"},
        },
        ["node_id"],
    ),
    _spec(
        "find_paths",
        """
        Find the bounded (≤4 hop) relationship chain between two anchor node IDs, returning the ordered
        triple+claim chain — this is the flagship multi-hop trace (battery → … → component maker). Use it
        when the question asks to connect/trace two named things. Do NOT use it for a single hop (use
        neighbors) or when you don't yet have both anchor node_ids (resolve them with find_entity first).
        """,
        {
            "src": {"type": "string"},
            "dst": {"type": "string"},
            "edge_whitelist": {"type": "array", "items": {"type": "string"},
                               "description": "optional edge types the path may use"},
            "max_hops": {"type": "integer", "description": "hop cap, ≤4 (default 4)"},
        },
        ["src", "dst"],
    ),
    _spec(
        "query_graph",
        """
        The generalist: filter/count/aggregate a class of nodes by typed constraints over raw AND
        precomputed materiality attrs, returning matches WITH claim IDs plus a separate 'indeterminate'
        partition (any node whose constrained attr is UNKNOWN/absent — never counted as a negative). Use it
        for "which X satisfy …", counts, and rankings. Do NOT use it to trace a specific path (find_paths)
        or read one node (get_node); do NOT treat 'indeterminate' as a 'no'.
        """,
        {
            "pattern": {"type": "string", "description": "node type to match (e.g. 'component'), or '*' for any"},
            "constraints": {"type": "array", "items": _CONSTRAINT_ITEM,
                            "description": "conjunction of typed constraints"},
            "anchor": {"type": "string", "description": "optional node_id to scope the search within ≤4 hops"},
            "aggregate": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["count", "min", "max", "rank"]},
                    "attr": {"type": "string", "description": "numeric attr for min/max/rank"},
                },
                "required": ["op"],
                "additionalProperties": False,
            },
        },
        ["pattern"],
        input_examples=[
            {"pattern": "component",
             "constraints": [{"attr": "chokepoint_count", "op": "<", "value": 3},
                             {"attr": "substitutability_state", "op": "=", "value": "known-sole-source"}]},
            {"pattern": "component", "anchor": "var_hq9p",
             "constraints": [{"attr": "chokepoint_status", "op": "=", "value": "candidate"}]},
            {"pattern": "component", "constraints": [{"attr": "status", "op": "=", "value": "confirmed"}],
             "aggregate": {"op": "count"}},
        ],
    ),
    _spec(
        "get_evidence",
        """
        Return the exact indicators behind a node or edge — per claim: source (type/grade/bias/url), dates,
        the doc span, credibility, observed-vs-inferred (from the claim's kind), and the corroboration set.
        Use it to CITE a hop/fact one-click-to-source before asserting it. Do NOT use it to discover
        structure (neighbors/find_paths) or to judge sufficiency of missing evidence (check_sufficiency).
        """,
        {"ref_id": {"type": "string", "description": "a node id or edge id to pull evidence for"}},
        ["ref_id"],
    ),
    _spec(
        "check_sufficiency",
        """
        Ask whether a scope (a node/edge id, or a Known-Gap id) has sufficient evidence; an empty/unmet
        scope returns a reasoned insufficiency with the missing slots + next_coverage_due + the Known Gap —
        NEVER a confident negative. Use it whenever a query_graph/neighbors result is empty or lands in the
        indeterminate partition, or when the question asks "what do we NOT know". Do NOT fabricate an answer
        instead of calling this — that is the disqualifying line.
        """,
        {"scope": {"type": "string", "description": "node id, edge id, or Known-Gap id to assess"}},
        ["scope"],
    ),
]


def tool_specs() -> list[dict[str, Any]]:
    """The seven ``graph_*`` tool schemas for the tool-calling API (a fresh copy per call)."""
    return [dict(s) for s in TOOL_SPECS]
