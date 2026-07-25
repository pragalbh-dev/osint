"""The declared contract the RK-BAKEOFF harness must satisfy — plus the two stand-ins the gates run against.

**Why this file exists.** The test hand is implementation-blind (plan §9, "three hands"): these gates are
written from plan §8 *before and independent of* how the harness gets built. A blind gate that can only
raise ``ImportError`` proves nothing — it would go green the moment a module with the right name exists,
whatever it does. So every gate here is written as a **property check over a resolved harness**, and this
module resolves that harness in one of two ways:

* **the real implementation**, if a plausibly-named callable is found under ``eval.extraction`` (best-effort
  discovery, see :func:`_discover`); the gate then binds to the shipped harness at integration; or
* **the NAIVE stand-in** below — a deliberately, *plausibly* wrong harness: it ranks candidates by mean
  score, ignores run-to-run spread, accepts a single run as truth, folds gate failures in as a weight, and
  scores an unmeasured metric as zero. That is what a well-meaning implementer builds if nobody writes these
  gates. Against it every gate fails **on its own property assertion**, with a message naming the property —
  never on an import.

The REFERENCE stand-in is the same contract implemented *correctly*, at the minimum size that satisfies the
spec. Each gate file runs its checks against the reference too (the ``…_positive_control`` tests). Those must
PASS. That is the non-vacuity proof: a check that fires on the naive harness and stays quiet on the correct
one is discriminating, not a permanent red light.

--------------------------------------------------------------------------------------------------
THE CONTRACT (plain data in, plain data out — so an independently-built harness can be driven by it)
--------------------------------------------------------------------------------------------------

**Candidate** — one model under test::

    {
      "name": "gemini",
      "model_id": "gemini-flash-latest",     # PINNED id required to win (plan §8 gate 3)
      "vlm_capable": True,                   # natively multimodal, or a declared multimodal tier retains
                                             #   the locked in-scope VLM path (plan §8 gate 1)
      "live_in_shipped_image": True,         # SDK installed + live-extracts inside the shipped image
      "freezes_seed_bundles": True,          # is the producer that freezes the seed bundles
                                             #   (live_in_shipped_image AND freezes ⇒ KEYLESS≡LIVE, gate 2)
      "runs": {                              # metric -> per-run values; None ⇒ UNMEASURED, not zero
          "claim_f1": [0.81, 0.83, 0.82],
          "citation_faithfulness": [1.0, 1.0, 1.0],
          "fabrication_rate": [0.0, 0.0, 0.0],   # lower is better
          "coref_binding": None,                 # e.g. awaiting S3 — must render "unmeasured"
      },
    }

**Claim** — one extracted or gold tuple::

    {"subject": "HQ-9/P", "predicate": "supplies-component", "object": "HT-233",
     "doc_id": "d01", "span": [12, 48]}

**Required harness surface** (any of the discovered aliases; see ``_SURFACES``):

* ``match_claims(gold, pred, *, rule) -> result`` with ``.precision .recall .f1 .pairs`` and an
  introspectable, non-empty ``.rule`` / ``.describe()``. Stateless, one-to-one, order-independent.
* ``score_faithfulness(pred, docs) -> result`` with ``.rate`` and ``.unfaithful`` — a claim is faithful only
  if its cited span actually supports it (G4: the span slices back).
* ``evaluate_gates(candidate) -> report`` with ``.passed`` and ``.failures`` (each failure NAMED).
* ``build_scorecard(candidates, *, min_margin, required_metrics, primary_metric) -> scorecard`` with
  ``.winner`` (str | None), ``.verdict`` (str) and ``.rows`` (per candidate: ``.runs`` per metric, a
  ``.spread``, a ``.measured`` flag, and the gate report).
"""

from __future__ import annotations

import difflib
import importlib
import statistics
from dataclasses import dataclass
from typing import Any

# ── discovery of the real implementation (best-effort; integration reconciles names) ──────────────

