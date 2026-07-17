"""SUFFICIENCY stage — evidence-requirement templates → satisfied / Known Gap (owned by SCORE).

F0 ships a **trivial stub**: every assertion is reported ``satisfied`` with no missing slots (the
skeleton detects no gaps). SCORE replaces this with real template evaluation that emits first-class
Known Gap nodes with ``missing_slots`` + ``next_coverage_due`` + ``observability_ceiling`` — the
mechanism of the non-negotiable (spine/04 §3.7, gate G8). The refusal statement is a fill-in-the-blank
template (``config.templates``), never regenerated prose (§3.11).

Frozen signature: ``check(assertion, claims, config) -> SufficiencyEval``.
"""

from __future__ import annotations

from chanakya.schemas import AssertionInput, ClaimRecord, ConfigBundle, SufficiencyEval


def check(
    assertion: AssertionInput,
    claims: dict[str, ClaimRecord],
    config: ConfigBundle,
) -> SufficiencyEval:
    """STUB: report satisfied (no gap known). SCORE evaluates the real templates + emits Known Gaps."""
    return SufficiencyEval(satisfied=True)
