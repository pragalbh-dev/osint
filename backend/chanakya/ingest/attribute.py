"""The attribution proposer — turn an *unattributed* VLM shape into a cited variant-identity inference.

**The problem.** A VLM reads an overhead frame and emits a deliberately *subject-blind* observation (shape
tokens, occupancy, geo — never "HQ-9"): naming a system from pixels collapses the model to its prior (gate
G11; DECISIONS 2026-07-18). So the graph holds an *unattributed shape at a site*. Deciding "this is an HQ-9"
is a separate, **cited inference** against reference literature — and that inference is exactly what lets an
IMINT look *corroborate* a textual "HQ-9 at X" report (a second, discipline-independent look → SCORE can
raise the deployment toward confirmed, capped at probable by decoy-risk until independently seen).

**Where it runs (the whole trick).** Not at single-doc ingest (the image is isolated; comparing a shape to
*all* literature is O(n²) and just pattern-matches the prior), and **never inside** ``rebuild()`` (which stays
deterministic — gate G1). The hypothesis and the *one* piece of literature to check only exist **after
resolution co-locates** imagery ↔ a claim naming a variant at that location ↔ that variant's reference
literature. So the inference is **connection-triggered**: an offline proposer over the **previous frozen
resolved view**, mirroring the RESOLVE/ASK discipline — *the LLM proposes upstream, frozen; ``rebuild()``
disposes deterministically.*

**What it emits.** One ``kind="inference"`` :class:`~chanakya.schemas.claim.ClaimRecord` D per co-location
triangle, whose ``Triple`` copies the textual claim C's exact ``(subject, predicate, object)`` (so RESOLVE
co-locates D and C on one edge and SCORE treats D as a second look), with ``premises=[A, B]`` (A = the VLM
observation, B = the reference fingerprint), ``doc_ref`` citing **both** the image region and the literature
line (gate G4), and decoy/provenance attrs. It is **raise-only** — a proposal; SCORE caps it at probable and
needs an independent look to confirm (there is no status/confidence field on a raw claim to set).

**General engine.** :func:`find_candidates` sweeps *every* ``basing_site`` in the view; each surviving
triangle is one scoped, subject-blind LLM call (budget-capped, skips logged). The "unattributed" gate (an
observation already used as an inference premise is skipped) makes repeated :func:`enrich` passes idempotent
— a standing enrichment pass converges instead of re-proposing.

Reuses :mod:`chanakya.ingest.imagery`'s corroboration machinery verbatim (``SignatureCorroboration`` tool,
``_corroboration_prompt``, ``_corroboration_eligible``) — the same subject-blind, forced-single-tool call,
re-triggered offline over the graph instead of per-frame at ingest. Structurally unreachable from
``rebuild()`` (lives in ``ingest/``, which the view pipeline never imports); the LLM SDK is reached only
lazily through the injected :class:`~chanakya.ingest.client.ExtractionClient`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chanakya.ingest import imagery
from chanakya.ingest.client import ExtractionClient, build_extraction_client
from chanakya.ingest.seed import FROZEN_INGEST_TIME
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    GraphView,
    SourceRegistryEntry,
    make_claim_id,
)
from chanakya.schemas.claim import EntityDescriptor, EventDescriptor, Extraction, Triple
from chanakya.schemas.values import DateValue
from chanakya.schemas.view import EdgeView, NodeView

# Ontology node types the rule keys on (config/ontology.yaml). Named, not magic — a site hosts the shape;
# a variant is the identity the fingerprint names. Kept as constants (not config) since the whole rule is
# *about* these two types; everything numeric/list-valued below is config-driven (gate G6).
_SITE_TYPE = "basing_site"
_VARIANT_TYPE = "variant"


# ── result records (raise-only; this module appends nothing itself) ─────────────────────────────────

@dataclass(frozen=True)
class AttributionCandidate:
    """One co-location triangle the deterministic rule surfaces: (site, variant) with A, B, and C in hand."""

    site_id: str
    variant_id: str
    variant_name: str
    observation: ClaimRecord   # A — the subject-blind VLM shape observation
    fingerprint: ClaimRecord   # B — the reference-literature fingerprint (2nd premise)
    textual: ClaimRecord       # C — the textual variant-presence claim whose triple D copies
    signature_geometry: str    # B's reference site-geometry text (LLM input + provenance)


@dataclass(frozen=True)
class SkipRecord:
    """A candidate/site the proposer declined to fire on — surfaced, never silently dropped."""

    site_id: str
    reason: str


@dataclass
class AttributionRun:
    """The proposer's output: the cited D claims + which sites fired + why others were skipped."""

    claims: list[ClaimRecord] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)
    skipped: list[SkipRecord] = field(default_factory=list)


