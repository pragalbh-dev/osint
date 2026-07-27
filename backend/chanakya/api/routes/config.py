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

**Trigger reachability (AH-3).** Anchors binding is only half of "is this tripwire actually watching".
The other half — measured wrong on the running app — is whether the *condition* it watches for can occur
on this graph at all. Two of the three shipped observables could not (one waits on an edge type coverage
yields none of; one compiles to arm-only and has no detector), and both rendered as ordinary armed
tripwires, one of them advertising "watching 66 node(s)". ``GET`` now carries
``diagnostics.trigger_reachability`` beside the anchor check and ``POST`` returns the same verdicts as
warnings, so an armed-but-silent wire can never again read as an all-clear. Also a warning, not a
rejection: arming a wire for a relation that is not yet observable is a legitimate act — being told
nothing about it is not.

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
from chanakya.observe import anchor_diagnostics, arm, reachability_diagnostics
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


def _reachability_check(state: AppState) -> dict[str, Any]:
    """The live trigger-reachability check over every armed observable (AH-3).

    The anchor check answers "do this tripwire's anchors bind to a node?". This answers the question one
    layer up, and the one the running app was measured getting wrong: **given that everything resolves,
    could the condition this tripwire watches for occur on this graph at all?** Two of the three shipped
    observables could not — one watches for a ``replenishes`` edge the view holds none of, one compiles
    to arm-only — and both rendered as plain armed tripwires. An armed tripwire that cannot fire turns an
    absence of alerts into an all-clear, which is the one thing this system may never do.

    Complete rather than problems-only, so the Watch panel can render a per-card verdict (a card that
    cannot say "watching, and it could fire" has to imply it). Recomputed per read against the current
    view, so a ``no_coverage`` verdict clears itself the moment an ingest produces the missing type —
    same hot-config rule as the anchor check, and never a boot-time-only validation. ``checked: false``
    rather than a clean bill of health when there is no view; an unperformed check is never a pass.
    """
    try:
        view = state.view()
    except RuntimeError:
        return {
            "checked": False,
            "reason": "no rebuilt view yet — trigger reachability cannot be checked",
            "observables": [],
        }
    return {"checked": True, "observables": reachability_diagnostics(state.config.snapshot(), view)}


def _reachability_is_worth_saying(entry: dict[str, Any], anchor_warned: set[str]) -> bool:
    """Should this reachability verdict be repeated in the write's ``warnings``?

    Two warnings for one fault is how a monitoring surface teaches its analyst to skim. When a tripwire's
    candidates are all outside its watch scope AND the anchor check already complained about the same
    tripwire, the two are the *same* finding seen from either end — and the anchor sentence is strictly
    the more useful one (it names which anchor, where it was declared, and whether it is broken or merely
    uncovered; the reachability sentence quotes it verbatim anyway). So the scope verdict defers.

    It still defers only in that overlap. A scope shortfall with **no** anchor complaint — every anchor
    resolved, but ``anchors_within_hops`` is too tight to reach any candidate — is invisible to the
    anchor check, and that is precisely the case this branch was added to catch. The verdict itself is
    unconditional on the read surface either way; this only decides whether the *write* repeats it.
    """
    if entry["can_fire"] or not entry["warning"]:
        return False
    return not (entry["gap_kind"] == "scope" and entry["observable_id"] in anchor_warned)


@router.get("/config/{section}", response_model=ConfigRead)
def get_config(section: str, state: AppState = Depends(get_state)) -> ConfigRead:
    """The current value of one section, from the live store. The mirror of ``post_config``.

    For ``observables`` the response also carries two live diagnostics, because "3 armed" is the same
    string whether those three are watching the graph or watching nothing:

    * ``diagnostics.anchor_check`` — whether each armed tripwire's anchors bind to a node (AH-1/AH-2);
    * ``diagnostics.trigger_reachability`` — whether each armed tripwire's *condition* could ever occur
      on this graph, and the named missing edge type / node type / attribute when it could not (AH-3).
    """
    resolved = _resolve_section(section)
    value = state.config.get_section(resolved)
    diagnostics: dict[str, Any] = {}
    if resolved == "observables":
        diagnostics["anchor_check"] = _anchor_check(state)
        diagnostics["trigger_reachability"] = _reachability_check(state)
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
    # VALIDATE BEFORE COMMITTING — the whole reduction, not just the pydantic parse.
    #
    # Pydantic validity is the first layer only: the readers that compile a section into its runtime form
    # (``ResolveConfig`` and the load-time validators behind it — a band ceiling outside the vocabulary, a
    # retired stage marker, a bad attribute role) raise on a section that is perfectly well-formed YAML and
    # semantically impossible. Those raise inside ``rebuild()``. With the commit outside the try/except, an
    # invalid POST committed the section to the LIVE store, returned an unhandled 500, and then every
    # subsequent config write and every rebuild 500ed too — hot config bricked until someone happened to
    # re-POST a valid section. That inverts the one contract this route exists to keep: nothing a user does
    # in-app may require a restart.
    #
    # So the candidate bundle is reduced first and committed only if the reduction succeeds. A rejected POST
    # leaves the running system byte-identical: same sections, same version, same view. Rolling back after
    # the fact would have left the version bumped twice and a window in which the live store held a section
    # nobody had validated.
    try:
        candidate = state.config.candidate(resolved, body.value)
        state.dry_run(candidate)
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(422, detail=f"invalid config for section {resolved!r}: {exc}") from exc
    version = state.config.commit(candidate)

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
        anchor_warned = {entry["observable_id"] for entry in check["unresolved"]}
        warnings.extend(
            f"{entry['observable_id']}: {entry['warning']}" for entry in check["unresolved"]
        )
        # AH-3 — and warn on a tripwire whose CONDITION cannot occur, not just one whose anchors miss.
        # Also non-fatal: arming a wire for a relation coverage has not produced yet is a legitimate,
        # even desirable act ("tell me the day this becomes observable") — what is not legitimate is
        # arming it and being told nothing, so it lands as a warning rather than a rejection.
        reach = _reachability_check(state)
        if not reach["checked"]:
            warnings.append(f"observable trigger reachability was not checked: {reach['reason']}")
        warnings.extend(
            f"{entry['observable_id']}: {entry['warning']}"
            for entry in reach["observables"]
            if _reachability_is_worth_saying(entry, anchor_warned)
        )
    return ConfigWriteResult(section=resolved, version=version, warnings=warnings)
