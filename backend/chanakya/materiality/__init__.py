"""MATERIALITY stage — precompute filterable node attrs inside ``rebuild()`` (owned by SCORE).

Materiality logic runs **once per rebuild** and materialises node attributes the retrieval tools
filter on: ``chokepoint_count`` / ``chokepoint_status`` / ``substitutability_state`` (spine/09; C/01
criteria #1/#4/#6/#7). Because it runs inside the pure rebuild, a config change recomputes it
automatically (hot-config). It does **not** call an LLM — pure graph computation (gate G1).

F0 ships a **trivial stub**: return the view unchanged (no materiality attrs). SCORE fills the real
chokepoint/substitutability computation. **No magic numbers here (gate G6):** the criteria/gates are
config-driven in the real body.

Frozen signature: ``precompute(view, config) -> GraphView``.
"""

from __future__ import annotations

from chanakya.schemas import ConfigBundle, GraphView


def precompute(view: GraphView, config: ConfigBundle) -> GraphView:
    """STUB (identity): leave materiality attrs unset. SCORE computes chokepoint/substitutability."""
    return view
