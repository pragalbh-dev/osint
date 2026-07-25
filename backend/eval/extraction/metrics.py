"""The per-run metrics — every scored line the scorecard prints, and the rule that a metric with no
substrate reports *nothing* rather than a zero.

:class:`MetricValue` is the load-bearing type here, and its invariant is enforced in code, not by
convention: a metric is either ``measured`` with a number, or ``unavailable`` with a reason and
``value=None``. There is no third state and no default. That is what stops the one failure mode this
harness could commit by accident — a metric whose substrate has not shipped (coref binding needs S3)
quietly scoring 0.0 for every candidate and dragging a real difference out of nothing, or scoring 1.0
and hiding one.

The metrics, and what each really measures:

* **surface P/R/F1** — the matcher's alignment (see :mod:`matcher`; its leniency is the measurement). The
  precision denominator excludes the spans the gold declares NEUTRAL — see :mod:`negative_gold`; leaving
  them in charges a candidate for reading the document correctly, and does so in proportion to how much of
  it the candidate read.
* **trap avoidance** — the fabrication line at the places the gold knows the answer: did the model stay
  silent where the document asserts nothing? Declared a *veto* rather than a weight, because a
  non-negotiable inside a composite is only a heavy weight, and any weight is a price.
* **identity over-read** — did the model assert ``same-as``/``distinct-from`` over a pair the page
  explicitly refuses to resolve? A count (N=2), never a rate, never ranked on.
* **citation faithfulness** — does the claim's cited span exist, sit in bounds, and lexically contain the
  claim's own surfaces? A *proxy* for entailment, and named as one: it asks "is the cited text about
  this?", not "does the cited text entail this". An optional judge seam is provided for the real thing.
* **extract-only-stated** — the fabrication line. Does the model assert surfaces that appear nowhere in
  the document? This is the metric the project's non-negotiable rule cares about most.
* **discriminator capture / fabrication-avoidance (A7)** — of the identity discriminators the source
  states, how many did the model carry? And of the ones the source does *not* state, how many did it
  correctly leave empty? The second is a fabrication measure: A7's contract is "absence means unknown,
  never infer an operator from nationality".
* **structured-output reliability** — did the forced tool call return, and did it stay inside the offered
  schema?
* **graph recall** — of the per-slice sub-oracle's nodes and edges, how many survive a rebuild of this
  run's claims?
* **kind tagging** — low weight, self-correcting (D-13.5), reported for completeness.
* **coref binding** — top-weighted. RK-COREF (S3) has landed, so the substrate exists: extraction pass 2
  offers the model a real mention-cluster field and stamps the accepted cluster's referent atom onto
  ``ClaimRecord.referent_id``. The pass is flag-gated, and :mod:`eval.extraction.coref_channel` checks
  the flag *before* any budget is spent, so "unmeasured" here means the models bound nothing — never a
  silent schema gap.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from rapidfuzz import fuzz

from chanakya.schemas import GraphView
from eval.gold.adapter import EmittedSpan

from .gold import SubOracle
from .matcher import MatchResult, normalizations, similarity
from .negative_gold import NegativeGold
from .policy import MatchPolicy, Pricing
from .recording import CallRecord
from .surface import DISCRIMINATOR_SLOTS, SurfaceClaim, normalize_surface

Status = Literal["measured", "unavailable"]
Direction = Literal["higher_is_better", "lower_is_better"]

#: The reason the coref metric reports when no claim carries a referent id. Matched on in the report so
#: the line reads "NO CLUSTERING", never "0.00".
#:
#: RK-COREF (S3) has landed, so the *substrate* now exists: extraction pass 2 offers the model a real
#: mention-cluster field and stamps each accepted cluster's referent atom onto ``ClaimRecord``. What this
#: string now means is therefore narrower and more interesting than it used to — either the channel was
#: unavailable on this run's config (``eval.extraction.coref_channel`` checks that up front, before any
#: budget is spent, precisely so this cannot be the explanation), or the pass ran and every candidate
#: declined to bind anything. Both are "not measured"; neither is a zero, and neither is a model's score.
#:
#: Deliberately does NOT name a config flag. The gate on pass 2 is being deleted, and a reason string that
#: sends an operator to a key that no longer exists is worse than one that names the check which will still
#: be there — ``coref_channel.inspect`` reports the cause, whatever the cause has become.
NO_CLUSTERING = (
    "NO CLUSTERING: not one claim carries a referent_id, so there is no system clustering to score. "
    "Either the coreference channel was unavailable on this run's config (eval.extraction.coref_channel "
    "reports the cause, and preflight prints it) or every candidate declined to bind any mention. Not a "
    "failure of any candidate and not a zero — simply not measured."
)


@dataclass(frozen=True)
class MetricValue:
    """One metric on one run: a number, or an explicit refusal to report one.

    The constructor enforces the invariant. A ``measured`` metric must carry a value; an ``unavailable``
    metric must carry ``None`` and a reason. Constructing anything else raises, so no code path can
    accidentally publish a placeholder number.
    """

    name: str
    value: float | None
    status: Status
    reason: str = ""
    unit: str = "rate"                       # "rate" | "seconds" | "usd" | "count"
    direction: Direction = "higher_is_better"
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == "measured" and self.value is None:
            raise ValueError(f"metric {self.name!r}: status=measured with no value")
        if self.status == "unavailable":
            if self.value is not None:
                raise ValueError(
                    f"metric {self.name!r}: status=unavailable must carry value=None, got {self.value!r} "
                    "— an unavailable metric may never publish a number"
                )
            if not self.reason:
                raise ValueError(f"metric {self.name!r}: status=unavailable needs a reason")

    @classmethod
    def measured(cls, name: str, value: float, **kw: Any) -> MetricValue:
        return cls(name=name, value=float(value), status="measured", **kw)

    @classmethod
    def unavailable(cls, name: str, reason: str, **kw: Any) -> MetricValue:
        return cls(name=name, value=None, status="unavailable", reason=reason, **kw)


def _rate(numerator: int, denominator: int, name: str, reason: str, **kw: Any) -> MetricValue:
    """A count ratio, or an explicit unavailable when the denominator is empty (never 0/0 → 0.0)."""
    if denominator <= 0:
        return MetricValue.unavailable(name, reason, **kw)
    return MetricValue.measured(name, numerator / denominator, **kw)


# ── surface P / R / F1 ────────────────────────────────────────────────────────────────────────────

def surface_metrics(match: MatchResult) -> dict[str, MetricValue]:
    """Precision / recall / F1 from the alignment. Degenerate slices report unavailable, not 0.0.

    The precision denominator is whatever :attr:`~eval.extraction.matcher.MatchResult.precision_denominator`
    says it is, so the gold's neutral-span exclusions are already inside the number and the ``detail``
    names every key that left the denominator. There is deliberately no second, "raw" precision metric:
    two precision lines on one scorecard is an invitation to quote whichever one flatters, and the honest
    one is the one that does not charge a model for reading the document correctly.
    """
    detail = {
        "matched": len(match.pairs),
        "gold_total": match.gold_total,
        "extracted_total": match.extracted_total,
        "precision_denominator": match.precision_denominator,
        "precision_excluded_as_neutral": list(match.precision_exclusions),
        "missed_gold": [g.key for g in match.missed_gold],
        "unmatched_extracted": [e.key for e in match.unmatched_extracted],
        "rejections": dict(match.rejections),
    }
    if match.gold_total == 0:
        reason = "the gold slice is empty — nothing to score against"
        return {n: MetricValue.unavailable(n, reason, detail=detail)
                for n in ("surface_precision", "surface_recall", "surface_f1")}
    if match.precision_denominator == 0:
        # Extracting nothing — or emitting only spans the gold declares neutral — is a real, scoreable
        # outcome for recall (0) and F1 (0). Precision is genuinely 0/0.
        why = ("the run extracted no claims" if match.extracted_total == 0 else
               f"all {match.extracted_total} emitted claim(s) sit on spans the gold declares NEUTRAL for "
               "precision")
        return {
            "surface_precision": MetricValue.unavailable(
                "surface_precision", f"{why} — precision is 0/0, undefined", detail=detail),
            "surface_recall": MetricValue.measured("surface_recall", 0.0, detail=detail),
            "surface_f1": MetricValue.measured("surface_f1", 0.0, detail=detail),
        }
    return {
        "surface_precision": MetricValue.measured("surface_precision", match.precision, detail=detail),
        "surface_recall": MetricValue.measured("surface_recall", match.recall, detail=detail),
        "surface_f1": MetricValue.measured("surface_f1", match.f1, detail=detail),
    }


# ── the negative gold: the fabrication line, and the identity over-read ───────────────────────────

def trap_avoidance(negative: NegativeGold, emitted: Sequence[EmittedSpan]) -> MetricValue:
    """Did the candidate stay silent at the spans that assert nothing? **The fabrication line.**

    This is the project's one non-negotiable expressed as a metric, at the places where the gold knows the
    answer: a ``not_a_claim`` span is a modal about the future, meta-commentary, a refusal or document
    noise, and a claim emitted over one has been invented.

    It is deliberately **not** weighted into the composite. Inside a composite a non-negotiable is just a
    heavy weight, and any weight is a price a good-enough model can pay; it is declared in
    ``gates.non_negotiable_floors`` instead, which makes it a veto (see :func:`eval.extraction.compare.decide`).

    Two ways this reports ``unavailable`` rather than a flattering 1.0, both of which block a winner
    because the metric is a declared non-negotiable: the slice declares no traps at all, and the emitted
    claims share no document with the labeled negative rows (a join failure whose "no hits" is
    indistinguishable from a clean run).
    """
    alignment = negative.alignment(emitted)
    if not alignment.usable:
        return MetricValue.unavailable("trap_avoidance", alignment.reason)
    result = negative.traps(emitted)
    rate = result.get("rate")
    detail = {k: v for k, v in result.items() if k != "rate"}
    detail["shared_files"] = list(alignment.shared_files)
    if rate is None:
        return MetricValue.unavailable(
            "trap_avoidance",
            "the labeled slice declares no `not_a_claim` traps, so the fabrication line has no substrate "
            "here — not a candidate's score and not a zero",
            detail=detail,
        )
    return MetricValue.measured("trap_avoidance", float(rate), detail=detail)


def identity_over_read(negative: NegativeGold, emitted: Sequence[EmittedSpan]) -> MetricValue:
    """How many genuinely-unresolved pairs did the candidate assert an identity over? (N=2 — a COUNT.)

    Reported as a ``count``, which is the mechanism that keeps it out of the weighted composite
    (``composite_series`` admits only 0..1 rates). That is the gold's own reporting rule honoured in the
    type system rather than in a comment: "N=2 — report the raw count, never a two-decimal rate, and never
    rank on it."
    """
    alignment = negative.alignment(emitted)
    if not alignment.usable:
        return MetricValue.unavailable("identity_over_read", alignment.reason,
                                       unit="count", direction="lower_is_better")
    result = negative.identity_over_reads(emitted)
    if not result.get("pairs"):
        return MetricValue.unavailable(
            "identity_over_read",
            "the labeled slice declares no `ambiguous` pairs, so there is no identity over-read to count",
            unit="count", direction="lower_is_better",
        )
    return MetricValue.measured(
        "identity_over_read", float(result["over_read"]), unit="count", direction="lower_is_better",
        detail={k: v for k, v in result.items() if k != "rate"},
    )


# ── grounding: citation faithfulness + extract-only-stated ────────────────────────────────────────

#: A judge that answers "does this text support this claim?". ``None`` = use the lexical proxy.
EntailmentJudge = Callable[[SurfaceClaim, str], bool]


def _lexically_grounded(claim: SurfaceClaim, haystack: str, policy: MatchPolicy) -> bool:
    """Every role surface must appear (fuzzily) inside ``haystack``, under the policy's readings.

    The identifier rule has to apply **here too**, and this is the lane where it matters most. Measured
    against the real slice documents at the declared 0.85 floor, the prose reading scores a faithful but
    de-hyphenated designator as ABSENT from a document that states it — ``HT233`` against d19 reads 0.80,
    ``HQ9P`` against d02 reads 0.75, the GD number reads 0.81 — so the harness would report a model that
    quoted the page correctly as having fabricated. That is a false positive on ``citation_faithfulness``
    and ``extract_only_stated``, the two metrics this bake-off declares non-negotiable, and it is a worse
    error than the recall dent the same normalisation caused in the matcher. Under
    ``designator_aware`` all five read 1.00. It cannot launder a fabrication: gluing removes punctuation
    *inside* a letters-and-digits token, so an invented surface only becomes groundable if the document
    already states the same string in a different rendering — which is what "grounded" means.
    """
    for norm in normalizations(policy):
        hay = norm(haystack)
        if not hay:
            continue
        if all(
            not norm(surface)
            or float(fuzz.partial_ratio(norm(surface), hay)) / 100.0 >= policy.grounding_similarity
            for surface in claim.role_surfaces()
        ):
            return True
    return False


def _slice_spans(claim: SurfaceClaim, doc_texts: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """The cited text for each char-addressable ref → (slices, out-of-bounds ref descriptions)."""
    slices: list[str] = []
    out_of_bounds: list[str] = []
    for ref in claim.refs:
        if not ref.char_addressable or ref.file not in doc_texts:
            continue
        text = doc_texts[ref.file]
        assert ref.span is not None
        start, end = sorted(ref.span)
        if start < 0 or end > len(text) or start >= end:
            out_of_bounds.append(f"{ref.file}[{ref.span[0]}:{ref.span[1]}] vs len {len(text)}")
            continue
        slices.append(text[start:end])
    return slices, out_of_bounds


def citation_faithfulness(
    claims: Sequence[SurfaceClaim], doc_texts: Mapping[str, str], policy: MatchPolicy,
    judge: EntailmentJudge | None = None,
) -> MetricValue:
    """Do claims cite a real, in-bounds span whose text actually carries the claim's surfaces?

    A claim with **no** provenance at all counts as unfaithful — the project treats an unsourced claim as
    the cardinal failure, so it cannot be excluded as "not gradable".

    Claims whose only refs are non-char-addressable (an image bbox/region, a PDF page, a CSV row) are
    excluded from the denominator and **reported** in ``detail['not_char_addressable']``. Counting them
    as passes would launder the imagery lane; counting them as failures would punish a model for the
    locator shape our own pipeline chose.
    """
    graded = 0
    faithful = 0
    unsourced: list[str] = []
    oob: list[str] = []
    not_addressable: list[str] = []

    for claim in claims:
        if not claim.refs:
            unsourced.append(claim.key)
            graded += 1
            continue
        slices, bad = _slice_spans(claim, doc_texts)
        if bad:
            oob.append(f"{claim.key}: {'; '.join(bad)}")
        if not slices:
            if bad:
                graded += 1  # it cited a span; the span does not exist. That is a failure, not an excuse.
            else:
                not_addressable.append(claim.key)
            continue
        graded += 1
        cited = "\n".join(slices)
        ok = judge(claim, cited) if judge is not None else _lexically_grounded(claim, cited, policy)
        if ok:
            faithful += 1

    detail = {
        "graded": graded,
        "faithful": faithful,
        "unsourced": unsourced,
        "span_out_of_bounds": oob,
        "not_char_addressable": not_addressable,
        "method": "entailment-judge" if judge is not None else "lexical proxy (span contains the surfaces)",
    }
    return _rate(
        faithful, graded, "citation_faithfulness",
        "no claim carried a char-addressable citation, so faithfulness could not be checked",
        detail=detail,
    )


def extract_only_stated(
    claims: Sequence[SurfaceClaim], doc_texts: Mapping[str, str], policy: MatchPolicy,
) -> MetricValue:
    """The fabrication line: does the model assert surfaces the document does not contain anywhere?

    Weaker than faithfulness on purpose — it does not care *where* in the document the support is, only
    that it exists. A claim that fails this is not a mis-cited claim; it is an invented one.

    Image-derived claims cannot be checked against text and are excluded from the denominator and
    reported. That exclusion is the honest limit of this metric, and the VLM lane is exactly where
    fabrication risk is highest — so the count is surfaced, never buried.
    """
    graded = 0
    supported = 0
    unsupported: list[str] = []
    ungradable: list[str] = []

    for claim in claims:
        texts = [doc_texts[ref.file] for ref in claim.refs if ref.file in doc_texts]
        if not texts:
            ungradable.append(claim.key)
            continue
        graded += 1
        if _lexically_grounded(claim, "\n".join(texts), policy):
            supported += 1
        else:
            unsupported.append(claim.key)

    detail = {
        "graded": graded,
        "supported": supported,
        "unsupported": unsupported,
        "ungradable_no_text_source": ungradable,
    }
    return _rate(
        supported, graded, "extract_only_stated",
        "no claim could be checked against document text (all sources were non-text)",
        detail=detail,
    )


# ── structured output / tool-call reliability ─────────────────────────────────────────────────────

def structured_output_reliability(calls: Sequence[CallRecord]) -> MetricValue:
    """Fraction of forced tool calls that returned, and returned inside the offered schema."""
    total = len(calls)
    failed = [c for c in calls if not c.ok]
    invented = {c.tool_name: list(c.invented_fields()) for c in calls if c.ok and c.invented_fields()}
    clean = sum(1 for c in calls if c.ok and not c.invented_fields())
    detail = {
        "calls": total,
        "failed": [c.error for c in failed],
        "invented_top_level_fields": invented,
        "clean": clean,
    }
    return _rate(clean, total, "structured_output_reliability",
                 "no extraction call was made", detail=detail)


# ── A7 discriminators ─────────────────────────────────────────────────────────────────────────────

def _walk_mentions(node: Any) -> Iterable[dict[str, Any]]:
    """Every named mention dict in a raw tool payload — anything with a non-empty string ``name``.

    Generic on purpose: the extraction schemas differ per source format (prose, notice, tender, imagery,
    …) and a per-format walker would silently skip whichever format the candidate happened to be given.
    """
    if isinstance(node, dict):
        name = node.get("name")
        if isinstance(name, str) and name.strip():
            yield node
        for value in node.values():
            yield from _walk_mentions(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_mentions(item)


def _mention_context(mention: Mapping[str, Any]) -> dict[str, str | None]:
    ctx = mention.get("context")
    if not isinstance(ctx, Mapping):
        return {slot: None for slot in DISCRIMINATOR_SLOTS}
    out: dict[str, str | None] = {}
    for slot in DISCRIMINATOR_SLOTS:
        value = ctx.get(slot)
        out[slot] = str(value) if isinstance(value, str) and value.strip() else None
    return out


@dataclass(frozen=True)
class DiscriminatorTally:
    captured: int = 0            # source states it, model carried it (value agrees)
    wrong: int = 0               # source states it, model filled something else
    missed: int = 0              # source states it, model left it empty
    fabricated: int = 0          # source does NOT state it, model filled it anyway
    correct_abstention: int = 0  # source does NOT state it, model left it empty
    ungradable_mentions: int = 0  # model mentions that aligned to no gold entity claim
    #: Gold entity claims a model mention aligned to. Carried so an empty denominator can name its real
    #: cause: "nothing aligned" is a fact about this candidate, "the gold labels no discriminators" is a
    #: fact about the slice, and reporting the second when the first is true sends an operator to the
    #: wrong file to fix a model's problem.
    aligned: int = 0

    @property
    def stated_total(self) -> int:
        return self.captured + self.wrong + self.missed

    @property
    def absent_total(self) -> int:
        return self.fabricated + self.correct_abstention


def tally_discriminators(
    payloads: Sequence[Mapping[str, Any]], gold: Sequence[SurfaceClaim], policy: MatchPolicy,
) -> DiscriminatorTally:
    """Align raw-payload mentions to gold entity claims by name, then grade the four A7 slots.

    Graded on the **raw tool payload**, not on ``ClaimRecord``: ``MentionContext`` is populated by the
    model but consumed by nothing downstream until S3, so the finished claim never carries it. The raw
    payload is the only place the model's discriminator behaviour is visible at all.
    """
    gold_entities = [g for g in gold if g.form == "entity"]
    mentions = [m for payload in payloads for m in _walk_mentions(payload)]

    # Greedy one-to-one name alignment, deterministic on (-score, gold key, mention index).
    scored: list[tuple[float, str, int]] = []
    for g in gold_entities:
        for i, m in enumerate(mentions):
            s = similarity(g.roles.get("name"), str(m.get("name")), policy)
            if s >= policy.role_min_similarity:
                scored.append((s, g.key, i))
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))

    used_gold: set[str] = set()
    used_mention: set[int] = set()
    aligned: list[tuple[SurfaceClaim, Mapping[str, Any]]] = []
    by_key = {g.key: g for g in gold_entities}
    for _, gold_key, idx in scored:
        if gold_key in used_gold or idx in used_mention:
            continue
        used_gold.add(gold_key)
        used_mention.add(idx)
        aligned.append((by_key[gold_key], mentions[idx]))

    captured = wrong = missed = fabricated = abstained = 0
    for g, mention in aligned:
        got = _mention_context(mention)
        for slot in DISCRIMINATOR_SLOTS:
            expected = g.discriminators.get(slot)
            actual = got.get(slot)
            if expected is not None:
                if actual is None:
                    missed += 1
                elif similarity(expected, actual, policy) >= policy.role_min_similarity:
                    captured += 1
                else:
                    wrong += 1
            else:
                if actual is None:
                    abstained += 1
                else:
                    fabricated += 1

    return DiscriminatorTally(
        captured=captured, wrong=wrong, missed=missed, fabricated=fabricated,
        correct_abstention=abstained, ungradable_mentions=len(mentions) - len(used_mention),
        aligned=len(aligned),
    )


def _no_discriminator_denominator(tally: DiscriminatorTally, what: str) -> str:
    """Why a discriminator denominator is empty — the candidate's doing, or the slice's.

    Both are "not measured", but they send an operator to different places, so they may not share one
    string. If no model mention aligned to a gold entity claim at all, the slice's labels were never
    reached and saying "the gold labels none" is simply false.
    """
    if tally.aligned == 0:
        return (
            f"no model mention aligned to a gold entity claim, so no {what} discriminator was ever "
            f"reached — this is a fact about this candidate's extraction, NOT about the slice's labels "
            f"({tally.ungradable_mentions} mention(s) aligned to nothing)"
        )
    return (f"the gold slice labels no {what} discriminators on the {tally.aligned} aligned entity "
            f"claim(s), so this cannot be measured")


def discriminator_metrics(tally: DiscriminatorTally) -> dict[str, MetricValue]:
    """Capture rate (of stated discriminators) and fabrication-avoidance (of unstated ones)."""
    detail = {
        "captured": tally.captured, "wrong": tally.wrong, "missed": tally.missed,
        "fabricated": tally.fabricated, "correct_abstention": tally.correct_abstention,
        "ungradable_mentions": tally.ungradable_mentions, "aligned": tally.aligned,
    }
    return {
        "discriminator_capture": _rate(
            tally.captured, tally.stated_total, "discriminator_capture",
            _no_discriminator_denominator(tally, "stated"),
            detail=detail,
        ),
        "discriminator_fabrication_avoidance": _rate(
            tally.correct_abstention, tally.absent_total, "discriminator_fabrication_avoidance",
            _no_discriminator_denominator(tally, "ABSENT"),
            detail=detail,
        ),
    }


# ── coref binding ─────────────────────────────────────────────────────────────────────────────────

def coref_binding(match: MatchResult) -> MetricValue:
    """B-cubed F1 of the system's document-local coref clusters against the gold's.

    Over the aligned (gold, extracted) pairs, each item's B-cubed precision is |same system cluster ∧
    same gold cluster| / |same system cluster|, its recall the same over the gold cluster, and the metric
    is the F1 of their means.

    The substrate is ``ClaimRecord.referent_id``, minted by RK-COREF (S3)'s extraction pass 2 — a second
    forced-tool call whose schema carries the model's own mention clustering. That pass ships behind a
    flag; :mod:`eval.extraction.coref_channel` checks it is live *before* any API budget is spent, so a
    dormant channel is caught as a precondition rather than surfacing here as a mystery blank.

    It deliberately does **not** fall back to "every claim is its own cluster", which would score a real
    number (and a flattering one for a model that never co-refers) off a decision no model made.
    """
    graded = [p for p in match.pairs if p.gold.coref_cluster is not None]
    if not graded:
        # Two very different causes, and they may not share one string. "The gold carries no labels" is a
        # fact about the slice that no candidate can fix; "nothing aligned" is a fact about THIS
        # candidate's extraction. Reporting the first when the second is true points an operator at the
        # answer file to fix a model's problem — the same wrong-file failure the coref channel's own
        # cause reporting exists to avoid.
        labeled = sum(1 for g in match.missed_gold if g.coref_cluster is not None)
        labeled += sum(1 for p in match.pairs if p.gold.coref_cluster is not None)
        if not match.pairs:
            return MetricValue.unavailable(
                "coref_binding",
                f"no extracted claim aligned with any gold claim, so no clustering was reached — a fact "
                f"about this candidate's extraction, NOT about the slice ({labeled} gold claim(s) do "
                f"carry coref_cluster labels)",
            )
        return MetricValue.unavailable(
            "coref_binding",
            f"none of the {len(match.pairs)} aligned gold claim(s) carry coref_cluster labels, so "
            f"binding cannot be scored on this alignment",
        )
    if not any(p.extracted.referent_id for p in graded):
        return MetricValue.unavailable("coref_binding", NO_CLUSTERING)

    items = [(p.gold.coref_cluster, p.extracted.referent_id) for p in graded]
    precisions: list[float] = []
    recalls: list[float] = []
    for gold_c, sys_c in items:
        same_sys = [g for g, s in items if s == sys_c]
        same_gold = [s for g, s in items if g == gold_c]
        precisions.append(sum(1 for g in same_sys if g == gold_c) / len(same_sys))
        recalls.append(sum(1 for s in same_gold if s == sys_c) / len(same_gold))
    p = sum(precisions) / len(precisions)
    r = sum(recalls) / len(recalls)
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return MetricValue.measured(
        "coref_binding", f1, detail={"bcubed_precision": p, "bcubed_recall": r, "graded": len(graded)}
    )


# ── kind tagging ──────────────────────────────────────────────────────────────────────────────────

def kind_tagging(match: MatchResult) -> MetricValue:
    """Accuracy of the claim ``kind`` on aligned pairs where the gold labels one (low weight, D-13.5)."""
    graded = [p for p in match.pairs if p.gold.kind]
    correct = sum(1 for p in graded if p.gold.kind == p.extracted.kind)
    return _rate(correct, len(graded), "kind_tagging",
                 "the gold slice labels no claim kinds", detail={"graded": len(graded)})


# ── graph recall vs the per-slice sub-oracle ──────────────────────────────────────────────────────

def graph_recall(view: GraphView, oracle: SubOracle, policy: MatchPolicy) -> dict[str, MetricValue]:
    """Node / edge / combined recall of the rebuilt view against the per-slice sub-oracle.

    Nodes align on ontology type + fuzzy name (ids are re-minted every extraction, so an id comparison
    would measure our id derivation, not the model). Edges are credited only when both endpoints aligned
    **and the direction matches**; a reversed edge is counted separately in ``detail`` and credited to
    nobody — canonical direction is a pipeline invariant, and silently accepting either way round would
    hide a real extraction defect.
    """
    scored: list[tuple[float, str, str]] = []
    view_nodes = {n.id: n for n in view.nodes}
    for onode in oracle.nodes:
        for vnode in view.nodes:
            if normalize_surface(onode.type) != normalize_surface(vnode.type):
                continue
            s = similarity(onode.name, vnode.name, policy)
            if s >= policy.role_min_similarity:
                scored.append((s, onode.key, vnode.id))
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))

    matched_node: dict[str, str] = {}
    used_view: set[str] = set()
    for _, okey, vid in scored:
        if okey in matched_node or vid in used_view:
            continue
        matched_node[okey] = vid
        used_view.add(vid)

    edges_by_type: dict[str, list[tuple[str, str]]] = {}
    for e in view.edges:
        edges_by_type.setdefault(normalize_surface(e.type), []).append((e.source, e.target))

    matched_edges = 0
    reversed_only: list[str] = []
    missing_edges: list[str] = []
    for oedge in oracle.edges:
        src = matched_node.get(oedge.source.key)
        tgt = matched_node.get(oedge.target.key)
        pairs = edges_by_type.get(normalize_surface(oedge.type), [])
        if src and tgt and (src, tgt) in pairs:
            matched_edges += 1
        elif src and tgt and (tgt, src) in pairs:
            reversed_only.append(oedge.key)
            missing_edges.append(oedge.key)
        else:
            missing_edges.append(oedge.key)

    detail = {
        "oracle_nodes": len(oracle.nodes),
        "matched_nodes": len(matched_node),
        "missing_nodes": [n.key for n in oracle.nodes if n.key not in matched_node],
        "oracle_edges": len(oracle.edges),
        "matched_edges": matched_edges,
        "reversed_direction_not_credited": reversed_only,
        "missing_edges": missing_edges,
        "view_nodes": len(view_nodes),
        "view_edges": len(view.edges),
    }
    total = len(oracle.nodes) + len(oracle.edges)
    return {
        "graph_node_recall": _rate(len(matched_node), len(oracle.nodes), "graph_node_recall",
                                   "the sub-oracle declares no nodes", detail=detail),
        "graph_edge_recall": _rate(matched_edges, len(oracle.edges), "graph_edge_recall",
                                   "the sub-oracle declares no edges", detail=detail),
        "graph_recall": _rate(len(matched_node) + matched_edges, total, "graph_recall",
                              "the sub-oracle is empty", detail=detail),
    }


# ── cost + latency ────────────────────────────────────────────────────────────────────────────────

def latency_metric(total_latency_s: float, calls: int) -> MetricValue:
    """Total wall time across the run's extraction calls (lower is better)."""
    if calls <= 0:
        return MetricValue.unavailable("latency_s", "no extraction call was made",
                                       unit="seconds", direction="lower_is_better")
    return MetricValue.measured("latency_s", total_latency_s, unit="seconds",
                                direction="lower_is_better", detail={"calls": calls})


