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

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from chanakya.schemas import CredibilityConfig, OntologyConfig

_FROM_END = "from"  # default supplier end (supplier == source; the dominant sustainment convention)
_TO_END = "to"

# Freshness classes (config/ontology.yaml `freshness_class`) that DECAY — an edge on one of these must
# have a reachable half-life or it silently scores as eternal (the SC-2 defect). `durable` / `n/a` never
# decay, so they are exempt from the reachability lint. Strings, not scoring numbers (gate G6).
_DECAYING_CLASSES = frozenset({"perishable", "semi-durable", "force-revalidated"})

# The default supersede/relocation instance key: both endpoints (a multi-valued edge — a variant has many
# components, so each object is its own instance). A FUNCTIONAL edge overrides this to `("from",)`.
_DEFAULT_INSTANCE_KEY: tuple[str, ...] = (_FROM_END, _TO_END)

# Per-edge declarations added by RK-LAYER (A2/A4/D12/R1.3) — plain YAML keys (ConfigModel extra="allow").
_INSTANCE_KEY_TAG = "instance_key_tag"
_MATERIALIZES = "materializes"
_REQUIRES_STATED = "requires_stated_endpoints"


@dataclass(frozen=True)
class Materialization:
    """One edge's declared instance materialization (A4 / D-13.6 / spine/13 §5.3).

    ``end`` — which endpoint (``from``/``to``) needs an *instance* even when the mention named only a
    design; ``node_type`` — the instance citizen to materialize there (a **presence**); ``link`` — the
    binding edge drawn from the materialized instance back to the shared design node (``instance-of``).

    **Why this is declared rather than derived.** A2's rule that endpoint *layers* fall out of the declared
    endpoint *types* is true but not sufficient here: ``observed-at``'s declared domain is ``variant`` /
    ``component`` — design types, because that is what an extractor may legitimately emit — while its
    semantics require an instance subject ("equipment was seen at a place" is a dated, located,
    operator-scoped fact). Nothing in the endpoint types can express that gap, so the intent is declared.
    Opt-in is also the fail-safe direction: an edge that declares nothing materializes nothing, so no edge
    type can silently start minting instances.
    """

    end: str
    node_type: str
    link: str


