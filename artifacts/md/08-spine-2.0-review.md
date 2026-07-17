# Spine 2.0 — review notes (working capture, 2026-07-16)

**Purpose.** Verbatim capture + itemized breakdown of Pragalbh's walk-through of `spine/01–04` (the
"scoping-spine-2.0" session). This is a *working aid* to drive the eventual spine-doc + data-scoping-doc
updates — nothing here is ratified. Tags: **[DECISION]** made · **[Q]** question to answer/explain ·
**[PROPOSAL]** design idea to evaluate · **[TBD]** deferred. Each item should be checked off against the
doc edit that lands it.

---

## 0. Verbatim (do not paraphrase; source of truth for this review)

> So far my understanding of the system is that: There are some Information sources, there is an editable
> schema, there is an ingestion pipeline that is connected to the schema, which creates one layer of the
> graph, then there is a configurable algorithm which is responsible for creating the disambiguated graph
> with confidence etc and also takes in user defined rules/ logics/ reasoning rubrics for various entity
> types and relationships: this is important since this is also the layer which makes the graph usable
> across problem statements: the specific logic of those problem statements can be encoded in the algo
> like : how to distinguish if 2 missile systems are same or not. I feel this layer has to have a higher
> layer of abstraction of figuring this out which is then driven by the configuration like: maybe a
> attribute layer of soft filters which connect ambiguity and then attribute logics that make these
> connections stronger or weaker and then finally rubric logic which is driven by an llm to finally based
> on all information, connections and attributes finalizes confidence etc. And this also plugs in to HITL.
> Then each problem statement basically becomes a combination of graph propagation/ structure detection/
> GraphRAG, decision making rubric on top of this graph like: chokepoints detection, correlated surge
> indicators, maybe some sort of processing algorithms too like baseline detection unless they can also be
> encoded as graph algorithms and then there are endpoints which encode and expose logic for various
> outputs from these problem statements like GIS displayable picture/ ORBAT. "The abstraction rules that
> keep the spine portable": I feel the act of encoding the logic of the problem statement as a algorithm
> over this graph is also a abstraction rule that keeps the spine portable no?. The subject: It certainly
> is a query parameter but ig we need to be specific for whom, i think it is a query parameter to the layer
> of algorithms over the data that each problem statement encodes.
>
> || Doc: spine/01-* : Ontology : Extension: This extension methodology should also be configurable and
> strict like llm shouldn't just suggest random shit, the analyst should be able to define a rubric for it
> and it should strictly be gated to be triggered on necessity because this is like a thing that can flood
> analyst for not on deadline work.; Open Questions: Store choice: we need to decide based on 1: what will
> be able to support the algorithms that we wanna work with given the problem statements, can it support
> the algorithms of all 3? 2: then the stated points as mentioned in the doc. and we will not be using
> 10-15 docs, that will not be able to cover all the scenarios we are thinking of capturing to capture
> depth for a problem statement: we will be using ig 100 or more docs just for problem C, and this is a
> separate problem statement : figuring out how many docs are needed to make it demoable and not make the
> end result/UI-UX too noisy, (we will also figure this out algorithmically in this discussion, note if not
> noted (tbd later)). "Where confidence lives ": yeah seems like a second layer thing, recompute should be
> triggered in case there is any change in the factors of the confidence formula which are basically change
> in attributes/edges, HITL additions, although we can ig for now make it a cron + HITL triggered in
> affected area? like we just need to display the thought and capability and make the design note for
> further addition. Claim immutability vs correction: sure whatever. Also various documents will list
> various mentions of the same entity/events so cross doc disambiguation and edge creation etc is also
> involved in graph algo not just within doc, which seems obvious ig.
>
> || Doc: spine/02* : Relevance is encoded at three layers : sure if credibility includes the whole
> configurable algorithm of resolving a node/relation and connecting with aliases and HITL (as i stated
> earlier in my broader understanding of the system). Extraction model & method : everything via llm, no
> need for extra effort for per source thing since this is a time gated demo not optimisation exercise. How
> aggressive is typed extraction at the edges: yeah if it an optimisation problem obviously later. Claim
> de-duplication : yeah 1 claim and ig 1 provenance span too since the doc is a singular unit ig. and also
> what is provenance span. Also we need a location standardization system like nominatim + llm. we need to
> create base level extraction objects for dates, location etc. which will be reused everywhere. will use
> pydantic.
>
> || Doc spine/03*: yeah all these sound fine although a rubric logic defined by analyst can only be taken
> care with an llm. so that needs to be added in this too. Open Questions: "Blocking / candidate
> generation ": soft filter of similarities, based on name, attributes, basically encode the initial search
> that any analyst would do in a corpus/database right: this might depend on entity type and will also be
> configurable, we will configure a few things as we feel suitable for use cases we face in problem C and
> progressively instead of exploratory in this. Threshold values : pick anything reasoning and sample and
> evaluate and tune once everything is configured and running e2e. Merge representation: yeah sure same as
> feels alright. Transliteration handling : figure it out.
>
> || Doc 4: Credibility = a tunable function of user-defined factors (Module 1): First I wanna clearly know
> the difference in claim and entities, is claim a relation? the claim corroboration is happening post
> entity merging right? Credibility and Corroboration: I feel maintaining a totally score based system
> requires a lot of maintenance and can only work as heuristics are discovered and added over time and is
> also very susceptible to data skewness. There might be some qualitative or rubric knowledge that the
> associates might use for such things that updates over time with their knowledge and view of the world,
> situations, SO I think over the scores should sit an llm call with those rubrics and later extendible to
> even use tools or query the graph further if the rubric requires, this way it is easy to keep it updated
> and maintained and usable. the axis part i am aligned with actually one rubric axis i just recalled is
> also like if 2 parties have no common incentive then that will also be able to refute the possibility of
> fakeness. Also we need to make sure that data insufficiency and data sparsity are not like interlinked,
> there can be a strong claim with just 3 strong corroborations and one less strong with 5 corroborations.
> this is important to make sure the actual intelligence is not dropped and we don't just alert on very
> obvious things, tuning HITL between these 2 is also a careful consideration. ..... lets talk on this and
> then update the spine docs, data scoping doc(with whatever could be beneficial knowledge for that flow.
> making sure we don't exactly bias it. messiness should be maintained. ) Supersedes vs. contradicts: yeah
> makes sense. Insufficient-evidence via evidence-requirement templates: sure makes sense, again if LLM is
> needed we should use certainly. Module 4 (manipulated / AI-generated media / misinformation): There is
> one more thing: let's say an analyst did notice that a post is bullshit in their own time and flagged it
> for the system (currently we do not have any way of doing this(since hitl is triggered by system) and
> thats alright), but we can probably then make all claims that resolve to this claim also be made fake.
> For future extension maybe we can think of some sort of social media specific algo of comment section,
> account authenticity, april fools day etc trips. Oh i see in scoring Integrity part this strategy is
> actually stated in reverse, interesting, help me understand. per indicator base: it is basically per
> source claim score right? the source reliability * the credibility score of the claim? The framing in the
> initial part of the doc is a bit confusing since it states corroboration as a subtopic of credibility and
> then as a separate topic and then as a separate score, which it is ig, we have per claim credibility and
> then ig corroboration is separate, make that clear whatever it is. and since scoring is conflicting in
> various places, explain to be intuitively what each one is and then i will decide which to take. lets work
> on this much and then we will proceed with other docs. also make sure you address all pointers and not
> miss anything, if required you can first note these somewhere verbatim to like later verify

---

## 1. Broader system model (Pragalbh's framing)

- **[PROPOSAL] Layered pipeline.** sources → editable schema → schema-connected ingestion → *evidence
  layer*; then a **configurable algorithm** builds the disambiguated *knowledge layer* with confidence,
  taking analyst-defined rules/rubrics per entity/relationship type. This algorithm layer is "what makes
  the graph usable across problem statements" (e.g. "are these 2 missile systems the same" is encoded here).
- **[PROPOSAL] 3-tier resolution/credibility abstraction inside that layer:**
  1. attribute **soft filters** that surface ambiguity / candidate links,
  2. attribute **logics** that strengthen/weaken those links,
  3. **LLM rubric** layer that, given all info + links + attributes, *finalizes confidence*.
  All config-driven; plugs into HITL.
- **[PROPOSAL] Problem statement = graph propagation / structure detection / GraphRAG + a decision rubric
  over the graph** (chokepoint detection, correlated surge indicators) + optional processing algos
  (baseline detection, unless encodable as graph algos) + **output endpoints** (GIS picture, ORBAT).
- **[Q/PROPOSAL] Is "encode the problem-statement logic as an algorithm over the graph" itself a 4th
  portability abstraction rule?** → evaluate (rule vs application layer).
- **[PROPOSAL] Subject-as-lens refinement:** subject is a query parameter *to the algorithm layer that each
  problem statement encodes* — "for whom" the parameter is.

## 2. spine/01 — graph & ontology

- **[DECISION/PROPOSAL] Ontology extension must be configurable + strict.** LLM must not "suggest random
  shit"; analyst defines a rubric for extension; extension is **gated to trigger only on necessity**
  (guard against flooding the analyst with non-deadline work).
- **[DECISION] Store choice criteria:** (1) can it support the *algorithms* we want for the problem
  statements — for **all 3** (A/B/C)? then (2) the points already in the doc.
- **[DECISION ✔ resolved 2026-07-16] Corpus size ≠ 10–15 docs → target ~40–50** (S≈20 signal, N≈20–30
  chaff; assessed view ~15–30 entities via the relevance funnel). Chosen *above* the computed ~24 floor for
  richer triage realism. Full logic + the coverage×noise-ratio method: `09-corpus-sizing.md`.
  **Consequence:** the subject-proximity view-time filter becomes a **required** build item (legibility at
  this count depends on it). Build the ~24 core (batch 1) first; add the chaff depth layer as batch 2.
- **[DECISION] "Where confidence lives" = second layer.** Recompute triggered by any change in confidence
  factors (attribute/edge changes, HITL additions). For now: **cron + HITL-triggered recompute in the
  affected area**. Just display the capability + design-note the fuller version.
- **[DECISION] Claim immutability vs correction:** accept doc's leaning ("sure whatever").
- **[DECISION] Cross-doc resolution is in scope of the graph algo** (mentions of the same entity/event
  across docs → cross-doc disambiguation + edge creation), not just within-doc.

## 3. spine/02 — ingestion & unit

- **[DECISION] 3 relevance layers: OK** — *iff* "credibility" here means the whole configurable
  resolution+alias+HITL algorithm (per §1 framing).
- **[DECISION] Extraction = everything via LLM.** No per-source-type engineering (time-gated demo, not an
  optimisation exercise).
- **[DECISION] Typed-extraction aggressiveness at edges → later** (optimisation problem).
- **[DECISION] Claim de-dup = 1 claim + 1 provenance span** (doc is a singular unit). **[Q] What is a
  "provenance span"?** → explain.
- **[DECISION] Add a location-standardisation system** (Nominatim + LLM).
- **[DECISION] Build reusable base extraction objects** for dates, locations, etc.; **Pydantic**.

## 4. spine/03 — resolution

- **[DECISION] Broadly OK**, but **analyst-defined rubric logic ⇒ needs an LLM** — add that here too.
- **[DECISION] Blocking / candidate generation = attribute/name soft-filter** ("encode the initial search
  an analyst would run over a corpus/DB"); **entity-type-dependent + configurable**; configure a few cases
  suitable for problem C **progressively (not exploratory)**.
- **[DECISION] Thresholds:** pick reasonable defaults, then sample/evaluate/tune once e2e is running.
- **[DECISION] Merge representation:** accept doc's leaning.
- **[TBD] Transliteration handling:** "figure it out."

## 5. spine/04 — credibility (main focus this turn)

### Questions to answer/explain this turn
- **[Q] Claim vs entity.** Is a claim a relation? Is claim **corroboration post-merge** (after entity
  resolution)?
- **[Q] "Integrity stated in reverse."** Explain the integrity scoring direction/logic (the reviewer
  noticed the M4 propagate-fake idea appears mirrored in the integrity scoring).
- **[Q] Per-indicator base = per-source claim score?** i.e. `source_reliability × claim_credibility`?
- **[Q] Corroboration framing is inconsistent** (subtopic of credibility → separate topic → separate
  score). Make it clear: per-claim credibility vs corroboration are distinct. **Explain each scoring
  construct intuitively** (04 vs 08 conflict) so Pragalbh can pick which to take.

### Proposals / decisions
- **[PROPOSAL] LLM-rubric over the numeric scores.** Rationale: pure score system is high-maintenance,
  only improves as heuristics are hand-added, susceptible to data skewness. Put an **LLM call with
  analyst rubrics over the scores** to finalize confidence; later extendible to let the LLM **use tools /
  query the graph** if the rubric requires. → evaluate against non-negotiables (fabrication ban,
  traceability, confirmed/probable separation, determinism).
- **[PROPOSAL] Extra rubric axis:** *no common incentive between two parties ⇒ refutes fakeness.*
- **[DECISION/constraint] Insufficiency ≠ sparsity.** A strong claim with 3 strong corroborations can beat
  a weak one with 5 — corroboration must be **quality/independence-weighted, not counted**; don't drop real
  intelligence; don't only alert on the obvious. **HITL tuning between these two is a careful
  consideration.**
- **[DECISION] Supersedes vs contradicts: OK.**
- **[DECISION] Insufficient-evidence via evidence-requirement templates: OK**; use LLM where needed.
- **[PROPOSAL/DECISION] Analyst-initiated integrity flag.** Today HITL is system-triggered only (accepted).
  Add: an analyst can **flag a post as fake on their own**, and the system **propagates "fake" to all
  claims that resolve to it.**
- **[TBD/future] Social-media-specific integrity algo** (comment section, account authenticity,
  April-fools trips) — roadmap.
- **[DECISION] When updating docs:** also feed **beneficial knowledge into the data-scoping doc for this
  flow — without biasing the generator; keep the messiness.**

---

## 6. Cross-cutting to resolve this session
- Reconcile the **04↔08 scoring conflict** into ONE canonical, intuitive definition (per-claim credibility
  · corroboration/aggregation · integrity · freshness · status gates) — then Pragalbh picks.
- Decide the **LLM-over-scores** bounded design (guardrails vs non-negotiables).
- **✔ resolved: corpus target ~40–50** (see `09-corpus-sizing.md`); the coverage×noise-ratio method
  answered "how many, algorithmically." Promotes the proximity-lens filter to a required build stage.
- Store choice gated on **algorithm support across A/B/C**.

---

# PART 2 — RESOLVED CANONICAL DESIGN (2026-07-17)

**Status: ratified in discussion; this section is the single source of truth the spine/C docs are reconciled
to.** Where a spine doc and this section disagree, this section wins (then fix the doc). Written after the
grounding + adversarial workflows; incorporates the red-team patches.

## A. Vocabulary (lock; use these exact words everywhere)

| Term | Lives on | Answers |
|---|---|---|
| **claim** | evidence layer (append-only, immutable) | one raw sourced assertion `Source S, dated D, asserts <s,p,o>`. Asserts an entity attribute, a relationship/edge, **or** an event. Never merged, never edited. |
| **resolved claim** | the same claim + a `resolved_ref = {entity_id, edge_instance}` | the same single-source claim after resolution pins *which* real entity/edge its s/o point at. Still one claim. |
| **merge_confidence** | a `same-as` edge (knowledge layer) | IDENTITY — are node A and B the same entity? |
| **claim_credibility** (`c`; was `s_i`) | one resolved claim | how much do I trust *this one source's* assertion? |
| **assertion_confidence** (was `C_raw`/`eff`) | the resolved node/edge | TRUTH — pooling all independent claims sharing this `resolved_ref`, how sure it's real? |
| **status** | the resolved node/edge | label derived by the gate machine: confirmed / probable / possible / insufficient→Known Gap / stale |

Rename in all docs: `s_i` → `claim_credibility`; `C_raw` → `assertion_confidence`. State explicitly: **credibility
is per resolved-claim; confidence is per resolved-assertion (pooled).** The "credibility" used *inside
resolution* is the `source_asserted` term of `merge_score`, NOT `claim_credibility`.

## B. Resolution → corroboration pipeline (all inside `rebuild()` = pure fn of (evidence log, decision log, config))

Resolution is **iterative collective/relational entity resolution** (bootstrap → fixpoint), NOT single-pass.
Stages:

| # | Stage | Produces | Deterministic? |
|---|---|---|---|
| 0 | Normalize (transliteration + seeded alias table) | normalized keys | Yes (rule-based) |
| 1 | Blocking / candidate-gen (all-pairs-within-block at demo scale) | candidate pairs | Yes; **LLM proposes extra candidates only on the selective gate — see D** |
| 2 | High-precision merge pass (bootstrap: shared ID / exact-strong attr+name) | initial partition | Yes (auto-merge ≥0.85) |
| 3 | Iterative relational merge (collective ER → fixpoint) | clusters; mid-band→HITL; weak→separate | Yes given fixed order + replayed decisions. **ITERATIVE**; fixpoint = no new auto-merge in a full pass (terminates: merges are monotone) |
| 4 | `resolved_ref` assignment | co-referring claims share a resolved_ref | Yes |
| 5 | Per-resolved-claim credibility | `c` per claim | Yes (config rubric) |
| 6 | Assertion-corroboration (noisy-OR over independence groups) + supersede/contradict | `assertion_confidence` | Yes |
| 7 | Status gates + sufficiency templates | status | Yes |

- `merge_score = 0.30·attribute + 0.40·relational + 0.15·temporal_consistency + 0.15·source_asserted`; bands
  **≥0.85 auto · 0.55–0.85 HITL · <0.55 keep-separate**. The 0.40 relational term is uncomputable until the
  bootstrap pass exists — that's *why* stage 2 precedes stage 3.
- **Max recall is the goal of candidate-gen (stage 1), NOT the merge decision** — the merge decision is
  precision-first (FD-2000 ≠ FT-2000 lands in the HITL band). Recall recovered by iteration + HITL.
- **Two "corroborations", never conflated:** merge-corroboration (`source_asserted`, identity, inside
  resolution) vs assertion-corroboration (noisy-OR, truth, after resolution). **Claims are never merged;
  only entities merge.** Co-reference via `resolved_ref` is what corroboration counts.
- **Two scores, two objects, never averaged:** `merge_confidence` (identity, on same-as edge) vs
  `claim_credibility`/`assertion_confidence` (truth, on resolved node/edge).

## C. Scoring (canonical — 08 factor-rubric base + 04 insufficient state; supersedes both docs' numbers)

**Per resolved claim:** `claim_credibility (c) = R(source) × Π(integrity) × freshness`
- **extraction/model_conf = 1.0 for the demo** (everything LLM-extracted; seam kept for real per-claim
  extraction confidence later — design-note it). No `model_conf` term active now.
- `R(source) = Σ_f w_f · factor_f`, analyst-tunable factors: **authority, process, directness, track_record,
  + intrinsic_plausibility**. `intrinsic_plausibility` = believability of the claim *on its face*, independent
  of source and corroboration (world-knowledge prior; the old `w_C` axis) — folded in as a rubric factor, the
  one axis where an LLM *downward* sanity prior is legitimate. Illustrative R outputs (tunable, CALIBRATE on
  frozen corpus): SIPRI 0.85 · official 0.75 · think-tank 0.65 · customs/tender 0.60 · named-social 0.35 ·
  anon-social 0.25.
- `Π(integrity)` = artifact_integrity{unaltered 1.0/unverifiable 0.85/edited 0.30/synthetic 0.10} ×
  first_seen{recycled 0.30/else 1.0} × caption{consistent 1.0/uncheckable 0.9/mismatched 0.30} ×
  coordinated_inauthenticity{independent 1.0/suspected 0.5/too-clean 0.4}. **Structural signals (image/
  perceptual hash, coordinated timestamps, aggregator/primary_origin_id, first_seen) are DETERMINISTIC
  detectors — never LLM-proposed. Only the soft "too-clean" narrative may be LLM-proposed, downward-only.**
- **adversary_denial = GATE (exclude the claim from grouping), NOT a multiplier.** single-pass `decoy_risk` =
  GATE (cap at probable). (Fixes 08, which wrongly bundled adversary_denial into the multiplier.)
- freshness `= 2^(−age/half_life[edge])` on `event_time`; per-edge half-lives — **coarse defaults now,
  calibrate later**; durable edges (manufactures/variant-of/imported-by) skip decay.

**Per resolved assertion:** group co-referring resolved claims into independence groups on 3 axes
(origin / discipline / interest; aggregator inherits upstream origins; same-class-but-passing = 0.5 weight;
adversary-denial excluded), then **`assertion_confidence = 1 − Π_g (1 − c_g)`**, `c_g` = max
`claim_credibility` in group g (echoes collapse → no fake corroboration). Noisy-OR = probabilistic OR under
independence.

**Status gates (structural, not one threshold):**
- **CONFIRMED** — sufficiency template satisfied AND ≥2 independent origin groups (discipline- AND
  interest-independent) AND `assertion_confidence ≥ 0.80` AND fresh AND no unresolved contradiction AND clean
  integrity/decoy AND gated attrs not UNKNOWN.
- **PROBABLE** — `0.50 ≤ assertion_confidence < 0.80`, OR template partially satisfied (single independent
  group), OR any integrity/decoy/adversary-denial flag caps here.
- **POSSIBLE** — assessable but low magnitude (`< 0.50`); a *lead*, never in the assessed picture.
- **INSUFFICIENT-EVIDENCE → Known Gap** — *assessability* fails (a required evidence **kind** is missing per
  the sufficiency template); **off the confidence scale** (a refusal, not "confidence≈0"); emits
  missing-slots + `next_coverage_due` + `observability_ceiling`. **This is the disqualifier-guard; keep it
  first-class in BOTH 04 and 08.** POSSIBLE (low magnitude) and INSUFFICIENT (assessability failure) are
  orthogonal axes — insufficiency ≠ sparsity.
- **CONTRADICTED** — credible opposing group within δ → HITL.
- **STALE overlay** — confirmed decays: → "**confirmed-as-of-DATE / coverage-lapsed**" (freshness annotation:
  still confirmed but coverage overdue) → once age > half-life, **demote one step to "probable (stale)"** (an
  actual label change). coverage-lapsed = the monitoring annotation; probable(stale) = the demoted label.
- Cutoffs unified at **0.50 / 0.80** (drop the stray 0.55). Fix 04's internal bugs: the non-monotonic w_C
  (grade6>grade5) disappears once intrinsic_plausibility is a rubric factor; delete the arithmetically-broken
  "(A–C AND 1–3, s_i≥0.50)" parenthetical.

## D. LLM usage (the invariant + proposer-vs-authority + selective invocation)

**Invariant:** *No LLM call ever runs inside `rebuild()`. Every LLM output is produced once, offline at
ingest/proposal time, and frozen as a cited, versioned record in the evidence or decision log; `rebuild()`
consumes those records with deterministic arithmetic. The LLM PROPOSES into the log; deterministic rules
DISPOSE in the rebuild.* → zero demo-path latency; determinism by frozen-replay (Opus 4.8 has no temperature);
traceability via `claim_ids`+model/version. Tool-use where added = the QnA read-only tools with a config hop
budget; transcript frozen.

| Point | LLM as PROPOSER (once, logged, cited) | Deterministic AUTHORITY (in `rebuild()`) |
|---|---|---|
| 1 Merge | candidate pairs (recall), alias/normalizer rules, cited explanations | `merge_score` + bands, clustering, the fixpoint |
| 2 Escalate | **raise** into HITL queue, rank it, apply NL triage rubric, context cards | escalate-vs-auto gate, any **removal** from review, thresholds |
| 3 Assert | soft "too-clean" flags (downward-only), assessment annotations for the human | Confidence Resolver, status machine, independence grouping, structural deception detectors, `on_fail→insufficient` |

**Red-team patches (mandatory):**
- (1a) LLM merge signal is **raise-only**: may lift a weak pair *into* the HITL band, but **auto-merge (≥0.85)
  must be reachable by the deterministic terms alone** — LLM can never push a trap pair across 0.85.
- (1b) candidate proposer traverses only the **evidence-layer claim graph + previous frozen view** (not the
  in-progress rebuild); it does **not** emit a relational score (relational is the fixpoint's job).
- (3a, top priority) **structural deception signals are deterministic detectors, not LLM** (hash/timestamp/
  aggregator/first-seen). LLM keeps only soft "too-clean," downward-only. Default **fail-closed**: a group
  counts as independent only when metadata affirmatively establishes it — absence of an LLM flag ≠ clean.
- (3b/3c) for the demo, the **insufficient/missing-evidence statement is a deterministic fill-in-the-blank
  template**; explanations are **templated sentences keyed off the gate vector**; **regenerate-prose-as-
  presentation is CUT** (only frozen validated prose displayed). Citation validator checks existence — not
  enough alone.
- (3d) adversary_denial + single-pass decoy_risk are **gates**, not multipliers (per C above).

**Selective invocation (so the LLM earns its place without O(n²) build cost — it's offline, so cost = build
tokens + candidate noise, both gated by a deterministic pre-filter):**
- **Candidate-gen:** fire the LLM only on entities that are **(i) a high-alias-risk type** (variant/component/
  unit/manufacturer, config) **and (ii) orphan/thin-block** (`deterministic_candidate_count < k`). One batched
  call per orphan over its block; cap by config budget; log skips. ≈ #orphan-risky-entities, not O(n²).
- **Raise-from-reject:** only pairs in a **near-miss band just below the keep-separate cutoff** AND touching
  **materiality (chokepoint) or novelty (unseen entity/alias)**. Raise-only.
- **Demo scope:** deterministic blocking + seeded alias table covers the *known* traps; demonstrate the LLM
  candidate-gen on **one planted alias not in the seeded table** (orphan component) → the adaptation/recall
  story. Everything beyond that one instance = design-note.

**Analyst-initiated integrity flag (new):** today HITL is system-triggered; add an analyst-initiated flag path
(a caller of the same adjudication service). Flagging a source/origin fake propagates automatically — because
dedup is by `primary_origin_id`, all echoes of that origin are already one group, so the gate/penalty applies
to every co-referring claim on the next `rebuild()`.

## E. Architecture

- Keep the **3 portability rules** (schema-flexible store; source-typed ingestion; subject = lens). Add a
  **"layer contract" corollary** (NOT a 4th rule): *because ingestion is source-typed and the subject is a
  lens, a use case = read-only graph analytics + a decision rubric + output adapters over the shared graph,
  adding no storage/ingestion.* Build the seam for C; confirm before generalizing to A/B.
- **Split resolution-confidence (`merge_confidence`) from claim-credibility/assertion-confidence** — two
  scores, two objects, never averaged. This is what lets us say "the node is real (resolved) but its basing is
  only probable (credibility)".
- **Subject-as-lens:** the subject supplies (a) anchor entities and (b) which configured pattern to run; the
  PS algorithm stays subject-generic (a subject is not its own database/algorithm).

## F. Data-gen implications for `05` (add to §5.2 handoff; non-biasing, keep messiness, generator stays blind)

- an **orphan/thin-block alias case**: a component reported under a differently-worded name NOT in the seeded
  alias table, so the LLM candidate-gen recall path can be demonstrated recovering it.
- a **deterministically-detectable deception cluster** (near-duplicate text + timestamp ordering — the reshare
  cluster) so structural M4 detection fires without an LLM and without narrating the verdict.
- an **adversary-denial case**: a claim denying a known dependency / asserting a fake second source, to
  exercise the discount gate.
  (Describe these as scenario *needs*, not prescribed content.)

## G. Per-doc edit map

- **spine/04** — full scoring reconcile: vocabulary (§A), canonical formulas (§C), insufficient+possible
  orthogonality, coverage-lapsed vs probable(stale), adversary-denial gate, fix internal bugs,
  extraction-conf=1.0 seam, two-corroborations framing; make 04 defer numbers to §C / 08 without self-contradiction.
- **spine/03** — iterative collective ER (bootstrap→fixpoint), precision-first merge / recall=candidate-gen,
  LLM candidate-gen selective gate (proposer-only; raise-only merge signal; no LLM relational score),
  two-scores-never-averaged, transliteration = rule-based + alias + LLM-propose-only, blocking configurable.
- **spine/08** — reconcile to §C: adversary-denial as gate; add INSUFFICIENT state alongside possible; state
  §3.9 resolution is iterative collective ER; **fix the "temperature-0" line → frozen-recorded-replay**; add
  the LLM-usage design (§D) + selective invocation; align vocabulary.
- **spine/05** — LLM raise-only triage (config rubric; raise + rank only; never remove; frozen/replayed
  ranking; recall≈1.0 held by the deterministic gate not by rank); analyst-initiated integrity-flag path
  (extend control point 8).
- **spine/01** — extension gating (configurable/strict/analyst-rubric/gated-on-necessity); confidence lives in
  layer 2 + recompute on factor change (rebuild pure fn; affected-area = optimization); cross-doc resolution;
  store criterion (support the algorithms for A/B/C); layer-contract corollary; subject-as-lens clarification.
- **spine/02** — extraction everything-via-LLM (no per-source engineering); define **provenance span** (1
  claim, ≥1 spans; across docs = separate claims); location standardization (Nominatim + LLM); reusable base
  extraction objects (dates/locations) via Pydantic; claim de-dup.
- **md/05-data-scoping-C** — add §F needs to the §5.2 handoff.
- **DECISIONS.md** — record every locked decision with the principle invoked + the alternative rejected.

## H. Extraction method — RESOLVED 2026-07-17: Option A (LLM-only + extract-raw guardrail)

**Extraction method: LLM-only vs hybrid-with-parsers.** In the `spine/02` discussion Pragalbh chose
"everything via LLM, no per-source effort" (build-effort reasoning). That collides with `spine/08` §4 and
`md/07-stack.md`, which both specify **hybrid** extraction (deterministic parsers for structured sources
SIPRI/customs/NOTAM/tender + LLM for prose + VLM for imagery) and lean on it for two things: (a) frozen
determinism and (b) a *parser-first anti-circularity / messiness-preservation* argument (a parser copies
the messy row verbatim; an LLM extractor might silently "un-mess" a front-company cover story inline — the
d05 problem from `06-preflight-audit.md` M-DATA-1). With extraction **frozen offline + `model_conf`=1.0
uniform + an "extract-raw, don't-resolve" LLM guardrail**, LLM-only is safe and determinism survives; the
only real loss is the "we deterministically parse structured feeds" defensibility line. **`spine/02` was
edited to LLM-only (per the decision); `07`/`08`/DECISIONS still say hybrid — left as-is pending the call.**
Options: **(A)** LLM-only + extract-raw guardrail → ripple to `07`/`08`/DECISIONS (recommended); **(B)**
keep hybrid parsers for the 2–3 structured source types → revert `spine/02`.

**DECIDED: Option A.** Refinement Pragalbh added: the guardrail is *stated-relationship-aware* — if a
document **states** an alias/`same-as`/equivalence relationship, the LLM **does** extract it as a sourced
claim (which then feeds `source_asserted` in resolution); the guardrail only withholds *unstated*
resolution (deciding identities the source doesn't assert, collapsing cover stories). Rippled to
`spine/02`, `md/07-stack.md`, `08` §4/§3.1/§5, and DECISIONS.md.
