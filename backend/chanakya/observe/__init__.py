"""OBSERVE stage — the declarative observable/tripwire evaluator (owned by session MONITOR).

Runs **after** ``rebuild()`` over the view (and the previous view for state-change deltas): evaluates
each armed observable (a DSL condition over existing attrs + precomputed metrics) and emits ``Alert``
objects (spine/08 §3.8, spine/09). Not inside the pure rebuild — it consumes the rebuilt view.

F0 ships a **trivial stub**: no observables fire. MONITOR fills the DSL evaluator + armed-registry +
the seeded Rawalpindi→Rahwali relocation tripwire. **No magic numbers here (gate G6).**

Frozen signature: ``evaluate(prev_view, view, config) -> [Alert]``.
"""

from __future__ import annotations

from chanakya.schemas import Alert, ConfigBundle, GraphView


def evaluate(
    prev_view: GraphView | None,
    view: GraphView,
    config: ConfigBundle,
) -> list[Alert]:
    """STUB: fire nothing. MONITOR evaluates ``config.observables`` against the view delta."""
    return []