_MODULES = (
    "eval.extraction.matcher",
    "eval.extraction.scorer",
    "eval.extraction.gates",
    "eval.extraction.scorecard",
    "eval.extraction.orchestrator",
    "eval.extraction.bakeoff",
    "eval.extraction",
)

_SURFACES: dict[str, tuple[str, ...]] = {
    "match_claims": ("match_claims", "match", "score_claims", "claim_prf1"),
    "score_faithfulness": (
        "score_faithfulness", "citation_faithfulness", "faithfulness", "score_citations",
    ),
    "evaluate_gates": ("evaluate_gates", "check_gates", "gate_report", "evaluate_preconditions"),
    "build_scorecard": ("build_scorecard", "scorecard", "compare_candidates", "build_report"),
}


def _discover(surface: str) -> Any | None:
    """Return the shipped callable for ``surface``, or ``None`` if the harness is not built yet."""
    for mod_name in _MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:  # not built / import-time dependency missing — not this gate's business
            continue
        for attr in _SURFACES[surface]:
            fn = getattr(mod, attr, None)
            if callable(fn):
                return fn
    return None


#: True when no shipped harness was found and the gates are checking the NAIVE stand-in.
#: Reported in every failure message so a red gate is never mistaken for a missing import.
USING_STAND_IN = all(_discover(s) is None for s in _SURFACES)

_WHY = (
    "no shipped harness found under eval.extraction — this property was checked against the NAIVE "
    "stand-in in tests/bakeoff/_bakeoff_contract_spec.py, which violates it by construction"
    if USING_STAND_IN
    else "checked against the shipped eval.extraction harness"
)


def why(msg: str) -> str:
    """Attach the resolution provenance to a property-failure message."""
    return f"{msg}\n[harness resolution: {_WHY}]"


# ── normalised result views (so a gate never depends on the impl's exact attribute spelling) ──────

def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for n in names:
        if isinstance(obj, dict) and n in obj:
            return obj[n]
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


@dataclass(frozen=True)
class MatchView:
    precision: float
    recall: float
    f1: float
    pairs: tuple[tuple[int, int], ...]
    rule: Any


def match_view(res: Any) -> MatchView:
    pairs = _get(res, "pairs", "matches", "matched", default=()) or ()
    return MatchView(
        precision=float(_get(res, "precision", "p", default=0.0)),
        recall=float(_get(res, "recall", "r", default=0.0)),
        f1=float(_get(res, "f1", "f_1", "fscore", default=0.0)),
        pairs=tuple(tuple(p) for p in pairs),
        rule=_get(res, "rule", "match_rule", "config", "describe"),
    )


@dataclass(frozen=True)
class ScorecardView:
    winner: str | None
    verdict: str
    rows: dict[str, Any]
    raw: Any

    def row(self, name: str) -> Any:
        return self.rows[name]

    def text(self) -> str:
        """All human-readable output of the scorecard, lowercased — what a reader would actually see."""
        parts = [str(self.verdict), str(self.raw)]
        render = _get(self.raw, "render", "to_text", "as_text", "markdown")
        if callable(render):
            try:
                parts.append(str(render()))
            except Exception:
                pass
        return " ".join(parts).lower()


def scorecard_view(res: Any) -> ScorecardView:
    rows_any = _get(res, "rows", "candidates", "results", default=())
    rows: dict[str, Any] = {}
    if isinstance(rows_any, dict):
        rows = dict(rows_any)
    else:
        for r in rows_any or ():
            rows[str(_get(r, "candidate", "name", default=""))] = r
    winner = _get(res, "winner", "primary", "chosen")
    return ScorecardView(
        winner=None if winner is None else str(winner),
        verdict=str(_get(res, "verdict", "conclusion", "summary", default="")),
        rows=rows,
        raw=res,
    )


