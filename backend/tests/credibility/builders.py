"""Tiny deterministic builders for SCORE stage tests (claims, sources, config, assertions).

Shared by tests/credibility, tests/sufficiency, tests/materiality. Everything is hand-built and offline
so the arithmetic can be asserted exactly (two 0.6 → 0.84; echoes → one group; gate caps at probable).
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import (
    AssertionInput,
    ClaimRecord,
    ConfigBundle,
    IndependenceGroup,
    SourceRegistryEntry,
)
from chanakya.schemas.claim import Triple
from chanakya.schemas.config_models import CredibilityConfig, SourcesConfig, TemplatesConfig
from chanakya.schemas.values import ExactDate


def cred_config(**overrides: Any) -> CredibilityConfig:
    """A credibility config whose classes all yield R = authority (weight 1.0) → easy exact arithmetic."""
    base: dict[str, Any] = {
        "factor_weights": {"authority": 1.0},
        "source_class_factors": {
            "imint": {"authority": 0.6},
            "text": {"authority": 0.6},
            "text2": {"authority": 0.6},
            "weak": {"authority": 0.25},
            "strong": {"authority": 0.9},
        },
        "integrity_penalties": {
            "first_seen.original": 1.0,
            "first_seen.recycled": 0.3,
            "coordinated_inauthenticity.independent": 1.0,
            "coordinated_inauthenticity.suspected": 0.5,
            "coordinated_inauthenticity.too_clean": 0.4,
            "artifact_integrity.edited": 0.3,
            "caption.mismatched": 0.3,
        },
        "thresholds": {"confirmed": 0.80, "probable": 0.50},
        "half_lives_days": {"based-at": 365},
        "decay_base": 2,
        "min_independent_groups": 2,
        "same_class_weight": 0.5,
        "pdq_recycled_hamming": 10,
        "aligned_bias_vectors": ["operator-state", "exporter-state"],
        "disciplines": {"imint": "IMINT"},
        "gated_attrs": ["foreign_control", "readiness"],
    }
    base.update(overrides)
    return CredibilityConfig(**base)


def bundle(
    credibility: CredibilityConfig | None = None,
    sources: list[SourceRegistryEntry] | None = None,
    templates: TemplatesConfig | None = None,
) -> ConfigBundle:
    return ConfigBundle(
        credibility=credibility or cred_config(),
        sources=SourcesConfig(sources=sources or []),
        templates=templates or TemplatesConfig(templates=[]),
    )


def source(
    sid: str,
    stype: str = "text",
    *,
    bias: str = "third-party",
    origin: str | None = None,
    aggregator: list[str] | None = None,
    adversary: bool = False,
    coordinated: bool = False,
    cadence: str | None = None,
) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        source_id=sid,
        source_type=stype,
        bias_vector=bias,  # type: ignore[arg-type]
        primary_origin_id=origin,
        aggregator_of=aggregator or [],
        adversary_denial_flag=adversary,
        coordinated_inauthenticity_flag=coordinated,
        cadence=cadence,
    )


def claim(
    cid: str,
    sid: str,
    *,
    predicate: str = "manufactures",
    subject: str = "u",
    obj: str = "s",
    kind: str = "observation",
    event: str | None = None,
    report: str | None = None,
    premises: list[str] | None = None,
    attributes: dict[str, Any] | None = None,
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid,
        source_id=sid,
        doc_ref={"file": f"{cid}.txt"},
        kind=kind,  # type: ignore[arg-type]
        asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=event) if event else None,
        report_time=ExactDate(iso_date=report) if report else None,
        premises=premises or [],
        attributes=attributes,
    )


def assertion(
    element_id: str = "e1",
    *,
    per_claim: dict[str, float] | None = None,
    groups: list[IndependenceGroup] | None = None,
    gate_flags: list[str] | None = None,
    contradiction: bool = False,
    satisfied: bool | None = True,
) -> AssertionInput:
    from chanakya.schemas import SufficiencyEval

    return AssertionInput(
        element_id=element_id,
        element_kind="edge",
        per_claim_credibility=per_claim or {},
        groups=groups or [],
        has_unresolved_contradiction=contradiction,
        gate_flags=gate_flags or [],
        sufficiency=None if satisfied is None else SufficiencyEval(satisfied=satisfied),
    )


def group(gid: str, claim_ids: list[str], *, weight: float = 1.0, discipline: str = "textual") -> IndependenceGroup:
    return IndependenceGroup(
        group_id=gid, claim_ids=claim_ids, weight=weight, axis_key={"discipline": discipline}
    )
