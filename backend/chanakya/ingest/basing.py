"""The basing proposer — turn an *observed occupancy* into a cited **unit-attribution** inference.

**The problem.** No open source states the fact the order-of-battle question actually needs. A satellite
write-up says *"six TEL-type objects consistent with HQ-9B occupy a revetment complex at PAF Base Nur
Khan, 09 OCT 2021"*; an induction announcement says *"the HQ-9/P has entered service with Army Air
Defence"*. Neither says **"formation X is based at site Y"** — the edge the relocation beat, the
freshness decay and the supersede all hang on. D-2.7 read that absence as "so don't extract basing at
all", which left the edge unowned by every service (EVAL RCA §2.2); D-P4.1/2/3 replace it with a
two-layer model:

* the **observed layer** — ``<equipment, observed-at, site>``, extracted, high confidence, directly seen
  (:mod:`chanakya.ingest.extract`'s occupancy slot, :mod:`chanakya.ingest.imagery`'s VLM read);
* the **attribution layer** — ``<unit, based-at, site>``, *derived here*, its own lower confidence,
  carrying both premises.

They are **never fused** into one flat confident basing assertion. That separation is the whole point:
the corpus contains a recycled-image trap and a grade-E relocation spoof built to punish a system that
collapses "kit was photographed here" into "this formation is stationed here".

**Where it runs.** Offline, upstream of the append, over the *previous frozen resolved view* — the same
connection-triggered discipline as :mod:`chanakya.ingest.attribute`, and for the same reason: the
hypothesis only exists once resolution has co-located an occupancy observation with a formation
reference. **Never inside** ``rebuild()`` (gate G1), which stays a pure deterministic fold.

**Why no model call.** Unlike the attribution proposer, this derivation is a *graph* step, not a
judgement about pixels: occupancy ∧ formation-association ⇒ candidate basing. Keeping it deterministic
means it needs no key, replays byte-identically, and cannot hallucinate a formation — the model is not
in a position to add anything a traversal cannot, so it is not asked.

**Endpoints are resolved node ids**, not surface strings — this pass runs *over the resolved view*, so the
two things it joins are already-canonical nodes and re-deriving them from names would only re-open the
identity question RESOLVE just closed. ``view.pipeline`` maps a triple endpoint through the merge map and
falls through to the literal, which lands on the node of that id. The coupling that buys: if RESOLVE's
canonical ids for these nodes change, a *frozen* derived bundle points at the old ids — so a re-record of
the source documents should be followed by a re-run of this pass, exactly as for ``*__attr.json``.

**Raise-only.** The emitted claim is ``kind="inference"`` with ``premises=[A, B]`` and a ``doc_ref``
spanning both (gate G4), and it sets **no** status and **no** confidence: SCORE prices it, and because an
inference shares an independence group with its premises it cannot self-corroborate to confirmed. The
``event_time`` is **inherited** from the grounding observation — that is what lets an old basing fact age
out and a newer one supersede it, and it is why the observation had to be dated first.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chanakya.ingest import imagery
from chanakya.ingest.seed import FROZEN_INGEST_TIME
from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView, make_claim_id
from chanakya.schemas.claim import DocRef, Triple
from chanakya.schemas.values import DateValue, canonical_iso_bounds
from chanakya.schemas.view import EdgeView, NodeView

# The two node types the rule keys on. Named, not magic — the whole rule is *about* a site and a
# formation; every list/number below is config-driven (gate G6).
_SITE_TYPE = "basing_site"
_UNIT_TYPE = "unit"

#: The affirmative-occupancy vocabulary, shared verbatim with the imagery lane's corroboration gate
#: (:data:`chanakya.ingest.imagery._OCCUPIED_TOKENS`) so "an empty site is not a deployment" means the
#: same thing in both places. Used as a **denylist**, not an allowlist: most sources never state an
#: occupancy word at all, and demanding one would suppress every honest sighting — but a source that
#: says the site is *empty* must never ground a positive basing claim. Without this the corpus's own
#: "TELs gone from the old Rawalpindi-area site, 2025-06-11" reading derived a 2025 Rawalpindi basing —
#: asserting the unit is at the one place the document says it left.
_OCCUPANCY_ATTR = "occupancy_state"


def _states_vacancy(claim: ClaimRecord) -> bool:
    """Does this observation state the site is **not** occupied? (An absence never grounds a presence.)"""
    if claim.polarity != "positive":
        return True
    word = (claim.attributes or {}).get(_OCCUPANCY_ATTR)
    if not isinstance(word, str) or not word.strip():
        return False  # unstated — the common case; the sighting itself is the occupancy evidence
    return not any(tok in word.lower() for tok in imagery._OCCUPIED_TOKENS)


# ── result records (raise-only; this module appends nothing itself) ─────────────────────────────────

@dataclass(frozen=True)
class BasingCandidate:
    """One derivation triangle: an occupancy observation at a site + a formation the equipment serves in."""

    site_id: str
    unit_id: str
    equipment_id: str
    observation: ClaimRecord  # A — the observed-occupancy claim (equipment seen at the site)
    formation: ClaimRecord    # B — the claim associating that equipment with the formation
    observed_edge: str
    formation_edge: str


@dataclass(frozen=True)
class SkipRecord:
    """A site/edge the proposer declined to derive from — surfaced, never silently dropped."""

    site_id: str
    reason: str


@dataclass
class BasingRun:
    """The proposer's output: the derived claims + which sites fired + why the others did not."""

    claims: list[ClaimRecord] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)
    skipped: list[SkipRecord] = field(default_factory=list)


