"""The supersession floor — D-P4.4 condition (iv), the post-status half of the relocation beat.

``view/supersede.py`` decides *ordering*: which of two assertions on one resolved edge instance is the
newer one. That is only three of the rule's four conditions. The fourth is a **quality floor on the
newer claim**, and it is what stops a supersession from being a free deletion primitive:

    (iv) the newer assertion must independently reach ≥ ``min_band`` on ≥ ``min_independent_looks``
         independent looks, with a clean deception gate.

Without it, *any* newer claim retires an older one — so one grade-E post asserting "the battery has
left" quietly retires a confirmed position, and the graph reports the adversary's preferred answer with
no alarm anywhere. ``d20_supersede_spoof`` (grade E, ``bias_vector: adversary``, ``decoy_risk_flag``) is
in the corpus for exactly that attack; it must be defeated by a *gate*, not by the accident that it
currently emits no relationship claim.

**Why this lives here and not in `view/supersede.py`.** Supersede runs at ``rebuild()`` step 2, *before*
``score_claims`` and ``assign_status`` — there is no confidence to gate on yet. So supersede emits an
ordered *candidate* pair and this pass, run immediately after the status machine, promotes it:

* **cleared** → the real ``superseded_by`` / ``supersedes`` link is written, the older assertion is
  re-run through the status machine carrying :data:`~chanakya.credibility.status.SUPERSEDED` (→ *stale*,
  not *insufficient* — it is history, not a gap: product/02 §7), and the relocation is **drawn** as a
  ``supersedes`` edge between the two objects (D-P4.11) so an analyst can see and click it.
* **held** → nothing is retired. The pair keeps ``candidate_supersede`` and goes to the analyst, which
  per D-P4.4 is the **default** outcome, not the exception (recall-biased triage, spine/05).

Pure and config-driven (gates G1/G2/G6): every number comes from ``config.credibility.supersede_floor``;
an **absent** floor block retires nothing (fail-closed — a missing safety gate must not read as an open
one). The status label is still written by ``assign_status`` alone (gate G5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chanakya.schemas import AssertionInput, ConfigBundle, EdgeView, NodeView

from .status import SUPERSEDED, assign_status

# ── the candidate-pair vocabulary, shared with ``view/supersede.py`` (its producer) ────────────
# Defined here because this module is the semantic owner of the gate, and because the dependency runs
# this way round without a cycle (``view`` already imports ``credibility``, never the reverse).
CANDIDATE = "candidate_supersede"  # this edge is half of an unadjudicated supersession → HITL
PENDING_NEWER = "supersede_pending_newer"  # on the OLDER edge: id of the newer edge nominated to retire it
PENDING_OLDER = "supersede_pending_older"  # on the NEWER edge: ids of the older edges it may retire
GATE = "supersede_gate"  # "pending" (supersede.py) → "promoted" / "held" (this pass)
GATE_PENDING = "pending"

# Attr vocabulary written by this pass (strings, never numbers — G6).
GATE_PROMOTED = "promoted"
GATE_HELD = "held"
HOLD_REASON = "supersede_hold_reason"  # on both edges of a held pair — why the analyst is being asked
DERIVED_VIA = "derived_via"  # on the drawn edge: which mechanism minted it
_DRAWN_EDGE_TYPE = "supersedes"  # declared in config/ontology.yaml (freshness_class n/a, symmetric)
_DRAWN_VIA = "supersede"

# Floor keys (all read from config.credibility.supersede_floor; see config/credibility.yaml).
_MIN_BAND = "min_band"  # names a key in credibility.thresholds — never a bare number here
_MIN_LOOKS = "min_independent_looks"
_BLOCKING = "blocking_gate_flags"
_ALLOWED_STATUS = "newer_status_allow"
# R1.4 — the EARNED-IDENTITY gate on the promotion (see :func:`_identity_failures`).
_REQUIRE_EARNED = "require_earned_identity"
_MIN_IDENTITY_CONF = "min_identity_confidence"
_RESOLVED_FROM = "resolved_from"       # the accepted-merge audit trail view/pipeline stamps on a node
_MERGE_CONFIDENCE = "merge_confidence"
_PROVISIONAL = "provisional"           # a build-materialized instance: identity not earned, by definition


@dataclass
class SupersedeOutcome:
    """What the pass did — returned so ``rebuild()`` can render it without re-deriving it."""

    drawn_edges: list[EdgeView] = field(default_factory=list)
    retired_element_ids: list[str] = field(default_factory=list)  # older edges now *stale*
    held_pairs: list[tuple[str, str]] = field(default_factory=list)  # (older, newer) still for HITL


def _floor(config: ConfigBundle) -> dict[str, object] | None:
    floor = getattr(config.credibility, "supersede_floor", None)
    return floor if isinstance(floor, dict) else None


def _effective_looks(edge: EdgeView) -> float:
    """The newer assertion's weighted independent-look count — the same measure the status machine uses."""
    return sum(g.weight for g in edge.supporting_claims)


