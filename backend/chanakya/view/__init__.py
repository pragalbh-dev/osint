"""The view layer — ``rebuild()`` orchestration, supersede/contradict, lens scoping, JSON export.

All four are F0-owned. ``rebuild()`` is the pure reduction; the other three are real (not stubbed)
per master §4.3. The five *stages* rebuild calls (``resolve``/``score_claims``/``assign_status``/
``check``/``precompute``) live in their own packages and are stubbed by F0, filled by Wave-1.
"""

from __future__ import annotations

from .export import sorted_view, view_to_dict, view_to_json
from .lens import apply_lens
from .pipeline import apply_decision_effects, apply_retractions, rebuild

__all__ = [
    "rebuild",
    "apply_retractions",
    "apply_decision_effects",
    "apply_lens",
    "sorted_view",
    "view_to_dict",
    "view_to_json",
]
