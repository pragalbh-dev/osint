"""API request/response shapes (master §4.8; product/03 A–H).

F0 freezes these so the SPA (out of scope here) and the API session bind to a stable contract. Field
*names* may still move — this is the shape-of-record. Endpoints these serve (final names fixed here):
``GET /view`` · ``GET /node/{id}`` · ``GET /evidence/{id}`` · ``POST /ask`` · ``POST /ingest`` ·
``POST /hitl/{merge|status|alert}`` · ``POST /config/{section}`` · ``GET /health``.
"""

from __future__ import annotations

from typing import Any, Literal

from .base import Record
from .claim import ClaimRecord, SourceRegistryEntry
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
    """First-class refusal (product/03 E / G) — what's missing + when coverage is due + the Known Gap.

    ``kind`` separates three refusals an analyst must never see conflated. "We looked and the evidence
    is thin" (``evidence``) is a statement about the WORLD; "we could not look at all" (``capability`` —
    no key, no recorded trace, a dead tool) is a statement about the SYSTEM; "we looked, found something,
    and would not stand behind the wording" (``withheld`` — failed citation/entailment) is a statement
    about the ANSWER. Rendering all three as "insufficient evidence to assess" overstates a gap in the
    world that may not exist — the same mislabelling family as stale-vs-insufficient, and a correctness
    bug rather than copy. Default stays ``evidence`` so existing producers are unchanged.
    """

    kind: Literal["evidence", "capability", "withheld"] = "evidence"
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
    # F0-amend (API, 2026-07-20): the VERBATIM cited span, ``claim_id -> [text per doc_ref]``,
    # positionally parallel to that claim's ``doc_refs()``. A file path + byte offset is a POINTER,
    # not a source — an analyst cannot audit a claim from ``d19…txt · L11 · 843–849``. The text is
    # read back out of the cited document at request time and never stored, so it cannot drift from
    # the append-only log; an unreadable/absent span yields ``""`` (never a paraphrase, never a
    # reconstruction). Additive/optional.
    quotes: dict[str, list[str]] = {}
    # F0-amend (API, 2026-07-20, T6): ``source_id -> SourceRegistryEntry`` for every source cited by
    # ``claims``. A raw source id (``d17b_withheld_gap``) is an internal key, not an attribution — an
    # analyst asked "who says so?" needs the source's CLASS and reliability grade, and those live only
    # in ``config/sources.yaml``, unreachable from any GET route until now. Returned VERBATIM from the
    # registry: no display string is synthesised server-side and no publisher NAME is invented, because
    # the registry does not carry one. Additive/optional — a source missing from the registry is simply
    # absent here and the UI falls back to the bare id rather than to a guess.
    sources: dict[str, SourceRegistryEntry] = {}


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
