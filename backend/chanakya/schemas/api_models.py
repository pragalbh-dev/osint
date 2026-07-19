"""API request/response shapes (master §4.8; product/03 A–H).

F0 freezes these so the SPA (out of scope here) and the API session bind to a stable contract. Field
*names* may still move — this is the shape-of-record. Endpoints these serve (final names fixed here):
``GET /view`` · ``GET /node/{id}`` · ``GET /evidence/{id}`` · ``POST /ask`` · ``POST /ingest`` ·
``POST /hitl/{merge|status|alert}`` · ``POST /config/{section}`` · ``GET /health``.
"""

from __future__ import annotations

from typing import Any, Literal

from .base import Record
from .claim import ClaimRecord
from .view import (
    ConfidenceBreakdown,
    Freshness,
    IndependenceGroup,
    KnownGap,
    Status,
    SufficiencyEval,
)

# ── POST /ask (product/03 E) ─────────────────────────────────────────────────────────────────

class AskRequest(Record):
    question: str
    subject: str | None = None  # apply a subject lens before answering


class AnswerHop(Record):
    """One edge traversed in a multi-hop answer — carries its own citations (no naked assertions)."""

    step: int
    edge: str  # the edge type / human phrase for the hop
    src: str
    dst: str
    claim_ids: list[str] = []
    observed_or_inferred: Literal["observed", "inferred"] = "observed"  # from each claim's kind field


class RefusalPayload(Record):
    """First-class refusal (product/03 E / G) — what's missing + when coverage is due + the Known Gap."""

    missing: list[str] = []
    next_coverage_due: str | None = None
    known_gap: KnownGap | None = None
    reason: str = ""  # a rendered template, never regenerated prose (§3.11)


class AskAnswer(Record):
    question: str
    sub_questions: list[str] = []
    hops: list[AnswerHop] = []
    answer: str | None = None  # None when refusing
    citations: list[str] = []  # every claim_id cited (validated to exist + entail — ASK)
    observed_claims: list[str] = []
    inferred_claims: list[str] = []
    refusal: RefusalPayload | None = None  # set instead of `answer` when evidence is insufficient


# ── GET /node, GET /evidence (product/03 B/C) ──────────────────────────────────────────────────

class ProvenanceDrawer(Record):
    """The confidence breakdown for a node/edge — "how do you know that?" (product/03 C)."""

    subject_ref: str
    status: Status | None = None
    confidence: ConfidenceBreakdown | None = None
    freshness: Freshness | None = None
    clusters: list[IndependenceGroup] = []  # "5 sources · 2 independent looks"
    opposing_claims: list[str] = []
    sufficiency: SufficiencyEval | None = None
    # F0-amend (API, 2026-07-19): the resolved evidence atoms (product/03 A) the ``clusters`` +
    # ``opposing_claims`` reference by id — each carries its exact ``doc_ref``, so the drawer is
    # self-contained one-click-to-source. Additive/optional: consumers that ignore it are unaffected.
    claims: list[ClaimRecord] = []


# ── POST /hitl/* (product/03 D) ────────────────────────────────────────────────────────────────

ReviewType = Literal["merge", "status-override", "alert-disposition", "integrity-flag"]


class ReviewContext(Record):
    """The snapshot shown to the decider + the three ranking dimensions (confidence/materiality/novelty)."""

    summary: str = ""
    confidence: float | None = None
    materiality: float | None = None
    novelty: float | None = None
    evidence: dict[str, Any] = {}


class ReviewQueueItem(Record):
    """The reusable HITL card envelope — same shape for every type, payload differs (product/03 D)."""

    item_id: str
    type: ReviewType
    subject: str
    context: ReviewContext = ReviewContext()
    options: list[str] = []  # merge: accept/reject/split · override: promote/demote/reject · alert: real/noise/needs-more
    effects: dict[str, Any] = {}  # preview of the downstream state change
    payload: dict[str, Any] = {}  # type-specific body (the two candidate entities, the breakdown, the before→after)
    actor: str = "system"
    ts: str | None = None
    pinned: bool = False  # ★ items pinned to the top (never trust LLM rank) — recall-biased triage


class HitlDecision(Record):
    """A writeback from the review UI — appended to the decision log, applied on next rebuild (G12)."""

    item_id: str
    type: ReviewType
    subject: str
    decision: str  # the chosen option
    rationale: str | None = None
    actor: str = "analyst"


# ── POST /ingest ───────────────────────────────────────────────────────────────────────────────

class IngestRequest(Record):
    """Raw doc → live extract+append (keyed), OR a pre-extracted claim bundle → append (keyless)."""

    doc_path: str | None = None  # a raw doc to extract (needs a key)
    raw_text: str | None = None
    source_id: str | None = None
    # F0-amend (API, 2026-07-19): the keyed live lane requires the source's credibility class to route
    # extraction + score the claims (INGEST ``ingest_document(source_type=…)``). Additive/optional — the
    # keyless bundle path ignores it. One of the ``sources.yaml`` ``source_type`` vocabulary values.
    source_type: str | None = None
    bundle: list[dict[str, Any]] | None = None  # pre-extracted ClaimRecord dicts (keyless lane)


class IngestResult(Record):
    appended_claim_ids: list[str] = []
    rebuilt: bool = False
    alerts_fired: list[str] = []


# ── POST /config/{section} ─────────────────────────────────────────────────────────────────────

class ConfigWrite(Record):
    """A hot-config write — no restart; triggers a live rebuild (spine/09)."""

    section: str  # one of CONFIG_SECTIONS
    value: dict[str, Any]


class ConfigWriteResult(Record):
    section: str
    version: int  # the config store's new version after the write


# ── GET /health ────────────────────────────────────────────────────────────────────────────────

class HealthResponse(Record):
    status: Literal["ok", "starting"] = "ok"
    rebuilt: bool = False  # 200 only after the first successful rebuild() (master §7)
    node_count: int = 0
    edge_count: int = 0
    config_version: int = 0