# ── config (namespaced knobs off credibility.yaml, extra="allow"; absent ⇒ dormant) ─────────────────

def _proposer_cfg(config: ConfigBundle) -> dict[str, Any]:
    """The proposer's knobs from ``credibility.yaml → basing_proposer`` (hot-config). ``{}`` ⇒ dormant."""
    return dict(getattr(config.credibility, "basing_proposer", None) or {})


# ── a small read-only index over the frozen view (mirrors attribute._Index) ──────────────────────────

@dataclass
class _Index:
    nodes: dict[str, NodeView]
    incident: dict[str, list[EdgeView]]
    claims: dict[str, ClaimRecord]

    @classmethod
    def build(cls, view: GraphView, claims: dict[str, ClaimRecord]) -> _Index:
        incident: dict[str, list[EdgeView]] = {}
        for e in view.edges:
            incident.setdefault(e.source, []).append(e)
            incident.setdefault(e.target, []).append(e)
        return cls(nodes={n.id: n for n in view.nodes}, incident=incident, claims=dict(claims))

    def edges_of(self, node_id: str) -> list[EdgeView]:
        return self.incident.get(node_id, [])

    def other(self, edge: EdgeView, node_id: str) -> str:
        return edge.target if edge.source == node_id else edge.source


# ── premise selection (pure) ─────────────────────────────────────────────────────────────────────────

def _upper_bound(value: DateValue | None) -> str | None:
    return canonical_iso_bounds(value)[1]


def _best_dated_claim(edge: EdgeView, ix: _Index,
                      where: Callable[[ClaimRecord], bool] | None = None) -> ClaimRecord | None:
    """The edge's most recently-*valid* backing claim — the grounding observation the derivation dates to.

    Ranked by the claim's ``event_time`` upper bound (a dated look beats an undated one; the later dated
    look wins), tie-broken by claim id so the choice is deterministic. A derivation with **no** dated
    premise is still allowed — it simply inherits no ``event_time`` and is therefore unorderable, which
    is the honest outcome and is exactly what the supersede rule treats as `candidate` rather than fact.
    """
    best: ClaimRecord | None = None
    best_key: tuple[int, str, str] | None = None
    for cid in edge.claim_ids:
        c = ix.claims.get(cid)
        if c is None or (where is not None and not where(c)):
            continue
        hi = _upper_bound(c.event_time)
        key = (1 if hi else 0, hi or "", c.claim_id)
        if best_key is None or key > best_key:
            best, best_key = c, key
    return best


