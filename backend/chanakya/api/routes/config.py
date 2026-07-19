"""``POST /config/{section}`` — hot-config writes (API.md scope 7; §1 invariant 3, spine/09).

Writes a whole config section to the **live** config store and triggers an in-process
:meth:`AppState.rebuild_and_swap` — **no restart**. Covers the documented surfaces: ``observable``
(define/arm a tripwire, §4.6), ``credibility`` (weights / thresholds / half-lives), ``ontology`` (extend
node/edge/event types) — and any other config section, since the store is generic. Defining an observable
also **arms it on save** (a read-only back-scan of the current view for immediate matches), so a tripwire
can light up against existing state the moment it's created, before any new ingest. The write goes to the
store, never a baked file.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.observe import arm
from chanakya.schemas import CONFIG_SECTIONS, ConfigWrite, ConfigWriteResult

router = APIRouter()

# API.md documents singular paths (/config/observable); the store sections are the plural keys.
_ALIASES = {
    "observable": "observables",
    "subject": "subjects",
    "source": "sources",
    "place": "places",
    "template": "templates",
}


def _resolve_section(section: str) -> str:
    resolved = _ALIASES.get(section, section)
    if resolved not in CONFIG_SECTIONS:
        raise HTTPException(
            404,
            detail={"error": "unknown config section", "section": section, "available": sorted(CONFIG_SECTIONS)},
        )
    return resolved


def _observable_ids(state: AppState) -> set[str]:
    return {o.observable_id for o in state.config.snapshot().observables.observables}


def _arm_new_observables(state: AppState, before_ids: set[str]) -> None:
    """Back-scan newly-defined observables against the current view; push immediate matches to the feed."""
    snapshot = state.config.snapshot()
    view = state.view()
    stamp = state.now()
    for obs in snapshot.observables.observables:
        if obs.observable_id in before_ids:
            continue
        for alert in arm(obs, view, snapshot):
            if alert.fired_ts is None:
                alert.fired_ts = stamp
            state.alerts.append(alert)


@router.post("/config/{section}", response_model=ConfigWriteResult)
def post_config(section: str, body: ConfigWrite, state: AppState = Depends(get_state)) -> ConfigWriteResult:
    resolved = _resolve_section(section)
    if body.section and _ALIASES.get(body.section, body.section) != resolved:
        raise HTTPException(
            400, detail={"error": "section mismatch", "path": resolved, "body": body.section}
        )

    before_ids = _observable_ids(state) if resolved == "observables" else set()
    try:
        version = state.config.set_section(resolved, body.value)
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(422, detail=f"invalid config for section {resolved!r}: {exc}") from exc

    if resolved == "observables":
        _arm_new_observables(state, before_ids)
    state.rebuild_and_swap()  # config changes propagate live (thresholds → statuses, etc.)
    return ConfigWriteResult(section=resolved, version=version)