def build_edge_instance_key(
    subject: str,
    predicate: str,
    obj: str,
    ends: tuple[str, ...] = _DEFAULT_INSTANCE_KEY,
    tag: str | None = None,
) -> str:
    """The single definition of the ``edge_instance`` grouping-key string (EVAL RCA §2.1 / D-P4.4).

    ``ends`` names the endpoints that identify the instance: ``("from", "to")`` (default) embeds the object
    so each ``(subject, predicate, object)`` is its own instance — the pre-fix behaviour, byte-identical
    for every non-functional edge. ``("from",)`` drops the object, so a **functional** edge's two targets
    for one subject (a unit's before/after basing site) share one instance and ``view.supersede`` /
    ``observe`` / the co-instance relocation exclusion can all see both — the three mechanisms §2.1 found
    dead. Order is fixed ``edge:<subject>:<predicate>:<object>`` so the default is unchanged on the wire.
    Used by BOTH producers (``resolve.entities.base_ref`` and the ``view.pipeline`` fallback) via
    :meth:`EdgeLaneIndex.edge_instance_key`, so the two can never drift apart again.

    ``tag`` (R1.3 / C1) appends a **sub-bucket** to a functional edge's key, so ``based-at`` is
    single-valued per *(unit, site_type)* rather than per unit: a unit at a garrison and concurrently at a
    forward site is two valid basings, not a relocation. ``None`` ⇒ the untagged key, byte-unchanged.
    """
    parts = ["edge"]
    if _FROM_END in ends:
        parts.append(subject)
    parts.append(predicate)
    if _TO_END in ends:
        parts.append(obj)
    if tag is not None:
        parts.append(tag)
    return ":".join(parts)


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
        self._supplier_end: dict[str, str] = {}  # sustainment edge → which endpoint holds the supplier
        self._freshness_class: dict[str, str] = {}  # edge → its declared ontology freshness class
        self._instance_key: dict[str, tuple[str, ...]] = {}  # edge → endpoints that form its instance key
        self._instance_key_tag: dict[str, str] = {}  # edge → node attr whose value tags the instance key
        self._materializes: dict[str, Materialization] = {}  # edge → its declared instance materialization
        self._requires_stated: dict[str, tuple[str, ...]] = {}  # edge → endpoints a source must have STATED
        seen: dict[tuple[str, str], list[str]] = {}
        for e in ontology.edge_types:
            if e.name not in self._names:
                self._ordered.append(e.name)
            self._names.add(e.name)
            if e.symmetric:
                self._symmetric.add(e.name)
            # freshness_class is declared on every edge (config/ontology.yaml) and drives SCORE's
            # class-level half-life default (D-P4.13/SC-2); read via getattr (ConfigModel extra="allow").
            fclass = getattr(e, "freshness_class", None)
            if isinstance(fclass, str):
                self._freshness_class[e.name] = fclass
            # supplier_end is a plain YAML field (ConfigModel extra="allow"), read for the chokepoint
            # direction (D-P4.7); only from/to are meaningful, anything else is ignored.
            end = getattr(e, "supplier_end", None)
            if isinstance(end, str) and end in (_FROM_END, _TO_END):
                self._supplier_end[e.name] = end
            # instance_key is a plain YAML list (ConfigModel extra="allow"): which endpoints form the
            # supersede/relocation instance key (D-P4.4). Keep only from/to entries, in canonical order;
            # anything else (or empty) falls back to the default at read time.
            ik = getattr(e, "instance_key", None)
            if isinstance(ik, (list, tuple)):
                ends = tuple(k for k in (_FROM_END, _TO_END) if k in ik)
                if ends:
                    self._instance_key[e.name] = ends
            # instance_key_tag (R1.3/C1): a node ATTRIBUTE on the endpoint the key drops, whose value tags
            # the supersede bucket, so `based-at` is single-valued per (unit, site_type) rather than per
            # unit. A plain YAML string (extra="allow"); absent ⇒ untagged (the pre-S2 key).
            tag = getattr(e, _INSTANCE_KEY_TAG, None)
            if isinstance(tag, str) and tag.strip():
                self._instance_key_tag[e.name] = tag.strip()
            # materializes (A4/D-13.6): this edge needs an INSTANCE endpoint the mention may only have
            # named at the design level, so the build mints the instance rather than pointing the edge at
            # the shared design node. Opt-in per edge — an edge declaring nothing mints nothing.
            spec = getattr(e, _MATERIALIZES, None)
            if isinstance(spec, dict):
                end = str(spec.get("end") or _FROM_END)
                node_type = spec.get("node_type")
                link = spec.get("link")
                if end in (_FROM_END, _TO_END) and isinstance(node_type, str) and isinstance(link, str):
                    self._materializes[e.name] = Materialization(end=end, node_type=node_type, link=link)
            # requires_stated_endpoints (D12): endpoints a SOURCE must have declared. An endpoint the build
            # had to materialize does not satisfy it, and the edge is withheld with a named gap rather than
            # asserting a relation no document states.
            req = getattr(e, _REQUIRES_STATED, None)
            if isinstance(req, (list, tuple)):
                ends = tuple(k for k in (_FROM_END, _TO_END) if k in req)
                if ends:
                    self._requires_stated[e.name] = ends
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

    def supplier_end(self, edge_type: str) -> str:
        """Which endpoint of a sustainment edge holds the **supplier** — ``"from"`` (source) or ``"to"``
        (target); the *dependent* end is the other one.

        Declared per-edge in ``config/ontology.yaml`` (``supplier_end``); defaults to ``"from"`` (supplier
        == source, the dominant convention) for any edge that doesn't declare it. Read by
        :func:`chanakya.materiality.precompute` so the sole-source in-degree TEST runs on the dependent
        end while the chokepoint FINDING attaches to the supplier end — one direction of truth for both
        the nomination pass and the dependency-closure pass (``exported-by`` puts the supplier on ``to``).
        """
        return self._supplier_end.get(edge_type, _FROM_END)

    def freshness_class(self, edge_type: str) -> str | None:
        """The ontology ``freshness_class`` declared on an edge — ``perishable`` / ``semi-durable`` /
        ``force-revalidated`` / ``durable`` / ``n/a`` — or ``None`` for an unknown edge (or one that
        declares none).

        The bridge SCORE's freshness lookup uses to fall back to a **class-level** half-life
        (``credibility.half_life_defaults[<class>]``) when no per-edge/variant half-life is configured.
        Without it the declared ``freshness_class`` is dead metadata and a perishable edge with only
        variant sub-keys (``based-at.field``/``.garrison``, never a bare ``based-at``) scores as eternal —
        the SC-2 defect. Config-driven: the class names live in ``config/ontology.yaml`` (gate G6).
        """
        return self._freshness_class.get(edge_type)

    def instance_key(self, edge_type: str) -> tuple[str, ...]:
        """Which endpoints form an edge's supersede/relocation **instance key** — ``("from",)`` for a
        FUNCTIONAL / single-valued-over-time edge (``based-at``: a unit is at one site at a time) or
        ``("from", "to")`` (the default) for a multi-valued edge (a variant has many components).

        Declared per-edge in ``config/ontology.yaml`` (``instance_key: [from]`` / ``[from, to]``). The
        object is IN the default key, so each ``(subject, predicate, object)`` is its own instance; a
        functional edge drops the object so a subject's two targets collapse to one instance and
        ``view.supersede`` can compare them (EVAL RCA §2.1 — the fix that revives supersede / the
        occupancy-crossing detector / the co-instance relocation exclusion at once).
        """
        return self._instance_key.get(edge_type, _DEFAULT_INSTANCE_KEY)

    def instance_key_tag(self, edge_type: str) -> str | None:
        """The node **attribute** whose value sub-buckets this edge's instance key, or ``None`` (R1.3/C1).

        Declared per-edge as ``instance_key_tag: site_type``. It names an attribute on the endpoint the
        functional key *drops*, so ``based-at`` becomes single-valued per *(unit, site_type)*: a unit at a
        garrison and concurrently at a forward field site is **two valid basings**, not a relocation's
        before/after. The previous unit-only key rested explicitly on "the corpus has no such simultaneous
        pair" — a corpus fact standing in for a design decision.
        """
        return self._instance_key_tag.get(edge_type)

    def materializes(self, edge_type: str) -> Materialization | None:
        """This edge's declared instance materialization, or ``None`` (A4/D-13.6). See
        :class:`Materialization` for why it is declared rather than derived from the endpoint types."""
        return self._materializes.get(edge_type)

    def requires_stated_endpoints(self, edge_type: str) -> tuple[str, ...]:
        """Endpoints of this edge a **source must have stated** — ``()`` for the default (D12).

        An endpoint the build had to *materialize* (no entity-form claim ever declared it) does not satisfy
        the requirement: the edge is withheld and a named gap raised, rather than asserting a relation no
        document states. Declared on ``imported-by``, whose object is a receiving *unit* that no customs or
        bill-of-lading document names.
        """
        return self._requires_stated.get(edge_type, ())

    def endpoint_layers(
        self, predicate: str, node_layer: Callable[[str], str | None]
    ) -> tuple[set[str], set[str]]:
        """``predicate → (from_layers, to_layers)`` — the edge's endpoint **layers** (A2).

        Derived, never declared: an endpoint's layer is the layer of the node types the edge already names
        in ``from``/``to``, looked up through ``node_layer`` (``NodeTypeIndex.node_layer``). A polymorphic
        end can legitimately span both layers, hence sets rather than scalars; an end that declares no
        types (a symmetric/structural edge) yields the empty set. This is the read that tells a *holding*
        edge (both ends design) from a layer-*binding* edge — and it is why no edge in the ontology
        declares a layer of its own.
        """
        f, t = self._endpoints.get(predicate, ([], []))
        return (
            {lay for lay in (node_layer(x) for x in f) if lay is not None},
            {lay for lay in (node_layer(x) for x in t) if lay is not None},
        )

    def edge_instance_key(
        self, subject: str, predicate: str, obj: str, tag: str | None = None
    ) -> str:
        """Build the ``edge_instance`` grouping key for a triple, honouring the edge's declared
        :meth:`instance_key`. The ONE key-builder both producers call
        (``resolve.entities.base_ref`` and the ``view.pipeline`` assembly fallback), so a functional edge's
        object is excluded identically on both paths and they can never diverge again (D-P4.4).

        ``tag`` carries the resolved :meth:`instance_key_tag` value when layer routing is on; ``None``
        (the default, and always the case with routing off) reproduces the pre-S2 key byte-for-byte."""
        return build_edge_instance_key(subject, predicate, obj, self.instance_key(predicate), tag)

    def unreachable_half_lives(self, credibility: CredibilityConfig) -> dict[str, str]:
        """Decaying edges with **no reachable half-life** → ``{edge: freshness_class}`` (a config error).

        An edge whose ``freshness_class`` decays (perishable / semi-durable / force-revalidated) but has
        **neither** a bare ``<edge>`` key in ``credibility.half_lives_days`` **nor** a
        ``half_life_defaults[<class>]`` entry falls through to no-decay and scores as **eternal** — a
        perishable tripwire that can never go stale (the SC-2 trap). Variant sub-keys (``<edge>.<x>``) do
        **not** count as reachable: nothing tags ``freshness_variant`` on a claim, so a claim on such an
        edge would still miss them. Surfaced (like :attr:`collisions`) for the caller to assert-empty as a
        loud gate; it does not hard-crash — mirroring the collisions precedent.
        """
        half_lives = getattr(credibility, "half_lives_days", {}) or {}
        defaults = getattr(credibility, "half_life_defaults", {}) or {}
        offenders: dict[str, str] = {}
        for edge, fclass in self._freshness_class.items():
            if fclass not in _DECAYING_CLASSES:
                continue
            if edge in half_lives:  # a bare per-edge half-life is reachable for any claim on this edge
                continue
            if defaults.get(fclass) is not None:  # a class default is reachable
                continue
            offenders[edge] = fclass
        return offenders

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


