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


class Partition(Record):
    """RESOLVE's output: which claim resolves to which entity/edge instance + the merge decisions.

    ``merge_confidence`` (identity) is a **separate object** from any truth confidence — it rides the
    same-as edge and is never fed into ``assertion_confidence`` (gate G5).
    """

    resolved_ref: dict[str, ResolvedRef] = {}  # claim_id → resolved_ref
    same_as: list[tuple[str, str]] = []  # accepted merges: (entity_id, entity_id)
    distinct_from: list[tuple[str, str]] = []  # explicit do-not-merge (FD-2000 ≠ FT-2000)
    merge_confidence: dict[str, float] = {}  # "<a>|<b>" same-as edge key → identity confidence


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
