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


# ── (d) the SCHEMA-ALIGNMENT fields: the extractor writes the key the identity scoring reads ────────
#
# The defect these close is not a missing mechanism but a missing *name*. `attribute_roles` declared
# `unit.designator` and `component.model_designation` identity-bearing, and no extraction slot existed for
# either — so both were stated on zero extracted entities, and every live unit and component reached scoring
# with nothing individuating on it. `variant.designators` is the mirror image: the extractor had been filling
# it on 40 claims while the declaration pointed at `export_designator`, a key the live path never writes.
#
# These assert the KEY, which is the whole point — a test that checked only "the value survives" would have
# passed throughout the period the two sides were writing and reading different names.

_ALIGNMENT_CASES = [
    pytest.param(
        "prose_claim",
        {"units": [{"name": "22 Air Defence Regiment", "designator": "22 AD Regt",
                    "source_quote": "22 Air Defence Regiment (22 AD Regt)"}]},
        "Analytic note: 22 Air Defence Regiment (22 AD Regt) held its annual firing.",
        "unit", "designator", "22 AD Regt", id="unit-designator-prose",
    ),
    pytest.param(
        "tender_procurement",
        {"procuring_org": {"name": "22 Air Defence Regiment", "designator": "22 AD Regt",
                           "source_quote": "procuring unit 22 Air Defence Regiment (22 AD Regt)"}},
        "Tender skeleton: procuring unit 22 Air Defence Regiment (22 AD Regt), sustainment lot.",
        "unit", "designator", "22 AD Regt", id="unit-designator-tender",
    ),
    pytest.param(
        "imagery_geoint",
        {"units": [{"name": "22 Air Defence Regiment", "designator": "22 AD Regt",
                    "source_quote": "22 Air Defence Regiment (22 AD Regt)"}]},
        "GEOINT note: 22 Air Defence Regiment (22 AD Regt) is named in the caption.",
        "unit", "designator", "22 AD Regt", id="unit-designator-imagery",
    ),
    pytest.param(
        "prose_claim",
        {"components": [{"name": "engagement radar", "model_designation": "HT-233",
                         "source_quote": "the HT-233 engagement radar"}]},
        "Analytic note: the HT-233 engagement radar was displayed.",
        "component", "model_designation", "HT-233", id="component-model-prose",
    ),
    pytest.param(
        "tender_procurement",
        {"line_items": [{"name": "engagement radar", "model_designation": "HT-233",
                         "source_quote": "line item: HT-233 engagement radar"}]},
        "Tender skeleton: line item: HT-233 engagement radar, two units.",
        "component", "model_designation", "HT-233", id="component-model-tender",
    ),
    pytest.param(
        "imagery_geoint",
        {"components": [{"name": "engagement radar", "model_designation": "HT-233",
                         "source_quote": "an HT-233 engagement radar"}]},
        "GEOINT note: an HT-233 engagement radar sits on the northern pad.",
        "component", "model_designation", "HT-233", id="component-model-imagery",
    ),
    pytest.param(
        "prose_claim",
        {"variants": [{"name": "HQ-9/P", "designators": ["HQ-9P", "FD-2000"],
                       "source_quote": "HQ-9/P, also written HQ-9P and marketed as FD-2000"}]},
        "Analytic note: HQ-9/P, also written HQ-9P and marketed as FD-2000, is in service.",
        "variant", "designators", ["HQ-9P", "FD-2000"], id="variant-designators-prose",
    ),
    pytest.param(
        "tender_procurement",
        {"system": {"name": "HQ-9/P", "designators": ["HQ-9P", "FD-2000"],
                    "source_quote": "HQ-9/P (HQ-9P, FD-2000)"}},
        "Tender skeleton: system HQ-9/P (HQ-9P, FD-2000), sustainment lot.",
        "variant", "designators", ["HQ-9P", "FD-2000"], id="variant-designators-tender",
    ),
]


@pytest.mark.parametrize("fmt,filled,text,etype,attr,expected", _ALIGNMENT_CASES)
def test_identity_attribute_reaches_the_key_the_scorer_reads(
    config: ConfigBundle, fmt: str, filled: dict, text: str, etype: str, attr: str, expected: object,
) -> None:
    loaded = loaders.load_document(text, file=f"synthetic_align_{fmt}.txt")
    source_type = "customs-tender" if fmt == "tender_procurement" else "curated-register"
    claims = extract_document(loaded, source_id="synthetic", source_type=source_type,
                              config=config, client=_client(filled), format_hint=fmt)
    entities = [e for e in _entities(claims) if e.entity_type == etype]
    assert entities, f"no {etype} entity emitted for format {fmt}"
    assert entities[0].attrs.get(attr) == expected