def _gate_flags(edge: EdgeView) -> set[str]:
    return set(edge.confidence.integrity_flags) if edge.confidence is not None else set()


def _floor_failures(newer: EdgeView, floor: dict[str, object], config: ConfigBundle) -> list[str]:
    """Every reason the newer assertion is not yet allowed to retire an older one (empty ⇒ it may)."""
    failures: list[str] = []

    band = floor.get(_MIN_BAND)
    cut = config.credibility.thresholds.get(str(band)) if isinstance(band, str) else None
    conf = newer.confidence.assertion_confidence if newer.confidence is not None else None
    if cut is None or conf is None or conf < cut:
        failures.append(f"newer-below-{band}")

    allowed = floor.get(_ALLOWED_STATUS)
    if isinstance(allowed, (list, tuple)) and newer.status not in {str(s) for s in allowed}:
        failures.append(f"newer-status-{newer.status}")

    min_looks = floor.get(_MIN_LOOKS)
    if isinstance(min_looks, (int, float)) and _effective_looks(newer) < float(min_looks):
        failures.append("newer-too-few-independent-looks")

    blocking = floor.get(_BLOCKING)
    if isinstance(blocking, (list, tuple)):
        hit = sorted(_gate_flags(newer) & {str(f) for f in blocking})
        failures.extend(f"newer-deception-gate:{f}" for f in hit)

    return failures


def _identity_failures(
    older: EdgeView,
    newer: EdgeView,
    nodes: dict[str, NodeView] | None,
    floor: dict[str, object],
    config: ConfigBundle,
) -> list[str]:
    """R1.4 — every reason this promotion is not the machine's to make (empty ⇒ it may proceed).

    **The chain this closes.** Two co-located batteries with no designations look nearly identical to the
    identity judge, so a formation merge is the path of least resistance. ``based-at`` is functional and
    keyed on the unit, so the moment they fuse their two distinct sites become *one unit's before and
    after*. This pass then clears the credibility floor on the newer of the two, sets the supersede link,
    **pops the pair out of the analyst's queue** — "adjudicated by the machine" — and, because the targets
    differ, **draws a relocation edge**. One identity error therefore becomes a positively-asserted movement
    assessment the analyst is never asked about: the non-negotiable breached without any component lying.

    Machine promotion is legitimate only over an identity the system actually **earned**. So the gate is
    scoped exactly where the harm is — a promotion that would **draw** a relocation across *differing*
    targets — and it holds when the subject is:

    * a **provisional** instance (build-materialized: there is no earned identity to rest on at all); or
    * a node resting on a merge recorded **below** ``min_identity_confidence``.

    A never-merged, single-claim subject is *not* caught: no identity decision was taken, so there is none
    to distrust — gating that would stop every honest relocation and teach the analyst to ignore the queue.
    Holding is not a refusal: the pair keeps ``candidate_supersede`` and goes to the analyst, which
    D-P4.4 already makes the default outcome. The co-location-specific half of this (making such a merge
    fail to *fuse* in the first place) is the identity layer's job — this is the downstream backstop that
    makes the failure survivable rather than fabricating on top of it.
    """
    if not bool(floor.get(_REQUIRE_EARNED)):
        return []
    if newer.target == older.target:
        return []  # a same-target refresh asserts no movement; there is nothing to fabricate
    node = (nodes or {}).get(newer.source)
    if node is None:
        return []
    if node.attrs.get(_PROVISIONAL):
        return ["subject-identity-provisional"]
    cut = floor.get(_MIN_IDENTITY_CONF)
    if not isinstance(cut, (int, float)):
        return []
    weak: list[str] = []
    for entry in node.attrs.get(_RESOLVED_FROM, []) or []:
        if not isinstance(entry, dict):
            continue
        conf = entry.get(_MERGE_CONFIDENCE)
        if isinstance(conf, (int, float)) and conf < float(cut):
            weak.append(str(entry.get("merged_ref", "?")))
    if weak:
        return [f"subject-identity-sub-confirmed:{ref}" for ref in sorted(weak)]
    return []


