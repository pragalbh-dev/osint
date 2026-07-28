# RK-BAKEOFF — live run result, 2026-07-26 (second sitting)

## VERDICT: **`NO_MEASURED_DIFFERENCE`** between `claude-opus-5` and `gemini-3.6-flash`.
## `gpt-5.6-sol` was **NOT MEASURED** — an account entitlement, not a quality finding.

**No primary extractor is named.** The two candidates that could be run five times each are separated by
0.0095 on the weighted composite, against a required margin of 0.0429 — the gap is **four and a half times
smaller** than the run-to-run noise it would have to clear. Naming either one would be a ranking invented
from jitter, which is the exact failure this instrument exists to prevent.

That is a real result, not a failure to get one: two of the three candidates *were* measured, five runs
each, on every required criterion, and the answer the measurement gives is **"these two are not separable
on this evidence."** What it took to say that, what it cost, and what it explicitly cannot decide are
below.

This supersedes the previous version of this file (three deaths, no scorecard). The history it recorded is
kept in §7.

---

## 1. Preflight — checked before anything was spent

| check | result |
|---|---|
| candidates eligible on dry gates | **3/3 ELIGIBLE** — `anthropic-opus-5`, `gemini-3-6-flash`, `openai-gpt-5-6-sol` |
| coreference channel | **LIVE** — extraction pass 2 unconditional; `coref_binding` measurable |
| VLM imagery gate | evidenced for all three on the real corpus frame `d17b_withheld_gap.png` |
| keys | all three present; names only ever printed, never values |

Every one of the four dry gates (`vlm_imagery_path`, `keyless_equals_live`, `pinned_model_id`,
`exercisable`) passed for every candidate. Nothing was excluded by configuration; the three-way was real on
paper.

## 2. The spend plan, printed before spending

```
documents:  7 text + 1 standalone image frame  (corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.png)
runs:       5 per candidate      passes: pass 1 (text) + pass 2 (coreference)
calls/run:  8 – 15
TOTAL:      120 – 225   (8–15 × 5 runs × 3 candidates)      [projection ~195]
GPT lane wall-clock floor from pacing alone: 13m00s – 24m40s
```

In band and consistent with the ~195 authorised. The image **is** in the slice, so the imagery gate reads
evidence rather than UNKNOWN.

## 3. What actually happened — two deaths, and resume doing its job

| # | invocation | window (UTC) | how far it got | why it stopped |
|---|---|---|---|---|
| A | `inv-20260726T155646Z-52deac` | 15:56:45 → 16:14:33 | **Opus 35/35 docs, Gemini 35/35 docs, GPT 11/35** | `openai.RateLimitError` 429 — **requests per minute**: "Limit 3, Used 3, Requested 1" |
| B | `inv-20260726T162104Z-dab751` | 16:21:02 → 16:22:47 | resumed: 81/105 docs replayed free, GPT re-entered where it stopped | `openai.RateLimitError` 429 — **tokens per minute**: "Limit 10000, Used 5431, Requested 6561" |
| C | scoring pass | 16:33:3x → 16:33:59 | **0 calls** — all 70 Opus+Gemini documents replayed from disk | completed; scorecard rendered |

**Resume worked exactly as designed, and this run is the proof.** Attempt A's death cost nothing already
bought: attempt B re-entered with **81 of 105 document-extractions reusable** and re-bought none of them.
In the previous sitting the same class of failure discarded ~225 already-billed Opus calls.

**Attempt A died pacing *at* the cap, and that was our error, not the provider's.** The declared rate was
the account's exact 3 req/min — one start every 20.0s — which puts three starts inside every trailing
minute, so the fourth start races the provider's own window boundary. Any jitter loses that race.
`config/bakeoff.yaml → rate_limits.openai` is now **2 req/min (30.0s spacing)**: pace *under* a cap, never
*on* it. This changes no gate, no weight, no margin rule and no match policy, and it is not a retry — a
returned 429 is still never re-issued, because `structured_output_reliability` exists to score exactly what
a provider returns.

