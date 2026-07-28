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
    # pair_key(a, b) → analyst-facing rationale, populated ONLY for a candidate that was RAISED by a
    # below-floor critical-attribute conflict (D5 take-care a, Stage 3A): the difference is on a declared-
    # critical attribute but is not credibly attested (below ``critical_veto_min_grade``), so instead of
    # walling the pair the resolver hands it to a human with the reason. Empty for every ordinary scored
    # candidate ⇒ byte-unchanged where no such raise fired.
    candidate_reasons: dict[str, str] = {}  # pair_key(a, b) → why a below-floor critical conflict was raised
    # D4 Stage 2 — identity as a three-status hypothesis. ``possible`` is the retained watch-list: pairs
    # scored in ``[possible_floor, hitl_low)`` that today would be dropped as ``separate``. Kept as latent
    # links (their ``merge_confidence``/``merge_breakdown`` still ride the same dicts) so the unresolved tail
    # is neither a false merge nor a lonely singleton — the antidote to fragmentation. **In-memory ONLY**:
    # never rendered as a wire edge (unlike ``candidates``), so the drawn view JSON is byte-unchanged. The
    # status label for any identity link (confirmed / probable / possible) is :meth:`identity_status`.
    possible: list[tuple[str, str]] = []  # retained sub-HITL identity links (watch-list) — NOT drawn
    distinct_from: list[tuple[str, str]] = []  # explicit do-not-merge (FD-2000 ≠ FT-2000) — hard veto before banding
    # pair_key(a, b) → what is MISSING before the identity of a pair the evidence otherwise FUSED can be
    # settled (G19). The escalate half of the non-negotiable, for the one refusal that reached nobody: the
    # cross-type wall un-fuses a pair and routes *neither* mention anywhere — no edge, no queue item, and
    # (before this) no gap either, which is indistinguishable from two mentions that never resembled each
    # other. ``rebuild()`` renders one Known Gap PER ENDPOINT, so each node states in its own drawer what
    # could not be decided about it and what would settle it. Only for pairs the evidence otherwise fused: a
    # low-scoring cross-type coincidence is noise and earns nothing (T3b-A).
    identity_refusals: dict[str, str] = {}
    # pair_key(a, b) → what is MISSING for a pair a cap withheld from the analyst's QUEUE while the ground for
    # withholding it came from a SOURCE's own statement. The escalate half for a triage decision that removes
    # the queue item: `contrast_ceiling: possible` refuses the fusion (right) and files the pair on the silent
    # watch-list (wrong — a document going out of its way to distinguish two things the score says are one is
    # either an extraction error or deception, and both are findings). Rendered as one Known Gap PER ENDPOINT,
    # exactly like ``identity_refusals`` — but deliberately a SEPARATE channel, because this one must NOT touch
    # the node's status: the pair being held apart is the correct outcome and neither node is unassessable.
    # Empty on the shipped config (`contrast_ceiling: probable` ⇒ the pair keeps its queue place).
    withheld_escalations: dict[str, str] = {}
    # pair_key(a, b) → why a hard WALL holds this pair apart, in words an analyst can act on (G18, S3).
    # A curated ``distinct_from`` needs no explanation — an analyst wrote it. A wall the system *derived*
    # does: a stated relationship conflict at overlapping times is a finding, and a finding with no stated
    # grounds is indistinguishable from a missing edge. Empty for every curated/structural veto ⇒ the drawn
    # edge keeps its existing generic reason and the view JSON is byte-unchanged (gate G2).
    wall_reasons: dict[str, str] = {}
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
    # RK-NAMECUT/N1 — the sibling of ``endpoint_node_types`` for the other half of a materialised endpoint:
    # what to CALL it. The view used to unwrap the designator out of an ``ent:<type>:<form>`` id and, failing
    # that, render the id itself as the node's name — a reader parsing an opaque handle, and an analyst shown
    # a key where a name belongs. The elected surface form is stated here instead, keyed by the post-merge id
    # the view draws, so an id may be re-keyed without renaming anything. Empty ⇒ every endpoint was
    # claim-backed and already named (gate G2).
    display_label: dict[str, str] = {}  # canonical entity id → the designator to SHOW for it
    # RK-NAMECUT/N1 — pair_key → the two ids it was built from. Every dict above is keyed by a JOINED string
    # ("a|b") and the Known-Gap rendering used to recover the endpoints by splitting it back, which is lossy
    # the moment an id contains the join character (an id built from a document's own surface form carries
    # whatever punctuation that document used). The key stays exactly as it was — it is quoted in the gap's
    # own id, so it is analyst-visible state — and the ids ride alongside it.
    pair_members: dict[str, tuple[str, str]] = {}
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
