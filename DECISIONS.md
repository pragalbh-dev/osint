# DECISIONS — Guidelines & Decisions Ledger

**What this is.** The single consolidated record of *how we work* (guiding principles), *what we've
decided* (locked-decisions ledger, with pointers to the detailed reasoning), and *what's still open*
(pulled from every design doc's "Open questions" tail). `CLAUDE.md` is the terse boot context; this is the
fuller reasoned index behind it.

**How to use it.** Read the principles once — they govern judgement calls. Keep ledger entries one-liners
with a `→ pointer`; the reasoning lives in the design docs, not here. *As of 2026-07-16. Deadline
20 Jul 2026, 12:00.*

**Decision process — how every decision is made & recorded:**
- **Note guideline-driven decisions as you go, and surface them at the end of the work** — not only buried
  in a commit. For each: the choice, the principle (§1) it invoked, the alternative rejected. At end of
  work, append them to the ledger (§2) and flag which design-doc tails to enrich, so the final design note
  can absorb them.
- **Borderline-harmful → ask first, with an options template.** If a decision could harm *any* aspect
  (correctness, credibility, demo-reliability, scope, timeline, reproducibility, extensibility), don't
  decide it yourself — put concrete options + tradeoffs to the user, never a bare open question. Unilateral
  calls are for the clearly-safe only.
- **Extensible by default; hardcode only with approval.** Architecture includes a configuration / framework
  layer for decision-making and HITL at *any* spine layer that needs it (the ontology is extensible; so are
  the reasoning frameworks, the credibility rubric, and observables). Anything that could extend to another
  use case (A/B) is built as an extensible seam rather than hardcoded to C — but confirm that extensibility
  choice with the user (options template) rather than assuming the abstraction; build the seam, not the
  other use cases' content.
- When you *close* an open question, move it up into the ledger.

---

## 1. Guiding principles (the "how we think")

These are the durable commitments. Almost every hard choice reduces to one of them.

1. **Credibility over collection.** Lead with how we know, not how much we gather. The graded work is
   resolution, credibility, and confidence discipline — *not* scraping. Collection is bounded on purpose.
2. **Depth over coverage.** One thread done to real depth beats three done shallowly. One good observable,
   one good visualisation, one worked query — each wired end-to-end and traceable.
3. **The product is judgement, not a dashboard.** The tool is *one input to the overall intelligence
   architecture* — decision-support with a human in the loop, never an autonomous oracle emitting finished
   intelligence.
4. **Never fabricate — "insufficient evidence" is a feature.** In evidence-sparse cases, say what's
   missing and when coverage is next due. This is the disqualifying line; treat it as sacred.
5. **Traceability by construction.** Every claim/node one-click back to its exact source. The bi-level
   graph makes this structural, not bolted-on. If a design choice would break traceability, it's wrong.
6. **Confirmed is not probable.** Epistemic honesty is structural: probable holdings never masquerade as
   confirmed; freshness lapses demote silently-aging "confirmed" nodes.
7. **Defensible, not clever.** Every choice must survive a sharp interviewer. Prefer transparent,
   explainable mechanisms (auditability > sophistication). Own the tradeoffs *out loud* — naming the
   synthetic-data limits is the senior move; hiding them reads junior.
8. **Build once, extend by specification.** The spine is built cleanly the first time so a second use case
   is mostly *specification* (which types/observables/queries), not core rework.
9. **Config-driven extensibility.** Analysts (not engineers) evolve the rules — credibility factors,
   thresholds, half-lives, observables, ontology extensions live in config / HITL, not buried in code.
10. **Model exactly what the target queries require, no richer.** The over-engineering trap. Every hour on
    provenance/confidence discipline beats an hour on ontology breadth.
11. **Reproducible where it matters; live where it counts.** The frozen baseline + tested queries run the
    same every time and the generator stays blind to the ontology (the pipeline earns its extractions); but
    determinism never cuts capability — the live-ingestion lane is fresh by design (that's what makes it
    *monitoring*), and a tight extraction prompt is "deterministic enough." (`spine/09`)

---

## 2. Locked decisions (ledger)

### Scope & framing
| Decision | Why (one line) | → |
|---|---|---|
| **Use case C** (ORBAT + supply-chain map), spine-first | Highest expected value: deliverable *is* the credibility mandate; hardest to dismiss as an LLM wrapper; auditable multi-hop; agent-proof design work | `md/04-claude-chat.md` Q1, `C/00` |
| **B built only if time allows**, as a reasoning layer over C's chokepoint signals; otherwise design-note only | B consumes C/A outputs; coherent two-step, never at C's expense; also the "four more weeks" answer | `spine/00`, `spine/06` roadmap |
| **Primary subject: HQ-9/P (Pakistan)**, enriched with China HQ-9; S-400 as design-note reference | One bounded traceable import (CN→PK); maximal alias messiness (C's marquee); English real sources; freshest reporting; best social stream | `md/05-data-scoping-C.md` §3, `C/00` |
| **Enrichment bound — LOCKED (Q5):** a China-side node is in-scope *iff* on a directed dependency/origin path reachable from a fielded PK HQ-9/P fire-unit, or a resolution anchor. Adds depth, never breadth | Bounds China-HQ-9 as depth not scope-creep; **residual open:** how aggressively to hunt/name tier-2/3 suppliers (effort-vs-value) | `C/00` |
| **Deliverable: hosted web app** + 2–3p design note + one worked query on call | Brief wants a running system, not slides; hosted raises the bar | brief, `md/01-assignment.md` |

### Architecture / spine
| Decision | Why | → |
|---|---|---|
| **One graph**; a subject is a query-time **lens**, not a partition | Matches "one organised corpus → one queryable graph"; C is this graph with C's ontology subset | `spine/01` |
| **Bi-level model**: append-only evidence layer + derived knowledge layer; node confidence = f(claims) | Makes traceability + confirmed/probable structural | `spine/01` |
| **Ontology: schema designed, instances discovered, extension human-gated** | Reproducible & defensible; avoids circular LLM-invents-schema; HITL proposes new types | `spine/01` |
| **Ingestion is source-typed, never use-case-typed** | A customs doc ingests identically regardless of consumer → one-graph, emergent relevance, extendible subjects | `spine/02` |
| **Unit of analysis = the sourced claim**, not the document/chunk | Matches source granularity; carries provenance; enables corroboration & traceability | `spine/02` |
| **Relevance encoded at 3 layers** (ontology-typing hard; subject-proximity soft; credibility soft) — **no hard ingestion relevance gate** | The shell company isn't visibly "about the subject" until resolution connects it; filtering at ingest deletes the signal | `spine/02` |
| **Resolution is relational/collective**, not string/embedding alone; shared-neighbourhood is the analyst signal | C's marquee; also must keep entities *apart* (FD-2000 ≠ FT-2000 false-merge) | `spine/03` |
| **Confidence bands with a HITL middle**: auto-merge / keep-separate / escalate | Ambiguous merges go to a human; decisions grow the alias table (learning) | `spine/03`, `spine/06` |
| **Credibility = "Confidence Resolver," a tunable function of user-defined factors**; source reliability is **derived from an analyst-set factor rubric** (authority · process · directness · track_record), never a fiat per-class number | Module 1 literally says "user-defined factors" — a rubric makes that true, a hardcoded tier table only looks configurable; STANAG A–F grounded | `spine/04`, `08` §3.4 |
| **Corroboration counts sources independent on *three axes*** (origin / discipline / interest); aggregator-inheritance + aligned-interest = false corroboration; adversary-denial discounted | Corroboration is gameable (plant one fake + two reshares; or two aligned-interest "sources"); the C research sharpened independence into the real deception surface | `spine/04`, `08` §3.5 |
| **Dynamic per-source rating** (track_record earns/loses reliability from confirmed/refuted history) = **roadmap, but a cheap next-if-time bolt-on** — seam pre-wired (factor + decision log) | Stronger "not hardcoded" answer; the brief only requires configurable factors, not auto-learning | `spine/06`, `08` §3.4 |
| **Freshness = per-edge-type half-life**; state machine confirmed → confirmed-as-of-DATE → probable(stale) | Facts perish at different rates; a node never silently stays "confirmed" | `spine/04` |
| **Insufficient-evidence via evidence-requirement templates** — the gap statement is *generated*, not written | Turns the non-negotiable into a checkable, configurable mechanism (highest-leverage pattern) | `spine/04` |
| **Module 4 = three orthogonal axes** (veracity / artifact integrity / contextual provenance) → one score; cheap penalty-signals, not a binary fake detector | "Credible attempt," not a solved deepfake detector; catches the recycled-photo case corroboration can't | `spine/04` |
| **Image trust is source-tiered**: satellite = high-provenance confirmation; social = low-provenance lead (never confirms alone) | Matches where misinformation concentrates | `spine/04` |
| **HITL is one cross-cutting adjudication service**; overrides mutate graph state (not just log); triage is recall-biased. **All 8 control points live in the service; 3 wired deep** (merge, confirmed↔probable override, alert disposition), 5 config/roadmap | Any stage calls the same `enqueue`; naming all 8 + phasing 3 is itself the range/portability flex ("four more weeks is mostly specification") | `spine/05`, `08` §3.10 |
| **Insufficient-evidence emits a first-class `Known Gap` node** (with `observability_ceiling`), not just a string → doubles as prioritized collection tasking; **supersedes vs. contradicts** is a rebuild rule (differ in valid_time → supersede→stale; same → contradict→HITL) | "What don't we know?" reads off nodes; keeps the relocation observable honest; distinguishes a fixable lapse from a permanently unobservable fact | `spine/04`, `C/01`, `08` §1/§3.7 |
| **Adaptation = freshness/coverage decay + a learning loop**; degrade visibly, never silently | What makes it *monitoring*; demo one mechanism (**alias table**), roadmap the rest | `spine/06` |
| **Trace: design the emit-interface now, defer the sink** (Braintrust/LangSmith later for eval-driven regression) | Append-only log + alias table + credibility store is enough to show the loop closing | `spine/06` |

### Spine 2.0 canonical design (2026-07-17 reconciliation)
| Decision | Why | → |
|---|---|---|
| **Canonical scoring form = 08's factor-rubric × noisy-OR corroboration** (rename `s_i`→`claim_credibility`, `C_raw`→`assertion_confidence`; unify cutoffs at **0.50/0.80**; `extraction/model_conf = 1.0` for the demo, seam kept for later per-claim extraction confidence) | Principle 9 (config-driven, analyst-tunable factors — Module 1) + principle 7 (defensible > clever): one transparent rubric beats maintaining two conflicting scoring constructs; **rejects** 04's separate two-axis `w_R × w_C` reliability/plausibility tables — `intrinsic_plausibility` is folded in as one rubric factor instead | `spine/04`, `08` §3.4, `08-spine-2.0-review.md` §A/§C |
| **INSUFFICIENT-EVIDENCE → Known Gap stays first-class and orthogonal to POSSIBLE** (assessability failure ≠ low magnitude; off the confidence scale entirely, not "confidence≈0") | Principle 4 (never fabricate — insufficient evidence is a feature, the disqualifying line) | **rejects** 08's draft collapsing insufficient into a "possible" confidence band | `spine/04`, `08-spine-2.0-review.md` §C |
| **Resolution is iterative collective/relational ER (bootstrap → fixpoint); the merge decision is precision-first — recall is recovered at candidate-gen (stage 1) + iteration + HITL, never by loosening the merge threshold** | Principle 2 (depth over coverage) + the false-merge discipline already locked for resolution (FD-2000 ≠ FT-2000 must stay apart) | **rejects** a recall-maximizing merge decision (auto-merging on weak signal to avoid missing pairs) | `spine/03`, `08-spine-2.0-review.md` §B |
| **Two scores, two objects, never averaged**: `merge_confidence` (identity, lives on the same-as edge) vs `claim_credibility`/`assertion_confidence` (truth, lives on the resolved node/edge) | Principle 6 (confirmed is not probable — structural separation) | **rejects** blending identity-confidence and truth-confidence into one pooled number | `spine/01`, `spine/04`, `08-spine-2.0-review.md` §B/§E |
| **LLM is proposer, never authority.** No LLM call runs inside `rebuild()`; every LLM output is produced once offline and frozen as a cited, versioned record; deterministic rules dispose. Structural deception detectors (hash/timestamp/aggregator/first-seen) are deterministic, never LLM; the insufficient-evidence statement is a deterministic fill-in-the-blank template; escalation is raise-only (LLM may rank/raise into the HITL band, never remove an item or push a pair past the 0.85 auto-merge line); LLM invocation is gated behind a deterministic pre-filter (high-alias-risk + orphan/thin-block for candidate-gen; near-miss + materiality/novelty for raise-from-reject) | Principle 4 (never fabricate) + principle 11 (reproducible/deterministic for the demo — frozen-replay stands in for "temperature-0," which Opus 4.8 doesn't support) + principle 5 (traceability by construction) | **rejects** letting the LLM finalize confidence or freely re-band status, and **rejects** regenerating prose at presentation time — only frozen, validated prose is ever displayed | `spine/04`, `spine/05`, `08`, `08-spine-2.0-review.md` §D |
| **`adversary_denial` (and single-pass `decoy_risk`) are GATES** (exclude the claim from grouping / cap status at probable) — **not multipliers** | Principle 6 (confirmed is not probable): a multiplier can still average out to "confirmed"; a gate cannot | **rejects** 08's original design, which bundled `adversary_denial` into the credibility multiplier | `spine/04`, `08-spine-2.0-review.md` §C |
| **Keep the 3 portability rules as-is; add a "layer contract" corollary** (a use case = read-only graph analytics + a decision rubric + output adapters over the shared graph, adding no storage/ingestion) rather than a new rule | Principle 8 (build once, extend by specification) | **rejects** promoting "encode the problem-statement logic as an algorithm over the graph" to a 4th independent portability rule — it's a consequence of the existing 3 rules, not a new one | `spine/01`, `08-spine-2.0-review.md` §E |
| **Analyst-initiated integrity flag**: an analyst can flag a source/origin as fake directly (a new caller of the same adjudication service, not system-triggered only); propagates automatically to every co-referring claim sharing that `primary_origin_id` on the next `rebuild()` | Principle 3 (the product is judgement — a human in the loop, not only a system-triggered queue) | **rejects** leaving integrity-flagging system-triggered-only (today's HITL) | `spine/04`, `spine/05`, `08-spine-2.0-review.md` §D |
| **Extraction = LLM-only, live at ingest (not frozen-only)** — everything via LLM → the one claim schema (no per-source parsers; time-gated demo); Gemini optional 2nd provider. A seeded baseline ships (keyless boot + reproducible graded beats), but **live ingestion is always available** so ingest→rebuild→alert runs for real. **Extract-raw guardrail:** extracts *stated* claims — incl. stated alias/`same-as` (→ `source_asserted` in resolution) — but never resolves/normalizes the *unstated*; replaces the parser-first anti-circularity defense. LLM runs upstream of the append, so the LLM-free-`rebuild()` invariant holds | Principle 10 (no per-source engineering) + principle 3 (live monitoring is a graded axis) + principle 7 (guardrail preserves messiness/anti-circularity) | **rejects** frozen-only extraction (can't demo live ingest→alert) *and* the hybrid deterministic-parsers extraction `07`/`08` originally drafted | `spine/02`, `spine/09`, `md/07-stack.md`, `08` §4, `08-spine-2.0-review.md` §H |

### Stack & retrieval (2026-07-17)
| Decision | Why | → |
|---|---|---|
| **Stack locked** — SQLite logs + **NetworkX** rebuilt view (KùzuDB-behind-the-view = scale path); FastAPI single process serving JSON + SPA same-origin; React/Vite + Tailwind/shadcn; Cytoscape.js + Leaflet vendored tiles; one multi-stage Docker image; **hosted on one always-on EC2 + Cloudflare Tunnel**; reviewers run it **both** ways (prebuilt GHCR image + `git clone && make run`); **`ANTHROPIC_API_KEY`** (+ optional `GEMINI_API_KEY`); Bedrock-via-EC2-instance-role = design-note prod path | Principle 7 (defensible, minimal moving parts) + principle 2 (depth over infra); single in-image artifact → `docker run` == the EC2 box == what reviewers run; the tunnel removes DNS/cert/port setup | **rejects** App Runner (adds ECR/IAM Day-0 setup), managed DB/VPC (unneeded at n≈25), split FE/BE hosting (CORS + 2 artifacts) | `md/07-stack.md` |
| **Multi-hop = bounded ReAct tool-calling loop over the graph — no framework, no embeddings**; ~7 namespaced `graph_*` tools; **materiality precomputed in `rebuild()` as filterable node attrs** + one parameterized `query_graph`; **entailment-based** citation validator; empty result → `check_sufficiency`, never a guess | Principle 5 (traceability by construction — tools return claim IDs, answer built from cited objects) + principle 4 (first-class refusal) + principle 10 (few capable tools) — research-backed (`md/14`) | **rejects** Microsoft GraphRAG (answer→LLM-summary→source defeats one-click provenance; corpus-theme search, not entity-anchored), vector RAG (single-hop, chunk-level provenance), free-form Text2Cypher (brittle; can't distinguish no-data from insufficient) | `spine/09`, `md/14` |
| **No embeddings in the runtime** — entity lookup = alias table + BM25 + fuzzy | The reason is **scale + signal, not determinism** (embeddings are deterministic): nothing to fuzzily recall at hundreds of curated nodes, and the discriminating OSINT signal is relational, not semantic (a front company is designed not to look like its parent) | **rejects** a runtime vector store; offline embedding candidate-gen for resolution stays roadmap | `spine/09`, `md/14` |
| **Hot-config / live-`rebuild()` — nothing a user does in-app requires an app restart.** `rebuild()` is a live in-process op (ms at demo scale) triggered by ingest/decision/config writes; user config (observables, weights, thresholds, ontology types) lives in a live store the UI writes to, not a baked file — so precompute-in-`rebuild()` tracks config changes automatically | Principle 9 (analysts, not engineers, evolve the rules — config-driven) + product UX (restart-to-reconfigure is a bad flow) | **rejects** boot-only rebuild / baked-config-file models that force a restart | `spine/09`, `md/07-stack.md` |
| **Analyst-defined observables + always-available live ingestion** — an observable is a DSL condition over existing attrs/precomputed metrics, defined live in the UI, armed immediately, fired on the next `rebuild()`; the locked Rawalpindi→Rahwali tripwire is just the seeded example; ingestion (append→rebuild→observable-eval) is always on, extraction is the optional front-end (raw+key → live extract; else pre-extracted claim bundles) | Principle 3 (the product is judgement — analyst configures their own tripwires) + principle 8 (extend by specification); makes the *monitoring/adaptation* graded axis real rather than a scripted reveal | **rejects** a single hardcoded observable + a scripted-reveal demo | `spine/09`, `C/02` |

### Data
| Decision | Why | → |
|---|---|---|
| **Hybrid synthetic-from-real**: real specimens as format/messiness templates, entities varied synthetically | Real messiness, controlled content; LLM "make it messy" produces fake, easily-un-messed noise | `md/04-claude-chat.md` Q3, `md/05` §0 |
| **Messiness = enumerable corruption operators**, applied programmatically | Reportable on the call; controlled and defensible | `md/04-claude-chat.md` Q3 |
| **Generator kept blind to the ontology**; seed a few **real uncurated docs**; **freeze multiple scenarios**, evaluators pick live | Kills the circularity objection; proves generalisation without live-generation risk | `md/04-claude-chat.md` Q3–Q4, `md/02-gemini-chat.md` Q4 |
| **Customs file is synthetic-from-real-template** (real BoL rows as template) | Finished SAM systems are genuinely invisible in public customs data for CN/RU/PK — defensible by necessity | `md/05` §0 |
| **Corpus = text + image + social**, six graded scenarios seeded from real material | Satisfies text+≥1 non-text rule; each scenario seeds a graded moment | `md/05` §5 |
| **Location precision is per-node-type, set by the touching query/observable — not by node grandeur** (fire-unit → pad/site; manufacturer/design-authority → facility+city+district; port → terminal; HQ → city; unobservable → Known Gap) | Principle 10 (model exactly what the queries need) — materiality applied to geography; the relocating fire-unit is the most precision-hungry node, the "biggest" org (Beijing design authority) needs only district | `md/13`, `C/01` |
| **Every demonstrated site carries ≥2 surface formats across independent docs** (DD/DMS/MGRS/toponym/renamed-alias/relative/port-alias) so the location-normalizer has real work; **anchor base/port coords real+public, the SAM pad synthetic-from-real & tagged** | Without multi-format refs the normalizer has nothing to resolve and can't be demonstrated; provenance-split keeps us from publishing novel battery fixes | `md/13`, `config/places.yaml`, `hq9p_primary.yaml` (places + expect.location + location_normalization flex) |
| **Location normalization = deterministic coord-canonicaliser + place-resolution over a seeded gazetteer, reusing the resolution layer's merge machinery; LLM proposes aliases only** — plus the **Karachi-Port ≠ Port-Qasim distinct-from trap** (geographic FT-2000) and a **withheld "Chaklala" alias** the resolver must earn | Principle 8 (build once, extend by spec — place is just another entity type with a geodesic attribute) + principle 4 (LLM proposes, rules dispose) + test-design (traps land in the HITL band; distinct-from is first-class) | `md/13`, `spine/08` §3.9, `config/places.yaml` |
| **Imagery = a resolution-tiered hybrid: Esri sub-meter (~0.5 m) for the frames that must SHOW a SAM site, Sentinel-2 (10 m) only for the deliberately-low-res cloud/gap beat, fabricated for social/deception.** Sentinel cannot resolve launchers (10 m; a TEL ≈ 1 px) — proven, so it must not carry positive equipment claims | Principle 4 (never fabricate — an image must not claim more than its pixels show; the VLM caption is neutral, so the shape must genuinely be present) + principle 7 (defensible: real morphology, not drawn) | `tools/gather/esri_fetch.py`, `md/12` addendum, `md/10` §6 |
| **"Confirm" SAM frames = real, unaltered imagery of genuine SAM sites (Xi'an HQ-9, Crimea S-400, Nanjing garrison, Lanzhou empty petal) RELABELED to scenario sites** — `integrity: real`, `provenance: relabeled`, `real_source` in the answer key; image quality matched to the claim (clear→confirmed, ambiguous→probable, empty→gap) | Principle 4 + principle 7 (own the synthetic-scenario limits out loud; auditable relabeling beats a fabricated "confirming" image the system should catch) | `hq9p_primary.yaml` (d07/d17/d18/d17b image blocks), `md/12` |

### Demo / output
| Decision | Why | → |
|---|---|---|
| **The one thread**: `source → credibility → triage → analyst → geo-tagged output`, driven by the worked query *"trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint"* | Brief: "show one thread end-to-end"; textbook auditable multi-hop | `C/02` |
| **Six demo flexes** each map to a graded quality + a planted scenario (confirmed/probable · insufficient-evidence · M4 override · HITL merge · freshness · the observable) | Each proves one graded property live | `C/02` |
| **One observable, wired end-to-end — LOCKED: the HQ-9B Rawalpindi→Rahwali (2025) occupancy state-change** (`based-at`); secondary tender/`replenishes` observables config-only | Exercises supersedes-vs-contradicts + decoy→probable cap + ≥2-independent gate + freshness decay in one beat; brief asks for ≥1, scope to one strong one | `C/02` (Q1), `08` §3.8 |
| **Confidence-coded geospatial layer + graph explorer**, click-through to provenance | Brief requires ≥1 viz; C benefits from both, but one done well beats two half-done | `spine/07`, `C/02` |

---

## 3. Open decisions (to close as the build proceeds)

> **PROPOSED RESOLUTIONS EXIST for every item below** in `artifacts/spine/08-detailed-design.md` —
> concrete verdicts with schemas, formulas, and defaults, plus a B-extensibility contract. **Pending
> user ratification** (its §7 lists the veto-worthy calls). On ratification, move each verdict into the
> ledger above and update the source-doc tails.
>
> **Already promoted to the ledger** (ratified / locked in the C docs, no longer just proposed): the
> credibility **factor rubric** (change #1) + **three-axis independence**; **dynamic per-source rating**
> as next-if-time; the **locked relocation observable**; **Known Gap** nodes + **supersedes/contradicts**;
> **HITL 8-control-points / 3-wired** phasing; the **enrichment bound (Q5)**. Items below remain open.
>
> **Also promoted (2026-07-17, spine 2.0 canonical reconciliation — see "Spine 2.0 canonical design" table
> above and `08-spine-2.0-review.md` PART 2):** the canonical scoring form (factor-rubric × noisy-OR,
> `claim_credibility`/`assertion_confidence` vocabulary, unified 0.50/0.80 cutoffs); INSUFFICIENT→Known Gap
> kept orthogonal to POSSIBLE; resolution as iterative collective ER with precision-first merge; the
> never-averaged two-scores rule; the LLM proposer-not-authority invariant (frozen-replay determinism,
> deterministic structural-deception detectors, raise-only escalation, selective invocation gate);
> `adversary_denial` as a gate, not a multiplier; the layer-contract corollary; the analyst-initiated
> integrity flag.

### Stack — DECIDED (2026-07-17) → `md/07-stack.md`, `spine/09`
Locked: **SQLite append-only logs + NetworkX rebuilt view** (KùzuDB-behind-the-view = scale path) · **LLM-only
extraction, live at ingest** (seeded baseline for keyless boot) · **no runtime embeddings** (alias + BM25 +
fuzzy) · Claude API direct (`claude-opus-4-8`) + optional Gemini, Bedrock-via-EC2-instance-role scaffolded ·
**bounded ReAct tool-calling agent** (~7 tools, `spine/09`; no `temperature` — 400 on Opus 4.8) · FastAPI
serving JSON + the built SPA same-origin · React/Vite + Tailwind/shadcn · Leaflet vendored tiles ·
Cytoscape.js · one multi-stage Docker image · **hosted on one always-on EC2 + Cloudflare Tunnel** · reviewers
run **both** ways (prebuilt GHCR image + `git clone && make run`) · secret via `.env`/compose env var
(`ANTHROPIC_API_KEY`). Through-line: a single in-image artifact so `docker run` == the EC2 box == what
reviewers run. Reasoning in the "Stack & retrieval (2026-07-17)" ledger table above.
- **Still open (taste/time):** frontend component strategy (shadcn default); map fallback depth; a thin
  CI-to-GHCR job. See `07-stack.md` → Open stack choices.

### Architecture open items
- **Where confidence lives** — on knowledge-layer node/edge, recomputed from evidence-layer claims. *Resolved: recompute is a live in-process `rebuild()`, ms at demo scale, run on any ingest/decision/config write — no restart (`spine/09`).* `spine/01`
- **Claim immutability vs correction** — retract via an appended retraction event rather than delete? *Leaning append-only.* `spine/01`
- **Typed-extraction aggressiveness at the edges**; **claim de-duplication** (one claim, multiple spans?). *Leaning one claim, multiple provenance spans.* `spine/02`
- **Resolution:** blocking / candidate generation (avoid O(n²)); high/low threshold values; **merge representation** (*leaning reversible same-as edge*); transliteration handling (rule vs learned). `spine/03`
- **Credibility:** per-edge-type **half-life defaults** (coarse now, calibrate later). *Score-combination
  form and confirmed/probable thresholds are now locked — see "Spine 2.0 canonical design" above.* `spine/04`, `C/01`
- **HITL:** UI surface (*leaning a minimal real review-queue for the ★ points so propagation is visible*); the structured trace-event schema; batching similar items. `spine/05`
- **Adaptation:** which single learning mechanism to demo (*leaning alias table*); how much of the loop is "online"; trace-sink choice (deferred). `spine/06`
- **Output:** how "observed vs inferred" is visually separated (still open). *Resolved: agent = bounded ReAct tool-calling loop over ~7 tools (`spine/09`); the call runs tested queries + live headroom, and ingestion/observables run live.* `spine/09`, `spine/07`, `C/02`

### C-specific open items
- How far the **China-HQ-9 enrichment** goes vs staying a reference (bound it — depth, not scope-creep). `C/00`
- **Radar/command node** — separate type vs component subtype (*leaning component with a `radar` role flag*); "component" granularity stop (*subsystem level*); how to model the **variant fork** (one PK import → HQ-9/P Army + HQ-9BE PAF, *leaning two `variant-of` children*). `C/01`
- **How many nodes** make the demo graph legible-but-non-trivial; exact **battery/site** as the query start (clean imagery frame — Karachi); which single observable; order of the flexes in the narrative. `C/00`, `C/02`

### Standalone research tasks (candidates for a subagent)
- **★ Materiality / IAF air-defence tradecraft** for SAM supply-chain + chokepoint analysis — drives the ontology and resolution signals. `C/01`
- **Adversary-methods-change / counter-deception** for supply-chain ORBAT (front-company rotation, dual-use relabelling, planted+self-referential corroboration, withheld signals) — research-hard. `spine/06`
- **Cheap deepfake/manipulation signals** that survive a demo (ELA, metadata, reverse-image); **collective/relational ER** literature; **grounded graph-RAG** with per-hop provenance. `spine/03`–`07`

---

## 4. The gates

**Spine gate** (= the "can I now build a second use case" pivot signal): the one worked query runs
end-to-end reproducibly · insufficient-evidence trips on a deliberately planted gap · every claim/node is
one-click traceable · a HITL override propagates to downstream state · the pipeline re-points to a new
subject/observable/question by editing **config, not core code**.

**Layer gate** (per use case): the target-output fields are all present, and you can beat the use case's
signature rebuttal. **C's rebuttal to beat:** *"how do you know that node is real — confirmed or
guessed?"* — deep enough when an interviewer can click anything and get a truthful
provenance/confidence/freshness answer.

## 5. Scope & time posture

~4 days. **Depth in batches:** build the spine with 2–3 HITL control points wired deeply, get one thread
running end-to-end, *then* add depth on top. A working thin thread beats a broken rich one. **C first**
(where the credibility discipline shines); **B only if the spine gate is met with time to spare.**
Everything past the demo — extra observables, more learning mechanisms, scale features (cost-only relevance
prefilter, resolution blocking, namespacing), B as a full layer — goes to the roadmap / "four more weeks"
section of the design note, not the build.
