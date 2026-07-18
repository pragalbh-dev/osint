"""The observable evaluator — fires ``Alert`` objects off a ``rebuild()`` view delta (spine/08 §3.8).

The frozen entrypoint is ``evaluate(prev_view, view, config) -> [Alert]``: for each armed observable
(every entry in ``config.observables`` — "armed" = written to the live config store), it compiles the
trigger, scopes candidates to the observable's lens ∪ ``watch_instances``, and emits an Alert for each
**crossing** (state-change), **new** element, or predicate that **newly becomes true** between the
previous and new views.

Load-bearing invariants:

* **Match is on the resolved instance, never a designator string** — edges key on ``edge_instance``,
  nodes on ``id`` (spine/08 §3.1 ``resolved_ref``). A spelling/transliteration variant that resolves
  to the same instance trips the same wire; a genuinely different instance does not.
* **State/status is SCORE's job, not MONITOR's.** The evaluator only reports that a state *changed*
  (occupied@A → occupied@B); the probable→confirmed resolution and the supersede→stale decay behind
  the beat are computed inside ``rebuild()`` (SCORE). MONITOR reads the *active* edge (the one not
  superseded) and fires on the delta.
* **No clock/RNG/network/LLM** — ``fired_ts`` is left ``None`` for the caller (API) to stamp on
  persist, which also keeps the evaluator deterministic and testable (gate spirit of G1/G2).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from chanakya.schemas import Alert, ConfigBundle, EdgeView, GraphView, NodeView, ObservableDef

from .dsl import MISSING, evaluate_condition, resolve_field, within_area
from .observable import (
    ARM_ONLY,
    CROSSING,
    EXISTS,
    MATCH,
    CompiledTrigger,
    compile_trigger,
    resolve_scope,
)

_EMPTY = GraphView()


# ── active-element resolution (supersede-aware) ────────────────────────────────────────────────

def _active_edges(view: GraphView, edge_type: str | None) -> dict[str, EdgeView]:
    """Map ``edge_instance`` → the *active* edge (the one not superseded), filtered by ``edge_type``.

    When several edges share an ``edge_instance`` (the before→after of a relocation), the active one is
    the live edge (``superseded_by is None``); ``supersedes`` breaks a tie toward the newest; a stable
    id sort keeps it deterministic (G2 spirit).
    """
    groups: dict[str, list[EdgeView]] = defaultdict(list)
    for e in view.edges:
        if edge_type is not None and e.type != edge_type:
            continue
        groups[e.edge_instance or e.id].append(e)
    active: dict[str, EdgeView] = {}
    for key, group in groups.items():
        live = [e for e in group if e.superseded_by is None]
        pool = [e for e in live if e.supersedes is not None] or live or group
        active[key] = sorted(pool, key=lambda e: e.id)[0]
    return active


def _active_nodes(view: GraphView, node_type: str | None) -> dict[str, NodeView]:
    return {n.id: n for n in view.nodes if node_type is None or n.type == node_type}


def _state_value(el: EdgeView | NodeView | None, ct: CompiledTrigger) -> Any:
    """The tracked-state value of an element under a crossing trigger (edge target / field / geofence)."""
    if el is None:
        return MISSING
    if ct.geo_area is not None:
        return within_area(el, ct.geo_area) if isinstance(el, NodeView) else MISSING
    if ct.state_field is not None:
        return resolve_field(el, ct.state_field)
    return MISSING


def _display(value: Any) -> Any:
    """Render a state value for the Alert before/after (bool geofence → inside/outside; else as-is)."""
    if value is MISSING:
        return None
    if isinstance(value, bool):
        return "inside" if value else "outside"
    return value


def _watched(el: EdgeView | NodeView) -> str:
    """The resolved instance the alert is *about* — the edge's source (unit) or the node itself."""
    return el.source if isinstance(el, EdgeView) else el.id


def _in_scope(watched: str, scope: set[str] | None) -> bool:
    return scope is None or watched in scope


def _geo_ok(el: EdgeView | NodeView, ct: CompiledTrigger) -> bool:
    """Location-scope seam: keep a node candidate only if it sits inside ``scope_area`` (if set).

    Edge candidates ignore ``scope_area`` (geofencing an edge needs its endpoint's location — the
    join is the roadmap wiring; the primitive is here). ``within_area`` is offline great-circle math.
    """
    if ct.scope_area is None:
        return True
    return within_area(el, ct.scope_area) is True if isinstance(el, NodeView) else True


def _alert(obs: ObservableDef, ct: CompiledTrigger, subject: str, before: Any, after: Any) -> Alert:
    return Alert(
        observable_id=obs.observable_id,
        subject=subject,
        before={ct.label: _display(before)} if before is not MISSING else {},
        after={ct.label: _display(after)},
        severity=obs.severity,
        # fired_ts intentionally None — the API stamps it on persist (keeps evaluate deterministic).
    )


# ── per-mode detectors ─────────────────────────────────────────────────────────────────────────

