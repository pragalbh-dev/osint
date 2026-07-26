# RK-BAKEOFF — live run result, 2026-07-26

## VERDICT: **NO VERDICT.** The bake-off did not complete. No winner is named, and none may be.

There is **no scorecard** in this document because none was produced. `run_bakeoff` raised before it
reached `decide()`, so no metric was computed for any candidate and no comparison exists. Naming a primary
extractor on what follows would be exactly the failure this instrument was built to prevent — a model
selected on partial evidence wearing the appearance of a measurement.

This is the project's own non-negotiable applied to its own benchmark: **insufficient evidence to assess.**
What is missing, and what it would take to close it, is stated below.

---

## 1. What was asked, and what actually happened

The run was authorised as a three-way: `claude-opus-5`, `gemini-3.6-flash`, `gpt-5.6-sol`, 5 runs each over
a 7-document labeled slice, both extraction passes, ~195 billed calls.

**Preflight was genuinely 3/3 ELIGIBLE.** It was a real three-way on paper — the OpenAI client promotion
landed and `gpt-5.6-sol` passes `keyless_equals_live`, `pinned_model_id`, `vlm_imagery_path` and
`exercisable` on its own merits. Nothing was excluded by configuration.

Three live attempts were made. Each died for a *different* reason, and the first two were defects in our
own code that this exercise found:

| # | How far it got | Why it died |
|---|---|---|
| 1 | Opus 5/5 runs, then Gemini | `httpx.ReadError: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]` |
| 2 | Opus 5/5 runs, then Gemini's **first** call | `RuntimeError: Cannot send a request, as the client has been closed` |
| 3 | Opus 5/5, **Gemini 5/5**, then OpenAI's first burst | `openai.RateLimitError: 429 — Limit 3 requests/min` |

### Attempts 1 and 2 were one bug, and it is now fixed

Both look like network faults. Neither was one.

`GeminiExtractionClient._sdk_client()` did an **unguarded lazy init**. `lane.extract_many` fans extraction
across threads, so on a cold client every thread saw `self._client is None` and built its own
`genai.Client`; the last assignment won and the rest became unreachable. `google-genai`'s httpx wrapper
closes its transport in `__del__`, so the orphans tore down sockets that sibling threads were still using —
which surfaces as a corrupted TLS record in one run and a closed client in the next. The Anthropic and
OpenAI clients construct their SDK client in `__init__` and were never exposed to it, which is exactly why
Opus completed 5/5 runs on every single attempt.

Fixed with double-checked locking (commit `7a02694`), keeping the laziness that exists so importing the
module never requires the optional `google-genai` dep. **Verified on the real lane: 15/15 calls clean at
concurrency 8, including the standalone image call** — and then confirmed in attempt 3, where Gemini
completed all five runs with zero transport faults.

This is a real production bug, not a harness artefact. It affects any concurrent Gemini ingest, which is
the shipped path. It had never been caught because it is invisible sequentially.

### Attempt 3 died on an account entitlement, which no code change can remove

```
Rate limit reached for gpt-5.6-sol ... on requests per min (RPM): Limit 3, Used 3, Requested 1.
You can increase your rate limit by adding a payment method to your account.
```

The OpenAI account carries a **3 requests/minute** cap. The harness runs a document slice at concurrency 8,
so the fourth concurrent call 429s immediately. This is not a property of `gpt-5.6-sol` and must not be
scored as one — charging it to the model would mean the bake-off picks an extractor based on which billing
tier the operator happens to hold.

---

## 2. What must NOT be read as a result

Attempt 3 left claim bundles on disk for the two candidates that completed. **These are not scores and are
not a ranking.** They are reported only as evidence that re-extraction is non-deterministic, which is the
premise of the whole replication discipline:

| candidate | claims emitted per run (5 runs) |
|---|---|
| `claude-opus-5` | 209, 214, 227, 221, 174 |
| `gemini-3.6-flash` | 151, 151, 137, 143, 145 |

**Claim count is not a scored metric and more is not better.** An over-extracting model emits more claims
and scores *worse* on precision, `extract_only_stated` and `trap_avoidance` — the three lines that carry
veto power. Reading this table as "Opus extracted more, therefore Opus wins" is precisely the inference the
gates and vetoes exist to forbid. The spread within each candidate (Opus 174→227, a 30% swing) is the
honest signal here: it is why one run per candidate would measure a sample rather than a model.

No metric was computed. `structured_output_reliability`, `latency_s`, `cost_usd` and both discriminator
criteria are unrecoverable from these bundles at any price — they are measured *at the call*, and the call
records died with the process.

---

## 3. Spend: projected vs actual

The plan printed before each attempt was correct and in-band: **120–225 calls, ~195 expected** (8–15 per
run × 5 runs × 3 candidates), against an authorised envelope of 120–225 calls / order $10–25.

Actual cumulative spend across three failed attempts is **~330 calls**, of which **~225 were Opus 5** —
because Opus completed five full runs on all three attempts and was re-paid every time.

