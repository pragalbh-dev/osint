"""Binds the impl-blind contract in :mod:`_bakeoff_contract_spec` to the shipped ``eval.extraction`` harness.

WHY THIS FILE EXISTS
────────────────────
The test hand wrote its gates against a *declared* contract (plain dicts in, duck-typed results out) and
resolved the real harness by best-effort name discovery. That discovery was written blind, and at
integration it half-worked, which is the worst outcome available:

* ``match_claims`` and ``evaluate_gates`` were found by name but have different **signatures** — the gates
  died with ``TypeError`` before reaching their own assertion;
* ``score_faithfulness`` and ``build_scorecard`` were not found at all (the impl spells them
  ``metrics.citation_faithfulness`` and ``compare.decide``), so those gates silently checked the NAIVE
  stand-in — while ``USING_STAND_IN`` (a single ``all()`` over the four surfaces) reported *False* and
  every failure message claimed it had "checked against the shipped eval.extraction harness".

Twenty-odd red gates therefore named the shipped implementation as the thing that failed, when the shipped
implementation was never called. A red carrying a false attribution is the same defect class as a green
carrying a false claim: it switches off the next reader's scepticism, and here it would have sent someone
to "fix" a working module.

This module removes the guesswork. It implements the declared contract *over the real types*, so each gate
tests the property it was written to test against the code that will actually run. It adapts shapes only —
it never softens a threshold, supplies a default the impl refuses to supply, or answers a question on the
impl's behalf.

WHAT IS ADAPTED (shape only)
────────────────────────────
=====================  ==========================================================================
contract surface       shipped implementation
=====================  ==========================================================================
``match_claims``       ``matcher.match_claims(gold, extracted, policy)`` — dicts → ``SurfaceClaim``,
                       the contract's ``rule['surface_threshold']`` → ``MatchPolicy`` floors.
``score_faithfulness`` ``metrics.citation_faithfulness(claims, doc_texts, policy)`` — a
                       ``MetricValue`` → ``.rate`` / ``.unfaithful``.
``evaluate_gates``     ``gates.dry_gates(Candidate, BakeoffConfig, imagery=ImageryObservations)`` — the
                       contract's four booleans → a real ``Candidate`` declaration. ``dry_gates`` is the
                       faithful binding because the contract hands over a declaration and no measured
                       numbers: it is the same set of preconditions ``preflight`` judges. The
                       non-negotiable METRIC gates (``evaluate_gates``' extra) need a run first.
``build_scorecard``    ``compare.decide(scores, config)`` — per-metric run lists → ``CandidateScore``
                       via ``build_series``, then the real verdict.
=====================  ==========================================================================

The contract's candidate booleans map onto the impl's declarations as follows, and the mapping is chosen
so that each boolean reaches the gate it was written for:

``vlm_capable=False``            → ``multimodal="none"``       (fails ``vlm_imagery_path``)
``live_in_shipped_image=False``  → ``client_module="eval.…"``  (fails ``keyless_equals_live``)
``freezes_seed_bundles=False``   → ``freezes_seed=False``      (fails ``keyless_equals_live``)
``model_id="…-latest"``          → floating alias              (fails ``pinned_model_id``)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from eval.extraction import compare as C
from eval.extraction import gates as G
from eval.extraction import matcher as MA
from eval.extraction import metrics as ME
from eval.extraction import policy as P
from eval.extraction import scorecard as SC
from eval.extraction.surface import SpanRef, SurfaceClaim

# ── the policy the contract's plain `rule` dict maps onto ─────────────────────────────────────────

#: Similarity kernels the impl actually offers (``policy.SimilarityName``).
_SIMILARITY_NAMES = frozenset({"token_sort_ratio", "token_set_ratio", "partial_ratio", "ratio"})

#: Match-policy defaults used when a gate passes no ``rule``. These mirror ``config/bakeoff.yaml`` and are
#: NOT tuned here — a binding layer that quietly relaxed a threshold would be measuring itself.
_BASE_POLICY = dict(
    similarity="token_sort_ratio",
    require_same_form=True,
    require_same_polarity=True,
    predicate_policy="normalized",
    entity_type_policy="normalized",
    role_min_similarity=0.70,
    pair_min_similarity=0.80,
    span_policy="bonus",
    span_iou_floor=0.30,
    span_bonus_weight=0.15,
    grounding_similarity=0.85,
)


def match_policy(rule: Mapping[str, Any] | None = None) -> P.MatchPolicy:
    """Build a real :class:`MatchPolicy` from the contract's ``rule`` dict.

    The contract expresses leniency as one number, ``surface_threshold``; the impl separates a per-role
    floor from the floor on their mean. A single threshold is applied to **both**, which is the faithful
    reading: "surfaces must match at least this well" with no per-role slack the contract never granted.
    """
    kw = dict(_BASE_POLICY)
    if rule:
        threshold = rule.get("surface_threshold")
        if threshold is not None:
            kw["role_min_similarity"] = float(threshold)
            kw["pair_min_similarity"] = float(threshold)
        # The contract's DEFAULT_RULE describes its similarity in prose ("difflib.SequenceMatcher
        # ratio"), which is documentation rather than a selector the impl offers. Only forward a value
        # the impl actually implements; anything else keeps the configured default rather than raising,
        # because the leniency THRESHOLD is what these gates are testing, not the kernel's name.
        if rule.get("similarity") in _SIMILARITY_NAMES:
            kw["similarity"] = rule["similarity"]
        for key in ("predicate_policy", "entity_type_policy", "span_policy"):
            if key in rule:
                kw[key] = rule[key]
    return P.MatchPolicy(**kw)


# ── dict ⇄ SurfaceClaim ───────────────────────────────────────────────────────────────────────────

def to_surface(d: Mapping[str, Any], key: str) -> SurfaceClaim:
    """One contract claim dict → a :class:`SurfaceClaim`.

    ``key`` is supplied by position, never derived from content: the impl's matcher enforces one-to-one
    alignment *by key*, so two genuinely distinct gold rows that happen to state the same triple must
    carry distinct keys or they would silently collapse into one and understate the gold total.
    """
    span = d.get("span")
    refs = ()
    if d.get("doc_id") is not None:
        refs = (SpanRef(file=str(d["doc_id"]),
                        span=(int(span[0]), int(span[1])) if span else None),)
    return SurfaceClaim(
        key=key,
        source_id=str(d.get("doc_id") or ""),
        form=str(d.get("form", "triple")),
        polarity=str(d.get("polarity", "positive")),
        roles={"subject": str(d.get("subject", "")), "object": str(d.get("object", ""))},
        predicate=d.get("predicate"),
        refs=refs,
    )


def _surfaces(claims: Sequence[Mapping[str, Any]], prefix: str) -> list[SurfaceClaim]:
    return [to_surface(d, f"{prefix}{i}") for i, d in enumerate(claims)]


# ── surface 1: match_claims ───────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundMatch:
    """The contract's match-result view over a real :class:`MatchResult`."""

    precision: float
    recall: float
    f1: float
    pairs: tuple[tuple[int, int], ...]
    rule: dict[str, Any]
    result: MA.MatchResult

    def describe(self) -> str:
        return self.result.policy.describe()


