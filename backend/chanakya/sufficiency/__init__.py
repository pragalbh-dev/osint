"""SUFFICIENCY stage — evidence-requirement templates → satisfied / Known Gap (owned by SCORE).

Real template evaluation (``checker.check``, re-exported here for the pipeline's frozen import): for each
assertion it checks whether the required *kinds* of evidence are present (``config.templates``); a failure
carries ``missing_slots`` + a generated ``next_coverage_due`` (from the providing source's ``cadence``) +
the ``observability_ceiling``, which the pipeline turns into a first-class Known Gap with a deterministic
templated refusal — the mechanism of the non-negotiable (spine/04 §3.7, gate G8). No LLM (gate G1).

Frozen signature: ``check(assertion, claims, config) -> SufficiencyEval``.
"""

from __future__ import annotations

from .checker import check

__all__ = ["check"]
