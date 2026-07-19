"""The status machine — noisy-OR pooling + confirmed/probable/possible/insufficient/contradicted/stale.

The third SCORE stage (master §4.3): turns per-claim credibilities + independence groups + the
deception/freshness/sufficiency gates into a **pooled `assertion_confidence`** and a **status label**,
plus the exact gate vector (for the provenance drawer). Pure and config-driven (gate G6): the two
cutoffs, the minimum independent-look count, and everything else come from ``config.credibility``.

Pooling — noisy-OR *across* independent groups, ``c_g`` = the strongest look in a group, scaled by the
group's independence weight (1.0 cross-discipline, 0.5 same-class):

    assertion_confidence = 1 − Π_g (1 − weight_g · c_g)

Status — gates are applied here, **never** folded into the arithmetic (spine/04 §3.4; DECISIONS
"adversary_denial is a gate, not a multiplier"):

* **insufficient** — a required evidence *kind* is missing (``sufficiency.satisfied`` is False). Off the
  confidence scale; dominates, because if we structurally can't assess we say so (the non-negotiable).
* **contradicted** — a credible opposing group on the same resolved instance → routed to HITL.
* **confirmed** — ALL of: ``assertion_confidence ≥ confirmed`` · ``≥ min_independent_groups`` effective
  independent looks · sufficiency satisfied · every look fresh (age ≤ 1 half-life) · clean integrity &
  clean decoy & no adversary-denial · gated attrs (foreign_control/readiness) not UNKNOWN.
* **stale** — would confirm on magnitude/groups/gates but its *freshest* look has aged past one
  half-life (a demoted-from-confirmed label — a node never silently stays confirmed as it ages).
* **probable** — ``probable ≤ conf < confirmed``, OR a single independent look, OR any cap gate
  (adversary-denial / single-pass decoy / aging) fires on an otherwise-strong assertion.
* **possible** — ``conf < probable`` — a lead, never in the assessed picture.

``assign_status`` reads sufficiency + the freshness/deception gate flags off the ``AssertionInput``
(the pipeline populates them where the claims + sources are in scope), so the machine needs no claim
bodies of its own.
"""

from __future__ import annotations

from chanakya.schemas import AssertionAssessment, AssertionInput, ConfigBundle, IndependenceGroup

# Gate-flag vocabulary (set on AssertionInput.gate_flags by the pipeline). Strings, not numbers (G6).
_ADVERSARY_DENIAL = "adversary-denial"
_DECOY_RISK = "decoy-risk"
_CONTRADICTION = "contradiction"
_AGING = "aging"  # at least one supporting look older than 1 half-life → blocks confirmed
_STALE = "stale"  # the freshest supporting look older than 1 half-life → demote confirmed→stale
_GATED_UNKNOWN = "gated-attr-unknown"  # a gated attr (foreign_control/readiness) is UNKNOWN
_CAP_FLAGS = frozenset({_ADVERSARY_DENIAL, _DECOY_RISK})

_CONFIRMED = "confirmed"
_PROBABLE = "probable"
_POSSIBLE = "possible"
_INSUFFICIENT = "insufficient"
_CONTRADICTED = "contradicted"


def group_confidence(group: IndependenceGroup, per_claim_credibility: dict[str, float]) -> float:
    """``c_g`` = the strongest claim credibility in the group, scaled by the group's independence weight."""
    if not group.claim_ids:
        return 0.0
    strongest = max((per_claim_credibility.get(cid, 0.0) for cid in group.claim_ids), default=0.0)
    return strongest * group.weight


def noisy_or(groups: list[IndependenceGroup], per_claim_credibility: dict[str, float]) -> float:
    """``1 − Π_g (1 − c_g)`` — corroboration pools across independent looks; echoes (one group) add nothing."""
    product = 1.0
    for group in groups:
        product *= 1.0 - group_confidence(group, per_claim_credibility)
    return 1.0 - product


def _effective_looks(groups: list[IndependenceGroup]) -> float:
    """Weighted count of independent looks — two cross-discipline looks = 2.0; a same-class pair = 1.5."""
    total = 0.0
    for group in groups:
        total += group.weight
    return total


def assign_status(
    assertions: list[AssertionInput],
    config: ConfigBundle,
) -> dict[str, AssertionAssessment]:
    """Pool each assertion's looks and assign its status via the gate machine (spine/04 §3.4)."""
    thresholds = config.credibility.thresholds
    confirmed_cut = thresholds.get(_CONFIRMED)
    probable_cut = thresholds.get(_PROBABLE)
    min_groups = getattr(config.credibility, "min_independent_groups", None)

    out: dict[str, AssertionAssessment] = {}
    for a in assertions:
        conf = noisy_or(a.groups, a.per_claim_credibility)
        flags = set(a.gate_flags)
        gate_vector: list[str] = []

        capped = bool(flags & _CAP_FLAGS)
        contradicted = a.has_unresolved_contradiction or _CONTRADICTION in flags
        insufficient = a.sufficiency is not None and not a.sufficiency.satisfied
        aging = _AGING in flags or _STALE in flags
        stale = _STALE in flags
        gated_unknown = _GATED_UNKNOWN in flags

        # Magnitude-and-structure eligibility for confirmed (freshness handled separately below).
        strong = (
            confirmed_cut is not None
            and conf >= confirmed_cut
            and min_groups is not None
            and _effective_looks(a.groups) >= min_groups
            and not capped
            and not gated_unknown
        )

        if insufficient:
            status = _INSUFFICIENT
            gate_vector.append("insufficient-evidence")
        elif contradicted:
            status = _CONTRADICTED
            gate_vector.append("credible-contradiction")
        elif strong and not aging:
            status = _CONFIRMED
        elif strong and stale:
            status = _STALE  # aged-out confirmed — the freshest look is past one half-life
            gate_vector.append("stale-demotion")
        elif probable_cut is not None and conf >= probable_cut:
            status = _PROBABLE
            if capped:
                gate_vector.append("capped-at-probable")
            elif strong and aging:
                gate_vector.append("aging-not-fresh")
            elif min_groups is not None and _effective_looks(a.groups) < min_groups:
                gate_vector.append("single-independent-look")
        else:
            status = _POSSIBLE
            gate_vector.append("below-probable-floor")

        for flag in (_ADVERSARY_DENIAL, _DECOY_RISK):
            if flag in flags:
                gate_vector.append(flag)

        out[a.element_id] = AssertionAssessment(
            element_id=a.element_id,
            assertion_confidence=conf,
            status=status,
            gate_vector=gate_vector,
        )
    return out