# ── config (namespaced knobs off credibility.yaml, extra="allow"; absent ⇒ dormant) ─────────────────

def _proposer_cfg(config: ConfigBundle) -> dict[str, Any]:
    """The proposer's knobs from ``credibility.yaml → attribution_proposer`` (hot-config). ``{}`` ⇒ dormant."""
    return dict(getattr(config.credibility, "attribution_proposer", None) or {})


def _candidate_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return dict(cfg.get("candidate") or {})


# ── a small read-only index over the frozen view (keeps ingest→agent decoupled; mirrors ToolContext) ─

@dataclass
class _Index:
    nodes: dict[str, NodeView]
    incident: dict[str, list[EdgeView]]
    claims: dict[str, ClaimRecord]
    sources: dict[str, SourceRegistryEntry]

    @classmethod
    def build(cls, view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle) -> _Index:
        incident: dict[str, list[EdgeView]] = {}
        for e in view.edges:
            incident.setdefault(e.source, []).append(e)
            incident.setdefault(e.target, []).append(e)
        return cls(
            nodes={n.id: n for n in view.nodes},
            incident=incident,
            claims=dict(claims),
            sources=config.sources.as_map(),
        )

    def edges_of(self, node_id: str) -> list[EdgeView]:
        return self.incident.get(node_id, [])

    def other(self, edge: EdgeView, node_id: str) -> str:
        return edge.target if edge.source == node_id else edge.source


# ── claim-body readers (an observation's payload attrs vs a claim's tier-3 bag) ──────────────────────

def _payload_attrs(claim: ClaimRecord) -> dict[str, Any]:
    """The ``attrs`` bag on an entity/event payload (a ``Triple`` has none), else ``{}``."""
    p = claim.payload
    return dict(p.attrs) if isinstance(p, (EntityDescriptor, EventDescriptor)) else {}


def _geometry_tokens(claim: ClaimRecord) -> list[str]:
    toks = _payload_attrs(claim).get("geometry_tokens")
    return [t for t in toks if isinstance(t, str)] if isinstance(toks, list) else []


def _triple(claim: ClaimRecord) -> Triple:
    """The claim's ``Triple`` payload — invariant on relationship claims (guarded where they're selected)."""
    assert isinstance(claim.payload, Triple)
    return claim.payload


def _fingerprint_text(claim: ClaimRecord, keys: list[str]) -> str | None:
    """The first non-empty site-geometry string under any configured fingerprint key (payload attrs first)."""
    for bag in (_payload_attrs(claim), claim.attributes or {}):
        for k in keys:
            v = bag.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


# ── the deterministic candidate rule (pure — no LLM; runs over the frozen view) ─────────────────────

def _shape_observation(node: NodeView, ix: _Index) -> ClaimRecord | None:
    """(a) the site's subject-blind VLM shape observation (claim A) — a ``vlm`` observation with geometry."""
    for cid in node.claim_ids:
        c = ix.claims.get(cid)
        if c is not None and c.kind == "observation" and c.extraction.method == "vlm" and _geometry_tokens(c):
            return c
    return None


def _is_attributed(obs_id: str, ix: _Index) -> bool:
    """Already bridged: the observation is a premise of some inference claim (⇒ convergence — skip on re-run)."""
    return any(obs_id in c.premises for c in ix.claims.values() if c.kind == "inference")


def _textual_relationship_claim(edge: EdgeView, ix: _Index) -> ClaimRecord | None:
    """A non-VLM observation *relationship* claim backing an edge (a text/parser look, not the image)."""
    for cid in edge.claim_ids:
        c = ix.claims.get(cid)
        if (c is not None and c.kind == "observation" and c.asserts == "relationship"
                and c.extraction.method != "vlm" and isinstance(c.payload, Triple)):
            return c
    return None


