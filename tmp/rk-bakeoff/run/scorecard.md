# RK-BAKEOFF — comparative extractor scorecard

Replication: **5 runs/candidate** (ranking refused below 3). Margin: **max(0.03, 2.0×pooled SD)**.


## 1. Gating preconditions — PASS/FAIL to win (never weighted)

A candidate failing any gate **cannot win at any score**. UNKNOWN blocks too: an unverified precondition is not a satisfied one.

| candidate | model id | gates | eligible to win |
|---|---|---|---|
| Anthropic Opus 5 (`anthropic-opus-5`) | `claude-opus-5` | `PASS` **vlm_imagery_path** — 6/6 standalone-image calls returned (multimodal=native; recorded probe 1/1 on d17b_withheld_gap.png @2026-07-25T20:27:24+00:00, this run 5/5)<br>`PASS` **keyless_equals_live** — chanakya.ingest.client is on the shipped ingest path, anthropic imports, and it is declared the seed producer<br>`PASS` **pinned_model_id** — 'claude-opus-5' is a concrete pinned id<br>`PASS` **exercisable** — ANTHROPIC_API_KEY is set<br>`PASS` **non-negotiable:citation_faithfulness** — citation_faithfulness=0.789 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies<br>`PASS` **non-negotiable:extract_only_stated** — extract_only_stated=0.955 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies<br>`PASS` **non-negotiable:trap_avoidance** — trap_avoidance=0.873 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies | **YES** |
| Gemini Flash 3.6 (`gemini-3-6-flash`) | `gemini-3.6-flash` | `PASS` **vlm_imagery_path** — 6/6 standalone-image calls returned (multimodal=native; recorded probe 1/1 on d17b_withheld_gap.png @2026-07-25T20:27:33+00:00, this run 5/5)<br>`PASS` **keyless_equals_live** — chanakya.ingest.client is on the shipped ingest path, google.genai imports, and it is declared the seed producer<br>`PASS` **pinned_model_id** — 'gemini-3.6-flash' is a concrete pinned id<br>`PASS` **exercisable** — GEMINI_API_KEY is set<br>`PASS` **non-negotiable:citation_faithfulness** — citation_faithfulness=0.833 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies<br>`PASS` **non-negotiable:extract_only_stated** — extract_only_stated=0.985 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies<br>`PASS` **non-negotiable:trap_avoidance** — trap_avoidance=0.745 measured; no absolute floor is configured, so only the relative veto (materially worse than a rival) applies | **YES** |

## 1b. Where these runs came from

> **Replayed, not re-run.** `anthropic-opus-5`, `gemini-3-6-flash` was scored entirely from artefacts an earlier invocation paid for. Those runs *were* sampled in a single sitting, so `determinism` means what it normally means — but the numbers describe that session, not this one.

| candidate | invocations | documents reused | documents bought |
|---|---|---|---|
| `anthropic-opus-5` | `inv-20260726T155646Z-52deac` | 35 | 0 |
| `gemini-3-6-flash` | `inv-20260726T155646Z-52deac` | 35 | 0 |

## 2. Measured criteria (mean ± sample SD over the runs)

| metric | weight | anthropic-opus-5 | gemini-3-6-flash | verdict |
|---|---|---|---|---|
| `citation_faithfulness` | 4.5 · **VETO** | 0.7891 ± 0.0103 (n=5) | 0.8331 ± 0.0191 (n=5) | gemini-3-6-flash > anthropic-opus-5 |
| `coref_binding` | 5 | 0.3511 ± 0.0881 (n=5) | 0.3658 ± 0.0243 (n=5) | NO MEASURED DIFFERENCE |
| `cost_usd` | 0 | not measured — UNPRICED — no pricing declared for this candidate in config/bakeoff.yaml | not measured — UNPRICED — no pricing declared for this candidate in config/bakeoff.yaml | not rankable |
| `determinism` | 2 | 0.6043 ± 0.0221 (n=5) | 0.6247 ± 0.0240 (n=5) | NO MEASURED DIFFERENCE |
| `discriminator_capture` | 4.5 | 0.2952 ± 0.0621 (n=5) | 0.1882 ± 0.1404 (n=5) | NO MEASURED DIFFERENCE |
| `discriminator_fabrication_avoidance` | 4 | 0.9217 ± 0.0567 (n=5) | 0.8842 ± 0.0753 (n=5) | NO MEASURED DIFFERENCE |
| `extract_only_stated` | 4.5 · **VETO** | 0.9550 ± 0.0110 (n=5) | 0.9852 ± 0.0055 (n=5) | gemini-3-6-flash > anthropic-opus-5 |
| `graph_edge_recall` | 0 | 0.3286 ± 0.0639 (n=5) | 0.3143 ± 0.0391 (n=5) | NO MEASURED DIFFERENCE |
| `graph_node_recall` | 0 | 0.6000 ± 0.0211 (n=5) | 0.5308 ± 0.0172 (n=5) | anthropic-opus-5 > gemini-3-6-flash |
| `graph_recall` | 3 | 0.5050 ± 0.0209 (n=5) | 0.4550 ± 0.0209 (n=5) | anthropic-opus-5 > gemini-3-6-flash |
| `identity_over_read` | 0 | 0.0000 ± 0.0000 (n=5) | 0.0000 ± 0.0000 (n=5) | NO MEASURED DIFFERENCE |
| `kind_tagging` | 0.5 | not measured — the gold slice labels no claim kinds | not measured — the gold slice labels no claim kinds | not rankable |
| `latency_s` | 0 | 261.8564 ± 5.1211 (n=5) | 234.7874 ± 24.3248 (n=5) | NO MEASURED DIFFERENCE |
| `structured_output_reliability` | 3 | 1.0000 ± 0.0000 (n=5) | 1.0000 ± 0.0000 (n=5) | NO MEASURED DIFFERENCE |
| `surface_f1` | 3 | 0.2006 ± 0.0098 (n=5) | 0.2059 ± 0.0220 (n=5) | NO MEASURED DIFFERENCE |
| `surface_precision` | 0 | 0.1382 ± 0.0073 (n=5) | 0.1573 ± 0.0188 (n=5) | NO MEASURED DIFFERENCE |
| `surface_recall` | 0 | 0.3662 ± 0.0201 (n=5) | 0.2985 ± 0.0257 (n=5) | anthropic-opus-5 > gemini-3-6-flash |
| `trap_avoidance` | 0 · **VETO** | 0.8727 ± 0.0498 (n=5) | 0.7455 ± 0.0407 (n=5) | anthropic-opus-5 > gemini-3-6-flash |

