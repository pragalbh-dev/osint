"""Regression tests for the adversarial-review fixes (the graded/guardrail-critical ones).

* **event-type inference** — a stated supplier→recipient transfer whose ``event_kind`` the model left
  empty must be typed ``TransferEvent``, NOT silently defaulted to ``SightingEvent`` (which would
  mis-type the supply-chain edges the use case is graded on).
* **imagery empty-site guardrail (allowlist)** — a variant corroboration inference fires ONLY on an
  affirmatively-occupied site; any other occupancy word ("vacant" / "unoccupied" / "dormant" / blank)
  yields no deployment/variant read (an empty site is not a deployment).
"""

from __future__ import annotations

import io
from typing import Any

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.extract import extract_document
from chanakya.ingest.imagery import LiteratureRef, read_image_document
from chanakya.ingest.loaders import load_document
from chanakya.schemas import ConfigBundle, EventDescriptor


def _config() -> ConfigBundle:
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (40, 90, 160)).save(buf, format="PNG")
    return buf.getvalue()


# ── event-type inference (fix #1) ────────────────────────────────────────────────────────────────

def test_unstated_event_kind_with_supplier_recipient_is_a_transfer_not_a_sighting() -> None:
    text = "China transferred 6 HQ-9 batteries to Pakistan in 2021.\n"
    loaded = load_document(text, file="d01.txt")
    # a realistic partial fill: the model gives supplier/recipient/system but omits the optional event_kind
    fill: dict[str, Any] = {"events": [
        {"system": "HQ-9", "supplier": "China", "recipient": "Pakistan", "quantity_text": "6 batteries",
         "source_quote": "China transferred 6 HQ-9 batteries to Pakistan"}
    ]}
    client = ScriptedExtractionClient([fill])
    claims = extract_document(loaded, source_id="d01", source_type="trade-media",
                              config=_config(), client=client)
    events = [c.payload for c in claims if isinstance(c.payload, EventDescriptor)]
    assert events, "a stated transfer must emit an event"
    assert events[0].event_type == "TransferEvent"  # inferred from supplier+recipient, NOT SightingEvent


# ── imagery empty-site guardrail: allowlist, not a bare "empty" denylist (fix #6) ──────────────────

_LIT = LiteratureRef(claim_id="d03-l4", variant="HQ-9", signature_geometry="radial revetments")


def _obs_fill(occupancy: str) -> dict[str, Any]:
    return {
        "geometry_tokens": ["radial-revetments", "central-radar-berm"],
        "occupancy_state": occupancy,
        "object_count_min": 4, "object_count_max": 6, "count_object": "revetments",
        "description": "revetments ringing a central berm", "resolution_sufficiency": "sufficient",
        "frame_kind": "overhead",
    }


def _inferences(claims: list[Any]) -> list[Any]:
    return [c for c in claims if c.kind == "inference"]


def test_vacant_site_yields_no_variant_inference() -> None:
    # "vacant" is emptiness worded so it slips a bare `"empty" in occ` denylist — the allowlist stops it.
    client = ScriptedExtractionClient([_obs_fill("vacant")])
    claims = read_image_document(_png(), file="d.png", source_id="d07", config=_config(),
                                 client=client, literature_ref=_LIT)
    assert claims and all(c.kind == "observation" for c in claims)  # the observation still lands
    assert not _inferences(claims)  # but NO deployment/variant inference on a not-occupied site


def test_occupied_site_permits_the_corroboration_inference() -> None:
    # control: an affirmatively-occupied site + a consistent corroboration → the inference IS emitted.
    client = ScriptedExtractionClient([_obs_fill("occupied"), {"consistent": True}])
    claims = read_image_document(_png(), file="d.png", source_id="d07", config=_config(),
                                 client=client, literature_ref=_LIT)
    infs = _inferences(claims)
    assert len(infs) == 1
    assert _LIT.claim_id in infs[0].premises  # premised on the ingested literature fingerprint
