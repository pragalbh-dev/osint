# Session DATA-C — Corpus Freeze + C Config Content

**Wave 0 · concurrent with F0/X0 · soft-depends F0 (config-schema validation only) · no LLM.**
Read `../00-master-plan.md` §4.4 (config surface — the schema you author content *over*), §4.2 (record
schemas — Source registry fields, Claim/answer-key alignment), §5 gate **G11** (generator-blind). This
session ships **content, not code**: it freezes the corpus and authors the six C config files as *content*
over F0's frozen config schemas. It touches no `chanakya/` module. It can start immediately and develop in
parallel with F0; the only F0 coupling is *soft* — the six YAML validate against F0's config schemas once
F0 merges (the store/loader is F0's, §4.4; this session does not build it).

## Goal

Two deliverables. **(A)** Turn the currently-uncommitted working corpus into a **frozen, committed,
manually-verified** demo corpus — the single reproducible input EVAL/INGEST/SHIP build against. **(B)**
Author the seven `config/*.yaml` that make the spine *be* Use Case C — the HQ-9/P ontology subset, source
registry, credibility rubric, resolution knobs, sufficiency templates, subject lens, and observables — as declarative content
the F0 config store loads. After DATA-C merges, the pipeline has a real subject to run and a real oracle to
grade against.

## Design docs to read first
`C/00-overview.md` (scope, enrichment bound, the three target queries) · `C/01-materiality-ontology.md`
(the 14-type ontology + the **demo-scope subset** §"Demo scope" — the authority for ontology.yaml) ·
`C/02-demo-thread.md` (the hero trace + the six flexes + the locked observable) · `product/04-scenario-
entities-and-corpus.md` (the ~15 instances, the 3 merge cards, the two threads, the d01–d23 doc index) ·
`md/05-data-scoping-C.md` (§4 alias tables, §5/§5.1 corpus + structural cases, §5.2 the drift-fix backlog) ·
`md/10-data-generation-strategy.md` (the operator taxonomies, the answer-key/manifest sidecar contract, the
generator-blind principle P1/P2/P7) · `md/13-location-normalization.md` (the place gazetteer + ≥2-format
seeding; `config/places.yaml`) · `spine/04-credibility.md` (R rubric factors, illustrative R defaults,
integrity-penalty tables, 0.50/0.80 thresholds, per-edge half-lives, the adversary-denial/decoy gates) ·
`spine/08-detailed-design.md` §3.6 (half-life coarse table — canonical for the *mechanism*), §3.7
(sufficiency-template shape + cadence-driven `next_coverage_due`), §3.8 (observable declarative spec).

## Scope (build these)

### PART A — Freeze the corpus

1. **Commit the uncommitted corpus.** Today only `d01`–`d14` are tracked (all show *modified*); everything
   else is untracked. Freeze, in one reviewable commit:
   - primary docs **`d15`–`d23`** (`d15_globaltimes_aligned`, `d16_adversary_denial`, `d17_rawalpindi_2021`,
     `d17b_withheld_gap`, `d18_rahwali_pass1`, `d19_rahwali_confirm`, `d20_supersede_spoof`,
     `d21_techdata_authority`, `d22_deep_tier_supplier`, `d23_cpmiec_false_attribution`) and the modified
     `d01`–`d14`;
   - **all `.png` imagery** attached to primary docs (`d07,d08,d10,d11,d12,d13,d17,d18`) and
     `corpus/raw/imagery/**`;
   - the **entire `hq9p_chaff` scenario** (`docs/` — ~27 `cd*/ce*/cs*/cx*` docs incl. `ce*` reshare PNGs —
     plus its `SCENARIO_MANIFEST.json` and `answer_key.json`);
   - the **modified `answer_key.json` + `SCENARIO_MANIFEST.json`** for `hq9p_primary`;
   - the generator/gather tooling under `tools/**` (`generate.py`, `imagery.py`, `attach_images.py`,
     `operators.yaml`, `gather/**`, probes) — **excluding `__pycache__`** (add a `.gitignore` rule if none
     covers it);
   - **`config/places.yaml`** (untracked today; authored per `md/13`) — commit as-is; extend only if a
     gazetteer gap surfaces during verification (§Owned paths).
2. **Reconcile the generator API-key drift.** `tools/generate/generate.py` currently accepts
   `("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")`. Stack is **locked on `ANTHROPIC_API_KEY`** (master §1) — drop
   `CLAUDE_API_KEY`; keep the optional `GEMINI_API_KEY` path only where the imagery tooling already needs it.
3. **Manually verify the frozen corpus against `answer_key.json`.** Walk every `documents[]` /
   `ground_truth` entry and confirm the *raw doc text* actually contains the earned signal the oracle
   expects (per `md/10` P2/P5 and the §5.2 drift-fixes F1–F8): the hero-trace path is edge-connected end to
   end (F1); HT-233 reads as chokepoint **candidate** / substitutability **UNKNOWN** (F2); the three merge
   cards have seed material — FD-2000→HQ-9/P `same-as`, HQ-9/P↔HQ-9BE `distinct-from`, FT-2000↔HQ-9/P
   `distinct-from` (D2); the relocation thread R1–R4 (Rawalpindi→Rahwali + spoof) is present (D1); ≥1 named
   deep-tier sub-supplier confirmed + rest candidate (F5); the location ≥2-format seeding of `md/13` §4 is
   in the docs. Record the pass in the PR body; fix mismatches by editing the *doc/answer-key*, never by
   feeding the answer key forward.
4. **Preserve generator-blind (gate G11).** The generator emits **only raw text** — no ontology import, no
   clean-field emission. `answer_key.json` and the `manifest.jsonl` sidecars are **EVAL-ONLY**: they are the
   grading oracle and are **NEVER** read by the pipeline or by `config/*.yaml`. Keep the generator's own
   config (`tools/generate/operators.yaml`, `tools/gather/sources.yaml`) under `tools/**`, distinct from the
   pipeline's `config/**` — that separation is the structural form of generator-blindness.

### PART B — Author the seven `config/*.yaml` (content over F0's §4.4 schemas)

All seven are **content over the config schemas F0 freezes** (master §4.4); DATA-C authors values, F0 owns the
models + loader. **Every numeric knob lives here, never in code (gate G6).** Illustrative constants are
calibration knobs (`spine/04` open Qs) — author the recommended defaults; they are tunable in-store.

5. **`ontology.yaml`** — the **demo-subset** node/edge/event types from `C/01` "Demo scope", no richer
   (over-engineering trap). Node types: **Manufacturer, Component (with `functional_role`
   ∈ acquisition|battle-management|engagement/fire-control|interceptor), Variant, Contract/Import, Unit
   (recursive — echelon + multi-valued `designator` incl. cover-designator/service_branch), Basing site,
   Interceptor Stockpile & Resupply, Technical-Data/Software & Calibration Authority, Source, Indicator,
   Known Gap** (`observability_ceiling` ∈ confirmable|probable-max|never-observable). Edge types: the
   **flagship-trace** set (`based-at`, `inducted-into`, `imported-by`, `exported-by`,
   `supplies-component`/`manufactures`, `variant-of`, `design-authority-for`); the **evidence** set
   (`evidenced-by`, `corroborates`, `contradicts`, `supersedes`, `derived-from`); **`same-as`** +
   **`distinct-from`**; **one `substitutable-by`** (three-state known-sole-source|known-alternates|UNKNOWN);
   **one deep-tier `component-of` + tier-2/3 `supplies-component`** branch. Event types first-class
   (`TransferEvent`, `InductionEvent`, `SightingEvent`, `ExerciseEvent`; `based-at` is a state derived from
   events — master §4.2). Every C/01 demo-subset type + the three seeded merge traps must be *representable*
   here.
6. **`sources.yaml`** — the source registry for the ~23 primary + chaff docs (master §4.2 Source entry).
   Per source: `source_type`, `reliability_grade` (STANAG **A–F**), `cadence` (drives sufficiency's
   `next_coverage_due`, §3.7), `bias_vector` ∈ {operator-state, exporter-state, third-party, commercial,
   adversary}, and the independence keys `primary_origin_id` / `aggregator_of`. Encode the known traps as
   registry data (the *signal*, not the verdict): **SIPRI = aggregator** (`aggregator_of` the press that
   cites it → one origin group); **ISPR (operator-state) + Chinese state media/Global Times
   (exporter-state) = aligned-interest** (same-side `bias_vector`, so not cross-interest); the
   adversary-denial source carries the flag its claim is gated by. Do **not** encode `answer_key` verdicts
   here — only the source-intrinsic fields the pipeline computes over.
7. **`credibility.yaml`** — the Confidence Resolver config (`spine/04` §"canonical form", `08` §3.4–3.6):
   the **R-factor rubric** (factors authority · process · directness · track_record · intrinsic_plausibility,
   + weights) with **illustrative R defaults** (SIPRI 0.85 · official 0.75 · think-tank 0.65 · customs/tender
   0.60 · named-social 0.35 · anon-social 0.25); the **integrity penalty tables** (`artifact_integrity`
   {unaltered 1.0/unverifiable 0.85/edited 0.30/synthetic 0.10} · `first_seen` {recycled 0.30/else 1.0} ·
   `caption` {consistent 1.0/uncheckable 0.9/mismatched 0.30} · `coordinated_inauthenticity`
   {independent 1.0/suspected 0.5/too-clean 0.4}); the **gates** (`adversary_denial` = exclude-from-grouping,
   `decoy_risk` = cap-at-probable — neither a multiplier); the **thresholds** (confirmed ≥ 0.80, probable
   0.50–0.80, possible < 0.50); and the **per-edge half-lives** (`spine/04` finer table + `08` §3.6 coarse
   canonical-for-mechanism — author the reconciled set, e.g. `based-at` field 30d/garrison 18mo,
   `operational-status` 3mo, `supplies-component` prime 5y/tier 18mo, durable edges ∞).
7a. **`resolution.yaml`** — the resolver knobs (`spine/08` §3.9, `md/05` §4, `md/13`) that RESOLVE consumes:
   `merge_score` weights (**0.30·attribute / 0.40·relational / 0.15·temporal / 0.15·source_asserted**), bands
   (**auto ≥ 0.85 / HITL 0.55–0.85 / keep-separate < 0.55**), blocking keys (type + country/domain + name
   token), the **seeded alias/transliteration table** (Triumf/Триумф, Hongqi/红旗, FD-2000→HQ-9/P), the
   **high-alias-risk type set** {variant, component, unit, manufacturer} + orphan-`k` + the proposer's LLM
   budget, and the place-resolution proximity radii. The **withheld forms** ("Chaklala"/`OPRN`, Karachi-Port
   vs Port-Qasim) are held out of the seed for the earned-merge demo (per `config/places.yaml`, `md/13`).
8. **`templates.yaml`** — evidence-requirement templates per assertion type (`spine/04` §insufficient,
   `08` §3.7 shape). At minimum the load-bearing `based-at` template (`imagery_confirmation within 365d`
   **OR** `independent_text_groups ≥2 within 365d`); plus templates for `inducted-into`, the
   sustainment-dependency assertion, and the never-observable classes (magazine depth, contract terms, C2
   topology → `observability_ceiling: never-observable`). `on_fail` emits the Known-Gap payload with
   `missing_slots` + a `next_coverage_due` computed from the source `cadence`.
9. **`subjects.yaml`** — the HQ-9/P **lens** (master §4.4, `C/00` target queries): anchor = **the Karachi
   HQ-9/P battery** (`unit_paad` / `site_karachi` — the well-sourced flagship-trace entry point, `C/02`);
   N-hop + materiality traversal/scoping rules (so chaff/distractors don't leak into the assessed view); and
   the **three target queries verbatim** — (1) *"trace this deployed HQ-9/P battery back to its component
   supplier and name the chokepoint"*, (2) *"is this holding confirmed or probable, and on what evidence?"*,
   (3) *"what do we NOT know here?"*. Subject is a query-time lens (gate G10) — pure config, no per-subject
   table.
10. **`observables.yaml`** — the declarative tripwires (`08` §3.8 spec). The **seeded** primary:
    `obs-basing-relocation` — occupancy state-change on the perishable `based-at` edge, `match_on:
    [resolved_unit, site_instance]` (not designators), `anchors_within_hops: 2`, scoped to the HQ-9B
    **Rawalpindi→Rahwali (2025)** relocation. Plus the **config-only** secondaries (armed but not wired into
    the narrative — proving observables are declarative): a follow-on interceptor order via `replenishes`,
    and a spares tender → "probable induction".

## Contracts implemented (content over F0's frozen schemas)

- Master **§4.4** config surface — the seven `config/*.yaml` are the C *content* of the schemas F0 freezes;
  they must round-trip through F0's config store unchanged.
- Master **§4.2** Source registry fields — `sources.yaml` populates the `SourceRegistryEntry` shape;
  `answer_key.json` aligns to (but is never an input to) the Claim/derived-state shapes.
- The **frozen corpus + `answer_key.json`** as the EVAL oracle consumed by EVAL/INGEST/SHIP (soft coupling,
  master §3 "Dependency notes") — this session freezes it; it does not build the harness.

DATA-C **freezes nothing in `chanakya/`** — F0 owns all schemas/stage signatures. If a config field the C
content needs is absent from F0's schema, that is an **F0-amendment PR** (master Rule 3), not an edit here.

## Acceptance criteria
- [ ] The full uncommitted corpus (`d15`–`d23`, all `.png`, `corpus/raw/imagery/**`, the entire
      `hq9p_chaff` scenario, both modified primary manifests) is **committed and frozen** on `feat/data-c`;
      `git status corpus/` is clean; `__pycache__` is gitignored, not committed.
- [ ] The frozen corpus is **manually verified against `answer_key.json`** (hero path traversable F1;
      HT-233 candidate/UNKNOWN F2; three merge cards seeded; relocation thread R1–R4 present; ≥1 named
      deep-tier supplier; ≥2-format location seeding) — verification recorded in the PR body.
- [ ] `tools/generate/generate.py` keys on **`ANTHROPIC_API_KEY`** only (`CLAUDE_API_KEY` removed); the
      generator still emits **only raw text** and imports no ontology — **gate G11 green**; `answer_key.json`
      / `manifest.jsonl` are confirmed EVAL-ONLY (never referenced by `config/**` or the pipeline).
- [ ] All seven `config/*.yaml` **validate against F0's config schemas and load into the config store** with
      no error (run once F0 is on `main`); `resolution.yaml` carries the merge weights/bands/blocking keys +
      the seeded alias/transliteration table (with the withheld forms held out).
- [ ] Every `C/01` demo-subset **node/edge/event type** is representable in `ontology.yaml`, and the three
      seeded traps — **FD-2000↔HQ-9/P `same-as` (auto-merge)**, **HQ-9/P↔HQ-9BE `distinct-from`**,
      **FT-2000↔HQ-9/P `distinct-from`** — are representable in `ontology.yaml` **and** their sources are
      present in `sources.yaml`.
- [ ] `credibility.yaml` carries the R rubric+defaults, integrity tables, both gates, the 0.50/0.80
      thresholds, and the per-edge half-lives; `templates.yaml` has the `based-at` template + never-
      observable classes; `subjects.yaml` carries the Karachi anchor + the three verbatim queries;
      `observables.yaml` has the seeded relocation observable + the two config-only secondaries.
- [ ] No hardcoded scoring/threshold/half-life literal is introduced anywhere (it all lives in config) —
      consistent with gate **G6**.

## Owned paths (nothing else)
`corpus/**` (docs + `.png` + `SCENARIO_MANIFEST.json` + `answer_key.json` + `manifest.jsonl` + `raw/**`),
`tools/**` (generator/gather scripts + their `operators.yaml`/`sources.yaml`), `config/ontology.yaml`,
`config/sources.yaml`, `config/credibility.yaml`, `config/resolution.yaml`, `config/templates.yaml`,
`config/subjects.yaml`, `config/observables.yaml`, and `.gitignore` (only to add a `__pycache__` rule if
missing).
**`config/places.yaml`** is owned only to *commit as-is / extend* — do not rewrite it.

## Out of scope
- **Extraction code + pre-extracted seed-bundle generation** (`corpus/scenarios/*/claims/**`) — that is
  **INGEST** (master §3; soft-depends this session's `sources.yaml`). Do **not** create `claims/` here.
- **The config STORE / loader / schema models** — **F0** (`chanakya/config/**`, `chanakya/schemas/**`).
  DATA-C authors YAML content only; if a schema field is missing, raise an F0-amendment.
- Any `chanakya/` stage logic, the API, Docker/deploy, the acceptance harness.

## Worktree lifecycle
`git worktree add ../wt-data-c -b feat/data-c` (off latest `main`) → freeze corpus + reconcile generator +
author the six YAML inside owned paths only → validate the YAML against F0's schemas once F0 is merged →
PR `[DATA-C]` per the master §8 template (list decisions taken + the corpus-verification result) → you
review & merge → you update `PROGRESS.md` → `git worktree remove ../wt-data-c` and delete the branch.
Develops in parallel with F0; the config-store validation step lands after F0 merges.