def _is_derived_from(obs_id: str, ix: _Index, derived_edge: str) -> bool:
    """Already derived: this observation is a premise of an inference on the derived lane (idempotence)."""
    for c in ix.claims.values():
        if c.kind != "inference" or obs_id not in c.premises:
            continue
        if isinstance(c.payload, Triple) and c.payload.predicate == derived_edge:
            return True
    return False


def _is_locatable_site(node: NodeView) -> bool:
    """Is this ``basing_site`` a place you could point to — a coordinate or a gazetteer match?

    The extractor mints a ``basing_site`` for every place a source names, which includes provinces,
    "air defence sectors" and "coastal belts". Those are *areas of operation*, not basing sites: "the
    unit is based at Punjab" is not a fact an analyst can act on, task collection against, or watch for
    a relocation. Requiring a located site is the location-precision spec (``md/13``) applied as an
    admission test to the derived layer — and it is what stops one formation from acquiring a dozen
    derived "bases" that are really just the regions its equipment was discussed in.
    """
    loc = node.location
    if loc is None:
        return False
    return loc.resolved_place_ref is not None or (
        loc.wgs84_lat is not None and loc.wgs84_lon is not None
    )


def _equipment_end(edge: EdgeView, ix: _Index) -> tuple[str, str] | None:
    """``(site_id, equipment_id)`` for an occupancy edge — or ``None`` if neither end is a site."""
    src, tgt = ix.nodes.get(edge.source), ix.nodes.get(edge.target)
    if tgt is not None and tgt.type == _SITE_TYPE and src is not None:
        return tgt.id, src.id
    if src is not None and src.type == _SITE_TYPE and tgt is not None:
        return src.id, tgt.id
    return None


def _formation_candidates(equipment_id: str, ix: _Index, formation_edges: list[str],
                          hop_edges: list[str]) -> list[tuple[str, ClaimRecord, str]]:
    """``(unit_id, backing claim B, edge type)`` for every formation the observed equipment serves in.

    Searched on the equipment node and one hop away over ``hop_edges`` (a *component* is observed at the
    site, but the formation association hangs off the *variant* it equips). Ranked most-evidenced first —
    the number of claims behind the association — then by unit id, so the pick is deterministic and the
    same equipment always attributes to the same formation at every site it is seen at. That last property
    is what makes a relocation legible at all: two sites keyed to one subject.
    """
    holders = [equipment_id]
    for e in ix.edges_of(equipment_id):
        if e.type in hop_edges:
            holders.append(ix.other(e, equipment_id))

    ranked: list[tuple[int, str, str, ClaimRecord, str]] = []
    seen: set[str] = set()
    for hid in holders:
        for e in ix.edges_of(hid):
            if e.type not in formation_edges:
                continue
            other_id = ix.other(e, hid)
            node = ix.nodes.get(other_id)
            if node is None or node.type != _UNIT_TYPE or other_id in seen:
                continue
            backing = _best_dated_claim(e, ix)
            if backing is None:
                continue
            seen.add(other_id)
            ranked.append((-len(e.claim_ids), other_id, other_id, backing, e.type))
    ranked.sort(key=lambda r: (r[0], r[1]))
    return [(unit_id, backing, etype) for _, _, unit_id, backing, etype in ranked]


