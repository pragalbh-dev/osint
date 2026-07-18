# Spine — Detailed Design (PROPOSED)

**Status: proposed, for ratification.** This memo resolves every open question left in spine docs
`01`–`07` into a concrete verdict, under one binding constraint you set: **the spine must extend to
Use Case B later without core rework.** Nothing here contradicts a locked decision; where a doc had a
"leaning," this either confirms it or overturns it with a reason. Read §7 first if short on time —
it lists the judgment calls that most deserve your veto. Upon ratification, verdicts move into the
`DECISIONS.md` ledger and each source doc's tail gets updated (per the working agreement); until then
the ledger's "Open decisions" section points here.

Inputs: `../md/01-assignment.md` (exact A/B/C wording), `../md/04-claude-chat.md`,
`../md/05-data-scoping-C.md`, spine docs 00–07, C docs 00–02.

> **Update (2026-07-17).** The stack / retrieval / hosting / extraction calls have since been **decided** —
> see `../md/07-stack.md`, `09-retrieval-and-tools.md`, and `DECISIONS.md` ("Stack & retrieval" + "Spine 2.0"
> tables). This memo is reconciled to them inline: extraction is **live at ingest** (not frozen-only),
> `rebuild()` is a **live hot-config op** with **materiality precompute** (no restart), the agent is a
> **bounded ReAct loop over ~7 `graph_*` tools** (`09`), hosting is **EC2 + Cloudflare Tunnel**, and
> determinism is **de-prioritised** (a free property of the frozen baseline, not a capability constraint).
> The scoring / schema / independence / HITL specifics below stand as the detailed design.

---

## 1. The one architectural commitment: two append-only logs + a rebuilt view

The bi-level graph (evidence vs knowledge, `01-graph-and-ontology.md`) should be implemented as
**event sourcing**, made explicit:

```
EVIDENCE LOG  (append-only)   claims extracted from sources        ─┐
DECISION LOG  (append-only)   HITL adjudications + system events    ├─► rebuild() ─► KNOWLEDGE VIEW
CONFIG        (versioned)     ontology, weights, templates, lenses ─┘              (entities, edges,
                                                                                    events, statuses)
```

**The knowledge layer is a pure function of (evidence log, decision log, config).** `rebuild()` runs
resolution → credibility scoring → status assignment → **materiality precompute** (chokepoint_count/status,
substitutability_state — the attrs the retrieval tools filter on, `09-retrieval-and-tools.md`)
deterministically. It is a **live in-process operation** triggered by any ingest / HITL decision / config
write — **not a boot-only step and never an app restart** (the hot-config rule, `09`): user config lives in
a store the process re-reads on each rebuild. At demo scale (hundreds of nodes) a full rebuild on every
change is milliseconds, so we don't need incremental materialization.

This one decision buys six properties we otherwise have to engineer separately:

1. **Traceability** — every node/edge in the view carries the claim IDs that produced it; "click node
   → claims → doc → exact row/line" is a lookup, not a feature.
2. **HITL propagation** — an analyst decision is a decision-log entry; replay applies it. "Override
   changes downstream state" (`05`) is structural: reject a claim, rebuild, the query answer changes.
3. **Reversible merges** — merges are log entries (accepted `same-as` assertions), the view collapses
   them; a later split is just another entry. Answers `03`'s merge-representation question.
4. **Retraction** — a retraction is itself an appended claim targeting a claim ID; the view excludes
   retracted claims. Answers `01`'s immutability question.
