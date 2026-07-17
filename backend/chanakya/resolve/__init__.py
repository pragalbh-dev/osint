"""RESOLVE stage — iterative relational entity resolution (owned by session RESOLVE).

F0 ships a **trivial identity stub**: each claim resolves to its own ``resolved_ref`` (taken from the
claim if the extractor set one, else synthesised deterministically), with **no** merges. This lets
``rebuild()`` run end-to-end today; RESOLVE replaces the body with candidate-gen + ``merge_score`` +
bands + bootstrap→fixpoint (master §4.3, spine/03).

Frozen signature: ``resolve(claims, config, prev_view) -> Partition``.
"""

from __future__ import annotations

from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView, Partition, ResolvedRef


def _identity_ref(claim: ClaimRecord) -> ResolvedRef:
    """A stable per-claim resolved_ref when the extractor left one unset (no merging performed)."""
    if claim.resolved_ref is not None:
        return claim.resolved_ref
    # Deterministic, string-free-of-designators: key off the structured payload, not raw text.
    p = claim.payload
    if p.form == "entity":
        return ResolvedRef(entity_id=f"ent:{p.entity_type}:{p.name}")
    if p.form == "triple":
        return ResolvedRef(entity_id=f"ent:{p.subject}", edge_instance=f"edge:{p.subject}:{p.predicate}:{p.object}")
    # form == "event": key by claim so distinct events never collide (RESOLVE merges the real ones)
    return ResolvedRef(entity_id=f"event:{p.event_type}:{claim.claim_id}")


def resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
) -> Partition:
    """STUB (identity): resolve each claim to itself; assert no merges. RESOLVE fills the real body."""
    resolved_ref = {c.claim_id: _identity_ref(c) for c in claims}
    return Partition(resolved_ref=resolved_ref)