def _variant_via_hop(node_id: str, ix: _Index, hop_edges: list[str]) -> str | None:
    """The variant one hop from a unit/component endpoint (e.g. variant --inducted-into--> unit)."""
    for e in ix.edges_of(node_id):
        if e.type in hop_edges:
            other = ix.nodes.get(ix.other(e, node_id))
            if other is not None and other.type == _VARIANT_TYPE:
                return other.id
    return None


def _variant_presence(node: NodeView, ix: _Index, presence_types: list[str],
                      hop_edges: list[str]) -> tuple[str, ClaimRecord] | None:
    """(b) a textually-asserted variant present at the site → ``(variant_id, C)``.

    C = a non-VLM observation relationship claim on a presence edge (default: ``based-at``) incident to the
    site. The variant is the edge's other endpoint if it is a ``variant`` node, else the variant one hop from
    the unit endpoint. D copies C's exact triple, so D and C co-locate on one edge regardless of orientation.
    """
    for e in ix.edges_of(node.id):
        if e.type not in presence_types:
            continue
        c = _textual_relationship_claim(e, ix)
        if c is None:
            continue
        other_id = ix.other(e, node.id)
        other = ix.nodes.get(other_id)
        if other is None:
            continue
        if other.type == _VARIANT_TYPE:
            return other_id, c
        v = _variant_via_hop(other_id, ix, hop_edges)
        if v is not None:
            return v, c
    return None


def _fingerprint(variant_id: str, ix: _Index, ref_classes: list[str], fp_keys: list[str],
                 hop_edges: list[str]) -> tuple[ClaimRecord, str] | None:
    """(c) a reference-literature fingerprint reachable from the variant → ``(B, geometry_text)``.

    Searched on the variant node and any node one hop away via a configured edge (the fingerprint often
    lives on a ``component``/``unit`` — the variant type carries no fingerprint attr in the ontology).
    """
    holders = [variant_id, *(ix.other(e, variant_id) for e in ix.edges_of(variant_id) if e.type in hop_edges)]
    seen: set[str] = set()
    for hid in holders:
        node = ix.nodes.get(hid)
        if node is None:
            continue
        for cid in node.claim_ids:
            if cid in seen:
                continue
            seen.add(cid)
            c = ix.claims.get(cid)
            if c is None:
                continue
            src = ix.sources.get(c.source_id)
            if src is None or src.source_type not in ref_classes:
                continue
            geom = _fingerprint_text(c, fp_keys)
            if geom:
                return c, geom
    return None


def find_candidates(view: GraphView, claims: dict[str, ClaimRecord],
                    config: ConfigBundle) -> tuple[list[AttributionCandidate], list[SkipRecord]]:
    """Sweep every ``basing_site`` for the co-location triangle. Pure — no LLM, deterministic (G1/G2).

    Returns the surviving candidates plus a :class:`SkipRecord` for each site that failed a clause (so the
    caller can log *why* nothing fired there — no silent drops). Not configured ⇒ ``([], [])`` (dormant).
    """
    cfg = _proposer_cfg(config)
    if not cfg:
        return [], []
    cc = _candidate_cfg(cfg)
    presence = list(cc.get("presence_edge_types") or [])
    ref_classes = list(cc.get("reference_source_classes") or [])
    fp_keys = list(cc.get("fingerprint_attrs") or [])
    hop_edges = list(cc.get("variant_hop_edges") or [])

    ix = _Index.build(view, claims, config)
    candidates: list[AttributionCandidate] = []
    skips: list[SkipRecord] = []
    for node in sorted(view.nodes, key=lambda n: n.id):  # stable order → G2
        if node.type != _SITE_TYPE:
            continue
        obs = _shape_observation(node, ix)
        if obs is None:
            skips.append(SkipRecord(node.id, "no-vlm-shape-observation"))
            continue
        if _is_attributed(obs.claim_id, ix):
            skips.append(SkipRecord(node.id, "already-attributed"))
            continue
        pres = _variant_presence(node, ix, presence, hop_edges)
        if pres is None:
            skips.append(SkipRecord(node.id, "no-textual-variant"))
            continue
        variant_id, textual = pres
        fp = _fingerprint(variant_id, ix, ref_classes, fp_keys, hop_edges)
        if fp is None or fp[0].claim_id == textual.claim_id:
            skips.append(SkipRecord(node.id, "no-fingerprint-literature"))
            continue
        fingerprint, geom = fp
        variant = ix.nodes[variant_id]
        candidates.append(AttributionCandidate(
            site_id=node.id, variant_id=variant_id, variant_name=variant.name or variant_id,
            observation=obs, fingerprint=fingerprint, textual=textual, signature_geometry=geom,
        ))
    return candidates, skips


