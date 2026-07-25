"""The claim matcher — the one place that decides what counts as "the same claim".

**The matcher's leniency IS the measurement.** Slacken the surface threshold and every model looks
accurate; tighten it and every model looks careless; make span agreement mandatory and you measure
offset arithmetic instead of reading comprehension. So the rule is not a heuristic buried in a scoring
loop: it is a declared :class:`~eval.extraction.policy.MatchPolicy` loaded from ``config/bakeoff.yaml``,
printed above every number it produced, and reported back on every result object.

THE ALIGNMENT RULE, in full
───────────────────────────
A gold claim *G* and an extracted claim *E* may be paired only if all the **admissibility** conditions
hold, and are then scored by a **pair score**; pairs are assigned one-to-one, best score first.

Admissibility (any failure makes the pair impossible, not merely low-scoring):

1. ``require_same_form``     — a triple never matches an entity or an event.
2. ``require_same_polarity`` — a negation is not a sloppy version of the assertion. This one matters to
   this project specifically: "no HQ-9 was observed" and "HQ-9 was observed" differ by the whole point.
3. ``predicate_policy``      — ``exact`` (byte-equal), ``normalized`` (casefold, ``-_/``→space, punctuation
   dropped, whitespace collapsed — so ``supplies-component`` ≡ ``Supplies Component``), or ``ignore``.
   An event's ``event_type`` is compared as its predicate.
4. ``entity_type_policy``    — the same three modes over an entity claim's ontology type.
5. Both sides must carry the **same role set** (subject+object / name / participant:0…n). An event with
   three participants is not the same claim as one with two.
6. ``span_policy == "require"`` — when both sides carry a char span in the same file, their IoU must
   reach ``span_iou_floor``.

Pair score:

* per-role similarity = ``rapidfuzz`` ``similarity`` fn over :func:`~eval.extraction.surface.normalize_surface`
  of the two role strings, scaled to 0..1;
* **every** role must reach ``role_min_similarity`` — a claim that nails the subject and invents the
  object is a *different claim*, not a 50%-correct one, and a blended average would hide exactly the
  failure mode this project cares about;
* the mean of the role similarities must reach ``pair_min_similarity``;
* under ``span_policy == "bonus"``, the best span IoU across the two claims' refs contributes
  ``span_bonus_weight * IoU`` to the score used for *ordering* (never for admissibility), so when two
  extracted claims are equally good on surfaces the one citing the right place wins the pairing.

Assignment: greedy, highest score first, one gold to one extracted. Ties break on ``(gold key,
extracted key)`` so the result is deterministic — this scorer is measuring another system's
non-determinism and must not add its own. Greedy is not guaranteed globally optimal; with a one-to-one
constraint and a hard per-role floor the difference from an optimal assignment is confined to
near-threshold pairs, and the alternative (an optimal-assignment solver) would trade an auditable rule
for an opaque one. That choice is stated here rather than hidden.

Precision = matched / extracted. Recall = matched / gold. F1 = harmonic mean, defined as 0.0 when either
side is empty (never 1.0 for "extracted nothing, gold empty" — an empty slice is a measurement failure,
and it is reported as such by :attr:`MatchResult.degenerate`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .policy import MatchPolicy
from .surface import SurfaceClaim, normalize_predicate, normalize_surface

_SIMILARITY_FNS = {
    "token_set_ratio": fuzz.token_set_ratio,
    "token_sort_ratio": fuzz.token_sort_ratio,
    "partial_ratio": fuzz.partial_ratio,
    "ratio": fuzz.ratio,
}


def similarity(a: str | None, b: str | None, policy: MatchPolicy) -> float:
    """Normalised surface similarity in 0..1 under the policy's chosen ``rapidfuzz`` function."""
    left, right = normalize_surface(a), normalize_surface(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return float(_SIMILARITY_FNS[policy.similarity](left, right)) / 100.0


def _predicates_compatible(gold: SurfaceClaim, pred: SurfaceClaim, policy: MatchPolicy) -> bool:
    if policy.predicate_policy == "ignore":
        return True
    if policy.predicate_policy == "exact":
        return (gold.predicate or "") == (pred.predicate or "")
    return normalize_predicate(gold.predicate) == normalize_predicate(pred.predicate)


def _entity_types_compatible(gold: SurfaceClaim, pred: SurfaceClaim, policy: MatchPolicy) -> bool:
    if gold.form != "entity" or policy.entity_type_policy == "ignore":
        return True
    if policy.entity_type_policy == "exact":
        return (gold.entity_type or "") == (pred.entity_type or "")
    return normalize_surface(gold.entity_type) == normalize_surface(pred.entity_type)


def best_span_iou(gold: SurfaceClaim, pred: SurfaceClaim) -> float | None:
    """Best char-span IoU across the two claims' refs; ``None`` when no pair of refs is comparable."""
    best: float | None = None
    for g_ref in gold.refs:
        for p_ref in pred.refs:
            iou = g_ref.iou(p_ref)
            if iou is None:
                continue
            best = iou if best is None else max(best, iou)
    return best


@dataclass(frozen=True)
class MatchedPair:
    """One aligned (gold, extracted) pair and the evidence for the alignment."""

    gold: SurfaceClaim
    extracted: SurfaceClaim
    score: float                      # the ordering score (surface mean + optional span bonus)
    surface_score: float              # the mean role similarity alone
    role_scores: dict[str, float]
    span_iou: float | None


@dataclass(frozen=True)
class MatchResult:
    """The alignment of one extracted claim set against one gold claim set, plus P/R/F1."""

    policy: MatchPolicy
    pairs: tuple[MatchedPair, ...]
    missed_gold: tuple[SurfaceClaim, ...]        # false negatives
    unmatched_extracted: tuple[SurfaceClaim, ...]  # false positives (as scored against the gold)
    gold_total: int
    extracted_total: int
    rejections: dict[str, int] = field(default_factory=dict)

    @property
    def precision(self) -> float:
        return len(self.pairs) / self.extracted_total if self.extracted_total else 0.0

    @property
    def recall(self) -> float:
        return len(self.pairs) / self.gold_total if self.gold_total else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def degenerate(self) -> bool:
        """True when one side is empty — the numbers are then a measurement failure, not a score."""
        return self.gold_total == 0 or self.extracted_total == 0


def _admissible(gold: SurfaceClaim, pred: SurfaceClaim, policy: MatchPolicy) -> str | None:
    """``None`` if the pair may be scored, else the name of the condition that ruled it out."""
    if policy.require_same_form and gold.form != pred.form:
        return "form"
    if policy.require_same_polarity and gold.polarity != pred.polarity:
        return "polarity"
    if not _predicates_compatible(gold, pred, policy):
        return "predicate"
    if not _entity_types_compatible(gold, pred, policy):
        return "entity_type"
    if set(gold.roles) != set(pred.roles):
        return "role_set"
    if policy.span_policy == "require":
        iou = best_span_iou(gold, pred)
        if iou is not None and iou < policy.span_iou_floor:
            return "span_iou"
    return None


def _score_pair(
    gold: SurfaceClaim, pred: SurfaceClaim, policy: MatchPolicy
) -> tuple[float, float, dict[str, float], float | None] | None:
    """Score an admissible pair, or ``None`` when a threshold rejects it."""
    role_scores: dict[str, float] = {}
    for role, g_text in gold.roles.items():
        s = similarity(g_text, pred.roles.get(role), policy)
        if s < policy.role_min_similarity:
            return None
        role_scores[role] = s
    if not role_scores:
        return None
    surface = sum(role_scores.values()) / len(role_scores)
    if surface < policy.pair_min_similarity:
        return None

    iou = best_span_iou(gold, pred)
    score = surface
    if policy.span_policy == "bonus" and iou is not None:
        score = surface + policy.span_bonus_weight * iou
    return score, surface, role_scores, iou


def match_claims(
    gold: list[SurfaceClaim], extracted: list[SurfaceClaim], policy: MatchPolicy
) -> MatchResult:
    """Align an extracted claim set against a gold one under ``policy`` → pairs + P/R/F1.

    Deterministic: candidate pairs are ordered by ``(-score, gold.key, extracted.key)``, so identical
    inputs give an identical alignment on every run.
    """
    rejections: dict[str, int] = {}
    scored: list[tuple[float, str, str, MatchedPair]] = []

    by_key_extracted = {e.key: e for e in extracted}
    for g in gold:
        for e in extracted:
            reason = _admissible(g, e, policy)
            if reason is not None:
                rejections[reason] = rejections.get(reason, 0) + 1
                continue
            result = _score_pair(g, e, policy)
            if result is None:
                rejections["threshold"] = rejections.get("threshold", 0) + 1
                continue
            score, surface, roles, iou = result
            scored.append((score, g.key, e.key, MatchedPair(
                gold=g, extracted=e, score=score, surface_score=surface, role_scores=roles, span_iou=iou,
            )))

    scored.sort(key=lambda row: (-row[0], row[1], row[2]))

    used_gold: set[str] = set()
    used_pred: set[str] = set()
    pairs: list[MatchedPair] = []
    for _, gold_key, pred_key, pair in scored:
        if gold_key in used_gold or pred_key in used_pred:
            continue
        used_gold.add(gold_key)
        used_pred.add(pred_key)
        pairs.append(pair)

    return MatchResult(
        policy=policy,
        pairs=tuple(pairs),
        missed_gold=tuple(g for g in gold if g.key not in used_gold),
        unmatched_extracted=tuple(
            by_key_extracted[k] for k in sorted(by_key_extracted) if k not in used_pred
        ),
        gold_total=len(gold),
        extracted_total=len(extracted),
        rejections=rejections,
    )


__all__ = [
    "MatchResult",
    "MatchedPair",
    "best_span_iou",
    "match_claims",
    "similarity",
]
