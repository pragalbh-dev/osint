"""Additive extraction-schema fields (RESOLUTION-REDESIGN data pass): ``VariantMention.operator_branch``
and ``UnitMention.alert_posture``.

Both mirror the existing ``signature_geometry`` precedent — an optional, only-when-stated Mention field
mapped verbatim into the emitted entity's tier-2 ``attrs`` dict at every site that emits the entity.
``operator_branch`` is the (already-declared-critical, previously unwired) D5 wall attribute on
``variant``; ``alert_posture`` is a new *supporting + perishable* attribute on ``unit`` — a transient
readiness/alert status, never a durable identity trait.

Corpus-independent by construction: every document here is synthetic text built in the test itself
(``loaders.load_document`` over an invented string), never a corpus file — these tests pin the MECHANISM
(a stated fact reaches the resolver's ``attrs`` dict), not any corpus-specific number or entity.
"""

from __future__ import annotations

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, loaders
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.extract import extract_document
from chanakya.schemas.claim import ClaimRecord, EntityDescriptor
from chanakya.schemas.config_models import ConfigBundle


@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """No adapter may hit Nominatim (none of these fixtures state a location, but stay consistent)."""
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture(scope="module")
def config() -> ConfigBundle:
    """The real ontology vocabulary, seeded from ``config/ontology.yaml`` (offline yaml read)."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _entities(claims: list[ClaimRecord]) -> list[EntityDescriptor]:
    return [c.payload for c in claims if isinstance(c.payload, EntityDescriptor)]


def _client(filled: dict) -> ScriptedExtractionClient:
    return ScriptedExtractionClient([filled])


# ── (a) VariantMention.operator_branch -> variant EntityDescriptor.attrs["operator_branch"] ───────
#
# Exercised at all three variant-emission sites this field was added to: prose (``variants``), tender
# (``system``), and imagery (``assessed_types``) — ``format_hint`` bypasses the raw-text sniffer so the
# synthetic text never needs to carry format-detection cues.

_VARIANT_CASES = [
    pytest.param(
        "prose_claim",
        {"variants": [{"name": "HQ-9P", "operator_branch": "Pakistan Air Force",
                       "source_quote": "the HQ-9P is operated by the Pakistan Air Force"}]},
        "Analytic note: the HQ-9P is operated by the Pakistan Air Force at an undisclosed site.",
        "curated-register",
        id="prose",
    ),
    pytest.param(
        "tender_procurement",
        {"system": {"name": "HQ-9P", "operator_branch": "Pakistan Air Force",
                    "source_quote": "HQ-9P system, operated by the Pakistan Air Force"}},
        "Tender skeleton: HQ-9P system, operated by the Pakistan Air Force, sustainment lot.",
        "customs-tender",
        id="tender",
    ),
    pytest.param(
        "imagery_geoint",
        {"assessed_types": [{"name": "HQ-9P", "operator_branch": "Pakistan Air Force",
                             "source_quote": "consistent with the PAF-operated HQ-9P"}]},
        "GEOINT note: revetments consistent with the PAF-operated HQ-9P.",
        "curated-register",
        id="imagery",
    ),
]


@pytest.mark.parametrize("fmt,filled,text,source_type", _VARIANT_CASES)
def test_operator_branch_reaches_variant_attrs(
    config: ConfigBundle, fmt: str, filled: dict, text: str, source_type: str,
) -> None:
    loaded = loaders.load_document(text, file=f"synthetic_{fmt}.txt")
    claims = extract_document(loaded, source_id="synthetic", source_type=source_type,
                              config=config, client=_client(filled), format_hint=fmt)
    variants = [e for e in _entities(claims) if e.entity_type == "variant"]
    assert variants, f"no variant entity emitted for format {fmt}"
    assert variants[0].attrs.get("operator_branch") == "Pakistan Air Force"


# ── (b) UnitMention.alert_posture -> unit EntityDescriptor.attrs["alert_posture"] ──────────────────
#
# Exercised at both unit-emission sites: prose (``units``) and tender (``procuring_org``); imagery's
# ``units`` list shares the same ``UnitMention`` class and the same attrs-mapping line, so it is covered
# by construction (imagery is exercised for the variant side above).

_UNIT_CASES = [
    pytest.param(
        "prose_claim",
        {"units": [{"name": "477 Air Defence Squadron", "alert_posture": "assessed non-operational",
                    "source_quote": "477 Air Defence Squadron is assessed non-operational"}]},
        "Analytic note: 477 Air Defence Squadron is assessed non-operational this quarter.",
        "curated-register",
        "assessed non-operational",
        id="prose",
    ),
    pytest.param(
        "tender_procurement",
        {"procuring_org": {"name": "477 Air Defence Squadron",
                           "alert_posture": "routine readiness during Exercise Falcon",
                           "source_quote": "477 Air Defence Squadron, routine readiness during Exercise Falcon"}},
        "Tender skeleton: procuring org 477 Air Defence Squadron, routine readiness during Exercise Falcon.",
        "customs-tender",
        "routine readiness during Exercise Falcon",
        id="tender",
    ),
    pytest.param(
        "imagery_geoint",
        {"units": [{"name": "477 Air Defence Squadron", "alert_posture": "on heightened alert",
                    "source_quote": "477 Air Defence Squadron on heightened alert"}]},
        "GEOINT note: 477 Air Defence Squadron on heightened alert at the pad.",
        "curated-register",
        "on heightened alert",
        id="imagery",
    ),
]


@pytest.mark.parametrize("fmt,filled,text,source_type,expected", _UNIT_CASES)
def test_alert_posture_reaches_unit_attrs(
    config: ConfigBundle, fmt: str, filled: dict, text: str, source_type: str, expected: str,
) -> None:
    loaded = loaders.load_document(text, file=f"synthetic_{fmt}.txt")
    claims = extract_document(loaded, source_id="synthetic", source_type=source_type,
                              config=config, client=_client(filled), format_hint=fmt)
    units = [e for e in _entities(claims) if e.entity_type == "unit"]
    assert units, f"no unit entity emitted for format {fmt}"
    assert units[0].attrs.get("alert_posture") == expected


# ── (c) all-optional discipline: leaving both fields unstated emits neither key ────────────────────

def test_unstated_fields_never_fabricated(config: ConfigBundle) -> None:
    """A source that states a unit/variant name but NOT the new fields must never invent a value."""
    text = "Analytic note: 477 Air Defence Squadron operates the HQ-9P."
    filled = {
        "units": [{"name": "477 Air Defence Squadron", "source_quote": "477 Air Defence Squadron"}],
        "variants": [{"name": "HQ-9P", "source_quote": "HQ-9P"}],
    }
    loaded = loaders.load_document(text, file="synthetic_unstated.txt")
    claims = extract_document(loaded, source_id="synthetic", source_type="curated-register",
                              config=config, client=_client(filled), format_hint="prose_claim")
    entities = _entities(claims)
    unit = next(e for e in entities if e.entity_type == "unit")
    variant = next(e for e in entities if e.entity_type == "variant")
    assert "alert_posture" not in unit.attrs
    assert "operator_branch" not in variant.attrs
