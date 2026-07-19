"""Subject-blind VLM read of an overhead frame → a sourced observation (+ an optional corroboration
inference) — the imagery lane of INGEST (session item 6; research reference ``md/15`` §2).

An image is treated exactly like any other source: it becomes provenance-bearing
:class:`~chanakya.schemas.claim.ClaimRecord`\\ s, minted upstream of ``store.append`` (gate G1). The
imagery lane emits at most two claims, and the split is the whole design:

* **(a) a subject-blind observation** (``kind="observation"``, ``method="vlm"``) — what is *literally
  visible* in the frame: generic geometry/feature tokens, an ``occupancy_state``, an object **count as a
  ``Quantity`` range or an abstention** (never a fabricated integer — VLM counting of many small similar
  objects is unreliable), a free-text description, a caption-vs-image consistency note, and any gsd note.
  The read carries **no variant / system-identity field** ("which HQ-9?" is unaskable — G11) and **no
  coordinate field** (the VLM *never* geolocates from pixels; text coordinates are authoritative and are
  frozen upstream, passed in via ``geo``). The two-hash :func:`~chanakya.ingest.hashing.image_fingerprint`
  is frozen onto this claim's tier-3 ``attributes`` bag — the integrity floor behind every imagery claim.

* **(b) a guided-LLM signature→variant inference** (``kind="inference"``, ``premises=[observation,
  literature-fingerprint]``) — emitted **only** when a ``literature_ref`` is supplied. This is *not* a
  pixel-leap: a second, guided LLM call judges whether the subject-blind observed signature is
  *consistent with* a reference site-geometry drawn from **ingested open-source literature** (itself a
  sourced claim). The variant is carried by that reference, never guessed by this module. When consistent,
  the bridge triple ``<site, based-at, variant>`` is asserted, traceable to **both** premises — the claim
  that lets a satellite frame corroborate a textual "system at base X" report (``md/15`` §2.4). It is
  emitted at *probable* conceptually (single-pass geometry + decoy risk); this module only emits the claim
  and its premises — SCORE caps confidence.

Two deterministic gates suppress the inference *before* the corroboration call, so an evidence-sparse
frame never yields a deployment/variant assertion (the non-negotiable, mechanised here):

* ``occupancy_state`` reading as **empty-pads** → no deployment read (an empty site is not a deployment).
* a **coarse frame** — resolution flagged insufficient (e.g. the low-res Sentinel-2 beat), a non-overhead
  framing, or nothing observed to corroborate — → "insufficient evidence to identify variant".

Everything here runs at *extraction* time (G1); the module never imports a subject/anchor, the answer
key, or ontology *instance* content, and never branches on a subject (G9/G11) — it branches only on
source-shape properties (occupancy / resolution / frame) and lets the variant flow in as data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from chanakya.ingest import loaders
from chanakya.ingest.client import ExtractionClient
from chanakya.ingest.hashing import image_fingerprint
from chanakya.schemas import ConfigBundle, make_claim_id
from chanakya.schemas.claim import ClaimRecord, DocRef, EntityDescriptor, Extraction, Triple
from chanakya.schemas.values import DateValue, Location, Quantity

# ── the literature reference the corroboration is judged against ──────────────────────────────────

@dataclass(frozen=True)
class LiteratureRef:
    """A pointer to an *already-ingested* reference-fingerprint claim the corroboration matches against.

    Supplied by the caller (the lane discovers it from ingested reference literature — an Army-Technology
    / geimint / SIPRI-class text describing a site geometry). Carrying the variant here, as **data**, is
    what keeps this module subject-blind: ``imagery.py`` never names "HQ-9", it corroborates an observed
    signature against whatever reference the caller hands it (``md/15`` §2.4).
    """

    claim_id: str  # the ingested literature-fingerprint claim → the inference's second premise
    variant: str  # the variant the literature names → the object of the bridge triple
    signature_geometry: str | None = None  # the reference site-geometry the corroboration compares to
    source_id: str | None = None  # the literature's source (context only, frozen on the inference)
    predicate: str = "based-at"  # the corroboration edge type (md/15 §2.4: <site, based-at, variant>)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The subject-blind, all-optional VLM schema (generic geometry only — never a subject/variant/coord).
#
# Plain ``BaseModel`` (extra="ignore") so ``model_json_schema()`` emits no ``required`` list and no
# closed object — a permissive tool the model fills only where the frame supports it. There is
# deliberately no system/variant field and no lat/lon field: the first is unaskable of pixels (G11), the
# second is authoritative from text (the VLM never geolocates).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

class FeatureMention(BaseModel):
    """One visible feature the frame supports — a generic token, never a system label."""

    feature: str | None = None  # generic: "revetment" | "radar berm" | "access road" | "pad" | "shelter"
    shape: str | None = None  # "radial" | "circular" | "rectangular" | "linear" | …
    arrangement: str | None = None  # "ringed around a central berm" | "in a row" | …
    note: str | None = None


class ImageryObservation(BaseModel):
    """A subject-blind read of one overhead frame — *only* what is literally visible.

    No system/model/variant/country field (identification is corroboration's job, never a pixel-leap);
    no coordinate field (geolocation is authoritative from text). The count is a range or an abstention,
    never a single confident integer.
    """

    geometry_tokens: list[str] = []  # generic shape tokens: "radial-revetments", "central-radar-berm", …
    features: list[FeatureMention] = []  # optional structured feature slots
    occupancy_state: str | None = None  # the model's word: "occupied" | "empty-pads" | "garrison" | …
    object_count_min: float | None = None  # a RANGE bound — never a fabricated hard integer
    object_count_max: float | None = None
    count_abstained: bool | None = None  # the model may decline to count (many small similar objects)
    count_object: str | None = None  # what is (roughly) counted — generic ("revetments", "pads")
    description: str | None = None  # free-text description of the frame
    caption: str | None = None  # any caption / burned-in text read off the image
    caption_vs_image_consistency: str | None = None  # "consistent" | "inconsistent" | "no-caption" | note
    resolution_sufficiency: str | None = None  # "sufficient" | "insufficient" | the model's note
    gsd_note: str | None = None  # any estimated ground-sample-distance / resolution note
    frame_kind: str | None = None  # coarse framing: "overhead" | "oblique" | "ground" | "map" | …


class SignatureCorroboration(BaseModel):
    """The guided-LLM judgement: is the observed signature *consistent with* the reference geometry?

    Not a forced classification — the model may set ``consistent=False`` (or leave it unset) when the
    observed features are insufficient or do not match, which yields **no** inference.
    """

    consistent: bool | None = None
    confidence_language: str | None = None  # the model's own hedge: "consistent with" | "cannot assess"
    matched_features: list[str] = []  # which observed tokens matched the reference geometry
    decoy_risk: str | None = None  # any decoy / deception caveat the model raises (SCORE caps on it)
    rationale: str | None = None


_VLM_TOOL = "read_overhead_image"
_CORROBORATION_TOOL = "corroborate_signature"

_VLM_SYSTEM = (
    "You are an overhead-imagery reading tool for an open-source intelligence pipeline. Describe ONLY what "
    "is literally visible in this single frame. Fill the tool with generic geometry and feature tokens "
    "(shapes, arrangements, berms, revetments, pads, roads, shelters), the occupancy state, and a "
    "free-text description. Do NOT name, guess, or identify any weapon system, model, variant, launcher "
    "type, radar type, or country — that identification is made elsewhere by corroboration against "
    "literature, NEVER from these pixels. Do NOT state coordinates or a location; geolocation comes from "
    "authoritative text, never from the image. Do NOT invent a precise object count: give a min/max "
    "range, or set count_abstained=true when small similar objects cannot be reliably counted. If the "
    "resolution is insufficient to distinguish features, say so (resolution_sufficiency='insufficient') "
    "and leave the geometry empty rather than guessing."
)
_CORROBORATION_SYSTEM = (
    "You are a corroboration tool. You are given (1) a subject-blind observed signature read from one "
    "overhead frame and (2) a reference site-geometry description drawn from ingested open-source "
    "literature for a named system. Judge ONLY whether the observed signature is consistent with the "
    "reference geometry. Do not assert identity beyond consistency; raise any decoy or deception risk in "
    "decoy_risk. If the observed features are insufficient, generic, or do not match, set "
    "consistent=false. Never force a match."
)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Tolerant accessors + small pure helpers (the ``extract.py`` transform patterns, kept local).
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


def _num(v: Any) -> float | None:
    """A finite number from a scalar/string field, else ``None`` (a bool is not a count)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def _prune(attrs: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None``/empty entries so an all-optional read never freezes empty attr keys."""
    return {k: v for k, v in attrs.items() if v not in (None, "", [], {})}


def _dump(v: Any) -> Any:
    """JSON-plain form of a value object for a loose ``attrs``/``attributes`` bag (byte-stable)."""
    return v.model_dump(mode="json") if isinstance(v, BaseModel) else v


def _flag_offontology(vocab: frozenset[str], type_name: str,
                      attributes: dict[str, Any] | None) -> dict[str, Any] | None:
    """Flag a type absent from the *live* config ontology in tier-3 (extensible, never silent)."""
    if vocab and type_name not in vocab:
        attributes = dict(attributes or {})
        attributes["_offontology_type"] = type_name
    return attributes


def _doc_token(source_id: str) -> str:
    """A kebab ``[a-z0-9-]`` doc token for a readable provisional claim id (``d07_x`` → ``d07-x``)."""
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
    return token or "img"


def _img_locator(ref: DocRef) -> str:
    """A short readable locator for an image claim id — the region stem, then frame, else ``img``."""
    if ref.region is not None:
        stem = "".join(ch for ch in ref.region.casefold() if ch.isalnum())
        return stem or "img"
    if ref.frame is not None:
        return f"f{ref.frame}"
    return "img"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The read: count discipline, corroboration gates, claim builders.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _count_quantity(filled: dict[str, Any]) -> Quantity:
    """The object count as a ``Quantity`` **range or abstention** — never a single fabricated integer.

    ``value`` is *never* set: a filled ``min``/``max`` becomes an evidence-graded range; an abstention
    (or a read that gave neither bound) becomes a ``Quantity`` carrying no number at all — an honest
    "we looked but cannot count", the anti-fabrication discipline for VLM counting.
    """
    lo = _num(filled.get("object_count_min"))
    hi = _num(filled.get("object_count_max"))
    unit = _str(filled, "count_object")
    if filled.get("count_abstained") is True or (lo is None and hi is None):
        return Quantity(unit=unit, count_state="fielded", approx=True)  # abstention: no numeric value
    return Quantity(min=lo, max=hi, unit=unit, count_state="fielded", approx=True)


# Framings on which a deployment/variant read is *possible* at all — an oblique/ground/map frame cannot
# carry an overhead deployment signature, so a stated non-overhead framing suppresses the inference.
_OVERHEAD_FRAMES = frozenset({"overhead", "satellite", "nadir", "near-nadir", "top-down", "vertical"})


def _corroboration_eligible(filled: dict[str, Any], *, geometry_tokens: list[str],
                            features: list[dict[str, Any]]) -> bool:
    """Deterministic pre-gate: may this frame carry a deployment/variant read *at all*? (md/15 §2.2/§2.3)

    ``False`` — so **no** inference, "insufficient evidence to identify variant" — when there is nothing
    observed to corroborate, the site reads as **empty-pads** (an empty site is not a deployment), the
    resolution is flagged **insufficient** (the low-res beat), or the framing is not overhead.
    """
    if not geometry_tokens and not features:
        return False  # nothing observed to corroborate against literature
    occ = (_str(filled, "occupancy_state") or "").lower()
    if "empty" in occ:  # "empty-pads": an empty site is not a deployment
        return False
    if (_str(filled, "resolution_sufficiency") or "").lower().startswith("insuff"):
        return False  # resolution floor (e.g. the deliberate Sentinel-2 10 m beat)
    frame = (_str(filled, "frame_kind") or "").lower()
    return not (frame and frame not in _OVERHEAD_FRAMES)


def _corroboration_prompt(*, geometry_tokens: list[str], features: list[dict[str, Any]],
                          description: str | None, occupancy: str | None,
                          literature: LiteratureRef) -> str:
    """The guided-LLM corroboration turn — the observed signature beside the reference geometry."""
    observed = "; ".join(geometry_tokens) or (description or "(no distinct geometry)")
    feat = "; ".join(
        " ".join(p for p in (_str(f, "shape"), _str(f, "feature"), _str(f, "arrangement")) if p)
        for f in features
    ) or "(none)"
    return (
        "OBSERVED SIGNATURE (subject-blind, from one overhead frame):\n"
        f"- geometry: {observed}\n"
        f"- features: {feat}\n"
        f"- occupancy: {occupancy or 'unstated'}\n"
        f"- description: {description or '(none)'}\n\n"
        "REFERENCE SITE-GEOMETRY (from ingested open-source literature):\n"
        f"- system: {literature.variant}\n"
        f"- reference geometry: {literature.signature_geometry or '(not provided)'}\n\n"
        "Judge only whether the observed signature is consistent with the reference geometry."
    )


def read_image_document(image: bytes, *, file: str, source_id: str, config: ConfigBundle,
                        client: ExtractionClient, report_time: DateValue | None = None,
                        ingest_time: DateValue | None = None, geo: Location | None = None,
                        literature_ref: LiteratureRef | None = None) -> list[ClaimRecord]:
    """Read one image into a subject-blind observation (+ an optional corroboration inference).

    The VLM read is forced through the single :class:`ImageryObservation` tool (subject-blind, no
    coordinate field); the two-hash fingerprint is frozen onto the observation's tier-3 ``attributes``.
    ``geo`` (authoritative text coordinates, resolved upstream) is frozen onto the observation as-is —
    the VLM never contributes a coordinate. When ``literature_ref`` is supplied **and** the frame clears
    the deterministic gates (:func:`_corroboration_eligible`), a second guided-LLM call judges
    signature↔literature consistency; a *consistent* judgement yields the bridge inference
    ``<site, based-at, variant>`` with ``premises=[observation, literature-fingerprint]``. Runs entirely
    upstream of ``store.append`` (G1); claims carry *provisional* ids (see the module note on premise
    remapping at id reassignment).

    An empty/invalid VLM read still yields the observation (the fingerprint + "read on date D" is itself a
    sourced fact, and an empty read is an insufficient-evidence signal, not silence) — but never an
    inference.
    """
    loaded = loaders.load_image(image, file)
    media_type = loaded.media_type
    img_ref = loaded.regions[0].to_doc_ref() if loaded.regions else DocRef(file=file, region="full")

    raw = client.read_image(tool_name=_VLM_TOOL, input_schema=ImageryObservation.model_json_schema(),
                            system=_VLM_SYSTEM, image=image, media_type=media_type)
    filled: dict[str, Any] = raw if isinstance(raw, dict) else {}

    node_vocab = frozenset(t.name for t in config.ontology.node_types)
    edge_vocab = frozenset(t.name for t in config.ontology.edge_types)

    token = _doc_token(source_id)
    locator = _img_locator(img_ref)
    obs_id = make_claim_id(token, locator, index=1)
    site_anchor = f"imagery-site:{source_id}"

    geometry_tokens = _strlist(filled, "geometry_tokens")
    features = [_prune(f) for f in _items(filled, "features")]
    features = [f for f in features if f]
    occupancy = _str(filled, "occupancy_state")
    description = _str(filled, "description")
    count = _count_quantity(filled)

    attrs = _prune({
        "site_type": "observed-imagery-site",
        "occupancy_state": occupancy,
        "geometry_tokens": geometry_tokens,
        "observed_features": features,
        "site_signature_geometry": description or ("; ".join(geometry_tokens) or None),
        "count": _dump(count),
        "gsd_note": _str(filled, "gsd_note"),
        "resolution_sufficiency": _str(filled, "resolution_sufficiency"),
        "frame_kind": _str(filled, "frame_kind"),
        "caption_vs_image_consistency": _str(filled, "caption_vs_image_consistency"),
        "description": description,
        "coordinates": _dump(geo) if geo is not None else None,
    })
    attributes: dict[str, Any] | None = _prune({
        "image_fingerprint": image_fingerprint(image).model_dump(mode="json"),
        "media_type": media_type,
        "caption_text": _str(filled, "caption"),
    })
    attributes = _flag_offontology(node_vocab, "basing_site", attributes)

    observation = ClaimRecord(
        claim_id=obs_id, source_id=source_id, doc_ref=img_ref,
        kind="observation", polarity="positive", asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name=site_anchor, attrs=attrs),
        report_time=report_time, ingest_time=ingest_time,
        extraction=Extraction(method="vlm", version=client.model_id, model_conf=1.0),
        attributes=attributes or None,
    )
    claims: list[ClaimRecord] = [observation]

    # (b) the guided-LLM signature→variant corroboration — only with a reference AND an eligible frame.
    if literature_ref is not None and _corroboration_eligible(
        filled, geometry_tokens=geometry_tokens, features=features
    ):
        corr = client.extract(
            tool_name=_CORROBORATION_TOOL, input_schema=SignatureCorroboration.model_json_schema(),
            system=_CORROBORATION_SYSTEM,
            text=_corroboration_prompt(geometry_tokens=geometry_tokens, features=features,
                                       description=description, occupancy=occupancy,
                                       literature=literature_ref),
        )
        if isinstance(corr, dict) and corr.get("consistent") is True:
            inf_attributes: dict[str, Any] | None = _prune({
                "confidence_language": _str(corr, "confidence_language"),
                "matched_features": _strlist(corr, "matched_features"),
                "decoy_risk": _str(corr, "decoy_risk"),
                "rationale": _str(corr, "rationale"),
                "corroborated_against": literature_ref.claim_id,
                "reference_source_id": literature_ref.source_id,
            })
            inf_attributes = _flag_offontology(edge_vocab, literature_ref.predicate, inf_attributes)
            claims.append(ClaimRecord(
                claim_id=make_claim_id(token, locator, index=2), source_id=source_id, doc_ref=img_ref,
                kind="inference", polarity="positive", asserts="relationship",
                payload=Triple(subject=site_anchor, predicate=literature_ref.predicate,
                               object=literature_ref.variant),
                report_time=report_time, ingest_time=ingest_time,
                premises=[obs_id, literature_ref.claim_id],
                extraction=Extraction(method="llm", version=client.model_id, model_conf=1.0),
                attributes=inf_attributes or None,
            ))
    return claims
