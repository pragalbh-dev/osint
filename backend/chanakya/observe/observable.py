"""Compile a declarative ``ObservableDef`` into a working trigger + resolve its watch-scope.

Two jobs, both pure and config-driven:

* **``compile_trigger``** maps the frozen ``trigger`` dict (spine/08 §3.8) into a ``CompiledTrigger``
  the evaluator runs. Named ``on`` forms (``occupancy_state_change`` …) are sugar over three generic
  *modes* — **crossing** (state-change), **exists** (new element in the delta), **match** (a predicate
  becomes true). A recognised-but-not-view-delta trigger (e.g. ``new_claim``, which lives in the
  evidence log, not the view) compiles to ``arm-only`` — it still parses/arms, it just cannot fire off
  a view delta (spine/09 honest boundary). There is **no per-observable branch** — adding a tripwire is
  config only (gate G6 / the "declarative, not hardcoded" acceptance). Three further generic seams keep
  it that way as analysts invent tripwires (EVAL RCA MON-1):

  - **``match_on``** — the observable *declares its own grouping key*: which part of a view element is
    the identity of "the thing being tracked", and which part is the **tracked state** that may change.
    ``[resolved_unit, site_instance]`` means "one wire per unit; the site is what moves" — so a unit's
    old and new basing edge are the *same* wire, and a different unit's churn is a different wire.
    Without it the evaluator falls back to ``edge_instance``. This is what makes ``agent/propose.py``'s
    per-trigger ``match_on`` defaults mean something end-to-end.
  - **``where_before`` / ``where_after`` / ``where_change``** — a generic condition block over the prior
    state, the new state, and the delta, evaluated by the *existing* DSL operators. Anything a bespoke
    trigger key would have said ("only if it moved **from** X", "only **to** Y") is expressible here,
    so the grammar never needs another one-off key.
  - **``unconsumed``** — every trigger key this compile did **not** read is returned and surfaced by
    ``explain()``. ``ConfigModel`` is deliberately ``extra="allow"`` (hot-config), so a mistyped or
    aspirational key cannot be rejected by the schema; the answer is to make the drop *visible* on the
    analyst's confirm screen rather than silent (the same silent-drift failure as the lens filter).
* **``resolve_scope``** turns ``subject`` (a lens: anchors + hop bound) **∪** ``watch_instances``
  (explicit resolved ids) into the set of in-scope node ids. ``anchors_within_hops`` comes from the
  trigger/lens (config), never a literal (G6). Returns ``None`` = unscoped (evaluate everything) — the
  lenient, recall-biased fallback when a named lens's anchors aren't present in this view (don't
  silently disarm the tripwire).
* **``resolve_scope_detail``** is the same computation with the *diagnosis* attached
  (:class:`ScopeResolution`). ``resolve_scope`` is a thin wrapper over it, so there is exactly one
  scoping rule and the diagnosis can never drift from the scope it describes.

**Why the diagnosis exists (AH-1).** A tripwire anchored on a node id that no longer resolves used to
watch *nothing* and say *nothing*: zero alerts, no exception, no log line — an absence presented as an
all-clear, which is the precise inverse of this system's one non-negotiable. Worse, the scope seeded
itself with the **raw config strings**, so a debugger saw the expected id sitting in scope while the
real node was excluded; the phantom masked the fault. Both are fixed here:

* the returned scope now carries only ids the resolver actually bound (no raw-string phantoms), and
* every unresolved anchor is named on :class:`ScopeResolution` with a plain-language ``warning`` that
  the evaluator's ``explain()``, ``GET /config/observables`` and the Watch panel all surface.

The **scope semantics are deliberately unchanged**. ``None`` means *unscoped* to
``evaluator._in_scope`` — i.e. **match everything** — so an all-anchors-missing observable that still
declares ``watch_instances`` keeps returning that (non-matching) set rather than ``None``. Collapsing it
to ``None`` would turn "silently fires nothing" into "silently fires on every element in the graph",
which is a louder lie, not a fix. The failure is made *loud*, not *different*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from chanakya.resolve import resolve_anchors
from chanakya.schemas import ConfigBundle, GraphView, ObservableDef

from .dsl import OPERATORS

# Modes the evaluator understands. "arm-only" = recognised + armable but not fireable from a view delta.
CROSSING, EXISTS, MATCH, ARM_ONLY = "crossing", "exists", "match", "arm-only"

# ── the `match_on` vocabulary ────────────────────────────────────────────────────────────────────
# A token names one part of a view element. **Key** tokens compose the grouping key — the identity of
# the wire, i.e. what makes two elements in the before- and after-view "the same thing". **State**
# tokens name the part that is the tracked *state* — what is allowed to change without becoming a
# different thing. Getting a state token into the key is exactly the MON-3 defect: group a unit's
# basing edge by its target and the before/after land in different groups and nothing ever crosses.
#
# The vocabulary is a config-level table, not per-observable code: a new token is one row here, and
# an unrecognised token is reported as unconsumed rather than silently ignored.
INSTANCE_KEY = "@instance"  # sentinel: the element's own resolved instance (edge_instance, else id)

MATCH_ON_KEY_FIELDS: dict[str, str] = {
    "resolved_instance": INSTANCE_KEY,  # the resolved edge/node instance — the default
    "resolved_ref": INSTANCE_KEY,
    "resolved_node": INSTANCE_KEY,
    "resolved_unit": "source",  # a functional edge's subject: one wire per unit
    "resolved_subject": "source",
    "resolved_src": "source",
    "resolved_contract": "source",
}
MATCH_ON_STATE_FIELDS: dict[str, str] = {
    "site_instance": "target",  # the site a unit occupies — the thing that moves
    "resolved_dst": "target",
    "resolved_object": "target",
    "resolved_stockpile": "target",
}

# Trigger keys every compile reads (or that are read downstream by ``resolve_scope``); per-branch keys
# are added by the branch that consumes them. Anything left over is reported on ``unconsumed``.
_BASE_CONSUMED = frozenset({
    "on", "label", "within_area", "match_on",
    "anchors_within_hops",  # read by resolve_scope, not here — consumed, just not by the compiler
    "where_before", "where_after", "where_change",
})


@dataclass(frozen=True)
class Condition:
    """One generic condition in a ``where_*`` block: ``element.<field> <op> <value>``.

    ``op is None`` is only meaningful inside ``where_change`` and means "any change" (the field must
    differ between the two views, whatever the new value is).
    """

    field: str
    op: str | None = None
    value: Any = None


@dataclass(frozen=True)
class CompiledTrigger:
    """The evaluator-ready form of an observable's ``trigger`` (see ``compile_trigger``)."""

    mode: str  # CROSSING | EXISTS | MATCH | ARM_ONLY
    element_kind: str  # "edge" | "node"
    type_filter: str | None  # edge_type / node_type selecting candidate elements
    state_field: str | None  # the field whose value is the tracked state (crossing / match)
    op: str | None  # comparator for MATCH mode
    value: Any  # expected value for MATCH mode
    geo_area: dict[str, Any] | None  # {center:[lat,lon], radius_km} for a geofence crossing
    label: str  # the before/after key on the emitted Alert (e.g. the edge_type)
    reason: str | None  # why an ARM_ONLY trigger cannot fire from the view delta
    scope_area: dict[str, Any] | None = None  # location seam: only watch node candidates inside this area
    group_by: tuple[str, ...] = ()  # `match_on` key fields; () = fall back to edge_instance/id
    where_before: tuple[Condition, ...] = ()  # the prior state must satisfy these
    where_after: tuple[Condition, ...] = ()  # the new state must satisfy these
    where_change: tuple[Condition, ...] = ()  # these fields must have *changed* (+ optional new-value test)
    unconsumed: tuple[str, ...] = ()  # trigger keys this compile did not read (surfaced by explain())