def find_candidates(view: GraphView, claims: dict[str, ClaimRecord],
                    config: ConfigBundle) -> tuple[list[BasingCandidate], list[SkipRecord]]:
    """Sweep every occupancy edge for the derivation triangle. Pure — no LLM, deterministic (G1/G2).

    Returns the surviving candidates plus a :class:`SkipRecord` per occupancy edge that failed a clause,
    so the caller can log *why* nothing was derived (no silent drops). Not configured ⇒ ``([], [])``.
    """
    cfg = _proposer_cfg(config)
    if not cfg:
        return [], []
    occupancy_edges = list(cfg.get("occupancy_edge_types") or [])
    formation_edges = list(cfg.get("formation_edge_types") or [])
    hop_edges = list(cfg.get("equipment_hop_edges") or [])
    derived_edge = str(cfg.get("derived_edge") or "")
    max_units = int(cfg.get("max_units_per_site") or 1)
    require_located = bool(cfg.get("require_located_site", True))
    if not (occupancy_edges and formation_edges and derived_edge):
        return [], []

    ix = _Index.build(view, claims)
    candidates: list[BasingCandidate] = []
    skips: list[SkipRecord] = []
    for edge in sorted(view.edges, key=lambda e: (e.type, e.source, e.target)):  # stable order → G2
        if edge.type not in occupancy_edges:
            continue
        ends = _equipment_end(edge, ix)
        if ends is None:
            skips.append(SkipRecord(edge.source, "occupancy-edge-has-no-site-endpoint"))
            continue
        site_id, equipment_id = ends
        site_node = ix.nodes[site_id]
        if require_located and not _is_locatable_site(site_node):
            skips.append(SkipRecord(site_id, "site-not-locatable"))
            continue
        # An explicit vacancy never grounds a presence — and it must not merely lose the "latest"
        # tie-break either: a vacated site's *newest* reading is precisely the one saying it is empty.
        observation = _best_dated_claim(edge, ix, where=lambda c: not _states_vacancy(c))
        if observation is None:
            reason = ("observation-states-vacancy" if edge.claim_ids else "no-backing-observation-claim")
            skips.append(SkipRecord(site_id, reason))
            continue
        if _is_derived_from(observation.claim_id, ix, derived_edge):
            skips.append(SkipRecord(site_id, "already-derived"))
            continue
        formations = _formation_candidates(equipment_id, ix, formation_edges, hop_edges)
        if not formations:
            skips.append(SkipRecord(site_id, "no-formation-reference"))
            continue
        for unit_id, backing, ftype in formations[:max_units]:
            candidates.append(BasingCandidate(
                site_id=site_id, unit_id=unit_id, equipment_id=equipment_id,
                observation=observation, formation=backing,
                observed_edge=edge.type, formation_edge=ftype,
            ))
    return candidates, skips


# ── the derived claim ────────────────────────────────────────────────────────────────────────────────

def _slug(node_id: str) -> str:
    """A kebab ``[a-z0-9-]`` fragment of a node id for a readable, unique claim id."""
    parts = [p for p in "".join(ch if ch.isalnum() else "-" for ch in node_id.lower()).split("-") if p]
    return "-".join(parts) or "x"


def _inherited_time(premises: list[ClaimRecord]) -> DateValue | None:
    """The premises' latest valid time, carried across **whole** — the derived fact's own valid time.

    Taken as the maximum over the premises' ``event_time`` upper bounds, and the winning premise's date
    value is copied *as it stands* (shape, granularity and ``boundary_source`` intact) rather than
    flattened to an ISO string: a derived fact must not read as more precisely dated than the observation
    it rests on. A vague "2025" stays vague — which is what lets the supersede rule tell "later" from
    "unorderable" instead of silently ranking a year-label above a day-precise date.
    """
    best: DateValue | None = None
    best_key: tuple[str, str] | None = None
    for c in premises:
        hi = _upper_bound(c.event_time)
        if hi is None or c.event_time is None:
            continue
        key = (hi, c.claim_id)
        if best_key is None or key > best_key:
            best, best_key = c.event_time, key
    return best


def _build_derived(cand: BasingCandidate, derived_edge: str,
                   ingest_time: DateValue) -> ClaimRecord:
    """Freeze the derived attribution claim D — cites both premises, inherits the observation's time."""
    obs, formation = cand.observation, cand.formation
    refs: list[DocRef] = [obs.doc_refs()[0], formation.doc_refs()[0]]
    obs_attrs = obs.attributes or {}
    attributes: dict[str, Any] = {
        "derived_via": f"{cand.observed_edge}+{cand.formation_edge}",
        "derived_layer": "unit-attribution",
        "observed_claim": obs.claim_id,
        "observed_site": cand.site_id,
        "observed_equipment": cand.equipment_id,
        "formation_claim": formation.claim_id,
        "formation_source_id": formation.source_id,
        # The attribution can never be firmer than the sighting it rests on: a decoy-flagged or
        # integrity-flagged observation carries that flag forward, so SCORE's edge gate sees it here too.
        "decoy_risk_flag": bool(obs_attrs.get("decoy_risk_flag")) or None,
    }
    return ClaimRecord(
        claim_id=make_claim_id(_slug(obs.source_id), f"{_slug(cand.unit_id)}-{_slug(cand.site_id)}-basing"),
        source_id=obs.source_id,
        doc_ref=refs,
        kind="inference", polarity="positive", asserts="relationship",
        payload=Triple(subject=cand.unit_id, predicate=derived_edge, object=cand.site_id),
        event_time=_inherited_time([obs, formation]),
        report_time=obs.report_time, ingest_time=ingest_time,
        premises=[obs.claim_id, formation.claim_id],
        attributes={k: v for k, v in attributes.items() if v not in (None, "", [], {})},
    )


