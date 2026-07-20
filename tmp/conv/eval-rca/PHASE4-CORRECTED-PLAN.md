# Phase 4 — CORRECTED plan (supersedes the four Phase-4 handoffs)

**Status:** ratified with the orchestrator, 2026-07-19. **This document wins** over
`handoff-score.md` / `handoff-arch.md` / `handoff-monitor.md` / `handoff-ask.md` wherever they disagree.

**Read this first — the original handoffs are NOT safe to build from.** Every Phase-4 finding was
re-verified against the post-Phase-1/2 code by eight parallel investigations. Result: **4 of the
recommended fixes are hacks** (one would have armed an adversarial trap planted in our own corpus),
**3 findings are attributed to the wrong service or to code instead of the answer key**, and **3
structural defects that no handoff scoped** turned out to be the actual blockers. The handoffs remain
useful for their evidence and probes; treat their *recommendations* as unverified.

Root cause + phase plan: `00-RCA-index.md`. Progress hub: `RCA-FIX-PROGRESS.md`. Decisions:
`RCA-FIX-DECISIONS.md` (append the D-P4 block below at PR time).

---

## 0. The recurring theme — state it in the design note

Five separate mechanisms in this codebase are **built, tested, green, and wired to nothing**:
`view/supersede.py`, the ontology's `freshness_class` layer, the refusal templates, `match_on`, and
the alert feed. In every case the test suite asserts against a data shape production never emits.
This is the signature of parallel sessions freezing incompatible conventions and integrating late.
It is worth one honest paragraph in the design note — it is a real and generalisable lesson about
multi-agent builds, and stating it is stronger than hoping nobody runs the suite.

---

## 1. Decisions ratified this session (append to `RCA-FIX-DECISIONS.md`)

