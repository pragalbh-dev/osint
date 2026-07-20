"""Imagery-lane tests — the subject-blind VLM observation + the guided-LLM corroboration inference.

Everything here is **offline + deterministic** (gate G10): a :class:`ScriptedExtractionClient` replays a
canned VLM-observation dict (and, when a corroboration is expected, a second canned judgement dict — the
client shares one FIFO queue across ``read_image`` then ``extract``), and a tiny PIL-generated PNG feeds
the real :func:`~chanakya.ingest.hashing.image_fingerprint`. The graded beats are asserted directly:

* **subject-blind** — the observation carries NO variant / system / country token anywhere (G11).
* **integrity frozen** — the two-hash fingerprint is frozen on the observation's tier-3 ``attributes``.
* **count discipline** — the count is a ``Quantity`` range or an abstention, never a hard integer.
* **evidence-sparse suppression** — ``empty-pads`` (and a coarse/low-res frame) yields NO deployment /
  variant inference, even with a ``literature_ref``.
* **the bridge inference** — with a ``literature_ref`` and an eligible frame, the corroboration inference
  carries ``premises=[observation_id, literature_fingerprint_id]`` and the variant as its object.
"""

from __future__ import annotations

import io
from typing import Any

from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.imagery import LiteratureRef, read_image_document
from chanakya.schemas.claim import ClaimRecord, EntityDescriptor, Triple
from chanakya.schemas.config_models import ConfigBundle
from chanakya.schemas.values import Location

# ── fixtures ─────────────────────────────────────────────────────────────────────────────────────

_VARIANT_TOKENS = ("hq-9", "hq9", "s-400", "fd-2000", "ht-233", "pakistan", "china")


def _png(color: tuple[int, int, int] = (40, 90, 160), size: int = 32) -> bytes:
    """A tiny deterministic PNG (real bytes, so the fingerprint's sha256/PDQ actually compute)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def _client(*filled: dict[str, Any]) -> ScriptedExtractionClient:
    return ScriptedExtractionClient(list(filled))


def _occupied_read() -> dict[str, Any]:
    """A rich, corroboration-eligible VLM read (occupied, overhead, features present)."""
    return {
        "geometry_tokens": ["radial-revetments", "central-radar-berm", "circular-access-road"],
        "features": [{"feature": "revetment", "shape": "radial",
                      "arrangement": "ringed around a central berm"}],
        "occupancy_state": "occupied",
        "object_count_min": 4,
        "object_count_max": 6,
        "count_object": "revetments",
        "description": "A prepared site: lobed revetments ringing a central radar berm, outer berm beyond.",
        "caption": "site overview",
        "caption_vs_image_consistency": "consistent",
        "resolution_sufficiency": "sufficient",
        "gsd_note": "~0.5 m",
        "frame_kind": "overhead",
    }


def _obs(claims: list[ClaimRecord]) -> ClaimRecord:
    return next(c for c in claims if c.kind == "observation")


def _inferences(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    return [c for c in claims if c.kind == "inference"]


def _text_blob(claim: ClaimRecord) -> str:
    """Every stated string on a claim's payload + attrs + tier-3 bag, lower-cased (for token scans)."""
    parts: list[str] = []
    payload = claim.payload
    if isinstance(payload, EntityDescriptor):
        parts.append(payload.entity_type)
        parts.append(payload.name)
        parts.append(str(payload.attrs))
    elif isinstance(payload, Triple):
        parts.extend([payload.subject, payload.predicate, payload.object])
    if claim.attributes:
        parts.append(str(claim.attributes))
    return " ".join(parts).lower()


# ── the observation: subject-blind, integrity frozen, count-as-range ──────────────────────────────

def test_observation_is_subject_blind_no_variant_token() -> None:
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read()))
    obs = _obs(claims)
    assert obs.extraction.method == "vlm"
    assert isinstance(obs.payload, EntityDescriptor)
    assert obs.payload.entity_type == "basing_site"  # a generic node TYPE, never a subject
    # NO variant / system / country token anywhere on the observation (G11).
    blob = _text_blob(obs)
    for token in _VARIANT_TOKENS:
        assert token not in blob, f"observation leaked a subject token: {token!r}"
    # …and the read carried no coordinate field (the VLM never geolocates from pixels).
    assert "wgs84_lat" not in str(obs.payload.attrs)


def test_fingerprint_frozen_on_observation_attributes() -> None:
    image = _png()
    claims = read_image_document(image, file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read()))
    obs = _obs(claims)
    assert obs.attributes is not None
    fp = obs.attributes.get("image_fingerprint")
    assert isinstance(fp, dict)
    # the frozen sha256 is the byte-stable digest of the exact bytes we ingested.
    import hashlib
    assert fp["sha256"] == hashlib.sha256(image).hexdigest()


def test_count_is_a_range_never_a_fabricated_integer() -> None:
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read()))
    obs = _obs(claims)
    assert isinstance(obs.payload, EntityDescriptor)
    count = obs.payload.attrs["count"]
    assert count["value"] is None  # never a single hard integer
    assert count["min"] == 4 and count["max"] == 6  # an evidence-graded range
    assert count["count_state"] == "fielded"


