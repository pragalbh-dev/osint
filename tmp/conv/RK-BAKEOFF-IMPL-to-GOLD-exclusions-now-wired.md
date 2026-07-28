# IMPL → GOLD hand: `precision_exclusions` is wired now, so the adapter's status prose is stale

**Branch:** `bakeoff/rk-impl` · **Nothing in your files was touched.** This is an observation, not a patch —
`eval/gold/adapter.py`, the two `.bakeoff.json` artefacts and the labeled slice are yours.

## What changed on my side

The harness now consumes all three of your declared hooks, per emitted claim, inside `score_run`:

- `precision_exclusions` → the returned keys leave the **precision denominator**
  (`matcher.MatchResult.precision_exclusions`, one definition of precision, enforced in the constructor:
  an excluded key must be unpaired, so precision can never exceed 1.0);
- `trap_avoidance` → a scored metric, declared a **veto** in `gates.non_negotiable_floors` and given no
  composite weight;
- `identity_over_read` → reported as a `count`, which structurally bars it from the composite (your N=2
  rule: "never a rate, never rank on it").

Consumer lives in `backend/eval/extraction/negative_gold.py`. It does **not** re-derive any of your
semantics — it only supplies observations and translates our document locators into your file namespace
(join key = the file *name*, since you cite repo-relative paths and the ingest lane cites whatever the
driver put on `DocInput.file`). Measured on the real slice, through the loaders:

| candidate | emitted | matched | precision before | precision after | excluded | trap_avoidance |
|---|---|---|---|---|---|---|
| perfect (65 positives) | 65 | 65 | 1.0000 | 1.0000 | 0 | 1.0000 |
| verbose-honest (+27 neutral) | 92 | 65 | 0.7065 | 1.0000 | 27 | 1.0000 |
| unmodelled only (+19) | 84 | 65 | 0.7738 | 1.0000 | 19 | 1.0000 |
| fabricating (+11 traps) | 76 | 65 | 0.8553 | 0.8553 | 0 | 0.0000 |

Your "the trap wins" rule holds: the fabricator's precision is byte-identical before and after.

## The stale strings (yours to change, or to leave)

`NEGATIVE_GOLD_SEMANTICS` still declares, and the derived `claim-gold.bakeoff.json` still publishes:

- `anti_coref.precision_exclusion_automatic` — "**NO** — unwired today … the other five are live
  over-penalties"
- `ambiguous.precision_exclusion_automatic` — "**NO** — unwired today, same as anti_coref …"
- `unmodelled.precision_exclusion_automatic` — "**NO** — unwired today, and this is the class where it
  bites hardest …"
- `unmodelled.precision_denominator` — "excluded — REQUIRES harness wiring; see the report"

and `adapter.main()` prints `negative classes needing harness wiring to be neutral: [...]`, derived from
`.startswith("NO")`. All four statements are now false: the wiring exists and is regression-tested
(`tests/extraction_bakeoff/test_precision_exclusions.py`,
`tests/gold_adapter/test_precision_exclusions_measured.py`).

Direction of the error is conservative — the artefact understates the instrument rather than a candidate —
so nothing is blocked on this. But a reviewer reading the derived file will conclude candidates are being
over-penalised when they are not.

If you update them, note two couplings:

1. `tests/gold_adapter/test_negative_gold_semantics.py:122` asserts the three strings start with `"NO"`;
2. `test_reproducible` compares the regenerated artefact against the committed one, so
   `python -m eval.gold.adapter` has to be re-run in the same commit.

A suggested shape, so the field keeps meaning "is it automatic *without* a harness call" while stating who
does call it: keep the `NO` prefix and append "— wired by `eval.extraction.negative_gold`, consumed in
`score_run`; see the measured table above". That leaves the CLI's `startswith("NO")` reading correct (the
exclusion is still not automatic — it requires the call) while removing "unwired today".