#: Declared-but-unwritable identity attributes that are KNOWN and deliberate, each with the reason it is not
#: a defect. Anything not on this list failing the gate below is the real thing: a scored slot that is empty
#: on every candidate. The list is meant to shrink.
_KNOWN_UNREACHABLE: dict[str, dict[str, str]] = {
    "unit": {
        # A formation's position is not a property of the formation — it is carried by the dated relationship
        # that puts it somewhere, which is why the mention class has no location field. Declared `perishable`,
        # so durable-identity scoring discards it in any case; it exists to give geography a time role.
        "coordinates": "a unit's location rides on its dated basing relationship, never on the unit itself",
    },
    "variant": {
        # Real, and written by the seeded baseline / answer key / ontology vocabulary — but not by the live
        # extraction path, which states designations as the LIST a source actually gives ("HQ-9/P, marketed as
        # FD-2000"). Both keys stay declared: `designators` covers the live half, this one the seeded half.
        # Picking one export name out of a stated list is a judgement the extractor is not asked to make.
        "export_designator": "seeded/answer-key half of the corpus; the live path states `designators`",
    },
}


def test_the_declared_identity_attributes_are_reachable_from_the_extractor() -> None:
    """The alignment itself, asserted against the shipped config rather than a fixture.

    Every attribute ``config/resolution.yaml`` declares identity-bearing and non-taxonomic must be a key some
    extraction path can actually write, or the declaration scores a slot that is structurally always empty —
    which is the state this pass found for ``unit.designator`` and ``component.model_designation``. Restricted
    to the four types the extractor mints directly; the derived citizens (``presence``, ``area_of_operations``)
    are assembled at rebuild and legitimately have no extraction slot.

    This is the gate that would have caught the original defect on the day it was introduced. It is a ratchet,
    not a snapshot: the two remaining gaps are enumerated in :data:`_KNOWN_UNREACHABLE` with the reason each is
    deliberate, so a *new* declaration against a key nothing writes fails here rather than being discovered
    later as a discriminator signal that fires on 4 of 203 candidates.
    """
    from chanakya import settings
    from chanakya.config.store import ConfigStore
    from chanakya.ingest.extract import ComponentMention, SiteMention, UnitMention, VariantMention

    resolution = ConfigStore.seed_from(settings.config_dir()).snapshot().resolution
    roles = resolution.model_dump().get("attribute_roles") or {}

    mentions: dict[str, tuple[type, set[str]]] = {
        # The mention class, plus the attrs the transform derives under a DIFFERENT name than the field
        # (a location string is normalised into `coordinates`; a range string into `range_km`).
        "unit": (UnitMention, set()),
        "component": (ComponentMention, set()),
        "variant": (VariantMention, set()),
        "basing_site": (SiteMention, {"coordinates"}),
    }
    unreachable: dict[str, list[str]] = {}
    for etype, (cls, derived) in mentions.items():
        declared = {
            attr for attr, spec in (roles.get(etype) or {}).items()
            if isinstance(spec, dict)
            and spec.get("role") in ("critical", "supporting")
            and spec.get("taxonomic") is not True
        }
        known = set(_KNOWN_UNREACHABLE.get(etype, {}))
        missing = sorted(declared - set(cls.model_fields) - derived - known)
        if missing:
            unreachable[etype] = missing
    assert not unreachable, (
        f"these attributes are declared identity-bearing but no extraction field writes them: {unreachable}. "
        "A declaration against a key the extractor never fills is scored on every merge candidate and is "
        "empty on every one of them — the identity evidence never reaches the comparison. Either add the "
        "capture field, or record it in _KNOWN_UNREACHABLE with the reason it is deliberate."
    )
    # …and the exception list must not outlive its exceptions: a name that IS now reachable has to come off,
    # or the list quietly re-admits the defect it documents.
    stale = {
        etype: sorted(attr for attr in attrs if attr in set(mentions[etype][0].model_fields))
        for etype, attrs in _KNOWN_UNREACHABLE.items()
        if any(attr in set(mentions[etype][0].model_fields) for attr in attrs)
    }
    assert not stale, f"_KNOWN_UNREACHABLE still excuses attributes the extractor now writes: {stale}"