5. **Reproducibility where it matters** — the graded read/Ask beats run identically every time: the
   **seeded baseline + tested queries** replay from frozen evidence/decision logs, with agent/adjudicator
   outputs stored as recorded, cited artifacts (Opus 4.8 rejects sampling params, so there's no
   "temperature-0" knob anyway). Determinism is **de-prioritised as a constraint** (`09`): it is a *free
   property of the frozen baseline*, never a reason to cut capability — the **live-ingestion lane is fresh
   by design** (that's what makes it *monitoring*), with a recorded hero-trace as the network-safety
   fallback for the graded Ask beat. Once a live-ingested claim is appended it *is* a frozen log record, so
   `rebuild()` stays a pure, replayable function (`07`, `09`).
6. **Deterministic confidence** — "where confidence lives" (`01`): per-claim scores are computed at
   ingest; per-assertion confidence/status are recomputed inside `rebuild()`. Cheap by construction.

**Store verdict** (open question in `01`): **SQLite for both logs; NetworkX for the view**, serialized
to JSON for the frontend. Rationale: the graded thing is provenance discipline, not database choice;
NetworkX gives free traversal for the multi-hop agent and trivial export for the graph explorer;
SQLite keeps the logs queryable, transactional, zero-ops — "code we can run" with no setup friction.
Neo4j/Kùzu is the documented scale path (see §6), not the demo path.

**One rebuild subtlety the C research surfaced — supersedes vs. contradicts.** When two claims about
the same resolved entity×edge-instance disagree, `rebuild()` must decide which. If their `event_time`s
*differ*, the newer one **supersedes** the older (a state change — a unit relocated) and the old
assertion degrades to stale, not contradicted. If their `event_time`s are the *same*, it's a genuine
**contradiction** → flagged, routed to HITL. When instance identity is uncertain (is this the same
mobile unit?), the resolver emits a *candidate-supersede* rather than silently overwriting — so
"vacant@SiteA" can't erase "occupied@SiteB" for a unit that may simply have moved. Both match on the
resolved entity×edge-instance (§3.1's `resolved_ref`), never on a designator string.

---

## 2. The B-extensibility contract

### 2.1 What B actually demands (from the brief's exact wording)

B's target output: *"a strategic warning estimate — current posture, most-likely and most-dangerous
courses of action, explicit confidence per judgement, the specific observable indicators that would
confirm or deny each course of action and when next coverage is due, and a clearly marked
alternative/dissenting view. Every judgement traceable to source; no unsupported leap from activity to
intent."* Hard part: *"separate exercise and signalling from real mobilisation; stay resistant to
planted or withheld signals; recognise when the system is being deceived."*

Decomposed, B needs from the spine: **(a)** activity *events* in time, not just structural edges;
**(b)** "what was true when" vs "what did we know when"; **(c)** a first-class home for *inferences*
(hypotheses, intent judgments) distinct from observations; **(d)** batteries of indicator tripwires,
cheap to declare; **(e)** *absence* of expected signals as evidence; **(f)** a credibility score whose
inputs stay interrogable (deception resistance = asking *why* confidence is high).

### 2.2 Six pre-wirings (each ~free now, expensive to retrofit)

| # | Pre-wiring | Cost now (C build) | What B gets later |
|---|---|---|---|
| 1 | **Events are first-class** in the meta-model: `{event_type, time-interval, location, participants}`. C already has them implicitly — TransferEvent (SIPRI row), InductionEvent (ISPR PR), SightingEvent (social/imagery), ExerciseEvent (NOTAM/NAVAREA). Name them; don't bury them as edges. Structural edges like `based-at` are *states derived from events*. | Zero — relabels what C extracts anyway; brief requires "entities, relationships **and events**" regardless | B's indicator stream is a query over events; A's time series is an aggregation over events |
| 2 | **Bi-temporal stamps on every claim**: `event_time` (when true in the world), `report_time` (when published), `ingest_time`. | Three fields + discipline. C needs the first two anyway (capture-time ≠ event-time trap; "last imaged 2016" printed as current) | Warning timelines; "what did we know when"; retro-analysis of missed indicators |
| 3 | **Inference is a claim kind** with lineage: `{kind: inference, premises: [claim_ids], rule/agent, confidence}`, appended like any claim. C uses it thinly: "tender for spares ⇒ probable induction"; chokepoint findings. | One enum value + one field. Makes "observed vs inferred" in answers structural, not prompt-level | ACH hypotheses = scored inference claims with evidence-for/against links; the whole B layer has a substrate |
| 4 | **Observables are declarative config**, evaluated by one engine over view deltas (spec in §3.8) — never a hardcoded check. | Build the evaluator once instead of hardcoding C's single tripwire — hours, not days | B's I&W indicator battery = N config entries + a diagnosticity-weighting layer on top |
| 5 | **Absence as evidence**: allow negative-polarity observation claims ("imagery of site S on date D shows *no* TELs") and let sufficiency templates treat empty slots as structured absences. | A `polarity` field + the templates we're building anyway | "Withheld signals" reasoning: expected-but-absent indicators become queryable evidence, not silence |
| 6 | **Decomposed credibility**: store the score *breakdown* (source-class base, integrity flags, independence groups, freshness factor) on every assertion, never just the scalar. | We need the breakdown for the demo's explainability anyway | Deception resistance: "confidence is high *because* three sources corroborate — but they share one origin" is a query |

### 2.3 Explicit non-goals now (B's 30%, not the spine)

Do **not** build: ACH scoring, MLCOA/MDCOA machinery, diagnosticity weights, dissent generation,
multi-theatre fusion, deception-pattern detectors beyond the too-clean penalty + coordination check.

### 2.4 What B costs later, given the contract

New config: B event types, indicator observables, B sufficiency templates, theatre lenses (a lens with
multiple anchor sets — `subject = lens` already covers it). New code: one hypothesis-scoring module
(ACH over inference claims) + one estimate-report template. Zero core rework. A, incidentally, falls
out of pre-wiring #1+#2 (baseline = aggregation over events) — worth one line in the design note.

---

## 3. Concrete schemas & formulas

### 3.1 Claim record (evidence log)

```yaml
claim_id:      c-000123
source_id:     src-ispr-2021-10-14        # registry entry: class, origin, cadence
doc_ref:       {file, span|row|frame}      # the exact line/row/box cited
kind:          observation | inference | retraction
polarity:      positive | negative         # negative = observed absence (pre-wiring #5)
asserts:       entity | relationship | event
payload:       (subject, predicate, object) | entity-descriptor | event-descriptor
event_time:    2021-10-14                  # a.k.a. C/01's `valid_time` — when true in the world
                                           #   (interval allowed; nullable+flagged). Powers supersedes-vs-contradicts.
report_time:   2021-10-14                  # when the source published
ingest_time:   2026-07-17
resolved_ref:  {entity_id, edge_instance}  # what this resolves to — supersede/contradict match on THIS, never a string
extraction:    {method: llm|vlm, model, model_conf}     # model = extraction model id; demo: model_conf held at 1.0; parser path = roadmap
premises:      [claim_ids]                 # inference only
targets:       claim_id                    # retraction only
```

**Naming reconciliation with C/01.** `event_time` here ≡ C/01's `valid_time` (the real-world time an
observation is *about*); the C ontology's `Indicator` is this claim record's `kind: observation`
instance. The `source_id` points at a **Source registry** entry carrying the deception-relevant fields
the C research added: `source_type`, `reliability_grade` (STANAG A–F), `primary_origin_id` +
`aggregator_of` (circular-reporting / aggregator-inheritance detection), `bias_vector`
(operator-state | exporter-state | third-party | commercial | adversary), and
`adversary_denial_flag`. These feed the independence grouping (§3.5) and the resolver (§3.4).

Claim-dedup rule (`02`): same assertion restated within one document = **one claim, multiple
`doc_ref` spans**. The same assertion across documents = **separate claims** — never merged, because
corroboration counting and independence grouping need them separate.

### 3.2 Decision/trace record (decision log) — answers `05`'s trace-schema question

```yaml
event_id, ts
actor:       system | analyst | agent
stage:       resolution | credibility | integrity | alerting | qna | ontology | coverage
type:        merge_proposal | merge_adjudication | status_override | integrity_flag |
             alert_fired | alert_disposition | template_eval | schema_proposal | coverage_event
subject_ref: claim/node/merge/alert id
context:     snapshot shown to the decider
options:     what was offered
decision:    what was chosen (+ optional rationale)
effects:     state changes applied on rebuild
```

One schema serves HITL, the learning loop, *and* audit — the analyst-decision subset of this log is
replay input, not just telemetry. `coverage_event` records observation *attempts* (e.g. "frame
reviewed, 95% cloud, unusable") — distinct from a negative observation, and consumed by the
sufficiency templates for "next coverage due."

### 3.3 Derived assertion state (knowledge view)

Every edge/event in the view carries: supporting claim IDs grouped by independence (§3.5), opposing
claims, confidence breakdown (per pre-wiring #6), status, freshness (`last_support_time`, half-life,
decay factor), and the latest template evaluation.

### 3.4 The Confidence Resolver — answers `04`'s score-combination question

This is the **Confidence Resolver** that `C/01-materiality-ontology.md` references as living here: a
*versioned, auditable* function that computes confirmed / probable / insufficient. It runs in **two
stages, never one product**: (1) a **per-claim credibility** = `reliability × integrity × freshness`,
then (2) **corroboration as a noisy-OR over independence groups** of those per-claim scores (origin- /
discipline- / interest-independent). Corroboration is *not* a multiplicative axis inside credibility — it
is a separate pooling step over separate claims (see `../md/08-spine-2.0-review.md` §A: two scores, never
averaged).

**Form verdict: transparent weighted algebra with rule overrides. Not Bayesian networks, not learned
weights.** Auditability > sophistication, and Module 1 demands analyst-tunable factors.

- **Per-claim:** `claim_credibility (c) = R(source) × Π(integrity_penalties) × freshness`, where
  `R(source)` is *derived from the factor rubric below*, never a hand-typed per-source constant.
  **Extraction confidence (`model_conf`) is held at 1.0 for the demo** — everything is LLM-extracted, so
  a per-claim extraction-confidence factor drops out of the arithmetic; it stays as the seam for a later
  non-uniform extractor / low-confidence VLM read (design-note it).
  `integrity_penalties` bundle the M4/deception signals (§3.5 + the C research): failed
  artifact-integrity, first-seen/recycled mismatch, coordinated-inauthenticity, and a
  `bias_vector`-aligned "too-clean" placement. **`adversary_denial_flag` is NOT one of these
  multipliers — it is a GATE:** a claim from an adversary asserting a fake second-source or denying a
  dependency is *excluded from independence grouping* (§3.5) and caps the affected assertion at
  *probable*; it is never taken at face value nor silently multiplied down. Likewise the C-specific
  single-pass imagery case — a signature match with `decoy_risk_flag` set — is a **gate that caps the
  assertion at *probable***, a context gate, not a penalty term and not a merge.
- **Freshness is per-claim:** `freshness = 2^(−age / half_life)`, age from the claim's own `event_time`
  (fall back to `report_time`, flagged); durable edge types skip decay (§3.6). A stale claim contributes
  a decayed `c` *before* pooling — old corroboration counts for less, and the freshest independent look
  dominates the noisy-OR naturally. (The STALE *status* overlay below is a separate honesty gate keyed on
  the freshest supporting look's age, so a pile of old corroborations can't keep a node "confirmed.")
- **Per-assertion (noisy-OR over independence groups):** `assertion_confidence = 1 − Π_g (1 − c_g)`
  where `c_g` = max `claim_credibility` in group g. One 0.6 source stays 0.6; two independent 0.6s →
  0.84; reshares of one origin collapse into one group and add nothing. Monotone, explainable in one
  sentence, and the arithmetic of why corroboration-gaming fails.

**Status machine (three gates, not one threshold):**

| Status | Condition |
|---|---|
| **confirmed** | sufficiency template satisfied AND ≥2 independent origin groups (discipline- AND interest-independent) AND `assertion_confidence ≥ 0.80` AND fresh AND no unresolved contradiction AND clean integrity/decoy |
| **probable** | `0.50 ≤ assertion_confidence < 0.80`, OR template partially satisfied (single independent group), OR any integrity / decoy / adversary-denial **gate** caps here |
| **possible** | `assertion_confidence < 0.50` — assessable but low *magnitude*; rendered as a *lead*, never in the assessed picture |
| **insufficient-evidence → Known Gap** | *assessability* fails — a required evidence **kind** is missing per the sufficiency template (§3.7). **Off the confidence scale** (a refusal, not "confidence≈0"); emits missing-slots + `next_coverage_due` + `observability_ceiling` as a first-class Known Gap node |
| **contradicted** | a credible opposing group exists within δ — flagged, routed to HITL |
| *(stale overlay)* | was confirmed, decay drops it: → "confirmed-as-of-DATE / coverage-lapsed" (annotation) → once age > half-life, demote one step to "probable (stale)" (label change) |

**POSSIBLE and INSUFFICIENT are orthogonal axes, never conflated.** POSSIBLE is a low-*magnitude* lead on
an assessable question (`assertion_confidence < 0.50`); INSUFFICIENT is an *assessability* failure — the
evidence *kind* the template requires is absent — and sits off the confidence scale entirely
(insufficiency ≠ sparsity). Keeping INSUFFICIENT first-class here (and in `04`) is what mechanises the
non-negotiable; it is the status-machine home of §3.7's Known Gap node.

**Source reliability `R(source)` is *derived from an analyst-set factor rubric*, not assigned per
class.** This is the crux of Module 1 — *"credibility based on user-defined factors / criterion."* The
analyst configures the **factors and their weights**; the number is the rubric's *output*, never a
constant someone typed. This is the difference between a defensible "user-defined factors" system and a
hardcoded tier table that only *looks* configurable. Factors (each scored 0–1, defaults in
`credibility.yaml`, all analyst-tunable):

| Factor | What it captures | High ↔ low contrast |
|---|---|---|
| **authority** | primary/authoritative *for this class of claim* | official body announcing its own induction ↔ a random blog |
| **process** | editorial / verification / analytic-coding rigor | SIPRI analyst-coded register, edited trade press ↔ anonymous post |
| **directness** | first-hand vs aggregated/reposted | eyewitness geotag ↔ "as reported by" reshare |
| **track_record** | this source's historical corroborated-vs-refuted rate | *starts at a neutral prior; the seam where dynamic per-source rating plugs in (roadmap; `../spine/06`)* |

`R(source) = Σ_f w_f · factor_f` (weights analyst-set, normalised; grounded in the Admiralty/NATO
two-axis convention — source reliability is its own axis, separate from item credibility /
corroboration). The per-class numbers below are therefore **illustrative outputs of the default
rubric**, shown so the demo has concrete values and a viewer can sanity-check the *ordering* — change a
weight or a factor score and every number re-derives:

| Source class | authority · process · directness | ⇒ R (default) | Note |
|---|---|---|---|
| Curated register (SIPRI) | high · high · low (secondary) | 0.85 | analyst-coded, not raw |
| Commercial satellite imagery | high · high · high | 0.85 | provider/timestamp/geo known (VLM-confidence is the inactive extraction seam; model_conf=1.0 now) |
| Official statement (ISPR, MND) | high · med · high | 0.75 | reliable for own announcements; euphemistic framing |
| Think-tank / trade media | med · high · low | 0.65 | hedged language shows up as intrinsic-plausibility/directness in the rubric; model_conf held at 1.0 for the demo |
| Customs/tender (synthetic-from-real) | med · med · med | 0.60 | consignee ≠ end user |
| Named social account with record | low · low · high | 0.35 | tip-off tier: can raise to probable, never confirm |
| Anonymous social | low · low · med | 0.25 | |

Note `track_record` is held at its neutral prior for the demo (all defaults above assume it); it is the
one factor that *moves on its own* once the dynamic per-source rating extension is wired. That
extension is a **four-more-weeks roadmap item** (`../spine/06`) — **but a cheap, natural next step if
time allows**, because the seam is already pre-wired: the factor exists, and the decision log already
records the confirmed/refuted history it would consume. So it's a bolt-on, not a rebuild.

Report statuses in ICD-203-style words-of-estimative-probability language (confirmed ↔ "very
likely/almost certain" ≥0.80; probable ↔ "likely" 0.50–0.80) — verify exact band wording before the
design note; it's the standard the graders' world uses.

### 3.5 Independence rule — answers `04`'s open question (upgraded to the C research's three axes)

Corroboration only counts claims that are independent on **three axes** — the C research is explicit
that failing any one produces *false* corroboration, and that this is the deception surface the brief
cares most about:

- **Origin-independent** — different publisher/author, and neither cites/quotes/links/embeds the other
  (shared image hash ⇒ same group). Crucially, an **aggregator inherits its upstream origins**: SIPRI
  *plus* the press it compiles are **not** two origins; a Source's `aggregator_of`/`primary_origin_id`
  fields collapse them into one group.
- **Discipline-independent** — different collection discipline (IMINT vs ELINT vs textual/HUMINT). Two
  reads of the *same* satellite pass are one look; imagery + an ELINT emitter-active report are two.
- **Interest-independent** — different `bias_vector`. Two **aligned-interest** sources (e.g. ISPR +
  Chinese state media, both parties to the transfer) are **not** cross-interest corroboration, however
  independent their bylines.

Implementation: cluster claims into **provenance groups** keyed on all three axes; the noisy-OR
(§3.4) runs over groups, so only genuinely independent looks raise confidence. Same-class-but-passing
pairs count at 0.5 weight. This is what makes the M4 flex work on two independent kill paths: the
recycled parade image's reshares collapse into one origin group (no corroboration boost) *and* the
first-seen mismatch applies an integrity penalty (per-claim `claim_credibility` drops). An
`adversary_denial_flag` claim is **excluded from grouping entirely — a gate, not a multiplier**: it
never enters an independence group at all, and caps the affected assertion at *probable*.

### 3.6 Freshness half-life defaults (C set; the `01`/`04` shared open item)

| Edge/event type | Half-life | Rationale (fact-change rate × source revisit rate) |
|---|---|---|
| `manufactures`, `variant-of` | ∞ (durable) | design facts don't decay |
| `imported-by` (transfer event) | ∞ | historical event |
| `supplies-component` | prime 5 y / tier-2–3 18 mo | supply relationships churn below the prime — a live dependency, not a durable design fact |
| `inducted-into` | 3 y | force structure changes slowly |
| `sustained-by` (depot/training) | 2 y | contracts/facilities churn |
| `based-at` (fixed SAM site) | 12 mo | sites persist but relocations happen; AMTI-style "last imaged 2016" must degrade by now |
| readiness/activity events | 60 d | perishable by nature |

**Coarse defaults now, calibrate later** — analyst-configurable; the mechanism and the config surface
are the decision, and the values are deliberately coarse, to be calibrated on the frozen corpus (§7).
(`04-credibility.md` prints a finer-grained illustrative per-edge breakdown; reconcile the two at
calibration — this coarse table is canonical for the *mechanism*.)

### 3.7 Sufficiency templates + coverage cadence

```yaml
assertion_type: based-at
require:
  any_of:
    - imagery_confirmation within 365d
    - independent_text_groups: {min: 2, within: 365d}
on_fail: insufficient_evidence(missing_slots, next_coverage_due)
```

`next_coverage_due` is *generated* from a per-source **cadence field** in the source registry
(Sentinel-2 revisit ~5 d; AMTI irregular ⇒ "unknown, last interval N months"; PPRA tender cycles) —
so the non-negotiable's "when next coverage is expected" is computed, never hand-written. Templates
also serve pre-wiring #5: an empty expected slot is a structured absence B can reason over.

**A failed template emits a first-class Known Gap node** (C/01's `Known Gap / Collection Requirement`
type), not just an inline "insufficient evidence" string — so *"what do we NOT know?"* reads off nodes,
not footnotes, and the output doubles as **prioritized collection tasking**. Each Known Gap carries an
`observability_ceiling` (`confirmable | probable-max | never-observable`) so a genuinely unobservable
fact (magazine depth, contract terms, C2 topology) is marked as *permanently* gapped rather than
looking like a coverage lapse that fresh imagery would fix. This is the node-level home of the
non-negotiable.

### 3.8 Observable spec (declarative; pre-wiring #4)

```yaml
observable_id: obs-basing-relocation
subject:       lens-hq9p-pk
trigger:       {on: occupancy_state_change, edge_type: based-at,
                match_on: [resolved_unit, site_instance],   # not designator strings
                anchors_within_hops: 2}
severity:      notify
disposition:   [real, noise, needs-more]     # feeds tripwire tuning (06)
```

**C's demo observable — now LOCKED in `C/02-demo-thread.md` (Q1)**, and richer than the earlier
"probable→confirmed flip" I first proposed here: **a basing/occupancy STATE-CHANGE tripwire on the
perishable `based-at` edge, scoped to the documented HQ-9B Rawalpindi→Rahwali (2025) relocation** of
one named fire-unit — now **just the seeded example**: observables are user-definable live via a DSL over
existing attrs/precomputed metrics, defined in-app with no restart (`09`). The full loop, **driven live by
`make ingest` / a UI ingest (not a scripted reveal)**: 2021 imagery = occupied@Rawalpindi → a single
2025 pass = occupied@Rahwali resolves only to **probable** (the `decoy_risk_flag` single-pass cap,
§3.4) → a second discipline-*and*-interest-independent source (§3.5) with a clean decoy check lifts it
to **confirmed** → `supersedes` (matched on resolved unit×site instance, §3.1) retires the stale
Rawalpindi position, whose `based-at` auto-degrades to **stale** under the garrison half-life. This one
observable exercises perishable-freshness decay, the decoy→probable cap, the ≥2-independent confirmed
gate, and supersedes-vs-contradicts *all at once* — a much stronger demo beat than a bare status flip,
and it still composes with the map (pins move + recolor). Secondary observables (a follow-on interceptor
order via `replenishes`; a spares tender → "probable induction") ship as *config-only* entries, not
wired into the narrative — proving observables are declarative, not hardcoded.

### 3.9 Resolution scoring — answers `03`'s open questions

**Resolution is iterative collective (relational) entity resolution, not single-pass.** A
**high-precision bootstrap pass** (shared ID / exact-strong attribute+name) seeds an initial partition,
then a **relational merge pass runs to a no-new-merge fixpoint** — it terminates because merges are
monotone, so a full pass that adds no auto-merge *is* the fixed point. This ordering is load-bearing:
the `0.40·relational` term below is *uncomputable* until some partition exists, which is exactly why the
bootstrap precedes the iterative pass.

`merge_score = 0.30·attribute + 0.40·relational + 0.15·temporal_consistency + 0.15·source_asserted`,
breakdown stored (same explainability principle). Bands: **auto-merge ≥ 0.85 · HITL 0.55–0.85 · keep
separate < 0.55** — defaults in config. **Max recall is the goal of candidate-generation, NOT of the
merge decision** — the merge decision is precision-first; recall is recovered by iteration + the HITL
band. The honest design statement: thresholds are *chosen so the planted traps land in the middle band*
(FD-2000/FT-2000: high attribute similarity, conflicting relational evidence ⇒ mid-band ⇒ analyst
queue). That's test design, and we say so.
Transliteration: rule-based normalizer + alias table seeded from `../md/05-data-scoping-C.md` §4;
the LLM may *propose* candidates (raise-only, and never a relational score — see §3.11) but its proposal
is just one signal, never an auto-merge.
Blocking keys (type + country/domain namespace + name token): implement as config for the design
note's scale story; at demo scale all-pairs-within-type is fine.

### 3.10 HITL control points — the full set, phased

`spine/05` enumerates **eight** control points and its architectural claim is that they are *the same
adjudication service with different payloads* (`enqueue(item, context, options, writeback) → decision
→ mutate view + emit trace`). That claim is only credible if the full set is named and the demo scope
is explicit — so here is the complete list with a **build-now vs. wired-later** split. All eight exist
in the service from day one; we *surface* three deeply for the demo and leave the rest as
config/roadmap. Nothing here is new architecture — it's the same enqueue call with a different payload,
which is exactly the point to make on the call.

| # | Control point | Payload / decision | Demo status |
|---|---|---|---|
| 1 | Credibility configuration | analyst sets resolver factors/weights (Module 1, §3.4) | **read-only panel now** (levers visible; §5); full editing later |
| 2 | **Merge adjudication** ★ | sub-threshold `same-as`/`distinct-from`: accept / reject / split | **BUILD NOW** — C's marquee (FD-2000 ≠ FT-2000) |
| 3 | Ontology extension | extraction proposes a new type/edge: add / map-to-existing / discard | later (roadmap) |
| 4 | **Confirmed↔probable override** ★ | promote / demote / reject an assertion; propagates on rebuild | **BUILD NOW** |
| 5 | Observable definition | analyst declares a tripwire condition | later (config-authored for the demo, not a UI) |
| 6 | **Alert disposition** ★ | fired tripwire: real / noise / needs-more → feeds tuning | **BUILD NOW** |
| 7 | Assessment review | final cited assessment accepted / annotated before it's "intelligence" | later |
| 8 | Integrity-flag disposition | M4 signal fired: discount / dismiss | later (auto-applied in the demo; surfaced in the drawer) |

The three ★ (merge, override, alert disposition) are the ones wired to a **real review-queue UI** so
propagation is *visible on screen* (§4, `05`). The other five are stated as "same service, deferred" —
which is itself the range/portability flex: *the architecture already accommodates all eight; the demo
proves the pattern on three.* This is a "four more weeks is mostly specification, not code" argument.

### 3.11 LLM usage — the invariant, proposer-vs-authority, selective invocation

**The invariant: no LLM call ever runs inside `rebuild()`** — and this holds even though extraction is now
**live at ingest** (`09`): the LLM runs *upstream* of the append, and once its output is appended it is a
**frozen, cited, versioned record** in the evidence or decision log; `rebuild()` then consumes those
records with deterministic arithmetic. *The LLM **proposes** into the log; deterministic rules **dispose**
in the rebuild.* Consequences: the view is deterministic given (log, config); traceability via `claim_ids`
+ model/version stamped on each record; and — since Opus 4.8 has no temperature to pin — determinism is a
*free property of the frozen log*, **de-prioritised as a constraint** (it never cuts capability; the
live-ingestion lane is fresh by design — §1 property 5). The QnA agent is a **bounded ReAct tool-calling
loop over the ~7 read-only `graph_*` tools** under a hop/iteration budget with an entailment citation
validator (full design in `09-retrieval-and-tools.md`); the recorded hero-trace is the network-safety
fallback, not the only path.

| Point | LLM as PROPOSER (once, logged, cited) | Deterministic AUTHORITY (in `rebuild()`) |
|---|---|---|
| Merge | candidate pairs (recall), alias/normalizer rules, cited explanations | `merge_score` + bands, clustering, the fixpoint (§3.9) |
| Escalate | **raise** into the HITL queue, rank it, apply the NL triage rubric, context cards | escalate-vs-auto gate, any **removal** from review, the thresholds |
| Assert | soft "too-clean" flags (downward-only), assessment annotations for the human | Confidence Resolver, status machine, independence grouping (§3.5), structural deception detectors, `on_fail → insufficient` |

**Red-team patches (mandatory):**

- **Raise-only merge signal.** The LLM merge signal may lift a weak pair *into* the HITL band, but
  **auto-merge (≥ 0.85) must be reachable by the deterministic terms alone** — the LLM can never push a
  trap pair across 0.85. The candidate proposer traverses only the evidence-layer claim graph + the
  previous frozen view (not the in-progress rebuild) and **emits no relational score** (relational is the
  fixpoint's job, §3.9).
- **Structural deception is deterministic.** Image/perceptual hash, coordinated timestamps,
  aggregator / `primary_origin_id`, `first_seen` are **deterministic detectors, never LLM-proposed** (§3.5).
  The LLM keeps only the soft "too-clean" narrative, **downward-only**. **Fail-closed**: a group counts as
  independent only when metadata affirmatively establishes it — absence of an LLM flag ≠ clean.
- **Insufficient / missing-evidence statements are deterministic templates.** The refusal statement is a
  fill-in-the-blank template keyed off the sufficiency-template gap (§3.7); explanations are templated
  sentences keyed off the gate vector; **regenerate-prose-as-presentation is CUT** — only frozen, validated
  prose is displayed. The citation validator checks existence **and entailment** — the cited claim must
  support/entail the statement, not merely exist (`09`).
- **Adversary-denial + single-pass decoy_risk are gates, not multipliers** (§3.4/§3.5).

**Selective invocation** (so the LLM earns its place without O(n²) build cost — it runs offline, so the
cost is build tokens + candidate noise, both gated by a deterministic pre-filter):

- **Candidate-gen:** fire the LLM only on entities that are **(i)** a high-alias-risk type
  (variant / component / unit / manufacturer, per config) **and (ii)** orphan / thin-block
  (`deterministic_candidate_count < k`). One batched call per orphan over its block; cap by config budget;
  log skips. Cost ≈ #orphan-risky-entities, not O(n²).
- **Raise-from-reject:** only pairs in a near-miss band just below the keep-separate cutoff **and** touching
  materiality (chokepoint) or novelty (unseen entity/alias). Raise-only.
- **Demo scope:** deterministic blocking + the seeded alias table cover the *known* traps; we demonstrate
  the LLM candidate-gen on **one planted alias not in the seeded table** (an orphan component) → the
  adaptation / recall story. Everything beyond that one instance is design-note.

**Analyst-initiated integrity flag (new).** Today HITL is system-triggered; add an analyst-initiated flag
path — a caller of the same adjudication service (§3.10 control point 8). Flagging a source/origin fake
propagates automatically: because dedup is by `primary_origin_id`, all echoes of that origin are already
one group, so the gate/penalty applies to every co-referring claim on the next `rebuild()`.

---

## 4. Open-question resolutions, per spine doc

| Doc | Open question | Verdict |
|---|---|---|
| 01 | Store choice | SQLite logs + NetworkX view, rebuilt (§1); graph DB is the scale path |
| 01 | Where confidence lives | Per-claim at ingest; per-assertion inside `rebuild()` (§1, §3.4) |
| 01 | Immutability vs correction | Append-only; retraction is a claim kind (§1) |
| 02 | Extraction method | **LLM-only, live at ingest (not frozen-only)** — everything via LLM function-calling → the one claim schema (structured + prose alike); Gemini optional 2nd provider; VLM → observation claims for imagery if real assets are added. A **seeded baseline** of pre-extracted claims ships (keyless boot + reproducible graded beats), but **live ingestion is always available** (`make ingest` / UI → extract → append → `rebuild()`). No per-source parser engineering (time-gated demo, `02`). **Extract-raw guardrail:** extracts *stated* claims — incl. any alias/`same-as` a source explicitly asserts (→ feeds `source_asserted`, §3.9) — but never resolves/normalizes the unstated. LLM runs upstream of the append, so the LLM-free-`rebuild()` invariant holds. Deterministic source-typed parsers = production/roadmap |
| 02 | Extraction aggressiveness | Extract all ontology-typed mentions at demo scale; cost-tiering stays a scale note |
| 02 | Claim dedup | One claim + multi-span within a doc; separate claims across docs (§3.1) |
| 03 | Blocking | Config-defined keys, exercised in the design note, not needed at demo n (§3.9) |
| 03 | Thresholds | 0.85 / 0.55, config; traps engineered into the middle band (§3.9) |
| 03 | Merge representation | Reversible same-as log entries; view collapses (§1) |
| 03 | Transliteration | Rule-based normalizer + seeded alias table; no learned model (§3.9) |
| 04 | Score combination | Weighted algebra + noisy-OR over independence groups; breakdown stored (§3.4) |
| 04 | Half-life values | Defaults table (§3.6), analyst-configurable |
| 04 | Confirmed/probable thresholds | Status machine: template AND ≥2 independent groups AND `assertion_confidence` ≥ 0.80 AND fresh; plus first-class insufficient→Known Gap (§3.4) |
| 04 | Independence definition | **Three axes** (origin / discipline / interest), per the C research; aggregator-inheritance + aligned-interest = false corroboration; provenance groups; 0.5 same-class weight (§3.5) |
| 05 | UI surface | **Minimal real review queue** for the ★ three (merge, status override, alert disposition) — propagation must be *visibly* demonstrable; scripted steps can't show the answer changing |
| 05 | Trace schema | §3.2 — one schema for HITL, learning loop, audit |
| 05 | Control-point scope | All **8** in the service; **3 wired deep** for the demo, 5 config/roadmap — full phasing in §3.10 |
| 05 | Batching | Group-by-entity in the queue UI if trivial; otherwise defer |
| 06 | Demo learning mechanism | Alias table confirmed — it's *derived state* from merge adjudications, so "same pair auto-resolves next time" falls out of replay; one screen shows the loop closing |
| 06 | Online-ness | Mechanism + one closed instance; genuine online learning out of scope |
| 06 | Trace sink | The two SQLite logs; Braintrust/LangSmith stays deferred |
| 07 | Which observable | **LOCKED (C/02 Q1):** the HQ-9B Rawalpindi→Rahwali occupancy state-change (supersedes + decoy cap + ≥2-independent gate + freshness decay in one beat); secondary tender/`replenishes` observables config-only (§3.8) |
| 07 | Agent framework | **Bounded ReAct tool-calling loop, no framework** — full design in `09-retrieval-and-tools.md`. ~7 namespaced `graph_*` tools (`find_entity`, `get_node`, `neighbors`, `find_paths`, `query_graph`, `get_evidence`, `check_sufficiency`) + **materiality precomputed in `rebuild()`**; bounds (hop≤4, top-k≈3, sufficiency-termination); no `temperature` (400 on Opus 4.8). Plus an **entailment-based citation validator**: every claim ID must exist *and* support/entail its hop — "no naked assertions" enforced mechanically. GraphRAG / vector RAG / free-form Text2Cypher rejected (`md/14`) |
| 07 | Map stack | Leaflet + **vendored tiles** (zero live-network dependency); explicitly ungraded (`md/07-stack.md`) |
| 07 | Observed-vs-inferred rendering | Structural, via claim `kind` (pre-wiring #3): answers group citations by observation vs inference; UI badges from the same field |

---

## 5. Config surface & module map (the portability proof)

Everything a new use case or subject touches is **config**; the planning-notes commitment ("extending
= writing each module's specification") made concrete:

```
config/
  ontology.yaml      # node/edge/event types (schema designed; instances discovered)
  sources.yaml       # source registry: class, reliability_grade, cadence, parser binding,
                     #   bias_vector + aggregator_of/primary_origin_id (independence, §3.5)
  credibility.yaml   # resolver factor rubric + weights (§3.4), integrity penalties, thresholds, half-lives
  templates.yaml     # evidence-requirement templates per assertion type
  subjects.yaml      # lenses: anchors, hop/materiality rules, target queries
  observables.yaml   # declarative tripwires (§3.8)
```

```
corpus/    frozen docs (+ scenario manifest: which graded scenario each doc seeds)
ingest/    LLM extractors → claims, LIVE at ingest (VLM for imagery; parsers = roadmap)
store/     evidence log + decision log + live config store (SQLite)
view/      rebuild(): resolution → credibility → status → materiality → NetworkX + JSON export
resolve/   candidate gen + scoring + banding
hitl/      adjudication service + review queue UI + writeback
observe/   observable evaluator over view deltas → alerts (post-rebuild)
agent/     bounded ReAct tool-loop (~7 graph_* tools) + entailment citation validator (09)
viz/       map (confidence-coded) + graph explorer (click-through to provenance) + queue
```

The **spine gate** test (from `00-overview.md`) maps to: re-point the system by editing
`subjects.yaml` + `observables.yaml` + dropping new docs in `corpus/` — no code changes.

**Frontend + hosting — DECIDED (`../md/07-stack.md`, `DECISIONS.md`):** Python backend — FastAPI (single
process) serving the rebuilt view as JSON + the HITL writeback endpoints + a **live ingest endpoint** +
the Ask agent (tooling in `tools/` is already Python). Frontend — one React/Vite SPA (Tailwind/shadcn):
Leaflet map (vendored tiles, confidence-coded pins), Cytoscape.js graph explorer (click-through to
provenance), review queue, ingest + observable-definition panels. Packaged as **one multi-stage Docker
image** (FastAPI serves the built SPA same-origin) and hosted on **one always-on EC2 + Cloudflare Tunnel**;
reviewers run the same image **both** ways (prebuilt GHCR image, or `git clone && make run`). Secret:
`ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) via `.env`. All swappable — nothing upstream depends on
these choices.

---

## 6. Where the new decisions break at scale (design-note additions)

- **Full rebuild is O(corpus)** — fine at demo scale, becomes incremental materialization at volume
  (standard event-sourcing evolution; the logs don't change, only the view engine).
- **NetworkX is in-memory** — ~10⁶ edges is the practical ceiling; migration path is a property-graph
  DB behind the same view interface.
- Existing scale notes stand: resolution blocking, cost-tiered extraction, namespacing.

---

## 7. To discuss on return (ratify / veto)

> This memo now **reconciles with the research-backed C docs** (`C/01`, `C/02`), which advanced while
> it was drafted. The Confidence Resolver naming, three-axis independence (§3.5), supersedes-vs-
> contradicts (§1), first-class Known Gap (§3.7), and the locked relocation observable (§3.8) all come
> *from* that C work — they strengthen the memo, they don't conflict with it.

1. **SQLite + NetworkX + rebuild-on-change** (§1) — the memo's central call. Veto = pick Kùzu/Neo4j
   now; cost is setup friction against "code we can run."
2. **Noisy-OR over three-axis independence groups + the 0.80/0.50 gates** (§3.4–3.5) — sanity-check the
   arithmetic story; alternatives (capped sum, rule table) are drop-in since the form is config-side.
3. **Half-life defaults** (§3.6) — the values, not the mechanism.
4. **Real minimal HITL queue UI for the ★ 3 of 8 control points** (§3.10, §4/05) — small frontend
   cost; I judged propagation-on-screen worth it. Veto = scripted CLI adjudication step.
5. **Demo observable = the Rawalpindi→Rahwali relocation** (§3.8) — now locked in C/02; confirm you're
   happy leading the demo with the richer state-change beat (it does a lot at once) vs. a simpler flip.
6. **Events as first-class for C now** (§2.2 #1) — I say fully commit; the alternative (edges only,
   events later) is the one retrofit that would genuinely hurt B.
7. **Credibility = factor rubric, not fiat R table** (§3.4) — ratify change #1; dynamic per-source
   rating stays roadmap but flagged as a cheap next-if-time bolt-on.
8. **Which research tasks to fan out** — materiality/tradecraft is **done** (folded into `C/01`);
   remaining: counter-deception patterns (feeds `06`), ICD-203 band wording verification (feeds §3.4),
   and the C-side deep-tier-supplier hunt (the `C/00` Q5 residual — your effort-vs-value call). None
   block the build start.
