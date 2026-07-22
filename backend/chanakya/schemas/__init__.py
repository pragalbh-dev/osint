"""Frozen schema surface (master §4.2, §4.8). Import from here, not the submodules.

Records (evidence/decision logs) · value objects · view/knowledge models · stage I/O · config
surfaces · API shapes. Everything downstream reads these; changing a field after F0 merges is an
F0-amendment PR (master §2 Rule 3).
"""

from __future__ import annotations

from .api_models import (
    AnswerHop,
    AskAnswer,
    AskRequest,
    ConfigRead,
    ConfigWrite,
    ConfigWriteResult,
    HealthResponse,
    HitlDecision,
    IngestRequest,
    IngestResult,
    PriorTurn,
    ProvenanceDrawer,
    RefusalPayload,
    ReviewContext,
    ReviewQueueItem,
    ReviewType,
)
from .base import ConfigModel, Record
from .claim import (
    Asserts,
    BiasVector,
    ClaimPayload,
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    EventDescriptor,
    Extraction,
    Kind,
    Polarity,
    ResolvedRef,
    SourceRegistryEntry,
    Triple,
)
from .config_models import (
    CONFIG_SECTIONS,
    ConfigBundle,
    CredibilityConfig,
    EntitiesConfig,
    EntityEntry,
    EvidenceTemplate,
    ObservableDef,
    ObservablesConfig,
    OntologyConfig,
    PlaceEntry,
    PlacesConfig,
    ResolutionConfig,
    SourcesConfig,
    SubjectLens,
    SubjectsConfig,
    TemplatesConfig,
    TypeDef,
)
from .decision import Actor, DecisionRecord, DecisionType, Stage
from .ids import is_claim_id, make_claim_id
from .stage_io import AssertionAssessment, AssertionInput, Partition, PlaceRef, pair_key
from .values import (
    BoundarySource,
    CountState,
    DateSpec,
    DateValue,
    ExactDate,
    GeocodeCandidate,
    Granularity,
    LabelDate,
    Location,
    Period,
    PrecisionClass,
    Quantity,
    SurfaceFormat,
    canonical_iso_bounds,
)
from .view import (
    Alert,
    AlertProvenance,
    ConfidenceBreakdown,
    EdgeView,
    EventView,
    Freshness,
    GraphView,
    IndependenceGroup,
    KnownGap,
    MaterialityAttrs,
    NodeView,
    ObservabilityCeiling,
    Status,
    SufficiencyEval,
)

__all__ = [
    # base
    "Record", "ConfigModel",
    # ids
    "make_claim_id", "is_claim_id",
    # values
    "ExactDate", "LabelDate", "Period", "DateSpec", "DateValue", "canonical_iso_bounds",
    "Granularity", "BoundarySource", "Location", "GeocodeCandidate", "PrecisionClass",
    "SurfaceFormat", "Quantity", "CountState",
    # claim / evidence log
    "ClaimRecord", "DocRef", "Triple", "EntityDescriptor", "EventDescriptor", "ClaimPayload",
    "Extraction", "ResolvedRef", "SourceRegistryEntry", "Kind", "Polarity", "Asserts", "BiasVector",
    # decision log
    "DecisionRecord", "Actor", "Stage", "DecisionType",
    # stage io
    "Partition", "PlaceRef", "AssertionInput", "AssertionAssessment", "pair_key",
    # view
    "GraphView", "NodeView", "EdgeView", "EventView", "KnownGap", "Alert", "AlertProvenance",
    "ConfidenceBreakdown", "IndependenceGroup", "Freshness", "SufficiencyEval", "MaterialityAttrs",
    "Status", "ObservabilityCeiling",
    # config
    "ConfigBundle", "CONFIG_SECTIONS", "OntologyConfig", "SourcesConfig", "CredibilityConfig",
    "ResolutionConfig", "TemplatesConfig", "SubjectsConfig", "ObservablesConfig", "TypeDef",
    "EvidenceTemplate", "SubjectLens", "ObservableDef", "PlacesConfig", "PlaceEntry",
    "EntitiesConfig", "EntityEntry",
    # api
    "AskRequest", "PriorTurn", "AskAnswer", "AnswerHop", "RefusalPayload", "ProvenanceDrawer", "ReviewQueueItem",
    "ReviewContext", "ReviewType", "HitlDecision", "IngestRequest", "IngestResult", "ConfigRead", "ConfigWrite",
    "ConfigWriteResult", "HealthResponse",
]