- **D-P4.1 — Overturn D-2.7's no-extract rule for basing.** D-2.7's premise ("no doc states unit→site")
  is **factually false** — ten corpus documents state a formation/battery at a site, three at
  analyst-graded confidence (d17, d18/d19, d07). Only *designated* unit ids are absent, which is an
  identity problem, not a fact-shape problem. D-2.7 was also **never implemented**: `based-at` is
  `extractor: true` and first in the extraction enum, and was emitted 4× in the current re-record.
  *Principle: extract what is stated; derive only the unstated.* *Rejected:* keeping the blanket rule
  (it silently contradicts `handoff-score.md`'s own dependency on INGEST producing basing edges).
- **D-P4.2 — Observed equipment-at-site gets its own edge lane.** Today `relane()` rejects
  `(variant → basing_site)` because no edge covers it, so genuinely-stated observations from d19/d23
  are destroyed into tier-3 notes; the 2 surviving `based-at` edges are *leaks* (both endpoints
  untypable), not policy. Add an occupancy/observed-at lane so the observed layer and the derived
  unit-attribution layer each carry their own confidence — this is what D-G2 asked for.
  **The lane MUST be emittable from the imagery extraction shape** (see §2.3).
- **D-P4.3 — Derivation is authored by an offline proposer, priced by SCORE, never by RESOLVE.**
  RESOLVE *structurally cannot* emit a claim (`resolve()` returns a `Partition`; there is no claim
  channel), and `rebuild()` is a pure deterministic function with no model access (gate G1). The
  derived basing fact belongs in the **evidence layer as an `inference` claim with `premises`** — the
  mechanism already exists and is used twice (`ingest/imagery.py`, `ingest/attribute.py`), and SCORE
  already prices it correctly (an inference shares a group with its premises → cannot self-corroborate
  to CONFIRMED). *Rejected:* the RES-1 assignment in `handoff-resolve.md` /
  `handoff-answer-key-grounding.md:172-174` — it asks RESOLVE for something its return type cannot express.
- **D-P4.4 — Supersession requires all four conditions.** Same functional slot (+ sub-scope) · different
  value · non-overlapping, separable intervals · newer claim independently reaches probable with a clean
  deception gate. Anything else → `candidate_supersede` → HITL, which becomes the **default**, not the
  exception. *Principle: the fabrication non-negotiable + recall-biased triage.* *Rejected:* the
  slot-key fix alone — measured, it would let the planted `d20` spoof retire the confirmed position.
- **D-P4.5 — Relocation beat runs off staged live ingest; the rewind is demoted and relabelled.**
  Alerting is transaction-time (an analyst is warned when information *arrives*); the historical rewind
  is a separate feature and must be labelled **"as we knew it on DATE"**, never "as it was". One `as_of`
  knob currently serves both jobs and also silently steers the freshness "now" — split it.
  *This is what the design always said* (`spine/08` §3.8, `C/02`): driven live by an ingest, **not a
  scripted reveal**. The `as_of` rewind in `eval/harness.py` is an EVAL-side improvisation.
- **D-P4.6 — Dates are required where the ontology declares perishability, not everywhere.** Of 126
  relationship claims, 78 are identity (a date is meaningless), 37 are durable (a date is inert), 11 sit
  on perishable/semi-durable edges (a date is load-bearing). Requiring dates universally would push the
  model to fabricate them on 78 identity claims. *Rejected:* option (a) "every relation gets a date".
- **D-P4.7 — Chokepoint direction is declared, not hardcoded.** Add `supplier_end: from|to` per
  sustainment edge in `config/ontology.yaml`. *Rejected:* `handoff-score.md`'s node-type allowlist —
  it re-hardcodes what Phase 1 made declarative, **and would nominate nothing at all today** (every
  currently-nominated node is `type: unknown`).
- **D-P4.8 — `mfr_taian` is re-graded to probable; the corroboration rule is NOT loosened.** The answer
  key demands CONFIRMED off a justification citing **one document**. Two open-source secondary analyses
  are not two independent collection disciplines. *Principle: confirmed = sourcing, not plausibility;
  the twice-ratified "do not retune credibility" holds.* Owner: DATA-C/EVAL, not SCORE.
- **D-P4.9 — `exclude_off_subject` is deleted, not implemented.** That label exists **only** in
  `answer_key.json`. Implementing it would wire the grading oracle into the runtime filter.
  *Rejected:* `handoff-arch.md`'s "implement the declared filter semantics" as written.
- **D-P4.10 — The seeded relocation observable is de-pinned.** It currently hardcodes `from_site`/
  `to_site`/`window` from the answer key (with a comment saying so) while those keys are **inert** — so
  it simultaneously *reads* as teaching-to-the-test and *behaves* as an unscoped global watch that fires
  on a Beijing street address. Replace with subject + change-class only; the sites appear in the alert,
  never in the definition. *The tripwire staying silent on the d20 spoof and the recycled imagery IS the
  credibility demonstration* — pinning the destination throws it away.

- **D-P4.11 — `supersedes` is drawn as a site→site edge *in addition to* the internal version-linking.**
  The oracle models it as a node→node edge; the code as edge→edge id fields; measuring one against the
  other reads 0 forever, and `config/ontology.yaml:93` declares a `supersedes` edge type nothing emits.
  Emit both: the internal link drives status (`superseded_by → stale`), the drawn edge makes the
  relocation **visible and one-click traceable** in the graph — which is how an analyst describes it and
  what the demo needs. *Principle: traceability; model to the query.* *Rejected:* re-grading the answer key
  to the internal shape (the relocation becomes invisible as a graph edge — weaker artifact, harder to audit).
- **D-P4.12 — Pin an explicit evaluation date in config; do NOT re-derive "now" from the data.**
  Today the freshness "now" falls out of `claim_available_iso` (`pipeline.py:375` → `timeref.py:41-51`),
  i.e. from the frozen ingest stamp — so a re-record silently moves every staleness number in the graph,
  and real elapsed time drifts the demo. Add an explicit `evaluation_date` (`auto | <ISO>`), pinned for the
  demo. *Principle: determinism / reproducibility (gate G2).* **This is orthogonal to the half-life
  choice, not a substitute for it** — the pinned date is the numerator, the half-life the denominator;
  both must be sane. Guard: a live-ingested claim dated after the pinned date must not produce a negative
  age — clamp at zero, don't silently invert freshness.
- **D-P4.13 — Perishable default = the garrison rate (540d), pending measurement.** On the corpus's real
  dates and a 2026-07-19 evaluation date, this is the only value that yields **Rawalpindi stale AND
  Rahwali still fresh**; the 30d field rate makes *both* stale and kills the beat. Earlier framing that
  540d "hides staleness longest" was wrong in context — with a 2021 vs 2025 gap it is the discriminating
  choice, not the lenient one. **Verify by measuring the actual freshness values before landing**, and
  record the measured numbers in the PR; if the window doesn't hold, escalate rather than tuning to fit.
- **D-P4.14 (RAISED, NOT RATIFIED) — the independence weight is applied twice.** The same-discipline
  group weight is applied once inside `group_confidence` (`status.py:53-58`, magnitude) and again in
  `_effective_looks` (`status.py:69-74`, count), which is a stricter model than `spine/04:167-171`
  describes. **This is a credibility retune → needs explicit ratification; do not fold it into another
  PR.** Flagged for the orchestrator, deliberately left open.

---

## 2. The three structural holes (none were in any handoff)

### 2.1 `edge_instance` embeds the object — kills three mechanisms at once

`resolve/entities.py:43` and `view/pipeline.py:275` both build `edge:{subj}:{pred}:{obj}`. Consequences:

- `view/supersede.py:59-60` early-returns at ≤1 target per instance → **supersedes / contradiction /
  candidate_supersede are mathematically unreachable in production**. The 0-supersedes symptom
  `handoff-score.md` attributed to "no service synthesizes them" and blamed on RESOLVE is this.
- `observe/evaluator.py:56,122-143` groups the crossing detector by the same key → the before-edge and
  after-edge of a relocation land in different buckets → **no crossing can ever be detected**.
- `resolve/scoring.py:29-42`'s co-instance **relocation exclusion** (which stops a unit's two bases being
  merged into one place) requires two entities to be co-objects of one instance → also dead.