# ── node-type identity rules (T3b) ───────────────────────────────────────────────────────────────
#
# The edge index above says what an endpoint *may connect to*. This index says what an endpoint **is**
# and how its identity works — the other half of the same designed schema, and the half the resolver
# needed. Both are read from ``config/ontology.yaml`` and neither hardcodes a type name (gate G6).

_IDENTITY = "identity"          # the per-node-type block these rules live in
_REFINES = "refines"            # this type is a narrower reading of another type's endpoint role
_INSTANCE_SPLIT = "instance_split"  # A2/D-13.5: the citizen + link a straddling mention splits into
_DESIGN, _INSTANCE = "design", "instance"
_HEAD_MARKERS = "name_head_markers"
_NAMED_INSTANCES = "named_instances"
_RELATIONAL = "relational"
_IDENTIFIER_PATTERNS = "identifier_patterns"

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _fold(text: str) -> str:
    """Casefold + collapse punctuation to single spaces (the comparison form for the rules below)."""
    return _NON_ALNUM.sub(" ", text.casefold()).strip()


@dataclass(frozen=True)
class _Refinement:
    """A node type declared as a narrower reading of ``base``, recognised from an instance's NAME."""

    name: str
    base: str
    head_markers: tuple[str, ...]
    named_instances: tuple[str, ...]

    def matches(self, name: str) -> bool:
        folded = _fold(name)
        if not folded:
            return False
        if folded in self.named_instances:
            return True
        head = folded.rsplit(" ", 1)[-1]
        return head in self.head_markers