## 3. Composite and verdict

Composite = weighted mean **per run** of these rate metrics: `citation_faithfulness`×4.5, `coref_binding`×5, `determinism`×2, `discriminator_capture`×4.5, `discriminator_fabrication_avoidance`×4, `extract_only_stated`×4.5, `graph_recall`×3, `structured_output_reliability`×3, `surface_f1`×3.

Excluded from the composite (reported above, not composited):

- `cost_usd` — weight 0 (reported, not composited)
- `graph_edge_recall` — weight 0 (reported, not composited)
- `graph_node_recall` — weight 0 (reported, not composited)
- `identity_over_read` — weight 0 (reported, not composited)
- `kind_tagging` — not rankable for anthropic-opus-5 (the gold slice labels no claim kinds); gemini-3-6-flash (the gold slice labels no claim kinds)
- `latency_s` — weight 0 (reported, not composited)
- `surface_precision` — weight 0 (reported, not composited)
- `surface_recall` — weight 0 (reported, not composited)
- `trap_avoidance` — weight 0 (reported, not composited)

Composite tiers (best first; candidates inside one tier are not separable at the configured margin):

1. `anthropic-opus-5`, `gemini-3-6-flash`

### VERDICT: `NO_MEASURED_DIFFERENCE`

NO MEASURED DIFFERENCE between anthropic-opus-5, gemini-3-6-flash: every gap between them sits inside the run-to-run noise at the configured margin. Naming one of them would be a ranking invented from jitter.

**Tied within noise: `anthropic-opus-5`, `gemini-3-6-flash`** — no winner.

## 4. The match policy that produced these numbers

The matcher's leniency **is** the measurement; read this before reading any figure above.

```
similarity        : token_sort_ratio (rapidfuzz, scaled 0..1)
same form/polarity: form=True  polarity=True
predicate         : normalized      entity_type: normalized
identifiers       : designator_aware (HQ-9/P ≡ HQ9P), agreement=nested_or_equal (HQ-9B ≢ HQ-9BE)
thresholds        : per-role >= 0.7, pair mean >= 0.8
spans             : bonus (IoU floor 0.3, bonus weight 0.15)
grounding         : surface must reach 0.85 against the cited text
```

## 5. What `surface_precision` excludes, and what vetoes a winner

Precision above is **matched / emitted-minus-neutral**. The labeled slice types its negative rows into four classes and declares only `not_a_claim` a true false positive; `unmodelled`, `anti_coref` and non-identity claims over an `ambiguous` pair are **neutral** — a candidate reading an off-ontology sentence correctly is not wrong, and charging it would penalise a model in proportion to how much of the document it read, which does not cancel between candidates and favours the terser extractor. Those exclusions come from `eval.gold.adapter.precision_exclusions` — the gold owner's own definition, consumed rather than re-derived — and every excluded claim key is listed in the metric detail of the JSON output.

A `not_a_claim` span is never excused. An emission there costs precision **and** is scored by `trap_avoidance`, and where a neutral span overlaps a trap the trap wins. A trap hit also requires the emission to be **unpaired** against positive gold: one trap span overlaps a positive claim's span, so a bare-overlap test would charge an honest model.

`trap_avoidance` is a **veto, not a weighted line** — it carries no weight and appears in `gates.non_negotiable_floors`. A non-negotiable inside a composite is only a heavy weight, and any weight is a price a good-enough model can pay. A candidate materially worse on it than a rival cannot be named winner at any score, and a candidate whose trap line was never measured is gate-UNKNOWN, which blocks just as hard. `identity_over_read` is reported as a raw count (N=2) and never ranked on.