**Every test hand-builds the slot-shaped key** (`based-at:unit_x`) that production never emits —
`tests/view/test_supersede.py:10`, `tests/fixtures/per_stage/alert_delta.json`, all of
`tests/observe/test_evaluator.py`, `tests/resolve/_helpers.py:89`, `tests/agent/fixtures.py:335`.
`artifacts/plan/PROGRESS.md:454-457` (the INGEST contract) and `edge_direction.py`'s docstring state
**two different** conventions. Four inconsistent statements of one key in one repo.

**Our own `artifacts/md/06-preflight-audit.md:245-256` already diagnosed this and prescribed the fix** —
declare which edges are single-valued per subject, **sub-scope `based-at` per `(unit, site_type)`** so
garrison + field basing don't collapse — and it was never closed.

Verified by running both conventions through the real evaluator with the real seeded observable:
production key → `[]`; slot key → `Alert(before=site_rawalpindi, after=site_rahwali)`.

### 2.2 Nobody owns deriving unit→site basing

D-2.7 removed it from INGEST on a false premise (§1, D-P4.1); `handoff-answer-key-grounding.md:172-174`
and `handoff-resolve.md` hand it to RESOLVE; **`phase3-resolve-PLAN.md` has no such work item** — its only
reference (line 165) *assumes the outcome*. SC-2, SC-4, MON-1, MON-2, MON-3 and the flagship demo beat all
sit on an edge no service is tasked with producing. Resolved by D-P4.1/2/3.

### 2.3 The relocation documents cannot emit a relationship at all

`format_sniffer` routes `source_type: satellite` unconditionally to `imagery_geoint`
(`ingest/extract.py:496,509`), and `ImageryGeoint` (`extract.py:373-381`) has **no `relations` field**.
So d17 and d18 are structurally incapable of stating any relationship — dated or not. d17 yields 13
claims, d18 yields 8, **zero relationships between them**. Corpus-wide there are exactly **2** `based-at`
claims (d02 Karachi, d14 China); the oracle expects three plus a `supersedes`.

**Adding a date field to `RelationMention` fixes nothing for d17/d18 until the imagery shape can emit the
occupancy lane.** D-P4.2 is therefore a prerequisite for the whole beat, not a nicety.

---

## 3. Per-service corrected findings

### SCORE

