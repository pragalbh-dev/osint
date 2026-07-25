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
#: On both edges of a pair that WAS promoted over an identity still in question (R1.4a): the movement is
#: asserted, but the pair stays in the analyst's queue and this records why it was not machine-adjudicated.
ADJUDICATION_HELD = "supersede_adjudication_held"
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
_PROVISIONAL = "provisional"           # a build-materialized instance: identity not earned, by definition


@dataclass
class SupersedeOutcome:
    """What the pass did — returned so ``rebuild()`` can render it without re-deriving it."""

    drawn_edges: list[EdgeView] = field(default_factory=list)
    retired_element_ids: list[str] = field(default_factory=list)  # older edges now *stale*
    held_pairs: list[tuple[str, str]] = field(default_factory=list)  # (older, newer) still for HITL
    #: R1.4(a) — promoted, but NOT taken off the analyst's desk: the identity under the movement is still an
    #: open question, so the pair keeps `candidate_supersede` and the analyst still decides.
    identity_unearned_pairs: list[tuple[str, str]] = field(default_factory=list)
    #: R1.4(b) — retired assertions whose honest `insufficient` was NOT overwritten with `stale`. The
    #: pipeline reads this to leave their Known Gaps in place.
    protected_refusals: list[str] = field(default_factory=list)


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


def identity_is_unearned(
    older: EdgeView,
    newer: EdgeView,
    nodes: dict[str, NodeView] | None,
    unsettled_identities: set[str],
    floor: dict[str, object],
) -> str | None:
    """R1.4 — is this promotion's *subject identity* still an open question? A reason string, or ``None``.

    **The chain this addresses.** Two co-located batteries with no designations look nearly identical to the
    identity judge, so a formation merge is the path of least resistance. ``based-at`` is functional and
    keyed on the unit, so the moment they fuse their two distinct sites become *one unit's before and
    after*. This pass then clears the credibility floor on the newer of the two, sets the supersede link,
    **pops the pair out of the analyst's queue** — "adjudicated by the machine" — and, because the targets
    differ, **draws a relocation edge**. One identity error therefore becomes a positively-asserted movement
    assessment the analyst is never asked about: the non-negotiable breached without any component lying.

    **What this DOES, and — the correction that matters — what it does not.** It does exactly one thing: it
    keeps the pair **in the analyst's queue**. It does **not** block the promotion, and it must not, because
    R1.4 restrains machine *adjudication* over an unearned identity, not supersession itself. An earlier
    version of this function returned a *hold*, and that quietly disabled the legitimate relocation beat —
    caught only by an independently-authored mirror test asserting the thing that must still work. Worth
    recording as a pattern rather than a slip: an implementer closing an over-promotion hole will reach for
    the broadest guard, because every test it can see rewards caution. **Timidity is a failure mode here,
    not a safe default.**

    Scoped to promotions that would **draw** a relocation across *differing* targets — a same-target refresh
    asserts no movement, so there is nothing to fabricate — and it fires when the subject is:

    * a **provisional** instance (build-materialized: there is no earned identity to rest on at all); or
    * an endpoint of an **open `candidate` merge** — a same-as the resolver put in front of the analyst and
      nobody has adjudicated.

    **What "sub-confirmed" is NOT.** Not the node's assessed *status*. The legitimate flagship relocation
    sits at *probable*, so reading the confidence label would suppress the very beat this leaves working. The
    question is about the identity **decision**, in the merge-band vocabulary: is it still open? A
    never-merged subject, and one whose merges are all settled, both pass.

    The co-location-specific half of this (making such a merge fail to *fuse* in the first place) is the
    identity layer's job; this is the downstream backstop that keeps a human in the loop if it does.
    """
    if not bool(floor.get(_REQUIRE_EARNED)):
        return None
    if newer.target == older.target:
        return None  # a same-target refresh asserts no movement; there is nothing to fabricate
    node = (nodes or {}).get(newer.source)
    if node is not None and node.attrs.get(_PROVISIONAL):
        return "subject-identity-provisional"
    if newer.source in unsettled_identities:
        return "subject-identity-open-candidate-merge"
    return None