def _restate(older: EdgeView, config: ConfigBundle) -> None:
    """Re-run the status machine over the retired assertion with the ``superseded`` flag set.

    The machine keeps sole ownership of the label (gate G5): this pass adds one gate flag and asks for a
    verdict, exactly as the pipeline does. Same inputs ⇒ same ``assertion_confidence``; only the label
    (and the gate vector the provenance drawer renders) moves.
    """
    flags = sorted(_gate_flags(older) | {SUPERSEDED})
    a = AssertionInput(
        element_id=older.id,
        element_kind="edge",
        per_claim_credibility=dict(older.confidence.per_claim_credibility) if older.confidence else {},
        groups=list(older.supporting_claims),
        opposing_claims=list(older.opposing_claims),
        gate_flags=flags,
        freshness=older.freshness,
        sufficiency=older.sufficiency,
    )
    assessment = assign_status([a], config)[older.id]
    older.status = assessment.status
    if older.confidence is not None:
        older.confidence.integrity_flags = flags


def _drawn_edge(older: EdgeView, newer: EdgeView) -> EdgeView:
    """The analyst-visible ``supersedes`` edge: *newer object* → *older object* (D-P4.11).

    The internal ``superseded_by``/``supersedes`` fields link *edges* and drive status; the oracle — and
    the way an analyst actually narrates a relocation — models it as one node→node fact ("Rahwali
    replaced Rawalpindi"). Emitting both keeps the status machinery unchanged and makes the relocation a
    thing you can see and click. It carries the **union** of both basing edges' claims, so the drawn edge
    is one-click traceable to the documents on either side of the move (gate G4).
    """
    return EdgeView(
        id=f"e:{newer.target}:{_DRAWN_EDGE_TYPE}:{older.target}",
        type=_DRAWN_EDGE_TYPE,
        source=newer.target,
        target=older.target,
        claim_ids=sorted(set(newer.claim_ids) | set(older.claim_ids)),
        attrs={
            DERIVED_VIA: _DRAWN_VIA,
            "newer_edge": newer.id,
            "older_edge": older.id,
            "subject": newer.source,
            # Named apart from the `edge_instance` FIELD deliberately: the drawn edge is not a member of
            # the basing instance (it must not land in the crossing detector's bucket), it merely records
            # which instance the relocation happened on.
            "source_edge_instance": newer.edge_instance,
        },
    )


def promote_supersessions(
    edges: list[EdgeView], config: ConfigBundle, nodes: dict[str, NodeView] | None = None
) -> SupersedeOutcome:
    """Promote each ordered candidate pair that clears the floor; leave the rest for HITL.

    Idempotent and order-independent: it reads the candidate attrs ``view/supersede.py`` wrote and the
    assessment the status machine just attached, so replaying the same logs + config yields the same
    edges byte-for-byte (gate G2).

    ``nodes`` supplies the subject's identity provenance for the **earned-identity** gate (R1.4). Optional
    and default-``None`` so every existing caller is unchanged; absent (or with the gate unconfigured) the
    behaviour is exactly the pre-S2 one.
    """
    outcome = SupersedeOutcome()
    floor = _floor(config)
    by_id = {e.id: e for e in edges}

    for older in sorted(edges, key=lambda e: e.id):
        newer_id = older.attrs.get(PENDING_NEWER)
        newer = by_id.get(newer_id) if isinstance(newer_id, str) else None
        if newer is None:
            continue
        # No floor configured ⇒ retire nothing. A safety gate whose config is missing must fail closed;
        # the pair simply stays in the analyst's queue where supersede.py left it.
        if floor is None:
            failures = ["supersede-floor-not-configured"]
        else:
            failures = _floor_failures(newer, floor, config)
            # R1.4 — the newer assertion clearing the CREDIBILITY floor is not enough: promoting also
            # removes the pair from the analyst's queue and draws a relocation, which is only the machine's
            # call over an identity it earned.
            failures = failures + _identity_failures(older, newer, nodes, floor, config)
        if failures:
            older.attrs[GATE] = GATE_HELD
            newer.attrs[GATE] = GATE_HELD
            older.attrs[HOLD_REASON] = failures
            newer.attrs[HOLD_REASON] = failures
            outcome.held_pairs.append((older.id, newer.id))
            continue

        older.superseded_by = newer.id
        newer.supersedes = older.id
        older.attrs[GATE] = GATE_PROMOTED
        newer.attrs[GATE] = GATE_PROMOTED
        # The pair is adjudicated by the machine — it is no longer a question for the analyst.
        older.attrs.pop(CANDIDATE, None)
        remaining = [oid for oid in newer.attrs.get(PENDING_OLDER, []) if oid != older.id]
        if remaining:
            newer.attrs[PENDING_OLDER] = remaining
        else:
            newer.attrs.pop(PENDING_OLDER, None)
            newer.attrs.pop(CANDIDATE, None)
        older.attrs.pop(PENDING_NEWER, None)
        _restate(older, config)
        outcome.retired_element_ids.append(older.id)
        if newer.target != older.target:
            outcome.drawn_edges.append(_drawn_edge(older, newer))

    return outcome