def test_count_abstention_carries_no_number() -> None:
    read = {**_occupied_read(), "count_abstained": True,
            "object_count_min": None, "object_count_max": None}
    claims = read_image_document(_png(), file="d10.png", source_id="d10", config=ConfigBundle(),
                                 client=_client(read))
    obs = _obs(claims)
    assert isinstance(obs.payload, EntityDescriptor)
    count = obs.payload.attrs["count"]
    assert count["value"] is None and count["min"] is None and count["max"] is None


def test_authoritative_geo_frozen_from_text_not_pixels() -> None:
    geo = Location(raw="24.9012 N, 67.2034 E", surface_format="DD",
                   wgs84_lat=24.9012, wgs84_lon=67.2034, precision_class="site")
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read()), geo=geo)
    obs = _obs(claims)
    assert isinstance(obs.payload, EntityDescriptor)
    coords = obs.payload.attrs["coordinates"]
    assert coords["wgs84_lat"] == 24.9012 and coords["wgs84_lon"] == 67.2034


# ── evidence-sparse suppression: empty-pads / coarse frame → NO deployment/variant claim ───────────

def test_empty_pads_yields_no_deployment_inference() -> None:
    read = {**_occupied_read(), "occupancy_state": "empty-pads"}
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9",
                        signature_geometry="radial revetments around a central HT-233 berm")
    # Only ONE queued dict: the corroboration LLM must NOT be called (empty-pads is pre-gated out).
    claims = read_image_document(_png(), file="d17.png", source_id="d17", config=ConfigBundle(),
                                 client=_client(read), literature_ref=lit)
    assert _inferences(claims) == []
    obs = _obs(claims)  # the observation still exists (a citable "empty-pads" read)
    assert isinstance(obs.payload, EntityDescriptor)
    assert obs.payload.attrs["occupancy_state"] == "empty-pads"


def test_insufficient_resolution_yields_no_inference() -> None:
    read = {**_occupied_read(), "resolution_sufficiency": "insufficient"}
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9")
    claims = read_image_document(_png(), file="d18.png", source_id="d18", config=ConfigBundle(),
                                 client=_client(read), literature_ref=lit)
    assert _inferences(claims) == []


def test_no_literature_ref_means_observation_only() -> None:
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read()))
    assert len(claims) == 1 and claims[0].kind == "observation"


# ── the bridge inference: premises=[observation, literature-fingerprint] ───────────────────────────

def test_corroboration_inference_carries_both_premises() -> None:
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9", source_id="ref01",
                        signature_geometry="radial revetments around a central HT-233 berm")
    corroboration = {"consistent": True, "confidence_language": "consistent with",
                     "matched_features": ["radial-revetments", "central-radar-berm"],
                     "decoy_risk": "single-pass geometry only", "rationale": "matches the HQ-9 site ring"}
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read(), corroboration), literature_ref=lit)
    infs = _inferences(claims)
    assert len(infs) == 1
    inf = infs[0]
    obs = _obs(claims)
    # premises = [the observation just emitted, the ingested literature fingerprint].
    assert inf.premises == [obs.claim_id, "ref01-l1"]
    assert isinstance(inf.payload, Triple)
    # The OBSERVED-occupancy lane, equipment -> site: a pixel read can support "this kit was seen here",
    # never "this formation is based here" (`based-at`, unit -> basing_site, DERIVED elsewhere at its own
    # lower confidence). The bridge used to assert <site, based-at, variant> — off-lane in BOTH type and
    # direction against the ontology (EVAL RCA §2.3 / D-P4.2).
    assert inf.payload.predicate == "observed-at"
    assert inf.payload.subject == "HQ-9"  # the variant flows from the literature reference, not the VLM
    assert inf.payload.object == obs.payload.name  # the same site anchor the observation created
    assert inf.attributes is not None
    assert inf.attributes.get("corroborated_against") == "ref01-l1"


def test_inconsistent_corroboration_emits_no_inference() -> None:
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9")
    corroboration = {"consistent": False, "rationale": "generic revetments, no radar ring"}
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read(), corroboration), literature_ref=lit)
    assert _inferences(claims) == []


def test_offontology_edge_flagged_when_predicate_absent_from_config() -> None:
    """A corroboration edge type not in the live ontology is emitted, flagged in tier-3 (extensible)."""
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9", predicate="consistent-with")
    partial = ConfigBundle.model_validate({"ontology": {"edge_types": [{"name": "based-at"}]}})
    corroboration = {"consistent": True}
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=partial,
                                 client=_client(_occupied_read(), corroboration), literature_ref=lit)
    inf = _inferences(claims)[0]
    assert inf.attributes is not None
    assert inf.attributes.get("_offontology_type") == "consistent-with"


# ── every emitted claim is a valid, provenance-bearing ClaimRecord ────────────────────────────────

def test_all_claims_valid_and_cite_the_image() -> None:
    lit = LiteratureRef(claim_id="ref01-l1", variant="HQ-9")
    claims = read_image_document(_png(), file="d07.png", source_id="d07", config=ConfigBundle(),
                                 client=_client(_occupied_read(), {"consistent": True}),
                                 literature_ref=lit)
    assert len(claims) == 2
    for c in claims:
        assert isinstance(c, ClaimRecord)
        for ref in c.doc_refs():
            assert ref.file == "d07.png"
            assert ref.region == "full"  # one-click traceable back to the image (G4)
        assert c.extraction.version == "scripted"
