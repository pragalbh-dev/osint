"""``GET /coverage`` — the identity-resolution coverage summary (Stage 4 / D11).

A read-only, keyless, deterministic derivation kept SEPARATE from ``GET /view``: it reports the resolver's
three-status identity tail (``confirmed`` / ``probable`` / ``possible``) overall and per entity type, and
names the types where the unresolved identity load is high relative to confirmed merges — a *collection
gap*, i.e. the operator needs more evidence on that type before the resolver can confirm the links it keeps
proposing. It is intentionally NOT folded into the node/edge view, so the drawn graph JSON stays
byte-identical (gate G2). No LLM, no network, no mutation — it re-reads the same logs + config ``rebuild()``
does and folds the partition behind the current view.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.resolve import ResolveConfig
from chanakya.view import partition_with_types
from chanakya.view.coverage import IdentityCoverage, identity_coverage

router = APIRouter()


@router.get("/coverage", response_model=IdentityCoverage)
def get_coverage(state: AppState = Depends(get_state)) -> IdentityCoverage:
    """The identity-coverage summary for the current resolution state (D11).

    ``cfg`` supplies the transparency policy dials and the config-driven ``coverage_gap_ratio``
    (``config/resolution.yaml``) — config is authoritative for the production threshold.
    """
    config = state.config.snapshot()
    partition, type_map = partition_with_types(state.evidence, state.decision, config)
    return identity_coverage(partition, type_map, ResolveConfig.from_bundle(config))
