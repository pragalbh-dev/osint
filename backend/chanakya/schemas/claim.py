"""The evidence log's records — the **unit of analysis is the sourced claim** (master §1, §4.2).

A ``ClaimRecord`` is immutable once appended: claims are never merged or edited (only *entities*
merge, via ``resolved_ref``, at rebuild); a correction is an appended ``retraction`` claim. This
is what makes one-click node→claim→doc-span traceability structural (gate G4) and the append-only
store honest (gate G3).

Payload is a discriminated union keyed on ``form`` and cross-checked against ``asserts``:
relationship→triple, entity→entity-descriptor, event→event-descriptor. Events are first-class
(``{event_type, time-interval, location, participants}``) — B pre-wiring #1; structural edges like
``based-at`` are *states derived from events*.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .base import Record
from .values import DateValue, Location, Period, Quantity

# ── Enumerations ───────────────────────────────────────────────────────────────────────────────

Kind = Literal["observation", "inference", "retraction"]
# negative = an observed *absence* ("imagery of site S shows no TELs") — B pre-wiring #5.
Polarity = Literal["positive", "negative"]
Asserts = Literal["entity", "relationship", "event"]
# operator-state | exporter-state = parties to the deal (aligned interest); the rest are cross-interest.
BiasVector = Literal["operator-state", "exporter-state", "third-party", "commercial", "adversary"]


# ── Provenance locator ───────────────────────────────────────────────────────────────────────

class DocRef(Record):
    """The exact cited location inside a source doc — the target of "one click to truth" (§4.2).

    Exactly one locator is normally set per ref; a claim restated within one doc keeps *one* claim
    with *multiple* DocRefs (master §3.1 claim-dedup).
    """

    file: str
    span: tuple[int, int] | None = None  # [start, end] char offsets in a text doc
    line: int | None = None  # 1-indexed line in a text doc — human-readable txt locator (span stays the exact range)
    row: int | None = None  # a table/CSV row (customs manifest)
    page: int | None = None  # a PDF page
    bbox: tuple[float, float, float, float] | None = None  # [x0, y0, x1, y1] on a page/image
    frame: int | None = None  # a video frame index
    region: str | None = None  # a named image region ("central berm")


# ── Payloads (discriminated on ``form``) ───────────────────────────────────────────────────────

class Triple(Record):
    """A subject–predicate–object relationship claim (``asserts == relationship``)."""

    form: Literal["triple"] = "triple"
    subject: str
    predicate: str
    object: str
    # A structured object when the predicate carries one (a count, a place, a date). Kept optional
    # so the LLM extractor can fill only what the source states.
    object_value: Quantity | Location | DateValue | None = None


class EntityDescriptor(Record):
    """An entity-existence/attribute claim (``asserts == entity``)."""

    form: Literal["entity"] = "entity"
    entity_type: str
    name: str
    attrs: dict[str, Any] = {}


class EventDescriptor(Record):
    """A first-class event claim (``asserts == event``) — TransferEvent, InductionEvent, etc."""

    form: Literal["event"] = "event"
    event_type: str
    time_interval: Period | DateValue | None = None
    location: Location | None = None
    participants: list[str] = []
    attrs: dict[str, Any] = {}


ClaimPayload = Triple | EntityDescriptor | EventDescriptor


# ── Extraction + resolution stamps ─────────────────────────────────────────────────────────────

class Extraction(Record):
    """How the claim was pulled. ``model_conf`` held at 1.0 for the demo (seam for a low-conf VLM read)."""

    method: Literal["llm", "vlm", "parser"] = "llm"
    version: str = ""
    model_conf: float = 1.0


class ResolvedRef(Record):
    """What a claim resolves to. **Supersede/contradict match on THIS, never a designator string.**

    On the raw claim this is the extractor's guess (usually unset); the authoritative resolution is
    RESOLVE's ``Partition`` produced inside ``rebuild()``.
    """

    entity_id: str | None = None
    edge_instance: str | None = None


# ── The claim record ─────────────────────────────────────────────────────────────────────────

class ClaimRecord(Record):
    """One sourced claim: *Source S, dated D, asserts <s,p,o>* (master §4.2, spine/08 §3.1)."""

    # THE CLAIM ATOM (plan §4 A1). The canonical value — the one assigned by
    # ``ingest.dedup.assign_claim_ids`` — is the per-mention addressing bedrock of the whole system: it is
    # minted once at ingest, immutable, and **never splits or merges**. The id present at construction is
    # only *provisional* (unique within one extraction call); dedup reassigns it, folds restatements, and
    # rewrites every cross-claim reference in lockstep. Everything that must survive a re-key addresses
    # this, never a derived node id and never a name (A5/A6).
    claim_id: str  # human-readable, e.g. "d05-row12" (schemas.ids)
    # THE REFERENT ATOM (plan §4 A1) — one per **document-local coreference cluster**, ``ref:<doc>-<c>``
    # (``schemas.ids.make_referent_id``). **Dormant in S1: always ``None``.** Populated at ingest from S3,
    # when coreference becomes a required tier and a cluster grain exists to mint against; optional-by-
    # default is what keeps this a non-breaking amendment on an ``extra="forbid"`` record, so the frozen
    # pre-S1 bundles still validate unchanged.
    #
    # It is a **grouping signal the rebuild consults and may decline** (D-13.18), never an address: a
    # knowledge node is a derived grouping of *claim* atoms (claim-atom-primary, A1/A5), so declining a
    # referent grouping simply de-groups to claim-atom granularity and raises for an analyst — no atom
    # ever splits. ``resolved_ref`` below stays the *derived* pointer at what a claim resolved to; this is
    # evidence-layer provenance and is never written by ``rebuild()`` (gate G17).
    #
    # Grain: an **entity-form** claim carries the referent of the mention it names. A relationship/event
    # claim has *two or more* mentions and therefore no single referent — its endpoints' referents are
    # reached through the tier-3 mention refs (``_subject_mention`` / ``_object_mention``, which name the
    # endpoint *claims*), so the field stays ``None`` on those forms.
    referent_id: str | None = None
    source_id: str  # → SourceRegistryEntry
    doc_ref: DocRef | list[DocRef]  # one, or many spans for one within-doc restatement
    kind: Kind
    polarity: Polarity = "positive"
    asserts: Asserts
    payload: ClaimPayload = Field(discriminator="form")
    event_time: DateValue | None = None  # ≡ C/01 valid_time — when true in the world
    report_time: DateValue | None = None  # when the source published
    ingest_time: DateValue | None = None  # when we got it
    resolved_ref: ResolvedRef | None = None
    extraction: Extraction = Extraction()
    premises: list[str] = []  # claim_ids — inference only
    targets: str | None = None  # claim_id — retraction only
    # Tier-3 of INGEST's 3-tier attribute promotion: source-native context with no ontology home
    # (HS-code, container#, BoL#). Nullable + typed-loose — traceable & queryable, never traversed;
    # promotable to a node/edge or a knowledge-layer attr later. Not resolved, not scored.
    attributes: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> ClaimRecord:
        """Pure structural checks only (no network/parse/clock — keeps rebuild reload G1-safe)."""
        want = {"relationship": "triple", "entity": "entity", "event": "event"}[self.asserts]
        if self.payload.form != want:
            raise ValueError(f"asserts={self.asserts!r} requires payload.form={want!r}, got {self.payload.form!r}")
        if self.kind == "retraction" and not self.targets:
            raise ValueError("retraction claim must set `targets` (the claim_id it retracts)")
        if self.kind == "inference" and not self.premises:
            raise ValueError("inference claim must set `premises` (the claim_ids it derives from)")
        return self

    def doc_refs(self) -> list[DocRef]:
        """Normalise ``doc_ref`` to a list (it may be one ref or many spans)."""
        return self.doc_ref if isinstance(self.doc_ref, list) else [self.doc_ref]


# ── Source registry ────────────────────────────────────────────────────────────────────────────

class SourceRegistryEntry(Record):
    """A source's deception-relevant metadata — feeds independence grouping (§3.5) + the resolver."""

    source_id: str
    source_type: str  # "curated-register" | "official-statement" | "satellite" | "social" | …
    reliability_grade: str | None = None  # STANAG A–F
    primary_origin_id: str | None = None  # circular-reporting detection
    aggregator_of: list[str] = []  # an aggregator inherits these upstream origins (SIPRI!)
    bias_vector: BiasVector | None = None
    coordinated_inauthenticity_flag: bool = False
    adversary_denial_flag: bool = False  # a GATE, not a multiplier (§3.4)
    cadence: str | None = None  # revisit interval → generates next_coverage_due (§3.7)
    citation_url: str | None = None
    # Co-located imagery (ING-8): sibling frame(s) for a citation whose primary payload is prose/records
    # (e.g. a GEOINT write-up beside its satellite frame). Repo-relative paths, same convention as
    # ``citation_url``. A list (not a single pointer) so a source with several frames stays representable;
    # each is co-loaded into extraction via the VLM lane alongside the primary text lane — never a
    # replacement for it. Empty for a source with no sibling imagery (the common case).
    images: list[str] = []
    # The date the document ITSELF states (a "DATE OF REPORT:" line, a post timestamp, a filing/issue
    # date) — ISO ``YYYY-MM-DD`` (ING-7). Populated only from a verbatim, unambiguous statement in the
    # source; left unset when the document carries no usable day-level date (never inferred/approximated
    # — a fabricated date is a disqualifying failure, master non-negotiable). Threaded through to
    # ``report_time`` at extraction; distinct from ``ingest_time`` (when *we* received it, pinned) and
    # from ``event_time`` (when the fact was true in the world, extracted per-transform from doc content).
    report_date: str | None = None
