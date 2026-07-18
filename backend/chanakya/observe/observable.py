"""Compile a declarative ``ObservableDef`` into a working trigger + resolve its watch-scope.

Two jobs, both pure and config-driven:

* **``compile_trigger``** maps the frozen ``trigger`` dict (spine/08 §3.8) into a ``CompiledTrigger``
  the evaluator runs. Named ``on`` forms (``occupancy_state_change`` …) are sugar over three generic
  *modes* — **crossing** (state-change), **exists** (new element in the delta), **match** (a predicate
  becomes true). A recognised-but-not-view-delta trigger (e.g. ``new_claim``, which lives in the
  evidence log, not the view) compiles to ``arm-only`` — it still parses/arms, it just cannot fire off
  a view delta (spine/09 honest boundary). There is **no per-observable branch** — adding a tripwire is
  config only (gate G6 / the "declarative, not hardcoded" acceptance).
* **``resolve_scope``** turns ``subject`` (a lens: anchors + hop bound) **∪** ``watch_instances``
  (explicit resolved ids) into the set of in-scope node ids. ``anchors_within_hops`` comes from the
  trigger/lens (config), never a literal (G6). Returns ``None`` = unscoped (evaluate everything) — the
  lenient, recall-biased fallback when a named lens's anchors aren't present in this view (don't
  silently disarm the tripwire).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from chanakya.schemas import ConfigBundle, GraphView, ObservableDef

from .dsl import OPERATORS

# Modes the evaluator understands. "arm-only" = recognised + armable but not fireable from a view delta.
CROSSING, EXISTS, MATCH, ARM_ONLY = "crossing", "exists", "match", "arm-only"


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


def compile_trigger(trigger: dict[str, Any]) -> CompiledTrigger:
    """Compile a frozen ``trigger`` dict into a ``CompiledTrigger`` — generic, no per-observable code."""
    on = trigger.get("on")
    edge_type = trigger.get("edge_type")
    node_type = trigger.get("node_type")
    kind = "edge" if edge_type or on in {"new_edge"} else "node"
    label = trigger.get("label") or trigger.get("field") or edge_type or node_type or (on or "state")
    area = trigger.get("within_area")  # location seam: a node-candidate pre-filter (same primitive as geofence)

    if on == "occupancy_state_change":
        # Occupancy = which site a unit is based-at; the state is the edge's target node.
        return CompiledTrigger(CROSSING, "edge", edge_type, "target", None, None, None, label, None, area)
    if on == "geofence_crossing":
        # Location seam (not demo-wired): fire when a watched node enters/leaves an area.
        return CompiledTrigger(
            CROSSING, "node", node_type, None, None, None, trigger.get("area"), label, None, area
        )
    if on == "state_change":  # generic crossing on any field
        return CompiledTrigger(CROSSING, kind, edge_type or node_type, trigger.get("field"),
                               None, None, None, label, None, area)
    if on in {"new_edge", "new_node"}:
        return CompiledTrigger(EXISTS, kind, edge_type or node_type, None, None, None, None, label, None, area)
    if on in OPERATORS:  # generic match: `on` is the comparator itself (eq / ge / exists / …)
        return CompiledTrigger(MATCH, kind, edge_type or node_type, trigger.get("field"),
                               on, trigger.get("value"), None, label, None, area)
    # Anything else is recognised but not a view-delta condition → arm-only (config-only, honest).
    reason = (
        f"trigger.on={on!r} is not a view-delta condition (e.g. new_claim lives in the evidence log, "
        "not the rebuilt view) — it arms but fires upstream of the view; see spine/09 honest boundary"
    )
    return CompiledTrigger(ARM_ONLY, kind, edge_type or node_type, trigger.get("field"),
                           None, None, None, label, reason, area)


def resolve_scope(obs: ObservableDef, view: GraphView, config: ConfigBundle) -> set[str] | None:
    """In-scope node ids = (lens anchors ∪ ``watch_instances``) expanded by ``anchors_within_hops``.

    ``None`` = unscoped (evaluate everything): the lenient fallback when a lens is named but its anchors
    aren't in this view, so a tripwire is never silently disarmed (recall bias). ``watch_instances`` are
    always in scope. Hop bound and anchor set are all config, never literals (G6, G10).
    """
    lens = config.subjects.as_map().get(obs.subject) if obs.subject else None
    anchors: list[str] = list(obs.watch_instances)
    if lens is not None:
        anchors.extend(lens.anchors)
    if not anchors:
        return None  # nothing declared to watch → unscoped

    hops = obs.trigger.get("anchors_within_hops")
    if hops is None:
        hops = lens.max_hops if lens is not None else 0

    und = nx.Graph()
    for n in view.nodes:
        und.add_node(n.id)
    for e in view.edges:
        und.add_edge(e.source, e.target)

    present = [a for a in anchors if a in und]
    if not present:
        # anchors declared but none present in this view — keep only the explicit instances, else
        # fall back to unscoped rather than disarm (recall-biased; conflict resolved in MONITOR).
        return set(obs.watch_instances) or None

    reach: set[str] = set(obs.watch_instances)
    for a in present:
        reach |= set(nx.single_source_shortest_path_length(und, a, cutoff=hops))
    return reach