def match_claims(gold, pred, *, rule=None) -> BoundMatch:  # noqa: ANN001 - contract shape
    policy = match_policy(rule)
    g = _surfaces(gold, "g")
    e = _surfaces(pred, "e")
    res = MA.match_claims(g, e, policy)
    gi = {c.key: i for i, c in enumerate(g)}
    ei = {c.key: i for i, c in enumerate(e)}
    pairs = tuple(sorted((gi[p.gold.key], ei[p.extracted.key]) for p in res.pairs))
    return BoundMatch(
        precision=res.precision, recall=res.recall, f1=res.f1, pairs=pairs,
        rule={"policy": policy.describe(), **(dict(rule) if rule else {})}, result=res,
    )


# ── surface 2: score_faithfulness ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundFaithfulness:
    rate: float
    unfaithful: tuple[int, ...]
    metric: ME.MetricValue


def score_faithfulness(pred, docs) -> BoundFaithfulness:  # noqa: ANN001 - contract shape
    """Contract ``score_faithfulness(pred, docs)`` over ``metrics.citation_faithfulness``.

    The contract wants ``.unfaithful`` as prediction indices. The impl reports faithful/graded counts plus
    named failure buckets (``unsourced``, ``span_out_of_bounds``), so the indices are recovered by
    re-running the impl's own per-claim grounding check — not by a second, looser rule of our own.
    """
    policy = match_policy(None)
    claims = _surfaces(pred, "e")
    metric = ME.citation_faithfulness(claims, dict(docs), policy)
    bad: list[int] = []
    for i, claim in enumerate(claims):
        if not claim.refs:
            bad.append(i)
            continue
        slices, _ = ME._slice_spans(claim, dict(docs))
        if not slices or not ME._lexically_grounded(claim, "\n".join(slices), policy):
            bad.append(i)
    rate = metric.value if metric.status == "measured" else 0.0
    return BoundFaithfulness(rate=float(rate or 0.0), unfaithful=tuple(bad), metric=metric)