def protects_an_honest_refusal(older: EdgeView, identity_unearned: bool) -> bool:
    """R1.4(b) — must this retirement leave its honest *insufficient* (and its Known Gap) alone?

    True only when **both** hold: the older assertion's evidence requirement was unmet (the same condition
    as "it raised a Known Gap" — both read ``sufficiency.satisfied``) **and** the identity under the movement
    is still an open question. Then the supersede link is still written — the newer fact stands — but the
    label is not restated to ``stale`` and the pipeline does not drop the gap. An ``insufficient`` is a
    **refusal to assess**, not a weak assessment: calling it ``stale`` says "we knew this and it has been
    overtaken" about something we never knew, and deleting the gap removes the only record that we still
    cannot assess it.

    **Why it is conditioned on the identity, and not standing alone.** D-13.14 names the gap deletion as one
    of *three consequences of the over-merge*: the supersede path "draws a relocation, removes the pair from
    the analyst's queue, and deletes the retired edge's Known Gap — turning an honest ``insufficient`` into
    ``stale``". The harm is an identity error laundering itself into a movement assessment; it is not that
    retiring an under-evidenced position is wrong in general. Unconditioned, this rule stops a legitimate
    relocation's retired end from ever reading ``stale`` — measured, on the real corpus — which disables the
    beat rather than protecting anything. **Both narrow prohibitions therefore share one trigger.**
    """
    if not identity_unearned:
        return False
    suff = older.sufficiency
    return suff is not None and not suff.satisfied


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
    edges: list[EdgeView],
    config: ConfigBundle,
    nodes: dict[str, NodeView] | None = None,
    unsettled_identities: set[str] | None = None,
) -> SupersedeOutcome:
    """Promote each ordered candidate pair that clears the floor; leave the rest for HITL.

    Idempotent and order-independent: it reads the candidate attrs ``view/supersede.py`` wrote and the
    assessment the status machine just attached, so replaying the same logs + config yields the same
    edges byte-for-byte (gate G2).

    ``nodes`` and ``unsettled_identities`` supply R1.4's two inputs: whether the subject is a
    build-materialized provisional instance, and whether its identity is still an open ``candidate`` merge.
    Both optional and default-``None`` so every existing caller is unchanged; absent (or with the gate
    unconfigured) the behaviour is exactly the pre-S2 one.

    **R1.4 changes two narrow things and nothing else** — see :func:`identity_is_unearned` and
    :func:`protects_an_honest_refusal`. It never blocks a promotion: an earned relocation is promoted,
    retired, restated to ``stale`` and drawn exactly as before.
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
        if failures:
            older.attrs[GATE] = GATE_HELD
            newer.attrs[GATE] = GATE_HELD
            older.attrs[HOLD_REASON] = failures
            newer.attrs[HOLD_REASON] = failures
            outcome.held_pairs.append((older.id, newer.id))
            continue

        # The floor is cleared: the pair IS promoted. R1.4 changes two narrow things about *how*, and
        # nothing about *whether* — an over-broad guard here disables the relocation beat, which is the
        # opposite failure and just as bad.
        unearned = (
            identity_is_unearned(older, newer, nodes, unsettled_identities or set(), floor)
            if floor is not None else None
        )
        older.superseded_by = newer.id
        newer.supersedes = older.id
        older.attrs[GATE] = GATE_PROMOTED
        newer.attrs[GATE] = GATE_PROMOTED
        if unearned is None:
            # Earned: the pair is adjudicated by the machine — no longer a question for the analyst.
            older.attrs.pop(CANDIDATE, None)
            remaining = [oid for oid in newer.attrs.get(PENDING_OLDER, []) if oid != older.id]
            if remaining:
                newer.attrs[PENDING_OLDER] = remaining
            else:
                newer.attrs.pop(PENDING_OLDER, None)
                newer.attrs.pop(CANDIDATE, None)
            older.attrs.pop(PENDING_NEWER, None)
        else:
            # R1.4(a): the movement is asserted — it cleared the credibility floor — but the identity under
            # it is still an open question, and an identity error here is exactly what turns into a
            # fabricated relocation. So the machine does NOT take the pair off the analyst's desk:
            # `candidate_supersede` and the pending links STAY, with the reason recorded, and the analyst is
            # still the one who decides. Promotion is not withheld; adjudication is.
            older.attrs[ADJUDICATION_HELD] = unearned
            newer.attrs[ADJUDICATION_HELD] = unearned
            outcome.identity_unearned_pairs.append((older.id, newer.id))
        # R1.4(b): over an unearned identity, a retired assertion that never *had* an assessment keeps its
        # honest refusal — the label is not restated to `stale` and (in the pipeline) its Known Gap is not
        # dropped. Every other retirement, earned or merely well-evidenced, restates exactly as before.
        if protects_an_honest_refusal(older, unearned is not None):
            outcome.protected_refusals.append(older.id)
        else:
            _restate(older, config)
            outcome.retired_element_ids.append(older.id)
        if newer.target != older.target:
            outcome.drawn_edges.append(_drawn_edge(older, newer))

    return outcome