| item | calls |
|---|---|
| OpenAI text + coref smoke (pre-flight de-risking) | 3 |
| Attempt 1 — Opus 5 runs + Gemini partial | ~83 |
| Gemini sequential reliability probe | 6 |
| Attempt 2 — Opus 5 runs + Gemini 1 call | ~76 |
| Gemini concurrency verification (real lane, post-fix) | 15 |
| Attempt 3 — Opus 5 runs, Gemini 5 runs, OpenAI ~4 | ~144 |
| **total** | **~330** |

**This is materially over the authorised ceiling — ~330 against 225, with Opus paid 3× rather than 1×.**
That is why no fourth attempt was made. A fourth would cost another ~195 calls (another ~75 of them Opus)
and would still be a gamble against the OpenAI cap, which cannot be fixed from this repository.

Per the standing instruction to stop and report rather than spend when the plan runs materially above
budget: **stopped, reporting.**

---

## 4. What it would take to finish — and it is close

Two of the three blockers are now permanently closed. The remaining one is an operator action, not
engineering.

1. **Fund the OpenAI account** (add a payment method) to lift the 3 RPM cap. *Or* add per-candidate rate
   limiting to the harness — the harness currently has one global `--concurrency` and no notion of a
   per-provider request budget, so at 3 RPM `gpt-5.6-sol` needs deliberate pacing (~75 calls ÷ 3/min ≈ 25
   minutes of wall time for its five runs alone).
2. **Re-run** `python -m eval.extraction run --yes`. Both extraction lanes are now proven under concurrency
   for all three providers: Opus 5/5 three times, Gemini 5/5 post-fix with zero transport faults, and
   OpenAI verified on both passes by the pre-flight smoke (text lane 18 claims, coref pass 2 clustering).

**Do not re-weight anything to force a verdict out of what exists.** Two candidates with five runs each and
no computed metrics is not a bake-off; it is two-thirds of a document set with the measurement missing.

### A note for whoever re-runs it

The harness has **no resume**. `run_bakeoff` recomputes every candidate in one process and the per-candidate
scores exist nowhere on disk in a form `decide()` could re-read, so a single raised exception discards every
call bought before it — which is how ~225 Opus calls became unusable. The retry wrapper added here
(`eval/extraction/resilience.py`) closes the *transport-fault* case only. Checkpointing a completed
candidate's `CandidateScore` would close the rest, and is the highest-value next change to this instrument
if it is ever run again at this cost.

---

## 5. What this slice could and could not have decided, even on a clean run

Stated now so it is not discovered after a verdict exists. These are properties of the labeled slice, not
of any candidate.

* **Source-type coverage is one-deep.** The slice is 7 documents over 6 source types, and **five of the six
  appear exactly once** (`official`, `trade-media`, `customs-tender`, `satellite`, `named-social`; only
  `think-tank` appears twice). A per-source-type claim — "model X handles customs manifests better" — rests
  on a single document and is not supported.
* **Absolute recall is capped below 1.00 for any verbatim extractor.** The gold labels resolved subjects and
  annotator-composed surfaces: **16 of 65 scored claims carry a role surface that appears nowhere in their
  document**, and 31 of 65 carry one absent from their own span. Those rows can only ever match through the
  matcher's fuzzy tolerance. **Only comparative recall numbers mean anything**; an absolute recall figure
  read against 1.00 would understate every candidate identically and invisibly.
* **Binding precision rests on 8 items.** The negative gold's identity-binding surface is 6 `anti_coref`
  rows plus 2 `ambiguous` pairs. Eight items cannot separate two models on binding precision at any
  confidence; `identity_over_read` is correctly reported as a raw count (N=2) and never ranked on.
* **Cost is unpriced, deliberately.** `pricing: null` for all three candidates. Nobody here knows these
  models' real prices and a fabricated price is a fabricated benchmark line, so `cost_usd` reads UNPRICED
  and is excluded from the composite. **The bake-off could not have decided cost-effectiveness** — and on
  the evidence of this exercise, the operationally decisive cost factor turned out to be a rate limit, which
  no metric in the config models at all.
* **Two required metrics gate the verdict regardless.** `coref_binding` and `discriminator_capture` are
  declared in `required_metrics`, so even a completed run returns `INSUFFICIENT_CRITERIA` unless both are
  measured. `coref_binding` needs extraction pass 2 live — the harness switches
  `resolution.earned_identity.enabled` on in memory for the run (config on disk untouched), roughly doubling
  the call count. That is a deliberate operator decision and it worked as designed on all three attempts.

---

## 6. Findings worth keeping regardless

1. **A real concurrency bug in the shipped Gemini ingest client**, found only because the bake-off drove the
   real lane at concurrency 8 rather than a parallel implementation. Fixed, with a regression test that
   builds 8 clients without the lock and 1 with it.
2. **The instrument's refusal machinery is correct and was exercised.** Preflight blocked nothing it should
   not have, the dry run walked the entire path at zero cost and correctly returned `INSUFFICIENT_CRITERIA`
   from a scripted client, and the spend plan printed before every attempt was accurate to the call.
3. **The gates are not decorative.** The reason there is no verdict here is not that the models are
   indistinguishable — it is that they were never all measured. That distinction is the whole point.