def cost_metric(usage: Mapping[str, int] | None, pricing: Pricing | None) -> MetricValue:
    """Run cost in USD — ``unavailable`` unless BOTH real usage and real prices exist.

    Never estimates. A cost line invented from a guessed price is a fabricated benchmark number, and this
    harness holds itself to the rule it exists to enforce.
    """
    if pricing is None:
        return MetricValue.unavailable(
            "cost_usd", "UNPRICED — no pricing declared for this candidate in config/bakeoff.yaml",
            unit="usd", direction="lower_is_better")
    if not usage:
        return MetricValue.unavailable(
            "cost_usd", "the provider reported no token usage for this run",
            unit="usd", direction="lower_is_better")
    cost = (usage.get("input_tokens", 0) / 1e6) * pricing.input_per_mtok + (
        usage.get("output_tokens", 0) / 1e6) * pricing.output_per_mtok
    return MetricValue.measured("cost_usd", cost, unit="usd", direction="lower_is_better",
                                detail=dict(usage))


__all__ = [
    "NO_CLUSTERING",
    "DiscriminatorTally",
    "EntailmentJudge",
    "MetricValue",
    "citation_faithfulness",
    "coref_binding",
    "cost_metric",
    "discriminator_metrics",
    "extract_only_stated",
    "graph_recall",
    "identity_over_read",
    "kind_tagging",
    "latency_metric",
    "structured_output_reliability",
    "surface_metrics",
    "tally_discriminators",
    "trap_avoidance",
]