| ID | Verdict | Corrected fix |
|---|---|---|
| SC-1 | **still-broken, worse** (16 bogus nominations, was 12) | Nomination is attached to the **consumer**, not the supplier — the in-degree test is a fact about the dependent, the *finding* belongs on the supplier. Note the file already contradicts itself: pass 2 (`precompute.py:133-134`) treats `source` as supplier while pass 1 nominates `target`. Fix per **D-P4.7** (`supplier_end` in ontology, both passes read one accessor). Handoff is **wrong** that all sustainment edges point at the consumer — `exported-by` is `contract → manufacturer`, so the supplier is the `to` end; pass 2's closure is therefore *also* wrong today (unreported second defect). **Second, deeper fix:** partition the sole-degree test by the component's `functional_role` (already declared in ontology, already extracted, already in the answer key) — without it, a variant with 3 components has in-degree 3 and HT-233 is **never** nominated. The current logic only appears to work because the graph is sparse. Empirically, direction-fix alone surfaces the real supply tier and drops every variant/unit nomination **with no node-type list**. |
| SC-2 | **still-broken** (`_half_life_days` returns `None` for both real `based-at` claims; `freshness_variant` is set by **no producer anywhere**) | **Not** a bare `based-at: 540` — that is a magic number and it is the *slower* of the two declared rates, i.e. the choice that hides staleness longest. Root cause is bigger: `config/ontology.yaml` declares `freshness_class` on every edge and **zero lines of backend code read it**. Add `half_life_defaults` keyed by freshness class (numbers from `spine/04:184-197`, not invented) + an `EdgeLaneIndex.freshness_class()` accessor + a config lint (mirror `EdgeLaneIndex.collisions`) so a perishable edge with no reachable half-life fails loudly. Stamp a `freshness-variant-assumed` gate entry when the class default fires. **Escalate:** perishable default 30d (field) makes nearly every basing edge stale; 540d (garrison) makes almost none — demo-visible, needs an options call. Variant tagging belongs to whoever mints the derived basing claim (D-P4.3). |
| SC-3 | **NOT a SCORE defect — stale** | The code does exactly what `spine/04:201-203` specifies (and is *more* permissive than the doc: soft 0.5 vs a hard requirement). The defect is in the answer key. **Reroute to DATA-C/EVAL per D-P4.8** with this evidence so they don't re-derive it: `mfr_taian`'s only two looks are `d24_tel_chassis_attribution` (think-tank) and `d25_hq9_site_fingerprint` (curated-register) — those are the only two docs mentioning Taian/Wanshan — and `answer_key.json`'s own `why` reads *"confirmed via d24 which directly names supplier+component+relationship"*, a single-source justification for a confirmed grade. `ANSWER-KEY-GROUNDING-AUDIT.md:119` repeats it without catching it. **Two legitimate, non-oracle-driven observations to raise separately** (both are credibility retunes → need ratification, do not fold in): (i) a primary-record vs secondary-analysis discipline split is defensible tradecraft but does **not** help `mfr_taian` (both looks are secondary); (ii) the group weight is applied **twice** — in `group_confidence` (magnitude) and again in `_effective_looks` (count) — which is stricter than `spine/04:167-171` describes. |
| SC-4a | **stale root cause** | The machinery **already exists** — `view/supersede.py:74-80` sets `superseded_by`/`supersedes`, `attrs["contradiction"]` **and** cross-links `opposing_claims`; it is wired at `pipeline.py:280` and consumed at `pipeline.py:383,398-406` → `status.py:94`. The handoff is wrong on three counts ("no service synthesizes them", "nothing sets the flag", "**RESOLVE** must populate `opposing_claims`"). Real cause is §2.1. **Plus:** `superseded_by` is written and read by **nothing** in SCORE (`status.py` derives `stale` purely from half-life) — the demo's headline "superseded → stale" consequence does not exist. |
| SC-4b | **still-broken (handoff correct)** | `sustained-by` genuinely never synthesized. But its **inputs do not exist**: 0 `replenishes` edges, 0 `interceptor_stockpile`, 0 `techdata_authority` nodes in the current view — **D-2.7's promised sustainment-node minting is absent from the re-recorded bundles despite being ratified and claimed code-complete.** Send back to INGEST before building the rollup. Derived edge status = weakest link on the path, capped at probable, `claim_ids` = union of the path's claims (gate G4), `derived_via` stamped. |

**Contract mismatch to reconcile (DATA-C/EVAL, not SCORE code):** the oracle models `supersedes` as a
**node→node edge** (`site_rahwali → site_rawalpindi`); the code models it as **edge→edge id fields**. Any
probe measuring one against the other reads 0 forever. `config/ontology.yaml:93` declares a `supersedes`
edge type nothing emits. Orchestrator's call: emit the site→site edge **in addition** to the internal
version-linking, so the relocation is visible in the graph and traceable.

### The supersede rule (D-P4.4) — where each guard lives

> **B supersedes A iff:** (i) same resolved subject + same edge type, that edge declared **functional over
> the subject**, plus any declared sub-scope (`based-at` is single-valued per `(unit, site_type)`);
> (ii) B's object ≠ A's object (same object ⇒ corroboration, full stop); (iii) their `event_time`
> **intervals do not overlap** and B is strictly later — overlapping ⇒ **contradiction**; missing or
> indistinguishable ⇒ **candidate_supersede**; **never `report_time` for ordering without flagging**;
> (iv) B independently reaches ≥ probable on ≥1 independent look **with a clean deception gate**.

- (i) cardinality + sub-scope → `config/ontology.yaml` (config-driven, gate G6).
- (i) key construction → **`resolve/entities.py:43` AND `view/pipeline.py:275` must change together**, and
  must agree with `edge_direction.py`'s docstring and `PROGRESS.md:454-457`. Fixing one leaves the other
  broken. Re-check that reviving `resolve/scoring.py:29-42` doesn't now over-fire.
- (ii)/(iii) → `view/supersede.py`. **Use `canonical_iso_bounds` properly** (`schemas/values.py:103-122`,
  already imported at `supersede.py:24`): compare `(lower, upper)` intervals, ~8 lines. Today
  `_latest_iso` takes only index `[1]` and compares with **string equality**, which produces two concrete
  bugs: d18's vague `2025` (upper `2025-12-31`) ranks **newer** than d19's precise `2025-03-27` and would
  retire the confirmation — **inverting the demo beat**; and two equally-vague `2025` claims share an
  upper bound and get flagged **contradiction → HITL** when the truth is "unorderable" (the
  `candidate_supersede` branch at `:64-67` already exists and is never reached). Also replace `_latest_iso`'s
  `max` over a target's claims — a late *restatement* of an old fact currently makes it "newest" and
  **reverses the arrow**.