class NodeTypeIndex:
    """``config/ontology.yaml``'s node-type identity rules, compiled to three deterministic queries.

    Three separate facts about a node type, all authored in config because all three are statements
    about the **world**, not about the code (gate G6 / CLAUDE.md "config-driven, not hardcoded"):

    * :meth:`refine` — a *refinement* type (``refines: <base>``) is a narrower reading of a base type
      that an edge's declared range cannot express. ``based-at``/``observed-at`` range over
      ``basing_site``, so every place a source names is minted as one — including provinces, "air
      defence sectors" and "coastal belts", which are **areas of responsibility, not places a unit
      sits** (``md/13`` §1; ``ingest/basing.py::_is_locatable_site`` already says so in prose). Naming
      the distinction in the ontology makes it structural: an area and a site can no longer be proposed
      as duplicates of one another.
    * :meth:`relational_identity` — may a *shared neighbourhood* count as identity evidence for this
      type? For most types yes (that is the collective-ER signal). For an AREA it is actively
      misleading: two sectors that both contain sightings of the same equipment share a neighbourhood
      **by construction** — that is a fact about the equipment's dispersal, not about the areas being
      one area.
    * :meth:`identifier` — does this type's NAME carry a hard identifier (a bill-of-lading / contract
      reference)? Two entities that each state one and state *different* ones can never be the same
      thing, which is a deterministic rail rather than a score penalty.

    A type that declares no ``identity`` block behaves exactly as before (gate G2).
    """

    def __init__(self, ontology: OntologyConfig) -> None:
        self._refinements: list[_Refinement] = []
        self._relational: dict[str, bool] = {}
        self._identifiers: dict[str, list[re.Pattern[str]]] = {}
        self._layer: dict[str, str] = {}                       # node type → design | instance (A2)
        self._attr_layer: dict[str, dict[str, str]] = {}       # node type → attr → design | instance (A2)
        self._splits: dict[str, Materialization] = {}          # node type → its straddle-split citizen
        for t in ontology.node_types:
            if isinstance(t.layer, str):
                self._layer[t.name] = t.layer
            per_attr = {a.name: a.layer for a in t.attrs if isinstance(a.layer, str)}
            if per_attr:
                self._attr_layer[t.name] = dict(per_attr)  # type: ignore[arg-type]
            split = getattr(t, _INSTANCE_SPLIT, None)
            if isinstance(split, dict):
                node_type, link = split.get("node_type"), split.get("link")
                if isinstance(node_type, str) and isinstance(link, str):
                    self._splits[t.name] = Materialization(
                        end=_FROM_END, node_type=node_type, link=link
                    )
            block = getattr(t, _IDENTITY, None)
            if not isinstance(block, dict):
                block = {}
            base = getattr(t, _REFINES, None)
            if isinstance(base, str) and base:
                self._refinements.append(
                    _Refinement(
                        name=t.name,
                        base=base,
                        head_markers=tuple(_fold(str(m)) for m in block.get(_HEAD_MARKERS, [])),
                        named_instances=tuple(_fold(str(m)) for m in block.get(_NAMED_INSTANCES, [])),
                    )
                )
            if _RELATIONAL in block:
                self._relational[t.name] = bool(block[_RELATIONAL])
            patterns = []
            for raw in block.get(_IDENTIFIER_PATTERNS, []):
                try:
                    patterns.append(re.compile(str(raw)))
                except re.error:
                    continue  # a malformed operator regex disables that rule; it never crashes rebuild()
            if patterns:
                self._identifiers[t.name] = patterns

    def refine(self, node_type: str | None, name: str | None) -> str | None:
        """The narrower node type this instance's NAME earns, or ``node_type`` unchanged.

        Declaration order decides when several refinements share a base, so the answer is deterministic
        and reviewable in the YAML itself. No refinement declared for ``node_type`` ⇒ identity (gate G2).
        """
        if not node_type or not name:
            return node_type
        for r in self._refinements:
            if r.base == node_type and r.matches(name):
                return r.name
        return node_type

    def relational_identity(self, node_type: str | None) -> bool:
        """May a shared neighbourhood contribute to ``merge_score`` for this type? Default **yes**."""
        if node_type is None:
            return True
        return self._relational.get(node_type, True)

    # ── the layer accessors (A2 / D-13.3) ────────────────────────────────────────────────────────

    def node_layer(self, node_type: str | None) -> str | None:
        """This node type's declared layer — ``"design"`` | ``"instance"`` | ``None`` (A2).

        ``None`` means the type is **outside** the two-layer routing (nothing splits, nothing
        materializes), never "design by default": a silent default would disarm the straddle trigger for
        any type someone forgets to tag, which is exactly the failure the per-attribute tag exists to
        prevent. Sits beside :meth:`refine` / :meth:`identifier` because all three are statements about the
        world authored in ``config/ontology.yaml``, not facts about the code (gate G6).
        """
        if node_type is None:
            return None
        return self._layer.get(node_type)

    def attr_layer(self, node_type: str | None, attr: str) -> str | None:
        """The declared layer of one attribute **of one node type** (A2), or ``None`` if undeclared.

        Per-*(type, attribute)* rather than global, because the same attribute name legitimately means
        different things on different types. Layer is still uniform *per type* — a genuinely dual-natured
        attribute is split into two attribute types (D-13.3), never resolved contextually here.
        """
        if node_type is None:
            return None
        return self._attr_layer.get(node_type, {}).get(attr)

    def straddling_attrs(self, node_type: str | None, attrs: Iterable[str]) -> list[str]:
        """The **instance**-layer attributes sitting on a **design**-layer node — the split trigger (A2).

        This mismatch is the signal that one extracted mention lumped a design and one of its instances
        together (spine/13 §5.1). Returned sorted, so the consequent split is deterministic (G2). Empty for
        an instance-layer node, for an untagged node type, and for any attribute whose layer is undeclared
        (absence reads *unknown* — it never masquerades as an instance fact, which would fabricate a split).
        The reverse direction (a *design* attribute on an *instance* node) is deliberately **not** a
        trigger: only instance-on-design hides an un-individuated instance; the reverse merely records a
        shared upstream fact.
        """
        if self.node_layer(node_type) != _DESIGN:
            return []
        per_attr = self._attr_layer.get(node_type or "", {})
        return sorted(a for a in attrs if per_attr.get(a) == _INSTANCE)

    def instance_split(self, node_type: str | None) -> Materialization | None:
        """The instance citizen + binding link a straddling mention of this type splits into, or ``None``.

        Declared per node type (``instance_split: {node_type: presence, link: instance-of}``). ``None``
        means this type has **no declared citizen for its instance-layer facts**, and the build then
        *records* the unrouted straddle on the node instead of inventing a structure for it — the honest
        outcome, and the reason a site's occupancy attrs do not mint a second presence beside the one its
        sighting already materialized.
        """
        if node_type is None:
            return None
        return self._splits.get(node_type)

    def identifier(self, node_type: str | None, name: str | None) -> str | None:
        """The hard identifier carried by this instance's name, or ``None`` if it carries none.

        ``None`` on either side is **not** a conflict — absence is not disagreement, the same doctrine
        ``resolve.scoring.has_hard_conflict`` already applies to attributes.
        """
        if not node_type or not name:
            return None
        for pattern in self._identifiers.get(node_type, []):
            if pattern.fullmatch(name.strip()):
                return name.strip()
        return None


