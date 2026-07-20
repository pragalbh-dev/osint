"""Ontology-derived edge machinery — the domain/range re-lane + the extraction enum (D-A).

The edge vocabulary collides with natural language: an LLM reads "the HQ-9/P equips the PAF" as
Variant→Unit, yet ``equips`` is defined Component→Variant; ``manufactures`` and ``supplies-component``
are near-synonyms. The fix (DECISIONS §6 "EVAL" D-A) is to make each *extractor* edge uniquely
determined by its endpoint node types (``from``/``to`` in ``config/ontology.yaml``) and to **re-lane**
every asserted fact onto the edge its endpoints imply — regardless of the verb the model chose —
**rejecting** any fact whose endpoints fit no edge instead of minting an ad-hoc predicate.

Pure + config-driven: the edge names live in the ontology, never hardcoded here (gate G6). This is the
shared mechanism; INGEST calls it at write time (constrain the extraction enum to
:meth:`EdgeLaneIndex.extractor_edges` and re-lane each triple via :meth:`EdgeLaneIndex.relane`), and any
other stage that needs the canonical edge for an endpoint-typed pair can reuse it.
"""

from __future__ import annotations

from dataclasses import dataclass

from chanakya.schemas import OntologyConfig


@dataclass(frozen=True)
class RelaneResult:
    """The outcome of re-laning one asserted ``(predicate, subject_type, object_type)``.

    ``reversed`` is True when the endpoints matched an edge only in the *swapped* order — i.e. the fact
    was written backwards; the caller should swap subject/object as well as adopt ``edge``.
    """

    edge: str | None      # the canonical edge name, or None if rejected (endpoints fit no edge)
    action: str           # "kept" (already canonical) | "relaned" | "rejected"
    reversed: bool = False
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.edge is not None


class EdgeLaneIndex:
    """The ontology's edge domain/range compiled to a deterministic re-lane + the extraction enum.

    Built from :class:`OntologyConfig`. Only ``extractor: true`` edges take part in re-laning (the
    resolution/evidence/derived edges are never LLM-asserted). Because every extractor edge has a unique
    ``(from → to)`` pair, ``canonical_edge`` is an unambiguous lookup; a ``(from, to)`` that maps to more
    than one edge is a vocabulary collision and is surfaced in :attr:`collisions` (a config error to fix,
    never a silent mis-lane).
    """

    def __init__(self, ontology: OntologyConfig) -> None:
        self._by_endpoints: dict[tuple[str, str], str] = {}
        self._extractor: list[str] = []
        self._names: set[str] = set()
        self._ordered: list[str] = []  # declaration order (deterministic accessors)
        self._symmetric: set[str] = set()
        self._endpoints: dict[str, tuple[list[str], list[str]]] = {}
        seen: dict[tuple[str, str], list[str]] = {}
        for e in ontology.edge_types:
            if e.name not in self._names:
                self._ordered.append(e.name)
            self._names.add(e.name)
            if e.symmetric:
                self._symmetric.add(e.name)
            # domain/range is declared on every directional edge, extractor or not — RESOLVE types a
            # triple ENDPOINT from it (RES-1), which is a separate concern from the extraction enum.
            self._endpoints[e.name] = (e.from_types(), e.to_types())
            if not e.extractor:
                continue
            self._extractor.append(e.name)
            for ft in e.from_types():
                for tt in e.to_types():
                    seen.setdefault((ft, tt), []).append(e.name)
                    self._by_endpoints[(ft, tt)] = e.name
        # a (from,to) mapping to >1 extractor edge can't be re-laned by endpoints alone — surface loudly.
        self.collisions: dict[tuple[str, str], list[str]] = {k: v for k, v in seen.items() if len(v) > 1}

    # ── queries ──────────────────────────────────────────────────────────────────────────────────

    def canonical_edge(self, subject_type: str | None, object_type: str | None) -> str | None:
        """The single extractor edge whose ``(from → to)`` matches these endpoint types, or None."""
        if not subject_type or not object_type:
            return None
        return self._by_endpoints.get((subject_type, object_type))

    def endpoint_types(self, predicate: str) -> tuple[list[str], list[str]]:
        """``predicate → (from_types, to_types)`` — the declared domain/range of one edge.

        The endpoint-typing primitive RESOLVE's RES-1 mention-linking uses: a triple's subject *is* an
        instance of the edge's domain and its object an instance of the range, so an endpoint that no
        entity-form claim ever declared can still be minted as a **typed** node rather than ``unknown``.
        Returns ``([], [])`` for an unknown edge and for a symmetric/structural edge that declares
        neither end (``same-as``) — the caller must then leave the endpoint an untyped mention.
        """
        f, t = self._endpoints.get(predicate, ([], []))
        return (list(f), list(t))

    def extractor_edges(self) -> list[str]:
        """The extraction enum — the relationship edges the LLM is allowed to assert (declaration order)."""
        return list(self._extractor)

    def traversable_edges(self) -> list[str]:
        """The edges safe to walk as *directed relations* in a multi-hop trace (declaration order).

        Every declared edge **minus the symmetric lanes** — the resolution lane (``same-as`` /
        ``distinct-from`` / ``coref-same-as`` / ``substitutable-by``) and the evidence/derived lane
        (``evidenced-by`` / ``corroborates`` / ``contradicts`` / ``derived-from`` / ``supersedes``). A
        ``distinct-from`` edge asserts **non**-identity and an evidence edge is provenance, so a path
        through either is a false fact-chain, not a relation (spine/09 AS-4). This is the ontology
        *declaring* which lanes are relations, read by :func:`chanakya.agent.tools.find_paths` as its
        default whitelist — never a hardcoded edge list on any one query.
        """
        return [name for name in self._ordered if name not in self._symmetric]

    def is_known(self, name: str) -> bool:
        """True if ``name`` is any declared edge type (extractor or not)."""
        return name in self._names

    def is_symmetric(self, name: str) -> bool:
        return name in self._symmetric

    # ── the write-time re-lane ─────────────────────────────────────────────────────────────────────

    def relane(
        self, predicate: str | None, subject_type: str | None, object_type: str | None
    ) -> RelaneResult:
        """Re-lane an asserted fact onto the edge its endpoint types imply.

        ``kept`` when the predicate already matches the endpoint-implied edge; ``relaned`` when the
        endpoints imply a *different* (correct) edge than the verb chosen — including the case where the
        fact was written backwards (``reversed=True``, swap the endpoints too); ``rejected`` when the
        endpoint types fit no extractor edge in either order — the caller should flag it (tier-3
        attribute), never invent a predicate. The chosen predicate is only a hint; endpoints are
        authoritative. Fully-typed triples get name + orientation here; :mod:`edge_direction` remains the
        fallback for triples where only one endpoint could be typed.
        """
        canon = self.canonical_edge(subject_type, object_type)
        if canon is not None:
            if predicate == canon:
                return RelaneResult(canon, "kept")
            return RelaneResult(canon, "relaned", reason=f"{predicate!r}@({subject_type}->{object_type}) -> {canon}")
        # the fact may be written backwards — the endpoints in swapped order may name a real edge.
        canon_rev = self.canonical_edge(object_type, subject_type)
        if canon_rev is not None:
            return RelaneResult(canon_rev, "relaned", reversed=True,
                                reason=f"{predicate!r}@({subject_type}->{object_type}) reversed -> {canon_rev}")
        return RelaneResult(None, "rejected", reason=f"no edge for ({subject_type}->{object_type})")
