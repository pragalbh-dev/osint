"""Supersedes-vs-contradicts resolution — **real F0 logic** (master §4.3, spine/08 §1).

When several relationship claims resolve to the **same edge instance** (RESOLVE's ``resolved_ref.
edge_instance`` — *never* a designator string) but assert different targets, ``rebuild()`` must decide:

* **differ in ``event_time`` (one strictly later)** → an **ordered candidate pair**: the newer edge is
  *nominated* to retire the older one. It is **not** retired here — see below.
* **same ``event_time``** → a genuine **contradiction** → both edges flagged + cross-linked in
  ``opposing_claims`` and ``attrs["contradiction"]``, routed to HITL.
* **instance identity uncertain** (an event_time missing, so ordering is impossible) →
  **candidate-supersede** (``attrs["candidate_supersede"]``) — so "vacant@A" can't silently erase
  "occupied@B" for a unit that may simply have moved.

**Why ordering alone is not enough (D-P4.4 condition iv).** A supersession retires a fact an analyst may
already have acted on, so "newer" is a necessary but not sufficient condition: the *newer* claim must also
independently reach ≥ probable on ≥1 independent look with a clean deception gate. Otherwise a single
grade-E adversary post ("the battery has left") silently retires a confirmed position — which is exactly
what ``d20_supersede_spoof`` was planted in the corpus to attempt. That floor **cannot be evaluated here**:
this module runs at ``pipeline.rebuild()`` step 2, *before* ``score_claims`` / ``assign_status``, so no
confidence exists yet. So this module emits only the **ordered pair** (:data:`PENDING_NEWER` /
:data:`PENDING_OLDER`) plus ``candidate_supersede`` — i.e. **HITL is the default outcome** — and
``credibility.supersession.promote_supersessions`` (post-status) promotes the pair to a real
``superseded_by``/``supersedes`` link + a *stale* older edge only once the newer edge clears the
configured floor. A pair that never clears it stays a candidate for the analyst.

This sets **structure only** (candidate links / ``opposing_claims`` / flags); it never writes ``status`` —
the status machine (SCORE) owns that (gate G5). Same edge instance + same target = plain corroboration
(one edge, many claims), handled by the caller.
"""

from __future__ import annotations

from collections import defaultdict
from typing import cast

from chanakya.credibility.supersession import (
    CANDIDATE,
    GATE,
    GATE_PENDING,
    PENDING_NEWER,
    PENDING_OLDER,
)
from chanakya.schemas import ClaimRecord, EdgeView, Triple, canonical_iso_bounds


def _latest_iso(claims: list[ClaimRecord]) -> str | None:
    """The freshest ``event_time`` upper-bound across a target's claims (None if any is undated)."""
    bounds = [canonical_iso_bounds(c.event_time)[1] for c in claims]
    if any(b is None for b in bounds):
        return None
    return max(b for b in bounds if b is not None)


def build_instance_edges(edge_instance: str, claims: list[ClaimRecord]) -> list[EdgeView]:
    """Build the EdgeView(s) for one resolved edge instance, applying supersede/contradict.

    One EdgeView per distinct ``(source, type, target)``; supersede/contradict links are set across
    them when the instance holds more than one target.
    """
    by_target: dict[tuple[str, str, str], list[ClaimRecord]] = defaultdict(list)
    for c in claims:
        t = cast(Triple, c.payload)  # caller guarantees relationship claims (payload is a Triple)
        by_target[(t.subject, t.predicate, t.object)].append(c)

    edges: list[EdgeView] = []
    for (subj, pred, obj), cs in sorted(by_target.items()):
        edges.append(
            EdgeView(
                id=f"e:{subj}:{pred}:{obj}",
                type=pred,
                source=subj,
                target=obj,
                edge_instance=edge_instance,
                claim_ids=sorted(c.claim_id for c in cs),
            )
        )

    if len(edges) <= 1:
        return edges  # single target → plain corroboration, nothing to supersede

    # Order the targets by freshness; resolve state-change vs contradiction vs uncertainty.
    timed = [(e, _latest_iso(by_target[(e.source, e.type, e.target)])) for e in edges]
    if any(iso is None for _, iso in timed):
        for e, _ in timed:
            e.attrs[CANDIDATE] = True  # can't order → don't overwrite; HITL adjudicates
        return edges

    timed.sort(key=lambda pair: pair[1] or "")  # oldest → newest
    newest_edge, newest_iso = timed[-1]
    for older_edge, older_iso in timed[:-1]:
        if older_iso == newest_iso:
            # same instant, different target → contradiction (a unit can't be two places at once)
            older_edge.attrs["contradiction"] = True
            newest_edge.attrs["contradiction"] = True
            older_edge.opposing_claims = sorted(set(older_edge.opposing_claims) | set(newest_edge.claim_ids))
            newest_edge.opposing_claims = sorted(set(newest_edge.opposing_claims) | set(older_edge.claim_ids))
        else:
            # Ordered, but NOT yet retired: nominate the pair and leave it in the HITL queue. The
            # confidence + deception floor (D-P4.4 iv) is unevaluable at this point in rebuild(), so the
            # post-status pass owns the promotion to superseded_by/supersedes/stale.
            older_edge.attrs[CANDIDATE] = True
            older_edge.attrs[PENDING_NEWER] = newest_edge.id
            older_edge.attrs[GATE] = GATE_PENDING
            newest_edge.attrs[CANDIDATE] = True
            pending = list(newest_edge.attrs.get(PENDING_OLDER, []))
            newest_edge.attrs[PENDING_OLDER] = sorted({*pending, older_edge.id})
            newest_edge.attrs[GATE] = GATE_PENDING
    return edges
