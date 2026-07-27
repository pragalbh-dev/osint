"""The derived basing edge — ``<unit, based-at, site>``, materialized **inside** ``rebuild()`` (A4/D-13.6).

*Usually* no open source states the fact the order-of-battle question needs. A satellite write-up says
*"six TEL-type objects consistent with HQ-9B occupy a revetment complex at PAF Base Nur Khan, 09 OCT
2021"*; an induction announcement says *"the HQ-9/P has entered service with Army Air Defence"*. Neither
says **"formation X is based at site Y"** — the edge the relocation beat, the freshness decay and the
supersede all hang on. So it is *derived*, from those two premises.

**What changed, and why it is not a relocation of the old pass.** That derivation used to run offline
(``ingest/basing.py``): it **minted** a ``kind="inference"`` ``ClaimRecord`` and **appended** it to the
evidence log, freezing derived output into the append-only record. That is the bi-level architecture
inverted — the evidence layer is supposed to hold what sources said, and everything derived is supposed to
be recomputed. A frozen inference also silently *outlives its premises*: re-record the sources and the
conclusion still sits in the log pointing at stale ids.

So the pass is **deleted**, not moved, and the edge is now a *pure knowledge-layer derivation* exactly like
``resolve`` or ``score``: recomputed every rebuild, **citing its two premise claim-atoms** so provenance is
still one click away, with **no mint and no append anywhere under ``rebuild()``** (gate G17). Nothing here
constructs a ``ClaimRecord`` or calls ``make_claim_id``; it builds ``EdgeView``s over claims that already
exist.

**The stated path is stronger and is not this.** When a source *names the formation at a site* — an ORBAT
reference, a military-balance yearbook — that is a **stated** ``based-at`` (``kind="observation"``,
extractor-emitted, normal source credibility, able to reach *confirmed* with independent corroboration).
This derivation is the **fallback** for the common case where formation-at-site is unstated; it is capped by
construction and never displaces a stated basing. *Stated ≠ trusted*, either: a grade-E spoof naming a unit
at a site still runs through source grade and the deception gates and lands at *possible*.

**Never a silent pick (R2.1 / G15's biting clause).** Where the observed equipment is associated with more
than one candidate formation, the old pass took ``formations[:max_units]`` and recorded **nothing** about
the ones it dropped — while every other rejection path in it appended a skip record. That is an
order-of-battle undercount with **no merge involved**, which is precisely why neither G15 nor G16 could see
it. Here, exceeding the configured fan-out produces a **named gap** that names the discarded candidates:
two candidate formations yield two attributions, or one plus an explicit gap. Never a silent pick.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from chanakya.ontology import EdgeLaneIndex, LayerRouting, NodeTypeIndex
from chanakya.schemas import ClaimRecord, ConfigBundle, DateValue, EdgeView, KnownGap, NodeView
from chanakya.schemas.values import canonical_iso_bounds

from .supersede import order_instance_edges

_SITE_TYPE = "basing_site"
_UNIT_TYPE = "unit"
_OCCUPANCY_ATTR = "occupancy_state"

#: Fallback affirmative-occupancy vocabulary, used only when config declares none. It is a **denylist
#: input**, not a scoring number: a source that says the site is *empty* must never ground a positive
#: basing. The same vocabulary is applied by the imagery lane's corroboration gate
#: (``ingest/imagery._OCCUPIED_TOKENS``), and the two must agree or "an empty site is not a deployment"
#: means two different things in two places. It is read from
#: ``credibility.yaml → basing_proposer.occupied_tokens`` so that agreement is a config edit rather than a
#: code edit — and so that nothing under ``rebuild()`` has to import an ``ingest`` module at all, which
#: would drag ``make_claim_id`` into the rebuild-reachable call graph and trip G17's static scan.
_DEFAULT_OCCUPIED_TOKENS = frozenset(
    {"occupied", "garrison", "active", "deployed", "manned", "present", "occupation"}
)

#: Gate flag stamped on every derived attribution. Read by ``credibility.status`` as a **cap**: a derived
#: basing is an inference and must not reach *confirmed* however well its premises are corroborated, which
#: the old form got for free (a minted inference shared an independence group with its premises). Citing
#: the premises *directly* would otherwise make the derivation look better-corroborated than the thing it
#: rests on — the exact inversion D-13.13 forbids.
DERIVED_INFERENCE = "derived-inference"

_DERIVED_LAYER = "unit-attribution"

# Edge attrs written here (strings, never numbers — gate G6).
PREMISES = "premises"
DERIVED_VIA = "derived_via"
DERIVED_LAYER = "derived_layer"


@dataclass
class BasingDerivation:
    """The derived edges + every reason nothing was derived. Raise-only: this module writes no evidence."""

    edges: list[EdgeView] = field(default_factory=list)
    gaps: list[KnownGap] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (site_id, reason)


def _cfg(config: ConfigBundle) -> dict[str, object]:
    """The derivation's knobs, still ``credibility.yaml → basing_proposer`` (hot-config). ``{}`` ⇒ dormant.

    Deliberately the *same* block the deleted offline pass read: the knobs describe the derivation, and the
    derivation did not change — only *where and when* it runs. Re-homing them would have churned config for
    no gain and broken every deployment that had tuned them.
    """
    return dict(getattr(config.credibility, "basing_proposer", None) or {})


def _edge_type_list(cfg: dict[str, object], key: str) -> list[str]:
    """A declared list-of-edge-types knob, narrowed out of the untyped config block. Absent ⇒ ``[]``.

    The ``isinstance`` is load-bearing, not ceremony: a knob mis-authored as a bare string
    (``occupancy_edge_types: located-at``) would otherwise *iterate its characters* and hand the derivation a
    list of single letters to match edge types against — the same shape of defect already found on the
    ingest path, where a string was iterated where a container was meant. Refusing a non-container leaves
    the derivation dormant, which is the fail-safe direction: no derived basing rather than garbage basing.
    """
    value = cfg.get(key)
    return [str(x) for x in value] if isinstance(value, (list, tuple)) else []


def _upper(value: DateValue | None) -> str | None:
    return canonical_iso_bounds(value)[1]


def _states_vacancy(claim: ClaimRecord, occupied_tokens: frozenset[str]) -> bool:
    """Does this observation state the site is **not** occupied? An absence never grounds a presence.

    A denylist, not an allowlist: most sources state no occupancy word at all and demanding one would
    suppress every honest sighting — but a source saying the site is *empty* must never ground a positive
    basing. Without this, "TELs gone from the old site, 2025-06-11" derives a basing at the one place the
    document says the unit left.
    """
    if claim.polarity != "positive":
        return True
    word = (claim.attributes or {}).get(_OCCUPANCY_ATTR)
    if not isinstance(word, str) or not word.strip():
        return False
    return not any(tok in word.lower() for tok in occupied_tokens)


def _best_dated(
    edge: EdgeView, claims: dict[str, ClaimRecord], where: Callable[[ClaimRecord], bool] | None = None
) -> ClaimRecord | None:
    """The edge's most recently-*valid* backing claim — the grounding observation the derivation dates to.

    Ranked by ``event_time`` upper bound (a dated look beats an undated one; the later dated look wins),
    tie-broken by claim id so the choice is deterministic (G2). A derivation with no dated premise is still
    allowed — it inherits no ``event_time`` and is therefore unorderable, which is the honest outcome and
    exactly what the supersede rule treats as a candidate rather than a fact.
    """
    best: ClaimRecord | None = None
    best_key: tuple[int, str, str] | None = None
    for cid in edge.claim_ids:
        c = claims.get(cid)
        if c is None or (where is not None and not where(c)):
            continue
        hi = _upper(c.event_time)
        key = (1 if hi else 0, hi or "", c.claim_id)
        if best_key is None or key > best_key:
            best, best_key = c, key
    return best


def _inherited_time(observation: ClaimRecord) -> DateValue | None:
    """The **grounding observation's** valid time, carried across whole — the derived fact's own valid time.

    The date value is copied *as it stands* (shape, granularity and boundary source intact) rather than
    flattened: a derived fact must not read as more precisely dated than the observation it rests on. A
    vague "2025" stays vague, which is what lets the supersede rule tell "later" from "unorderable" instead
    of silently ranking a year label above a day-precise date.

    **It is the observation's time, not the later of the two premises' — a defect fixed here.** The old
    offline pass took the maximum over *both* premises. But the same ``inducted-into`` claim backs every
    attribution for a given unit, and :func:`_best_dated` always picks that edge's *newest* backing claim, so
    the maximum meant **every basing of that unit inherited one and the same induction date** — and two
    basings with identical dates are unorderable, so they read as a *contradiction* ("the unit is in two
    places at once") instead of a relocation. Measured on the real corpus: a 2021 sighting at the old site
    inherited a 2025 induction date and its genuine 2025 successor became a contradiction rather than a
    supersede. The frozen bundles masked it, having been recorded against a sparser earlier view.

    The observation is what dates an occupancy; the induction merely licenses attributing it to a unit. That
    is also what this module has always *said* — "the ``event_time`` is inherited from the grounding
    observation … which is why the observation had to be dated first" — so this restores the stated contract
    rather than choosing a new one.
    """
    return observation.event_time


def _is_locatable(node: NodeView) -> bool:
    """Is this site a place you could point to — a coordinate or a gazetteer match?

    "The unit is based at Punjab" is not a fact an analyst can task collection against or watch for a
    relocation (``md/13``'s precision spec). Requiring a located site is what stops one formation from
    acquiring a dozen derived "bases" that are really the regions its equipment was discussed in.
    """
    loc = node.location
    if loc is None:
        return False
    return loc.resolved_place_ref is not None or (
        loc.wgs84_lat is not None and loc.wgs84_lon is not None
    )


def _equipment_end(edge: EdgeView, nodes: dict[str, NodeView]) -> tuple[str, str] | None:
    """``(site_id, equipment_id)`` for an occupancy edge, or ``None`` if neither end is a site."""
    src, tgt = nodes.get(edge.source), nodes.get(edge.target)
    if tgt is not None and tgt.type == _SITE_TYPE and src is not None:
        return tgt.id, src.id
    if src is not None and src.type == _SITE_TYPE and tgt is not None:
        return src.id, tgt.id
    return None


def _formation_candidates(
    equipment_id: str,
    nodes: dict[str, NodeView],
    incident: dict[str, list[EdgeView]],
    claims: dict[str, ClaimRecord],
    formation_edges: list[str],
    hop_edges: list[str],
) -> list[tuple[str, ClaimRecord, str]]:
    """``(unit_id, backing claim B, edge type)`` for every formation the observed equipment serves in.

    Searched on the equipment node and one hop away over ``hop_edges`` — a *component* is observed at the
    site while the formation association hangs off the *variant* it equips, and (with routing on) a
    materialized *presence* reaches its design over ``instance-of``. Ranked most-evidenced first, then by
    unit id, so the pick is deterministic and the same equipment attributes to the same formation at every
    site it is seen at — the property that makes a relocation legible at all.
    """
    holders = [equipment_id]
    for e in incident.get(equipment_id, []):
        if e.type in hop_edges:
            holders.append(e.target if e.source == equipment_id else e.source)

    ranked: list[tuple[int, str, ClaimRecord, str]] = []
    seen: set[str] = set()
    for hid in holders:
        for e in incident.get(hid, []):
            if e.type not in formation_edges:
                continue
            other = e.target if e.source == hid else e.source
            node = nodes.get(other)
            if node is None or node.type != _UNIT_TYPE or other in seen:
                continue
            backing = _best_dated(e, claims)
            if backing is None:
                continue
            seen.add(other)
            ranked.append((-len(e.claim_ids), other, backing, e.type))
    ranked.sort(key=lambda r: (r[0], r[1]))
    return [(unit_id, backing, etype) for _, unit_id, backing, etype in ranked]


def _derived_edge(
    unit_id: str,
    site_id: str,
    equipment_id: str,
    obs: ClaimRecord,
    formation: ClaimRecord,
    observed_edge: str,
    formation_edge: str,
    derived_edge_type: str,
    edge_instance: str,
) -> EdgeView:
    """One derived attribution, **citing both premise claim-atoms** — provenance one click away, no mint.

    ``claim_ids`` is the two premises themselves. That is the whole point of the change: the analyst clicks
    the derived basing and lands on the sighting and the induction, rather than on a synthesized claim that
    stands between them and the evidence. The attribution can never be firmer than the sighting it rests
    on, so a decoy/integrity flag on the observation is carried forward for the status gate to see.
    """
    obs_attrs = obs.attributes or {}
    attrs: dict[str, object] = {
        DERIVED_VIA: f"{observed_edge}+{formation_edge}",
        DERIVED_LAYER: _DERIVED_LAYER,
        PREMISES: [obs.claim_id, formation.claim_id],
        "observed_claim": obs.claim_id,
        "observed_equipment": equipment_id,
        "formation_claim": formation.claim_id,
    }
    if obs_attrs.get("decoy_risk_flag"):
        attrs["decoy_risk_flag"] = True
    return EdgeView(
        id=f"e:{unit_id}:{derived_edge_type}:{site_id}",
        type=derived_edge_type,
        source=unit_id,
        target=site_id,
        edge_instance=edge_instance,
        claim_ids=sorted({obs.claim_id, formation.claim_id}),
        time_interval=_inherited_time(obs),
        attrs=attrs,
    )


def _truncation_gap(site_id: str, kept: list[str], dropped: list[str], cap: int) -> KnownGap:
    """R2.1 / G15's biting clause: a truncated formation attribution names what it dropped.

    The undercount this prevents involves **no merge at all**, which is why it was invisible to both the
    co-location cap and the presence/formation gate. Raising ``max_units_per_site`` turns this into two
    attributions instead — the choice is a config dial, and either answer is honest. What is not honest is
    the third option the old pass took: keep one, say nothing.
    """
    return KnownGap(
        id=f"gap:{site_id}:formation-attribution",
        related_ref=site_id,
        what_missing=(
            f"{len(kept) + len(dropped)} candidate formations are associated with the equipment observed "
            f"here; the attribution fan-out is capped at {cap}, so {', '.join(dropped)} "
            f"{'is' if len(dropped) == 1 else 'are'} not attributed. Formation count at this site is "
            f"unresolved: designation coverage needed"
        ),
        observability_ceiling="confirmable",
        missing_slots=["unit.designator"],
    )


def derive(
    nodes: dict[str, NodeView],
    edges: list[EdgeView],
    claims: dict[str, ClaimRecord],
    config: ConfigBundle,
    lane: EdgeLaneIndex,
    node_types: NodeTypeIndex,
    routing: LayerRouting,
) -> BasingDerivation:
    """Materialize the derived ``based-at`` edges over the assembled view. Pure; deterministic (G1/G2).

    Every non-firing occupancy edge is recorded with its reason, and an ambiguous attribution produces a
    named gap. Not configured ⇒ nothing derived.
    """
    out = BasingDerivation()
    cfg = _cfg(config)
    if not cfg:
        return out
    occupancy_edges = _edge_type_list(cfg, "occupancy_edge_types")
    formation_edges = _edge_type_list(cfg, "formation_edge_types")
    hop_edges = _edge_type_list(cfg, "equipment_hop_edges")
    derived_edge_type = str(cfg.get("derived_edge") or "")
    raw_cap = cfg.get("max_units_per_site")
    cap = int(raw_cap) if isinstance(raw_cap, int) and not isinstance(raw_cap, bool) and raw_cap > 0 else 1
    require_located = bool(cfg.get("require_located_site", True))
    if not (occupancy_edges and formation_edges and derived_edge_type):
        return out
    declared_tokens = cfg.get("occupied_tokens")
    occupied_tokens = (
        frozenset(str(t).lower() for t in declared_tokens)
        if isinstance(declared_tokens, (list, tuple)) and declared_tokens
        else _DEFAULT_OCCUPIED_TOKENS
    )
    # With routing on, the sighting's subject is a materialized presence, so the formation association is
    # one further hop away — over the `instance-of` link back to the design. Declared, not assumed.
    if routing.design_link_edge and routing.design_link_edge not in hop_edges:
        hop_edges = [*hop_edges, routing.design_link_edge]

    incident: dict[str, list[EdgeView]] = {}
    for e in edges:
        incident.setdefault(e.source, []).append(e)
        incident.setdefault(e.target, []).append(e)

    by_instance: dict[str, list[EdgeView]] = {}
    for edge in sorted(edges, key=lambda e: (e.type, e.source, e.target)):  # stable order → G2
        if edge.type not in occupancy_edges:
            continue
        ends = _equipment_end(edge, nodes)
        if ends is None:
            out.skipped.append((edge.source, "occupancy-edge-has-no-site-endpoint"))
            continue
        site_id, equipment_id = ends
        if require_located and not _is_locatable(nodes[site_id]):
            out.skipped.append((site_id, "site-not-locatable"))
            continue
        # An explicit vacancy must not merely lose the "latest" tie-break: a vacated site's NEWEST reading
        # is precisely the one saying it is empty.
        obs = _best_dated(edge, claims, where=lambda c: not _states_vacancy(c, occupied_tokens))
        if obs is None:
            out.skipped.append(
                (site_id, "observation-states-vacancy" if edge.claim_ids else "no-backing-observation-claim")
            )
            continue
        formations = _formation_candidates(
            equipment_id, nodes, incident, claims, formation_edges, hop_edges
        )
        if not formations:
            out.skipped.append((site_id, "no-formation-reference"))
            continue
        kept = [unit_id for unit_id, _, _ in formations[:cap]]
        dropped = [unit_id for unit_id, _, _ in formations[cap:]]
        if dropped:
            out.gaps.append(_truncation_gap(site_id, kept, dropped, cap))
        for unit_id, backing, ftype in formations[:cap]:
            # The `site_type` sub-bucket is NOT applied here — see `layers.retag_instances`. It is a
            # per-SUBJECT decision spanning this subject's stated basings too, so it can only be made once
            # every basing exists. Until then a derived edge keys exactly as a claim-backed one does.
            ei = lane.edge_instance_key(unit_id, derived_edge_type, site_id)
            drawn = _derived_edge(
                unit_id, site_id, equipment_id, obs, backing, edge.type, ftype, derived_edge_type, ei
            )
            by_instance.setdefault(ei, []).append(drawn)
            out.edges.append(drawn)

    # Two derived basings on one instance are a candidate relocation, and they must go through the SAME
    # ordering the claim-backed edges do — otherwise the derived layer would be the one place a state change
    # is invisible. Suppressed instances (an unmappable site class) are built but never ordered: the third
    # state's "no fusion", already paired with its named gap.
    for _ei, group in sorted(by_instance.items()):
        if len(group) > 1:
            order_instance_edges(group, {e.id: edge_bounds(e) for e in group})
    return out


def edge_bounds(edge: EdgeView) -> tuple[str, str] | None:
    """A derived edge's inherited validity as a fully-bounded interval, or ``None`` (⇒ unorderable).

    Shared with ``layers.retag_instances``, which has to re-run the ordering inside each re-bucketed
    instance and must read validity the same way this module wrote it.
    """
    lo, hi = canonical_iso_bounds(edge.time_interval)
    return (lo, hi) if lo is not None and hi is not None else None
