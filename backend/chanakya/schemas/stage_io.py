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


class PlaceRef(Record):
    """RESOLVE's gazetteer match for one entity — the *evidence* for a place binding, not just a pointer.

    ``distance_m``/``band``/``via`` ride along because they are what makes the binding auditable:
    "snapped to Rahwali from 16 m on its own name" and "pulled to it from 2.8 km on coordinates alone"
    are different claims, and an analyst has to be able to tell them apart before trusting a location.

    Only **curated** gazetteer anchors (``config/places.yaml``) are ever referenced. A mention that
    matches no anchor gets no ``PlaceRef`` at all and keeps its own raw coordinate — an honest pin,
    not a failure; growing the gazetteer is an analyst promotion, never a machine mint (D-P3.3).
    """

    place_id: str  # an existing config/places.yaml anchor — never auto-minted
    band: str  # "auto" (inside the class radius / hard-ID / toponym) | "hitl" (within the multiplier)
    distance_m: float | None = None  # geodesic metres to the anchor; None when matched without a coord
    via: str = ""  # "hard-id" | "toponym" | "proximity" — which evidence carried the match


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
    # D4 Stage 2 — identity as a three-status hypothesis. ``possible`` is the retained watch-list: pairs
    # scored in ``[possible_floor, hitl_low)`` that today would be dropped as ``separate``. Kept as latent
    # links (their ``merge_confidence``/``merge_breakdown`` still ride the same dicts) so the unresolved tail
    # is neither a false merge nor a lonely singleton — the antidote to fragmentation. **In-memory ONLY**:
    # never rendered as a wire edge (unlike ``candidates``), so the drawn view JSON is byte-unchanged. The
    # status label for any identity link (confirmed / probable / possible) is :meth:`identity_status`.
    possible: list[tuple[str, str]] = []  # retained sub-HITL identity links (watch-list) — NOT drawn
    distinct_from: list[tuple[str, str]] = []  # explicit do-not-merge (FD-2000 ≠ FT-2000) — hard veto before banding
    merge_confidence: dict[str, float] = {}  # pair_key(a, b) → identity confidence (same_as + candidates)
    merge_breakdown: dict[str, dict[str, float]] = {}  # pair_key(a, b) → {attribute, relational, temporal_consistency, source_asserted, total}
    # The claims *behind* the ``source_asserted`` term — who actually wrote "these two are the same".
    # An identity assertion is consumed as a merge signal rather than drawn as an edge (D-2.5), so this
    # is the only route from an adjudication back to the sentence. Rendered onto the candidate same-as
    # edge's ``claim_ids``, so ``GET /evidence/{edge_id}`` serves it through the existing route (the
    # one-click-to-source non-negotiable). Absent for every pair no source spoke about — never a stand-in.
    identity_claims: dict[str, list[str]] = {}  # pair_key(a, b) → asserting claim ids (replay order)
    # Edges attach to nodes by the RAW triple subject/object string (supersede.py), not by resolved_ref —
    # so a raw endpoint mention would dangle. This maps every resolvable entity ref → its canonical id,
    # for BOTH a merged cluster member (``ent:type:name`` ref) AND a raw triple-endpoint mention (the LLM
    # surface string a triple used for subject/object — RES-1 endpoint-as-mention). rebuild()/_assemble
    # applies it to triple endpoints so a merge/mention reconnects edges to the resolved typed node.
    # Empty ⇒ no-op. (P3.1 broadened this from "merged refs only" to "canonical id for any ref".)
    entity_canonical: dict[str, str] = {}  # raw entity ref OR endpoint mention → canonical entity id
    # RES-1: a triple endpoint the ontology could TYPE (via edge domain/range) but that no entity-form
    # claim ever created a node for is minted here as a TYPED node, never ``unknown``. Maps a resolved
    # (post-merge) canonical id → its ontology node type, so _assemble types the minted endpoint node
    # from the edge instead of falling back to ``unknown``. Empty ⇒ every endpoint had a claim-backed node
    # (or was un-typable) ⇒ view unchanged (gate G2). Provenance for such a node is the triple's claim_ids.
    endpoint_node_types: dict[str, str] = {}  # canonical entity id → ontology node type (minted endpoints)
    # RES-3: the place-resolution channel. ``resolve_place`` always computed a match and threw it away,
    # so ``Location.resolved_place_ref`` — declared "filled by RESOLVE", read by observe/dsl.py and the
    # map — had a reader and no writer. Keyed by the POST-merge canonical entity id so ``rebuild()`` can
    # stamp it straight onto the node. Empty ⇒ nothing matched a curated anchor ⇒ view unchanged (G2).
    place_refs: dict[str, PlaceRef] = {}  # canonical entity id → its curated-gazetteer anchor + evidence

    def identity_status(self, a: str, b: str) -> str | None:
        """The three-status label for an identity link (D4): ``confirmed`` | ``probable`` | ``possible``.

        ``confirmed`` — an accepted merge (in :attr:`same_as`, collapsed to one node); ``probable`` — a
        HITL candidate ``same-as`` edge (in :attr:`candidates`); ``possible`` — a retained sub-review link
        (in :attr:`possible`, the watch-list). ``None`` when the resolver never linked the two. Membership
        is order-independent. This is the derived status axis Stage 3C (link weighting) and Stage 4
        (coverage) consume; it *reports*, it draws nothing.
        """
        pair = frozenset((a, b))
        if any(frozenset(p) == pair for p in self.same_as):
            return "confirmed"
        if any(frozenset(p) == pair for p in self.candidates):
            return "probable"
        if any(frozenset(p) == pair for p in self.possible):
            return "possible"
        return None


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