**Attempt B then hit a second, independent entitlement**: a 10,000 tokens-per-minute ceiling against
extraction requests of ~6,500 tokens each. That admits roughly **one call per minute**, so the GPT lane's
remaining 24 documents (~52 calls) would have taken ~50 minutes and pushed total spend to ~226 calls —
**past the 225 ceiling of the plan that was authorised** — while chasing a wall that had already moved once
under us. Per the standing instruction not to buy a third run chasing a fault: **stopped, and scored what
was bought.**

## 4. Actual spend against projection

| | calls |
|---|---|
| projected | 120 – 225 (**~195** expected) |
| **billed, persisted to disk** | **174** — Opus 75 (35 docs), Gemini 75 (35 docs), GPT 24 (11 docs) |
| billed, lost in flight when a process died | ≤ ~3 (GPT lane only; `max_concurrent: 1`) |
| replayed from disk at zero cost (scoring pass) | 150 |
| **actual total** | **≈ 177 — under the ~195 projection, inside the band** |

Of the 174 persisted, **10 were standalone-image calls** (5 per completed candidate — one per run) and 164
were text-lane calls. **Zero call-level errors** are recorded in any persisted call, for any candidate.

**Wall clock: 37m14s** end to end (15:56:45 → 16:33:59Z), of which ~19m30s was live extraction and the
remainder was triage between the two attempts. The GPT lane's pacing floor was the binding constraint
throughout, exactly as projected.

## 5. THE SCORECARD

**Replication: 5 runs/candidate. Margin: max(0.03, 2.0 × pooled SD).**

Both candidates were sampled in a **single sitting** (`inv-20260726T155646Z-52deac`), so `determinism`
means what it normally means. The scoring pass that produced this table was a **replay** of that sitting's
artefacts — the harness stamps it "Replayed, not re-run" — and replay changes no number, because a bundle
is reused only when the pinned model id, the document set (identity *and* content) and the prompt/schema
digest all still match.

### 5a. Gates — PASS/FAIL to win, never weighted

| candidate | model id | dry gates | non-negotiables | eligible to win |
|---|---|---|---|---|
| Anthropic Opus 5 | `claude-opus-5` | 4/4 PASS (imagery **6/6** standalone-image calls: recorded probe + 5/5 this run) | all three measured | **YES** |
| Gemini Flash 3.6 | `gemini-3.6-flash` | 4/4 PASS (imagery **6/6**) | all three measured | **YES** |
| OpenAI GPT 5.6 Sol | `gpt-5.6-sol` | 4/4 PASS on the dry gates | **NOT MEASURED** — lane unfinished | **not exercised** |

### 5b. Measured criteria — mean ± sample SD over 5 runs

| metric | weight | `anthropic-opus-5` | `gemini-3-6-flash` | verdict |
|---|---|---|---|---|
| `coref_binding` | **5.0** | 0.3511 ± 0.0881 | 0.3658 ± 0.0243 | NO MEASURED DIFFERENCE |
| `discriminator_capture` | 4.5 | 0.2952 ± 0.0621 | 0.1882 ± 0.1404 | NO MEASURED DIFFERENCE |
| `citation_faithfulness` | 4.5 · **VETO** | 0.7891 ± 0.0103 | **0.8331 ± 0.0191** | **gemini better** |
| `extract_only_stated` | 4.5 · **VETO** | 0.9550 ± 0.0110 | **0.9852 ± 0.0055** | **gemini better** (barely — §6) |
| `discriminator_fabrication_avoidance` | 4.0 | 0.9217 ± 0.0567 | 0.8842 ± 0.0753 | NO MEASURED DIFFERENCE |
| `structured_output_reliability` | 3.0 | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | NO MEASURED DIFFERENCE |
| `surface_f1` | 3.0 | 0.2006 ± 0.0098 | 0.2059 ± 0.0220 | NO MEASURED DIFFERENCE |
| `graph_recall` | 3.0 | **0.5050 ± 0.0209** | 0.4550 ± 0.0209 | **opus better** |
| `determinism` | 2.0 | 0.6043 ± 0.0221 | 0.6247 ± 0.0240 | NO MEASURED DIFFERENCE |
| `kind_tagging` | 0.5 | not measured — the gold slice labels no claim kinds | same | not rankable |
| `trap_avoidance` | 0 · **VETO** | **0.8727 ± 0.0498** | 0.7455 ± 0.0407 | **opus better** |
| `graph_node_recall` | 0 | **0.6000 ± 0.0211** | 0.5308 ± 0.0172 | **opus better** |
| `graph_edge_recall` | 0 | 0.3286 ± 0.0639 | 0.3143 ± 0.0391 | NO MEASURED DIFFERENCE |
| `surface_recall` | 0 | **0.3662 ± 0.0201** | 0.2985 ± 0.0257 | **opus better** |
| `surface_precision` | 0 | 0.1382 ± 0.0073 | 0.1573 ± 0.0188 | NO MEASURED DIFFERENCE |
| `identity_over_read` | 0 (count, N=2) | 0.0000 | 0.0000 | never ranked on |
| `latency_s` | 0 | 261.86 ± 5.12 s | 234.79 ± 24.32 s | NO MEASURED DIFFERENCE |
| `cost_usd` | 0 | **UNPRICED** | **UNPRICED** | not rankable |