def row_metric(row: Any, metric: str) -> Any:
    """The per-metric stat block on a scorecard row, whatever the impl calls the container."""
    stats = _get(row, "metrics", "metric_stats", "stats", "scores", default=None)
    if isinstance(stats, dict) and metric in stats:
        return stats[metric]
    return _get(row, metric)


def stat_runs(stat: Any) -> Any:
    """The per-run values behind a stat — ``None`` if the harness kept only an aggregate."""
    return _get(stat, "runs", "values", "samples", "observations", "per_run")


def stat_spread(stat: Any) -> Any:
    """The reported dispersion of a stat — ``None`` if the harness collapsed N runs to a point."""
    return _get(stat, "spread", "stdev", "std", "stddev", "sigma", "variance", "range", "iqr")


def stat_measured(stat: Any) -> bool | None:
    """Explicit measured/unmeasured flag, if the harness carries one."""
    return _get(stat, "measured", "is_measured", "available")


# ── the sample data types the gates build (test-owned; the harness only sees plain dicts) ─────────

def claim(subject: str, predicate: str, obj: str, doc_id: str = "d01",
          span: tuple[int, int] = (0, 0)) -> dict[str, Any]:
    return {"subject": subject, "predicate": predicate, "object": obj,
            "doc_id": doc_id, "span": list(span)}


def candidate(name: str, *, model_id: str = "pinned-model-1.0", vlm_capable: bool = True,
              live_in_shipped_image: bool = True, freezes_seed_bundles: bool = True,
              runs: dict[str, list[float] | None] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "model_id": model_id,
        "vlm_capable": vlm_capable,
        "live_in_shipped_image": live_in_shipped_image,
        "freezes_seed_bundles": freezes_seed_bundles,
        "runs": dict(runs or {}),
    }


#: A clean, replicated, gate-passing metric block — the baseline the gates perturb one axis at a time.
def clean_runs(f1: list[float]) -> dict[str, list[float] | None]:
    n = len(f1)
    return {
        "claim_f1": list(f1),
        "citation_faithfulness": [1.0] * n,
        "fabrication_rate": [0.0] * n,
        "structured_output_reliability": [1.0] * n,
    }


REQUIRED_METRICS = ("claim_f1", "citation_faithfulness", "fabrication_rate")
PRIMARY_METRIC = "claim_f1"
#: Lower-is-better metrics; a harness must not "improve" by maximising these.
LOWER_IS_BETTER = frozenset({"fabrication_rate", "cost_usd", "latency_s"})


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The NAIVE stand-in — plausibly wrong. Every gate must fire on it.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _norm(s: str) -> str:
    return " ".join(str(s).lower().split())


class _NaiveMatchResult:
    def __init__(self, precision: float, recall: float, f1: float, pairs: list[tuple[int, int]]):
        self.precision, self.recall, self.f1, self.pairs = precision, recall, f1, pairs
        # NOTE: no `.rule` — the naive matcher's leniency is undocumented and unconfigurable.


class _NaiveMatcher:
    """Exact-tuple, many-to-one, and *stateful*: it remembers which gold claims it has already used.

    Every one of those is a real bug class seen in hand-rolled scorers. The state is what makes it
    unstable across invocations — the second call on the same inputs scores lower.
    """

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()

    def __call__(self, gold, pred, *, rule=None):  # noqa: ANN001 - test stand-in
        keys = [(_norm(g["subject"]), _norm(g["predicate"]), _norm(g["object"])) for g in gold]
        pairs: list[tuple[int, int]] = []
        for j, p in enumerate(pred):
            k = (_norm(p["subject"]), _norm(p["predicate"]), _norm(p["object"]))
            if k in self._seen:
                continue
            for i, gk in enumerate(keys):
                if gk == k:
                    pairs.append((i, j))  # many-to-one: the same gold can be claimed twice
            self._seen.add(k)
        precision = len(pairs) / len(pred) if pred else 0.0
        recall = len(pairs) / len(gold) if gold else 0.0
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        return _NaiveMatchResult(precision, recall, f1, pairs)