# ── layer routing: the type/instance split and its knobs (A2/A3/A4) ──────────────────────────────
#
# Read from ``config/ontology.yaml``'s top-level ``layer_routing`` block (a plain YAML mapping —
# ``OntologyConfig`` is ``extra="allow"``, the same precedent the ``materiality`` block already sets). The
# split runs **unconditionally**: the staging flag that gated it is deleted, because the pieces are one
# change to what a node *is*, and a system that can be switched between two answers to that question has
# two ontologies. Each mechanism is bounded by what these knobs — and the node/edge type declarations they
# read — actually declare; nothing here is a code literal beyond the key names and the fail-safe fallbacks
# (gate G6).

_LAYER_ROUTING = "layer_routing"


@dataclass(frozen=True)
class LayerRouting:
    """``config/ontology.yaml → layer_routing``, compiled. An absent block leaves every knob unset."""

    presence_type: str = ""
    design_link_edge: str = ""
    provisional_prefix: str = "presence"
    count_attrs: tuple[str, ...] = ()
    #: The **closed vocabulary** an ``instance_key_tag`` value must normalise into (ruling L1 / C1 ⊂ C7).
    #: The stated value is free text conflating several concepts, so the raw string is never the key.
    site_type_vocabulary: tuple[str, ...] = ()
    #: Raw stated value → vocabulary class, for genuine synonyms the fold cannot reach. Authored by the
    #: data pass (ruling L1 step 4); an empty map is the honest starting state, not a defect.
    site_type_aliases: tuple[tuple[str, str], ...] = ()
    #: The bucket an **absent or unmappable** tag value collapses to. It is ONE shared bucket on purpose:
    #: the evasion direction here is over-merge, and giving an unmappable value a bucket of its own would
    #: let an unstated ``site_type`` buy a second concurrent basing for free. Note this is only the first
    #: third of the third state — see :meth:`normalise_tag`.
    absent_bucket: str = "unknown"
    #: Bundle-filename suffixes the boot/seed loader **skips**, so a frozen derived conclusion cannot be
    #: replayed alongside the live derivation of the same fact. Empty ⇒ the loader globs everything.
    superseded_derived_bundle_suffixes: tuple[str, ...] = ()
    #: ``derived_layer`` markers the **rebuild** declines to read as evidence — the backstop for a store
    #: that already holds such claims, where the file-level skip above never ran.
    superseded_derived_layers: tuple[str, ...] = ()

    @classmethod
    def from_ontology(cls, ontology: OntologyConfig) -> LayerRouting:
        block = getattr(ontology, _LAYER_ROUTING, None)
        if not isinstance(block, dict):
            return cls()

        def _strs(key: str) -> tuple[str, ...]:
            raw = block.get(key)
            return tuple(str(x) for x in raw) if isinstance(raw, (list, tuple)) else ()

        aliases = block.get("site_type_aliases")
        alias_pairs = (
            tuple(sorted((str(k), str(v)) for k, v in aliases.items()))
            if isinstance(aliases, dict) else ()
        )
        return cls(
            presence_type=str(block.get("presence_type") or ""),
            design_link_edge=str(block.get("design_link_edge") or ""),
            provisional_prefix=str(block.get("provisional_prefix") or "presence"),
            count_attrs=_strs("count_attrs"),
            site_type_vocabulary=_strs("site_type_vocabulary"),
            site_type_aliases=alias_pairs,
            absent_bucket=str(block.get("absent_bucket") or "unknown"),
            superseded_derived_bundle_suffixes=_strs("superseded_derived_bundle_suffixes"),
            superseded_derived_layers=_strs("superseded_derived_layers"),
        )

    def retired_bundle_suffixes(self) -> tuple[str, ...]:
        """Bundle suffixes a loader should skip — the declared list, read through one accessor.

        Callers hand the result straight to ``ingest.seed.seed_store_from_bundles(skip_suffixes=…)``, so the
        decision lives here rather than being re-derived at every seed call site. A frozen bundle whose
        conclusion the rebuild now derives itself is stale *output*, not evidence: replaying it would
        double-count the derivation and let a conclusion outlive its premises.
        """
        return self.superseded_derived_bundle_suffixes

    def normalise_tag(self, value: object) -> tuple[str, bool]:
        """A stated ``instance_key_tag`` value → ``(bucket, mapped)`` — C7's normalisation prerequisite.

        Casefolds and collapses punctuation on both sides, consults the configured alias map, and matches
        the **closed vocabulary**. ``mapped=True`` ⇒ the class is the bucket, and this basing instance is a
        full citizen of the supersede comparison.

        ``mapped=False`` — absent, or free text that does not map — is the **third state**, and the caller
        owes all three parts of it (ruling L1 / C7):

        1. **no de-confliction** — the bucket returned is :attr:`absent_bucket`, one shared bucket, never a
           bucket of its own (the evasion direction is over-merge);
        2. **no fusion** — the edge must be marked ineligible for supersede nomination, so an unresolved
           site class can never manufacture a relocation;
        3. **a named gap** — so a suppressed supersede is *visible*, never a silent non-event.

        Returning ``(absent_bucket, False)`` gives the caller exactly what it needs for all three; taking
        only part 1 and treating the value as usable is the failure mode this signature exists to prevent.
        """
        if not isinstance(value, str) or not value.strip():
            return self.absent_bucket, False
        folded = _fold(value).replace(" ", "_")
        for raw, target in self.site_type_aliases:
            if _fold(raw).replace(" ", "_") == folded:
                folded = _fold(target).replace(" ", "_")
                break
        for allowed in self.site_type_vocabulary:
            if _fold(allowed).replace(" ", "_") == folded:
                return folded, True
        return self.absent_bucket, False
