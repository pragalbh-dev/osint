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
6. ``identifier_agreement == "nested_or_equal"`` — **a designator disagreement is a veto.** For each role,
   take the identifier-shaped tokens of both surfaces (tokens mixing letters and digits, after the
   designator normalisation below: ``HQ-9B`` → ``{hq9b}``, ``the system`` → ``{}``). The pair is
   inadmissible unless one side's set is contained in the other's. Designation is a *discriminator* in this
   domain, and no edit-distance floor can carry it: measured on the labeled gold, ``HQ-9B``/``HQ-9BE``
   scores 0.91 and two different GD numbers score 0.95, so without this rule the kernel silently merges
   sibling variants and distinct import events — the over-merge the whole project exists to prevent. An
   empty identifier set is contained in everything, so ordinary prose is untouched.
7. ``span_policy == "require"`` — when both sides carry a char span in the same file, their IoU must
   reach ``span_iou_floor``.

Pair score:

* per-role similarity = ``rapidfuzz`` ``similarity`` fn over the normalised role strings, scaled to 0..1;
  under ``identifier_policy == "designator_aware"`` the role is scored **twice** — once under
  :func:`~eval.extraction.surface.normalize_surface` (punctuation is a word boundary: right for prose) and
  once under :func:`~eval.extraction.surface.normalize_designator` (punctuation inside a letters-and-digits
  token is typographic: right for ``HQ-9/P`` ≡ ``HQ9P``) — and the better of the two is taken. Taking the
  max means the rule can only *add* matches, never remove one that already worked; the tightening comes
  from the identifier veto above, not from the kernel;
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

Recall = matched / gold. F1 = harmonic mean, defined as 0.0 when either side is empty (never 1.0 for
"extracted nothing, gold empty" — an empty slice is a measurement failure, and it is reported as such by
:attr:`MatchResult.degenerate`).

PRECISION AND ITS DENOMINATOR
─────────────────────────────
Precision is ``matched / precision_denominator``, and the denominator is **not** simply everything the
model emitted. The labeled slice declares three classes of span (``unmodelled``, ``anti_coref``, and a
non-identity claim over an ``ambiguous`` pair) at which emitting a claim is *correct reading*, not a false
positive: the document really does say that, the ontology just cannot express it or the identity must stay
unbound. Charging those to precision is not a small unfairness — it scales with how much of a document a
model reads, so it does **not** cancel between candidates and systematically favours the terser
extractor, on a line weighted 3.0.

So :attr:`MatchResult.precision_exclusions` carries the emitted keys the **gold** declares neutral (see
:mod:`eval.extraction.negative_gold`, which consumes the gold owner's own hooks and never re-derives the
semantics). Two invariants are enforced in the constructor rather than trusted:

* an excluded key must be one the matcher left **unpaired** — a matched claim is explained by positive
  gold and dropping it from the denominator would push precision above 1.0;
* ``not_a_claim`` spans are never in the set. Those emissions are fabrication and must cost precision;
  the gold's hook withholds the exclusion from them, and the trap wins whenever a span is both.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from rapidfuzz import fuzz

from .policy import MatchPolicy
from .surface import (
    SurfaceClaim,
    identifier_tokens,
    normalize_designator,
    normalize_predicate,
    normalize_surface,
)

_SIMILARITY_FNS = {
    "token_set_ratio": fuzz.token_set_ratio,
    "token_sort_ratio": fuzz.token_sort_ratio,
    "partial_ratio": fuzz.partial_ratio,
    "ratio": fuzz.ratio,
}


def normalizations(policy: MatchPolicy) -> tuple[Callable[[str | None], str], ...]:
    """The readings of a surface this policy scores. One per rung, best score wins.

    ``prose`` scores only the punctuation-is-a-word-boundary reading; ``designator_aware`` also scores the
    identifier-glued one. Exposed rather than inlined because the grounding proxies in
    :mod:`~eval.extraction.metrics` must ask the *same* question of a document ("does this surface appear
    here?") — a matcher that accepts ``HT233`` for ``HT-233`` while the faithfulness check calls it absent
    would report a faithful model as fabricating, on the metric the project treats as non-negotiable.
    """
    if policy.identifier_policy == "designator_aware":
        return (normalize_surface, normalize_designator)
    return (normalize_surface,)


def similarity(a: str | None, b: str | None, policy: MatchPolicy) -> float:
    """Normalised surface similarity in 0..1 under the policy's chosen ``rapidfuzz`` function.

    Scored once per reading in :func:`normalizations`; the best rung wins, so ``designator_aware`` can only
    raise a score. The tightening that pays for that leniency is :func:`identifiers_agree`.
    """
    fn = _SIMILARITY_FNS[policy.similarity]
    best = 0.0
    for norm in normalizations(policy):
        left, right = norm(a), norm(b)
        if not left and not right:
            return 1.0
        if not left or not right:
            continue
        best = max(best, float(fn(left, right)) / 100.0)
    return best


def identifiers_agree(a: str | None, b: str | None, policy: MatchPolicy) -> bool:
    """Do these two surfaces name the same designators? (``nested_or_equal``; see the ALIGNMENT RULE §6.)

    Nested rather than equal, because a surface may legitimately carry a designator its counterpart omits —
    ``the FT-2000`` against ``the FT-2000 (sometimes rendered FT-2000A)``. It is **not** prefix-tolerant:
    ``{hq9}`` is not contained in ``{hq9p}``, so ``HQ-9`` and ``HQ-9/P`` stay different things.
    """
    if policy.identifier_agreement == "ignore":
        return True
    left, right = identifier_tokens(a), identifier_tokens(b)
    return left <= right or right <= left


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
    #: Emitted claim keys the GOLD declares neutral for precision. Set by
    #: :meth:`with_precision_exclusions`, never by the matcher itself — the matcher knows nothing about
    #: negative gold, and inventing the semantics here is the drift this split exists to prevent.
    precision_exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.precision_exclusions:
            return
        excluded = set(self.precision_exclusions)
        matched = {p.extracted.key for p in self.pairs}
        overlap = sorted(excluded & matched)
        if overlap:
            raise ValueError(
                f"precision exclusions name claim(s) the matcher PAIRED with positive gold: {overlap}. A "
                "matched claim is explained by the gold and may never leave the precision denominator — "
                "dropping it would push precision above 1.0 and credit a model for a span it hit."
            )
        unknown = sorted(excluded - {e.key for e in self.unmatched_extracted})
        if unknown:
            raise ValueError(
                f"precision exclusions name claim(s) that are not in this alignment at all: {unknown}. An "
                "exclusion computed against a different run's claims would shrink this run's denominator "
                "for free."
            )

    def with_precision_exclusions(self, keys: Sequence[str]) -> MatchResult:
        """The same alignment with the gold's neutral-span exclusions applied to the denominator."""
        return replace(self, precision_exclusions=tuple(dict.fromkeys(keys)))

    @property
    def precision_denominator(self) -> int:
        """Everything emitted, less the emissions the gold declares neutral. Never below ``len(pairs)``."""
        return self.extracted_total - len(set(self.precision_exclusions))

    @property
    def precision(self) -> float:
        denominator = self.precision_denominator
        return len(self.pairs) / denominator if denominator else 0.0

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
        return self.gold_total == 0 or self.precision_denominator == 0


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
    for role, g_text in gold.roles.items():
        if not identifiers_agree(g_text, pred.roles.get(role), policy):
            return "identifier"
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
    "identifiers_agree",
    "match_claims",
    "normalizations",
    "similarity",
]
