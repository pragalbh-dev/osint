"""Layer routing — the type/instance split, applied at rebuild (A2/A3/A4; spine/13 §3a/§5).

``config/ontology.yaml`` says which *layer* every node type and every attribute belongs to; this module
is what that declaration **does**. Three mechanisms, all pure, all behind ``layer_routing.enabled``:

1. **Endpoint materialization (A4/D-13.6).** An edge that declares ``materializes`` needs an *instance*
   endpoint, but a source states only the design — *"HQ-9/P at Rahwali"* arrives as
   ``observed-at: variant → basing_site``. Pointing that at the shared design node would assert that the
   design *itself* is at a place, and would pool every operator's sightings onto one node. So the build
   materializes a provisional **presence** as the subject, re-points the sighting at it, and draws the
   ``instance-of`` link back to the design. A cross-layer *holding* edge — an induction announcement, a
   country-level "X equips Y" — declares nothing and therefore mints **nothing**.

2. **The straddle split (A2/D-13.5).** An *instance*-layer attribute sitting on a *design*-layer node is
   the signal that one extracted mention lumped a design and one of its instances together. Where the node
   type declares an ``instance_split`` citizen the build separates them into two linked nodes; where it
   does not, the unrouted straddle is **recorded on the node** rather than given an invented structure —
   a site's occupancy attributes belong to the presence its sighting already materialized, and minting a
   second presence for them would double-count one fact.

3. **The ``site_type``-tagged supersede bucket (R1.3/C1, and C7 via ruling L1).** ``based-at`` is
   single-valued per *(unit, site_type)*, not per unit: a unit at its garrison and concurrently at a
   forward site is two valid basings, not a relocation. The stated ``site_type`` is free text, so the raw
   string is **never** the key — it is normalised into a closed vocabulary, and a value that will not map
   takes the **third state**: no de-confliction, no fusion, and a named gap.

**Nothing here mints a claim atom or appends to the evidence log** (gate G17). A presence node id and an
``instance-of`` edge are *derived-layer* objects, recomputed from the same claims every rebuild; the
provisional-instance id lives in its own namespace rather than ``ent:`` so it never becomes another
name-as-address offender for S4 to unwind.

**Grain (F8).** One presence per *(design endpoint, site endpoint)* — i.e. per resolved ``observed-at``
edge instance, not per mention. That is deliberately *coarser* than S3's coref grain will be, and it is
safe in exactly the way D-13.14 says: "merging co-located reports into one **presence** is safe; merging
them into one **formation** on co-location alone would undercount the order of battle." S3 owns the real
mint grain and must not read this as already-correct.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from chanakya.credibility.supersession import CANDIDATE, GATE, PENDING_NEWER, PENDING_OLDER
from chanakya.ontology import EdgeLaneIndex, LayerRouting, Materialization, NodeTypeIndex
from chanakya.schemas import ClaimRecord, EdgeView, KnownGap, NodeView

_FROM_END = "from"
_TO_END = "to"
_DESIGN = "design"

#: Node attrs this module writes. Strings, never numbers (gate G6).
PROVISIONAL = "provisional"                       # this instance was materialized, not claim-declared
INSTANCE_OF = "instance_of_design"                # the design node a provisional instance points at
STRADDLE_UNROUTED = "layer_straddle_unrouted"     # instance attrs on a design node with no declared citizen
SPLIT_FROM = "layer_split_from"                   # the design node this instance was split out of
#: Edge attrs this module writes.
SUPERSEDE_SUPPRESSED = "supersede_suppressed"     # this instance may not nominate a supersede, and why
STATED_TAG = "stated_instance_key_tag"            # the raw, unmapped stated value, kept verbatim
MATERIALIZED_END = "materialized_endpoint"        # which end the build had to materialize
DERIVED_VIA = "derived_via"

_MISSING_PRESENCE_SLOTS = ("site", "observed_window")


@dataclass
class RoutingOutcome:
    """Everything the routing did, returned so ``rebuild()`` can render it — never a silent effect."""

    #: presence node id → the design node id it is an ``instance-of``.
    materialized: dict[str, str] = field(default_factory=dict)
    #: presence node id → the *other* endpoint of the edge that materialized it (a site), where there is
    #: one. Kept so the derived human label can be assembled from node **names** rather than parsed back
    #: out of the id — a label built by splitting an id is a label that breaks when the id scheme does.
    materialized_at: dict[str, str] = field(default_factory=dict)
    #: design node id → claims that mentioned it and were routed onto a materialized instance. Re-pointing
    #: a sighting must not cost the design node its provenance: the source *did* name the design — that is
    #: how the presence came to exist — so the design keeps citing the claim, exactly as it did before
    #: routing (where it inherited those claims from the sighting edge). Without this the design node falls
    #: back to whichever *other* edge happens to mention it, and can silently lose the dated look it was
    #: decaying against.
    design_citations: dict[str, set[str]] = field(default_factory=dict)
    #: extra derived-layer edges to add to the view (the ``instance-of`` links).
    link_edges: list[EdgeView] = field(default_factory=list)
    #: withheld relations: ``(predicate, endpoint_id, end)`` — a ``requires_stated`` violation. Deduped, so
    #: several claims asserting one unsourced relation earn one gap rather than one each.
    withheld: list[tuple[str, str, str]] = field(default_factory=list)
    #: named gaps the routing owes the analyst.
    gaps: list[KnownGap] = field(default_factory=list)


def routing_config(ontology: Any) -> LayerRouting:
    """``config/ontology.yaml → layer_routing``, compiled. Absent ⇒ disabled ⇒ every mechanism inert."""
    return LayerRouting.from_ontology(ontology)


# ── 1 + 3: per-triple routing (called from the assembler's relationship branch) ────────────────────

def _tag_of(
    predicate: str,
    subject: str,
    obj: str,
    attr: str,
    lane: EdgeLaneIndex,
    nodes: dict[str, NodeView],
    layers: LayerRouting,
) -> tuple[str, str | None, bool]:
    """``(bucket, raw_stated_value, mapped)`` for one edge's ``instance_key_tag`` (R1.3/C1, C7 via L1).

    The tag attribute is read off the endpoint the **functional key drops** — for ``based-at`` that is the
    site, whose ``site_type`` says what *kind* of place this basing is. That is the endpoint whose identity
    the functional key deliberately forgets, and therefore the one whose *class* has to come back in as a
    sub-bucket. ``mapped=False`` covers **both** an absent value and a stated-but-unmappable one: for keying
    they are the same condition — we do not know the class.
    """
    ends = lane.instance_key(predicate)
    holder = obj if _TO_END not in ends else subject
    node = nodes.get(holder)
    raw = (node.attrs.get(attr) if node is not None else None)
    bucket, mapped = layers.normalise_tag(raw)
    return bucket, (raw if isinstance(raw, str) else None), mapped


def retag_instances(
    edges: list[EdgeView],
    nodes: dict[str, NodeView],
    lane: EdgeLaneIndex,
    layers: LayerRouting,
    order: Callable[[list[EdgeView], dict[str, tuple[str, str] | None]], object],
    intervals: Callable[[EdgeView], tuple[str, str] | None],
) -> list[KnownGap]:
    """Apply the ``instance_key_tag`` sub-bucket **per subject**, or take the third state (R1.3/C1/L1/C7).

    **Why this is a post-pass over the finished edge list, and why it must be per subject.** The tag
    de-conflicts one subject's basings by *kind of place*: a unit at its garrison and concurrently at a
    forward site is two valid basings, not a relocation. That is only sound when every one of that subject's
    basings has a **known** class. If even one does not, then tagging the rest *separates* the unknown one
    from them — and separation is de-confliction, the one thing C7's third state forbids, because it makes a
    real relocation quietly stop firing while the code still looks deterministic. (Measured, not
    hypothetical: the flagship relocation's two ends are described on different axes — one names a revetment
    complex, the other an airfield — so a per-edge tag put them in different buckets and the supersede
    silently never fired, with nothing anywhere to say so.)

    So the decision is per ``(subject, predicate)`` and covers **every** basing of that subject — stated and
    rebuild-derived alike, which is why it runs after the derivation rather than during keying:

    * **all classes known** ⇒ split into per-class instances and re-run the ordering inside each. Two
      concurrent basings at different kinds of site stop being a manufactured before/after.
    * **any class unknown** (absent *or* stated-but-unmappable — for keying, the same condition) ⇒ **no
      de-confliction**: the whole group keeps one untagged instance, so nothing is separated. **No fusion**:
      the nomination is withdrawn, so an unresolved class can never manufacture a relocation. **A named
      gap**, so the withheld supersede is a visible refusal rather than a non-event. Never one without the
      other two.

    A group with a single member is a special case of "nothing to fuse": its class is applied if known, and
    if unknown it simply keeps the untagged key with no suppression and no gap — a "cannot assess a
    relocation" notice against every lone basing in the graph is how a gap register stops being read.
    """
    gaps: list[KnownGap] = []
    groups: dict[tuple[str, str, str], list[EdgeView]] = {}
    for edge in edges:
        attr = lane.instance_key_tag(edge.type)
        if attr is not None:
            groups.setdefault((edge.source, edge.type, attr), []).append(edge)

    for (subject, predicate, attr), group in sorted(groups.items()):
        resolved = [
            (edge, *_tag_of(predicate, edge.source, edge.target, attr, lane, nodes, layers))
            for edge in group
        ]
        for edge, _bucket, raw, mapped in resolved:
            if raw and not mapped:
                edge.attrs[STATED_TAG] = raw  # keep the unresolved class visible on the edge itself
        if all(mapped for _e, _b, _r, mapped in resolved):
            by_bucket: dict[str, list[EdgeView]] = {}
            for edge, bucket, _raw, _mapped in resolved:
                edge.edge_instance = lane.edge_instance_key(subject, predicate, edge.target, bucket)
                by_bucket.setdefault(bucket, []).append(edge)
            if len(by_bucket) > 1:
                # The classes genuinely separated this subject's basings, so the ordering the untagged key
                # produced spanned instances that are not comparable. Clear it and re-order within each.
                for edge in group:
                    clear_supersede_nomination(edge)
                for bucket_edges in by_bucket.values():
                    order(bucket_edges, {e.id: intervals(e) for e in bucket_edges})
            continue
        if len(group) > 1:
            for edge in group:
                clear_supersede_nomination(edge)
                edge.attrs[SUPERSEDE_SUPPRESSED] = "instance-key-tag-unmappable"
            raw = next((r for _e, _b, r, m in resolved if r and not m), None)
            gaps.append(unmapped_tag_gap(group[0].edge_instance or subject, predicate, attr, raw))
    return gaps


def clear_supersede_nomination(edge: EdgeView) -> None:
    """Withdraw a supersede nomination, leaving the edge itself drawn, scored and clickable.

    Nomination attrs only: what is removed is the machine's *claim to have ordered this pair*, which is the
    thing an unresolved (or newly re-bucketed) site class does not license. Imported by ``view/pipeline``
    rather than duplicated, so the vocabulary has one owner.
    """
    edge.attrs.pop(CANDIDATE, None)
    edge.attrs.pop(PENDING_NEWER, None)
    edge.attrs.pop(PENDING_OLDER, None)
    edge.attrs.pop(GATE, None)


def _presence_id(layers: LayerRouting, instance_end: str, other_end: str) -> str:
    """The deterministic id of a materialized presence: ``<prefix>:<design>@<site>`` (see the grain note)."""
    return f"{layers.provisional_prefix}:{instance_end}@{other_end}"


def _node_type_of(node_id: str, nodes: dict[str, NodeView], endpoint_types: dict[str, str]) -> str | None:
    node = nodes.get(node_id)
    if node is not None:
        return node.type
    return endpoint_types.get(node_id)


def route_triple(
    claim: ClaimRecord,
    subject: str,
    predicate: str,
    obj: str,
    *,
    nodes: dict[str, NodeView],
    endpoint_types: dict[str, str],
    lane: EdgeLaneIndex,
    node_types: NodeTypeIndex,
    layers: LayerRouting,
    outcome: RoutingOutcome,
) -> tuple[str, str] | None:
    """Route one relationship claim: materialize its instance endpoint, or withhold it.

    Returns the ``(subject, object)`` the edge should actually be drawn between — with a materialized
    presence substituted in where the mention named only the design — or ``None`` when the edge must be
    **withheld** because an endpoint the ontology requires a source to have *stated* was one the build had
    to materialize (D12). A withheld edge is always paired with a named gap; it is never dropped quietly.
    """
    # D12 — `requires_stated_endpoints`. "Stated" means an entity-form claim declared this endpoint. An
    # endpoint that exists only because an edge referenced it (RESOLVE minted it from the edge's own
    # domain/range) is NOT a source statement about that entity, and an edge type declaring the requirement
    # says the relation is meaningless without one. Withholding + a gap is the honest outcome; drawing it
    # would assert precisely the relation no document states.
    for end in lane.requires_stated_endpoints(predicate):
        endpoint = subject if end == _FROM_END else obj
        if endpoint not in nodes and endpoint in endpoint_types:
            # Recorded once per (predicate, endpoint, end), not once per withheld claim: several claims can
            # assert the same unsourced relation, and the *gap* they earn is one statement about one missing
            # thing. Raising it per claim would put the same finding in the register three times.
            entry = (predicate, endpoint, end)
            if entry not in outcome.withheld:
                outcome.withheld.append(entry)
            return None

    mat = lane.materializes(predicate)
    if mat is None:
        return subject, obj  # a holding / design-layer edge materializes nothing (spine/13 §5.3)

    instance_end = subject if mat.end == _FROM_END else obj
    other_end = obj if mat.end == _FROM_END else subject
    declared = _node_type_of(instance_end, nodes, endpoint_types)
    if declared == mat.node_type:
        return subject, obj  # the mention already named an instance — nothing to materialize
    if node_types.node_layer(declared) != _DESIGN:
        # Not a design-layer endpoint and not the citizen either: the ontology cannot tell us this is a
        # lumped mention, so we assert nothing about it. Silence here is a *declaration* gap, and the
        # `layer: null` reading (unknown, never "design") is what keeps it from fabricating a split.
        return subject, obj

    pid = _presence_id(layers, instance_end, other_end)
    node = nodes.get(pid)
    if node is None:
        node = NodeView(
            id=pid,
            type=mat.node_type,
            name=None,  # a provisional instance has no stated name; the label is derived downstream
            attrs={PROVISIONAL: True, INSTANCE_OF: instance_end},
        )
        nodes[pid] = node
        outcome.materialized[pid] = instance_end
        outcome.materialized_at[pid] = other_end
    if claim.claim_id not in node.claim_ids:
        node.claim_ids.append(claim.claim_id)
    _inherit_sourced_attrs(node, claim, layers)
    _record_link(outcome, pid, instance_end, mat, claim)
    outcome.design_citations.setdefault(instance_end, set()).add(claim.claim_id)
    return (pid, obj) if mat.end == _FROM_END else (subject, pid)


def label_provisional_instances(nodes: dict[str, NodeView], outcome: RoutingOutcome) -> None:
    """Give every materialized instance a **derived** human label (A5: the label is derived, never minted).

    A node with no name renders as its raw id, and a raw id is not something an analyst can read — which is
    the whole complaint the display-name work already fixed once for claim-backed nodes. A provisional
    instance has no *stated* name (no source named it; that is what makes it provisional), so its label is
    composed from the two nodes it stands between: "<design> at <site>". Nothing is invented — both halves
    are names an analyst can already click through to — and it is marked *provisional* so the label never
    reads as a settled identity.

    Runs after every node exists, so the site's own name (itself possibly an analyst-curated display name)
    is available. Sorted for determinism (gate G2).
    """
    for pid in sorted(outcome.materialized):
        node = nodes.get(pid)
        if node is None or node.name:
            continue
        design = nodes.get(outcome.materialized[pid])
        site = nodes.get(outcome.materialized_at.get(pid, ""))
        design_label = (design.name if design is not None else None) or outcome.materialized[pid]
        if site is not None:
            node.name = f"{design_label} at {site.name or site.id} (provisional presence)"
        else:
            node.name = f"{design_label} (provisional instance)"


def apply_design_citations(nodes: dict[str, NodeView], outcome: RoutingOutcome) -> None:
    """Give each design node back the claims whose sightings were routed onto its instances.

    Called after the assembler has materialized every dangling endpoint, so it applies whether the design
    node came from an entity claim or from an edge. Sorted for determinism (gate G2).
    """
    for design_id, claim_ids in sorted(outcome.design_citations.items()):
        node = nodes.get(design_id)
        if node is None:
            continue
        node.claim_ids = sorted(set(node.claim_ids) | claim_ids)


def _inherit_sourced_attrs(node: NodeView, claim: ClaimRecord, layers: LayerRouting) -> None:
    """Copy the presence's **sourced** attributes off the grounding claim — and nothing else (A3/D-13.19).

    ``count`` is the one that matters: it is an attribute of the presence *with its own sourced evidence*
    (an imagery TEL count, a stated OOB figure), default **unknown**, and it is **never** derived from how
    many claims or reports landed on this node — *k* reports of one battery is not *k* launchers. So the
    only values written here are ones a source stated on the claim itself; an absent value stays absent.
    """
    stated = claim.attributes or {}
    for attr in layers.count_attrs:
        value = stated.get(attr)
        if value in (None, "", [], {}):
            continue
        node.attrs.setdefault(attr, value)


def _record_link(
    outcome: RoutingOutcome, pid: str, design_id: str, mat: Materialization, claim: ClaimRecord
) -> None:
    """Draw (or extend) the ``instance-of`` binding from a materialized instance to its shared design."""
    eid = f"e:{pid}:{mat.link}:{design_id}"
    for existing in outcome.link_edges:
        if existing.id == eid:
            if claim.claim_id not in existing.claim_ids:
                existing.claim_ids = sorted({*existing.claim_ids, claim.claim_id})
            return
    outcome.link_edges.append(
        EdgeView(
            id=eid,
            type=mat.link,
            source=pid,
            target=design_id,
            claim_ids=[claim.claim_id],
            attrs={DERIVED_VIA: "layer-routing", MATERIALIZED_END: mat.end},
        )
    )


# ── 2: the straddle split ─────────────────────────────────────────────────────────────────────────

def split_straddlers(
    nodes: dict[str, NodeView],
    node_types: NodeTypeIndex,
    layers: LayerRouting,
    outcome: RoutingOutcome,
) -> None:
    """Split every design-layer node carrying instance-layer attributes (A2/D-13.5), or record why not.

    Iterated in sorted id order so the split is deterministic (gate G2). Where the node type declares an
    ``instance_split`` citizen the instance attributes **move** — the design node keeps only design facts,
    which is the whole point of the split. Where it declares none, the straddle is recorded on the node and
    the attributes stay put: inventing a citizen would either fabricate structure or double-count a fact
    another mechanism already models.
    """
    for node_id in sorted(nodes):
        node = nodes[node_id]
        straddlers = node_types.straddling_attrs(node.type, node.attrs.keys())
        if not straddlers:
            continue
        split = node_types.instance_split(node.type)
        if split is None:
            node.attrs[STRADDLE_UNROUTED] = straddlers
            continue
        pid = f"{layers.provisional_prefix}:{node_id}"
        inst = nodes.get(pid)
        if inst is None:
            inst = NodeView(
                id=pid,
                type=split.node_type,
                name=None,
                claim_ids=list(node.claim_ids),
                attrs={PROVISIONAL: True, INSTANCE_OF: node_id, SPLIT_FROM: node_id},
            )
            nodes[pid] = inst
            outcome.materialized[pid] = node_id
        for attr in straddlers:
            inst.attrs[attr] = node.attrs.pop(attr)
            series = node.attr_history.pop(attr, None)
            if series:
                inst.attr_history[attr] = series
        _link_split(outcome, pid, node_id, split, node.claim_ids)
        # A presence split out of a lumped mention has no stated site or window — it is genuinely
        # under-individuated, which D-13.8 says to record as `unknown` plus a named gap, never to fill in.
        outcome.gaps.append(
            KnownGap(
                id=f"gap:{pid}",
                related_ref=pid,
                what_missing=(
                    "instance separated from a lumped design mention; no source states its site or "
                    "observation window"
                ),
                observability_ceiling="confirmable",
                missing_slots=list(_MISSING_PRESENCE_SLOTS),
            )
        )


def _link_split(
    outcome: RoutingOutcome, pid: str, design_id: str, split: Materialization, claim_ids: Iterable[str]
) -> None:
    eid = f"e:{pid}:{split.link}:{design_id}"
    if any(e.id == eid for e in outcome.link_edges):
        return
    outcome.link_edges.append(
        EdgeView(
            id=eid,
            type=split.link,
            source=pid,
            target=design_id,
            claim_ids=sorted(set(claim_ids)),
            attrs={DERIVED_VIA: "straddle-split"},
        )
    )


# ── the named gaps the routing owes ───────────────────────────────────────────────────────────────

def unmapped_tag_gap(edge_instance: str, predicate: str, attr: str, raw: str | None) -> KnownGap:
    """The third state's third part (ruling L1 / C7): a suppressed supersede must be **visible**.

    The stated site class would not map into the closed vocabulary, so this basing instance is neither
    de-conflicted (it shares the fail-safe bucket) nor allowed to fuse (it may not nominate a supersede).
    Both of those are *non-events*, and a non-event with no gap beside it is indistinguishable from the
    mechanism working — which is how a relocation stops firing while the code still looks deterministic.
    """
    stated = f"stated as {raw!r}" if raw else "not stated by any source"
    return KnownGap(
        id=f"gap:{edge_instance}:{attr}",
        related_ref=edge_instance,
        what_missing=(
            f"{attr} for this {predicate} does not map to a known site class ({stated}), so a "
            f"change of site here cannot be assessed as a relocation"
        ),
        observability_ceiling="confirmable",
        missing_slots=[attr],
    )


def withheld_edge_gap(predicate: str, endpoint: str, end: str) -> KnownGap:
    """D12's gap: the relation is withheld because the endpoint the ontology requires was never stated."""
    return KnownGap(
        id=f"gap:{predicate}:{end}:{endpoint}",
        related_ref=endpoint,
        what_missing=(
            f"no source states the {end} endpoint of {predicate}; the relation is withheld rather than "
            f"asserted against an endpoint the build had to materialize"
        ),
        observability_ceiling="confirmable",
        missing_slots=[f"{predicate}.{end}"],
    )