class _NaiveFaithfulness:
    """Assumes the model cited honestly. Never looks at the document."""

    def __call__(self, pred, docs):  # noqa: ANN001 - test stand-in
        return type("R", (), {"rate": 1.0, "unfaithful": []})()


class _NaiveGates:
    """Reports everything as satisfied — the gate that is never actually evaluated."""

    def __call__(self, cand):  # noqa: ANN001 - test stand-in
        return type("R", (), {"passed": True, "failures": []})()


class _NaiveScorecard:
    """Ranks by mean primary metric. One run is truth; spread is discarded; a gate failure is a weight;
    an unmeasured metric scores zero."""

    def __call__(self, candidates, *, min_margin=0.0, required_metrics=(),  # noqa: ANN001
                 primary_metric=PRIMARY_METRIC):
        rows = []
        best_name, best_score = None, float("-inf")
        wanted = list(dict.fromkeys((*required_metrics, primary_metric)))
        for c in candidates:
            runs = c["runs"].get(primary_metric) or []
            mean = statistics.fmean(runs) if runs else 0.0  # unmeasured ⇒ 0.0
            gates = _NaiveGates()(c)
            score = mean * (0.9 if not gates.passed else 1.0)  # gate folded in as a weight
            # Keeps only the point estimate; an unmeasured metric is carried as a real 0.0.
            metrics = {m: (statistics.fmean(c["runs"][m]) if c["runs"].get(m) else 0.0)
                       for m in dict.fromkeys((*wanted, *c["runs"]))}
            rows.append(type("Row", (), {
                "candidate": c["name"], "mean": mean, "score": score, "gates": gates,
                "metrics": metrics,
            })())
            if score > best_score:
                best_name, best_score = c["name"], score
        return type("SC", (), {
            "winner": best_name,
            "verdict": f"{best_name} scores highest on {primary_metric}",
            "rows": rows,
        })()


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The REFERENCE stand-in — the same contract, implemented correctly, at minimum size.
# Used only by the ``…_positive_control`` tests, to prove each gate can be satisfied.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

DEFAULT_RULE: dict[str, Any] = {
    "kind": "fuzzy-surface, exact-predicate, one-to-one",
    "surface_threshold": 0.85,
    "normalisation": "casefold + whitespace-collapse",
    "similarity": "difflib.SequenceMatcher ratio",
}


@dataclass(frozen=True)
class RefMatchResult:
    precision: float
    recall: float
    f1: float
    pairs: tuple[tuple[int, int], ...]
    rule: dict[str, Any]

    def describe(self) -> str:
        return (f"{self.rule['kind']}; surfaces matched at ratio >= {self.rule['surface_threshold']} "
                f"({self.rule['similarity']}, {self.rule['normalisation']}); predicates exact")


