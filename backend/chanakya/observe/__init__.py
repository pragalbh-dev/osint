"""OBSERVE stage — the declarative observable/tripwire evaluator (owned by session MONITOR).

Runs **after** ``rebuild()`` over the view (and the previous view for state-change deltas): evaluates
each armed observable (a DSL condition over existing view attrs + precomputed materiality metrics) and
emits ``Alert`` objects (spine/08 §3.8, spine/09). Not inside the pure rebuild — it consumes the
rebuilt view; no LLM/network here.

Public surface:

* ``evaluate(prev_view, view, config) -> [Alert]`` — the frozen entrypoint: fire on the view delta.
* ``arm(observable, view, config) -> [Alert]`` — arm-on-save read-only pass + back-scan.
* ``explain(observable, view=None, config=None) -> dict`` — how an observable compiles (mode, scope,
  arm-only reason) and, given a view, whether its anchors actually resolve (AH-1).
* ``anchor_diagnostics(config, view) -> [dict]`` — every armed observable whose anchors do **not** all
  resolve; the API/SPA-facing "this tripwire is watching nothing" statement.
* ``read_dispositions(records) -> {observable_id: DispositionStats}`` — read HITL dispositions back
  for tripwire tuning (consumption side; HITL owns the writeback).

The DSL grammar (``dsl``) and trigger compiler (``observable``) carry no scoring literals — operators,
thresholds, severities, hop bounds all come from config (gate G6).
"""

from __future__ import annotations

from chanakya.schemas import Alert  # re-export: the fired-tripwire object (product/03 F)

from .disposition import DispositionStats, read_dispositions
from .dsl import OPERATORS, evaluate_condition, within_area
from .evaluator import anchor_diagnostics, arm, evaluate, explain
from .observable import (
    CompiledTrigger,
    ScopeResolution,
    compile_trigger,
    resolve_scope,
    resolve_scope_detail,
)

__all__ = [
    "evaluate",
    "arm",
    "explain",
    "anchor_diagnostics",
    "read_dispositions",
    "DispositionStats",
    "compile_trigger",
    "resolve_scope",
    "resolve_scope_detail",
    "ScopeResolution",
    "CompiledTrigger",
    "evaluate_condition",
    "within_area",
    "OPERATORS",
    "Alert",
]
