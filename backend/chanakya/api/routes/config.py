"""``GET|POST /config/{section}`` — hot-config reads + writes (API.md scope 7; §1 invariant 3, spine/09).

**Write.** Writes a whole config section to the **live** config store and triggers an in-process
:meth:`AppState.rebuild_and_swap` — **no restart**. Covers the documented surfaces: ``observable``
(define/arm a tripwire, §4.6), ``credibility`` (weights / thresholds / half-lives), ``ontology`` (extend
node/edge/event types) — and any other config section, since the store is generic. Defining an observable
also **arms it on save** (a read-only back-scan of the current view for immediate matches), so a tripwire
can light up against existing state the moment it's created, before any new ingest. The write goes to the
store, never a baked file.

**Read.** The write replaces a *whole* section, so without a read there is no safe read-modify-write:
a client wanting to nudge one credibility weight, or arm one extra observable, would have to either
re-send a copy of the config it has hardcoded (config duplicated in the client — exactly what
"config-driven, not hardcoded" forbids) or send a partial and clobber the rest. ``GET`` closes that:
same path, same section vocabulary, same :class:`ConfigStore` accessor — so read and write agree by
construction. It serves the **live store**, never ``config/*.yaml`` on disk, which is what makes an
in-app edit visible to the very next read with no restart.

It also makes the **armed** catalogue readable. Until now the only observable knowledge the SPA had was
the *fired* alert feed on ``GET /view``, so a cold boot with three armed tripwires and no firings was
indistinguishable from "nothing is being watched" — an underclaim just as dishonest as an overclaim.

**Anchor validation (AH-1).** Arming a tripwire against an instance id that resolves to nothing used to
be accepted in silence, and the tripwire then watched nothing in silence — an absence reading as an
all-clear, which is exactly what this system may not do. Both the read and the write now run the live
anchor check: ``GET`` carries it under ``diagnostics.anchor_check`` (so the Watch panel can say
"watching nothing" beside the armed card) and ``POST`` returns it as ``warnings``. It is a **warning,
not a rejection** — an anchor may legitimately be declared before the entity exists, and the check is
re-run live on every read, so it clears itself when an ingest creates the node. No restart, no cached
verdict, and no boot-time-only validation (the hot-config rule).

Every section is readable. ``config/`` holds no secrets by construction (secrets live in ``.env`` and
are read via ``chanakya.settings``, never through :class:`ConfigBundle`), so there is no section to
withhold, and withholding one would leave a config editor that cannot edit it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.observe import anchor_diagnostics, arm
from chanakya.schemas import CONFIG_SECTIONS, ConfigRead, ConfigWrite, ConfigWriteResult

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


def _anchor_check(state: AppState) -> dict[str, Any]:
    """The live anchor check over every armed observable (AH-1) — never a boot-time-only validation.

    Recomputed on each read against the **current** view, so it honours the hot-config rule in both
    directions: a tripwire armed against an entity that does not exist yet reports as unresolved now and
    clears itself the moment an ingest creates that node — with no restart, and no cached verdict.
    ``checked: false`` is returned rather than a clean bill of health when there is no view to check
    against; an unperformed check is never reported as a pass.
    """
    try:
        view = state.view()
    except RuntimeError:  # not booted yet — /health guards this, but never claim a pass we didn't run
        return {"checked": False, "reason": "no rebuilt view yet — anchors cannot be checked", "unresolved": []}
    return {"checked": True, "unresolved": anchor_diagnostics(state.config.snapshot(), view)}


@router.get("/config/{section}", response_model=ConfigRead)
def get_config(section: str, state: AppState = Depends(get_state)) -> ConfigRead:
    """The current value of one section, from the live store. The mirror of ``post_config``.

    For ``observables`` the response also carries ``diagnostics.anchor_check`` — whether each armed
    tripwire's anchors actually bind to a node in the current view. Without it the catalogue read says
    "3 armed" identically whether those three are watching the graph or watching nothing.
    """
    resolved = _resolve_section(section)
    value = state.config.get_section(resolved)
    diagnostics: dict[str, Any] = {}
    if resolved == "observables":
        diagnostics["anchor_check"] = _anchor_check(state)
    return ConfigRead(
        section=resolved,
        version=state.config.version,
        value=value.model_dump(mode="json"),
        diagnostics=diagnostics,
    )


@router.post("/config/{section}", response_model=ConfigWriteResult)
def post_config(section: str, body: ConfigWrite, state: AppState = Depends(get_state)) -> ConfigWriteResult:
    resolved = _resolve_section(section)
    if body.section and _ALIASES.get(body.section, body.section) != resolved:
        raise HTTPException(
            400, detail={"error": "section mismatch", "path": resolved, "body": body.section}
        )
    # Optimistic concurrency for read-modify-write: only checked when the caller opts in by echoing
    # the version its GET returned. Absent → last-writer-wins, the pre-existing contract.
    if body.if_version is not None and body.if_version != state.config.version:
        raise HTTPException(
            409,
            detail={
                "error": "config version conflict",
                "section": resolved,
                "expected": body.if_version,
                "current": state.config.version,
            },
        )

    before_ids = _observable_ids(state) if resolved == "observables" else set()
    try:
        version = state.config.set_section(resolved, body.value)
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(422, detail=f"invalid config for section {resolved!r}: {exc}") from exc

    if resolved == "observables":
        _arm_new_observables(state, before_ids)
    state.rebuild_and_swap()  # config changes propagate live (thresholds → statuses, etc.)

    # AH-1 — validate the anchors AFTER the rebuild, against the view the tripwire will actually run on.
    # Non-fatal by design (see ConfigWriteResult): an anchor may precede the entity that satisfies it, so
    # rejecting would break "arm the tripwire, then ingest". Silence would not — hence the warning.
    warnings: list[str] = []
    if resolved == "observables":
        check = _anchor_check(state)
        if not check["checked"]:
            warnings.append(f"observable anchors were not checked: {check['reason']}")
        warnings.extend(
            f"{entry['observable_id']}: {entry['warning']}" for entry in check["unresolved"]
        )
    return ConfigWriteResult(section=resolved, version=version, warnings=warnings)
