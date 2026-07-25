"""The observable evaluator — fires ``Alert`` objects off a ``rebuild()`` view delta (spine/08 §3.8).

The frozen entrypoint is ``evaluate(prev_view, view, config) -> [Alert]``: for each armed observable
(every entry in ``config.observables`` — "armed" = written to the live config store), it compiles the
trigger, scopes candidates to the observable's lens ∪ ``watch_instances``, and emits an Alert for each
**crossing** (state-change), **new** element, or predicate that **newly becomes true** between the
previous and new views.

Load-bearing invariants:

* **Match is on the resolved instance, never a designator string** — the grouping key comes from the
  observable's own declared ``match_on`` (``resolved_unit`` → the edge's subject, ``site_instance`` →
  the target is the *state*, ``resolved_instance`` → ``edge_instance``); with nothing declared, edges
  key on ``edge_instance`` and nodes on ``id`` (spine/08 §3.1 ``resolved_ref``). Either way it is a
  resolved id: a spelling/transliteration variant that resolves to the same instance trips the same
  wire; a genuinely different instance does not.
* **The alert cites its evidence** — every fired Alert carries the claim ids behind the before-state
  and the after-state (G4). An analyst never gets "the unit moved" with nothing to click.
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

from chanakya.schemas import (
    Alert,
    AlertProvenance,
    ConfigBundle,
    EdgeView,
    GraphView,
    NodeView,
    ObservableDef,
)

from .dsl import MISSING, evaluate_condition, resolve_field, within_area
from .observable import (
    ARM_ONLY,
    CROSSING,
    EXISTS,
    INSTANCE_KEY,
    MATCH,
    CompiledTrigger,
    ScopeResolution,
    compile_trigger,
    resolve_scope,
    resolve_scope_detail,
)

_EMPTY = GraphView()

Element = EdgeView | NodeView


# ── grouping key (the observable's declared identity for "the same wire") ───────────────────────

def _default_key(el: Element) -> str:
    """The fallback identity of a view element: its resolved edge instance, else its own id."""
    return (el.edge_instance or el.id) if isinstance(el, EdgeView) else el.id


def _group_key(el: Element, ct: CompiledTrigger) -> str:
    """The key an element groups under, honouring the observable's declared ``match_on`` (MON-3).

    ``match_on`` names the *identity* parts (``resolved_unit`` → the edge's subject); the tracked-state
    part (``site_instance`` → the target) is deliberately **excluded**, which is what lets a unit's old
    and new basing edge land in one group and cross. If any declared part is absent on this element we
    fall back to the default key rather than collapse unrelated elements into one bucket (recall bias:
    a wrong merge would fire a false alert about the wrong subject).
    """
    if not ct.group_by:
        return _default_key(el)
    parts: list[str] = []
    for field in ct.group_by:
        value = _default_key(el) if field == INSTANCE_KEY else resolve_field(el, field)
        if value is MISSING or value is None:
            return _default_key(el)
        parts.append(str(value))
    return "|".join(parts)


# ── active-element resolution (supersede-aware) ────────────────────────────────────────────────

def _active_edges(view: GraphView, ct: CompiledTrigger) -> dict[str, EdgeView]:
    """Map grouping key → the *active* edge (the one not superseded), filtered by the trigger's type.

    When several edges share a key (the before→after of a relocation), the active one is the live edge
    (``superseded_by is None``); ``supersedes`` breaks a tie toward the newest; a stable id sort keeps
    it deterministic (G2 spirit).
    """
    groups: dict[str, list[EdgeView]] = defaultdict(list)
    for e in view.edges:
        if ct.type_filter is not None and e.type != ct.type_filter:
            continue
        groups[_group_key(e, ct)].append(e)
    active: dict[str, EdgeView] = {}
    for key, group in groups.items():
        live = [e for e in group if e.superseded_by is None]
        pool = [e for e in live if e.supersedes is not None] or live or group
        active[key] = sorted(pool, key=lambda e: e.id)[0]
    return active


def _active_nodes(view: GraphView, ct: CompiledTrigger) -> dict[str, NodeView]:
    return {_group_key(n, ct): n for n in view.nodes
            if ct.type_filter is None or n.type == ct.type_filter}


def _candidates(view: GraphView, ct: CompiledTrigger) -> dict[str, Any]:
    """Active candidate elements of the trigger's kind, keyed by the declared grouping key."""
    return _active_edges(view, ct) if ct.element_kind == "edge" else _active_nodes(view, ct)


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


# ── generic condition block (`where_before` / `where_after` / `where_change`) ───────────────────

def _conditions_hold(el: Element | None, conds: tuple[Any, ...]) -> bool:
    """Every condition in a block must hold on ``el``; an absent element satisfies nothing (honest)."""
    if el is None:
        return False
    return all(evaluate_condition(el, c.field, c.op or "exists", c.value) for c in conds)


def _gates_pass(prev_el: Element | None, new_el: Element, ct: CompiledTrigger) -> bool:
    """Apply the observable's declared condition blocks to this before→after pair.

    Generic replacement for what bespoke trigger keys used to want (``from_site``/``to_site``/…):
    ``where_before`` constrains the prior state, ``where_after`` the new state, ``where_change`` the
    delta itself (the named field must differ; an ``op``/``value``, if given, additionally tests the
    new value). Blocks needing a prior state never pass when there is none — a tripwire is not allowed
    to assert what the world looked like before if it never saw it.
    """
    if ct.where_after and not _conditions_hold(new_el, ct.where_after):
        return False
    if ct.where_before and not _conditions_hold(prev_el, ct.where_before):
        return False
    if ct.where_change:
        if prev_el is None:
            return False
        for cond in ct.where_change:
            if resolve_field(prev_el, cond.field) == resolve_field(new_el, cond.field):
                return False
            if cond.op and not evaluate_condition(new_el, cond.field, cond.op, cond.value):
                return False
    return True


# ── alert construction (incl. provenance — G4) ─────────────────────────────────────────────────

def _claim_ids(el: Element | None) -> list[str]:
    return list(el.claim_ids) if el is not None else []


def _provenance(prev_el: Element | None, new_el: Element) -> AlertProvenance:
    """The evidence behind the alert: the claims that asserted the prior state and the new state.

    The union is order-stable (before-claims first, then new ones) and de-duplicated — it is what the
    provenance drawer opens on when the analyst clicks the alert. Status/confidence are copied from the
    *after* element (SCORE computed them; MONITOR never derives a score — G5).
    """
    before_ids, after_ids = _claim_ids(prev_el), _claim_ids(new_el)
    union: list[str] = []
    for cid in before_ids + after_ids:
        if cid not in union:
            union.append(cid)
    conf = new_el.confidence.assertion_confidence if new_el.confidence is not None else None
    return AlertProvenance(
        before_ref=prev_el.id if prev_el is not None else None,
        after_ref=new_el.id,
        before_claim_ids=before_ids,
        after_claim_ids=after_ids,
        claim_ids=union,
        status=new_el.status,
        assertion_confidence=conf,
    )


def _alert(obs: ObservableDef, ct: CompiledTrigger, subject: str, before: Any, after: Any,
           prev_el: Element | None = None, new_el: Element | None = None) -> Alert:
    return Alert(
        observable_id=obs.observable_id,
        subject=subject,
        before={ct.label: _display(before)} if before is not MISSING else {},
        after={ct.label: _display(after)},
        severity=obs.severity,
        provenance=_provenance(prev_el, new_el) if new_el is not None else None,
        # fired_ts intentionally None — the API stamps it on persist (keeps evaluate deterministic).
    )


# ── per-mode detectors ─────────────────────────────────────────────────────────────────────────

def _crossing(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
              scope: set[str] | None) -> list[Alert]:
    prev_active = _candidates(prev, ct)
    new_active = _candidates(new, ct)

    out: list[Alert] = []
    for key, el in new_active.items():
        watched = _watched(el)
        if not _in_scope(watched, scope) or not _geo_ok(el, ct):
            continue
        prev_el = prev_active.get(key)
        new_state = _state_value(el, ct)
        prev_state = _state_value(prev_el, ct)
        # A crossing needs a *known prior state* that differs — first-appearance is `new_edge`, not a
        # crossing; an indeterminate new state (MISSING) never fires (don't invent a change).
        if prev_state is MISSING or new_state is MISSING or prev_state == new_state:
            continue
        if not _gates_pass(prev_el, el, ct):
            continue
        out.append(_alert(obs, ct, watched, prev_state, new_state, prev_el, el))
    return out


def _exists(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
            scope: set[str] | None) -> list[Alert]:
    prev_keys = set(_candidates(prev, ct))
    new_active = _candidates(new, ct)

    out: list[Alert] = []
    for key, el in new_active.items():
        if key in prev_keys:
            continue
        watched = _watched(el)
        if not _in_scope(watched, scope) or not _geo_ok(el, ct):
            continue
        if not _gates_pass(None, el, ct):
            continue
        after = resolve_field(el, ct.state_field) if ct.state_field else _watched(el)
        out.append(_alert(obs, ct, watched, MISSING, after, None, el))
    return out


def _match(obs: ObservableDef, ct: CompiledTrigger, prev: GraphView, new: GraphView,
           scope: set[str] | None) -> list[Alert]:
    if ct.state_field is None or ct.op is None:
        return []
    prev_active = _candidates(prev, ct)
    new_active = _candidates(new, ct)

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
        if not _gates_pass(prev_el, el, ct):
            continue
        out.append(_alert(obs, ct, watched, MISSING, resolve_field(el, ct.state_field), prev_el, el))
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


def _condition_text(cond: Any) -> str:
    return f"{cond.field} {cond.op or 'changes'}" + ("" if cond.value is None else f" {cond.value!r}")


def explain(
    observable: ObservableDef,
    view: GraphView | None = None,
    config: ConfigBundle | None = None,
) -> dict[str, Any]:
    """Introspect how an observable compiles (mode, scope inputs, arm-only reason) — for the config UI.

    Also reports what the compile **did not** use: ``unconsumed_keys`` names every trigger key that was
    dropped (``ConfigModel`` is ``extra="allow"``, so nothing else can catch a typo or an aspirational
    key) and ``unconsumed_warning`` says so in one sentence for the analyst's confirm screen. A silently
    ignored key is how a tripwire ends up meaning something other than what it reads like.

    **Anchor honesty (AH-1).** ``watch_instances`` used to be echoed back verbatim with no statement of
    whether any of them resolved to a real node — so a tripwire watching nothing explained itself exactly
    like a healthy one. Pass ``view`` + ``config`` and the same scoping used at fire time runs here:
    ``unresolved_anchors`` names every anchor that binds to nothing and ``anchor_warning`` says what that
    means in one sentence. Without a view the check *cannot* be done, and ``anchor_check`` says so rather
    than implying a clean bill of health — an unperformed check is never reported as a pass.
    """
    ct = compile_trigger(observable.trigger)
    out = {
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
        # How the wire is grouped and what counts as its state (MON-3): [] = the default edge_instance/id.
        "match_on_group_by": list(ct.group_by),
        "tracked_state_field": ct.state_field,
        "conditions": {
            block: [_condition_text(c) for c in getattr(ct, block)]
            for block in ("where_before", "where_after", "where_change")
            if getattr(ct, block)
        },
        "unconsumed_keys": list(ct.unconsumed),
    }
    if ct.unconsumed:
        out["unconsumed_warning"] = (
            "these trigger keys were not used by the compiled tripwire and have no effect: "
            + ", ".join(ct.unconsumed)
        )
    out.update(_anchor_explanation(observable, view, config))
    return out


def _anchor_explanation(
    observable: ObservableDef, view: GraphView | None, config: ConfigBundle | None
) -> dict[str, Any]:
    """The anchor half of ``explain`` — what resolved, what did not, and what that means (AH-1)."""
    if view is None or config is None:
        return {
            "anchor_check": "not performed — no view supplied, so whether these anchors resolve is unknown",
            "unresolved_anchors": None,
        }
    detail = resolve_scope_detail(observable, view, config)
    out: dict[str, Any] = {
        "anchor_check": "ok" if detail.warning is None else detail.severity,
        "anchors_requested": list(detail.requested),
        "anchors_resolved": detail.resolved_map,
        "anchor_resolution": dict(detail.resolution_via or {}),
        "unresolved_anchors": list(detail.missing),
        # AH-2 — an anchor awaiting coverage is not a broken one; keep them apart on every surface.
        "anchors_pending_coverage": list(detail.pending_coverage),
        "anchors_dangling": list(detail.dangling),
        "anchor_severity": detail.severity,
        "anchors_declared_in": dict(detail.declared_in or {}),
        "watched_node_count": detail.watched_node_count,  # None = unscoped (watches everything)
        "watching_nothing": detail.watching_nothing,
    }
    if detail.warning:
        out["anchor_warning"] = detail.warning
    return out


def anchor_diagnostics(config: ConfigBundle, view: GraphView) -> list[dict[str, Any]]:
    """Every armed observable whose declared anchors do **not** all resolve against ``view`` (AH-1).

    The list is the API/SPA-facing form of :class:`ScopeResolution`: one entry per *broken* observable,
    so an empty list is the positive statement "every armed tripwire's anchors bind to a real node".
    Deterministic (config order); no clock/RNG — safe to call on any read path.

    **AH-2, two corrections to what counts as reportable:**

    * An ``arm-only`` observable is skipped. Both ``_fire`` and ``arm`` return on ``ARM_ONLY`` *before*
      calling ``resolve_scope``, so its scope is provably never consulted — reporting an anchor problem
      there blames an anchor for a silence that ``explain()`` already attributes, correctly and
      separately, to arm-only mode. ``explain()`` still reports its anchors, so nothing is hidden.
    * Entries carry ``severity``. A caller that renders every entry with equal loudness will cry wolf on
      this system's own default boot state, where a deliberately-withheld document leaves a declared
      entity uncovered; ``severity == "pending_coverage"`` is the quiet case.
    """
    out: list[dict[str, Any]] = []
    for obs in config.observables.observables:
        if compile_trigger(obs.trigger).mode == ARM_ONLY:
            continue
        detail: ScopeResolution = resolve_scope_detail(obs, view, config)
        if detail.warning is None:
            continue
        out.append(
            {
                "observable_id": obs.observable_id,
                "unresolved_anchors": list(detail.missing),
                "resolved_anchors": detail.resolved_map,
                "pending_coverage": list(detail.pending_coverage),
                "dangling": list(detail.dangling),
                "declared_in": dict(detail.declared_in or {}),
                "severity": detail.severity,
                "watched_node_count": detail.watched_node_count,
                "watching_nothing": detail.watching_nothing,
                "warning": detail.warning,
            }
        )
    return out