def _parse_conditions(raw: Any, block: str) -> tuple[Condition, ...]:
    """Parse a ``where_*`` block into ``Condition``s. Fails loud on a malformed/unknown operator.

    Accepts one mapping or a list of them: ``{field, op?, value?}``. ``op`` defaults to ``eq`` when a
    ``value`` is given and ``exists`` when it is not (except in ``where_change``, where omitting ``op``
    means "changed at all"). Every operator is the DSL's — no new comparator vocabulary lives here.
    """
    if raw is None:
        return ()
    entries = raw if isinstance(raw, list) else [raw]
    out: list[Condition] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("field"):
            raise ValueError(f"{block} entry must be a mapping with a 'field': got {entry!r}")
        op = entry.get("op")
        if op is None and block != "where_change":
            op = "eq" if "value" in entry else "exists"
        if op is not None and op not in OPERATORS:
            raise ValueError(f"unknown {block} operator {op!r}; expected one of {sorted(OPERATORS)}")
        out.append(Condition(field=str(entry["field"]), op=op, value=entry.get("value")))
    return tuple(out)


def _parse_match_on(raw: Any) -> tuple[tuple[str, ...], str | None, list[str]]:
    """Split ``match_on`` into (grouping-key fields, tracked-state field, unrecognised tokens)."""
    if raw is None:
        return (), None, []
    tokens = [str(t) for t in (raw if isinstance(raw, list) else [raw])]
    keys: list[str] = []
    state: str | None = None
    unknown: list[str] = []
    for tok in tokens:
        if tok in MATCH_ON_KEY_FIELDS:
            field = MATCH_ON_KEY_FIELDS[tok]
            if field not in keys:
                keys.append(field)
        elif tok in MATCH_ON_STATE_FIELDS:
            state = state or MATCH_ON_STATE_FIELDS[tok]
        else:
            unknown.append(f"match_on:{tok}")
    return tuple(keys), state, unknown