- (iv) confidence floor → **cannot live in `supersede.py`** (runs at `pipeline.py:280`, before
  `score_claims` at `:363`). Have supersede emit only `candidate_supersede` + an ordered pair, and let a
  post-status pass promote it once B clears the floor. The floor was **already ratified** (D8 /
  `md/11:22` / `SCORE.md:94-97`) and implemented nowhere. Extend it to require a clean deception gate:
  `d20_supersede_spoof` is grade **E**, `bias_vector: adversary`, `decoy_risk_flag: true` — and
  `view/pipeline.py:95-132` already computes exactly that signal.
- `superseded_by → stale` → wire into `credibility/status.py`.
- **Add a test that builds from claims with `resolved_ref=None`** (the production path), or the drift returns.

### INGEST (new Phase-4 work, from D-P4.1/2/6)

1. **Add a date slot to `RelationMention`** (`extract.py:190-201` — currently 4 fields, no date; every
   other mention type has one). Prompt for it as *"when the source says this relationship was true"*.
   **Plumbing is already complete and unused**: `_Emitter.relation(..., event_time=...)`
   (`extract.py:727-782`) forwards it on all three branches; every caller (`:933`, `:1162`) omits the
   kwarg. Fix = one field + one prompt clause + passing an existing argument.
2. **Require the date only where `freshness_class` is perishable/semi-durable** (D-P4.6), with the
   fallback ladder: stated relation date → the observation sentence's date → document `report_time` →
   nothing; **record which rung fired** (`values.py:31` already has the
   `explicit/derived_from_label/relative/model_guess` enum for this).
3. **Add a `relations`/occupancy slot to `ImageryGeoint`** (§2.3) so satellite docs can emit the
   observed equipment-at-site lane. Without this the beat is impossible.
4. **Fix the imagery lane's backwards basing assertion** — `imagery.py:69,403-404` asserts
   `<site, based-at, variant>`, off-lane in **both type and direction** vs `ontology.yaml:81`
   (`unit → basing_site`), and the read-side canonicaliser (`pipeline.py:347`) cannot repair a
   (site, variant) pair. It will mint a third malformed shape the moment it fires with a `literature_ref`.
