"""``rebuild()`` — the pure, deterministic reduction of (evidence, decision, config) → view.

**The load-bearing invariant (master §1, gate G1):** no LLM, network, clock, or randomness runs
here. The LLM *proposed* upstream (its output is frozen in the logs); deterministic rules *dispose*
inside this function. Given the same logs + config, the emitted view is byte-identical (gate G2).

Stage call-order is fixed (master §4.3):
``resolve → score_claims → (group by independence) → assign_status → check → precompute``, with the
supersession floor (``credibility.supersession``) slotted between ``assign_status`` and ``precompute``
— it is the one gate that needs a *scored* view to decide, so it cannot run with ``supersede.py``.
Around those stages, F0 owns four *real* pieces: retraction handling, supersede/contradict ordering
(``supersede.py``), rendering the resolver's decisions as edges (candidate ``same-as`` + ``distinct-from``,
G4-exempt / never scored), and HITL decision-effect application (gate G12). All numeric scoring lives
in the stages (which read config), never here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, cast

from pydantic import ValidationError

from chanakya.credibility import (
    assertion_freshness,
    assign_status,
    group_by_independence,
    promote_supersessions,
    score_claims,
)
from chanakya.edge_direction import canonicalize_claims
from chanakya.materiality import precompute
from chanakya.ontology import EdgeLaneIndex, LayerRouting, NodeTypeIndex
from chanakya.resolve import (
    COREF_PREDICATE,
    IDENTITY_PREDICATES,
    identity_ledger,
    location_attr,
    resolve,
    resolve_with_types,
)
from chanakya.schemas import (
    AssertionInput,
    AttrValueClaim,
    ClaimRecord,
    ConfidenceBreakdown,
    ConfigBundle,
    DecisionRecord,
    EdgeView,
    EntityDescriptor,
    EventDescriptor,
    EventView,
    GraphView,
    KnownGap,
    Location,
    NodeView,
    Partition,
    PlacesConfig,
    SourceRegistryEntry,
    SufficiencyEval,
    Triple,
    canonical_iso_bounds,
    pair_key,
    report_bounded_validity,
)
from chanakya.sufficiency import check

#: The sufficiency slot an identity refusal is missing. One name, used by the node's ``missing_slots`` and by
#: the per-endpoint ``gap:identity:`` record, so the refuse half and the escalate half say the same word.
IDENTITY_SLOT = "identity" 
from chanakya.timeref import effective_as_of, is_available_by

from . import basing as derived_basing
from .export import sorted_view
from .layers import (
    RoutingOutcome,
    apply_design_citations,
    label_provisional_instances,
    retag_instances,
    route_triple,
    split_straddlers,
    withheld_edge_gap,
)
from .supersede import build_instance_edges, order_instance_edges

# ── log normalisation ────────────────────────────────────────────────────────────────────────

def _replay[T](source: object, item_type: type[T]) -> list[T]:
    """Accept a log object (``.replay()``) or a plain list of records — return the list."""
    if hasattr(source, "replay"):
        return cast("list[T]", source.replay())
    return cast("list[T]", list(cast("Iterable[T]", source)))


# ── retraction (real F0) ─────────────────────────────────────────────────────────────────────

def apply_retractions(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    """Drop claims targeted by a retraction claim (and the retraction records themselves).

    Retraction is an *appended* claim, never a delete (append-only store, gate G3); the view simply
    excludes the retracted claim on rebuild.
    """
    retracted = {c.targets for c in claims if c.kind == "retraction" and c.targets}
    return [c for c in claims if c.kind != "retraction" and c.claim_id not in retracted]


def apply_claim_exclusions(
    claims: list[ClaimRecord], decisions: list[DecisionRecord]
) -> list[ClaimRecord]:
    """Drop claims a HITL decision rejected — sourced from the decision log, applied like a retraction.

    The richer *reject* beat (SCORE pickup #1): rejecting a look **excludes** it upstream of scoring so
    the status machine re-derives the verdict from fewer independent groups (confirmed→probable), instead
    of force-flipping the label post-machine. HITL emits an ``exclude_claims`` effect; rebuild applies it
    here — the claim is never mutated or deleted from the log (append-only, gate G3), just left out of the
    view on this rebuild. Empty when no decision excludes anything → view unchanged (gate G2).
    """
    excluded: set[str] = set()
    for d in decisions:
        effect = (d.effects or {}).get("exclude_claims")
        if isinstance(effect, str):
            excluded.add(effect)
        elif isinstance(effect, (list, tuple)):
            excluded.update(str(cid) for cid in effect)
    return [c for c in claims if c.claim_id not in excluded] if excluded else claims


def deception_gate_flags(
    element: NodeView | EdgeView | EventView,
    claims_by_id: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
) -> list[str]:
    """The unconditional deception gate — ``adversary-denial`` (spine/04 §3.4) — computed where claims +
    the source registry are in scope, so ``assign_status`` can cap from the ``AssertionInput`` alone.

    Fires if any supporting claim's source carries ``adversary_denial_flag`` (a fake second-source / a
    denial of a known dependency). Empty on clean elements → golden view unchanged (gate G2). The
    *decoy* gate is separate (single-pass-conditional — see :func:`has_decoy_look`).
    """
    for cid in element.claim_ids:
        claim = claims_by_id.get(cid)
        if claim is None:
            continue
        src = sources.get(claim.source_id)
        if src is not None and src.adversary_denial_flag:
            return ["adversary-denial"]
    return []


def has_decoy_look(
    element: NodeView | EdgeView | EventView, claims_by_id: dict[str, ClaimRecord]
) -> bool:
    """True if a single-pass decoy signal rides this element — on the element itself, or on a supporting
    claim's ``attributes`` (e.g. INGEST's attribution ``inference`` claim D, which carries
    ``decoy_risk_flag`` on ``ClaimRecord.attributes``, never on the edge). The *cap* is applied only when
    the assertion is single-pass (< the min independent looks); a second independent look resolves it.
    """
    if getattr(element, "attrs", {}).get("decoy_risk_flag"):
        return True
    for cid in element.claim_ids:
        claim = claims_by_id.get(cid)
        attrs = (claim.attributes or {}) if claim is not None else {}
        if attrs.get("decoy_risk_flag") or attrs.get("decoy_risk"):
            return True
    return False


def gated_attr_flags(
    element: NodeView | EdgeView | EventView, config: ConfigBundle
) -> list[str]:
    """``gated-attr-unknown`` if a configured gated attr (foreign_control/readiness) is present-but-UNKNOWN.

    Such an element cannot reach *confirmed* (spine/04 §3.4: gated attrs not UNKNOWN; C/01 "never
    default-to-OEM"). An absent attr is not applicable → no flag. The gated-attr list is config-driven
    (default the two C/01 gated attrs). Empty on clean elements → golden view unchanged (gate G2).
    """
    gated = getattr(config.credibility, "gated_attrs", None) or ("foreign_control", "readiness")
    attrs = getattr(element, "attrs", {})
    for attr in gated:
        value = attrs.get(attr)
        if isinstance(value, str) and value.strip().upper() == "UNKNOWN":
            return ["gated-attr-unknown"]
    return []


# ── partition application ────────────────────────────────────────────────────────────────────

def _apply_partition(claims: list[ClaimRecord], partition: Partition) -> list[ClaimRecord]:
    """Stamp each claim with its resolved_ref from the partition (immutably — a copy)."""
    out = []
    for c in claims:
        rr = partition.resolved_ref.get(c.claim_id, c.resolved_ref)
        out.append(c.model_copy(update={"resolved_ref": rr}) if rr is not c.resolved_ref else c)
    return out


# ── resolution-decision rendering (real F0: merges + traps made inspectable) ───────────────────

def _merge_provenance(nodes: dict[str, NodeView], partition: Partition) -> None:
    """Stamp accepted-merge provenance on the surviving (canonical) node — the auto-merge audit trail.

    An accepted merge is *effected* by a shared ``resolved_ref`` (both members already collapsed to
    one node); this records the *why* (which ref, at what confidence, with the score breakdown) on
    that node so the merge stays one-click inspectable. ``merge_confidence`` is identity, never truth
    (gate G5). Iterated in sorted order for byte-determinism (gate G2).
    """
    for member, canonical in sorted(partition.same_as):
        node = nodes.get(canonical)
        if node is None:
            continue
        key = pair_key(member, canonical)
        entry: dict[str, Any] = {"merged_ref": member}
        conf = partition.merge_confidence.get(key)
        if conf is not None:
            entry["merge_confidence"] = conf
        breakdown = partition.merge_breakdown.get(key)
        if breakdown:
            entry["breakdown"] = breakdown
            # D4 Stage 2 — the merge's own corroboration ledger, ADDITIVELY beside ``breakdown`` (never
            # replacing it): which independent identity signals corroborated this confirmed merge, with
            # their values ("merge corroboration, not assertion corroboration"). Derived purely from the
            # breakdown, and recorded ONLY when a signal fired — a degenerate breakdown ({"total": …}) adds
            # no key, so the pre-Stage-2 ``resolved_from`` shape is preserved byte-for-byte.
            ledger = identity_ledger(breakdown)
            if ledger:
                entry["identity_ledger"] = ledger
        node.attrs.setdefault("resolved_from", []).append(entry)


def _resolution_edges(node_ids: set[str], partition: Partition) -> list[EdgeView]:
    """Render the resolver's *undecided* + *veto* decisions: candidate ``same-as`` + ``distinct-from`` edges.

    These cite a merge decision, not a claim, so they are G4-exempt and are **never scored** (added
    after the status machine; they carry ``merge_confidence`` — identity — never
    ``assertion_confidence``, gate G5). Auto-merges do *not* appear here (they collapse to one node —
    see :func:`_merge_provenance`); only pairs an analyst still has to adjudicate, and explicit
    do-not-merge traps, surface as edges. An edge is emitted only when *both* endpoints exist as nodes.

    **The endpoints are CANONICALISED first, and that is a bug fix, not a tidy-up.** The resolver keys its
    decisions on RAW entity ids; ``_assemble`` names nodes by their CANONICAL id. Testing raw membership
    against a canonical node set therefore silently dropped every decision whose endpoint had itself been
    merged — measured on the booted corpus: 20 of 42 candidate merges and 11 of 76 walls were nowhere on the
    analyst's surface, including both cross-country walls. Worse, the better resolution got the more decisions
    vanished (more merges ⇒ more raw ids that are no longer node ids), and ``POST /hitl/merge`` 404s without
    the drawn edge — so those pairs were un-adjudicable: the analyst could not act even on the ones they
    somehow knew about. Several raw pairs can collapse onto one canonical pair, so each canonical pair is
    emitted ONCE, taking the strongest case (highest identity confidence) and the first non-empty reason in
    sorted raw order — deterministic (gate G2).
    """
    out: list[EdgeView] = []
    for a, b, raw_keys in _canonical_decisions(partition.candidates, node_ids, partition):
        # The strongest case among the raw pairs that collapsed onto this canonical pair — the analyst is
        # owed the best evidence for the proposal, not an arbitrary one. Deterministic: highest identity
        # confidence, ties broken lexicographically (gate G2).
        best = min(raw_keys, key=lambda k: (-partition.merge_confidence.get(k, 0.0), k))
        key = pair_key(a, b)
        breakdown = partition.merge_breakdown.get(best, {})
        # D4 Stage 2 — the merge-corroboration ledger, ADDITIVELY beside ``breakdown`` (kept intact):
        # which independent identity signals corroborated this candidate. Only when a signal fired.
        attrs: dict[str, Any] = {"merge_band": "candidate", "breakdown": breakdown}
        ledger = identity_ledger(breakdown)
        if ledger:
            attrs["identity_ledger"] = ledger
        # WHY this pair is an open question rather than a merge — the cap's own words, the stated
        # critical disagreement, the licensing coreference quote, the bridged wall. The resolver has
        # always computed it; nothing rendered it, so the one surface an analyst actually opens showed a
        # score and no grounds. "Escalate to the analyst" is not satisfied by a value in a dict.
        # Read over EVERY collapsed raw pair, not just the strongest: whichever of them the resolver gave a
        # reason to, that reason is this pair's ground, and losing it to the confidence tie-break would
        # re-open exactly the hole this render exists to close.
        reason = next(
            (r for r in (partition.candidate_reasons.get(k) for k in [best, *raw_keys]) if r), None
        )
        if reason:
            attrs["reason"] = reason
        out.append(
            EdgeView(
                id=f"same-as:{key}",
                type="same-as",
                source=a,
                target=b,
                merge_confidence=partition.merge_confidence.get(best),
                # The claims in which a source asserts the identity — the evidence *behind* the
                # ``source_asserted`` term of the breakdown beside it. G4 still exempts this edge
                # (it may legitimately have none: most candidates are scored on name + neighbourhood
                # alone), but where a source did speak, the analyst must be able to read it — and
                # ``GET /evidence/{edge_id}`` serves exactly this list, so no new route is needed.
                # Unioned across the collapsed raw pairs (order-preserving): no asserting sentence is
                # dropped because two mentions of one side resolved together.
                claim_ids=_merged_claim_ids(partition.identity_claims, raw_keys),
                attrs=attrs,
            )
        )
    for a, b, raw_keys in _canonical_decisions(partition.distinct_from, node_ids, partition):
        # G18/B4: EVERY rail that can draw a wall states its own ground, and a DERIVED finding never claims
        # to be a curated one. The fallback below is reached only if a rail draws a wall and records no
        # ground — a defect rather than a state — so it says that plainly instead of asserting "explicit",
        # which would misattribute a machine inference to a person.
        reason = next(
            (r for r in (partition.wall_reasons.get(k) for k in raw_keys) if r),
            "held apart by a hard do-not-merge wall whose ground was not recorded by the rail that raised "
            "it — this is a defect in that rail, not a statement about the pair. Treat the wall as holding "
            "and report the missing ground.",
        )
        out.append(
            EdgeView(
                id=f"distinct-from:{pair_key(a, b)}",
                type="distinct-from",
                source=a,
                target=b,
                attrs={"reason": reason},
            )
        )
    return out


def _canonical_decisions(
    pairs: list[tuple[str, str]], node_ids: set[str], partition: Partition
) -> list[tuple[str, str, list[str]]]:
    """Resolver decisions keyed on RAW entity ids → the CANONICAL pairs the analyst can actually see.

    Returns ``(canonical_a, canonical_b, [raw pair_keys])``, sorted. The resolver decides over raw ids while
    ``_assemble`` names nodes by canonical id, so a raw-vs-canonical membership test dropped every decision
    whose endpoint had itself been merged — silently, and *more* of them the better resolution got. Two
    filters remain, and both are real rather than artefacts:

    * ``ca == cb`` — the two mentions ended up as ONE node along some other chain, so there is no pair left
      to draw and nothing to adjudicate;
    * an endpoint that is not a node at all — a registry seed or a mention no claim ever instantiated. There
      is nothing to hang an edge on, and inventing a node for it would fabricate an entity.

    Several raw pairs can collapse onto one canonical pair; the caller gets all of their keys so it can pick
    the strongest confidence and keep whichever of them carries a reason.
    """
    canon = partition.entity_canonical
    grouped: dict[tuple[str, str], list[str]] = {}
    for a, b in sorted(pairs):
        ca, cb = canon.get(a, a), canon.get(b, b)
        if ca == cb or ca not in node_ids or cb not in node_ids:
            continue
        grouped.setdefault(tuple(sorted((ca, cb))), []).append(pair_key(a, b))  # type: ignore[arg-type]
    return [(a, b, keys) for (a, b), keys in sorted(grouped.items())]


def _merged_claim_ids(claims: dict[str, list[str]], raw_keys: list[str]) -> list[str]:
    """Union of the identity claims across every raw pair that collapsed onto one canonical pair.

    Order-preserving and duplicate-free, so ``GET /evidence/{edge_id}`` serves every sentence that asserted
    this identity and never the same one twice.
    """
    out: list[str] = []
    for key in raw_keys:
        for cid in claims.get(key, []):
            if cid not in out:
                out.append(cid)
    return out


# ── graph assembly (+ supersede/contradict) ──────────────────────────────────────────────────

def _attr_value_claim(value: Any, claim: ClaimRecord) -> AttrValueClaim:
    """One retained attribute value + the time axes its claim asserted it over (D7, §1B).

    ``report_time`` is the upper bound on the value's validity where no explicit interval was stated —
    computed by the pure :func:`report_bounded_validity` helper (no clock/parse — G1). Pure record; no
    ordering or supersede decision is taken here (deferred to Stage 3B).
    """
    valid_from, valid_until = report_bounded_validity(claim.event_time, claim.report_time)
    return AttrValueClaim(
        value=value,
        claim_id=claim.claim_id,
        event_time=claim.event_time,
        report_time=claim.report_time,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def _series_sort_key(entry: AttrValueClaim) -> tuple[bool, str, str, str]:
    """Deterministic oldest→newest order for a retained attribute series (data availability, not a decision).

    Ordered by ``event_time`` lower bound, then ``report_time`` lower bound, then ``claim_id`` (unique →
    a total, hash-seed-independent order — G2). Undated entries sort last. This is presentation ordering
    for the retained series; it makes no supersede/contradiction/winner decision (that is Stage 3B).
    """
    ev_lo, _ = canonical_iso_bounds(entry.event_time)
    rep_lo, _ = canonical_iso_bounds(entry.report_time)
    return (ev_lo is None, ev_lo or "", rep_lo or "", entry.claim_id)


def _assemble(
    resolved: list[ClaimRecord],
    entity_canonical: dict[str, str] | None = None,
    endpoint_node_types: dict[str, str] | None = None,
    lane: EdgeLaneIndex | None = None,
    node_types: NodeTypeIndex | None = None,
    display_names: dict[str, str] | None = None,
    routing: LayerRouting | None = None,
    outcome: RoutingOutcome | None = None,
) -> tuple[dict[str, NodeView], list[EdgeView], list[EventView]]:
    nodes: dict[str, NodeView] = {}
    events: list[EventView] = []
    edge_groups: dict[str, list[ClaimRecord]] = defaultdict(list)
    # Layer routing (A2/A3/A4) always runs; what it *does* is whatever the ontology declares (an ontology
    # that declares no `materializes`, no `instance_split` and no `instance_key_tag` routes nothing).
    # `outcome` is an OUT-parameter rather than a fourth return value on purpose: the 3-tuple signature is
    # what every existing caller (and every independently-authored test) already binds.
    routing = routing or LayerRouting()
    outcome = outcome if outcome is not None else RoutingOutcome()
    # Relationship claims are buffered rather than grouped inline: the `instance_key_tag` sub-bucket is read
    # off a NODE attribute (a site's `site_type`), so every entity claim has to have landed before any edge
    # can be keyed. Grouping order is preserved (buffer order == replay order) and the view is sorted at the
    # end regardless, so nothing observable moves (gate G2).
    triples: list[ClaimRecord] = []
    # A merge reconnects edges: a triple's raw subject/object (supersede.py reads these directly) is
    # remapped to the merged entity's canonical id. Empty map ⇒ identity ⇒ view unchanged (gate G2).
    canon = entity_canonical or {}

    def to_canonical(ref: str) -> str:
        return canon.get(ref, ref)

    def display(node_id: str, name: str | None) -> str | None:
        """The analyst-curated prose name for a node, if the entity registry declares one (T3b-E).

        ``config/entities.yaml``'s ``display_name`` already exists for exactly this case and the ASK
        agent already honours it (``agent/context.py``) — the *view* simply never did, so the graph and
        the answers disagreed about what one node is called. The sharp instance: ``unit_hq9b``'s only
        corpus-attested surface forms are its OPERATOR ("PAF", "Pakistan Air Force"), which the registry
        deliberately seeds as aliases; whichever claim replayed first then named the node, and the
        relocation beat rendered as "Pakistan Air Force moved from Nur Khan to Rahwali". An air force did
        not relocate; one fire unit did. This invents nothing — it surfaces the name an analyst already
        wrote down, with its rationale, in config. No ``display_name`` ⇒ the claim's own name (gate G2).
        """
        return (display_names or {}).get(node_id) or name

    def refined(node_type: str, name: str | None) -> str:
        """The ontology's node-type refinement for a claim-declared type (T3b-A).

        The SAME ``NodeTypeIndex.refine`` RESOLVE calls, so the type the resolver blocked and scored on
        and the type the view renders can never disagree — the ``edge_instance_key`` precedent. Absent
        index ⇒ the declared type, unchanged (gate G2).
        """
        return node_types.refine(node_type, name) or node_type if node_types else node_type

    for c in resolved:
        rr = c.resolved_ref
        payload = c.payload
        # Narrow on the payload type (isinstance) — the validator guarantees it matches `asserts`.
        if isinstance(payload, EntityDescriptor):
            raw = rr.entity_id if rr and rr.entity_id else f"ent:{payload.entity_type}:{payload.name}"
            nid = to_canonical(raw)
            node = nodes.get(nid)
            if node is None:
                node = NodeView(
                    id=nid,
                    type=refined(payload.entity_type, payload.name),
                    name=display(nid, payload.name),
                )
                nodes[nid] = node
            if c.claim_id not in node.claim_ids:
                node.claim_ids.append(c.claim_id)
            for k, v in payload.attrs.items():
                node.attrs.setdefault(k, v)  # scalar contract UNCHANGED: first claim wins (replay order)
                # ADDITIVE (D7, §1B): retain EVERY asserted value with its time axes — role-agnostic, so a
                # later/conflicting value is just another entry rather than a silently-dropped one.
                node.attr_history.setdefault(k, []).append(_attr_value_claim(v, c))
            if node.location is None:
                node.location = _node_location(payload.attrs)  # first claim wins, as the attrs do
        elif isinstance(payload, EventDescriptor):
            eid = rr.entity_id if rr and rr.entity_id else f"event:{c.claim_id}"
            events.append(
                EventView(
                    id=eid,
                    event_type=payload.event_type,
                    time_interval=payload.time_interval,
                    location=payload.location,
                    participants=[to_canonical(p) for p in payload.participants],
                    attrs=dict(payload.attrs),
                    claim_ids=[c.claim_id],
                )
            )
        else:  # Triple (relationship)
            # An identity assertion is CONSUMED, not drawn (D-2.5/P3.2). "A same-as B" is a statement
            # about who two names refer to, and the knowledge layer already expresses that answer — by
            # merging them, or by leaving them apart with a candidate edge the analyst can adjudicate.
            # Drawing it as well produced a third thing: dozens of self-loops and twin nodes for the very
            # designators resolution had just reconciled. The claim itself is untouched in the evidence
            # log and still visible in the merge breakdown that cites it. `distinct-from` is the exact
            # opposite and stays drawn — an invisible veto is indistinguishable from a missing edge.
            # In-document coreference is the same kind of statement (an answer about identity), reached by
            # reading one document's discourse rather than by asserting an alias, so it is consumed on the
            # same terms: it either became a merge or it is sitting in the candidate queue with its
            # licensing quote. Drawing it too would re-introduce exactly the twin-node picture above.
            if payload.predicate in IDENTITY_PREDICATES or payload.predicate == COREF_PREDICATE:
                continue
            triples.append(c)

    # ── the straddle split (A2/D-13.5) ────────────────────────────────────────────────────────────
    # Runs after every entity claim has folded, so a node's full attribute set is visible: the trigger is a
    # property of the whole node, not of whichever claim happened to arrive first. Before the edges are
    # keyed, so a split node's edges attach to the right half.
    if node_types is not None:
        split_straddlers(nodes, node_types, routing, outcome)

    ep_types = endpoint_node_types or {}
    for c in triples:
        payload = cast(Triple, c.payload)
        # Remap endpoints through the merge map so build_instance_edges (which reads the raw
        # subject/object) attaches the edge to the canonical nodes. No-op when nothing merged.
        subj, obj = to_canonical(payload.subject), to_canonical(payload.object)
        if lane is not None and node_types is not None:
            # A4/D-13.6 — endpoint identity is resolved HERE, in the derived layer, never baked into the
            # immutable claim: an instance-layer edge materializes the instance it implies, a holding edge
            # mints nothing, and an edge whose ontology demands a STATED endpoint is withheld rather than
            # pointed at one the build had to invent (D12).
            routed = route_triple(
                c, subj, payload.predicate, obj,
                nodes=nodes, endpoint_types=ep_types, lane=lane,
                node_types=node_types, layers=routing, outcome=outcome,
            )
            if routed is None:
                continue
            subj, obj = routed
        if (subj, obj) != (payload.subject, payload.object):
            c = c.model_copy(update={"payload": payload.model_copy(update={"subject": subj, "object": obj})})
        # Group corroborating claims by the edge's RESOLVED identity — recomputed here from the
        # *canonical* endpoints, NOT read from `rr.edge_instance`. That stored ref was minted by
        # `base_ref` from the claim's PRE-resolution surface strings, so the moment resolution merges an
        # endpoint the ref still names the old designator while the EdgeView `id` (built by
        # `build_instance_edges` from `subj`/`obj`) names the canonical one. The two then disagree, one
        # logical edge fragments across several ei-buckets carrying the same `id`, and the later re-key
        # on `el.id` overwrites all but the last bucket — silently stranding the corroborating claims on
        # unscored rows (residual #16). Rebuilding the key through the SAME `lane` builder RESOLVE uses
        # reproduces `rr.edge_instance` byte-for-byte whenever nothing merged (canonical ≡ raw), so
        # unmerged graphs are unchanged (gate G2); merged endpoints now pool onto one edge. A functional
        # edge (`based-at`) still keys on the subject alone on both paths (EVAL RCA §2.1 / D-P4.4).
        # Absent a lane (a caller with no ontology in hand) fall back to the stored ref, then the default.
        # NOTE the `instance_key_tag` sub-bucket (R1.3/C1) is deliberately NOT applied here. It de-conflicts
        # one subject's basings by kind of place, which is only sound when EVERY basing of that subject has a
        # known class — otherwise tagging the known ones separates the unknown one from them, and separation
        # is de-confliction, the thing C7's third state forbids. That decision therefore needs the whole
        # subject in view, including the rebuild-derived basings that do not exist yet, so it is a post-pass
        # (`layers.retag_instances`, called from `rebuild()` after the derivation). Until then every edge
        # keys exactly as it does with routing off.
        rr = c.resolved_ref
        if lane is not None:
            ei = lane.edge_instance_key(subj, payload.predicate, obj)
        elif rr and rr.edge_instance:
            ei = rr.edge_instance
        else:
            ei = f"edge:{subj}:{payload.predicate}:{obj}"
        edge_groups[ei].append(c)

    edges: list[EdgeView] = []
    for ei, cs in edge_groups.items():
        edges.extend(build_instance_edges(ei, cs))
    edges.extend(outcome.link_edges)
    for predicate, endpoint, end in outcome.withheld:
        outcome.gaps.append(withheld_edge_gap(predicate, endpoint, end))

    # Never leave an edge dangling: materialise a referenced-but-undeclared node, citing the edge's
    # claims as its (weak) provenance so gate G4 (every node carries ≥1 claim_id) still holds. RESOLVE
    # types such an endpoint from the edge's own domain/range where the ontology allows it (RES-1), so
    # this materialises a real typed node; ``unknown`` now means only "the ontology could not type it",
    # which is an honest gap rather than the id-namespace artefact it used to be.
    for e in edges:
        for endpoint in (e.source, e.target):
            if endpoint not in nodes:
                node_type = ep_types.get(endpoint, "unknown")
                nodes[endpoint] = NodeView(
                    id=endpoint,
                    type=node_type,
                    name=display(endpoint, _endpoint_display_name(endpoint)),
                    claim_ids=list(e.claim_ids),
                )

    apply_design_citations(nodes, outcome)
    label_provisional_instances(nodes, outcome)

    # Time-order each retained attribute series (oldest→newest). Deterministic; carries no decision.
    for node in nodes.values():
        for series in node.attr_history.values():
            series.sort(key=_series_sort_key)

    return nodes, edges, events


def _node_location(attrs: dict[str, Any]) -> Location | None:
    """Surface the frozen ``Location`` INGEST stamped into an entity's attrs as the node's ``location``.

    The canonical coordinate was always on the claim; it simply had no home on the view element, so the
    map, ``observe/dsl``'s ``location.*`` fields and ``agent/tools`` had nothing to read — and RESOLVE's
    place match had nowhere to land. Anything that is not a well-formed frozen ``Location`` is left alone
    rather than guessed at (an entity with no coordinate keeps ``location = None``, gate G2).
    """
    value = location_attr(attrs)
    if not isinstance(value, dict):
        return None
    try:
        return Location.model_validate(value)
    except ValidationError:
        return None


# Where the *evidence* for a place binding is rendered. Not bookkeeping: "snapped to Rahwali from 16 m"
# and "pulled to it from 2.8 km" are different claims, and the analyst is the one who has to tell them
# apart before trusting a location. Kept as node attrs so any consumer reads them without a new schema.
PLACE_MATCH_BAND = "place_match_band"
PLACE_MATCH_DISTANCE_M = "place_match_distance_m"
PLACE_MATCH_VIA = "place_match_via"

# Where the DRAWN point came from, and how big the honest doubt around it is (T5). A coordinate is a
# claim like any other, and these two attrs are the only thing standing between "we read a grid
# reference off the document" and "we looked its province up in a table" — which a map that renders
# both as the same pin quietly erases.
#   stated-coordinate → the source itself gave a position; the node's own frozen WGS84 point is used.
#   gazetteer-anchor  → the source named a curated place; the ANCHOR's coordinate is borrowed, and the
#                       anchor's precision class is what the node may claim (never finer).
LOCATION_SOURCE = "location_source"
LOCATION_SOURCE_STATED = "stated-coordinate"
LOCATION_SOURCE_ANCHOR = "gazetteer-anchor"
LOCATION_UNCERTAINTY_RADIUS_M = "location_uncertainty_radius_m"

# The precision ladder, finest first (md/13 §1 + the ``province`` rung T5 added). Ordering it here is
# what lets the view weigh two *independent* statements of how well a thing is located: what the
# surface form pinned ("a 5-digit grid reference" → pad) and what the curated anchor is known to
# ("PAF Base Nur Khan" → site). Both are evidence, so a node that resolves cleanly keeps the finer of
# the two — otherwise adopting an anchor would silently DOWNGRADE a document that handed us a grid.
PRECISION_LADDER: tuple[str, ...] = ("pad", "site", "terminal", "district", "city", "province")


def _finer_precision(a: str | None, b: str | None) -> str | None:
    """The finer of two precision classes; an unknown/unranked class never wins over a ranked one."""
    ranked = [p for p in (a, b) if p in PRECISION_LADDER]
    if not ranked:
        return a or b
    return min(ranked, key=PRECISION_LADDER.index)


def _stamp_place_refs(
    nodes: dict[str, NodeView], partition: Partition, places: PlacesConfig | None = None
) -> None:
    """Write RESOLVE's gazetteer match onto the node — the writer ``resolved_place_ref`` never had (RES-3).

    Only **curated** ``config/places.yaml`` anchors are ever referenced. A mention that matched none is
    absent from ``place_refs``: it keeps its own raw coordinate and carries no ref, which is the honest
    outcome (an incidental pin, not a named anchor) rather than a failure to fix. The frozen ``Location``
    is a value object, so it is replaced with a copy, never mutated in passing. Empty map ⇒ no-op (G2).

    **Anchor adoption (T5).** When the matched node holds no coordinate of its own — the ordinary case
    for a stated toponym, since the keyless boot path has no geocoder and a gazetteer lookup is not
    INGEST's to make on the evidence layer — it adopts the anchor's ``canonical_dd`` and the anchor's
    ``precision_class``. This is a *derived-layer* inference and is labelled as one: the frozen claim
    still says only "central Punjab", and the node says "placed at the Punjab anchor, province
    precision, ±150 km". Nothing is invented — an entity that matches no anchor gets no coordinate and
    stays deliberately unplotted rather than being nudged onto the nearest thing with a number.
    """
    by_id = places.as_map() if places is not None else {}
    radii = dict(places.proximity_radius_m) if places is not None else {}
    for nid, ref in sorted(partition.place_refs.items()):
        node = nodes.get(nid)
        if node is None:
            continue  # a match on an entity no claim materialised as a node — nothing to stamp
        base = node.location or Location(raw=node.name or node.id)
        update: dict[str, Any] = {"resolved_place_ref": ref.place_id}
        anchor = by_id.get(ref.place_id)
        adopted = (
            anchor is not None and anchor.canonical_dd is not None and base.wgs84_lat is None
        )
        if adopted and anchor is not None and anchor.canonical_dd is not None:
            lat, lon = anchor.canonical_dd
            update.update(wgs84_lat=float(lat), wgs84_lon=float(lon),
                          precision_class=anchor.precision_class)
        elif anchor is not None and ref.band == "auto":
            # The node brought its own coordinate AND cleanly resolved to a curated anchor: two
            # statements about the same fix. Keep the finer. This is what stops a 4-decimal DD pair
            # buried in prose — parsed, correctly, as a degree-scale DMS by shape — from being drawn
            # as a 15 km blob when the analyst has curated that very spot as a pad.
            update["precision_class"] = _finer_precision(base.precision_class,
                                                         anchor.precision_class)
        node.location = base.model_copy(update=update)
        node.attrs[PLACE_MATCH_BAND] = ref.band
        if ref.distance_m is not None:
            node.attrs[PLACE_MATCH_DISTANCE_M] = ref.distance_m
        if ref.via:
            node.attrs[PLACE_MATCH_VIA] = ref.via
        if node.location.wgs84_lat is not None:
            node.attrs[LOCATION_SOURCE] = (
                LOCATION_SOURCE_ANCHOR if adopted else LOCATION_SOURCE_STATED
            )
    _stamp_uncertainty(nodes, radii)


def _stamp_uncertainty(nodes: dict[str, NodeView], radii: dict[str, float]) -> None:
    """Attach the uncertainty envelope every plotted point is entitled to, from the config radii.

    Runs over *every* located node, not only anchor-matched ones, so a coordinate parsed straight out
    of a document is described on the same axis as one borrowed from the gazetteer: a 4-decimal DD pair
    is a ``pad`` (±500 m), a degree-only DMS is a ``city`` (±15 km). A node whose precision class is
    unknown gets no radius rather than a guessed one — the map draws that as an explicitly unsized pin.
    """
    if not radii:
        return
    for node in nodes.values():
        loc = node.location
        if loc is None or loc.wgs84_lat is None or not loc.precision_class:
            continue
        radius = radii.get(loc.precision_class)
        if radius is not None:
            node.attrs[LOCATION_UNCERTAINTY_RADIUS_M] = float(radius)
        node.attrs.setdefault(LOCATION_SOURCE, LOCATION_SOURCE_STATED)


def _minted_name(node_id: str) -> str | None:
    """The display name inside a minted endpoint id (``ent:<type>:<name>``), else None.

    RESOLVE mints an endpoint node as ``ent:<type>:<surface form>``, so the designator the document
    actually used is recoverable for display/search without a second channel. Split is bounded at 2 so a
    name containing ``:`` survives intact. A stable-id node (``var_hq9p``) never reaches here — it is
    claim-backed and already materialised above.
    """
    parts = node_id.split(":", 2)
    return parts[2] if len(parts) == 3 and parts[0] == "ent" and parts[2] else None


def _endpoint_display_name(node_id: str) -> str | None:
    """The designator to SHOW for a materialised endpoint — typed or ``unknown`` (T3b-D).

    A typed endpoint is minted as ``ent:<type>:<surface form>`` and unwraps via :func:`_minted_name`. An
    endpoint the ontology could not type is never minted at all: it stays the raw surface form, so **the
    id IS the designator**. Rendering it nameless was the reason the graph showed a bare
    ``HQ-9/P TEL`` id with type ``unknown`` — the one piece of information the analyst needed (what the
    document actually called it) was on the node the whole time and simply not surfaced.

    A name is a display concern, not an identity one: it does not make the node resolvable. These nodes
    fail to resolve because RESOLVE left them as untyped mentions rather than entities, which is fixed
    at the typing layer (``resolve._edge_allowed_types``), not here.
    """
    return _minted_name(node_id) or node_id or None


# ── HITL decision effects (real F0, gate G12) ─────────────────────────────────────────────────

def apply_decision_effects(view: GraphView, decisions: Iterable[DecisionRecord]) -> GraphView:
    """Apply decision-log ``effects`` to the view — this is what makes HITL propagation structural.

    An analyst ``status_override`` sets the element's status (legitimately overriding the machine —
    the whole point of gate G12); an ``integrity_flag`` adds a flag to the confidence breakdown.
    """
    idx: dict[str, NodeView | EdgeView | EventView] = {}
    for n in view.nodes:
        idx[n.id] = n
    for e in view.edges:
        idx[e.id] = e
    for ev in view.events:
        idx[ev.id] = ev

    for d in decisions:
        effects = d.effects or {}
        set_status = effects.get("set_status")
        if isinstance(set_status, dict):
            for elid, status in set_status.items():
                el = idx.get(elid)
                if el is not None:
                    el.status = status
        add_flag = effects.get("add_integrity_flag")
        if isinstance(add_flag, dict):
            el = idx.get(add_flag.get("element_id", ""))
            if el is not None:
                if el.confidence is None:
                    el.confidence = ConfidenceBreakdown()
                flag = add_flag.get("flag")
                if flag:
                    el.confidence.integrity_flags = sorted(set(el.confidence.integrity_flags) | {flag})
    return view


# ── the orchestrator ─────────────────────────────────────────────────────────────────────────

def _prepare_active_claims(
    evidence: object, decision: object, config: ConfigBundle
) -> tuple[list[ClaimRecord], list[DecisionRecord]]:
    """``rebuild()``'s claim-preparation prologue, factored out so a *second* pure read of the resolution
    state (Stage-4 identity coverage, ``partition_with_types``) prepares claims through the EXACT same
    path — zero drift risk. In order:

    * replay both logs;
    * ``apply_retractions`` — drop retracted claims (append-only, gate G3);
    * ``apply_claim_exclusions`` — HITL reject drops the look upstream of scoring;
    * the ``config.credibility.as_of`` rewind — a *past* as-of hides claims not yet available then, an
      honest point-in-time view (``is_available_by`` is clock-free — G1); unset/future ⇒ no-op (G2);
    * ``canonicalize_claims`` — orient relationship claims the producer did not canonicalize so
      oppositely-phrased claims of one fact key to the same ``edge_instance`` and corroborate; a no-op
      when the ontology declares no directions, reorienting only this derived view, never the log.

    Pure & deterministic (G1/G2).
    """
    claims: list[ClaimRecord] = _replay(evidence, ClaimRecord)
    decisions: list[DecisionRecord] = _replay(decision, DecisionRecord)
    active = apply_retractions(claims)
    active = apply_claim_exclusions(active, decisions)
    if config.credibility.as_of:
        active = [c for c in active if is_available_by(c, config.credibility.as_of)]
    active = canonicalize_claims(active, config)
    active = _drop_superseded_derivations(active, config)
    return active, decisions


def _drop_superseded_derivations(claims: list[ClaimRecord], config: ConfigBundle) -> list[ClaimRecord]:
    """Ignore frozen ``inference`` claims whose derivation ``rebuild()`` now performs itself (A4/D-13.6).

    The offline basing pass used to **mint** its conclusion into the append-only log. That pass is deleted,
    and the same edge is materialized in the derived layer every rebuild — so those frozen claims are not
    evidence, they are stale *output* of a mechanism that no longer exists. Reading them as evidence would
    double-count the derivation and let a conclusion outlive its premises.

    This is a **derived-layer read**, not a retraction: the claims stay in the log, still replayable, still
    inspectable, exactly as ``as_of`` rewinding and HITL exclusion leave their inputs alone. Which
    ``derived_layer`` values are superseded is declared in config; an empty declaration retires nothing.
    """
    routing = LayerRouting.from_ontology(config.ontology)
    if not routing.superseded_derived_layers:
        return claims
    retired = set(routing.superseded_derived_layers)
    return [
        c for c in claims
        if not (c.kind == "inference" and (c.attributes or {}).get("derived_layer") in retired)
    ]


def partition_with_types(
    evidence: object, decision: object, config: ConfigBundle
) -> tuple[Partition, dict[str, str]]:
    """The resolver's identity :class:`Partition` + its entity→type map, from the same logs + config
    ``rebuild()`` reads — the inputs the Stage-4 coverage summary (``GET /coverage``) folds over.

    Claims are prepared through the identical prologue :func:`_prepare_active_claims`, so this reproduces
    the partition behind the current view exactly; ``prev_view`` is irrelevant to the partition
    (``resolve`` does not read it), so it is not needed here. A SEPARATE derivation from the drawn view —
    it computes no nodes/edges and never touches the view JSON (gate G2).
    """
    active, decisions = _prepare_active_claims(evidence, decision, config)
    return resolve_with_types(active, config, None, decisions)


def rebuild(evidence: object, decision: object, config: ConfigBundle, prev_view: GraphView | None = None) -> GraphView:
    """Reduce the two logs + config to the knowledge view — pure & deterministic (G1, G2)."""
    active, decisions = _prepare_active_claims(evidence, decision, config)

    # 1. resolution — resolve() is a pure function of (claims, config, prev_view, decision log): the
    #    decision log carries the offline LLM proposer's frozen merge_proposal records + the analyst's
    #    replayed merge_adjudication(accept)s that grow the alias table (spine/03; still no live LLM — G1).
    partition = resolve(active, config, prev_view, decisions)
    resolved = _apply_partition(active, partition)

    # 2. assemble nodes/edges/events (+ supersede/contradict — real F0); the merge map reconnects a
    #    merged-away entity's edges to its canonical node (no-op when nothing merged). With layer routing
    #    on, this is also where a straddling mention splits and an instance-layer edge materializes the
    #    instance it implies (A2/A4) — endpoint identity is resolved in the derived layer, per rebuild.
    lane = EdgeLaneIndex(config.ontology)
    node_types = NodeTypeIndex(config.ontology)
    routing = LayerRouting.from_ontology(config.ontology)
    routing_outcome = RoutingOutcome()
    nodes, edges, events = _assemble(
        resolved,
        partition.entity_canonical,
        partition.endpoint_node_types,
        lane,
        node_types,
        {e.entity_id: e.display_name for e in config.entities.entities if e.display_name},
        routing,
        routing_outcome,
    )
    _merge_provenance(nodes, partition)  # accepted-merge audit trail on the canonical node
    _stamp_place_refs(nodes, partition, config.places)  # RES-3: curated-anchor binding + its evidence
    claims_by_id = {c.claim_id: c for c in resolved}
    sources = config.sources.as_map()

    # 2b. the DERIVED basing edge (A4/D-13.6/G17) — `<unit, based-at, site>` materialized here, citing its
    #     two premise claim-atoms, with no mint and no append. It runs before scoring so the derived edge is
    #     priced by the same machinery as every other edge (and capped by its gate flag, never confirmed).
    derivation = derived_basing.derive(
        nodes, edges, claims_by_id, config, lane, node_types, routing
    )
    edges.extend(derivation.edges)
    # 2c. NOW that every basing of every subject exists — stated and derived — apply the `site_type`
    #     sub-bucket, or take the third state (R1.3/C1/L1/C7). This is the only point at which the
    #     per-subject decision can be made correctly.
    derivation.gaps.extend(
        retag_instances(
            edges, nodes, lane, routing, order_instance_edges, derived_basing.edge_bounds
        )
    )
    derived_edge_ids = {e.id for e in derivation.edges}

    # 3. credibility (per-claim) — decisions carry analyst integrity flags (origin-wide, incl. future claims)
    credibility = score_claims(resolved, sources, config, decisions)

    # 4. per-assertion inputs: independence groups attached to each element
    elements: dict[str, NodeView | EdgeView | EventView] = {}
    for n in nodes.values():
        elements[n.id] = n
    for e in edges:
        elements[e.id] = e
    for ev in events:
        elements[ev.id] = ev

    # The clock-free evaluation "now" for freshness/staleness (pinned as_of, else newest claim).
    as_of = effective_as_of(config, resolved)

    assertions: list[AssertionInput] = []
    #: Elements whose sufficiency failed ONLY because their identity is refused — their gap is the richer
    #: `gap:identity:` one, so the generic per-element gap is skipped rather than duplicated.
    identity_gap_suppressed: set[str] = set()
    for eid, el in elements.items():
        groups = group_by_independence(el.claim_ids, claims_by_id, sources, config)
        el.supporting_claims = groups
        per_claim = {cid: credibility[cid] for cid in el.claim_ids if cid in credibility}
        kind = "node" if isinstance(el, NodeView) else ("edge" if isinstance(el, EdgeView) else "event")
        contradiction = bool(getattr(el, "attrs", {}).get("contradiction"))
        # Gates computed where claims + sources are in scope, so assign_status can enforce the caps
        # from the AssertionInput alone (spine/04 §3.4): deception (adversary-denial/decoy-risk),
        # freshness (aging/stale), and gated-attr-unknown (foreign_control/readiness).
        fresh_summary, fresh_flags = assertion_freshness(el.claim_ids, claims_by_id, as_of, config)
        gate_flags = deception_gate_flags(el, claims_by_id, sources)
        # Single-pass decoy: caps at probable only when the assertion is a lone look; a second
        # independent, clean look resolves it (spine/04 "single-pass"; keeps gate G7 satisfiable).
        if has_decoy_look(el, claims_by_id):
            min_g = getattr(config.credibility, "min_independent_groups", None)
            effective_looks = sum(g.weight for g in groups)
            if min_g is None or effective_looks < min_g:
                gate_flags.append("decoy-risk")
        gate_flags.extend(fresh_flags)
        gate_flags.extend(gated_attr_flags(el, config))
        if contradiction:
            gate_flags.append("contradiction")
        # A derived attribution cites its two premises DIRECTLY, which — left alone — would make it look
        # better corroborated than the sighting it rests on (two independent premise sources pool to two
        # independent looks). The old minted form got its ceiling for free, because an inference shared an
        # independence group with its premises. This flag restores it explicitly: derivation is the weaker
        # of the formation's two provenance paths and must not reach *confirmed* (D-13.13).
        if eid in derived_edge_ids:
            gate_flags.append(derived_basing.DERIVED_INFERENCE)
        a = AssertionInput(
            element_id=eid,
            element_kind=kind,
            per_claim_credibility=per_claim,
            groups=groups,
            opposing_claims=list(el.opposing_claims),
            has_unresolved_contradiction=contradiction,
            gate_flags=gate_flags,
            freshness=fresh_summary,
        )
        # Sufficiency runs BEFORE status so the confirmed gate can require it + the machine owns the
        # `insufficient` label (assessability ⊥ magnitude — spine/04 §3.7). AssertionInput.sufficiency
        # is the F0-frozen channel for exactly this (§4.3 "illustrative" order reconciled here).
        a.sufficiency = check(a, claims_by_id, config)
        assertions.append(a)

    # 4b. G19's REFUSE half, on the node itself — the half that never fired.
    #
    # An identity refusal says two sources disagree about what KIND of thing a mention is (or which operator
    # it belongs to). Until this ran, the only consequence was a Known Gap: the same rebuild published
    # `ent:variant:HT-233` as a first-class ORBAT variant at status CONFIRMED while emitting a gap saying that
    # mention's type is contradicted. Confirmed asserts "we have established this"; what we have established
    # is that two sources disagree about what it is.
    #
    # Routed through ``sufficiency`` rather than a second status writer, because assessability is exactly what
    # sufficiency is for (⊥ magnitude, spine/04 §3.7) and the machine must keep sole ownership of the label
    # (G5). `insufficient` then dominates, and the node says "insufficient evidence to assess" with `identity`
    # named as the missing slot.
    #
    # **It lands on the reading that is NOT better attested, and the asymmetry is deliberate.** A refusal hangs
    # off both endpoints because both mentions are un-anchored by it, but the two are not equally in doubt: one
    # side is a well-corroborated component with several independent looks, the other a single-claim mention a
    # lone extraction typed differently. Marking both unassessable would let one flaky mention shatter a
    # well-corroborated node — the failure `critical_veto_min_grade` exists to prevent one rail over. So the
    # weaker reading (fewer effective independent looks) carries the refusal; on a tie neither reading wins and
    # both carry it. The better-attested side is NOT let off: it keeps the per-endpoint `gap:identity:` record,
    # so the disagreement reaches the analyst on both nodes either way.
    _by_id = {a.element_id: a for a in assertions}
    _looks = {a.element_id: sum(g.weight for g in a.groups) for a in assertions}
    for _pair_ref in sorted(partition.identity_refusals):
        _ends = [
            partition.entity_canonical.get(e, e)
            for e in _pair_ref.split("|")
        ]
        _ends = [e for e in dict.fromkeys(_ends) if e in nodes and e in _by_id]
        if not _ends:
            continue
        _weakest = min(_looks.get(e, 0.0) for e in _ends)
        for _eid in _ends:
            if _looks.get(_eid, 0.0) > _weakest:
                continue  # the better-attested reading keeps its assessment (and its gap)
            _a = _by_id[_eid]
            _slots = list(_a.sufficiency.missing_slots) if _a.sufficiency else []
            if IDENTITY_SLOT not in _slots:
                _slots.append(IDENTITY_SLOT)
            if _a.sufficiency is None or _a.sufficiency.satisfied:
                # The richer `gap:identity:<pair>:<node>` gap below already names what is missing and what
                # would settle it, so the generic per-element gap would be the same finding twice — and a
                # register that lists one finding twice teaches an analyst to skim it.
                identity_gap_suppressed.add(_eid)
            _a.sufficiency = SufficiencyEval(
                satisfied=False,
                missing_slots=_slots,
                next_coverage_due=_a.sufficiency.next_coverage_due if _a.sufficiency else None,
                ceiling=(_a.sufficiency.ceiling if _a.sufficiency else None) or "confirmable",
                template_id=_a.sufficiency.template_id if _a.sufficiency else None,
            )

    # 5. status (batch) — reads a.sufficiency + a.gate_flags for the gate machine
    assessments = assign_status(assertions, config)

    # 6. attach status/confidence/freshness/sufficiency; emit a first-class Known Gap on a failed template
    known_gaps: list[KnownGap] = []
    for a in assertions:
        el = elements[a.element_id]
        suff = a.sufficiency
        el.sufficiency = suff
        el.freshness = a.freshness
        assess = assessments.get(a.element_id)
        if assess is not None:
            el.status = assess.status
            el.confidence = ConfidenceBreakdown(
                per_claim_credibility=a.per_claim_credibility,
                independence_groups=a.groups,
                integrity_flags=a.gate_flags,
                freshness_factor=a.freshness.decay_factor if a.freshness else None,
                assertion_confidence=assess.assertion_confidence,
            )
        if suff is not None and not suff.satisfied and a.element_id not in identity_gap_suppressed:
            known_gaps.append(
                KnownGap(
                    id=f"gap:{a.element_id}",
                    related_ref=a.element_id,
                    what_missing=(suff.missing_slots[0] if suff.missing_slots else "evidence requirement unmet"),
                    observability_ceiling=suff.ceiling or "confirmable",
                    next_coverage_due=suff.next_coverage_due,
                    missing_slots=list(suff.missing_slots),
                )
            )

    # 6b. supersession floor (D-P4.4 iv) — runs HERE, after the status machine and before materiality,
    #     because the gate is a question about the *newer* assertion's confidence + deception flags,
    #     which do not exist until step 5. `view/supersede.py` (step 2) could only order the pair.
    #     Promoting writes the superseded_by/supersedes link, re-runs the status machine over the
    #     retired edge (→ stale, via the `superseded` gate flag) and draws the node→node `supersedes`
    #     edge; failing the floor leaves the pair as `candidate_supersede` for the analyst.
    # R1.4's two prohibitions are unconditional. They are what closes the fabrication path: without them a
    # sub-confirmed identity promotes, the analyst's candidate is popped off the queue, the retired assertion
    # is restated `stale` (asserting it was once established) and a differing target draws a relocation
    # nobody reported. The two are independent: (a) asks whether this is one unit, (b) whether we ever
    # established the origin at all.
    #
    # "Unsettled" is the OPEN CANDIDATE MERGE — every endpoint of a same-as the resolver put in front of the
    # analyst and nobody has adjudicated. Deliberately not the node's assessed status: the legitimate
    # flagship relocation sits at *probable*, so reading the confidence label would suppress the beat this is
    # meant to leave working. The question is whether the IDENTITY DECISION is still open.
    unsettled = {eid for pair in partition.candidates for eid in pair}
    supersede_outcome = promote_supersessions(edges, config, nodes, unsettled)
    edges.extend(supersede_outcome.drawn_edges)
    # A retired assertion is history, not a coverage gap: drop the "insufficient evidence" Known Gap it
    # raised while it was still being assessed as a live fact. The gap would tell an analyst to go
    # collect on a position the graph has just established the subject has LEFT — the opposite of the
    # honest-refusal contract, which is about what we cannot assess, not about what has been overtaken.
    #
    # R1.4(b) — and the deletion is now both NARROW and non-silent. `retired_element_ids` already excludes
    # every assertion whose evidence requirement was unmet: an `insufficient` is a *refusal to assess*, not a
    # weak assessment, so calling it `stale` would say "we knew this and it has been overtaken" about
    # something we never knew, and dropping its gap would remove the only record that we still cannot assess
    # it. Those keep both their label and their gap. A WELL-EVIDENCED retirement is untouched — it reads
    # `stale` and its gap (it has none) is moot; R1.4(b) protects an honest refusal, it does not disable
    # retirement. Where a gap IS dropped, the retired edge records which one, so the drop is auditable
    # rather than a disappearance.
    retired = set(supersede_outcome.retired_element_ids)
    if retired:
        absorbed = {g.related_ref: g.id for g in known_gaps if g.related_ref in retired}
        for edge in edges:
            if edge.id in absorbed:
                edge.attrs["retired_known_gap"] = absorbed[edge.id]
        known_gaps = [g for g in known_gaps if g.related_ref not in retired]
    # G19's escalate half: a pair the evidence otherwise FUSED, refused by a type or namespace
    # contradiction. One gap PER ENDPOINT (the pair is what is contradicted, but a gap hangs off a node and
    # each of the two mentions is separately un-anchored by the refusal), so neither half is left with no
    # edge, no queue item and no record — which is what the cross-type refusal used to do.
    #
    # The endpoints are CANONICALISED before the membership test, for the same reason as the drawn resolution
    # edges: a refusal is keyed on RAW entity ids while nodes are named by canonical id, so a raw endpoint
    # that had itself been merged failed ``in nodes`` and its gap was dropped — 5 of the 14 endpoints on the
    # booted corpus. The escalate half then fired for the pair and reached the analyst for one of its two
    # mentions, or for neither.
    for pair_ref, what_missing in sorted(partition.identity_refusals.items()):
        seen_refs: set[str] = set()
        for endpoint in pair_ref.split("|"):
            ref = partition.entity_canonical.get(endpoint, endpoint)
            if ref in nodes and ref not in seen_refs:
                seen_refs.add(ref)
                known_gaps.append(
                    KnownGap(
                        id=f"gap:identity:{pair_ref}:{ref}",
                        related_ref=ref,
                        what_missing=what_missing,
                        observability_ceiling="confirmable",
                        missing_slots=[IDENTITY_SLOT],
                    )
                )
    # …and the escalation for a pair a cap withheld from the QUEUE on a ground a source stated
    # (``withheld_escalations``). Same per-endpoint rendering as the refusal above and the same
    # canonicalisation, but it never touches either node's status: the pair being held apart is the correct
    # outcome here, and what is open is only WHY the source and the score disagree. Empty on the shipped
    # config (`contrast_ceiling: probable` keeps the queue place, so nothing is re-routed).
    for pair_ref, what_missing in sorted(partition.withheld_escalations.items()):
        seen_refs = set()
        for endpoint in pair_ref.split("|"):
            ref = partition.entity_canonical.get(endpoint, endpoint)
            if ref in nodes and ref not in seen_refs:
                seen_refs.add(ref)
                known_gaps.append(
                    KnownGap(
                        id=f"gap:withheld:{pair_ref}:{ref}",
                        related_ref=ref,
                        what_missing=what_missing,
                        observability_ceiling="confirmable",
                        missing_slots=[IDENTITY_SLOT],
                    )
                )
    # The routing's + derivation's own named gaps: an unrouted straddle, a suppressed supersede, a withheld
    # relation, a truncated formation attribution. Appended AFTER the retirement filter — these are not
    # assertions that could be retired, they are statements about what the build could not conclude.
    known_gaps.extend(routing_outcome.gaps)
    known_gaps.extend(derivation.gaps)
    # One gap per missing thing. Several mechanisms can independently notice the same absence (two claims
    # withheld against one endpoint, a gap raised on an element that also carries a routing gap), and a
    # register that lists the same finding twice reads as two findings — which is how an analyst learns to
    # skim it. First occurrence wins, so the order above (assessment gaps, then routing, then derivation) is
    # the precedence, and it is deterministic (gate G2).
    _seen_gaps: set[str] = set()
    known_gaps = [g for g in known_gaps if not (g.id in _seen_gaps or _seen_gaps.add(g.id))]

    view = GraphView(
        nodes=list(nodes.values()),
        edges=edges,
        events=events,
        known_gaps=known_gaps,
    )

    # 7. materiality precompute — inside rebuild, tracks config automatically (spine/09)
    view = precompute(view, config)

    # 8. HITL decision effects last (an override wins over the machine — gate G12)
    view = apply_decision_effects(view, decisions)

    # 8b. render the resolver's decisions as edges — candidate same-as (HITL band) + distinct-from
    #     traps. Added AFTER scoring so they're never assigned a truth status (G5); G4-exempt.
    view.edges.extend(_resolution_edges({n.id for n in view.nodes}, partition))

    # 9. deterministic ordering + diagnostic meta (no clock, no RNG — G2)
    view = sorted_view(view)
    view.meta = {
        "config_version": config.version,
        "node_count": len(view.nodes),
        "edge_count": len(view.edges),
        "event_count": len(view.events),
        "known_gap_count": len(view.known_gaps),
    }
    return view