def reference_match_claims(gold, pred, *, rule: dict[str, Any] | None = None) -> RefMatchResult:  # noqa: ANN001
    rule = dict(DEFAULT_RULE if rule is None else rule)
    thr = float(rule.get("surface_threshold", DEFAULT_RULE["surface_threshold"]))

    def sim(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()

    scored: list[tuple[float, int, int]] = []
    for i, g in enumerate(gold):
        for j, p in enumerate(pred):
            if _norm(g["predicate"]) != _norm(p["predicate"]):
                continue
            s = min(sim(g["subject"], p["subject"]), sim(g["object"], p["object"]))
            if s >= thr:
                scored.append((s, i, j))
    # Deterministic, one-to-one greedy: best similarity first, ties broken by stable content keys so
    # the result does not depend on input ordering.
    def key(t: tuple[float, int, int]) -> tuple:
        s, i, j = t
        g, p = gold[i], pred[j]
        return (-s, _norm(g["subject"]), _norm(g["predicate"]), _norm(g["object"]),
                _norm(p["subject"]), _norm(p["object"]), str(p.get("doc_id")), tuple(p.get("span", ())))

    used_g: set[int] = set()
    used_p: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _s, i, j in sorted(scored, key=key):
        if i in used_g or j in used_p:
            continue
        used_g.add(i)
        used_p.add(j)
        pairs.append((i, j))
    m = len(pairs)
    precision = m / len(pred) if pred else 0.0
    recall = m / len(gold) if gold else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return RefMatchResult(precision, recall, f1, tuple(sorted(pairs)), rule)


@dataclass(frozen=True)
class RefFaithfulness:
    rate: float
    unfaithful: tuple[int, ...]


def reference_score_faithfulness(pred, docs) -> RefFaithfulness:  # noqa: ANN001
    """G4: a claim is faithful only if the span it cites actually slices back and supports it."""
    bad: list[int] = []
    for j, p in enumerate(pred):
        text = docs.get(p.get("doc_id"), "")
        start, end = (list(p.get("span")) + [0, 0])[:2]
        span = _norm(text[start:end])
        if not span or _norm(p["subject"]) not in span or _norm(p["object"]) not in span:
            bad.append(j)
    rate = 0.0 if not pred else (len(pred) - len(bad)) / len(pred)
    return RefFaithfulness(rate, tuple(bad))


@dataclass(frozen=True)
class RefGateReport:
    passed: bool
    failures: tuple[str, ...]


_FLOATING_TOKENS = ("latest", "preview", "exp", "experimental")


def _is_floating(model_id: str) -> bool:
    tokens = str(model_id).replace("@", "-").replace("_", "-").replace(":", "-").lower().split("-")
    return any(t in _FLOATING_TOKENS for t in tokens)


def reference_evaluate_gates(cand) -> RefGateReport:  # noqa: ANN001
    f: list[str] = []
    if not cand.get("vlm_capable"):
        f.append("VLM-IMAGERY: would drop the locked in-scope VLM imagery path")
    if not cand.get("live_in_shipped_image"):
        f.append("KEYLESS-EQ-LIVE: does not live-extract inside the shipped image")
    if not cand.get("freezes_seed_bundles"):
        f.append("KEYLESS-EQ-LIVE: is not the producer that freezes the seed bundles")
    if _is_floating(cand.get("model_id", "")):
        f.append(f"PINNED-ID: {cand.get('model_id')!r} is a floating alias, not a pinned model id")
    return RefGateReport(not f, tuple(f))


@dataclass
class RefStat:
    runs: tuple[float, ...] | None
    measured: bool
    replicated: bool
    mean: float | None
    spread: float | None
    lo: float | None
    hi: float | None

    def __str__(self) -> str:
        if not self.measured:
            return "unmeasured"
        spread = "spread unknown (unreplicated)" if self.spread is None else f"± {self.spread:.4f}"
        return f"{self.mean:.4f} {spread} over {len(self.runs or ())} runs {list(self.runs or ())}"


def _stat(values: list[float] | None) -> RefStat:
    if values is None or len(values) == 0:
        return RefStat(None, False, False, None, None, None, None)
    vs = tuple(float(v) for v in values)
    return RefStat(vs, True, len(vs) >= 2, statistics.fmean(vs),
                   statistics.pstdev(vs) if len(vs) >= 2 else None, min(vs), max(vs))


@dataclass
class RefRow:
    candidate: str
    metrics: dict[str, RefStat]
    gates: RefGateReport
    eligible: bool
    notes: tuple[str, ...]

    def __str__(self) -> str:
        gate = "GATES OK" if self.gates.passed else "DISQUALIFIED: " + "; ".join(self.gates.failures)
        body = "; ".join(f"{k}={v}" for k, v in self.metrics.items())
        return f"{self.candidate}: {gate} | {body} | {'; '.join(self.notes)}"


@dataclass
class RefScorecard:
    rows: list[RefRow]
    winner: str | None
    verdict: str

    def __str__(self) -> str:
        return f"VERDICT: {self.verdict}\n" + "\n".join(str(r) for r in self.rows)


def _better(a: RefStat, b: RefStat, metric: str, min_margin: float) -> str:
    """'a' / 'b' / '' (no measured difference) for one metric — margin AND noise band must both clear."""
    if not (a.measured and b.measured and a.replicated and b.replicated):
        return ""
    gap = (a.mean or 0.0) - (b.mean or 0.0)
    if metric in LOWER_IS_BETTER:
        gap = -gap
    noise = (a.spread or 0.0) + (b.spread or 0.0)
    if abs(gap) < min_margin or abs(gap) <= noise:
        return ""
    return "a" if gap > 0 else "b"


def reference_build_scorecard(candidates, *, min_margin: float,  # noqa: ANN001
                              required_metrics=REQUIRED_METRICS,
                              primary_metric: str = PRIMARY_METRIC) -> RefScorecard:
    required = tuple(dict.fromkeys((*required_metrics, primary_metric)))
    rows: list[RefRow] = []
    for c in candidates:
        metrics = {m: _stat(c["runs"].get(m)) for m in dict.fromkeys((*required, *c["runs"]))}
        gates = reference_evaluate_gates(c)
        notes: list[str] = []
        unmeasured = [m for m in required if not metrics[m].measured]
        unreplicated = [m for m in required if metrics[m].measured and not metrics[m].replicated]
        if unmeasured:
            notes.append("unmeasured required metric(s): " + ", ".join(unmeasured))
        if unreplicated:
            notes.append("unreplicated (single run, spread unknown): " + ", ".join(unreplicated))
        if not gates.passed:
            notes.append("cannot win: gating precondition failed")
        rows.append(RefRow(c["name"], metrics, gates,
                           gates.passed and not unmeasured and not unreplicated, tuple(notes)))

    blocked = [r for r in rows if not r.eligible]
    eligible = [r for r in rows if r.eligible]

    if any("unmeasured required metric(s)" in n for r in rows for n in r.notes):
        return RefScorecard(rows, None, "no winner: a required metric is UNMEASURED — "
                                        + "; ".join(f"{r.candidate}: {n}" for r in rows for n in r.notes
                                                    if "unmeasured" in n))
    if any("unreplicated" in n for r in rows for n in r.notes):
        return RefScorecard(rows, None, "no winner: unreplicated — a single run is not a measurement; "
                                        "N>=2 runs with reported spread are required")
    if not eligible:
        return RefScorecard(rows, None, "no winner: every candidate failed a gating precondition — "
                                        + "; ".join(f"{r.candidate}: {'; '.join(r.gates.failures)}"
                                                    for r in blocked))

    def dominates(a: RefRow, b: RefRow) -> bool:
        # Fabrication + citation faithfulness are non-negotiable: a primary-metric lead cannot buy off a
        # materially worse score on either. They are not tradeable, so they veto rather than average.
        for guard in ("fabrication_rate", "citation_faithfulness"):
            if guard in a.metrics and guard in b.metrics:
                if _better(b.metrics[guard], a.metrics[guard], guard, min_margin) == "a":
                    return False
        return _better(a.metrics[primary_metric], b.metrics[primary_metric],
                       primary_metric, min_margin) == "a"

    winners = [a for a in eligible if all(dominates(a, b) for b in eligible if b is not a)]
    if len(winners) == 1 and len(eligible) > 1:
        w = winners[0]
        return RefScorecard(rows, w.candidate,
                            f"{w.candidate} wins: materially ahead on {primary_metric} "
                            f"(margin >= {min_margin} and outside the pooled run-to-run spread), "
                            f"gating preconditions satisfied")
    if len(eligible) == 1:
        # Plan §8's honest fallback: a sole admissible candidate is a legitimate outcome, but the
        # scorecard must say it is NOT a measured comparison rather than imply one that did not run.
        w = eligible[0]
        caveat = ("the other candidate(s) were disqualified on gating preconditions ("
                  + "; ".join(f"{r.candidate}: {', '.join(r.gates.failures) or ', '.join(r.notes)}"
                              for r in blocked) + ")") if blocked else "no other candidate was measured"
        return RefScorecard(rows, w.candidate,
                            f"{w.candidate} stands as the only admissible candidate — {caveat}. "
                            "This is not a measured comparison between models")

    # No candidate dominates. Say *which* honest reason, and never invent a ranking.
    pairs = [(a, b) for a in eligible for b in eligible if a is not b]
    primary_all_within_noise = all(
        _better(a.metrics[primary_metric], b.metrics[primary_metric], primary_metric, min_margin) == ""
        for a, b in pairs
    )
    guard_diff = any(
        g in a.metrics and g in b.metrics
        and _better(a.metrics[g], b.metrics[g], g, min_margin) != ""
        for a, b in pairs for g in ("fabrication_rate", "citation_faithfulness")
    )
    if primary_all_within_noise and not guard_diff:
        return RefScorecard(rows, None,
                            "no measured difference: the gap between eligible candidates on "
                            f"{primary_metric} lies inside the minimum margin ({min_margin}) or the "
                            "pooled run-to-run spread; ranking them would be manufacturing a result "
                            "out of jitter")
    if guard_diff:
        return RefScorecard(rows, None,
                            "no winner: the candidates differ materially on a non-negotiable (citation "
                            f"faithfulness / fabrication). Those are not tradeable against {primary_metric}, "
                            "so a score lead does not buy a win and no ranking is issued")
    return RefScorecard(rows, None, "no winner: no candidate is materially ahead")


# ── the resolved surfaces the gates actually call ─────────────────────────────────────────────────

_naive_matcher_singleton = _NaiveMatcher()

MATCH = _discover("match_claims") or _naive_matcher_singleton
FAITHFULNESS = _discover("score_faithfulness") or _NaiveFaithfulness()
GATES = _discover("evaluate_gates") or _NaiveGates()
SCORECARD = _discover("build_scorecard") or _NaiveScorecard()


def do_match(gold, pred, *, rule=None):  # noqa: ANN001
    try:
        return match_view(MATCH(gold, pred, rule=rule))
    except TypeError:
        return match_view(MATCH(gold, pred))


def do_faithfulness(pred, docs):  # noqa: ANN001
    return FAITHFULNESS(pred, docs)


def do_gates(cand):  # noqa: ANN001
    return GATES(cand)


def do_scorecard(candidates, *, min_margin: float, required_metrics=REQUIRED_METRICS,
                 primary_metric: str = PRIMARY_METRIC) -> ScorecardView:
    return scorecard_view(SCORECARD(candidates, min_margin=min_margin,
                                    required_metrics=required_metrics,
                                    primary_metric=primary_metric))


def ref_scorecard(candidates, *, min_margin: float, required_metrics=REQUIRED_METRICS,
                  primary_metric: str = PRIMARY_METRIC) -> ScorecardView:
    return scorecard_view(reference_build_scorecard(
        candidates, min_margin=min_margin, required_metrics=required_metrics,
        primary_metric=primary_metric))


__all__ = [
    "DEFAULT_RULE", "LOWER_IS_BETTER", "PRIMARY_METRIC", "REQUIRED_METRICS", "USING_STAND_IN",
    "MatchView", "ScorecardView", "candidate", "claim", "clean_runs", "do_faithfulness", "do_gates",
    "do_match", "do_scorecard", "match_view", "ref_scorecard", "reference_build_scorecard",
    "reference_evaluate_gates", "reference_match_claims", "reference_score_faithfulness",
    "row_metric", "scorecard_view", "stat_measured", "stat_runs", "stat_spread", "why",
]