def _crossing(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
              scope: set[str] | None) -> list[Alert]:
    if ct.element_kind == "edge":
        prev_active: dict[str, Any] = _active_edges(prev, ct.type_filter)
        new_active: dict[str, Any] = _active_edges(new, ct.type_filter)
    else:
        prev_active = _active_nodes(prev, ct.type_filter)
        new_active = _active_nodes(new, ct.type_filter)

    out: list[Alert] = []
    for key, el in new_active.items():
        watched = _watched(el)
        if not _in_scope(watched, scope) or not _geo_ok(el, ct):
            continue
        new_state = _state_value(el, ct)
        prev_state = _state_value(prev_active.get(key), ct)
        # A crossing needs a *known prior state* that differs — first-appearance is `new_edge`, not a
        # crossing; an indeterminate new state (MISSING) never fires (don't invent a change).
        if prev_state is MISSING or new_state is MISSING or prev_state == new_state:
            continue
        out.append(_alert(obs, ct, watched, prev_state, new_state))
    return out


def _exists(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
            scope: set[str] | None) -> list[Alert]:
    if ct.element_kind == "edge":
        prev_keys = {e.edge_instance or e.id for e in prev.edges
                     if ct.type_filter is None or e.type == ct.type_filter}
        new_active: dict[str, Any] = _active_edges(new, ct.type_filter)
    else:
        prev_keys = {n.id for n in prev.nodes if ct.type_filter is None or n.type == ct.type_filter}
        new_active = _active_nodes(new, ct.type_filter)

    out: list[Alert] = []
    for key, el in new_active.items():
        if key in prev_keys:
            continue
        watched = _watched(el)
        if not _in_scope(watched, scope) or not _geo_ok(el, ct):
            continue
        after = resolve_field(el, ct.state_field) if ct.state_field else _watched(el)
        out.append(_alert(obs, ct, watched, MISSING, after))
    return out


def _match(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
           scope: set[str] | None) -> list[Alert]:
    if ct.state_field is None or ct.op is None:
        return []
    if ct.element_kind == "edge":
        prev_active: dict[str, Any] = _active_edges(prev, ct.type_filter)
        new_active: dict[str, Any] = _active_edges(new, ct.type_filter)
    else:
        prev_active = _active_nodes(prev, ct.type_filter)
        new_active = _active_nodes(new, ct.type_filter)

    out: list[Alert] = []
    for key, el in new_active.items():
        watched = _watched(el)
        if not _in_scope(watched, scope) or not _geo_ok(el, ct):
            continue
        if not evaluate_condition(el, ct.state_field, ct.op, ct.value):
            continue
        prev_el = prev_active.get(key)
        # Fire only when the predicate *newly* becomes true — avoids re-firing every rebuild.
        if prev_el is not None and evaluate_condition(prev_el, ct.state_field, ct.op, ct.value):
            continue
        out.append(_alert(obs, ct, watched, MISSING, resolve_field(el, ct.state_field)))
    return out


_DETECTORS = {CROSSING: _crossing, EXISTS: _exists, MATCH: _match}


# ── public API ───────────────────────────────────────────────────────────────────────────────

def _fire(obs: ObservableDef, prev: GraphView, new: GraphView, config: ConfigBundle) -> list[Alert]:
    ct = compile_trigger(obs.trigger)
    if ct.mode == ARM_ONLY:
        return []
    scope = resolve_scope(obs, new, config)
    return _DETECTORS[ct.mode](obs, ct, prev, new, scope)


def evaluate(prev_view: GraphView | None, view: GraphView, config: ConfigBundle) -> list[Alert]:
    """Fire alerts for every armed observable whose condition crosses between ``prev_view`` and ``view``.

    ``prev_view is None`` (the first rebuild / a cold boot from the seeded baseline) yields **no**
    alerts: the baseline is the reference point, not a change. The first real alert comes from the next
    ingest/decision/config write that produces a baseline→after delta (spine/07 "fire on next rebuild").
    """
    if prev_view is None:
        return []
    alerts: list[Alert] = []
    for obs in config.observables.observables:
        alerts.extend(_fire(obs, prev_view, view, config))
    # Deterministic order (no clock/RNG — G2 spirit): by observable then subject.
    return sorted(alerts, key=lambda a: (a.observable_id, a.subject or ""))


def arm(observable: ObservableDef, view: GraphView, config: ConfigBundle) -> list[Alert]:
    """Read-only pass when an observable is defined/edited (spine/09 arm-on-save + back-scan).

    Evaluates the observable against the *current* view (no rebuild): ``exists``/``match`` triggers
    report matches that already hold (the back-scan — "you armed this and something already trips it");
    a ``crossing`` needs a delta, so it arms silently until the next ``rebuild()``. Returns the
    immediate matches (empty for a crossing/arm-only trigger).
    """
    ct = compile_trigger(observable.trigger)
    if ct.mode not in (EXISTS, MATCH):
        return []
    scope = resolve_scope(observable, view, config)
    return _DETECTORS[ct.mode](observable, ct, _EMPTY, view, scope)


def explain(observable: ObservableDef) -> dict[str, Any]:
    """Introspect how an observable compiles (mode, scope inputs, arm-only reason) — for the config UI."""
    ct = compile_trigger(observable.trigger)
    return {
        "observable_id": observable.observable_id,
        "mode": ct.mode,
        "element_kind": ct.element_kind,
        "type_filter": ct.type_filter,
        "fires_from_view_delta": ct.mode != ARM_ONLY,
        "arm_only_reason": ct.reason,
        "subject": observable.subject,
        "watch_instances": list(observable.watch_instances),
        "severity": observable.severity,
        "disposition_options": list(observable.disposition),
    }