# ── the scoped, subject-blind LLM call + the emitted inference D ─────────────────────────────────────

def _slug(node_id: str) -> str:
    """A kebab ``[a-z0-9-]`` fragment of a node id for a readable, unique claim id."""
    parts = [p for p in "".join(ch if ch.isalnum() else "-" for ch in node_id.lower()).split("-") if p]
    return "-".join(parts) or "x"


def _build_inference(cand: AttributionCandidate, corr: dict[str, Any],
                     client: ExtractionClient, ingest_time: DateValue) -> ClaimRecord:
    """Freeze the cited bridge inference D — copies C's triple, cites both sources, carries the decoy signal."""
    obs, fingerprint, textual = cand.observation, cand.fingerprint, cand.textual
    img_ref = obs.doc_refs()[0]        # the image region/bbox (G4: one click to the pixels)
    lit_ref = fingerprint.doc_refs()[0]  # the literature line/span (G4: one click to the reference)
    matched = imagery._strlist(corr, "matched_features")
    triple = _triple(textual)  # guaranteed a Triple by _textual_relationship_claim
    d_id = make_claim_id(
        imagery._doc_token(obs.source_id), f"{imagery._img_locator(img_ref)}-{_slug(cand.variant_id)}-attr")
    attributes = imagery._prune({
        "decoy_risk": True,       # single-pass pixel read — cannot self-confirm (SCORE caps)
        "decoy_risk_flag": True,  # the boolean SCORE's edge gate reads (see the SCORE handoff)
        "single_pass": True,
        "fingerprint_match": matched or True,
        "matched_features": matched,
        "confidence_language": imagery._str(corr, "confidence_language"),
        "rationale": imagery._str(corr, "rationale"),
        "corroborated_against": fingerprint.claim_id,
        "reference_source_id": fingerprint.source_id,
        "attributed_variant": cand.variant_id,  # the identity the shape matched (provenance, even off-triple)
    })
    return ClaimRecord(
        claim_id=d_id, source_id=obs.source_id, doc_ref=[img_ref, lit_ref],
        kind="inference", polarity="positive", asserts="relationship",
        payload=Triple(subject=triple.subject, predicate=triple.predicate, object=triple.object),
        report_time=obs.report_time, ingest_time=ingest_time,
        premises=[obs.claim_id, fingerprint.claim_id],  # [A, B] — non-empty (validator enforces for inference)
        extraction=Extraction(method="llm", version=client.model_id, model_conf=1.0),
        attributes=attributes or None,
    )


