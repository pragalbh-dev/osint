"""Dating the frame from its sibling write-up (EVAL RCA D-P4.6 step 4 / build-order item 1).

A GEOINT source is one document with two modalities: a ``.txt`` that states *when* the pass was flown and
a ``.png`` that shows what it saw. The VLM cannot date a frame any more than it can geolocate one, and
``read_image_document`` stamped only ``report_time``/``ingest_time`` — so the imagery observation, the
very claim a derived basing fact inherits its valid time from, was **undated**. Everything downstream that
orders or ages basing then had nothing to order by, and adding inheritance to the derivation first would
have been a no-op.

:func:`~chanakya.ingest.imagery.inherit_observation_time` closes that, on **both** the live lane and the
frozen recorder (KEYLESS ≡ LIVE). It only ever fills a hole, and only from the document's own text —
never from the publication date, never invented.
"""

from __future__ import annotations

import io
from typing import Any

from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.imagery import inherit_observation_time, read_image_document
from chanakya.schemas.claim import ClaimRecord, DocRef, EntityDescriptor, Extraction
from chanakya.schemas.config_models import ConfigBundle
from chanakya.schemas.values import ExactDate, LabelDate, canonical_iso_bounds


def _png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (40, 90, 160)).save(buf, format="PNG")
    return buf.getvalue()


def _text_claim(cid: str, when: Any) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid, source_id="d17_rawalpindi_2021", doc_ref=DocRef(file="d17.txt", line=3),
        kind="observation", polarity="positive", asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name="PAF Base Nur Khan"),
        event_time=when, extraction=Extraction(method="llm", version="scripted"),
    )


def _vlm_claims(**kw: Any) -> list[ClaimRecord]:
    return read_image_document(
        _png(), file="d17.png", source_id="d17_rawalpindi_2021", config=ConfigBundle(),
        client=ScriptedExtractionClient([{"occupancy_state": "occupied", "frame_kind": "overhead"}]),
        **kw,
    )


def test_vlm_observation_accepts_an_event_time() -> None:
    when = ExactDate(iso_date="2021-10-09", raw="09 OCT 2021")
    obs = _vlm_claims(event_time=when)[0]
    assert obs.event_time == when


def test_vlm_read_alone_is_undated() -> None:
    """The frame states no date — the lane must not manufacture one from the clock or the report."""
    assert _vlm_claims()[0].event_time is None


def test_frame_inherits_the_sibling_texts_latest_observed_date() -> None:
    claims = [
        _text_claim("t1", ExactDate(iso_date="2021-08-03", raw="03 AUG 2021")),
        _text_claim("t2", ExactDate(iso_date="2021-10-09", raw="09 OCT 2021")),
        *_vlm_claims(),
    ]
    out = inherit_observation_time(claims)
    vlm = next(c for c in out if c.extraction.method == "vlm")
    assert canonical_iso_bounds(vlm.event_time) == ("2021-10-09", "2021-10-09")
    assert (vlm.attributes or {})["_event_time_rung"] == "sibling-document-observation"


def test_inheritance_never_overwrites_a_date_the_frame_already_carries() -> None:
    own = ExactDate(iso_date="2025-03-27", raw="27 March")
    claims = [_text_claim("t1", ExactDate(iso_date="2021-08-03", raw="")), *_vlm_claims(event_time=own)]
    out = inherit_observation_time(claims)
    assert next(c for c in out if c.extraction.method == "vlm").event_time == own


def test_no_dated_text_leaves_the_frame_undated() -> None:
    claims = [_text_claim("t1", None), *_vlm_claims()]
    out = inherit_observation_time(claims)
    assert next(c for c in out if c.extraction.method == "vlm").event_time is None


def test_text_claims_are_left_untouched() -> None:
    text = _text_claim("t1", LabelDate(granularity="year", year=2025, raw="2025"))
    out = inherit_observation_time([text, *_vlm_claims()])
    assert out[0] == text


def test_inheritance_is_deterministic() -> None:
    claims = [
        _text_claim("t2", ExactDate(iso_date="2021-10-09", raw="")),
        _text_claim("t1", ExactDate(iso_date="2021-10-09", raw="")),
        *_vlm_claims(),
    ]
    a = inherit_observation_time(claims)
    b = inherit_observation_time(list(reversed(claims)))
    got = [next(c for c in x if c.extraction.method == "vlm").event_time for x in (a, b)]
    assert got[0] == got[1]
