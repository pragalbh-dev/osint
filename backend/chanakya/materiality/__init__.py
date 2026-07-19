"""MATERIALITY stage — precompute filterable node attrs inside ``rebuild()`` (owned by SCORE).

Real chokepoint/substitutability computation (``precompute.precompute``, re-exported here). Runs **once
per rebuild**, last (after status), and materialises the attrs the retrieval tools filter on —
``chokepoint_count`` / ``chokepoint_status`` / ``substitutability_state`` (spine/09; C/01 criteria
#1/#4/#6/#7/#10), each carrying its contributing claim/edge IDs. Pure graph computation over the scored
view — no LLM (gate G1); config-driven, no scoring literals (gate G6). UNKNOWN substitutability renders
as *candidate* + a Known Gap, never as a confirmed sole-source.

Frozen signature: ``precompute(view, config) -> GraphView``.
"""

from __future__ import annotations

from .precompute import precompute

__all__ = ["precompute"]
