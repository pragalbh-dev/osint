# DECISIONS — Guidelines & Decisions Ledger

**What this is.** The single consolidated record of *how we work* (guiding principles), *what we've
decided* (locked-decisions ledger, with pointers to the detailed reasoning), and *what's still open*
(pulled from every design doc's "Open questions" tail). `CLAUDE.md` is the terse boot context; this is the
fuller reasoned index behind it.

**How to use it.** Read the principles once — they govern judgement calls. When you *make or change* a
non-trivial decision, add a row to the ledger and update the source doc's tail. When you *close* an open
question, move it up into the ledger. Keep entries one-liners with a `→ pointer`; the reasoning lives in
the design docs, not here. *As of 2026-07-16. Deadline 20 Jul 2026, 12:00.*

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
11. **Reproducible & deterministic for the demo.** Frozen scenarios; the live query runs the same every
    time; the generator stays blind to the ontology so the pipeline earns its extractions.

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

### Data
| Decision | Why | → |
|---|---|---|
| **Hybrid synthetic-from-real**: real specimens as format/messiness templates, entities varied synthetically | Real messiness, controlled content; LLM "make it messy" produces fake, easily-un-messed noise | `md/04-claude-chat.md` Q3, `md/05` §0 |
| **Messiness = enumerable corruption operators**, applied programmatically | Reportable on the call; controlled and defensible | `md/04-claude-chat.md` Q3 |
| **Generator kept blind to the ontology**; seed a few **real uncurated docs**; **freeze multiple scenarios**, evaluators pick live | Kills the circularity objection; proves generalisation without live-generation risk | `md/04-claude-chat.md` Q3–Q4, `md/02-gemini-chat.md` Q4 |
| **Customs file is synthetic-from-real-template** (real BoL rows as template) | Finished SAM systems are genuinely invisible in public customs data for CN/RU/PK — defensible by necessity | `md/05` §0 |
| **Corpus = text + image + social**, six graded scenarios seeded from real material | Satisfies text+≥1 non-text rule; each scenario seeds a graded moment | `md/05` §5 |

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

### ★ Stack — deferred, gated on finalising spine scope (`artifacts/spine/`)
Decide tools *after* the spine scope is pinned down, so choices follow needs. Demo scale (~10–15 docs)
makes almost anything viable — pick for **schema-flexibility, easy provenance attachment, reproducibility**,
not scale.
- **Graph store** — property graph (Neo4j / KùzuDB / in-memory NetworkX) vs RDF vs document-store-with-graph-view. `spine/01`
- **Extraction method** — LLM function-calling to the claim schema vs **hybrid** (parsers for NOTAM/customs/tender + LLM for prose). *Leaning hybrid.* `spine/02`
- **Agent framework** — plain deterministic tool-calling loop vs a framework. *Favour minimal + reproducible.* `spine/07`
- **Map / geo stack** — tile source + rendering lib. `spine/07`
- **Frontend + hosting** — the web-app framework and deploy target (needed now that the deliverable is a hosted app). *new*

### Architecture open items
- **Where confidence lives** — on knowledge-layer node/edge, recomputed from evidence-layer claims; confirm recompute is cheap/deterministic per update. `spine/01`
- **Claim immutability vs correction** — retract via an appended retraction event rather than delete? *Leaning append-only.* `spine/01`
- **Typed-extraction aggressiveness at the edges**; **claim de-duplication** (one claim, multiple spans?). *Leaning one claim, multiple provenance spans.* `spine/02`
- **Resolution:** blocking / candidate generation (avoid O(n²)); high/low threshold values; **merge representation** (*leaning reversible same-as edge*); transliteration handling (rule vs learned). `spine/03`
- **Credibility:** exact score-combination form (transparent > sophisticated); per-edge-type **half-life defaults**; confirmed/probable thresholds; a concrete **"independence" rule**. `spine/04`, `C/01`
- **HITL:** UI surface (*leaning a minimal real review-queue for the ★ points so propagation is visible*); the structured trace-event schema; batching similar items. `spine/05`
- **Adaptation:** which single learning mechanism to demo (*leaning alias table*); how much of the loop is "online"; trace-sink choice (deferred). `spine/06`
- **Output:** how "observed vs inferred" is visually separated; whether the call runs a scripted worked query vs live free-form (*leaning one scripted query + headroom for a follow-up*). `spine/07`, `C/02`

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