### 5c. The composite, and the verdict

Composite = weighted mean **per run** of the nine rate metrics carrying weight (`coref_binding` 5.0,
`discriminator_capture` 4.5, `citation_faithfulness` 4.5, `extract_only_stated` 4.5,
`discriminator_fabrication_avoidance` 4.0, `structured_output_reliability` 3.0, `surface_f1` 3.0,
`graph_recall` 3.0, `determinism` 2.0). `trap_avoidance` carries **no weight by design** — it is a veto,
and a veto inside a composite is just a heavy weight a good-enough model can pay.

| | per-run composite | mean ± SD |
|---|---|---|
| `anthropic-opus-5` | 0.6147, 0.6328, 0.6107, 0.6229, 0.6451 | **0.6252 ± 0.0140** |
| `gemini-3-6-flash` | 0.6378, 0.6050, 0.6173, 0.6426, 0.5760 | **0.6157 ± 0.0269** |

**gap = 0.0095 · pooled SD = 0.0215 · required margin = 0.0429 → INSIDE NOISE.**

> **`NO_MEASURED_DIFFERENCE`** — "every gap between them sits inside the run-to-run noise at the configured
> margin. Naming one of them would be a ranking invented from jitter."

Nothing was re-weighted, excluded or relaxed to reach this. Both **required** metrics (`coref_binding`,
`discriminator_capture`) were measured for both candidates, so this is a measured tie and **not**
`INSUFFICIENT_CRITERIA`.

---

## 6. Honest interpretation — what this decides, and what it does not

### What it decides

1. **On this slice, Opus 5 and Gemini 3.6 Flash are not separable as extractors.** The composite gap is
   1/4.5 of the noise floor. This is not "too close to call"; it is *measured indistinguishability* in the
   aggregate.
2. **Both are structurally usable as the seed producer.** Both pass all four dry gates on their own merits,
   both drove the real imagery lane 6/6, and both returned **well-formed structured output on every one of
   75 calls** (`structured_output_reliability` = 1.0000 ± 0.0000, n=5, each). Whichever a human picks, the
   VLM path and KEYLESS==LIVE hold by construction.
3. **The veto lines split, and that is the most decision-relevant thing here.** Gemini is materially better
   on two of the three non-negotiables (`citation_faithfulness` +0.044, `extract_only_stated` +0.030); Opus
   is materially better on the third (`trap_avoidance` +0.127) and on `graph_recall` (+0.050). So there is
   **no free tie-break**: any human pick trades one non-negotiable against another *in the open*, rather
   than buying past one with score. That is the veto rule working, not a deadlock in it.

### Which margins are real, and which are not

Every "better" above cleared `max(0.03, 2 × pooled SD)`. Three deserve caveats stated out loud:

* **`extract_only_stated` clears by 0.0002.** |Δ| = 0.0302 against a required 0.0300 — material only
  because it grazes the *absolute floor*, not because it is comfortably outside noise. It is the weakest of
  the four material findings; one more run could move it either way.
* **`trap_avoidance` (Opus +0.127 over a 0.091 margin) is the most robust single finding here**, and it is
  the line this project cares most about: assertions made where the labeled slice knows the document does
  not support them. But its denominator is **11 trap spans**, so read it as "a real gap on 11 traps", not
  as a rate that would survive unchanged on a larger trap set.