def compile_trigger(trigger: dict[str, Any]) -> CompiledTrigger:
    """Compile a frozen ``trigger`` dict into a ``CompiledTrigger`` — generic, no per-observable code."""
    on = trigger.get("on")
    edge_type = trigger.get("edge_type")
    node_type = trigger.get("node_type")
    kind = "edge" if edge_type or on in {"new_edge"} else "node"
    label = trigger.get("label") or trigger.get("field") or edge_type or node_type or (on or "state")
    area = trigger.get("within_area")  # location seam: a node-candidate pre-filter (same primitive as geofence)

    group_by, match_state, unknown_tokens = _parse_match_on(trigger.get("match_on"))
    blocks = {b: _parse_conditions(trigger.get(b), b) for b in ("where_before", "where_after", "where_change")}
    # An explicit `field` always wins over the state implied by `match_on` (the analyst was specific).
    declared_state = trigger.get("field") or match_state

    def built(mode: str, kind_: str, type_filter: str | None, state_field: str | None, op: str | None,
              value: Any, geo: dict[str, Any] | None, reason: str | None, *reads: str) -> CompiledTrigger:
        consumed = _BASE_CONSUMED | set(reads)
        return CompiledTrigger(
            mode, kind_, type_filter, state_field, op, value, geo, label, reason, area,
            group_by=group_by, unconsumed=tuple(sorted(set(trigger) - consumed) + unknown_tokens),
            **blocks,
        )

    if on == "occupancy_state_change":
        # Occupancy = which site a unit is based-at; the state is the edge's target node.
        return built(CROSSING, "edge", edge_type, declared_state or "target", None, None, None, None,
                     "edge_type", "field")
    if on == "geofence_crossing":
        # Location seam (not demo-wired): fire when a watched node enters/leaves an area.
        return built(CROSSING, "node", node_type, None, None, None, trigger.get("area"), None,
                     "node_type", "area")
    if on == "state_change":  # generic crossing on any field
        return built(CROSSING, kind, edge_type or node_type, declared_state, None, None, None, None,
                     "edge_type", "node_type", "field")
    if on in {"new_edge", "new_node"}:
        return built(EXISTS, kind, edge_type or node_type, None, None, None, None, None,
                     "edge_type", "node_type")
    if on in OPERATORS:  # generic match: `on` is the comparator itself (eq / ge / exists / …)
        return built(MATCH, kind, edge_type or node_type, declared_state, on, trigger.get("value"),
                     None, None, "edge_type", "node_type", "field", "value")
    # Anything else is recognised but not a view-delta condition → arm-only (config-only, honest).
    reason = (
        f"trigger.on={on!r} is not a view-delta condition (e.g. new_claim lives in the evidence log, "
        "not the rebuilt view) — it arms but fires upstream of the view; see spine/09 honest boundary"
    )
    return built(ARM_ONLY, kind, edge_type or node_type, declared_state, None, None, None, reason,
                 "edge_type", "node_type", "field")


@dataclass(frozen=True)
class ScopeResolution:
    """The watch-scope **plus the diagnosis of how it was reached** (AH-1).

    ``node_ids`` is exactly what ``resolve_scope`` returns (``None`` = unscoped / match everything).
    The rest is what an analyst needs to tell "watching the right thing and quiet" apart from "watching
    nothing and quiet":

    * ``requested`` — every anchor string the observable declared (``watch_instances`` + its lens's).
    * ``resolved`` / ``resolution_via`` — the anchors that bound to a view node, and via which ladder rung.
    * ``missing`` — the anchors that bound to **nothing in this view**. Non-empty = part of what this
      tripwire claims to watch is not being watched.
    * ``watching_nothing`` — the scope is a real (non-``None``) set that contains **no** view node at
      all, so the tripwire is structurally incapable of firing. Its silence is not an all-clear.
    * ``warning`` — the analyst-facing sentence, ``None`` when every anchor resolved.
    """

    node_ids: set[str] | None
    requested: tuple[str, ...] = ()
    resolved: dict[str, str] | None = None
    resolution_via: dict[str, str] | None = None
    missing: tuple[str, ...] = ()
    watching_nothing: bool = False
    watched_node_count: int | None = None  # real view nodes in scope; None = unscoped (everything)
    warning: str | None = None

    @property
    def resolved_map(self) -> dict[str, str]:
        return dict(self.resolved or {})