def propose_basing(view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle, *,
                   ingest_time: DateValue = FROZEN_INGEST_TIME) -> BasingRun:
    """Derive one ``<unit, based-at, site>`` inference per triangle (raise-only; appends nothing).

    Pure and keyless — the demo materialises the attribution layer with no API key, and two runs over the
    same view produce byte-identical claims. Budget-capped by ``max_claims_per_pass``; every non-firing
    occupancy edge is logged with its reason.
    """
    run = BasingRun()
    cfg = _proposer_cfg(config)
    if not cfg:
        return run  # dormant: the proposer is not configured on this deployment
    derived_edge = str(cfg.get("derived_edge") or "")
    budget = cfg.get("max_claims_per_pass")

    candidates, skips = find_candidates(view, claims, config)
    run.skipped.extend(skips)
    for cand in candidates:
        if budget is not None and len(run.claims) >= int(budget):
            run.skipped.append(SkipRecord(cand.site_id, "over-budget"))
            continue
        run.claims.append(_build_derived(cand, derived_edge, ingest_time))
        run.fired.append(cand.site_id)
    return run


# ── orchestration: the offline enrichment pass (rebuild → propose → append → rebuild) ────────────────

def enrich(store: Any, config: ConfigBundle, *, rebuild_fn: Any = None,
           ingest_time: DateValue = FROZEN_INGEST_TIME) -> BasingRun:
    """One enrichment pass: rebuild the frozen view, derive over it, append D, re-rebuild to materialise it.

    D is minted **upstream of ``store.append``** (G1); propagation happens on the *next* ``rebuild()``,
    never inline. Idempotent — a second pass finds the observation already derived-from and proposes
    nothing. The real ``rebuild`` is imported lazily (kept out of the module import graph); tests inject
    ``rebuild_fn``.
    """
    if rebuild_fn is None:
        from chanakya.view.pipeline import rebuild as rebuild_fn
    prev = rebuild_fn(store, [], config)
    claims = {c.claim_id: c for c in store.replay()}
    run = propose_basing(prev, claims, config, ingest_time=ingest_time)
    if run.claims:
        store.append_many(run.claims)
        rebuild_fn(store, [], config)  # materialise D as a derived, cited basing edge
    return run


def freeze_bundles(run: BasingRun, bundles_dir: Path) -> list[Path]:
    """Freeze derived attributions as byte-stable ``<source_id>__basing.json`` bundles (KEYLESS ≡ LIVE).

    A distinct ``__basing.json`` family, mirroring the attribution proposer's ``__attr.json``: the seed
    loader still globs and appends them at boot, and ``seed.extract_corpus``'s prune step preserves them
    (they record the *offline enrichment* pass, not any one source's extraction). Grouped by the grounding
    observation's source — the provenance the derived claim inherits.
    """
    from collections import defaultdict

    from chanakya.ingest import seed

    by_source: dict[str, list[ClaimRecord]] = defaultdict(list)
    for claim in run.claims:
        by_source[claim.source_id].append(claim)
    written: list[Path] = []
    for source_id, source_claims in sorted(by_source.items()):
        path = bundles_dir / f"{source_id}__basing.json"
        seed._write_bundle(path, source_claims)
        written.append(path)
    return written