# ── surface 3: evaluate_gates ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundGates:
    passed: bool
    failures: tuple[str, ...]
    report: G.GateReport


def _config(min_margin: float = 0.03,
            required_metrics: Sequence[str] = ()) -> P.BakeoffConfig:
    """A real :class:`BakeoffConfig` carrying the shipped gate rules and the contract's margin."""
    return P.BakeoffConfig(
        schema_version="rk-bakeoff/1.0",
        replication=P.Replication(runs_per_candidate=5, min_runs_for_ranking=2),
        margin=P.Margin(min_absolute=min_margin, noise_multiplier=2.0),
        gates=P.GateConfig(
            floating_alias_patterns=["-latest", ":latest", "@latest", "latest"],
            production_client_package="chanakya.ingest",
            # The shipped config names `extract_only_stated` as its fabrication line; the contract names
            # the same thing `fabrication_rate` (inverted polarity). Both are declared so the veto binds
            # whichever spelling a gate uses. Floors stay null — the veto is RELATIVE and needs no
            # invented threshold.
            non_negotiable_floors={"citation_faithfulness": None, "extract_only_stated": None,
                                   "fabrication_rate": None},
        ),
        weights={"claim_f1": 3.0, "citation_faithfulness": 4.5, "fabrication_rate": 4.5,
                 "structured_output_reliability": 3.0, "coref_binding": 5.0},
        match_policy=P.MatchPolicy(**_BASE_POLICY),
        candidates=[],
        required_metrics=list(required_metrics),
    )


def to_candidate(c: Mapping[str, Any]) -> P.Candidate:
    """The contract's four booleans → a real :class:`Candidate` declaration."""
    live = bool(c.get("live_in_shipped_image", True))
    return P.Candidate(
        id=str(c["name"]),
        label=str(c["name"]),
        provider="test",
        model_id=str(c.get("model_id", "pinned-model-1.0")),
        # A client under `chanakya.ingest` is on the shipped path; one under `eval` is not — which is
        # exactly what `live_in_shipped_image=False` asserts.
        client_module="chanakya.ingest.client" if live else "eval.extraction.some_candidate_client",
        client_class="TestClient",
        sdk_module="json",  # always importable: this binding is not testing SDK availability
        key_env="PATH",     # always set: key provisioning is a separate gate, exercised separately
        multimodal="native" if c.get("vlm_capable", True) else "none",
        freezes_seed=bool(c.get("freezes_seed_bundles", True)),
        pricing=None,
    )


def evaluate_gates(cand) -> BoundGates:  # noqa: ANN001 - contract shape
    # `dry_gates`, not `evaluate_gates`: the contract's surface takes a candidate *declaration* and no
    # measured numbers, which is exactly the set of preconditions `preflight` judges — imagery (on the
    # observations supplied), KEYLESS==LIVE, the pin, the key. The non-negotiable METRIC gates need a run to
    # have produced numbers; binding them here with nothing to judge would report UNKNOWN for every contract
    # candidate and turn every gate red for a reason the contract never asked about.
    report = G.dry_gates(
        to_candidate(cand), _config(),
        # The contract's candidates declare VLM capability rather than evidencing it, so the binding
        # supplies one successful image call for a declared-capable candidate. A declared-incapable one
        # still FAILs on `multimodal="none"`, which is the property the gate tests.
        imagery=G.ImageryObservations(calls_ok=1, calls_total=1,
                                      sources=("binding: one declared image call",)),
    )
    return BoundGates(
        passed=report.eligible,
        failures=tuple(f"{g.name}: {g.detail}" for g in report.blocking),
        report=report,
    )


# ── surface 4: build_scorecard ────────────────────────────────────────────────────────────────────

#: Metrics the contract declares lower-is-better, so the binding tags their series correctly. A series
#: tagged the wrong way would make the impl *prefer* fabrication — the exact bug the fabrication gate hunts.
_LOWER_IS_BETTER = frozenset({"fabrication_rate", "cost_usd", "latency_s"})