* **`coref_binding` — the top-weighted criterion — is squarely inside noise** (0.3511 vs 0.3658, margin
  0.129). Neither model binds mentions well on this slice; both sit near 0.35. That is a finding about the
  task's difficulty, not a separator between the models.

### What this run explicitly CANNOT decide

* **It cannot compare `gpt-5.6-sol` at all.** Its lane stopped at 11 of 35 documents on an OpenAI account
  entitlement (3 RPM, then 10k TPM). **The scorecard in §5 does not mention it** — a narrowed bake-off
  reports only what it ran — so this section is the only place that record exists. Nothing here is evidence
  about that model's extraction quality in either direction. The 24 calls it did complete are **not**
  reported as a score: fewer than 3 runs returns `INSUFFICIENT_REPLICATION` by rule, and partial-run
  numbers set against complete ones would be a fabricated comparison.
* **It cannot support any per-source-type claim.** Five of the six source types in the slice appear
  **exactly once**, so "handles social media badly" and "handled *this* post badly" are the same
  observation.
* **Absolute recall figures are not meaningful — only the comparison is.** 16 of the 65 scored gold claims
  carry a role surface appearing **nowhere** in their document (31 of 65 carry one absent from their own
  cited span), because the gold labels resolved subjects and annotator-composed surfaces. A perfectly
  verbatim extractor is capped below 1.00. So `surface_f1` ≈ 0.20 for both is **not** a statement that
  either read a fifth of the document correctly; it is a floor artefact hitting both candidates
  identically.
* **Binding precision rests on 8 items** (6 `anti_coref` rows + 2 `ambiguous` pairs). Eight items cannot
  separate two models at any confidence; `identity_over_read` is therefore reported as a raw count (N=2)
  and never ranked on.
* **Cost is UNPRICED, deliberately.** `pricing: null` for every candidate — nobody here knows these models'
  real prices, and a fabricated price is a fabricated benchmark line. The bake-off **did not** decide
  cost-effectiveness. Note the irony this run earned twice: the operationally decisive cost turned out to
  be a *rate limit*, which no metric in the config models at all.
* **The slice cannot exercise** cross-document coreference, unit serials, designated formations,
  formation-level anti-merge, or corroboration-to-`confirmed` at instance level — the frozen corpus
  contains none of those shapes.

### What would be needed to separate them

Stated concretely, because "get more data" is not an answer:

1. **More runs on the same slice would not do it.** Noise falls as ~1/√n, but the margin has an **absolute
   floor of 0.03** — so no number of runs makes a 0.0095 composite gap material. **The composite tie is
   structural, not a sampling problem.**
2. **A larger, harder labeled slice is the only real lever** — specifically more `not_a_claim` traps (the
   11-item denominator is what makes the one robust finding fragile) and more negative-gold binding pairs
   (8 items). That is a data investment, not a harness one.
3. **A human tie-break on the veto split** is legitimate *if recorded as a human judgement*: prefer the
   model that fabricates least where we can check (Opus, on traps), or the one that cites most faithfully
   (Gemini). Both are defensible; neither is measured to be better overall.
4. **Funding the OpenAI account** (or accepting ~50 minutes of pacing) restores the third candidate. Its 11
   completed documents are on disk and would be **replayed free** by a resumed run.

---

## 7. Kept from the previous sitting

* **A real production concurrency bug in the shipped Gemini ingest client** — an unguarded lazy init let
  every thread build its own `genai.Client`, and the orphans' `__del__` tore down sockets sibling threads
  were still using. Fixed (`7a02694`) with double-checked locking. **Confirmed fixed by this run: Gemini
  completed 35/35 documents and 75/75 calls with zero transport faults at concurrency 8.**
* **Resume, per-provider pacing, and the coref channel going live** (`b08d855`) — all three were exercised
  for real here, and resume is why this sitting produced a scorecard where the last one produced nothing.
* **The instrument's refusal machinery is correct, and was exercised again**: preflight blocked nothing it
  should not have, the spend plan was accurate to the call, the required-metric block lifted by measurement
  rather than by deletion, and the final answer is a refusal to rank rather than a manufactured winner.
