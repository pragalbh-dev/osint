"""Canonical edge direction — one house convention per relationship type (INGEST canonical-edge-direction,
2026-07-19; ``tmp/conv/INGEST-canonical-edge-direction-at-write.md``).

**The silent failure this fixes.** Two claims corroborate only when they land on the **same graph edge**,
and an edge is keyed by its resolved ``(subject, predicate, object)`` triple (``resolve``'s ``edge_instance``
and ``view.supersede.build_instance_edges``). So two claims of *one fact* written with subject and object
**flipped** — "HQ-9 at Rahwali" vs. "Rahwali hosts HQ-9" — become two different edges and never corroborate,
silently, with both claims looking fine on their own. The text lane, the imagery inference, and even two
independent LLM extractions of one sentence can each orient an edge differently.

**The fix.** Write every relationship claim in **one canonical direction per relationship type**, so every
producer (text extraction, the imagery inference, anything added later) emits a given edge the same way; then
co-location just works and the append-only log is internally consistent. The ontology already declares each
relationship's direction — this module reads that declaration, promoted from a human ``# Unit->Site`` comment
to machine-readable ``from:``/``to:`` fields on each edge ``TypeDef`` (``ConfigModel`` is ``extra="allow"``,
so these are plain YAML fields — no F0 schema change) — and orients a claim's endpoints to match.

**Two placements, one function** (belt + suspenders):

* **write-side** — the INGEST lane runs :func:`canonicalize_claims` per document (over that doc's own entity
  claims + the place gazetteer) before dedup, so what is *appended to the immutable log* is already correct.
* **read-side net** — ``rebuild()`` runs it again over all active claims, as a fallback for any producer that
  could not type its endpoints at write-time (or predates the convention). It reorients only the *derived
  view* — it never rewrites the log.

**Pure & deterministic (gates G1/G2):** no network, clock, or RNG; the same ``(claims, config)`` always yields
the same orientation. The module **never guesses** — a symmetric/structural edge (``same-as``, ``corroborates``,
``supersedes``, …), a same-type edge (``component-of``), a triple whose object is a structured value, or a
triple whose endpoints cannot be typed is returned exactly as written. It is a **no-op** on an ontology that
declares no edge directions (the golden test fixtures), so those views stay byte-identical.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from chanakya.schemas import ClaimRecord, ConfigBundle
from chanakya.schemas.claim import EntityDescriptor, Triple

#: The ontology's place-like node type. Gazetteer places (airbases, seaports, SAM sites) resolve to this
#: node type, so a place named *only* inside a relationship — never separately emitted as an entity claim —
#: can still be typed. A single named default (not magic), overridable by callers of :func:`type_index`.
_PLACE_NODE_TYPE = "basing_site"

#: Tier-3 provenance keys naming the **mention** (the entity claim id) that supplied each endpoint of a
#: relationship claim — INGEST's mention-keyed provenance (``ingest/coref.py``). They are *positional*:
#: ``_subject_mention`` describes ``Triple.subject``, so anything that reorders the endpoints must swap
#: them too, or a relation silently points at the wrong mention. That invariant is why the names live
#: here, beside the one function that reorders endpoints, rather than in ``ingest/`` (which this module
#: must never import — ``rebuild()`` calls it, and the ingest package reaches the LLM client).
SUBJECT_MENTION_ATTR = "_subject_mention"
OBJECT_MENTION_ATTR = "_object_mention"


def swap_mention_refs(attributes: dict | None) -> dict | None:
    """Swap the positional mention refs so they follow a subject/object flip. ``None``/absent ⇒ unchanged."""
    if not attributes:
        return attributes
    subject, obj = attributes.get(SUBJECT_MENTION_ATTR), attributes.get(OBJECT_MENTION_ATTR)
    if subject is None and obj is None:
        return attributes
    swapped = dict(attributes)
    for key, value in ((SUBJECT_MENTION_ATTR, obj), (OBJECT_MENTION_ATTR, subject)):
        if value is None:
            swapped.pop(key, None)
        else:
            swapped[key] = value
    return swapped

#: A ``designator -> node type`` lookup returning ``None`` for an untypable designator.
TypeOf = Callable[[str], str | None]


@dataclass(frozen=True)
class DirectionRule:
    """The declared endpoint node-types of one directional relationship: ``from_type --pred--> to_type``.

    Either end may be ``None`` when the ontology declares only one — enough to detect a flip for a
    polymorphic-object edge (``manufactures`` fixes the *manufacturer* end; the object may be a component
    or a variant). A rule with *both* ends equal (``component-of``) cannot disambiguate by type.
    """

    from_type: str | None
    to_type: str | None


def _str_field(type_def: object, *names: str) -> str | None:
    """First non-empty string among ``names`` on an edge ``TypeDef`` (``from``/``to`` ride as YAML extras)."""
    for name in names:
        value = getattr(type_def, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def direction_map(config: ConfigBundle) -> dict[str, DirectionRule]:
    """``predicate -> DirectionRule`` for every **directional** edge type that declares an endpoint.

    Symmetric/structural edges (``symmetric: true``) and edges that declare neither ``from`` nor ``to`` are
    omitted, so they are never reoriented. An empty map ⇒ :func:`canonicalize_claims` is a pure no-op (an
    ontology that has not adopted the convention is left byte-identical).
    """
    out: dict[str, DirectionRule] = {}
    for td in config.ontology.edge_types:
        if bool(getattr(td, "symmetric", False)):
            continue
        from_type = _str_field(td, "from", "from_type")
        to_type = _str_field(td, "to", "to_type")
        if from_type or to_type:
            out[td.name] = DirectionRule(from_type=from_type, to_type=to_type)
    return out


def type_index(claims: list[ClaimRecord], config: ConfigBundle, *,
               place_node_type: str = _PLACE_NODE_TYPE) -> dict[str, str]:
    """``designator -> node type`` from the in-scope entity claims, backed by the place gazetteer.

    Entity claims win — the extractor already classified "Rahwali" as a ``basing_site`` when it emitted the
    entity — and the gazetteer fills a designator named only inside a relationship. Deterministic: the first
    writer wins in claim order, so re-runs are byte-stable (G2).
    """
    index: dict[str, str] = {}
    for claim in claims:
        payload = claim.payload
        if isinstance(payload, EntityDescriptor) and payload.name:
            index.setdefault(payload.name, payload.entity_type)
    for place in config.places.places:
        for name in (place.canonical_name, *place.aliases):
            if isinstance(name, str) and name:
                index.setdefault(name, place_node_type)
    return index


def _orientation_score(subject_type: str | None, object_type: str | None, rule: DirectionRule) -> int:
    """Evidence that ``(subject_type -> object_type)`` matches ``rule``: +1 per declared+known end that fits,
    −1 per declared+known end that clashes, 0 where a constraint or a type is absent.

    Comparing this score against the swapped orientation's score decides a flip *only on positive evidence*,
    so a partly-known or ambiguous triple (equal scores) is never reoriented.
    """
    score = 0
    if rule.from_type is not None and subject_type is not None:
        score += 1 if subject_type == rule.from_type else -1
    if rule.to_type is not None and object_type is not None:
        score += 1 if object_type == rule.to_type else -1
    return score


def reversed_for_types(
    predicate: str, subject_type: str | None, object_type: str | None,
    rules: dict[str, DirectionRule],
) -> bool:
    """Should a triple be swapped, given only its predicate + endpoint types (no ``Triple`` in hand)?

    The **partial-typing companion** to :func:`canonicalize_claim` for INGEST's write-time re-lane: when
    only one endpoint could be typed, :meth:`EdgeLaneIndex.relane` cannot *name* the edge, but the edge's
    declared direction can still say whether the fact was written **backwards**. Returns ``False`` (leave
    as written) for an unknown / symmetric / same-type predicate, or whenever the known types give no
    positive evidence for a swap — mirroring :func:`_is_reversed`, on which the same scoring rule is used.
    """
    rule = rules.get(predicate)
    if rule is None or (rule.from_type is not None and rule.from_type == rule.to_type):
        return False
    return _orientation_score(object_type, subject_type, rule) > _orientation_score(
        subject_type, object_type, rule
    )


def _is_reversed(triple: Triple, rule: DirectionRule, type_of: TypeOf) -> bool:
    """Is ``triple`` **cleanly reversed** — swapping its endpoints strictly improves the type fit?

    ``False`` (leave as written) when the triple is already canonical, when neither orientation is better
    (ambiguous / untypable / same-type edge), or when nothing can be typed.
    """
    if rule.from_type is not None and rule.from_type == rule.to_type:
        return False  # same-type edge (component-of): type cannot tell subject from object
    subject_type, object_type = type_of(triple.subject), type_of(triple.object)
    current = _orientation_score(subject_type, object_type, rule)
    swapped = _orientation_score(object_type, subject_type, rule)
    return swapped > current


def canonicalize_claim(claim: ClaimRecord, rules: dict[str, DirectionRule], type_of: TypeOf) -> ClaimRecord:
    """Return ``claim`` in canonical direction — a copy with subject/object swapped iff cleanly reversed.

    Returned untouched (the same object): a non-relationship claim; a symmetric/undeclared predicate; a
    triple whose ``object`` is a structured value (``object_value`` set — the object is a value, not a typed
    node, so there is no direction to fix); and any triple whose endpoints do not clearly indicate a flip.
    The predicate label is never changed — there is one directional predicate per relationship, so
    re-ordering the endpoints is the whole correction.
    """
    payload = claim.payload
    if not isinstance(payload, Triple) or payload.object_value is not None:
        return claim
    rule = rules.get(payload.predicate)
    if rule is None or not _is_reversed(payload, rule, type_of):
        return claim
    flipped = payload.model_copy(update={"subject": payload.object, "object": payload.subject})
    # The mention refs are positional (they name which mention supplied each endpoint), so they flip with
    # the endpoints — otherwise a reoriented relation would point at the wrong mention's cluster.
    return claim.model_copy(
        update={"payload": flipped, "attributes": swap_mention_refs(claim.attributes)}
    )


def canonicalize_claims(claims: list[ClaimRecord], config: ConfigBundle, *,
                        place_node_type: str = _PLACE_NODE_TYPE) -> list[ClaimRecord]:
    """Orient every relationship claim to its type's canonical direction — pure and deterministic.

    A no-op returning the input list unchanged when the ontology declares no edge directions, so an
    un-adopted ontology (the golden fixtures) stays byte-identical. Otherwise each cleanly-reversed triple
    is returned as an oriented copy and everything else is returned as-is (untouched claims keep object
    identity, so downstream sees no spurious churn).
    """
    rules = direction_map(config)
    if not rules:
        return claims
    type_of: TypeOf = type_index(claims, config, place_node_type=place_node_type).get
    return [canonicalize_claim(c, rules, type_of) for c in claims]


__all__ = [
    "OBJECT_MENTION_ATTR",
    "SUBJECT_MENTION_ATTR",
    "DirectionRule",
    "canonicalize_claim",
    "canonicalize_claims",
    "direction_map",
    "reversed_for_types",
    "swap_mention_refs",
    "type_index",
]
