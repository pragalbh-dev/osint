"""Fixtures for the RESOLVE tests — small hand-built configs + claim builders (offline, deterministic)."""

from __future__ import annotations

from typing import Any

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    CredibilityConfig,
    DocRef,
    EntityDescriptor,
    ExactDate,
    OntologyConfig,
    PlaceEntry,
    PlacesConfig,
    ResolutionConfig,
    ResolvedRef,
    SourceRegistryEntry,
    SourcesConfig,
    Triple,
)

# The canonical C weights/bands, so tests exercise the real defaults (DATA-C authors the same numbers).
WEIGHTS = {"attribute": 0.40, "relational": 0.40, "temporal_consistency": 0.05, "source_asserted": 0.15}
BANDS = {"auto_merge": 0.85, "hitl_low": 0.45}


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
    place_allowed_precision_classes: dict[str, list[str]] | None = None,
    place_min_geocode_confidence: float | None = None,
    toponym_descriptive_markers: list[str] | None = None,
    place_bind_on_curated_toponym: bool = False,
    place_identity_precision_classes: list[str] | None = None,
    containment_min_descriptor_len: int | None = None,
    containment_min_short_tokens: int | None = None,
    acronym_min_len: int | None = None,
    source_grades: dict[str, str] | None = None,
    coref_authoritative_evidence: list[str] | None = None,
    entity_geo_conflict_max_km: dict[str, float] | None = None,
    relational_support_k: int | None = None,
    ontology: OntologyConfig | None = None,
) -> ConfigBundle:
    resolution = ResolutionConfig(
        coref_authoritative_evidence=coref_authoritative_evidence or [],
        entity_geo_conflict_max_km=entity_geo_conflict_max_km or {},
        relational_support_k=relational_support_k,
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
        place_allowed_precision_classes=place_allowed_precision_classes or {},
        place_min_geocode_confidence=place_min_geocode_confidence,
        toponym_descriptive_markers=toponym_descriptive_markers or [],
        place_bind_on_curated_toponym=place_bind_on_curated_toponym,
        place_identity_precision_classes=place_identity_precision_classes or [],
        containment_min_descriptor_len=containment_min_descriptor_len,
        containment_min_short_tokens=containment_min_short_tokens,
        acronym_min_len=acronym_min_len,
    )
    places_cfg = PlacesConfig(places=places or [], proximity_radius_m=proximity_radius_m or {})
    # ``source_grades``: {source_id: source_class} + a one-factor rubric, so R(source) == the number below
    # and a test can state "this class is worth X" without restating the whole credibility surface.
    sources_cfg = SourcesConfig(
        sources=[SourceRegistryEntry(source_id=sid, source_type=cls) for sid, cls in (source_grades or {}).items()]
    )
    credibility = CredibilityConfig(
        factor_weights={"authority": 1.0} if source_grades else {},
        source_class_factors=CLASS_AUTHORITY if source_grades else {},
    )
    return ConfigBundle(
        version=1,
        resolution=resolution,
        places=places_cfg,
        sources=sources_cfg,
        credibility=credibility,
        ontology=ontology or OntologyConfig(),
    )


# One-factor stand-in for the real rubric: R(class) == its authority score (see mk_config).
CLASS_AUTHORITY = {"curated-register": {"authority": 0.9}, "anon-social": {"authority": 0.2}}


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


def coref(
    subject: str,
    obj: str,
    *,
    evidence: str = "EXPLICIT_EQUIVALENCE",
    quote: str = "Full Name (SHORT)",
    source: str = "src-t",
    cluster: str = "c1",
) -> ClaimRecord:
    """An in-document coreference claim as INGEST's extraction pass 2 emits it (``ingest/coref.py``).

    Written on its own predicate, carrying the categorical evidence kind and the verbatim licensing span
    in the tier-3 bag — that bag is what ``resolve._coref_pairs`` reads to decide bootstrap vs raise-only.
    """
    return ClaimRecord(
        claim_id=_cid("cr"),
        source_id=source,
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="relationship",
        payload=Triple(subject=subject, predicate="coref-same-as", object=obj),
        attributes={"_coref_cluster": cluster, "_coref_evidence": evidence, "source_quote": quote},
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
