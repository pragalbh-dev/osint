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

from rank_bm25 import BM25Okapi

from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    EdgeView,
    GraphView,
    NodeView,
    SourceRegistryEntry,
)

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize(text: str) -> str:
    """Case-fold + collapse whitespace, but **keep** punctuation (hyphen/slash carry designator identity).

    So ``"HQ-9/P" → "hq-9/p"`` and ``"HQ9P" → "hq9p"`` stay *distinct* at the **exact** tier — the gap
    that keeps a look-alike from silently binding. The softer *punctuation-squashed* tier (:func:`squash`)
    is what deliberately folds them back together as a ranked near-miss, never an auto-bind.
    """
    return _WS.sub(" ", text.strip().lower())


def squash(text: str) -> str:
    """The punctuation-squashed key: normalise then strip **every** non-alphanumeric.

    So ``"HQ-9/P" ≡ "HQ-9P" ≡ "HQ 9 P" → "hq9p"``. This single fold is what resolves the demo anchor
    when the extracted node is named ``HQ-9P`` but the analyst types ``HQ-9/P`` — a near-miss with ranked
    candidates, not an exact bind (spine/09 AS-6).
    """
    return _NON_ALNUM.sub("", normalize(text))


@dataclass(frozen=True)
class NameEntry:
    """One searchable surface form for a node (its name, an attr alias, or a config alias-table entry)."""

    norm: str
    node_id: str
    surface: str
    kind: str  # "name" | "attr_alias" | "config_alias"
    squashed: str = ""  # punctuation-squashed form of ``surface`` (the near-miss tier key)


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
    lane: EdgeLaneIndex | None = None          # ontology edge machinery (canonical_edge / traversable_edges)
    traversable: set[str] = field(default_factory=set)  # find_paths' default whitelist (empty → traverse all)
    bm25: BM25Okapi | None = None             # built ONCE over ``names`` (find_entity reuses it per call)
    display_names: dict[str, str] = field(default_factory=dict)  # node id → registry-declared prose name

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
        ctx.lane = EdgeLaneIndex(config.ontology)
        ctx.traversable = set(ctx.lane.traversable_edges())
        ctx.display_names = {
            e.entity_id: e.display_name for e in config.entities.entities if e.display_name
        }
        ctx.names = cls._build_name_index(view, config)
        # BM25 over every searchable surface, built ONCE here (not rebuilt per find_entity call).
        corpus = [e.norm.split() for e in ctx.names]
        ctx.bm25 = BM25Okapi(corpus) if any(corpus) else None
        return ctx

    @staticmethod
    def _build_name_index(view: GraphView, config: ConfigBundle) -> list[NameEntry]:
        entries: list[NameEntry] = []
        surfaces_of: dict[str, set[str]] = defaultdict(set)  # node_id → its normalised name/attr surfaces
        for n in view.nodes:
            if n.name:
                norm = normalize(n.name)
                entries.append(NameEntry(norm=norm, node_id=n.id, surface=n.name, kind="name", squashed=squash(n.name)))
                surfaces_of[n.id].add(norm)
            for alias in n.attrs.get("aliases", []) or []:
                if isinstance(alias, str):
                    entries.append(
                        NameEntry(norm=normalize(alias), node_id=n.id, surface=alias, kind="attr_alias", squashed=squash(alias))
                    )
                    surfaces_of[n.id].add(normalize(alias))
        # config alias table: canonical → aliases. Attach the WHOLE equivalence class (canonical + every
        # alias, INCLUDING the canonical string itself as a searchable surface) to the node that matches
        # ANY member of the class by a normalised surface — not just a node whose *name* == the canonical.
        # The old name-equality rule silently dropped an entire class (e.g. HQ-9/P → FD-2000, HIMADS)
        # whenever the extracted node was named by an alias (HQ-9P) rather than the canonical (spine/09 AS-6).
        for canonical, aliases in config.resolution.alias_table.items():
            members = [canonical, *aliases]
            member_norms = {normalize(m) for m in members}
            target_id = next(
                (nid for nid in sorted(surfaces_of) if surfaces_of[nid] & member_norms), None
            )
            if target_id is None:
                continue
            for m in members:
                entries.append(
                    NameEntry(norm=normalize(m), node_id=target_id, surface=m, kind="config_alias", squashed=squash(m))
                )
        return entries

    def display_name(self, node_id: str) -> str:
        """The name to show an ANALYST for a node — never its internal id if anything better exists.

        Order: the entity registry's ``display_name`` (an analyst-declared prose name, more specific than
        the surface form a document happened to use) → the node's own resolved name → the id as the last
        resort. Ids stay on the structured payload (``AnswerHop.src``/``dst``, citations) for the UI to key
        on; they do not belong in a sentence. The single naming rule for every answer surface.
        """
        declared = self.display_names.get(node_id)
        if declared:
            return declared
        n = self.nodes_by_id.get(node_id)
        return n.name if n is not None and n.name else node_id

    def bm25_scores(self, query_norm: str) -> list[float]:
        """BM25 relevance of ``query_norm`` against every surface in :attr:`names` (index-aligned)."""
        if self.bm25 is None:
            return [0.0] * len(self.names)
        return [float(s) for s in self.bm25.get_scores(query_norm.split())]

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