5. **Date the grounding VLM observation** (`imagery.py:369-376` sets only `report_time`/`ingest_time`;
   `ingest/lane.py:147-165` never threads the sibling text's stated pass date through), **then** add
   `event_time` inheritance over `premises` in `attribute.py:333-341` / `imagery.py:400-409`. Step 2
   alone is a no-op — do them in this order.

### The derivation proposer (D-P4.3)

Generalise `ingest/attribute.py`'s connection-triggered proposer: offline, upstream of the append, over
the previous frozen resolved view — **never inside `rebuild()`** (gate G1). Emits
`kind="inference"`, `premises=[occupancy observation, formation-hint claim]`, `doc_ref` spanning **both**
premises (gate G4), `event_time` inherited from the grounding observation. Raise-only; SCORE caps it.
This is a rename of an existing mechanism, not new machinery.

### ARCH

| ID | Verdict | Corrected fix |
|---|---|---|
| AR-1 | **done — nothing left for ARCH** | Registry landed (14 entities / ~76 aliases). Consumption is Phase-3 `P3.0`. **Do not wire it from an ARCH branch** — that duplicates RESOLVE. **Unassigned gap:** registry aliases never reach the view. `agent/context.py:92` reads `n.attrs["aliases"]`; nothing writes it. Phase 3 should stamp the adopted entry's `canonical_name` + `aliases` onto the canonical `NodeView.attrs` — one mechanism then serves ASK, the lens and MONITOR. **Keep the display name separate from the match keys**: `config/entities.yaml:130` sets `canonical_name: "HQ-9/P (export designator; …)"`; if that becomes `node.name` it pollutes the BM25 token pool and leaks a parenthetical sentence into answers and alerts. Ensure the plain designator is in the alias list. |
| AR-2 | **still-broken; two defects, handoff names one** | (a) `lens.py:54-55` does literal `anchor in und` — no resolution. (b) **Silent empty**: zero anchors yields an empty view whose meta reports only `scoped_from_nodes`. A lens that cannot find its own subject is a coverage condition and must say so. Fix: **one shared resolver** (`resolve/anchor.py`, the view-level sibling of `_matching_eids`, reusing `normalize` + `AliasIndex` + `entities.as_map()`) — **not** a lens-local second copy. Ladder: literal id → registry canonical/alias (type-gated) → alias class. Record `anchors_requested/resolved/missing` + how each matched in `GraphView.meta`. **Refactor `observe/observable.py:108` onto the same helper — there are three copies of this check and fixing only the lens leaves MONITOR broken.** Layering is fine (`view/pipeline.py:29` already imports from `resolve`). **Handoff is wrong** that `tools.py:397` is the same anti-pattern — it raises an actionable `ToolError`, which is the designed contract; downgrade that cross-reference. UX shape agreed with the orchestrator: subject picker = BM25-ranked search over subjects; ASK path = the same resolver. |
| AR-3 | **still-broken, understated** | Not "partially honoured" — the shipped config declares **four keys, none of which the code reads**, so `_passes_materiality` falls straight to `return True`: **zero filtering, 100% of the time.** Implement `node_types_allow`; make `never_drop_indeterminate` an explicit read (the code already behaves this way by accident — make the guarantee auditable). **Delete `exclude_off_subject` (D-P4.9 — oracle-only label) and `materiality_attrs`** (descriptive prose; its own comment says it describes what `query_graph` filters on; also `subjects.yaml:27-32` lists `status`, which lives on `NodeView`, not `MaterialityAttrs` — the tell that it was never a schema). Real chaff protection = hop-bound-from-resolved-anchor + `node_types_allow`; the deleted pair never had an implementation path, so this is scope-correction, not clipping. **Do NOT add a raising validator** — `ConfigModel` is `extra="allow"` **by documented design** (`schemas/base.py:27-31`) so DATA-C can add knobs without an F0 amendment; a raise would be the only exception across nine surfaces and would break hot-config writes (`api/routes/config.py:66-73`). Instead: report `unrecognised_filter_keys` in `GraphView.meta` + a gate-style CI test (alongside `test_g6_no_magic_numbers.py`). `subjects.yaml` is DATA-C-owned — route the edit via `tmp/conv/`. |

### ASK

| ID | Verdict | Corrected fix |
|---|---|---|
| AS-1 | **still-broken (crash reproduced live)** | Don't add per-builder guards (the handoff's fix) — **type-erasure at the boundary** is the defect: `run_tool` returns a union and nothing carries the discriminant. Add `RecordedCall.ok` (`"error" not in result`), have `AgentTrace.last()/all_of()` filter to `ok` **by default**, and add `failures()`. Builders then structurally cannot see an error dict. **Audit result: one crasher (`_from_get_node`, `assemble.py:149`) and three silent conflaters** (`_from_query_graph`, `_from_neighbors`, and `_from_paths`'s tail which is safe only *by accident*) that cannot distinguish "failed" from "found nothing" — which the non-negotiable requires to read differently. Reject a `ToolResult` dataclass: the dict is serialized straight to the model. |
| AS-2 | **still-broken; understated** | Live repro: all 5 hero calls error, and with AS-1 patched what ships is *"Insufficient evidence to assess comp_ht233… missing corroborating coverage"* about **a node that does not exist**, with `missing=[]` — a **fabricated assessment**, the disqualifying failure mode. **Keep the scripted plan** (ratified, `spine/09:77-79` — it's the deterministic keyless path); a scripted *plan* computes over the live graph, hardcoded fallback *ids* substitute the expected answer. **Delete the fallback literals outright** (`loop.py:148,167,171`), fail closed. **Three defects the handoff missed:** (1) anchors are typed by **string prefix** (`a.startswith("site")`) — an id convention doing a type system's job, and the reason `variant_anchor` binds to a *unit*; type from the registry or `get_node`. (2) `loop.py:170` asks for a component's maker over **`manufactures`**, which Phase-1 D-A.1 tightened to Manufacturer→**Variant** — post-Phase-3 that step **can never connect**; derive via `EdgeLaneIndex.canonical_edge("manufacturer","component")`. (3) `context.py:97-105` never indexes `config.entities`. Refusal text should be built from the tools' **own** error+suggestion strings — honest, actionable, zero new prose, zero fabrication risk. Do **not** add a `kind` field to `RefusalPayload` without logging it in `API-to-FRONTEND-contract-log.md`. |
| AS-3 | **still-broken** | Raise on unknown id, matching every sibling tool. The ReAct loop recovers fine (`run_tool` converts `ToolError` → `{error, suggestion}`, the planner re-issues). **Caveat the handoff missed:** the guard must accept **known-gap ids** — `check_sufficiency` legitimately takes a `KnownGap.id`, and live gap ids (`gap:HQ-9/P`) are **not** node ids. Test both the negative and the gap-id positive. |
| AS-4 | **half stale** | The cited junk is gone or scheduled: ad-hoc predicates **~22→0** (Phase 2); `same-as` **42→53** but Phase-3 D-P3.4 stops drawing them. Whitelisting to dodge those would be a **hack** that masks a Phase-3 regression. **Still valid on a different argument:** `distinct-from` stays drawn *by design* and asserts **non**-identity — a path through it is a false chain; same for the evidence lane (`evidenced-by`/`corroborates`/`contradicts`/`derived-from`). Fix at the **tool default** (`find_paths` defaults `allow` to the ontology's traversable lanes) not as a literal list on the hero call — that covers the free ReAct loop too, and `loop.py:174` then needs no change, which is the tell it's the right layer. Frame it in the PR as "the ontology declares which lanes are relations", not as junk-hiding. |
| **AS-5** | **NEW — not in the handoff** | **The refusal templates are unreachable dead code.** `tools.py:481-483` compares a `str` slot against `require.all_of`/`any_of`, which are lists of **dicts** → always `False`; and `a or b` short-circuits so a template with a non-empty `all_of` never has its `any_of` examined. All seven analyst-authored `refusal_template` strings are unreachable and every refusal falls through to hardcoded fallback prose. **CLAUDE.md names these templates as the mechanism that enforces the non-negotiable.** Fix: iterate `all_of + any_of` and match on `set(entry.keys()) & set(missing)`. Re-check `tests/agent/test_ask.py:40` and `test_tools.py:176` before landing. |
| **AS-6** | **NEW — `find_entity`** | It **computes ranked candidates and throws them away**, raising instead (`tools.py:214-217`). Two compounding index bugs (`context.py:98-105`): the alias table is attached only to a node whose **name** equals the canonical, so the entire `HQ-9/P` entry (incl. `FD-2000`, `HIMADS`) is **silently dropped**; and the canonical string itself is never indexed as searchable. Tests pass only because the fixture names the node `HQ-9/P`. **BM25 already exists and runs** (`rank-bm25` declared, imported at `tools.py:21-22`) — but is rebuilt **per call**; move it into `ToolContext.build`. Fix: return a ranked candidate list with per-candidate `type`, `status`, `claim_count`, `why` (which surface matched, which leg scored), aliases, `distinct_from`, ≤2 neighbours, ≤2 sources. **Never auto-bind when a `distinct-from` sibling is also in the candidate set** — that promotes the planted look-alike traps from something the scorer must survive into a structural veto. Tier ladder: exact → punctuation-squashed (`HQ-9/P`≡`HQ-9P`, the single change that fixes the demo anchor) → alias class via RESOLVE's `AliasIndex` → blended fuzzy+BM25, capped below the exact tiers. **Do not read `config/entities.yaml` from ASK** — HITL-learned aliases live in the decision log and replay through `AliasIndex`; a registry shortcut fixes one demo string and leaves the adaptation story broken. Net token effect is a **saving** (a near-miss currently costs a whole extra turn). No API/frontend contract impact (`find_entity` is not exposed by any route). Amend `spine/09:93` "actionable errors" → "actionable results". |

### MONITOR

| ID | Verdict | Corrected fix |
|---|---|---|
| MON-1 | **confirmed; handoff's line cite omits the important key** | Dead keys are `:12` (`match_on`) **and** `:14-17`; `anchors_within_hops` (`:13`) **is** consumed. **`unit` should be DELETED, not implemented** — it duplicates `watch_instances`, which already exists, is the documented resolved-instance scope channel, and is what the live proposer populates; two scoping channels can disagree. **`match_on` is the load-bearing one**: `agent/propose.py:41-48,163` stamps it onto **every** analyst-drafted observable and **nothing reads it at either end** — a hot-config promise failing in the shipped path, not a seeded-YAML nit. `from_site`/`to_site`/`window` → a generic `where_before`/`where_after`/`where_change` condition block evaluated by the **existing DSL** (`observe/dsl.py:68-84`, which already raises on unknown operators) — not three new trigger keys in the one file whose docstring promises no per-observable branch. Unconsumed keys → return them on `CompiledTrigger`, surface in `explain()` (which `propose.py:170` already pipes to the analyst), and reject at config-write/arm time — **not** a pydantic-level raise (fights `extra="allow"`). **Measured consequence today:** anchors are absent → `resolve_scope` returns `None` → the flagship tripwire watches the **entire graph**, and a Beijing street-address change on a manufacturer fires it. |
| MON-2 | **confirmed; premise intact after Phase 2, for a reason the handoff didn't state** | All 452 `ingest_time` values are the single frozen `2026-07-19` (`"frozen-seed-baseline"`), and `timeref.py:34` checks `ingest_time` **first**, so Phase-2's real `report_time` work changes nothing for the rewind. **A valid-time field DOES exist** (`schemas/claim.py:122`, consumed by `supersede.py` and freshness) — the rewind is simply wired to the wrong axis; don't read the handoff as "there is no valid time". **But rewinding on `event_time` does NOT fix the beat — measured:** fail-open keeps 396/452 → **the same 100 edges as today** (no delta at all); fail-closed keeps 19 → **3 nodes** (graph evaporates). Deeper: valid-time is an **interval** question and `EdgeView` has no `valid_from`/`valid_to` — a point filter over an interval model is an approximation wearing a semantics. Resolve per **D-P4.5**. Also **split `claim_available_iso`**: it currently feeds *both* the rewind filter (`pipeline.py:340`) and the freshness "now" (`pipeline.py:375`), so changing the availability definition silently moves every half-life in the system. **Never fabricate staggered ingest dates** — `schemas/claim.py:172-178` calls a fabricated date a disqualifying failure. |
| MON-3 | **confirmed; handoff's fix is necessary but not sufficient, and aimed at the wrong layer** | Handoff says "the fix belongs in MONITOR's grouping, not RESOLVE's edge-instance scheme" — **wrong**: `resolve/entities.py:43` emits the same broken key and `pipeline.py`/`supersede.py` depend on it (§2.1). Patch only the detector and you get the alert but **not** the stale Rawalpindi edge — you'd ship half the beat and lose the credibility half. Do **both**: the ontology cardinality declaration (which revives supersede) **and** `match_on` as the detector's config-declared grouping key. `_watched` (`evaluator.py:89-91`) already returns `el.source`, so the **alert subject is already correct** — only the grouping is wrong. Fix `tests/fixtures/per_stage/alert_delta.json` + `tests/observe/test_evaluator.py` to the production convention in the same change. |
| **MON-4** | **NEW** | **Alerts carry no provenance** — `schemas/view.py:147-156` has no claim ids, doc refs, or confidence. In a system whose non-negotiable is one-click traceability, the alert is the **only** artifact without it. An analyst gets "the unit moved" with nothing to click. |
| **MON-5** | **NEW** | **The frontend never reads the live alert feed.** It is already typed (`frontend/src/api/types.ts:175`) and already on `GET /view`; `WatchView.tsx` / `AlertCard.tsx` render frozen demo constants and **hardcode the "armed" badge**. The panel is a picture of a tripwire. |

---

## 4. Build order (by unblocking power, not by service)

1. **INGEST**: occupancy lane emittable from `ImageryGeoint` (§2.3) + relation date slot + fix the
   backwards imagery basing direction + date the VLM observation. *Nothing downstream is testable first.*
2. **Ontology**: `instance_key`/functional declaration (+ `based-at` sub-scope), `supplier_end`,
   `half_life_defaults` by freshness class. Three config declarations that unblock five findings.
3. **Both key producers together** (`resolve/entities.py` + `view/pipeline.py`), reconcile with
   `edge_direction.py`'s docstring and `PROGRESS.md`; add a production-path supersede test.
4. **ASK** (all independent, all safe now): AS-1 → AS-3 → AS-5 → AS-6 → AS-2 → AS-4.
5. **SCORE**: chokepoint direction + function partition; freshness-class defaults + lint; the
   post-status supersede gate (confidence floor + deception gate); `superseded_by → stale`.
6. **Derivation proposer** (D-P4.3) + `sustained-by` rollup — after INGEST re-mints the sustainment nodes.
7. **ARCH**: shared anchor resolver (+ refactor the observables copy onto it); materiality filter.
8. **MONITOR**: `match_on` grouping; trigger validation + DSL condition blocks; de-pin the seeded
   observable; alert provenance.
9. **EVAL/harness**: staged-ingest beat; retire `PRE_RELOCATION_AS_OF`; split `claim_available_iso`.
10. **Frontend**: read the live alert feed.
11. **DATA-C/EVAL**: `mfr_taian` → probable (D-P4.8); `supersedes` shape reconciliation; the
    `report_time` gap (**29 of 53 sources carry no `report_date`, including `d18` — the doc that triggers
    the relocation observable**).

## 5. Design-note disclosures generated here (→ `artifacts/md/16-design-note-disclosures.md`)

- The rewind is **transaction time** — "as we knew it on DATE", never "as it was". A true valid-time
  rewind is roadmap and degrades on a corpus where most claims carry no event date. Saying so is the
  right register for a system whose whole premise is naming what it cannot do.
- Undated claims are **retained** in a rewind (conservative: hide only what we can prove hadn't arrived).
- The five built-but-unwired mechanisms (§0) and what that says about late integration in a parallel build.
- Basing is **earned, not stated**: observed occupancy and derived unit-attribution are modelled at
  separate confidences because no source states a designated unit at a named site.

## 6. Verify

```bash
export CHANAKYA_ROOT=<worktree>
backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```
Phase-4 acceptance: no `gap:chokepoint:*` on variant/unit types and the real supply tier nominated ·
stale count > 0 once basing lands · `supersedes`/`sustained-by` non-zero · the hero path returns a real
chain (or, pre-Phase-3, an honest refusal naming the unresolved anchors with **no** hardcoded id anywhere
in the output) · `view_lens.json` non-empty with `anchors_resolved` in meta · the relocation alert fires on
a staged ingest **and stays silent on the d20 spoof and the recycled imagery**.