def propose_attributions(view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle, *,
                         client: ExtractionClient | None = None,
                         ingest_time: DateValue = FROZEN_INGEST_TIME) -> AttributionRun:
    """Propose one cited inference D per co-location triangle (raise-only; appends nothing).

    Reads the *already-rebuilt* frozen ``view``; for each candidate runs imagery's deterministic pre-gate
    then one scoped, subject-blind corroboration call (A's shape tokens + B's reference geometry only) and
    emits D when the model judges them consistent. Budget-capped; every non-firing candidate is logged.
    Keyless / not-configured ⇒ an empty run — an honest refusal, never a fabricated attribution.
    """
    run = AttributionRun()
    cfg = _proposer_cfg(config)
    if not cfg:
        return run  # dormant: the proposer is not configured on this deployment
    resolved = client if client is not None else build_extraction_client()
    if resolved is None:
        return run  # no extraction key → refuse, never guess (KEYLESS: the frozen-bundle path materialises D)

    budget = cfg.get("max_calls_per_rebuild")
    candidates, skips = find_candidates(view, claims, config)
    run.skipped.extend(skips)
    calls = 0
    for cand in candidates:
        if budget is not None and calls >= budget:
            run.skipped.append(SkipRecord(cand.site_id, "over-budget"))
            continue
        attrs = _payload_attrs(cand.observation)
        tokens = _geometry_tokens(cand.observation)
        features = [f for f in (attrs.get("observed_features") or []) if isinstance(f, dict)]
        # imagery's deterministic gate: empty-pads / insufficient-res / non-overhead frames never reach the LLM.
        if not imagery._corroboration_eligible(attrs, geometry_tokens=tokens, features=features):
            run.skipped.append(SkipRecord(cand.site_id, "ineligible-frame"))
            continue
        corr = resolved.extract(
            tool_name=imagery._CORROBORATION_TOOL,
            input_schema=imagery.SignatureCorroboration.model_json_schema(),
            system=imagery._CORROBORATION_SYSTEM,
            text=imagery._corroboration_prompt(
                geometry_tokens=tokens, features=features,
                description=attrs.get("description"), occupancy=attrs.get("occupancy_state"),
                literature=imagery.LiteratureRef(
                    claim_id=cand.fingerprint.claim_id, variant=cand.variant_name,
                    signature_geometry=cand.signature_geometry, source_id=cand.fingerprint.source_id,
                    predicate=_triple(cand.textual).predicate),
            ),
        )
        calls += 1
        run.fired.append(cand.site_id)
        if isinstance(corr, dict) and corr.get("consistent") is True:
            run.claims.append(_build_inference(cand, corr, resolved, ingest_time))
        else:
            run.skipped.append(SkipRecord(cand.site_id, "not-consistent"))
    return run


# ── orchestration: the offline enrichment pass (rebuild → propose → append → rebuild) ────────────────

def enrich(store: Any, config: ConfigBundle, *, client: ExtractionClient | None = None,
           rebuild_fn: Any = None, ingest_time: DateValue = FROZEN_INGEST_TIME) -> AttributionRun:
    """One enrichment pass: rebuild the frozen view, propose over it, append D, re-rebuild to materialise it.

    D is minted **upstream of ``store.append``** (G1); propagation is on the *next* ``rebuild()``, never
    inline. Idempotent — a second pass finds the observation already attributed and proposes nothing. The
    real ``rebuild`` is imported lazily (kept out of the module import graph); tests inject ``rebuild_fn``.
    """
    if rebuild_fn is None:
        from chanakya.view.pipeline import rebuild as rebuild_fn
    prev = rebuild_fn(store, [], config)
    claims = {c.claim_id: c for c in store.replay()}
    run = propose_attributions(prev, claims, config, client=client, ingest_time=ingest_time)
    if run.claims:
        store.append_many(run.claims)
        rebuild_fn(store, [], config)  # materialise D as a decoy-flagged edge co-located with C
    return run


def freeze_bundles(run: AttributionRun, bundles_dir: Path) -> list[Path]:
    """Freeze proposed inferences as byte-stable ``<source_id>__attr.json`` bundles (KEYLESS ≡ LIVE path).

    Written as a distinct ``__attr.json`` family so ``seed.seed_store_from_bundles`` still globs + appends
    them at boot (the keyless demo materialises D without a key), while ``seed.extract_corpus``'s per-source
    prune step preserves them — they are the recording of the *offline enrichment* pass, not of any one
    source's extraction. Grouped by the observation's source (the IMINT provenance D inherits).
    """
    from collections import defaultdict

    from chanakya.ingest import seed

    by_source: dict[str, list[ClaimRecord]] = defaultdict(list)
    for claim in run.claims:
        by_source[claim.source_id].append(claim)
    written: list[Path] = []
    for source_id, claims in sorted(by_source.items()):
        path = bundles_dir / f"{source_id}__attr.json"
        seed._write_bundle(path, claims)
        written.append(path)
    return written
