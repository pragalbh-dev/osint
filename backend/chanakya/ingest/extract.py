"""Source-typed, TYPE-guided **extraction** — the linchpin that turns a loaded document into a list
of provenance-bearing :class:`~chanakya.schemas.claim.ClaimRecord`\\ s, upstream of ``store.append``.

This is where the *unit of analysis* is minted: one **sourced claim** (``Source S, dated D, asserts
<s,p,o>``), never a document or a text chunk. The pipeline per document is deliberately three flat,
inspectable steps — no cleverness hidden in a validator (gate G1):

1. **dispatch** — :func:`format_sniffer` reads deterministic *raw-text cues* to pick one of six native
   *formats* (a source axis, never a subject axis — gates G9/G11). The credibility ``source_type`` is a
   hint that splits the two ambiguous families (official → PR|NOTAM, customs-tender → BoL|tender); the
   raw text is the arbiter and the fallback.
2. **extract** — the format's all-optional pydantic schema is turned into a JSON tool schema
   (``model_json_schema()``) and handed to the forced-single-tool :class:`ExtractionClient`. The schema
   carries **generic ontology TYPES only** (node / edge / event type names) — *never* an instance,
   subject, or anchor ("HQ-9" is a value the model fills from the source, never a field the schema
   names). Every extracted item carries a verbatim ``source_quote`` — the provenance anchor.
3. **transform** — a deterministic per-format ``transform_*`` maps each filled field to a typed claim
   by a *fixed lookup table* (field → ontology TYPE), **never by inference**. Three disciplines are
   mechanised here:

   * **All-optional = anti-fabrication.** A source that states nothing yields **zero** claims. Every
     schema field is optional; the model fills only what the source states; the transform emits only
     what the model filled.
   * **Extract-raw guardrail.** A *stated* alias / "formerly" / "see also" becomes a ``same-as``
     relationship claim; the transform **never** resolves the *unstated* — it never decides two
     differently-named entities are one, and never links a shell consignee to a SAM end-user/depot.
     That resolution is RESOLVE's job, at rebuild.
   * **Structural provenance (G4).** Every emitted claim carries a ``doc_ref`` that resolves to the
     exact source span: the transform does ``loaded.text.find(source_quote)`` → char span →
     ``loaded.doc_ref`` / ``loaded.locate``, falling back to the field value, then the whole line, so
     **every** claim is one-click traceable. Record-per-line formats (customs) cite the row.

The three-tier attribute promotion the transform applies: **tier-1** facts that earn their own node /
edge / event (an ``EntityDescriptor`` / ``EventDescriptor`` / ``Triple``); **tier-2** knowledge attrs
that ride on a node/event (``attrs`` — a range, a count-state, a coordinate); **tier-3** source-native
context with no ontology home (HS-code, container#, B/L#) → the loose ``ClaimRecord.attributes`` bag,
traceable and queryable but never traversed.

Everything here runs at *extraction* time. The claim-emitting path is deterministic (no clock, no RNG):
``ingest_time`` is passed in, IDs are minted in a serial pass. Claims come back with *provisional*
readable IDs (``ClaimRecord.claim_id`` is required); ``dedup.assign_claim_ids`` reassigns the canonical
ones once within-doc restatements are folded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from chanakya import edge_direction
from chanakya.ingest import adapters
from chanakya.ingest import imagery as imagery_gate
from chanakya.ingest.client import ExtractionClient
from chanakya.ingest.loaders import LoadedDoc
from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas import ConfigBundle, make_claim_id
from chanakya.schemas.claim import (
    ClaimPayload,
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    EventDescriptor,
    Extraction,
    Triple,
)
from chanakya.schemas.values import (
    DateValue,
    ExactDate,
    LabelDate,
    Location,
    Quantity,
    canonical_iso_bounds,
)

# ── the generic ontology TYPE vocabulary (mirrors config/ontology.yaml; NOT instance content) ─────

# These are *type names*, the schema/transform vocabulary — hardcoding them is not a G9 violation
# (G9 forbids subject/anchor/instance content, not the ontology's own type axis). The transform maps
# fields → these strings by the fixed tables below, never by LLM inference. When a stated fact's type
# is absent from the *live* config ontology, the claim is still emitted (closest generic type) and the
# off-ontology type is flagged in tier-3 ``attributes`` — extensibility without silent loss.

NodeTypeName = Literal[
    "manufacturer", "trading_org", "component", "variant", "contract_import_event", "unit",
    "basing_site", "interceptor_stockpile", "techdata_authority", "source", "indicator", "known_gap",
]
EventTypeName = Literal["TransferEvent", "InductionEvent", "SightingEvent", "ExerciseEvent"]

# The relationship-predicate enum handed to the model is NOT a hardcoded literal — it is driven at
# schema-build time from :meth:`EdgeLaneIndex.extractor_edges` (the ~10 relationship edges) by
# :func:`_constrain_relation_enum`, so the model can only assert real relationship edges. Identity /
# evidence / derived edges (``same-as``, ``distinct-from``, ``corroborates`` …) are deliberately absent
# from that enum — identity still flows through its OWN dedicated fields (``aka`` / ``designators`` /
# ``aliases`` / ``distinctions``), never the ``relations`` slot (D-A, DECISIONS §6 "EVAL").

# event_kind (a source-neutral verb the schema offers the model) → the ontology event TYPE.
_EVENT_KIND_TO_TYPE: dict[str, EventTypeName] = {
    "transfer": "TransferEvent",
    "induction": "InductionEvent",
    "sighting": "SightingEvent",
    "exercise": "ExerciseEvent",
}

Format = Literal[
    "prose_claim", "notam_navwarning", "customs_gd_bol",
    "tender_procurement", "social_post", "imagery_geoint",
]


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The six all-optional extraction schemas (generic TYPES only — never an instance/subject/anchor).
#
# Plain ``BaseModel`` (extra defaults to "ignore") so ``model_json_schema()`` emits NO
# ``additionalProperties: false`` and NO ``required`` list — a permissive tool schema (never Anthropic
# strict-mode / never a forced field). The schema exists only to describe the tool; the transforms read
# the model's filled dict *by key*, tolerantly, so a noisy LLM value never crashes extraction.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

class OrgMention(BaseModel):
    """A named organization the source states (a manufacturer, exporter, consignee, shipper…)."""

    name: str | None = None
    role: str | None = None  # e.g. "manufacturer" | "export-agent" | "consignee" | "shipper"
    aka: str | None = None  # a STATED alias / "formerly" / "see also" for THIS org → a same-as claim
    origin_country: str | None = None
    source_quote: str | None = None  # verbatim text this item is based on (provenance anchor)


class UnitMention(BaseModel):
    """A named operating/military unit or force element the source states."""

    name: str | None = None
    echelon: str | None = None
    service_branch: str | None = None
    home_garrison: str | None = None
    source_quote: str | None = None


class VariantMention(BaseModel):
    """A named weapon-system / variant the source states (the *value* is the source's, never fixed)."""

    name: str | None = None
    family: str | None = None
    designators: list[str] = []  # stated alternate designators (each a candidate same-as)
    range_text: str | None = None
    confidence_language: str | None = None  # the source's own hedge ("consistent with", "probable")
    signature_geometry: str | None = None  # the source's CHARACTERISTIC / reference physical layout of THIS
    # weapon TYPE in general (e.g. "consistent with HQ-9 deployments", "the characteristic X site layout",
    # "associated with the X system") — set ONLY when the source generalizes a signature to the system/type,
    # NEVER a single site's own observed geometry (that belongs on the site).
    source_quote: str | None = None


class ComponentMention(BaseModel):
    """A named sub-system / component the source states (a radar, an interceptor, a test set…)."""

    name: str | None = None
    component_class: str | None = None
    functional_role: str | None = None
    radar_band: str | None = None
    quantity_text: str | None = None
    count_state: str | None = None
    source_quote: str | None = None


class SiteMention(BaseModel):
    """A named place / basing-or-logistics site the source states, with any stated location string."""

    name: str | None = None
    site_type: str | None = None
    location_text: str | None = None  # any surface form — coords / toponym / "<dist> <bearing> of X"
    signature_geometry: str | None = None
    occupancy_state: str | None = None
    source_quote: str | None = None


class SourceMention(BaseModel):
    """A source/register/origin the document itself names (SIPRI, a database, an upstream report)."""

    name: str | None = None
    source_type: str | None = None
    source_quote: str | None = None


class EventMention(BaseModel):
    """A stated event — a transfer / induction / sighting / exercise — with its parties + time + place."""

    event_kind: Literal["transfer", "induction", "sighting", "exercise"] | None = None
    system: str | None = None
    supplier: str | None = None
    recipient: str | None = None
    unit: str | None = None
    quantity_text: str | None = None
    count_state: str | None = None
    date_text: str | None = None
    location_text: str | None = None
    source_quote: str | None = None


class RelationMention(BaseModel):
    """A relationship the source *explicitly states*, keyed by a generic edge TYPE (never inferred).

    ``relation`` is typed ``str`` here; the *allowed values* are narrowed to the extractor-edge enum in
    the tool schema at build time (:func:`_constrain_relation_enum`). The model's verb is only a hint —
    the transform re-lanes the fact onto the edge its endpoint types imply (:meth:`_Emitter.relation`).

    ``date_text`` is the **valid-time** slot (EVAL RCA D-P4.6): *when the source says the relationship
    was true*, not when the document was published. Every other mention type already has one
    (``EventMention.date_text`` / ``SightingMention.time_text`` / ``PassMention.pass_date``); without it
    a *perishable* relationship — where a unit is based, what a magazine currently holds — could never
    age, be ordered against a later statement of the same fact, or be superseded. It stays **optional**:
    an identity or durable relationship legitimately carries no date, and forcing one would only invite
    a fabricated date on the ~78 identity claims that have none (D-P4.6 rejects "every relation gets a
    date"). :meth:`_Emitter.relation` resolves the fallback ladder and records which rung fired.
    """

    relation: str | None = None
    subject: str | None = None
    object: str | None = None
    date_text: str | None = Field(
        default=None,
        description=(
            "When the source says this relationship was TRUE (not the publication date) — e.g. the "
            "imagery pass date for an equipment-at-site observation, the induction date, the contract "
            "date. Copy the source's own wording. Leave empty when the source states no such date; "
            "never guess one."
        ),
    )
    source_quote: str | None = None


class AliasMention(BaseModel):
    """A stated identity/non-identity between two named things → a ``same-as`` / ``distinct-from`` claim."""

    name_a: str | None = None
    name_b: str | None = None
    source_quote: str | None = None


class DenialMention(BaseModel):
    """A stated *negation* / observed absence → a negative-polarity observation claim."""

    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    source_quote: str | None = None


class ProseClaim(BaseModel):
    """Analytic / official prose (curated-register, trade-media, think-tank, official-PR, exporter media)."""

    sources: list[SourceMention] = []
    manufacturers: list[OrgMention] = []
    units: list[UnitMention] = []
    variants: list[VariantMention] = []
    components: list[ComponentMention] = []
    basing_sites: list[SiteMention] = []
    events: list[EventMention] = []
    relations: list[RelationMention] = []
    aliases: list[AliasMention] = []
    distinctions: list[AliasMention] = []
    denials: list[DenialMention] = []


class NoticeMention(BaseModel):
    """One ICAO NOTAM / NAVAREA notice — an activity in a place over a time window."""

    notice_id: str | None = None
    location_ref: str | None = None  # coords / ICAO / place string
    activity: str | None = None
    hazard_type: str | None = None
    time_window: str | None = None
    event_kind: Literal["sighting", "exercise"] | None = None  # military activity → an event; else None
    source_quote: str | None = None


class NotamNavWarning(BaseModel):
    """ICAO NOTAM / NAVAREA navigational-warning strings (official, machine-formatted)."""

    notices: list[NoticeMention] = []


class GdRow(BaseModel):
    """One customs Goods-Declaration / bill-of-lading row — the many-claims-per-row unit."""

    gd_no: str | None = None
    bl_no: str | None = None
    consignee: OrgMention | None = None
    shipper: OrgMention | None = None
    port_of_discharge: str | None = None
    terminal: str | None = None
    filing_date: str | None = None
    declared_value: str | None = None
    hs_code: str | None = None
    containers: list[str] = []
    description: str | None = None
    count_state: str | None = None
    destination_ref: str | None = None  # a STATED onward destination (kept as its own place, never resolved)
    destination_quote: str | None = None
    freight_forwarder: str | None = None
    aliases: list[AliasMention] = []  # stated same-as within the row (spelling variants, "formerly")
    source_quote: str | None = None


class CustomsGdBol(BaseModel):
    """Customs GD / bill-of-lading extract, record-per-line + annotations (customs-tender family)."""

    rows: list[GdRow] = []


class StockpileMention(BaseModel):
    """A stated interceptor / spares stockpile posture — the perishable sustainment node (depth, resupply)."""

    name: str | None = None
    stocked_round: str | None = None
    magazine_depth: str | None = None
    resupply_lead_time: str | None = None
    source_quote: str | None = None


class TechDataMention(BaseModel):
    """A stated technical-data / design-authority holding — the durable sustainment node (TDP, calibration)."""

    name: str | None = None
    holds: str | None = None  # TDP | firmware | crypto-keys | calibration-ref (as the source states it)
    foreign_control: str | None = None
    source_quote: str | None = None


class TenderProcurement(BaseModel):
    """A procurement tender skeleton — numbered clauses + [REDACTED] (customs-tender family)."""

    tender_id: str | None = None
    procuring_org: UnitMention | None = None
    system: VariantMention | None = None
    oem: OrgMention | None = None
    line_items: list[ComponentMention] = []
    contract_value: str | None = None
    issue_date: str | None = None
    # A sustainment tender states a spares/stockpile posture and/or a technical-data authority — each a
    # first-class sustainment NODE (interceptor_stockpile / techdata_authority). The rolled-up
    # `sustained-by` edge is SCORE's derived synthesis, NOT emitted here (Phase-4 boundary).
    stockpile: StockpileMention | None = None
    techdata_authority: TechDataMention | None = None
    aliases: list[AliasMention] = []
    distinctions: list[AliasMention] = []  # explicit "no interoperability" / "not related" → distinct-from
    relations: list[RelationMention] = []
    source_quote: str | None = None


class SightingMention(BaseModel):
    """A sighting a social post claims — a system/unit doing something somewhere at some time."""

    system: str | None = None
    unit: str | None = None
    activity: str | None = None
    location_text: str | None = None
    time_text: str | None = None
    source_quote: str | None = None


class PostMention(BaseModel):
    """One social post — a handle + timestamp + status URL + body, with any claimed sightings."""

    handle: str | None = None
    posted_at: str | None = None
    status_url: str | None = None
    body: str | None = None
    sightings: list[SightingMention] = []
    negations: list[DenialMention] = []  # "nothing unusual to report" → an observed absence
    source_quote: str | None = None


class SocialPost(BaseModel):
    """Handle + datetime + status-URL + body, multi-post (named-social / anon-social)."""

    posts: list[PostMention] = []


class PassMention(BaseModel):
    """One imagery pass/observation — a dated read of object(s) at a resolution, with a count."""

    pass_date: str | None = None
    object_type: str | None = None
    object_count_text: str | None = None
    count_state: str | None = None
    dimensions: str | None = None
    location_text: str | None = None
    source_quote: str | None = None


class GapMention(BaseModel):
    """A stated collection gap — what could not be observed, and when next coverage is due."""

    description: str | None = None
    next_coverage_due: str | None = None
    missing_slot: str | None = None
    source_quote: str | None = None


class OccupancyMention(BaseModel):
    """Equipment **observed at a site** on a date — the honestly-observable occupancy layer (D-P4.2).

    A satellite write-up can state that a launcher cluster / radar / system type was *seen at* a named
    place on a named pass; it almost never states that a *designated formation* is based there. So this
    is deliberately equipment→site (``observed-at``), a lane of its own — the derived unit-attribution
    (``based-at``) is minted separately, from this plus a formation reference, at its own lower
    confidence (:mod:`chanakya.ingest.basing`). Fusing the two into one confident basing assertion is
    exactly what the corpus's recycled-image and relocation-spoof traps are built to punish.
    """

    observed: str | None = None       # what was seen, as the source names it (a system type, a radar, a TEL)
    site: str | None = None           # the site/place it was seen at, as the source names it
    observed_date: str | None = None  # the pass/observation date the source gives for THIS sighting
    occupancy_state: str | None = None  # the source's own word: "occupied" | "empty" | "active" | …
    source_quote: str | None = None


class ImageryGeoint(BaseModel):
    """Satellite GEOINT analyst *prose* (the co-located .png runs the VLM path in imagery.py).

    ``occupancy`` / ``units`` / ``relations`` close EVAL RCA §2.3: this schema had **no relationship
    slot at all**, so the relocation documents (d17/d18) were *structurally* incapable of stating that
    anything was anywhere — 21 claims between them, zero relationships. Occupancy is the lane the
    imagery genuinely supports; ``relations`` additionally lets a write-up that plainly names a
    formation at a site say so directly (D-P4.1 overturns the old blanket no-extract rule for basing).
    """

    site: SiteMention | None = None
    observations: list[PassMention] = []
    occupancy: list[OccupancyMention] = []
    assessed_types: list[VariantMention] = []
    components: list[ComponentMention] = []
    units: list[UnitMention] = []
    relations: list[RelationMention] = []
    collection_gaps: list[GapMention] = []
    source_quote: str | None = None


#: The format → schema registry. ``extract_document`` builds the tool schema from ``model_json_schema()``.
SCHEMAS: dict[str, type[BaseModel]] = {
    "prose_claim": ProseClaim,
    "notam_navwarning": NotamNavWarning,
    "customs_gd_bol": CustomsGdBol,
    "tender_procurement": TenderProcurement,
    "social_post": SocialPost,
    "imagery_geoint": ImageryGeoint,
}

_TOOL_NAMES: dict[str, str] = {fmt: f"extract_{fmt}" for fmt in SCHEMAS}

_SYSTEM_BASE = (
    "You are a structured-extraction tool for an open-source intelligence pipeline. Read the document "
    "and fill the tool with ONLY facts the document explicitly states. Leave every field the document "
    "does not state empty — never invent, infer, or complete a name, number, date, or place. For every "
    "item you fill, put the exact verbatim text it is based on in `source_quote`. Extract identities as "
    "the source gives them: a stated alias, 'formerly', 'see also', spelling variant, or 'also known as' "
    "is an alias pair — NEVER merge two differently-named things into one, and never resolve a hidden or "
    "unstated identity. Use the generic type slots provided; put whatever names/designations the source "
    "uses as values. When you record a relationship the source dates — where something is based or was "
    "seen, when a system entered service, when a shipment moved — copy the source's own date wording "
    "into that relation's `date_text`; leave it empty when the source gives no such date. "
    "A physical/visual SIGNATURE can describe either one specific SITE (that site's own observed layout) or "
    "a WEAPON TYPE in general (the type's characteristic / reference layout, shared across its deployments). "
    "Keep the two separate. Put a single site's observed geometry in that site's `signature_geometry`. Fill a "
    "variant's `signature_geometry` ONLY when the source itself states what the TYPE characteristically looks "
    "like — e.g. 'a layout consistent with prior HQ-9 deployments elsewhere', 'the characteristic HQ-9 site "
    "layout', 'a signature associated with the HQ-9 system'. Do NOT fill it when the source merely identifies "
    "one site by comparing it to references (e.g. 'assessed as HQ-9 based on its layout, compared against "
    "reference signatures') — that is a site observation plus an identification method, not a stated type "
    "signature. Never generalize a single site's observation into a type signature on your own."
)
_SYSTEM_PROMPTS: dict[str, str] = {
    "prose_claim": _SYSTEM_BASE + " This is analytic or official prose.",
    "notam_navwarning": _SYSTEM_BASE
    + " This is an ICAO NOTAM / NAVAREA bulletin: extract each notice's id, location, activity, hazard "
    "and time window. Only set event_kind when the notice describes military sighting/exercise activity.",
    "customs_gd_bol": _SYSTEM_BASE
    + " This is a customs goods-declaration / bill-of-lading extract, one shipment per row. For each row "
    "capture consignee, shipper (with any stated aka/spelling-variant), ports, filing date, declared "
    "value, HS code, containers, and any stated onward destination — keep them as stated, do not link "
    "the consignee to the destination.",
    "tender_procurement": _SYSTEM_BASE
    + " This is a procurement tender: capture the procuring org, the system referred to (with all stated "
    "aliases), the OEM, line items, value and dates. An explicit 'no interoperability'/'not related' "
    "statement between two systems is a distinct-from pair, not a same-as.",
    "social_post": _SYSTEM_BASE
    + " These are social-media posts: one entry per post with its handle, timestamp, status URL and "
    "body. A claimed sighting is a sighting; 'nothing to report'/'no movement' is a negation.",
    "imagery_geoint": _SYSTEM_BASE
    + " This is a satellite imagery analyst report: capture the site and its coordinates, each dated "
    "pass with object type/count, the assessed system type (with the analyst's own confidence wording), "
    "components, any military formation/unit the report names, and every stated collection gap. When "
    "the report states that equipment (a system type, launchers, a radar) was OBSERVED AT a named site, "
    "record it in `occupancy` with the site and the date of the pass it was seen on — this is what the "
    "imagery observes. Only put a relationship in `relations` when the report states it outright.",
}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# format_sniffer — deterministic raw-text dispatch (documented rules).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _cue_hits(text_upper: str, cues: tuple[str, ...]) -> int:
    """How many distinct cue strings appear in ``text_upper`` (a cheap raw-text signature counter)."""
    return sum(1 for c in cues if c in text_upper)


# Raw-text cue banks (upper-cased). A family is claimed when ≥2 distinct cues hit (robust to one-off
# collisions), except the strong single-token signatures (a NOTAM id line, a GD number) which are decisive.
_NOTAM_CUES = ("NOTAM", "NAVAREA", "NAVWARN", " RWY ", "AERODROME", "AIRAC", " WEF ", "Q) O", "ARP ")
_CUSTOMS_CUES = ("GD NO", "B/L NO", "BILL OF LADING", "CONSIGNEE", "SHIPPER", "HS CODE",
                 "PORT OF DISCHARGE", "DECLARED VALUE", "WEBOC", "MANIFEST")
_TENDER_CUES = ("TENDER", "BID ", "BIDDER", "ANNEXURE", "EARNEST MONEY", "EMD", "PROCUREMENT",
                "[REDACTED]", "ELIGIBILITY", "OEM")
_SOCIAL_CUES = ("HANDLE:", "STATUS URL", "FOLLOWERS", "@", "#", "REPOST", "RETWEET", "POSTED")
# GEOINT is detected only by *strong* analyst-report signatures — prose that merely mentions "satellite
# imagery" is analytic prose, not a GEOINT product, so those weak words are deliberately excluded.
_GEOINT_CUES = ("WGS-84", "WGS84", "OFF-NADIR", "CENTROID", "REVETMENT", "PETAL/RING", "MULTI-PASS")


def _looks_notam(text_upper: str) -> bool:
    return _cue_hits(text_upper, _NOTAM_CUES) >= 2 or "NOTAM" in text_upper


def _looks_customs(text_upper: str) -> bool:
    return _cue_hits(text_upper, _CUSTOMS_CUES) >= 2 or "GD NO" in text_upper


def _looks_tender(text_upper: str) -> bool:
    return _cue_hits(text_upper, _TENDER_CUES) >= 2


def _looks_social(text_upper: str) -> bool:
    return _cue_hits(text_upper, _SOCIAL_CUES) >= 2 or "STATUS URL" in text_upper


def _looks_geoint(text_upper: str) -> bool:
    return "GEOSPATIAL INTELLIGENCE" in text_upper or _cue_hits(text_upper, _GEOINT_CUES) >= 2


def format_sniffer(text: str, source_type: str | None) -> Format:
    """Pick the native extraction *format* from the raw text + the credibility ``source_type`` hint.

    Deterministic and subject-blind (gate G9): the decision reads document *shape*, never who the
    document is about. ``source_type`` narrows to a family; the raw text splits the two ambiguous
    families and is the fallback when the ``source_type`` is unknown. Rules, in order:

    * ``source_type`` names a **NOTAM/NAVAREA** source → ``notam_navwarning``.
    * ``source_type`` is **official** (PR / statement / ISPR) → ``notam_navwarning`` if the body shows
      NOTAM cues (a ``NOTAM`` token / ``RWY … WEF`` / ``Q) O…`` field), else ``prose_claim``.
    * ``source_type`` is **customs-tender** → ``customs_gd_bol`` if customs cues (a ``GD No`` / two of
      ``Consignee``/``Shipper``/``B/L``/``HS Code``/``Declared Value``), else ``tender_procurement`` if
      tender cues, else ``customs_gd_bol`` (customs is the record-shaped default).
    * ``source_type`` is **social** → ``social_post``; **satellite/imagery** → ``imagery_geoint``.
    * Unknown ``source_type`` → sniff the raw text in priority NOTAM → customs → tender → social →
      GEOINT, else ``prose_claim`` (the analytic-prose default).
    """
    st = (source_type or "").lower()
    up = text.upper()

    is_notam_src = any(k in st for k in ("notam", "navarea", "navwarn", "navigation-warning"))
    is_official = any(k in st for k in ("official", "press", "statement", "ispr", "pr-", "-pr", "govt"))
    is_customs_tender = any(k in st for k in ("customs", "tender", "procurement", "weboc", "bol", "bill"))
    is_social = any(k in st for k in ("social", "twitter", "telegram", "forum", "handle"))
    is_satellite = any(k in st for k in ("satellite", "imagery", "geoint", "geospatial"))

    if is_notam_src:
        return "notam_navwarning"
    if is_official:
        return "notam_navwarning" if _looks_notam(up) else "prose_claim"
    if is_customs_tender:
        if _looks_customs(up):
            return "customs_gd_bol"
        return "tender_procurement" if _looks_tender(up) else "customs_gd_bol"
    if is_social:
        return "social_post"
    if is_satellite:
        return "imagery_geoint"

    # Unknown source_type → pure raw-text sniff (NOTAM first: its machine format is unmistakable).
    if _looks_notam(up):
        return "notam_navwarning"
    if _looks_customs(up):
        return "customs_gd_bol"
    if _looks_tender(up):
        return "tender_procurement"
    if _looks_social(up):
        return "social_post"
    if _looks_geoint(up):
        return "imagery_geoint"
    return "prose_claim"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Transform machinery — tolerant dict access, provenance resolution, the claim emitter.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _str(d: dict[str, Any], key: str) -> str | None:
    """A trimmed non-empty string from a filled-dict field, else ``None`` (never fabricates)."""
    v = d.get(key)
    return v.strip() if isinstance(v, str) and v.strip() else None


def _strlist(d: dict[str, Any], key: str) -> list[str]:
    """A list of trimmed non-empty strings (accepts a scalar string too)."""
    v = d.get(key)
    if isinstance(v, list):
        return [x.strip() for x in v if isinstance(x, str) and x.strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def _items(d: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """The list-of-objects under ``key`` (dropping any non-dict noise)."""
    v = d.get(key)
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _obj(d: dict[str, Any], key: str) -> dict[str, Any] | None:
    """A single nested object under ``key``, else ``None``."""
    v = d.get(key)
    return v if isinstance(v, dict) else None


def _dump(v: Any) -> Any:
    """JSON-plain form of a value object for a loose ``attrs``/``attributes`` bag (byte-stable)."""
    return v.model_dump(mode="json") if isinstance(v, BaseModel) else v


def _prune(attrs: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None``/empty entries so an all-optional source never freezes empty attr keys."""
    return {k: v for k, v in attrs.items() if v not in (None, "", [], {})}


def _resolve_doc_ref(loaded: LoadedDoc, quote: str | None, *, fallback: str | None = None,
                     cite_row: bool = False) -> DocRef:
    """Attach an exact source span to a claim (gate G4) — the provenance mechanism, verbatim-first.

    Finds ``source_quote`` in the assembled text → char span → :meth:`LoadedDoc.doc_ref` (exact span +
    line + page). Falls back to the field value, then to the whole first content region, then the file.
    ``cite_row`` additionally stamps the table ``row`` from the overlapping region (customs manifest).
    The returned ``DocRef`` is always resolvable (``file`` is always set).
    """
    for probe in (quote, fallback):
        if not probe:
            continue
        idx = loaded.text.find(probe)
        if idx < 0:
            continue
        end = idx + len(probe)
        if cite_row:
            regions = loaded.locate(idx, end)
            r = regions[0] if regions else None
            return DocRef(
                file=loaded.file, span=(idx, end),
                line=(r.line if r else None), row=(r.row if r else None),
                page=(r.page if r else None),
            )
        return loaded.doc_ref(idx, end)

    # No verbatim/value hit: cite the whole first content region, else the file (still resolvable).
    if loaded.regions:
        r0 = loaded.regions[0]
        return DocRef(file=loaded.file, span=r0.span, line=r0.line,
                      row=(r0.row if cite_row else None), page=r0.page)
    return DocRef(file=loaded.file)


def _sanitize_doc_token(source_id: str) -> str:
    """A kebab ``[a-z0-9-]`` doc token for a readable provisional claim id (``d05_x`` → ``d05-x``)."""
    out: list[str] = []
    prev_dash = False
    for ch in source_id.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    token = "".join(out).strip("-")
    return token or "doc"


# ── relation valid-time: the fallback ladder + its honesty channel (D-P4.6) ────────────────────────

#: Ontology ``freshness_class`` values on which a relationship's date is **load-bearing** — the edge
#: decays, so an undated claim on it can never age, order or supersede. A relation re-laned onto one of
#: these and left undated is flagged (:data:`_UNDATED_ATTR`), never dropped and never given a made-up
#: date. Durable / identity / structural edges are exempt by design (D-P4.6 rejected "every relation
#: gets a date": 78 of 126 relationship claims are identity, where a date is meaningless and demanding
#: one only invites fabrication).
_DATED_CLASSES: frozenset[str] = frozenset({"perishable", "semi-durable"})

#: Tier-3 keys recording *which rung of the ladder* produced a relation's ``event_time`` — the same
#: honesty discipline as ``values.BoundarySource``, one level up: the boundary source says how a date
#: string became ISO bounds, this says where the date came from at all.
_RUNG_ATTR = "_event_time_rung"
_UNDATED_ATTR = "_undated_perishable"

#: The ladder, in order. ``stated`` — the source dated the relationship itself. ``observation`` — the
#: enclosing observation/sentence (an imagery pass date, a post timestamp) supplied it. ``report_time``
#: — nothing dated the fact, so the document's own report date bounds it (an upper bound on when the
#: fact was true, re-stamped ``relative`` because it was resolved *against* the report, not stated).
_RUNG_STATED = "stated"
_RUNG_OBSERVATION = "observation"
_RUNG_REPORT = "report_time"

#: The affirmative-occupancy vocabulary, shared with the imagery lane's corroboration gate so "an empty
#: site is not a deployment" means the same thing on the text and pixel paths.
_OCCUPIED_TOKENS = imagery_gate._OCCUPIED_TOKENS


def states_vacancy(occupancy_state: str | None) -> bool:
    """Does a stated occupancy word say the site is **not** occupied? (Unstated ⇒ no claim either way.)"""
    if not occupancy_state or not occupancy_state.strip():
        return False
    return not any(tok in occupancy_state.lower() for tok in _OCCUPIED_TOKENS)


def _restamp_relative(value: DateValue) -> DateValue:
    """Re-stamp a date borrowed from the document's ``report_time`` as ``boundary_source="relative"``.

    The report date is a real, explicit date *of the document* — but as the *relationship's* valid time
    it was resolved by inference against the report, which is precisely what the ``relative`` boundary
    source means (``schemas/values.py``). Copying it across without re-stamping would launder a derived
    bound into an explicit one; SCORE and the analyst both read that field.
    """
    if isinstance(value, (ExactDate, LabelDate)):
        return value.model_copy(update={"boundary_source": "relative"})
    return value


def _locator(ref: DocRef) -> str:
    """A short readable locator for a claim id, derived from the ref's tightest positional axis."""
    if ref.row is not None:
        return f"row{ref.row}"
    if ref.line is not None:
        return f"l{ref.line}"
    if ref.span is not None:
        return f"c{ref.span[0]}"
    return "x"


@dataclass
class _Emitter:
    """Collects claims for one document, minting deterministic provisional ids in a serial pass.

    Deliberately not a validator and not clock/RNG-bound (gate G1/G9): everything it stamps is frozen
    now, upstream of the append, so ``rebuild()`` only ever reads it. ``dedup.assign_claim_ids`` later
    folds within-doc restatements and reassigns the canonical ids — these ids are provisional but real
    (``ClaimRecord.claim_id`` is required).
    """

    source_id: str
    loaded: LoadedDoc
    model_id: str
    report_time: DateValue | None
    ingest_time: DateValue | None
    node_types: frozenset[str]
    edge_types: frozenset[str]
    event_types: frozenset[str]
    lane: EdgeLaneIndex           # the domain/range re-lane + extraction enum (D-A)
    dir_rules: dict[str, edge_direction.DirectionRule]  # partial-typing orientation fallback
    geocoder: adapters.Geocoder | None = None
    _n: int = 0
    claims: list[ClaimRecord] = field(default_factory=list)
    # name -> entity_type of every entity emitted *for this document*, so a relation's endpoints can be
    # typed from the entities the same document mentioned (write-time endpoint-type recovery).
    _entity_types: dict[str, str] = field(default_factory=dict)
    # name -> the claim id of the *first* entity claim emitted for that name in this document: the
    # document-local **mention id**. Relationship claims carry it per endpoint (mention-keyed provenance),
    # so a relation stays anchored to the mention that named it — and follows that mention automatically
    # if the entity is later split. First-writer-wins, mirroring ``_entity_types``, so it is deterministic.
    _entity_claim_ids: dict[str, str] = field(default_factory=dict)

    def location(self, raw: str | None, *, surface_format: str | None = None) -> Location | None:
        """Normalize a stated location, injecting the doc's geocoder — the one location call-site.

        Centralises every transform's ``normalize_location`` through the emitter so the injected
        geocoder (gazetteer coord-cache → Nominatim, or ``None`` = offline) reaches all of them
        uniformly. Coordinate freezing only; ``resolved_place_ref`` stays ``None`` (RESOLVE's, at
        rebuild). Runs upstream of the append (gate G1).
        """
        return adapters.normalize_location(raw, surface_format=surface_format, geocoder=self.geocoder)

    def _emit(self, payload: ClaimPayload, asserts: str, ref: DocRef, *,
              kind: str = "observation", polarity: str = "positive",
              event_time: DateValue | None = None, attributes: dict[str, Any] | None = None) -> str:
        """Freeze one claim and return its **provisional** id (the document-local mention/claim handle)."""
        self._n += 1
        cid = make_claim_id(_sanitize_doc_token(self.source_id), _locator(ref), index=self._n)
        attrs = _prune(attributes) if attributes else {}
        self.claims.append(ClaimRecord(
            claim_id=cid,
            source_id=self.source_id,
            doc_ref=ref,
            kind=kind,
            polarity=polarity,
            asserts=asserts,
            payload=payload,
            event_time=event_time,
            report_time=self.report_time,
            ingest_time=self.ingest_time,
            extraction=Extraction(method="llm", version=self.model_id, model_conf=1.0),
            attributes=attrs or None,
        ))
        return cid

    def entity(self, entity_type: str, name: str, ref: DocRef, *, attrs: dict[str, Any] | None = None,
               event_time: DateValue | None = None, attributes: dict[str, Any] | None = None) -> None:
        self._entity_types.setdefault(name, entity_type)  # first writer wins → deterministic recovery
        attributes = self._offontology(self.node_types, entity_type, attributes)
        cid = self._emit(
            EntityDescriptor(entity_type=entity_type, name=name, attrs=_prune(attrs or {})),
            "entity", ref, event_time=event_time, attributes=attributes,
        )
        self._entity_claim_ids.setdefault(name, cid)  # this document's mention id for ``name``

    def event(self, event_type: str, ref: DocRef, *, participants: list[str] | None = None,
              time_interval: DateValue | None = None, location: Location | None = None,
              attrs: dict[str, Any] | None = None, polarity: str = "positive",
              event_time: DateValue | None = None, attributes: dict[str, Any] | None = None) -> None:
        attributes = self._offontology(self.event_types, event_type, attributes)
        self._emit(
            EventDescriptor(
                event_type=event_type,
                time_interval=time_interval,
                location=location,
                participants=[p for p in (participants or []) if p],
                attrs=_prune(attrs or {}),
            ),
            "event", ref, polarity=polarity, event_time=event_time or time_interval,
            attributes=attributes,
        )

    def triple(self, subject: str, predicate: str, obj: str, ref: DocRef, *,
               object_value: Quantity | Location | DateValue | None = None,
               polarity: str = "positive", event_time: DateValue | None = None,
               attributes: dict[str, Any] | None = None) -> None:
        """Emit a relationship claim **verbatim** — the raw path (identity edges + already-canonical edges).

        Never re-lanes: identity claims (``same-as`` / ``distinct-from`` from stated aliases/designators)
        and deterministic structural role-edges keep the exact predicate they were given. LLM-asserted
        relationships go through :meth:`relation`, which re-lanes onto the endpoint-implied edge first.

        Each endpoint also carries the **mention** that named it (:meth:`_mention_refs`) whenever this
        document emitted an entity claim for that surface form — mention-keyed provenance, added on top of
        the verbatim strings, never in place of them.
        """
        attributes = self._offontology(self.edge_types, predicate, attributes)
        attributes = self._mention_refs(attributes, subject, obj)
        self._emit(
            Triple(subject=subject, predicate=predicate, object=obj, object_value=object_value),
            "relationship", ref, polarity=polarity, event_time=event_time, attributes=attributes,
        )

    def _mention_refs(self, attributes: dict[str, Any] | None, subject: str,
                      obj: str) -> dict[str, Any] | None:
        """Anchor each endpoint to the mention (entity claim) that named it, where this doc has one.

        Positional by construction — ``_subject_mention`` describes ``Triple.subject`` — so any later
        reorientation must swap them (``edge_direction.swap_mention_refs``). An endpoint the document
        never declared as an entity (a bare string in a relation) simply gets no ref: the surface form on
        the payload stays the only handle, exactly as before.
        """
        refs = {
            edge_direction.SUBJECT_MENTION_ATTR: self._entity_claim_ids.get(subject),
            edge_direction.OBJECT_MENTION_ATTR: self._entity_claim_ids.get(obj),
        }
        refs = {k: v for k, v in refs.items() if v is not None}
        if not refs:
            return attributes
        return {**(attributes or {}), **refs}

    def relation_time(self, edge: str | None, date_text: str | None,
                      context_time: DateValue | None,
                      attributes: dict[str, Any] | None) -> tuple[DateValue | None, dict[str, Any] | None]:
        """Resolve a relationship's **valid time** down the ladder, recording which rung fired (D-P4.6).

        ``stated relation date → the enclosing observation's date → the document's report_time → none``.
        The rung is stamped in tier-3 (:data:`_RUNG_ATTR`) alongside the resolved value's own
        ``boundary_source``, so an analyst can always see whether the date was read off the sentence,
        borrowed from the pass it sits in, or merely bounded by the publication date — three very
        different strengths of evidence that a bare ISO string would flatten into one.

        The ladder is walked for **every** relation, but only a relation whose edge decays
        (:data:`_DATED_CLASSES`) is *required* to land on a rung: reaching the bottom there is a real
        coverage gap and is flagged :data:`_UNDATED_ATTR` — surfaced, never patched with a guess. On a
        durable/identity edge an absent date is simply correct.
        """
        fclass = self.lane.freshness_class(edge) if edge else None
        decaying = fclass in _DATED_CLASSES
        stated = adapters.normalize_date(date_text, report_time=self.report_time)
        value, rung = None, None
        if stated is not None:
            value, rung = stated, _RUNG_STATED  # the source dated the fact — always taken
        elif not decaying:
            # A durable/identity relation is NOT walked down the fallback rungs: stamping every such
            # claim with the publication date would manufacture a valid time nobody asserted, on the
            # 115-of-126 claims where it is inert anyway (D-P4.6).
            return None, attributes
        elif context_time is not None:
            value, rung = context_time, _RUNG_OBSERVATION
        elif self.report_time is not None:
            value, rung = _restamp_relative(self.report_time), _RUNG_REPORT

        out = dict(attributes or {})
        if rung is not None:
            out[_RUNG_ATTR] = rung
        else:
            out[_UNDATED_ATTR] = True  # a decaying edge with no date at any rung — a coverage gap, stated
        return value, out

    def relation(self, subject: str, predicate: str, obj: str, ref: DocRef, *,
                 subj_type: str | None = None, obj_type: str | None = None,
                 object_value: Quantity | Location | DateValue | None = None,
                 event_time: DateValue | None = None, date_text: str | None = None,
                 context_time: DateValue | None = None, source_quote: str | None = None,
                 attributes: dict[str, Any] | None = None) -> None:
        """Emit an **LLM-asserted** relationship, re-laned onto the edge its endpoint types imply (D-A).

        Endpoint types are taken from ``subj_type``/``obj_type`` when the caller knows them (the
        structural transforms), else recovered from the entities this document emitted (``_entity_types``).
        Then, by how much can be typed:

        * **both typed** → :meth:`EdgeLaneIndex.relane` names the edge (and orientation). ``rejected``
          (endpoints fit no edge) records the fact as a tier-3 note on the subject node — never a
          first-class edge, never an invented predicate.
        * **one typed** → :func:`edge_direction.reversed_for_types` fixes orientation only; the as-stated
          predicate (already a valid extractor edge post enum-narrowing) is kept.
        * **neither typed** → keep the as-stated predicate, flagged tier-3 (provenance never dropped).

        THE PROVENANCE RULE: whenever the label or orientation is changed, the emitted claim carries the
        as-stated predicate, the verbatim ``source_quote`` and the re-lane reason — normalising the *label*
        so two sources of one fact corroborate on one edge, never overwriting what the source said.

        VALID TIME: the date ladder (:meth:`relation_time`) is resolved **after** the re-lane, against the
        *final* edge — because whether a date is load-bearing is a property of the edge the fact lands on,
        not of the verb the model reached for. ``event_time`` passed explicitly by a structural caller
        wins outright (it is already the resolved fact-time).
        """
        st = subj_type or self._entity_types.get(subject)
        ot = obj_type or self._entity_types.get(obj)

        def dated(edge: str | None, attrs: dict[str, Any] | None) -> tuple[DateValue | None, dict[str, Any] | None]:
            if event_time is not None:
                return event_time, attrs
            return self.relation_time(edge, date_text, context_time, attrs)

        if st is not None and ot is not None:
            result = self.lane.relane(predicate, st, ot)
            if not result.ok:  # endpoints fit no edge — record, don't invent a predicate
                self._record_rejected(subject, st, predicate, obj, ref, result.reason, source_quote)
                return
            subj_out, obj_out = (obj, subject) if result.reversed else (subject, obj)
            attrs = attributes
            if result.action == "relaned":  # label and/or orientation changed → preserve provenance
                attrs = self._relane_provenance(attributes, predicate, result.reason, source_quote)
            when, attrs = dated(result.edge or predicate, attrs)
            self.triple(subj_out, result.edge or predicate, obj_out, ref, object_value=object_value,
                        event_time=when, attributes=attrs)
            return

        if st is not None or ot is not None:  # partial typing → orientation only, predicate kept as stated
            if edge_direction.reversed_for_types(predicate, st, ot, self.dir_rules):
                reason = f"{predicate!r} reoriented ({st or '?'}->{ot or '?'})"
                attrs = self._relane_provenance(attributes, predicate, reason, source_quote)
                when, attrs = dated(predicate, attrs)
                self.triple(obj, predicate, subject, ref, object_value=object_value,
                            event_time=when, attributes=attrs)
            else:
                when, attrs = dated(predicate, attributes)
                self.triple(subject, predicate, obj, ref, object_value=object_value,
                            event_time=when, attributes=attrs)
            return

        # Neither endpoint typable: keep the as-stated predicate, flag tier-3 (never drop the provenance).
        flagged = dict(attributes or {})
        flagged["_endpoint_typing"] = "unresolved"
        if source_quote:
            flagged.setdefault("source_quote", source_quote)
        when, flagged_out = dated(predicate, flagged)
        self.triple(subject, predicate, obj, ref, object_value=object_value,
                    event_time=when, attributes=flagged_out)

    @staticmethod
    def _relane_provenance(attributes: dict[str, Any] | None, as_stated: str, reason: str,
                           source_quote: str | None) -> dict[str, Any]:
        """The provenance trio a re-laned claim must carry (as-stated predicate + verbatim quote + why)."""
        attrs = dict(attributes or {})
        attrs["_as_stated_predicate"] = as_stated
        attrs["_relane_reason"] = reason
        if source_quote:
            attrs.setdefault("source_quote", source_quote)
        return attrs

    def _record_rejected(self, subject: str, subj_type: str, predicate: str, obj: str, ref: DocRef,
                         reason: str, source_quote: str | None) -> None:
        """A relation whose endpoints fit no edge: keep the fact as a tier-3 note on the subject node.

        No first-class edge (would be an ad-hoc predicate + could mint an ``unknown`` endpoint node) and
        no invented predicate — the fact stays traceable/queryable in the evidence log but is never
        traversed. Mirrors the ``_offontology`` flag: a tier-3 attribute, not a graph edge.
        """
        rejected: dict[str, Any] = {"predicate": predicate, "object": obj, "reason": reason}
        if source_quote:
            rejected["source_quote"] = source_quote
        self.entity(subj_type, subject, ref, attributes={"_rejected_relation": rejected})

    @staticmethod
    def _offontology(vocab: frozenset[str], type_name: str,
                     attributes: dict[str, Any] | None) -> dict[str, Any] | None:
        """Flag a type absent from the *live* config ontology in tier-3 (extensible, never silent)."""
        if vocab and type_name not in vocab:
            attributes = dict(attributes or {})
            attributes["_offontology_type"] = type_name
        return attributes


def _vocab(config: ConfigBundle) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Live type-name vocabularies from the config ontology (empty → validation is skipped)."""
    onto = config.ontology
    return (
        frozenset(t.name for t in onto.node_types),
        frozenset(t.name for t in onto.edge_types),
        frozenset(t.name for t in onto.event_types),
    )


def _emitter(source_id: str, loaded: LoadedDoc, config: ConfigBundle, model_id: str,
             report_time: DateValue | None, ingest_time: DateValue | None,
             geocoder: adapters.Geocoder | None = None) -> _Emitter:
    nodes, edges, events = _vocab(config)
    return _Emitter(source_id=source_id, loaded=loaded, model_id=model_id,
                    report_time=report_time, ingest_time=ingest_time,
                    node_types=nodes, edge_types=edges, event_types=events,
                    lane=EdgeLaneIndex(config.ontology), dir_rules=edge_direction.direction_map(config),
                    geocoder=geocoder)


def _money_quantity(raw: str | None) -> Quantity | None:
    """A monetary/declared value → ``Quantity`` (thousands separators stripped so the number survives)."""
    if not raw:
        return None
    return adapters.normalize_quantity(raw.replace(",", ""))


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Per-format transforms — field → typed claim, by a fixed table (never inference).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _emit_relations(em: _Emitter, mentions: list[dict[str, Any]], *,
                    context_time: DateValue | None = None) -> None:
    """Stated ``relations`` → re-laned relationship claims, each carrying its stated valid time (D-P4.6).

    The one call-site shared by every format with a ``relations`` slot, so the date ladder can never be
    wired on one transform and forgotten on another (which is how ``event_time`` came to be omitted at
    both existing call sites while the emitter's plumbing sat complete and unused). ``context_time`` is
    the enclosing observation's date when the format has one (an imagery pass) — the ladder's second rung.
    """
    for m in mentions:
        rel, subj, obj = _str(m, "relation"), _str(m, "subject"), _str(m, "object")
        if rel and subj and obj:
            quote = _str(m, "source_quote")
            ref = _resolve_doc_ref(em.loaded, quote, fallback=subj)
            em.relation(subj, rel, obj, ref, source_quote=quote,
                        date_text=_str(m, "date_text"), context_time=context_time)


def _emit_aliases(em: _Emitter, mentions: list[dict[str, Any]], predicate: str, *,
                  cite_row: bool = False) -> None:
    """Stated ``same-as`` / ``distinct-from`` pairs → relationship claims (the extract-raw guardrail)."""
    for al in mentions:
        a, b = _str(al, "name_a"), _str(al, "name_b")
        if a and b:
            ref = _resolve_doc_ref(em.loaded, _str(al, "source_quote"), fallback=a, cite_row=cite_row)
            em.triple(a, predicate, b, ref)


def transform_prose_claim(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                          config: ConfigBundle, report_time: DateValue | None,
                          ingest_time: DateValue | None, model_id: str,
                          geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """Analytic/official prose → source / org / unit / variant / component / site entities + events +
    stated relations + alias/distinct/denial claims. Emits only what the model filled (all-optional)."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)

    for m in _items(filled, "sources"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("source", name, ref, attrs={"source_type": _str(m, "source_type")})

    for m in _items(filled, "manufacturers"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("manufacturer", name, ref,
                      attrs={"role": _str(m, "role"), "origin_country": _str(m, "origin_country")})
            aka = _str(m, "aka")
            if aka:
                em.triple(name, "same-as", aka, ref)

    for m in _items(filled, "units"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("unit", name, ref, attrs={
                "echelon": _str(m, "echelon"), "service_branch": _str(m, "service_branch"),
                "home_garrison": _str(m, "home_garrison"),
            })

    for m in _items(filled, "variants"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            rng = adapters.normalize_quantity(_str(m, "range_text"))
            em.entity("variant", name, ref, attrs={
                "family": _str(m, "family"), "designators": _strlist(m, "designators"),
                "range_km": _dump(rng), "confidence_language": _str(m, "confidence_language"),
                "site_signature_geometry": _str(m, "signature_geometry"),
            })
            for desig in _strlist(m, "designators"):
                em.triple(name, "same-as", desig, ref)

    for m in _items(filled, "components"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("component", name, ref, attrs={
                "component_class": _str(m, "component_class"),
                "functional_role": _str(m, "functional_role"), "radar_band": _str(m, "radar_band"),
            })

    for m in _items(filled, "basing_sites"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            loc = em.location(_str(m, "location_text"))
            em.entity("basing_site", name, ref, attrs={
                "site_type": _str(m, "site_type"),
                "site_signature_geometry": _str(m, "signature_geometry"),
                "occupancy_state": _str(m, "occupancy_state"), "coordinates": _dump(loc),
            })

    for m in _items(filled, "events"):
        _emit_event(em, m)

    _emit_relations(em, _items(filled, "relations"))

    _emit_aliases(em, _items(filled, "aliases"), "same-as")
    _emit_aliases(em, _items(filled, "distinctions"), "distinct-from")

    # Denials / negations are NOT emitted as edges: a negation is not a subject→object knowledge edge,
    # and its free-text endpoints would mint junk `unknown` nodes (RCA ING-1). Nothing downstream reads
    # denials today; with the pipeline drawing every triple, retaining them would still pollute the
    # graph — so the denial lane is dropped here (zero denial-derived edges / `unknown` nodes).

    return em.claims


def _emit_event(em: _Emitter, m: dict[str, Any]) -> None:
    """A prose/social ``EventMention`` → an ``EventDescriptor`` (TransferEvent / Induction / Sighting…)."""
    kind = _str(m, "event_kind")
    supplier, recipient, unit = _str(m, "supplier"), _str(m, "recipient"), _str(m, "unit")
    participants = [p for p in (_str(m, "system"), supplier, recipient, unit) if p]
    if not participants:
        return
    # Infer the event TYPE from the stated participant structure when the LLM left `event_kind` empty —
    # never blind-default a supplier→recipient transfer to a SightingEvent (which silently mis-types the
    # supply-chain / order-of-battle edges the use case is graded on).
    if kind:
        event_type = _EVENT_KIND_TO_TYPE.get(kind, "SightingEvent")
    elif supplier and recipient:
        event_type = "TransferEvent"
    elif unit and _str(m, "system"):
        event_type = "InductionEvent"
    else:
        event_type = "SightingEvent"
    ref = _resolve_doc_ref(em.loaded, _str(m, "source_quote"), fallback=participants[0])
    when = adapters.normalize_date(_str(m, "date_text"), report_time=em.report_time)
    where = em.location(_str(m, "location_text"))
    qty = adapters.normalize_quantity(_str(m, "quantity_text"), count_state=_str(m, "count_state"))
    em.event(event_type, ref, participants=participants, time_interval=when, location=where,
             attrs={"quantity": _dump(qty), "count_state": _str(m, "count_state")})


def transform_notam_navwarning(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                               config: ConfigBundle, report_time: DateValue | None,
                               ingest_time: DateValue | None, model_id: str,
                               geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """NOTAM / NAVAREA → a dated activity-in-place claim per notice. Military activity (event_kind) →
    a SightingEvent/ExerciseEvent; otherwise an ``indicator`` observation (a civil notice still yields
    a citable located fact — never a fabricated military read)."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)
    for m in _items(filled, "notices"):
        activity = _str(m, "activity")
        notice_id = _str(m, "notice_id")
        name = activity or notice_id
        if not name:
            continue
        ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=notice_id or activity)
        where = em.location(_str(m, "location_ref"))
        when = adapters.normalize_date(_str(m, "time_window"), report_time=report_time)
        tier3 = {"notice_id": notice_id, "location_ref": _str(m, "location_ref")}
        kind = _str(m, "event_kind")
        if kind:
            em.event(_EVENT_KIND_TO_TYPE.get(kind, "SightingEvent"), ref, participants=[name],
                     time_interval=when, location=where,
                     attrs={"activity": activity, "hazard_type": _str(m, "hazard_type")},
                     attributes=tier3)
        else:
            em.entity("indicator", name, ref, event_time=when, attrs={
                "indicator_class": _str(m, "hazard_type") or "navigational-notice",
                "coordinates": _dump(where), "valid_time": _dump(when),
            }, attributes=tier3)
    return em.claims


def transform_customs_gd_bol(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                             config: ConfigBundle, report_time: DateValue | None,
                             ingest_time: DateValue | None, model_id: str,
                             geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """One customs row → MANY typed claims: consignee & shipper as ``trading_org`` nodes (tier-1;
    ``manufacturer`` is reserved for real OEMs — ING-3), a ``contract_import_event`` NODE with the row's
    own roles projected into ``exported-by``→shipper / ``imported-by``→consignee edges (ING-2), a
    TransferEvent carrying port (Location) + filing date (Date) + declared value (Quantity), with
    HS-code/container#/B-L# in the tier-3 ``attributes`` bag. A stated alias/'formerly'/spelling-variant →
    a ``same-as`` claim; a stated onward destination is kept as its OWN ``basing_site`` — the consignee is
    NEVER linked to it (the unstated shell→depot / import→end-user resolution is RESOLVE's)."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)
    for row in _items(filled, "rows"):
        row_ref = _resolve_doc_ref(loaded, _str(row, "source_quote"), cite_row=True)
        tier3 = _prune({
            "gd_no": _str(row, "gd_no"), "bl_no": _str(row, "bl_no"),
            "hs_code": _str(row, "hs_code"), "containers": _strlist(row, "containers"),
            "freight_forwarder": _str(row, "freight_forwarder"),
        })

        participants: list[str] = []
        roles: dict[str, str] = {}
        for slot, role in (("consignee", "consignee"), ("shipper", "shipper")):
            org = _obj(row, slot)
            oname = _str(org, "name") if org else None
            if org and oname:
                oref = _resolve_doc_ref(loaded, _str(org, "source_quote"), fallback=oname, cite_row=True)
                em.entity("trading_org", oname, oref,
                          attrs={"role": role, "origin_country": _str(org, "origin_country")},
                          attributes=dict(tier3))
                participants.append(oname)
                roles[role] = oname
                aka = _str(org, "aka")
                if aka:
                    em.triple(oname, "same-as", aka, oref)

        _emit_aliases(em, _items(row, "aliases"), "same-as", cite_row=True)

        # The shipment itself → a TransferEvent (port=location, filing date=date, value=quantity).
        port = _str(row, "port_of_discharge") or _str(row, "terminal")
        where = em.location(port)
        when = adapters.normalize_date(_str(row, "filing_date"), report_time=report_time)
        value = _money_quantity(_str(row, "declared_value"))
        if participants or where or when or value:
            em.event("TransferEvent", row_ref, participants=participants, time_interval=when,
                     location=where, event_time=when, attrs={
                         "declared_value": _dump(value), "description": _str(row, "description"),
                         "count_state": _str(row, "count_state"),
                     }, attributes=dict(tier3))

        # The row IS an import event → a first-class node, with its own structural roles projected onto
        # edges (a deterministic projection of present fields, never inference). Keyed by GD/BoL number.
        # These role-edges are emitted verbatim (not re-laned): the row's role IS the edge, and the
        # generic ``trading_org`` endpoint is intentional (linking the shell to the end-user is RESOLVE's).
        import_key = _str(row, "gd_no") or _str(row, "bl_no")
        if import_key and roles:
            em.entity("contract_import_event", import_key, row_ref,
                      event_time=when, attrs={"event_subtype": "customs-import",
                                              "declared_value": _dump(value)},
                      attributes=dict(tier3))
            if "shipper" in roles:
                em.triple(import_key, "exported-by", roles["shipper"], row_ref)
            if "consignee" in roles:
                em.triple(import_key, "imported-by", roles["consignee"], row_ref)

        # A STATED onward destination → its own place (never a resolved consignee→depot edge).
        dest = _str(row, "destination_ref")
        if dest:
            dref = _resolve_doc_ref(loaded, _str(row, "destination_quote"), fallback=dest, cite_row=True)
            dloc = em.location(dest)
            em.entity("basing_site", dest, dref,
                      attrs={"site_type": "stated_destination", "coordinates": _dump(dloc)})
    return em.claims


def transform_tender_procurement(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                                 config: ConfigBundle, report_time: DateValue | None,
                                 ingest_time: DateValue | None, model_id: str,
                                 geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """A procurement tender → a contract_import_event node + the procuring unit, the referenced system
    (with every stated alias → same-as), the OEM, component line items (quantities as tier-2), and any
    explicit distinct-from ('no interoperability'). Aliases stay stated; nothing unstated is resolved."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)
    root_ref = _resolve_doc_ref(loaded, _str(filled, "source_quote"))

    tender_id = _str(filled, "tender_id")
    when = adapters.normalize_date(_str(filled, "issue_date"), report_time=report_time)
    value = _money_quantity(_str(filled, "contract_value"))
    if tender_id or value:
        em.entity("contract_import_event", tender_id or "procurement-tender", root_ref,
                  event_time=when, attrs={"event_subtype": "sustainment-tender",
                                          "contract_value": _dump(value)},
                  attributes=_prune({"tender_id": tender_id}))

    org = _obj(filled, "procuring_org")
    if org and _str(org, "name"):
        oname = _str(org, "name")
        assert oname is not None
        oref = _resolve_doc_ref(loaded, _str(org, "source_quote"), fallback=oname)
        em.entity("unit", oname, oref, attrs={"echelon": _str(org, "echelon"),
                                              "service_branch": _str(org, "service_branch")})

    system = _obj(filled, "system")
    if system and _str(system, "name"):
        sname = _str(system, "name")
        assert sname is not None
        sref = _resolve_doc_ref(loaded, _str(system, "source_quote"), fallback=sname)
        rng = adapters.normalize_quantity(_str(system, "range_text"))
        em.entity("variant", sname, sref, attrs={"family": _str(system, "family"),
                                                 "designators": _strlist(system, "designators"),
                                                 "range_km": _dump(rng),
                                                 "site_signature_geometry": _str(system, "signature_geometry")})
        for desig in _strlist(system, "designators"):
            em.triple(sname, "same-as", desig, sref)

    oem = _obj(filled, "oem")
    if oem and _str(oem, "name"):
        ename = _str(oem, "name")
        assert ename is not None
        eref = _resolve_doc_ref(loaded, _str(oem, "source_quote"), fallback=ename)
        em.entity("manufacturer", ename, eref, attrs={"role": _str(oem, "role") or "oem"})

    for m in _items(filled, "line_items"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            qty = adapters.normalize_quantity(_str(m, "quantity_text"), count_state=_str(m, "count_state"))
            em.entity("component", name, ref, attrs={
                "component_class": _str(m, "component_class"),
                "functional_role": _str(m, "functional_role"), "quantity": _dump(qty),
            })

    # A sustainment tender implies sustainment NODES — the perishable spares/stockpile posture and/or the
    # durable technical-data authority. Nodes only: the `sustained-by` rollup is SCORE's derived synthesis
    # (Phase-4 boundary), so no `sustained-by`/`design-authority-for` edge is minted here.
    stock = _obj(filled, "stockpile")
    if stock:
        sname = _str(stock, "name") or "sustainment spares/stockpile"
        if _str(stock, "name") or _str(stock, "stocked_round") or _str(stock, "magazine_depth"):
            sref = _resolve_doc_ref(loaded, _str(stock, "source_quote"), fallback=sname)
            em.entity("interceptor_stockpile", sname, sref, attrs={
                "stocked_round": _str(stock, "stocked_round"),
                "magazine_depth": _str(stock, "magazine_depth"),
                "resupply_lead_time": _str(stock, "resupply_lead_time"),
            })

    td = _obj(filled, "techdata_authority")
    if td and (_str(td, "name") or _str(td, "holds")):
        tname = _str(td, "name") or "technical-data / calibration authority"
        tref = _resolve_doc_ref(loaded, _str(td, "source_quote"), fallback=tname)
        em.entity("techdata_authority", tname, tref, attrs={
            "holds": _str(td, "holds"), "foreign_control": _str(td, "foreign_control"),
        })

    _emit_relations(em, _items(filled, "relations"), context_time=when)

    _emit_aliases(em, _items(filled, "aliases"), "same-as")
    _emit_aliases(em, _items(filled, "distinctions"), "distinct-from")
    return em.claims


def transform_social_post(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                          config: ConfigBundle, report_time: DateValue | None,
                          ingest_time: DateValue | None, model_id: str,
                          geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """Social posts → a ``source`` node per handle (status URL in tier-3), a SightingEvent per claimed
    sighting, and a negative-polarity observation for a 'nothing to report' negation. The post's stated
    uncertainty is preserved as text — INGEST extracts the claim, SCORE weighs it."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)
    for post in _items(filled, "posts"):
        handle = _str(post, "handle")
        posted = adapters.normalize_date(_str(post, "posted_at"), report_time=report_time)
        status_url = _str(post, "status_url")
        post_ref = _resolve_doc_ref(loaded, _str(post, "source_quote"), fallback=handle or status_url)
        if handle:
            em.entity("source", handle, post_ref, event_time=posted, attrs={"source_type": "social"},
                      attributes=_prune({"status_url": status_url, "posted_at": _str(post, "posted_at")}))

        for s in _items(post, "sightings"):
            participants = [p for p in (_str(s, "system"), _str(s, "unit")) if p]
            if not participants:
                continue
            sref = _resolve_doc_ref(loaded, _str(s, "source_quote"), fallback=participants[0])
            when = adapters.normalize_date(_str(s, "time_text"), report_time=report_time) or posted
            where = em.location(_str(s, "location_text"))
            em.event("SightingEvent", sref, participants=participants, time_interval=when,
                     location=where, event_time=when,
                     attrs={"activity": _str(s, "activity")},
                     attributes=_prune({"status_url": status_url}))

        # A 'nothing to report' negation is NOT emitted as an edge — see the prose transform's denial
        # note (RCA ING-1): free-text negation endpoints would mint junk `unknown` nodes, and no consumer
        # reads denials. Zero negation-derived edges / `unknown` nodes.
    return em.claims


def transform_imagery_geoint(filled: dict[str, Any], *, source_id: str, loaded: LoadedDoc,
                             config: ConfigBundle, report_time: DateValue | None,
                             ingest_time: DateValue | None, model_id: str,
                             geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """GEOINT analyst prose → a ``basing_site`` (with WGS84 coords), a SightingEvent per dated pass
    (object count as a Quantity range, count_state=fielded), the assessed system ``variant`` carrying
    the analyst's own confidence wording, and radar/components. Collection gaps are a sufficiency signal,
    NOT order-of-battle entities: SCORE's sufficiency engine emits the correctly-shaped ``gap:*`` items —
    so a ``known_gap`` node is minted **only** when a normalized ``missing_slot`` is stated, keyed by that
    slot (never the verbose sentence, which never merges — RCA ING-4). Coords come from the text.

    Plus the **relationship** half this format was missing entirely (EVAL RCA §2.3): any formation the
    report names (``units``), the dated observed-occupancy lane (``occupancy`` → ``observed-at``), and any
    relationship the report states outright (``relations``). Until these existed the relocation documents
    could emit no edge of any kind, dated or not — the beat's actual blocker."""
    em = _emitter(source_id, loaded, config, model_id, report_time, ingest_time, geocoder)

    site = _obj(filled, "site")
    site_name = _str(site, "name") if site else None
    if site and site_name:
        sref = _resolve_doc_ref(loaded, _str(site, "source_quote"), fallback=site_name)
        loc = em.location(_str(site, "location_text"))
        em.entity("basing_site", site_name, sref, attrs={
            "site_type": _str(site, "site_type"),
            "site_signature_geometry": _str(site, "signature_geometry"),
            "occupancy_state": _str(site, "occupancy_state"), "coordinates": _dump(loc),
        })

    # The passes also supply the *context* date for any occupancy statement the report leaves undated —
    # the ladder's second rung. The LATEST pass is taken: it is the collect the report's own currency
    # rests on, and it is the bound an analyst would quote for "as of when".
    latest_pass_time: DateValue | None = None
    latest_pass_bound: str | None = None
    for m in _items(filled, "observations"):
        obj_type = _str(m, "object_type")
        anchor = obj_type or site_name
        if not anchor:
            continue
        ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=obj_type)
        when = adapters.normalize_date(_str(m, "pass_date"), report_time=report_time)
        bound = canonical_iso_bounds(when)[1]
        if bound is not None and (latest_pass_bound is None or bound > latest_pass_bound):
            latest_pass_time, latest_pass_bound = when, bound
        count = adapters.normalize_quantity(_str(m, "object_count_text"),
                                            count_state=_str(m, "count_state") or "fielded")
        em.event("SightingEvent", ref, participants=[anchor], time_interval=when, event_time=when,
                 attrs={"object_type": obj_type, "count": _dump(count),
                        "dimensions": _str(m, "dimensions")})

    for m in _items(filled, "assessed_types"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("variant", name, ref, attrs={"family": _str(m, "family"),
                                                   "confidence_language": _str(m, "confidence_language"),
                                                   "site_signature_geometry": _str(m, "signature_geometry")})

    for m in _items(filled, "components"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("component", name, ref, attrs={"component_class": _str(m, "component_class"),
                                                     "functional_role": _str(m, "functional_role")})

    for m in _items(filled, "units"):
        name = _str(m, "name")
        if name:
            ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=name)
            em.entity("unit", name, ref, attrs={
                "echelon": _str(m, "echelon"), "service_branch": _str(m, "service_branch"),
                "home_garrison": _str(m, "home_garrison"),
            })

    # The OBSERVED-occupancy lane (D-P4.2 / §2.3) — what a frame can honestly state: equipment seen at a
    # place on a date. Emitted through ``relation`` like any stated fact, so the endpoint types re-lane it
    # onto ``observed-at`` (or onto ``based-at`` when the source names a *formation* rather than kit) —
    # the site end is typed here because this slot is site-anchored by construction. The claim is the
    # OBSERVED layer only; attributing it to a unit is a separate, lower-confidence derived claim
    # (:mod:`chanakya.ingest.basing`), never fused into this one.
    for m in _items(filled, "occupancy"):
        seen, where_name = _str(m, "observed"), _str(m, "site")
        if not (seen and where_name):
            continue
        occupancy = _str(m, "occupancy_state")
        quote = _str(m, "source_quote")
        ref = _resolve_doc_ref(loaded, quote, fallback=seen)
        when = adapters.normalize_date(_str(m, "observed_date"), report_time=report_time)
        if states_vacancy(occupancy):
            # A report that the site is EMPTY is an observation of **absence**, and the pipeline draws
            # every relationship claim — so emitting it on the occupancy lane would assert presence at
            # the one place the source says the kit has left. Kept as a dated, cited fact on the SITE
            # (a vacated position is among the most informative things imagery says), never as an edge —
            # the same rule this module already applies to denials and negations (RCA ING-1).
            em.entity("basing_site", where_name, ref, event_time=when or latest_pass_time, attrs={
                "occupancy_state": occupancy, "occupancy_observed_date": _str(m, "observed_date"),
            }, attributes=_prune({"_observed_absence": {"observed": seen, "source_quote": quote}}))
            continue
        em.relation(seen, "observed-at", where_name, ref, obj_type="basing_site",
                    source_quote=quote, date_text=_str(m, "observed_date"),
                    context_time=latest_pass_time,
                    attributes=_prune({"occupancy_state": occupancy}))

    _emit_relations(em, _items(filled, "relations"), context_time=latest_pass_time)

    for m in _items(filled, "collection_gaps"):
        # Key by the normalized missing_slot ONLY — never the raw sentence. No slot ⇒ no node (the gap is
        # still a sufficiency signal SCORE handles via its own gap:* items; INGEST mints no OB entity).
        slots = _strlist(m, "missing_slot")
        if not slots:
            continue
        slot_key = slots[0]
        ref = _resolve_doc_ref(loaded, _str(m, "source_quote"), fallback=slot_key)
        due = adapters.normalize_date(_str(m, "next_coverage_due"), report_time=report_time)
        em.entity("known_gap", slot_key, ref, attrs={
            "missing_slots": slots, "next_coverage_due": _dump(due),
        })
    return em.claims


#: Format → deterministic transform. Each maps filled fields to typed claims by a fixed table.
_Transform = Any  # a transform_* callable; kept loose to avoid a verbose Protocol for one call site.
TRANSFORMS: dict[str, _Transform] = {
    "prose_claim": transform_prose_claim,
    "notam_navwarning": transform_notam_navwarning,
    "customs_gd_bol": transform_customs_gd_bol,
    "tender_procurement": transform_tender_procurement,
    "social_post": transform_social_post,
    "imagery_geoint": transform_imagery_geoint,
}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The multimodal extract call — text + rendered page images, windowed by page only when oversized.
#
# A PDF now yields the whole document's text (OCR / pymupdf) **and** every page rendered to an image
# (loaders.PageImage). ``extract_document`` feeds both to ONE forced-tool call so the model reads prose,
# tables and figures together. A very large document is windowed by page (a size *guard*, not the
# default): each window is one forced-tool call, and the filled dicts are merged BEFORE the single
# transform pass — so a multi-page PDF is still one doc, deduped in one batch with one deterministic
# id-assignment (gate G2). Thresholds are INGEST tunables (module constants, the `MAX_TOKENS` precedent;
# G6 scans only the scoring packages, never `ingest/`).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

#: Max pages fed to a single multimodal call before the doc is windowed by page.
PDF_CHUNK_MAX_PAGES = 8
#: Max characters of doc text fed to a single call before windowing (a coarse token-budget proxy).
PDF_CHUNK_MAX_CHARS = 60_000


def _page_char_ranges(loaded: LoadedDoc) -> dict[int, tuple[int, int]]:
    """``page → (min_start, max_end)`` char span, from the regions that carry both a page and a span."""
    ranges: dict[int, tuple[int, int]] = {}
    for r in loaded.regions:
        if r.page is None or r.span is None:
            continue
        s, e = r.span
        lo, hi = ranges.get(r.page, (s, e))
        ranges[r.page] = (min(lo, s), max(hi, e))
    return ranges


def _page_windows(pages: list[int], page_ranges: dict[int, tuple[int, int]], *,
                  max_pages: int, max_chars: int) -> list[list[int]]:
    """Greedily pack contiguous pages into windows bounded by ``max_pages`` and ``max_chars``.

    At least one page per window (a lone page that alone exceeds ``max_chars`` still forms its own
    window, never dropped). Deterministic given the sorted ``pages`` — the window order is the page order.
    """
    windows: list[list[int]] = []
    current: list[int] = []
    current_chars = 0
    for page in pages:
        lo, hi = page_ranges.get(page, (0, 0))
        page_chars = hi - lo
        if current and (len(current) >= max_pages or current_chars + page_chars > max_chars):
            windows.append(current)
            current, current_chars = [], 0
        current.append(page)
        current_chars += page_chars
    if current:
        windows.append(current)
    return windows


def _window_text(loaded: LoadedDoc, win_pages: list[int],
                 page_ranges: dict[int, tuple[int, int]]) -> str:
    """The contiguous text substring covering ``win_pages`` (empty when the window is image-only).

    A substring of ``loaded.text`` — so a ``source_quote`` the model returns from the window is still
    found by ``loaded.text.find`` over the *full* doc in the transform (provenance stays exact, G4)."""
    spans = [page_ranges[p] for p in win_pages if p in page_ranges]
    if not spans:
        return ""
    return loaded.text[min(s for s, _ in spans):max(e for _, e in spans)]


def _merge_filled(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-window filled dicts into one (list fields concatenated; scalars/objects first-non-empty).

    The all-optional schemas are list-heavy (``sources``/``rows``/``notices``/``observations``…); a
    windowed extraction fills each window's slice, and this stitches them back into the single dict the
    transform expects — as if one call had read the whole document."""
    if len(parts) == 1:
        return parts[0]
    out: dict[str, Any] = {}
    for part in parts:
        for key, value in part.items():
            if isinstance(value, list):
                bucket = out.setdefault(key, [])
                if isinstance(bucket, list):
                    bucket.extend(value)
            elif out.get(key) in (None, "", {}, []):
                out[key] = value
    return out


def _extract_filled(loaded: LoadedDoc, *, tool_name: str, input_schema: dict[str, Any],
                    system: str, client: ExtractionClient, config: ConfigBundle) -> Any:
    """Force the extraction tool over the doc text + rendered page images — one call, or page-windowed.

    A single forced-tool call carries ``loaded.text`` plus every ``PageImage`` (the common case — the
    call count is unchanged, so scripted/offline tests replay exactly one response). Only a document that
    exceeds :data:`PDF_CHUNK_MAX_PAGES` / :data:`PDF_CHUNK_MAX_CHARS` **and** has page structure is
    windowed by page; each window is its own forced-tool call and the filled dicts are merged before the
    single transform pass. Returns the (merged) filled dict, or the raw client result when not chunking.
    """
    def _call(text: str, images: list[tuple[bytes, str]]) -> Any:
        # Pass ``images`` only when there are any, so a pure-text source calls ``extract`` with exactly
        # the old signature (a text-only client double needs no change; only image calls use the kwarg).
        if images:
            return client.extract(tool_name=tool_name, input_schema=input_schema, system=system,
                                  text=text, images=images)
        return client.extract(tool_name=tool_name, input_schema=input_schema, system=system, text=text)

    page_images = loaded.page_images
    all_images = [(pi.data, pi.media_type) for pi in page_images]
    page_ranges = _page_char_ranges(loaded)
    pages = sorted(set(page_ranges) | {pi.page for pi in page_images})
    oversized = len(pages) > PDF_CHUNK_MAX_PAGES or len(loaded.text) > PDF_CHUNK_MAX_CHARS

    if not (pages and oversized):
        return _call(loaded.text, all_images)

    parts: list[dict[str, Any]] = []
    for win_pages in _page_windows(pages, page_ranges, max_pages=PDF_CHUNK_MAX_PAGES,
                                   max_chars=PDF_CHUNK_MAX_CHARS):
        win_set = set(win_pages)
        win_images = [(pi.data, pi.media_type) for pi in page_images if pi.page in win_set]
        filled = _call(_window_text(loaded, win_pages, page_ranges), win_images)
        if isinstance(filled, dict):
            parts.append(filled)
    return _merge_filled(parts) if parts else {}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The public entry point.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _constrain_relation_enum(schema: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    """Narrow the ``relations``-field predicate enum in the tool schema to the extractor edges (D-A).

    The model may assert ONLY the ~10 relationship edges (``EdgeLaneIndex.extractor_edges()``) — never an
    identity/evidence/derived edge (``same-as``, ``corroborates`` …) through the ``relations`` slot.
    Driven from the *live* ontology at build time, not a hardcoded literal; identity still flows through
    its own dedicated fields (``aka`` / ``designators`` / ``aliases`` / ``distinctions``). A no-op when the
    ``RelationMention`` def or its ``relation`` property is absent (a schema without stated relations).
    """
    rel_def = schema.get("$defs", {}).get("RelationMention")
    if isinstance(rel_def, dict) and isinstance(rel_def.get("properties"), dict):
        props = rel_def["properties"]
        if "relation" in props and allowed:
            props["relation"] = {
                "anyOf": [{"enum": list(allowed), "type": "string"}, {"type": "null"}],
                "default": None, "title": "Relation",
            }
    return schema


def extract_document(loaded: LoadedDoc, *, source_id: str, source_type: str,
                     config: ConfigBundle, client: ExtractionClient,
                     report_time: DateValue | None = None, ingest_time: DateValue | None = None,
                     format_hint: str | None = None,
                     geocoder: adapters.Geocoder | None = None) -> list[ClaimRecord]:
    """Extract a loaded document into provenance-bearing claims — dispatch → forced tool → transform.

    Deterministic given the client's output: :func:`format_sniffer` picks the format (or ``format_hint``
    overrides), the format's all-optional pydantic schema becomes the forced tool's JSON schema, the
    client fills it (over the doc text **and** any rendered page images — one multimodal call, windowed
    by page only when the doc exceeds the size guard), and the per-format transform maps fields → typed
    claims with exact ``doc_ref``\\ s and adapter-normalized dates/locations/quantities. ``geocoder``
    (gazetteer coord-cache → Nominatim, or ``None`` = offline) is threaded to every location call-site.
    Runs entirely upstream of ``store.append`` (gate G1); the returned claims carry *provisional* ids
    (``dedup.assign_claim_ids`` reassigns the canonical ones). An empty doc, or a client that fills
    nothing, yields **zero** claims (anti-fabrication).
    """
    fmt: Format = format_hint if format_hint in SCHEMAS else format_sniffer(loaded.text, source_type)  # type: ignore[assignment]
    schema_model = SCHEMAS[fmt]
    input_schema = _constrain_relation_enum(
        schema_model.model_json_schema(), EdgeLaneIndex(config.ontology).extractor_edges()
    )
    filled = _extract_filled(
        loaded, tool_name=_TOOL_NAMES[fmt], input_schema=input_schema,
        system=_SYSTEM_PROMPTS[fmt], client=client, config=config,
    )
    if not isinstance(filled, dict):
        return []
    transform = TRANSFORMS[fmt]
    claims: list[ClaimRecord] = transform(
        filled, source_id=source_id, loaded=loaded, config=config,
        report_time=report_time, ingest_time=ingest_time, model_id=client.model_id,
        geocoder=geocoder,
    )
    # Pass 2 — in-document coreference (dormant unless configured). Additive by construction: pass 1's
    # claims are returned untouched and the cluster rides alongside them on its own lane. Living here
    # rather than in the lane means BOTH callers inherit it in lockstep — the live ingest path and the
    # keyless bundle-recording path (``seed._extract_source``) — so offline can never drift from live.
    from chanakya.ingest import coref  # local: keeps the pass off the module import graph

    return claims + coref.propose_coreference(
        claims, loaded=loaded, source_id=source_id, config=config, client=client,
        report_time=report_time, ingest_time=ingest_time,
    )