def _scope_warning(missing: tuple[str, ...], scope: set[str] | None, watched: int) -> str:
    """The one sentence an analyst reads. Names the unresolved anchor and refuses to imply an all-clear.

    Three distinct failures, because they have opposite consequences and must not read alike:
    *unscoped* (the tripwire silently widened to the whole graph), *watching nothing* (it silently
    narrowed to nothing), and *partial* (part of what it claims to watch is unwatched).
    """
    named = ", ".join(missing)
    if scope is None:
        return (
            "this tripwire declares anchors that resolve to no node in the current view (unresolved: "
            f"{named}), so it has fallen back to UNSCOPED — it now evaluates every element in the graph "
            "rather than the subject you declared. Anything it fires is about the whole graph, not that "
            "subject. Correct the anchor id, or wait for coverage that creates that entity."
        )
    if watched == 0:
        return (
            "insufficient evidence to scope this tripwire: none of its declared anchors resolve to a "
            f"node in the current view (unresolved: {named}). It is watching nothing and cannot fire — "
            "its silence is NOT an all-clear. Correct the anchor id, or wait for coverage that creates "
            "that entity, then re-check."
        )
    return (
        f"this tripwire is watching {watched} node(s), but {len(missing)} declared anchor(s) did not "
        f"resolve to any node in the current view (unresolved: {named}). Whatever those anchors were "
        "meant to watch is NOT being watched, and silence about it is not an all-clear."
    )


def resolve_scope_detail(obs: ObservableDef, view: GraphView, config: ConfigBundle) -> ScopeResolution:
    """``resolve_scope`` + the diagnosis (see :class:`ScopeResolution`). The single scoping rule.

    Scope semantics are **identical** to the pre-AH-1 behaviour by construction (see the module
    docstring): the only change to ``node_ids`` is that a declared ``watch_instance`` now contributes the
    node id it actually **resolved to** instead of its raw config string. A raw string that is not a view
    node id could never match ``evaluator._watched`` (always a real node id), so it was inert — inert but
    *misleading*, because it made a broken anchor look present in the scope.
    """
    lens = config.subjects.as_map().get(obs.subject) if obs.subject else None
    watch: list[str] = list(obs.watch_instances)
    anchors: list[str] = list(watch)
    if lens is not None:
        anchors.extend(lens.anchors)
    if not anchors:
        return ScopeResolution(None)  # nothing declared to watch → unscoped, and nothing to diagnose

    hops = obs.trigger.get("anchors_within_hops")
    if hops is None:
        hops = lens.max_hops if lens is not None else 0

    # Same shared resolver the lens uses (literal → registry alias → alias class), so a watch-scope and a
    # lens can't diverge on which anchors "count as present" (AR-2). Unresolved is now *named*, not dropped.
    resolutions = resolve_anchors(anchors, view, config)
    resolved = {r.requested: r.node_id for r in resolutions if r.node_id is not None}
    via = {r.requested: r.via for r in resolutions if r.via is not None}
    missing = tuple(dict.fromkeys(r.requested for r in resolutions if r.node_id is None))
    present = [r.node_id for r in resolutions if r.node_id is not None]

    def diagnosed(scope: set[str] | None) -> ScopeResolution:
        node_ids = {n.id for n in view.nodes}
        # Count only ids that are *really* nodes in this view — a scope entry that is not a node can
        # never match ``evaluator._watched``, so counting it would restate the phantom in a number.
        watched = None if scope is None else len(scope & node_ids)
        watching_nothing = watched == 0
        warning = _scope_warning(missing, scope, watched or 0) if missing else None
        return ScopeResolution(
            scope, tuple(anchors), resolved, via, missing, watching_nothing, watched, warning
        )

    if not present:
        # Anchors declared but none present in this view. Keep only the explicit instances, else fall back
        # to unscoped rather than disarm (recall-biased; conflict resolved in MONITOR). Preserved
        # deliberately: `set() or None` here would mean "match EVERYTHING", a louder lie than silence.
        return diagnosed(set(watch) or None)

    und = nx.Graph()
    for n in view.nodes:
        und.add_node(n.id)
    for e in view.edges:
        und.add_edge(e.source, e.target)

    # Seed with the ids the watch instances RESOLVED to — never the raw config strings (the phantom).
    reach: set[str] = {resolved[w] for w in watch if w in resolved}
    for a in present:
        reach |= set(nx.single_source_shortest_path_length(und, a, cutoff=hops))
    return diagnosed(reach)


def resolve_scope(obs: ObservableDef, view: GraphView, config: ConfigBundle) -> set[str] | None:
    """In-scope node ids = (lens anchors ∪ ``watch_instances``) expanded by ``anchors_within_hops``.

    ``None`` = unscoped (evaluate everything): the lenient fallback when a lens is named but its anchors
    aren't in this view, so a tripwire is never silently disarmed (recall bias). ``watch_instances`` are
    always in scope. Hop bound and anchor set are all config, never literals (G6, G10). Callers that need
    to *report* an unresolved anchor use :func:`resolve_scope_detail` instead — same computation.
    """
    return resolve_scope_detail(obs, view, config).node_ids
