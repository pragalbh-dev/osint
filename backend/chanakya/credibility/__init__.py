"""CREDIBILITY stage — the Confidence Resolver + independence grouping + status machine (owned by SCORE).

F0 ships **trivial stubs** (no scoring): ``score_claims`` returns no credibilities, grouping is the
identity (one look per claim — never *over*-claiming corroboration), and ``assign_status`` assigns no
status. This keeps ``rebuild()`` running while SCORE fills the real bodies (per-claim
reliability×integrity×freshness, noisy-OR over independence groups, the 3-gate status machine —
spine/04, master §4.3).

**No magic numbers here (gate G6):** the real SCORE bodies read weights/thresholds/half-lives from
``config.credibility``. These stubs contain no scoring literals.

Frozen signatures:
    score_claims(resolved_claims, sources, config, decisions=None) -> {claim_id: claim_credibility}
    group_by_independence(claim_ids, claims, sources, config) -> [IndependenceGroup]
    assign_status(assertions, config) -> {element_id: AssertionAssessment}
"""

from __future__ import annotations

from chanakya.schemas import (
    AssertionAssessment,
    AssertionInput,
    ClaimRecord,
    ConfigBundle,
    DecisionRecord,
    IndependenceGroup,
    SourceRegistryEntry,
)


def score_claims(
    resolved_claims: list[ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    config: ConfigBundle,
    decisions: list[DecisionRecord] | None = None,
) -> dict[str, float]:
    """STUB: compute no per-claim credibilities yet. SCORE fills reliability×integrity×freshness.

    ``decisions`` (the replayed decision log, optional) is SCORE's channel for analyst integrity flags:
    an ``flag_origin`` effect must penalise **every** claim sharing that ``primary_origin_id`` — including
    claims ingested *after* the flag (the monitoring beat) — not just the flagged element. Additive &
    optional, so the existing ``rebuild()`` / API caller is unaffected (master §2 Rule 3).
    """
    return {}


def group_by_independence(
    claim_ids: list[str],
    claims: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    config: ConfigBundle,
) -> list[IndependenceGroup]:
    """STUB (identity): one group per claim — no collapsing, so no false corroboration is asserted.

    SCORE replaces this with 3-axis (origin/discipline/interest) clustering (§3.5).
    """
    return [
        IndependenceGroup(group_id=f"grp:{cid}", claim_ids=[cid])
        for cid in claim_ids
    ]


def assign_status(
    assertions: list[AssertionInput],
    config: ConfigBundle,
) -> dict[str, AssertionAssessment]:
    """STUB: assign no status / no confidence. SCORE fills the 3-gate machine (spine/04 §3.4)."""
    return {a.element_id: AssertionAssessment(element_id=a.element_id) for a in assertions}
