"""``ToolContext`` — the indexed, read-only view the ``graph_*`` tools run against (owned by ASK).

Built once per :func:`chanakya.agent.ask` call from the ``(view, claims, config)`` triple. It is a pure
index over an *already-rebuilt* view — no LLM, no network, no clock — so every tool is deterministic and
its results (and therefore the citations built from them) are invariant across runs (sessions/ASK.md
acceptance: "tool layer is deterministic"). All ordering is stable-sorted by ``(-score, id)`` / ``id``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    EdgeView,
    GraphView,
    NodeView,
    SourceRegistryEntry,
)

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Case-fold + collapse whitespace, but **keep** punctuation (hyphen/slash carry designator identity).

    So ``"HQ-9/P" → "hq-9/p"`` and ``"HQ9P" → "hq9p"`` stay *distinct* — that gap is exactly what lets
    ``find_entity('HQ9P')`` miss the exact table and fall to the "did you mean 'HQ-9/P'?" suggestion.
    """
    return _WS.sub(" ", text.strip().lower())


@dataclass(frozen=True)
class NameEntry:
    """One searchable surface form for a node (its name, an attr alias, or a config alias-table entry)."""

    norm: str
    node_id: str
    surface: str
    kind: str  # "name" | "attr_alias" | "config_alias"


@dataclass
class ToolContext:
    """Indexed, read-only inputs shared by every tool."""

    view: GraphView
    claims: Mapping[str, ClaimRecord]
    config: ConfigBundle

    nodes_by_id: dict[str, NodeView] = field(default_factory=dict)
    edges_by_id: dict[str, EdgeView] = field(default_factory=dict)
    out_edges: dict[str, list[EdgeView]] = field(default_factory=lambda: defaultdict(list))
    in_edges: dict[str, list[EdgeView]] = field(default_factory=lambda: defaultdict(list))
    names: list[NameEntry] = field(default_factory=list)
    sources: dict[str, SourceRegistryEntry] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        view: GraphView,
        claims: Mapping[str, ClaimRecord],
        config: ConfigBundle,
    ) -> ToolContext:
        ctx = cls(view=view, claims=claims, config=config)
        ctx.nodes_by_id = {n.id: n for n in view.nodes}
        ctx.edges_by_id = {e.id: e for e in view.edges}
        out_edges: dict[str, list[EdgeView]] = defaultdict(list)
        in_edges: dict[str, list[EdgeView]] = defaultdict(list)
        for e in view.edges:
            out_edges[e.source].append(e)
            in_edges[e.target].append(e)
        ctx.out_edges = out_edges
        ctx.in_edges = in_edges
        ctx.sources = config.sources.as_map()
        ctx.names = cls._build_name_index(view, config)
        return ctx

    @staticmethod
    def _build_name_index(view: GraphView, config: ConfigBundle) -> list[NameEntry]:
        entries: list[NameEntry] = []
        name_to_id: dict[str, str] = {}
        for n in view.nodes:
            if n.name:
                norm = normalize(n.name)
                entries.append(NameEntry(norm=norm, node_id=n.id, surface=n.name, kind="name"))
                name_to_id.setdefault(norm, n.id)
            for alias in n.attrs.get("aliases", []) or []:
                if isinstance(alias, str):
                    entries.append(
                        NameEntry(norm=normalize(alias), node_id=n.id, surface=alias, kind="attr_alias")
                    )
        # config alias table: canonical → aliases. Attach an alias to the node whose *name* is that canonical.
        for canonical, aliases in config.resolution.alias_table.items():
            node_id = name_to_id.get(normalize(canonical))
            if node_id is None:
                continue
            for alias in aliases:
                entries.append(
                    NameEntry(norm=normalize(alias), node_id=node_id, surface=alias, kind="config_alias")
                )
        return entries

    # ── traversal helpers ─────────────────────────────────────────────────────────────────────

    def incident_edges(self, node_id: str, direction: str) -> list[EdgeView]:
        """Edges touching ``node_id`` in the requested direction (``out`` | ``in`` | ``both``).

        Edges are stored origin-ward but the graph is traversed bidirectionally (DATA-C reconciliation),
        so ``both`` is the usual choice for a subject trace.
        """
        if direction == "out":
            return list(self.out_edges.get(node_id, []))
        if direction == "in":
            return list(self.in_edges.get(node_id, []))
        return list(self.out_edges.get(node_id, [])) + list(self.in_edges.get(node_id, []))

    def other_end(self, edge: EdgeView, node_id: str) -> str:
        return edge.target if edge.source == node_id else edge.source