@dataclass
class BoundStat:
    """One metric on one candidate, in the shape the contract's readers introspect."""

    runs: tuple[float, ...] | None
    measured: bool
    mean: float | None
    spread: float | None
    series: SC.MetricSeries

    def __str__(self) -> str:
        return C.summarize_spread(self.series)


@dataclass
class BoundRow:
    candidate: str
    metrics: dict[str, BoundStat]
    gates: BoundGates
    notes: tuple[str, ...] = ()

    def __str__(self) -> str:
        gate = "GATES OK" if self.gates.passed else "DISQUALIFIED: " + "; ".join(self.gates.failures)
        body = "; ".join(f"{k}={v}" for k, v in self.metrics.items())
        return f"{self.candidate}: {gate} | {body} | {'; '.join(self.notes)}"


@dataclass
class BoundScorecard:
    rows: list[BoundRow]
    winner: str | None
    verdict: str

    def __str__(self) -> str:
        return f"VERDICT: {self.verdict}\n" + "\n".join(str(r) for r in self.rows)


def _series_for(name: str, values: Sequence[float] | None, n_runs: int,
                min_runs: int) -> SC.MetricSeries:
    direction = "lower_is_better" if name in _LOWER_IS_BETTER else "higher_is_better"
    if values is None:
        per_run = [ME.MetricValue.unavailable(
            name, f"{name} was not measured in this run", direction=direction)] * max(n_runs, 1)
    else:
        per_run = [ME.MetricValue.measured(name, v, direction=direction) for v in values]
    return SC.build_series(name, per_run, n_runs, min_runs)


def build_scorecard(candidates, *, min_margin: float = 0.03,  # noqa: ANN001 - contract shape
                    required_metrics: Sequence[str] = (),
                    primary_metric: str = "claim_f1") -> BoundScorecard:
    """Contract ``build_scorecard`` over ``compare.decide``.

    ``min_runs_for_ranking`` is pinned to 2 — the lowest value the impl's own policy model permits — so the
    replication gate is exercised at its real structural floor rather than at a number chosen here.
    """
    config = _config(min_margin, required_metrics)
    wanted = list(dict.fromkeys((*required_metrics, primary_metric)))
    min_runs = config.replication.min_runs_for_ranking

    scores: list[SC.CandidateScore] = []
    rows: list[BoundRow] = []
    for c in candidates:
        runs_by_metric: dict[str, Any] = dict(c.get("runs") or {})
        names = list(dict.fromkeys((*wanted, *runs_by_metric)))
        n_runs = max((len(v) for v in runs_by_metric.values() if v), default=0)
        series = {n: _series_for(n, runs_by_metric.get(n), n_runs, min_runs) for n in names}
        bound_gates = evaluate_gates(c)

        run_scores = tuple(
            SC.RunScore(candidate_id=str(c["name"]), run_index=i, metrics={}, claims=())
            for i in range(n_runs)
        )
        scores.append(SC.CandidateScore(
            candidate_id=str(c["name"]), label=str(c["name"]),
            model_id=str(c.get("model_id", "")), gates=bound_gates.report,
            series=series, runs=run_scores,
        ))
        rows.append(BoundRow(
            candidate=str(c["name"]),
            metrics={
                n: BoundStat(
                    runs=tuple(series[n].values) if series[n].values else None,
                    measured=series[n].status == "measured",
                    mean=series[n].mean, spread=series[n].stdev, series=series[n],
                )
                for n in names
            },
            gates=bound_gates,
        ))

    verdict, _ = C.decide(scores, config)
    by_name = {r.candidate: r for r in rows}
    for name, reason in verdict.disqualified.items():
        if name in by_name:
            by_name[name].notes = (*by_name[name].notes,
                                   f"cannot win: gating precondition failed — {reason}")
    statement = verdict.statement
    if verdict.disqualified:
        statement += " DISQUALIFIED: " + "; ".join(
            f"{k}: gating precondition failed — {v}" for k, v in verdict.disqualified.items())
    return BoundScorecard(rows=rows, winner=verdict.winner, verdict=statement)


__all__ = [
    "BoundFaithfulness", "BoundGates", "BoundMatch", "BoundScorecard",
    "build_scorecard", "evaluate_gates", "match_claims", "match_policy",
    "score_faithfulness", "to_candidate", "to_surface",
]
