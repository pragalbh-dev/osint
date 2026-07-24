"""The 8 control points — all present in the one service, differently-shaped ``enqueue`` calls.

This module *is* the portability flex (session §8; spine/08 §3.10): eight places across the spine can
hand a human the wheel, and every one of them is the same envelope + the same service — never bespoke
per-stage adjudication code. Depth is phased, not architecture:

* **wired-deep ★** — ``merge`` · ``status-override`` · ``alert-disposition``: real payloads, real
  writeback, real propagation on rebuild. Pinned to the top of the queue.
* **built** — ``integrity-flag``: the analyst-initiated caller (§9); real writeback + propagation.
* **config** — ``credibility-config`` (read-only levers now) · ``observable-definition``
  (config-authored tripwires for the demo).
* **roadmap** — ``ontology-extension`` · ``assessment-review``: named, typed, not built.

HITL **renders** the signals/scores/breakdowns it is *handed* (by RESOLVE / SCORE / MONITOR); it does
not compute them — that separation is what keeps the two-scores rule (G5) and the stage boundaries
clean. The builders below take the computed evidence as parameters and pack it into the card payload.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from chanakya.schemas import ReviewContext, ReviewQueueItem, ReviewType, Stage

from .queue import build_item

Depth = Literal["wired-deep", "built", "config", "roadmap"]


class ControlPoint(BaseModel):
    """A catalogue entry — one of the 8 places any stage can escalate to the analyst."""

    key: str
    stage: Stage
    review_type: ReviewType | None  # None for the config/roadmap points (no card type yet)
    depth: Depth
    star: bool  # pinned to the top of the queue
    note: str


# All 8 — the flex is that they live in one service, not that all 8 are built now.
CONTROL_POINTS: list[ControlPoint] = [
    ControlPoint(key="credibility-config", stage="credibility", review_type=None, depth="config",
                 star=False, note="read-only levers now (weights/thresholds visible); full edit later"),
    ControlPoint(key="merge", stage="resolution", review_type="merge", depth="wired-deep",
                 star=True, note="sub-threshold same-as/distinct-from — accept/reject/split"),
    ControlPoint(key="ontology-extension", stage="ontology", review_type=None, depth="roadmap",
                 star=False, note="a proposed new type — add / map-to-existing / discard"),
    ControlPoint(key="status-override", stage="credibility", review_type="status-override", depth="wired-deep",
                 star=True, note="confirmed↔probable — promote/demote/reject (propagates on rebuild)"),
    ControlPoint(key="observable-definition", stage="alerting", review_type=None, depth="config",
                 star=False, note="config-authored tripwires for the demo (not a UI card yet)"),
    ControlPoint(key="alert-disposition", stage="alerting", review_type="alert-disposition", depth="wired-deep",
                 star=True, note="a fired tripwire — real/noise/needs-more (tunes the tripwire)"),
    ControlPoint(key="assessment-review", stage="qna", review_type=None, depth="roadmap",
                 star=False, note="analyst review of a generated assessment before it stands"),
    ControlPoint(key="integrity-flag", stage="integrity", review_type="integrity-flag", depth="built",
                 star=False, note="analyst-initiated: flag a source/origin fake (propagates by origin)"),
]

CONTROL_POINTS_BY_KEY: dict[str, ControlPoint] = {cp.key: cp for cp in CONTROL_POINTS}


# ── the wired-deep ★ cards + the built integrity-flag caller ────────────────────────────────────

def build_merge_item(
    *,
    item_id: str,
    candidate_a: dict[str, Any],
    candidate_b: dict[str, Any],
    signals: list[dict[str, Any]],
    merge_score: float,
    band: Literal["auto-merge", "needs-you", "keep-separate"],
    context: ReviewContext | None = None,
    ts: str | None = None,
    prior_merge_event: str | None = None,
) -> ReviewQueueItem:
    """★ Merge card (§4). Renders the two candidates side-by-side, the weighted match signals, and the
    score/band **RESOLVE handed us** — we never recompute them (G5). Options: accept/reject/split.

    Effects grow the alias table (accept), record a distinct-from (reject), or reverse a prior merge
    (split) — each a RESOLVE-consumed payload appended to the log, reversible by another append (G3).
    """
    a_id, b_id = candidate_a["id"], candidate_b["id"]
    a_name, b_name = candidate_a.get("name"), candidate_b.get("name")
    # RESOLVE's alias index is keyed by *normalised names*, not entity ids (aliases.build has no graph to
    # map an id back to a name). So the effect must carry the two NAMES for the accept-link / reject-bar
    # to actually bite on the next rebuild — the ids alone would land in a name closure that matches
    # nothing. ``names`` is emitted only when both candidates supplied one; ``same_as``/``pair`` keep the
    # ids for provenance + the split reversal, and the shape the direct-construction tests assert is intact.
    names = [a_name, b_name] if a_name and b_name else None
    _names = {"names": names} if names else {}
    effects = {
        "accept": {"grow_alias": {"same_as": [a_id, b_id],
                                  "alias": {"canonical": a_id, "surface": b_name}, **_names}},
        "reject": {"record_distinct": {"pair": [a_id, b_id], **_names}},
        "split": {"split_merge": {"pair": [a_id, b_id], "reverses": prior_merge_event, **_names}},
    }
    payload = {
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "signals": signals,  # [{signal, weight, value}] — name/attr · shared-neighbourhood · timeline · source-says-same
        "merge_score": merge_score,
        "band": band,
    }
    ctx = context or ReviewContext(summary=f"Same entity? {a_id} vs {b_id}", confidence=merge_score)
    return build_item(item_id=item_id, type="merge", subject=f"merge:{a_id}:{b_id}",
                      options=["accept", "reject", "split"], effects=effects, payload=payload,
                      context=ctx, pinned=True, ts=ts)


def build_status_override_item(
    *,
    item_id: str,
    subject_ref: str,
    current_status: str | None,
    confidence: dict[str, Any] | None = None,
    promote_to: str = "confirmed",
    demote_to: str = "probable",
    context: ReviewContext | None = None,
    ts: str | None = None,
) -> ReviewQueueItem:
    """★ Status-override card (§5). Renders the element, its current status, and the confidence
    breakdown **SCORE handed us**. Options: promote/demote/reject.

    Effects set the status on the next rebuild (gate G12 — the override wins over the machine).
    ``reject`` is a **forced demote** for now (decision 2026-07-18): it lands the same
    ``set_status→probable`` as demote; the richer "exclude the claim → the machine recomputes
    confirmed→probable" behaviour is deferred (would need rebuild to drop a claim upstream of scoring).
    """
    effects = {
        "promote": {"set_status": {subject_ref: promote_to}},
        "demote": {"set_status": {subject_ref: demote_to}},
        "reject": {"set_status": {subject_ref: demote_to}},  # forced demote (stands in for claim-rejection)
    }
    payload = {"subject_ref": subject_ref, "current_status": current_status, "confidence": confidence or {}}
    ctx = context or ReviewContext(summary=f"Override status of {subject_ref} (now: {current_status})")
    return build_item(item_id=item_id, type="status-override", subject=subject_ref,
                      options=["promote", "demote", "reject"], effects=effects, payload=payload,
                      context=ctx, pinned=True, ts=ts)


def build_alert_disposition_item(
    *,
    item_id: str,
    observable_id: str,
    subject_ref: str,
    before: dict[str, Any],
    after: dict[str, Any],
    severity: str = "notify",
    context: ReviewContext | None = None,
    ts: str | None = None,
) -> ReviewQueueItem:
    """★ Alert-disposition card (§6). Renders the fired tripwire and *what changed* (before→after,
    e.g. occupied@Rawalpindi → occupied@Rahwali). Options: real/noise/needs-more.

    The disposition is appended as a tuning effect MONITOR consumes; HITL does not fire or re-evaluate
    alerts (out of scope) — it only disposes a fired one.
    """
    effects = {
        d: {"tune_tripwire": {"observable_id": observable_id, "disposition": d}}
        for d in ("real", "noise", "needs-more")
    }
    payload = {"observable_id": observable_id, "before": before, "after": after, "severity": severity}
    ctx = context or ReviewContext(summary=f"Alert on {observable_id}: {subject_ref}")
    return build_item(item_id=item_id, type="alert-disposition", subject=subject_ref,
                      options=["real", "noise", "needs-more"], effects=effects, payload=payload,
                      context=ctx, pinned=True, ts=ts)


def build_integrity_flag_item(
    *,
    item_id: str,
    primary_origin_id: str,
    affected_element: str,
    co_referring_claims: list[str],
    flag: str = "analyst-flagged-inauthentic",
    context: ReviewContext | None = None,
    ts: str | None = None,
) -> ReviewQueueItem:
    """Analyst-initiated integrity flag (§9) — a *new caller* of the same service.

    The analyst flags a source/origin fake by ``primary_origin_id``. Because dedup groups claims by
    origin, the co-referring claims sharing that origin support the **same resolved element**; flagging
    that element (F0's ``add_integrity_flag`` effect) taints every one of them on the next rebuild — no
    per-claim fan-out here. ``flag_origin`` carries the origin-keyed intent + the co-referring set for
    provenance and for SCORE's fuller per-claim penalty (incl. *future* claims of the origin), which is
    the deferred structural version.
    """
    effects = {
        "flag": {
            "add_integrity_flag": {"element_id": affected_element, "flag": flag},
            "flag_origin": {"primary_origin_id": primary_origin_id, "co_referring_claims": co_referring_claims},
        }
    }
    payload = {"primary_origin_id": primary_origin_id, "affected_element": affected_element,
               "co_referring_claims": co_referring_claims, "flag": flag}
    ctx = context or ReviewContext(summary=f"Flag origin {primary_origin_id} as inauthentic")
    return build_item(item_id=item_id, type="integrity-flag", subject=primary_origin_id,
                      options=["flag"], effects=effects, payload=payload, context=ctx, ts=ts)
