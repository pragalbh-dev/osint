"""Fixtures for the RESOLVE tests — small hand-built configs + claim builders (offline, deterministic)."""

from __future__ import annotations

from typing import Any

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DocRef,
    EntityDescriptor,
    ExactDate,
    PlaceEntry,
    PlacesConfig,
    ResolutionConfig,
    ResolvedRef,
    Triple,
)

# The canonical C weights/bands, so tests exercise the real defaults (DATA-C authors the same numbers).
WEIGHTS = {"attribute": 0.30, "relational": 0.40, "temporal_consistency": 0.15, "source_asserted": 0.15}
BANDS = {"auto_merge": 0.85, "hitl_low": 0.55}


def mk_config(
    *,
    alias_table: dict[str, list[str]] | None = None,
    transliteration: dict[str, str] | None = None,
    distinct_from: dict[str, list[str]] | None = None,
    attribute_rules: dict[str, Any] | None = None,
    attribute_scoring: dict[str, float] | None = None,
    hard_id_fields: dict[str, Any] | None = None,
    blocking_keys: list[str] | None = None,
    high_alias_risk_types: list[str] | None = None,
    orphan_block_threshold_k: int | None = None,
    llm_candidate_gen: dict[str, Any] | None = None,
    places: list[PlaceEntry] | None = None,
    proximity_radius_m: dict[str, float] | None = None,
    place_proximity_hitl_multiplier: float | None = None,
) -> ConfigBundle:
    resolution = ResolutionConfig(
        merge_weights=dict(WEIGHTS),
        bands=dict(BANDS),
        blocking_keys=blocking_keys or ["type", "country_or_domain_namespace", "name_token"],
        alias_table=alias_table or {},
        transliteration=transliteration or {},
        distinct_from=distinct_from or {},
        attribute_rules=attribute_rules or {},
        attribute_scoring=attribute_scoring or {},
        hard_id_fields=hard_id_fields or {},
        high_alias_risk_types=high_alias_risk_types or [],
        orphan_block_threshold_k=orphan_block_threshold_k,
        llm_candidate_gen=llm_candidate_gen or {},
        place_proximity_hitl_multiplier=place_proximity_hitl_multiplier,
    )
    places_cfg = PlacesConfig(places=places or [], proximity_radius_m=proximity_radius_m or {})
    return ConfigBundle(version=1, resolution=resolution, places=places_cfg)


_counter = {"n": 0}


def _cid(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']}"


def entity(eid: str, etype: str, name: str, **attrs: Any) -> ClaimRecord:
    return ClaimRecord(
        claim_id=_cid(eid),
        source_id="src-t",
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type=etype, name=name, attrs=attrs),
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def triple(
    subject: str,
    predicate: str,
    obj: str,
    *,
    iso: str | None = None,
    source: str = "src-t",
    edge_instance: str | None = None,
) -> ClaimRecord:
    # State predicates carry a slot-based edge_instance ("<predicate>:<subject>") upstream, so a unit's
    # two based-at targets share one instance — the supersede/relocation slot (as F0's golden fixture does).
    rr = ResolvedRef(entity_id=f"ent:{subject}", edge_instance=edge_instance) if edge_instance else None
    return ClaimRecord(
        claim_id=_cid("t"),
        source_id=source,
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=iso) if iso else None,
        resolved_ref=rr,
    )
