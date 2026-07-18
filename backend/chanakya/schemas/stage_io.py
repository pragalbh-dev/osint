"""Intermediate types passed between ``rebuild()`` stages — **frozen so stages compose cleanly**.

These live in ``schemas/`` (F0-owned) precisely so that both ``view/rebuild`` and each stage package
(``resolve``, ``credibility``, ``sufficiency``, ``materiality``) import the *same* types and never
depend on each other's code (master §2 conflict-freedom). The stage signatures in §4.3 are
"illustrative"; these are the concrete, frozen forms.
"""

from __future__ import annotations

from typing import Literal

from .base import Record
from .claim import ResolvedRef
from .view import Freshness, IndependenceGroup, Status, SufficiencyEval


def pair_key(a: str, b: str) -> str:
    """Order-independent key for a merge pair → indexes ``merge_confidence`` / ``merge_breakdown``.

    Sorted so ``(a, b)`` and ``(b, a)`` collide and the key is deterministic (gate G2).
    """
    return "|".join(sorted((a, b)))


class Partition(Record):
    """RESOLVE's output: which claim resolves to which entity/edge instance + the merge decisions.

    Three tiers of decision: ``same_as`` (ACCEPTED merges — effected by a shared ``resolved_ref`` so
    the members collapse to one node; provenance stamped on that node), ``candidates`` (HITL-band
    pairs kept separate → rendered as candidate ``same-as`` edges for an analyst to adjudicate), and
    ``distinct_from`` (explicit do-not-merge — a hard veto applied before banding).

    ``merge_confidence``/``merge_breakdown`` (identity) are a **separate object** from any truth
    confidence — they ride the same-as edge and are never fed into ``assertion_confidence`` (gate G5).
    Index both by :func:`pair_key`.
    """

    resolved_ref: dict[str, ResolvedRef] = {}  # claim_id → resolved_ref (shared entity_id ⇒ collapse to one node)
    same_as: list[tuple[str, str]] = []  # accepted merges (member, canonical) — collapse via resolved_ref
    candidates: list[tuple[str, str]] = []  # HITL-band pairs kept separate → candidate same-as edges + review queue
    distinct_from: list[tuple[str, str]] = []  # explicit do-not-merge (FD-2000 ≠ FT-2000) — hard veto before banding
    merge_confidence: dict[str, float] = {}  # pair_key(a, b) → identity confidence (same_as + candidates)
    merge_breakdown: dict[str, dict[str, float]] = {}  # pair_key(a, b) → {attribute, relational, temporal_consistency, source_asserted, total}


class AssertionInput(Record):
    """One assertion (a resolved node/edge/event) fed to ``assign_status``/``check``.

    Carries the per-claim credibilities + the independence groups (the master's ``groups`` arg,
    embedded per-assertion) + the deception gates that cap status at *probable* (§3.4).
    """

    element_id: str
    element_kind: Literal["node", "edge", "event"]
    per_claim_credibility: dict[str, float] = {}
    groups: list[IndependenceGroup] = []
    opposing_claims: list[str] = []
    has_unresolved_contradiction: bool = False
    gate_flags: list[str] = []  # e.g. "adversary-denial", "decoy-risk" → cap at probable, never confirm
    freshness: Freshness | None = None
    sufficiency: SufficiencyEval | None = None


class AssertionAssessment(Record):
    """``assign_status`` output: ``{assertion_confidence, gate_vector, status}`` (master §4.3)."""

    element_id: str
    assertion_confidence: float | None = None  # noisy-OR over independence groups (truth)
    status: Status | None = None  # set only here (the status machine) — G5
    gate_vector: list[str] = []  # which gates fired (caps/contradiction/freshness), for the drawer
