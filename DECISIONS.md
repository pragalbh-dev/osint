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

### Extraction & ingestion (2026-07-17, DATA-C/INGEST context pass)
| Decision | Why | → |
|---|---|---|
| **Extraction = provider-native function-calling — no DSPy, no litellm.** One tool `emit_claims`, `input_schema` = the F0 `ExtractionResult`/`ClaimRecord` model, forced `tool_choice`, **no `temperature`/`top_p`/`top_k`** (400 on Opus 4.8); behind a thin 2-method `LLMClient` protocol so provider is swappable | Principle 5/7 (transparency graded — the operative prompt lives in readable code, not a compiled `states/*.json` artifact) + the copy-paste case for DSPy is mostly **non-DSPy** (ally's concurrency = ThreadPool + a Consul/gRPC rate-limiter that **silently no-ops off-cluster**; "Azure" = OCR we don't need); short OSINT docs make DSPy's truncation/stall/continuation machinery dead weight; DSPy's cache-to-disk is a reproducibility footgun; no trainset/compile budget in ~4d | **rejects** DSPy-as-`ai_extraction_v2` (opacity + cache/determinism trap, unrealized optimizer upside), **rejects** litellm-only (hides Anthropic strict-tool use; translation-layer drift on the structured-output surface). litellm = one-line swap-in later if a 3rd provider is ever needed (roadmap) | `plan/sessions/INGEST.md`, `spine/02`, ai_extraction_v2 dive |
| **Extraction provider = Gemini** (native `google-genai` function-calling). The frozen keyless claim bundles are **Gemini output** (canonicalised + pinned `ingest_time`); **Anthropic `claude-opus-4-8` stays the ASK-agent provider** and an optional 2nd extraction impl behind the same `LLMClient` protocol | User has the Gemini key + quota already wired (`tools/imagery.py`), Gemini is natively multimodal so it also carries the VLM path on one client, and it's the high-volume lane | **rejects** Anthropic-default extraction (would re-freeze bundles from a different provider than the imagery tooling already uses). Confirm exact Gemini model id for the key/region → `extraction.model` config, never hardcoded | `plan/sessions/INGEST.md`, `.env` |
| **VLM imagery path is IN demo scope** (not roadmap): an imagery doc yields **both** the analyst-`.txt` text claim(s) **and** Gemini-VLM pixel claims — a `kind:observation` claim (occupancy_state / `observed_signature` / count-as-`Quantity` + geo / resolution / first_seen / caption_consistency / decoy_risk) **plus a separate `kind:inference` claim** for signature→variant — **REFINED 2026-07-18 (see row below):** NOT a VLM-emitted field but a **guided-LLM corroboration** of the observation against **ingested reference literature** (`premises:[observation, literature-fingerprint]`, **capped at probable** until a 2nd discipline-independent look); the VLM observation itself carries no variant field. The deterministic integrity stack (`sha256` + PDQ perceptual `first_seen`) stays **outside** the LLM | User chose full VLM; it models the **pixel-vs-attribution boundary the oracle deliberately tests** (relabeled-real frames — d07 "Karachi" pixels are an HQ-9 site near Xi'an), the strongest demo; Gemini multimodal makes it cheap on the chosen provider | **rejects** the text-only demo posture. **Timeline guard:** build **additive** — text path + social-image integrity stack (the M4 recycled-parade flex, keyless-safe) land first as the safe demo; VLM pixel-reading enrichment second | `plan/sessions/INGEST.md` §6, `C/01` (`signature_library`), `spine/04` |
| **Reuse from `ai_extraction_v2` = patterns, not code:** semaphore-bounded `asyncio.gather` fan-out + per-page unit-of-work + per-item failure isolation (a failed page = a flagged **coverage gap**, never a silent drop); the ~40-line `@retry` (transient-transport backoff); Pydantic **coerce-and-flag** robustness (`_safe_enum`→OTHER, `model_validator` shape-repair, ISO date sanitize) = recall-bias at the extraction boundary; VLM = same tool + an image content block | Principle 2 (depth over infra — lift the proven shape, skip the cluster scaffolding) + the recall-bias mandate (never drop a claim over a malformed enum) | **drops** DSPy, the Consul/gRPC `@rate_limiter` (the no-op-off-cluster trap), all Pulsar/S3/Secret/PodWorker infra, and the entire OCR/bbox/grid/cell/chart/Excel/table-split pile | `plan/sessions/INGEST.md`, ai_extraction_v2 dive |
| **Image integrity = TWO hashes frozen at ingest; a LOCAL index is the deterministic authority (2026-07-18 deep-research, `md/15` §1).** `sha256` = exact-byte / same-origin grouping ONLY (any recompression flips ~half its bits — avalanche); a **PDQ** 256-bit perceptual hash (Hamming-threshold + quality gate, both config) is the recycled/near-dup signal — it catches the **lazy recycle** (screenshot / re-upload / format-convert) but a determined crop+rotate+overlay slips it (the **lazy-recycle bottleneck**; SSCD = roadmap). `first_seen=recycled` is computed in `rebuild()` over a **local corpus-internal `perceptual-hash→earliest-date` index**; a near-dup is a **penalty + HITL flag, never proof, never an auto entity-merge** (false-merge of look-alike SAM sites is the dominant risk) | Principle 11 (reproducible where it matters) + 5 + 7 + 4 (quality gate = no fabrication on weak evidence) — **fixes** the `spine/04`/`08`/INGEST "perceptual/crypto hash" conflation (sha256 can't do recycled; perceptual degrades under WhatsApp recompression → BOTH, distinct roles) | **rejects** single-"hash" wording. Reverse-image (TinEye) is **roadmap**, deferred **NOT** for determinism/keyless (the app is keyed; it would run at ingest as a frozen **proposer**, never inside `rebuild()`, so G1 is untouched) but for **build-budget + crawl-date≠first-appearance**; if wired, frozen on the record behind a swappable adapter. Bellingcat: recycling is a *more common* disinfo method than manipulation | `md/15` §1, `spine/04` §D, `08` §3.11, `plan/sessions/INGEST.md` §6 |
| **Imagery VLM = subject-blind structured observation; signature→variant is a guided-LLM CORROBORATION vs ingested literature, NOT a VLM leap (2026-07-18 deep-research + user decision, `md/15` §2).** The VLM emits an all-optional **observation** (generic feature tokens · `occupancy_state` · `count`-as-`Quantity`-range · free-text · `caption_vs_image_consistency` · frozen `geo`/`gsd`) — **no variant field**; naming a subject collapses it to its prior (VLMs ~100% canonical vs ~17% counterfactual; "sycophantic modality gap"). The signature→variant leap is a separate `inference` claim, `premises:[observation, literature-fingerprint]`, capped at **probable** (`decoy_risk`); the fingerprint is **discovered from ingested reference text**, not hand-authored config. This same inference is **what lets a satellite image corroborate a text "HQ-9 at base X" claim** (both resolve to one `Basing site` edge; EO vs text = independent) | Principle 4 (never fabricate — no priming, honest counts, empty-pads→insufficient, variant grounded in a source not a pixel-leap) + 5 (traceable to both premises) + 9 + 11 | **rejects** subject-primed prompts, a satellite-specific variant-classification schema, AND the VLM asserting a variant from pixels (→ design note); **rejects** a hand-authored `signature_library` (use ingested literature). Resolution-floor gate scoped to the deliberate low-res beat (Sentinel-2 10 m; main confirm frames Esri ~0.5 m) | `md/15` §2, `C/01` (`site_signature_geometry`, Indicator), `spine/04`, `plan/sessions/INGEST.md` §6 |
| **Extraction schema = per-source (all-optional) extraction schema + deterministic transformer → the one `ClaimRecord` (2026-07-18 deep-research + user decision, `md/15` §3).** Bare OpenIE triples are too noisy; a single all-purpose emit-claims asks too much of the LLM on structured rows. Each `source_type` gets an all-optional extraction schema (carrying generic ontology TYPES, shaped so the transformer is a **simple field→type mapping, not inference**); the LLM fills only what the source *states* (nothing stated → NO claim → insufficient-evidence), and the transformer builds the s/p/o + does node-typing + the **3-tier attribute promotion** (own node/edge · knowledge-layer attribute · nullable typed `attributes` bag for HS-code/container#/BoL#). A BoL row → **many** typed claims, each keeping the raw cell on `doc_ref` (G4) | Principle 4 (all-optional = anti-fabrication; the transformer, not the LLM, constructs claims — auditable) + 8 + 10 + 2 + 5 | **rejects** pure OpenIE (flattens/noisy) and a subject-aware single direct-emit; the single-schema **direct-emit = later optimization**. Source-typed schemas are G9-safe (source-typed ≠ use-case-typed) and *more* G11-safe (LLM never picks an instance). `attributes` bag = small F0-amendment (nullable, raise-not-widen) | `md/15` §3, `spine/02`, `08` §3.1, `plan/sessions/INGEST.md` item 2a |

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
- **Perceptual-hash primary** — ***Resolved (2026-07-18): PDQ*** (256-bit, `pdqhash`; best recompression robustness). The **lazy-recycle bottleneck** (crop+rotate+overlay slips it) is noted; SSCD = roadmap. Hamming threshold + quality cutoff are config. `md/15` §1, `plan/sessions/INGEST.md` §6
- **Extraction: per-source schema vs single direct-emit** — ***Resolved (2026-07-18): per-source (all-optional) extraction schema + deterministic transformer → `ClaimRecord`*** (`md/15` §3); the transformer does node-typing + 3-tier attribute promotion; single-schema direct-emit = later optimization. `plan/sessions/INGEST.md` item 2a
- **Typed `attributes` bag** — ***Resolved (2026-07-18): adopt*** as a nullable typed key-value field on the ClaimRecord payload, filled by the transformer via the **3-tier promotion** (own node/edge · knowledge-layer attribute · attributes bag). Small F0-amendment (raise-not-widen, master Rule 3). `md/15` §3, `spine/08` §3.1
- **F0 reconciliation — extraction sub-schema naming** *(raised 2026-07-18, `md/15` §4).* master §4.2 `{method, version, model_conf}` vs INGEST `extraction.model`. *Recommendation: standardize on `model` as an F0-amendment (pending F0 PR).* `plan/00-master-plan.md` §4.2, `plan/sessions/INGEST.md`

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

---

## 6. Build decisions (appended per session; §8 of the master plan)

### F0-amendment — places + merge-edge rendering (RESOLVE-raised, 2026-07-18)
- **`config/places.yaml` promoted to the 8th loaded config section (`PlacesConfig`).** Principle 9
  (config-driven extensibility) + the hot-config rule: the gazetteer is genuinely analyst-tunable config,
  so it is served by the live store (hot-editable, no restart, single source of truth) rather than
  read from a second file path inside RESOLVE. Rejected: RESOLVE loads `places.yaml` itself (a second
  config path; gazetteer not hot-editable). → `schemas/config_models.py`, `config/store.py`. *(User
  approved the config-store route after the gazetteer's open-world-overlay purpose was explained.)*
- **Merges + traps are first-class in the view: `rebuild()` emits candidate `same-as` + `distinct-from`
  edges (with `merge_confidence` + score breakdown) and stamps `resolved_from` provenance on
  auto-merged nodes; `Partition` gains `candidates` + `merge_breakdown`.** Principle 5 (traceability) +
  6 (confirmed ≠ probable): the marquee "grain in the chaff, human in the loop" reasoning has to be
  *visible* — the analyst adjudicates a rendered candidate, and the "why" is one click away. Edges are
  emitted after the status machine so they are never scored (G5) and are G4-exempt (they cite a merge
  decision, not a claim). Rejected: keep merge decisions inside the Partition only, unrendered (marquee
  invisible in the graph). → `schemas/stage_io.py`, `view/pipeline.py`. *(User approved the "small F0
  touch-up".)*
- **`resolve()` receives the decision log; `_assemble()` reconnects merged entities' edges.** Principle 5
  (traceability) + the design's own words (spine/03:37 — resolution is a pure function of *evidence log,
  **decision log**, config*): the offline LLM proposer's `merge_proposal` records + the analyst's
  `merge_adjudication(accept)`s (alias learning) both live in the decision log, so `resolve()`'s signature
  gains `decisions` (default None; only `rebuild()` calls it → no sibling breaks; still LLM-free on the
  rebuild path, G1). And because edges attach to nodes by the *raw* triple subject/object string
  (`supersede.py`), a merge is made to actually reconnect edges via `Partition.entity_canonical`, applied
  in `_assemble()`. Both additive + empty-safe (golden byte-identical, G2). Rejected: apply learned merges
  only as post-resolve HITL effects (can't unlock the relational fixpoint, and can't collapse nodes cleanly);
  leave edges dangling on merge (corrupts the graph). → `schemas/stage_io.py`, `view/pipeline.py`,
  `resolve/__init__.py`.
- **FT-2000 is scored into the HITL band, not seeded as a hard `distinct-from`.** Principle 3 (product is
  judgement) + 4-adjacent: the look-alike must demonstrate the scoring judgement + human adjudication, not
  be pre-vetoed. Config fix routed to DATA-C (`tmp/conv/RESOLVE-config-and-oracle-observations.md`);
  RESOLVE emits it as a mid-band candidate. Rejected: keep the seeded veto (short-circuits the demo).
  *(User decision, this session.)*

### RESOLVE — iterative relational entity resolution (2026-07-18)
- **Precision-first / false-merge discipline is structural.** distinct-from is a hard veto enforced at the
  **cluster level** (a union that would co-cluster a vetoed pair is refused — a direct-pair-only check let a
  bridge node fuse HQ-9/P↔HQ-9BE transitively); gazetteer `distinct_from` (Karachi-Port ≠ Port-Qasim) is a
  **veto computed before entity resolution**, so co-located/co-shipping ports never fuse. Rejected:
  per-pair-only veto (bypassable). → `cluster.py`, `places.py`.
- **LLM is proposer, never authority; raise-only is structural.** `band()` reaches *auto* only via the
  deterministic terms; an LLM `merge_proposal` (consumed from the decision log) can only lift a pair to the
  *HITL* band — a maximal LLM signal on a trap can't cross 0.85. Rejected: LLM feeding the numeric score.
  → `cluster.py`, `propose.py`.
- **Merges are a reversible overlay, never destructive collapse.** `same_as` + a flat `entity_canonical`
  collapse nodes at assembly; a claim's own `resolved_ref` is untouched, so a no-merge run is byte-identical
  to F0's stub (G2) and a split is just another decision-log entry. → `__init__.py`, `cluster.finalise`.
- **Relocation ≠ identity.** Two entities that are co-endpoints of one supersede `edge_instance` are
  excluded from the relational term and score temporal-consistency 0 (reusing F0's supersede identity — a
  unit's two bases don't fuse the bases). → `scoring.py`.
- **Adversarial self-review before PR (principle 7, defensible-not-clever).** Two review workflows
  (find → adversarially-verify) caught 12 + 1 confirmed defects the unit tests missed; each is fixed and
  locked by a regression (`tests/resolve/test_review_regressions.py`). Rejected: ship on green units alone.

### F0 — Foundation (choice · principle invoked · alternative rejected)
- **Records `extra="forbid"`, config surfaces `extra="allow"`.** Principle 5 (traceability) + 9
  (config-driven): a drifted record fails loudly; DATA-C may add config knobs without an F0-amendment.
  Rejected: one permissive base for both (silent contract drift) / one strict base for both (every DATA-C
  knob = an amendment). → `schemas/base.py`.
- **No network/parse/clock/RNG in any pydantic validator; value objects are shapes + canonical slots
  only.** Principle 4/11 + gate G1: a validator would fire Nominatim/parse on every `rebuild()` reload and
  break purity. The normalization *adapters* are INGEST's, run once at extraction. A pure
  `canonical_iso_bounds()` gives SCORE an offline freshness read. Rejected: on-instantiation geocoding
  (breaks G1). → `schemas/values.py`.
- **Two scores are separate objects (G5): `merge_confidence` on the same-as edge, `assertion_confidence`
  in the confidence breakdown; `status` set only by the machine or an explicit override.** Principle 6
  (confirmed ≠ probable). Rejected: a single pooled confidence number. → `schemas/view.py`, `pipeline.py`.
- **Append-only enforced two ways: no mutating methods + SQLite `RAISE(ABORT)` triggers (G3).** Principle 5
  + the immutability decision. Rejected: convention-only append-only (a raw UPDATE would slip through). →
  `store/log.py`.
- **Supersede/contradict matches on `resolved_ref.edge_instance`, not designator strings; sets structure
  (`superseded_by`/`opposing`/flags), never `status` (SCORE reads the structure → stale).** Principle 6 +
  the supersedes-vs-contradicts rule; keeps G5 clean. Rejected: supersede writing `status` directly. →
  `view/supersede.py`.
- **A subject is a lens parameter; no per-subject package (G10). Edge id = `e:{src}:{type}:{tgt}`.**
  Principle 8 (build once, extend by spec). Rejected: a bespoke per-subject graph/table. → `view/lens.py`.
- **`make test`/`lint`/`typecheck` are real; only the app targets are stubbed.** Acceptance requires
  `make test` green (master §7). Reconciles F0.md scope #1's "all targets echo TODO".
- **`PROGRESS.md` not edited in the F0 PR.** Master §2 Rule 4 (never in a PR; user maintains at merge)
  overrides F0.md scope #10's "seed". Reconciliation, not a contract change.
- **Rename the rebuild *module* to `view/pipeline.py` (function stays `rebuild`).** DX/testability: a
  module and function sharing `chanakya.view.rebuild` made the module un-patchable via attribute access.

**Design-doc tails to enrich (flagged per the working agreement):**
- `plan/00-master-plan.md` §4.1 — add `tests/{view,store,config,schemas}` to F0's owned paths; note
  `make test/lint` are real; note `Location` carries `geocode_candidates`+`proposed_alias` (closes the
  PROGRESS "F0 location descriptor" reconciliation); note `rebuild()` module is `view/pipeline.py`.
- `sessions/F0.md` — reconcile scope #1 (test/lint real) + #10 (PROGRESS not in the PR).

### MONITOR — Observable DSL engine (choice · principle invoked · alternative rejected)
- **Explicit `watch_instances` union'd with the lens (F0-amendment #9).** Principle 3 (the analyst
  configures their own tripwires) + 8 (extend by spec): an observable's scope = a lens (graph-hop
  neighbourhood) **∪** an explicit set of resolved entity ids, so "watch exactly these units" and "watch
  this area of the graph" are one model. Rejected: overloading `subject` to `str|list` (a frozen-field
  type change) / burying the list in the `trigger` dict (undiscoverable for the API/SPA). → `schemas`
  (amend), `observe/observable.py`.
- **One generic DSL (equality/threshold/exists) + crossing as a delta *mode*; `trigger.on` compiles to
  crossing/exists/match/arm-only with NO per-observable branch (G6).** Principle 9 (analysts evolve the
  rules via config, not code) + 8. Operator tokens match `query_graph`'s so the DSL and retrieval speak
  one vocabulary. Rejected: three hardcoded trigger handlers (not declarative — a new tripwire would need
  code). → `observe/dsl.py`, `observe/observable.py`.
- **`new_claim` (source-class) compiles to *arm-only*.** Principle 4 (never fabricate) + spine/09 honest
  boundary: a claim-level trigger lives in the evidence log, not the rebuilt view, so it parses + arms but
  cannot fire off a *view* delta — and `explain()` says exactly why. Rejected: faking a fire from data the
  view doesn't carry. → `observe/observable.py`.
- **Match on the resolved `edge_instance`/`id`, never a designator string; supersede-aware active-edge
  selection.** Principle 6 + the supersedes-vs-contradicts rule: a spelling/transliteration variant that
  resolves to the same instance trips the same wire; a different instance does not. Rejected: matching on
  names (would break or duplicate the wire). → `observe/evaluator.py`.
- **`evaluate()` leaves `fired_ts=None` (the API stamps it on persist); no clock/RNG/network/LLM in
  `observe/`.** G1/G2 spirit — a wall-clock in the evaluator would make it non-deterministic and
  un-fixture-able. Rejected: stamping the time inside `evaluate`. → `observe/evaluator.py`.
- **Lenient scope fallback: a named lens whose anchors are absent in the current view → unscoped, not
  disarmed.** Recall-bias (hold recall of escalation ≈ 1.0): never silently drop a tripwire because its
  subject isn't present yet. Rejected: dropping candidates when the lens can't resolve. →
  `observe/observable.py::resolve_scope`.
- **Disposition: MONITOR *consumes* (reads `alert_disposition` back into per-observable tuning stats),
  HITL *owns* the card + writeback; the verdict vocabulary comes from each observable's config;
  `needs-more` is flagged awaiting-coverage; nothing auto-retunes.** Principle 3 (human-in-loop) + the
  non-negotiable (insufficiency is first-class). Rejected: MONITOR mutating config/graph from dispositions
  (a machine silently retuning its own tripwires). → `observe/disposition.py`.
- **Location axis built as a *seam*, not demo-wired (locked 2026-07-18).** Principle 8 (extensible seam,
  user-approved) + the "build seam, roadmap the demo" call: geofence entry/exit (`within_area`, offline
  `geopy` great-circle math) and a "near a place" location-scope filter are pure config edits, proven by
  tests, but the shipped `config/observables.yaml` wires none — the demo stays led by the instance-scoped
  Rawalpindi→Rahwali relocation. Rejected: wiring a geofence into the demo (competes with the locked beat)
  / not building the axis (clips a capability the data already supports). → `observe/dsl.py`,
  `observe/evaluator.py`.

**Design-doc tails to enrich (MONITOR):**
- `spine/07` / `spine/08` §3.8 — record the DSL operator set (eq/threshold/exists + crossing mode), the
  `new_claim` arm-only honest boundary, the `watch_instances` explicit-scope, and the geofence/location
  seam (roadmap).
- `C/02` — note the geofence tripwire is a roadmap flex, not demo-wired.

**Follow-up handed to another session:**
- **ASK owns `propose_observable_from_text()`** — free text ("watch HQ-9B and the 8th SAM regiment for
  relocations") → an `ObservableDef` draft, reusing ASK's `find_entity` to resolve named mentions to ids
  (LLM proposes upstream; the analyst confirms before arming). MONITOR pre-wired the target: the
  `watch_instances` field + `explain()` for the confirm screen. Logged as an ASK scope note in
  `PROGRESS.md`.

### ASK — Bounded ReAct agent + citation validator (choice · principle invoked · alternative rejected)
- **`ask()` gains two optional query-time inputs (F0-amendment):**
  `ask(question, view, config, llm=None, claims=None)`. Principle: *LLM is a proposer downstream of
  `rebuild()`; testability + keyless boot* (invariant #2, master §6); *unit = the sourced claim, one-click
  to source* (principle 5). Both are additive/optional so the API caller `ask(question, view, config)` is
  unaffected.
  - `llm` reaches the agent through a provider-agnostic `agent.client.LLMClient` seam so offline tests
    inject a mock/recorded client and keyless boot replays the recorded hero-trace. Rejected: keeping the
    3-arg signature and constructing the client internally from env (harder to inject; hides the
    dependency). *User chose the amendment route.*
  - `claims` (a `claim_id → ClaimRecord` lookup) because `rebuild()`'s view references claims by ID only —
    the bodies (`kind`, `doc_ref`, source, dates) live in the evidence log, and `get_evidence` +
    observed-vs-inferred need them. Rejected: stuffing claim bodies into `view.meta` (bloats the `/view`
    payload; `meta` is diagnostic-only) or reconstructing them from the view (impossible — `kind`/span/date
    aren't there).
- **Bind the hero trace to the DATA-C `answer_key.json` edge names, not `sessions/ASK.md`'s prose.**
  Principle: *the answer_key/`ontology.yaml` is authoritative (design-authority order, master preamble).*
  Chain = `site_karachi ←based-at– unit_paad ←inducted-into– var_hq9p ←equips– comp_ht233 ←manufactures–
  mfr_casic` (5 nodes/4 edges; stored origin-ward, traversed bidirectionally). Rejected: ASK.md's stale
  `imported-by → exported-by → supplies-component` (would diverge from the corpus and break EVAL).
- **Chokepoint honesty fork → return both, never collapse.** Principle: *the non-negotiable — absence of
  evidence ≠ evidence of absence.* `query_graph` reports confirmed-and-candidate separately and partitions
  `substitutability_state = UNKNOWN` into an `indeterminate` set, never counted as "no substitute" (HT-233
  stays CANDIDATE). Closes the spine/09 open question along its stated leaning. Rejected: collapsing
  candidate/UNKNOWN into a confirmed negative (prints ignorance as a finding).
- **`propose_observable_from_text` is a draft-only proposer (MONITOR handoff, folded into this PR).**
  Principle 3 (human-in-loop) + invariant #2 (LLM proposes upstream, never disposes): free text → an
  `ObservableDef` draft the analyst confirms before MONITOR arms it. Named mentions resolve via ASK's
  `find_entity` (matched on the resolved instance, never a designator string); an unresolvable mention is
  surfaced with its "did you mean" and left out of `watch_instances`. Reuses MONITOR's pre-wired
  `watch_instances` (F0-amend #9) + `explain()`. Rejected: auto-arming a tripwire from text (removes the
  human gate) / silently binding a near-match (a wrong-entity tripwire is worse than an unresolved one).
### INGEST — F0-amendment (schema slots) + onboarding decisions (choice · principle · alternative rejected)
- **Additive nullable schema slots via a small F0-amendment (not folded into the INGEST PR).** Master Rule 3:
  a shared-contract change lands as its own early PR so siblings rebase. Added `DocRef.line` (human-readable
  txt locator; char `span` stays the exact range) + `ClaimRecord.attributes` (tier-3 source-native bag).
  Additive/nullable → no sibling code change. Rejected: overloading per-payload `attrs` for tier-3 (no home on
  a bare relationship Triple); deriving line at display time only (user asked it be stored). → `schemas/claim.py`.
- **Defer `extraction.version`→`model` rename.** Coordination-floor stability > cosmetic naming: the rename
  touches `claim.py` + 4 live sibling worktrees for no demo benefit; INGEST stores the model-id in the existing
  `version` field and defers the rename to a post-INGEST PR. Rejected: renaming mid-Wave-1.
- **INGEST owns the bearing+distance geo-offset (the Rahwali beat).** Principle 4/11 + G1: the locked
  relocation observable only fires if d18(DMS)≡d19("~12 km NNW of Gujranwala") unify; INGEST deterministically
  applies the bearing+distance → Rahwali-level WGS84 at extraction (pure geo-math, no network), keeping the
  Gujranwala anchor as a `geocode_candidate`; place-merge stays RESOLVE's. Rejected: freezing only the anchor
  centroid + widening RESOLVE's radius (fragile vs the distinct-from traps; silent demo failure).
- **Extraction dispatch = native record format, not credibility `source_type`.** Principle 8 + G9: `source_type`
  (credibility class) is coarser than the doc's native shape (`official`=PR|NOTAM, `customs-tender`=BoL|tender);
  6 format-keyed all-optional schemas + a deterministic text sniffer split the ambiguous families. Format is a
  source axis (G9-safe, not use-case-typed). Rejected: one schema per `source_type` (wrong-schema routing for
  NOTAM/tender docs).
- **Concurrency: parallel extraction, serial deterministic id-assignment, single-writer append+rebuild.**
  User ask + G2: fan out I/O-bound extraction across+within docs under a bounded semaphore, then assign
  `claim_id`s in a serial pass (stable sort by doc then span offset) so frozen bundles stay byte-stable;
  `append` + `rebuild()` serialized. Rejected: assigning ids during the parallel fan-out (nondeterministic
  order → breaks G2 byte-stability).

**Build decisions (feat/ingest, appended at implementation):**
- **The lane triggers `rebuild`/`observe` via INJECTED callables, never an import (G9).** The G9 gate
  forbids `chanakya/ingest` importing `chanakya.view`/`observe`/`resolve`/materiality-scoring; the lane
  legitimately orchestrates rebuild+observe, so `ingest_document(rebuild_fn=, observe_fn=)` takes them as
  params (the `/ingest` API passes the real ones). Rejected: importing the stages (fails G9) / a
  function-local lazy import (evades the scanner but keeps the coupling). This also makes the lane offline-
  unit-testable.
- **Geocoding at extraction is OPT-IN (offline by default); revises the earlier "INGEST owns the bearing+
  distance offset" note.** `adapters.normalize_location(geocoder=None)` does offline coord-canonicalisation
  only — it never makes an unexpected live Nominatim call in the claim path (determinism / G2 / keyless).
  The Rahwali bearing-offset for a *named* anchor is computed only when a geocoder is injected at
  `make extract` (frozen into the bundle), else deferred to RESOLVE's gazetteer at rebuild. Recommended
  injected geocoder = a **gazetteer-backed** offline resolver over `config/places.yaml` (byte-stable). This
  supersedes the earlier "pure geo-math, no network at extraction" wording for named anchors. Rejected: an
  unconditional live Nominatim call at claim-mint time (the adversarial-review HIGH finding).
- **Imagery corroboration eligibility = an affirmative-occupancy ALLOWLIST.** The "no fabrication on an
  empty site" guardrail gates on `occupancy_state ∈ {occupied, garrison, …}`, not a bare `"empty" in occ`
  denylist, so "vacant"/"unoccupied"/"dormant"/blank can't slip a deployment/variant read. Rejected: a
  substring denylist (misses reworded emptiness). (Adversarial-review HIGH.)
- **Cross-claim references (`premises`/`targets`) are remapped in `dedup.assign_claim_ids`, not per-caller.**
  A general fix so the imagery signature→variant inference keeps pointing at its observation in BOTH the
  live lane and the frozen-bundle seed; the lane additionally namespaces each concurrent extraction chunk's
  provisional ids so multiple co-located images can't collide + cross-wire. Rejected: a lane-only remap
  (leaves the seed path broken).

**PDF-multimodal + geocoding follow-up (feat/ingest-pdf-geo, 2026-07-19; handoff `tmp/conv/INGEST-handoff-pdf-geocoding-keyless.md`):**
- **PDF path = one non-brittle read: OCR-when-keyed / pymupdf text, and ALWAYS render every page to an
  image for ONE multimodal extract call. No born-digital detection.** Principle: capability over premature
  optimization; depth on the reading path. The old text-density heuristic (born-digital vs scanned) is
  dropped — an `AZURE_*` provider present → Azure OCR (paged text+tables+figures); else pymupdf's text
  layer (poppler fallback). Either way pymupdf rasterises every page, and text + page images feed one
  forced-tool call so the model reads prose, tables and figures together. Rejected: the brittle
  "no-page-returned-text → OCR" branch and a separate per-figure VLM call. `md/15` §4, `spine/02`,
  `plan/sessions/INGEST.md` item 1.
- **Subject-blindness stays scoped to STANDALONE adversarial imagery; the PDF page-read is subject-aware
  multimodal.** Principle 4/11 + G9: the sycophantic-modality-gap risk (~17% counterfactual) is a
  *pixel-only* failure mode, so satellite/social `.png` keep the subject-blind `imagery.py` lane
  (`read_image`); a PDF page-read is text-anchored (the surrounding prose is legitimate context) so it
  rides the new `extract(images=…)`. Routing is by file-shape (loader dispatch), which for this corpus
  equals the source-type split. Rejected: forcing subject-blindness onto document figures (needless
  capability loss) or feeding subjects to standalone imagery (the documented failure). `md/15` §2/§4.
- **OCR regions get char-spans assigned at assembly (G4 fix).** Azure returns paged regions with
  `page`/`bbox` but no char `span`; the loader now stamps a span as it concatenates, so
  `loaded.text.find(source_quote)` → `locate` → the region's page/bbox. Without it an OCR'd doc silently
  lost per-page provenance. Validated live (real Azure OCR → `find→page` resolves). Principle 5 + G4.
- **Page-window chunking is a size GUARD (`PDF_CHUNK_MAX_PAGES=8`/`_CHARS=60_000`), not the default; filled
  dicts merge BEFORE one transform pass.** Principle: a multi-page PDF is ONE doc → one dedup batch → one
  deterministic id-assignment (G2). Only an oversized, page-structured doc is windowed; each window's text
  is a contiguous substring so `find` provenance still resolves. Thresholds are module constants (the
  `MAX_TOKENS` precedent; G6 scans only the scoring packages, never `ingest/`) — a full INGEST config
  section was disproportionate for two tunables and would touch F0-owned schema. Rejected: per-window
  transform passes (would split one doc's dedup batch, breaking G2). Candidate to graduate to config later.
- **Gazetteer-first coordinate cache at INGEST, then Nominatim (`ChainedGeocoder`); refines the md/13
  baseline that put ALL gazetteer use in RESOLVE.** Per the two 2026-07-19 coordination notes (the handoff
  + RESOLVE's `INGEST-locations-gazetteer-vs-nominatim.md`): INGEST uses `config/places.yaml` as a strict
  offline **coordinate cache** (EXACT normalised match on `canonical_name`/`alias`/`icao`/`locode` →
  freeze `canonical_dd`, `source="gazetteer"`), Nominatim for the open world. Additive + strictly *better*
  for determinism (anchor coords byte-stable offline); `resolved_place_ref` still left `None` (identity
  stays RESOLVE's). Reads only the coordinate fields, never `proximity_radius_m`/`distinct_from`. The
  withheld "Chaklala" alias is absent from the seed → never hits → RESOLVE earns it. Principle: config-
  driven + reproducibility. Rejected: Nominatim-only at INGEST (loses offline byte-stability for anchors).
  `md/13`, RESOLVE note. → enrich `md/13`'s "Stage A/B split" tail with the coordinate-cache refinement.
- **The gazetteer key normaliser is a LOCAL byte-identical copy of RESOLVE's `normalize()`, pinned by a
  test — not an import.** RESOLVE is `not-started`/unmerged, so importing `chanakya.resolve.normalize`
  would break this branch's CI and force a merge-order dependency (master §2 Rule 2: "merge order is
  irrelevant"). The copy (transliterate → casefold → collapse non-alnum → strip, driven by
  `config.resolution.transliteration`) is pinned by `test_gazetteer_key_matches_resolve_normalize_spec`
  so a drift is caught. Rejected: the direct import (breaks the branch now) and a lazy-import-with-fallback
  (nondeterministic keys). → when RESOLVE lands, dedupe both to one shared module (a small follow-up).
- **`extract(images=…)` is an ADDITIVE, backward-compatible protocol change.** Principle: don't churn
  siblings (master §2 R3). `images` defaults empty and is passed to the client ONLY when non-empty, so a
  pure-text source calls `extract` with exactly the old signature (text-only client doubles need no
  change). `read_image` stays for the standalone-imagery lane. Rejected: a separate multimodal method
  (duplicates the seam) or requiring every client double to add the param.
- **`pymupdf` added to core deps (AGPL-3.0, flagged).** Sanctioned by master §2 R1 (pyproject is the one
  shared file where additive dep lines are welcome). AGPL is fine for a hosted take-home (not distributed
  as a product) — flagged for the design note (`md/16`). Rejected: `pdfminer.six`+`pypdf` (permissive but
  loses one-lib page rendering, the whole point of the multimodal path).
- **Default Gemini model `gemini-flash-latest` (was `gemini-2.5-flash`, now new-user-404).** Live testing
  surfaced that the pinned `gemini-2.5-flash` returns "no longer available to new users"; the floating
  `-latest` alias tracks the current flash so a stale pin never dead-ends live extraction. `model_id` stays
  overridable. `md/07`. Also: `AZURE_ENDPOINT`/`AZURE_API_KEY` accepted alongside `AZURE_DOCINTEL_*` (the
  project `.env` names). Recorder geocoder defaults offline (deterministic re-record); the CLI builds the
  live gazetteer→Nominatim chain (`--offline` restricts to the gazetteer).

### HITL — Adjudication service + writeback + cards (choice · principle invoked · alternative rejected)
- **`reject` = forced demote (`set_status→probable`) for now; no F0-amendment.** *(User decision
  2026-07-18.)* Principle: demo-reliability + don't unilaterally change a shared contract siblings read.
  Rejected: a `reject-claim` effect that excludes a claim upstream of scoring so the status machine
  recomputes confirmed→probable — that needs rebuild to drop a decision-named claim before the stages (an
  F0-amendment). **Deferred:** the machine-recompute variant, re-verified end-to-end at EVAL / a later pass.
  → `controlpoints.build_status_override_item`.
- **HITL never mutates the view — writeback only *appends* a `DecisionRecord`; the next `rebuild()` applies
  `effects`.** Principle 5 + gate G12 (propagation is structural, not a fan-out). Rejected: per-stage code
  that edits graph state on disposition. → `writeback.py`.
- **Deterministic disposing path (G1/G2): no LLM/network/clock/RNG; `event_id` derived from
  `(item, chosen option)`, `ts` supplied by the caller.** Principle 4/11. Rejected: `datetime.now()`/`uuid`
  inside writeback (would break byte-identical replay). The triage-rank rubric LLM is **offline** and enters
  only as a pre-baked, replayed `frozen_rank` (data) — never a live call. → `writeback.py`, `triage.py`.
- **Recall-biased triage: auto-proceed requires *positive* safety on confidence AND materiality AND
  novelty; any unknown (`None`) escalates.** Principle: hold recall of escalation ≈ 1.0 — never silently
  drop. Rejected: a precision-first gate that lets unknowns auto-proceed. → `triage.should_escalate`.
- **★ pinning + LLM-raise-only are enforced *structurally* in `order_queue`:** pinned items lead (fixed
  priority, ignoring the rank), unranked items are retained (never dropped), unknown ids are ignored (never
  injected). Principle: finite analyst attention + LLM proposes, never authorities. Rejected: trusting the
  LLM rank to order the whole queue (could bury/remove a real item or move the escalate boundary). →
  `triage.order_queue`.
- **`TriageConfig` is HITL-owned + overridable, not a new shared config section.** Principle 9
  (config-driven) + keep the F0-amendment surface minimal. Rejected: adding a `triage`/`hitl` section to the
  shared config store (an F0 config-schema amendment for a module-local knob). *(hitl/ is outside gate G6.)*
- **Per-option `effects` preview on the item; writeback records the chosen option's effect verbatim.**
  Principle 5 — what the analyst was shown is exactly what is logged. Rejected: re-deriving effects at
  writeback (silent divergence from the preview). → `queue.build_item`, `writeback.build_record`.
- **Integrity flag stays within F0's effect vocabulary (single-element `add_integrity_flag`) and also
  carries a `flag_origin` intent (`primary_origin_id` + co-referring set).** Consistency with the `reject`
  call (no F0-amendment) + honest scoping: co-referring claims sharing one origin support the *same* resolved
  element, so flagging it propagates on rebuild today. Rejected: origin-keyed fan-out inside `rebuild()`
  (F0-amendment). **Deferred / flagged:** SCORE does the fuller per-claim penalty incl. *future* claims of a
  flagged origin — until then, a flag doesn't auto-taint claims that arrive *after* it (a monitoring-grade
  gap). → `controlpoints.build_integrity_flag_item`.

**Design-doc tails to enrich (flagged per the working agreement):**
- `sessions/HITL.md` acceptance #1 — note `reject` is forced-demote for now; machine-recompute via
  claim-exclusion is deferred (would be an F0-amendment) and re-verified at EVAL.
- `spine/05` / `spine/08` §3.11 — note the analyst integrity-flag propagates at the *element* level via
  F0's `add_integrity_flag` for the demo; full per-claim + future-claim origin fan-out is SCORE's.
- **Flag to EVAL:** re-verify (a) status recompute (reject→confirmed→probable via the machine) and
  (b) integrity origin fan-out end-to-end once SCORE lands.

### SCORE — Confidence Resolver + Sufficiency/Known-Gap + materiality (choice · principle · alternative rejected)
- **Freshness reference "now" = an explicit `as_of` config input, resolved clock-free** (pinned ISO date /
  API-stamped `now` at the request edge / else the newest available claim date). *Principle 11
  (reproducible/deterministic) + principle 5 (auditable replay)* — a wall clock inside `rebuild()` would
  break G1/G2 and make a past assessment unreplayable. **Rejects** reading `date.today()` in the reduction.
  A **past `as_of` also rewinds the graph** (hides claims not yet available then — an honest point-in-time
  "what did we know when"). *User-approved 2026-07-19.*
- **`adversary_denial` = gate; `decoy_risk` = single-pass-conditional gate — neither is a multiplier.**
  Adversary-denial: excluded from grouping AND caps at probable, always. Decoy: caps a *single-pass* look at
  probable, but a **second independent, clean look resolves it** → confirmable. *Principle 6 (confirmed is not
  probable)* + it reconciles spine/04's "single-pass basing cannot confirm" with the INGEST attribution-
  inference net-effect **and** keeps gate G7 satisfiable (a `decoy-risk` flag never rides a confirmed element).
  **Rejects** an unconditional decoy cap (would forbid the hero IMINT+text confirmation).
- **Inference claims share their premises' independence group** (derivation ≠ corroboration). *Principle 4
  (never fabricate corroboration)* — "I see a cylinder" + "that cylinder is an HQ-9" is one look, not two.
- **Pipeline reorder `check → assign_status`** so the status machine reads sufficiency, enforces it in the
  confirmed gate, and owns the `insufficient` label (assessability ⊥ magnitude). *Principle 4 (the
  non-negotiable is structural)* — **rejects** the post-machine reconciliation that could leave a
  confirmed-but-insufficient element (a G7 hole). `AssertionInput.sufficiency` is F0's frozen channel for it.
- **UNKNOWN substitutability renders as *candidate* + a first-class Known Gap, never a confirmed sole-source**;
  a `known-alternate` carrying `adversary_denial` is discounted (can't dissolve a real chokepoint); an
  all-inferred nomination is capped at candidate (#7). *Principle 4 (absence of evidence ≠ evidence of
  absence — the disqualifying line)* — **rejects** printing ignorance as a dependency.
- **All resolver knobs live in config, never code (G6):** `decay_base`, `min_independent_groups`,
  `same_class_weight`, `pdq_recycled_hamming`, `aligned_bias_vectors`, `disciplines`, `gated_attrs` added to
  `credibility.yaml`. *Principle 9 (analyst-tunable, config-driven)* — **rejects** hardcoded thresholds.

**Contract amendments:** F0-amend **#18** (`f0/score-amendments`) — `CredibilityConfig.as_of`, `chanakya/timeref.py`,
`score_claims(…, decisions=None)`, rebuild rewind-filter + `apply_claim_exclusions` + `deception_gate_flags`
(all additive/optional, golden byte-identical). The `check→assign_status` reorder rides in the SCORE PR (#20)
as a view-internal reconciliation. Both logged in PROGRESS.md → "Contract amendments (SCORE)".

**Open questions closed (moved from §3):** freshness-reference "now" mechanism (→ config `as_of`); the
chokepoint honesty fork stays at query-time (ASK) while precompute keeps the confirmed/candidate partition +
three-state `substitutability_state` faithful (never a single collapsed count).

### INGEST — attribution proposer (VLM shape → variant inference) (choice · principle · alternative rejected)
- **Offline, connection-triggered proposer over the *previous frozen resolved view*, upstream of append, never
  reachable from `rebuild()` (G1).** New module `ingest/attribute.py`, sibling of `imagery.py` (which
  `view/pipeline` never imports → structurally G1-safe); reuses imagery's corroboration machinery
  (`SignatureCorroboration`/`_corroboration_prompt`/`_corroboration_eligible`) at a *new trigger*. Built as the
  general engine (sweeps every `basing_site`, budget-capped, skips logged) per user's scope call. Rejected: a
  thin single-beat hardcode; emitting the inference at extraction time (the imagery precedent — dead code from
  the main lane, and it can't see the co-location that only exists after resolution).
- **D copies the textual claim C's exact `(subject,predicate,object)` — inverting imagery's hardcoded
  `site→variant`.** Co-location keys on the resolved triple, so D and C must be byte-identical to land on one
  edge (the "second look"). Copying C's already-resolved strings makes this hold **even under the current
  identity-resolver stub**. Rejected: reusing imagery's orientation (lands on a *different* edge → silent
  no-corroboration). **Root-cause flagged out of lane:** a canonical edge-direction-at-write invariant (fixes
  the whole class, incl. two text sources disagreeing) → `tmp/conv/INGEST-canonical-edge-direction-at-write.md`;
  once it lands the copy-C workaround is removed and `imagery.py`'s backwards inference is flipped.
- **D cites BOTH the image region AND the literature line (a `doc_ref` list).** G4 "one click to truth" for a
  two-source inference; extends the imagery precedent (image-only). → `attribute._build_inference`.
- **Decoy signal carried as both `decoy_risk` and `decoy_risk_flag`; `premises=[A,B]` is the SCORE grouping
  signal.** SCORE reads `decoy_risk_flag` on the assembled edge and unions `{A,D}` via the premise link (so an
  inference never corroborates its own premise). `single_pass`/`fingerprint_match`/`attributed_variant` are
  provenance-only. **SCORE confirmed** it does the grouping (`_derivation_linked`) + a **single-pass-conditional
  cap** (fires only at <2 independent looks — G7-safe: lone pixel→probable, pixel+independent text→confirmed).
  → `tmp/conv/INGEST-to-SCORE-inference-decoy-and-grouping.md`.
- **Convergence gate: an observation already used as an inference premise is skipped.** Makes the standing
  enrichment pass idempotent (real work once, silence on re-runs). The premise link does triple duty: audit
  trail + don't-double-count + already-done. Rejected: re-proposing every rebuild (duplicate inferences, wasted
  LLM calls, never converges).
- **Config knobs under `credibility.yaml: attribution_proposer` (`extra="allow"`), model id from the client.**
  No F0-amendment (mirrors `resolution.yaml`'s `llm_candidate_gen`); absent block ⇒ dormant, no code-literal
  defaults (G6). Rejected: a 9th `CONFIG_SECTION` (an F0 contract change for a proposer's tunables).
- **Fingerprint (clause c) searched on the variant + 1 hop; reference classes are the real source_types.** The
  ontology puts fingerprint attrs on `component`/`unit`/`basing_site`, never the `variant` type, so B is reached
  within one hop (`equips`/`inducted-into`). `reference_source_classes = [curated-register, think-tank,
  trade-media]` — there is no `reference` source_type. Corrected in the DATA handoff.
- **Keyless / unconfigured ⇒ an empty run (honest refusal, never a guess); KEYLESS≡LIVE via a frozen recorder.**
  `freeze_bundles` writes `*__attr.json` bundles the keyless boot materialises; a one-line prune guard in
  `seed.extract_corpus` preserves them across a re-record. → `attribute.freeze_bundles`, `seed.py`.

**Cross-lane coordination filed (tmp/conv — INGEST does not self-fix corpus/credibility):**
- **DATA:** author the HQ-9 TEL site-geometry fingerprint reference doc (B, reachable from the variant) + a
  clean variant→site textual C at Rahwali → `tmp/conv/INGEST-to-DATA-attribution-fingerprint-doc.md`.
- **SCORE:** decoy-attr→edge promotion + `{A,D}` independence grouping (both confirmed done) →
  `tmp/conv/INGEST-to-SCORE-inference-decoy-and-grouping.md`.
- **Extraction lane + F0:** canonical edge direction at write → `tmp/conv/INGEST-canonical-edge-direction-at-write.md`.

**Design-doc tails to enrich (flagged per the working agreement):**
- `spine/07` / `md/15` §2.4 — the signature→variant bridge now also runs as an *offline, connection-triggered*
  enrichment over the frozen view (not only per-frame at ingest); note the trigger + convergence.
- **Working agreement added to `CLAUDE.md`:** talk to the user (orchestrator) in plain/intuitive language —
  no verbatim code/schema in chat; depth stays in files, design docs, and handoff notes.

### DATA — Attribution fingerprint doc (d25) + claim-level oracle (choice · principle · alternative rejected)
- **The attribution reference (leg c) is a real figure/doc the VLM reads into a prose `signature_geometry`
  string — the two sides need only be "similar enough for a human to compare", not one schema.** *Principle 9
  (config-/LLM-driven, not rigid) + principle 7 (defensible > clever)* — an LLM judges the image's shape
  tokens against the reference prose, so a string carries it; a "cover these features" **prompt** (not a
  rigid structured schema) supplies the what-to-include and generalises across technical docs. **Rejects**
  forcing the reference into the image's structured shape schema (over-engineered; a rigid token match would
  over/under-fire on the deliberately-ambiguous decoy frame). *User-approved 2026-07-19.*
- **d25's figure is a deterministic labelled recognition schematic, NOT a real Esri overhead.** *Principle 11
  (reproducible) + don't manufacture a false trap* — reusing the real HQ-9 petals (Xi'an→d07, Lanzhou→d17b)
  collides under the PDQ recycled-image detector and falsely fires the M4 recycled trap reserved for the
  parade chain; an arbitrary fresh HQ-9 coordinate is landscaped/ambiguous. A schematic is the authentic
  recognition-literature genre and encodes the real published geometry. **Rejects** a relabeled real frame
  for the reference. Disclosed in `md/16`.
- **`source_type: curated-register` (not `reference`).** *Principle 4 (fail-closed — never fabricate
  credibility) + config-consistency* — `reference` is absent from `source_class_factors`, so SCORE scores it
  **R=0 (fails closed)** and the inference can't clear probable; `curated-register` is in **both** the rubric
  (R≈0.85) and the proposer's `reference_source_classes` (which INGEST/#21 set to `[curated-register,
  think-tank, trade-media]`). **Rejects** `reference` (unscored); curated-register is the cleanest register
  semantics and fail-safe (d25 would also qualify as think-tank, but that class scores lower and is broader).
  *SCORE + user-confirmed 2026-07-19.*
- **No corpus re-orientation of `based-at`; the proposer hops unit→variant, so unit-subject C works and D
  lands on the existing unit-at-Rahwali edge.** *Principle 7 (don't re-model what the code already handles) +
  preserves the unit×site-keyed supersede/anti-spoof lesson* — the INGEST→DATA doc's "C must be
  variant-subject" overstated the requirement (`_variant_via_hop` recovers the variant; identity rides as
  `attributed_variant`). **Rejects** a parallel variant-subject `based-at` edge or a new news doc; **d19
  stays the independent look**.
- **Claim-level oracle added for inference D** (`answer_key → attribution_inference`): premises [A,B], both
  doc_refs, decoy attrs, resolved triple, group-{A,D}/independent-d19→confirmed. *Principle 5 (traceability) +
  principle 4 (the braked single pixel-read is the point)* — the first claim-level gold in an otherwise
  doc-level oracle, for the INGEST determinism test.

**Handoff:** `tmp/conv/DATA-to-INGEST-fingerprint-doc-DELIVERED.md` — the one BLOCKING code-side wiring
(extraction attaches `signature_geometry` to a *floating* `basing_site`; it must land on a variant-adjacent
node — recommended `observable_fingerprint` on `comp_tel_chassis` via `equips`), the reading-prompt checklist,
the figure/multimodal path, and the proposer config knobs to verify. **FYI drift:** d22/d24 `source_type:
think-tank` vs `source_class: "reference"` label mismatch (cosmetic, unrelated to firing).

### API — FastAPI layer over the merged Wave-1 modules (choice · principle invoked · alternative rejected)
_(2026-07-19, `feat/api`. The thin HTTP layer — master §4.8. Full detail: PROGRESS "API" handoff note.)_
- *Thin API, delegate the LLM* → `/ask` + `/ingest` are the only LLM-touching endpoints, and only by
  delegation to ASK / INGEST; the API adds no reasoning and imports no `anthropic` at module load
  (`create_app` lazy-imports `fastapi`, keeping `import chanakya.api` side-effect-free). *Rejected:* the
  API re-deriving any stage logic.
- *One owner of the held view + alert feed* → a single `AppState.rebuild_and_swap()` is the sole
  in-process mechanism behind hot-config / live-ingest / HITL propagation (atomic swap, MONITOR fired on
  the delta, wall-clock `fired_ts` stamped by the API so `evaluate` stays deterministic — G2). The keyed
  ingest lane runs with `live_rebuild=False` so it never rebuilds a view the app doesn't hold. *Rejected:*
  letting the lane rebuild internally (double rebuild + a divergent view).
- *`/ingest` is a sync `def`* → the lane runs its own `asyncio` fan-out; an `async` route would call
  `asyncio.run` inside the running loop and crash. FastAPI threadpools a `def` route, so many users ingest
  concurrently. *Principle:* honour how the merged code actually behaves. *Rejected:* an `async` route.
- *Honest keyless boot* → boot seeds from committed bundles if present, else stands up an **empty** graph
  the analyst fills via `/ingest` — never a fabricated corpus (the non-negotiable). The seed is
  source-agnostic, so SHIP's baked baseline / DATA's extracted bundles drop in with no code change.
- *Public-demo cost guard* → keyed live extraction is gated by `CHANAKYA_ENABLE_EXTRACTION` (default off);
  visitors land on the instant keyless bundle path (Gemini quota/rate-limit protection). *Rejected:*
  always-on extraction (cost/abuse exposure on a hosted demo).
- *Structural HITL only (G5/G12)* → no endpoint sets status directly; `dispose` appends a `DecisionRecord`
  and the following `rebuild()` applies its effects. The card is reconstructed from live view state (no
  queue endpoint in §4.8). Demote/promote step one level along the confidence ladder. *Rejected:* mutating
  node status in the handler.
- *One-click-to-source needs the atoms* → **F0-amendment** `ProvenanceDrawer.claims: list[ClaimRecord]`
  (additive) so the drawer embeds each cited claim with its exact `doc_ref`. *Rejected:* a new lean claim
  projection (2nd shape) / a per-claim endpoint (N+1, beyond §4.8). Plus **F0-amendment**
  `IngestRequest.source_type` (the keyed lane needs the source credibility class). Both additive/optional;
  logged in PROGRESS + `tmp/conv/API-to-FRONTEND-contract-log.md` (user-approved "best decision + inform
  the frontend via the contract log", 2026-07-19).
### EVAL — RCA fix-plan ratifications (choice · principle invoked · alternative rejected, 2026-07-19)
- **D-A — Edge-vocabulary collision fix (Phase 1/2).** Keep the ratified edge-type names; add declared
  domain/range (from-type→to-type, plus a symmetric flag for same-as/distinct-from/substitutable-by) to
  every edge in `config/ontology.yaml`; constrain the extractor to emit only predefined edges via a
  Pydantic enum on the extraction output schema; and add a deterministic write-time re-laning validator
  that maps each fact onto the correct edge by its **endpoint types** (Variant→Unit ⇒ inducted-into,
  Mfr→Component ⇒ supplies-component, Component→Variant ⇒ equips), rejecting/flagging any fact whose
  endpoints match no edge instead of minting an ad-hoc predicate. *Principle 9 (config-driven &
  extensible, not hardcoded) + principle 10 (model to what the queries need).* **Rejects** renaming the
  edges to match natural English — the directional ambiguity is inherent to the words (renaming doesn't
  fix it without domain/range), and it would force re-syncing `answer_key.json` + `C/01` + the design note
  days before the demo for cosmetic gain. Owners: DATA-C + ARCH (vocab + domain/range, Phase 1); INGEST
  (enum + write-time re-lane, Phase 2). → `tmp/conv/eval-rca/00-RCA-index.md` Phase 1/2.
- **D-B — Entity canonical-id registry (Phase 1, consumed Phase 3).** Introduce an entity registry
  mirroring `config/places.yaml` — `{canonical_id (== the oracle id), type, canonical_name, aliases[]}` —
  as the standardization/traceability id space. The extractor does not resolve names to canonical ids; it
  emits surface form + type only. RESOLVE owns surface→canonical mapping via alias-equivalence (seeded ∪
  learned) + fuzzy name + attribute/relational scoring; the alias table is a growing prior — auto-merges
  and HITL-accepts replay from the decision log into the effective alias set. Open-world: an unknown
  entity still mints a node. *Principle 9 (config-driven/extensible) + the HITL learning loop.* **Rejects**
  surface-form-only ids (status quo) — the cause of the id-namespace split. Owners: DATA-C (registry
  content, Phase 1); RESOLVE (consume into canonical node ids + band recalibration + containment/head-token
  bootstrap, Phase 3). → `tmp/conv/eval-rca/00-RCA-index.md` Phase 1/3.
- **D-C — Eval matching contract + id-unification target.** The eval harness matches view→oracle by
  name+type overlap, not id-exact — a deliberate, temporary bridge, because the golden `answer_key`'s
  hand-assigned ids and the ids RESOLVE currently mints are two different namespaces (Master A,
  `eval-rca`). Target state: one unified id namespace, where the registry's canonical ids (D-B) are used by
  resolve-minted nodes, subject-lens anchors, and observables **and** — via a separate answer_key
  reconciliation task — the golden output too, at which point eval can match by id and the bridge retires.
  *Principle: make the system work now + traceability.* **Rejects** forcing id-exact matching today
  (pushes brittle id-election guarantees into Phase 3 prematurely). Owners: EVAL (bridge); DATA-C/EVAL
  (answer_key reconciliation — a separate follow-up task, not Phase 1). →
  `tmp/conv/eval-rca/00-RCA-index.md`.

### INGEST + F0 — canonical edge direction at write (choice · principle invoked · alternative rejected)
_(2026-07-19, `feat/ingest-canonical-direction`. Implements the write-time direction/re-lane half of the
EVAL RCA **D-A** decision above — the ontology `from`/`to`/`symmetric` fields + a deterministic endpoint-type
canonicalizer — for the corroboration-co-location case; the two decisions converged independently.)_
- **One canonical direction per relationship type, enforced at claim-production, with a read-side net as a
  fallback.** Two claims corroborate only on the *same* edge (keyed by the resolved `(s,p,o)` triple), so
  oppositely-phrased claims of one fact ("unit at site" vs "site hosts unit") silently split into two edges and
  never corroborate. Fix writes every producer's claim in the same direction. *Principle:* provenance/audit
  integrity — a backwards claim is a *wrong record*, so fix it at write, not on every read. *Rejected:* read-only
  normalization (leaves the immutable log internally inconsistent); doing nothing (the silent failure the whole
  confirmed-vs-probable machinery depends on). **User call (options template):** write-side **+** a read-side net.
- **Direction promoted from ontology comments to machine-readable `from`/`to` (+ `symmetric`) YAML fields; read
  via `getattr` — no F0 schema-file change.** `TypeDef` is `extra="allow"`, so the fields ride as extras (exactly
  as the handoff prescribed). *Principle:* config-driven/extensible, not hardcoded; minimise the F0 contract
  surface (keeps off the F0 worktrees' `config_models.py`). *Rejected:* adding typed fields to `TypeDef` now (an
  F0 contract edit + cross-worktree conflict risk for a purely additive knob) — trivial follow-up if wanted.
- **Endpoint typing reuses the doc's own entity claims + the place gazetteer; genuine unknowns are left as
  written.** No extractor prompt/schema change. *Principle:* deterministic (G1/G2), minimal LLM surface, no
  re-record churn. *User call:* chose "reuse in-doc types + gazetteer" over "also tag endpoints in the extractor".
- **Score-based orientation: flip only on positive type evidence, never guess.** Handles polymorphic-object
  edges by declaring only `from` (`manufactures`, `sustained-by` — the fixed end alone detects a flip) and leaves
  same-type edges (`component-of`) and value-object triples (`object_value` set) untouched. *Principle:* the
  non-negotiable — never fabricate/mangle where evidence is ambiguous. *Rejected:* a strict both-ends-required
  rule (misses polymorphic edges); relabeling predicates (there's one directional predicate per relationship —
  re-ordering endpoints is the whole correction).
- **Shared pure module `chanakya/edge_direction.py` (imports schemas only), called by both the ingest lane
  (`_finalize`, before dedup) and `rebuild()` (before `resolve`).** *Principle:* gate G9 — `ingest` must not
  import `view`, and `view` must not drag the extraction client, so the canonicalizer lives in a neutral module
  both import. No-op on an ontology with no declared directions ⇒ golden fixtures byte-stable (G2), no
  re-record needed (user: nothing frozen into the graph yet, so no cleanup).

**Cleanup deferred (user: no cleanup this pass — graph is empty):**
- `imagery.py`'s hardcoded `site→variant` inference and `attribute.py`'s copy-C workaround are now *unnecessary*
  but left in place; the canonicalizer is conservative and won't mangle them. Simplify when convenient.

**Design-doc tails to enrich:**
- `spine/01`/`spine/02` — the sourced-claim unit now carries a **canonical edge-direction invariant** at write;
  edge identity is orientation-free. `spine/08` — record the `from`/`to`/`symmetric` ontology fields + the
  two-placement (write + read-net) enforcement.

- **RCA-fix hub.** Build-time sub-decisions (manufactures tightening D-A.1; the re-lane provenance rule
  D-A.2; registry-as-open-world-prior D-B.1; the foreign_control/materiality-seeding deferral D-C.1; and the
  keep-Phase-1-self-contained reconciliation with INGEST's uncommitted `edge_direction.py`) are logged in
  `tmp/conv/eval-rca/RCA-FIX-DECISIONS.md`; phase tracking + the handoff index in
  `tmp/conv/eval-rca/RCA-FIX-PROGRESS.md`. Phase 1 shipped on branch `fix/phase1-edge-vocab-and-entity-registry`
  (PR #29). **Reconciled with the INGEST block above:** Phase 1 promoted `from`/`to` to *typed* `TypeDef`
  fields (the "trivial follow-up" that block deferred) + added `symmetric`/`extractor`, and tightened
  `manufactures` to Mfr→Variant; `edge_direction.py` (direction) and `chanakya/ontology.py` (predicate
  re-lane) are complementary and both read the same ontology `from`/`to`.

---

## INGEST — in-document coreference clustering, pass 1 of 2 (2026-07-19, `feat/ingest-coref`)

Implements the **INGEST half** of `tmp/conv/INGEST-RESOLVE-in-document-coreference-clustering-PROPOSAL.md`
(Option B, derived overlay). Scope set by the user: **emit + persist only** — RESOLVE honouring the clusters
is a deliberate follow-on ("reconcile RESOLVE to the new INGEST thing"). Handoff:
`tmp/conv/INGEST-to-RESOLVE-coreference-handoff.md`.

**Trigger satisfied empirically (the proposal's own go/no-go).** On the rebuilt view, **86 of 258 nodes
(33%) are `unknown`-type dangling relation endpoints** — including `CPMIEC` / `China Precision Machinery
Import-Export Corporation`, `BIRM` / `Beijing Institute of Radio Measurement`, `CASIC` / `China Aerospace
Science and Industry Corporation`. The coreference leak the proposal predicted is real and large, so this
was built on measurement, not on the argument alone.

- **The cluster rides its own predicate `coref-same-as`, NOT `same-as`.** *Principle:* "don't route a
  decision made with more information through a layer that has less." `resolve.scoring._IDENTITY_PREDICATES`
  already weighs `same-as`/`aka`/… as **one term of `merge_score`**, so writing the cluster there would
  silently dilute a context-licensed extractor decision into a partial score that attribute-dissimilarity
  can outvote — i.e. exactly the option the proposal rejected. On its own lane it is provably inert to
  today's scorer (asserted in `test_coref_lane_is_inert_to_the_resolvers_merge_scoring`), so this slice
  changes **no** merge behaviour, and the eventual honor policy keys on a signal that cannot be confused
  with ordinary identity scoring. *Rejected:* a bare `same-as` triple (dilution, above); a new first-class
  cluster record in the F0-owned schema (cleaner model, but cross-lane blast radius through store+rebuild
  for a slice nothing consumes yet — user chose the reversible option).
- **Pass 2 lives inside `extract_document`, not the lane.** *Principle:* KEYLESS ≡ LIVE. Both callers — the
  live lane and `seed._extract_source` (the frozen-bundle recorder) — go through `extract_document`, so they
  inherit the pass in lockstep and offline can never drift from live. It cannot live in `_finalize`, which is
  the pure no-LLM pass (gate G1).
- **DORMANT BY DEFAULT** (block commented out in `config/credibility.yaml`). *Principle:* don't pay a cost
  with no payoff. Enabling costs a **second extraction call per document** and re-records every frozen
  bundle, while nothing consumes the clusters until the honor policy lands. Turn it on *with* that policy.
  An explicitly empty `categories: []` means dormant, never a silent fall-back to "all".
- **Undeclared endpoints are typed from the ontology's edge domain/range.** *Principle:* keep the rail
  biting where it matters. Most real coreferent mentions reach the graph *only* as relation endpoints, so
  typing them `unknown` would disable the same-type rail exactly where it is needed — a caught bug: a
  proposal merging `CPMIEC` with `HQ-9/P` was accepted until `manufactures` (manufacturer→variant) typed
  them apart.
- **`kind` follows what the claim can cite:** `inference` with `premises` naming the member mentions when a
  member is a declared entity; `observation` when the whole cluster is undeclared endpoints (no upstream
  claim exists to cite, and an explicit "… (CPMIEC)" equivalence is something the document *states*).
  *Principle:* report what a claim actually rests on — inventing a premise to keep one uniform kind would be
  a provenance lie. Dropping such clusters instead was tried and rejected: it silently discards the dominant
  real-corpus case.
- **Mention-keyed provenance on every relationship claim** (`_subject_mention`/`_object_mention` → the entity
  claim that named each endpoint, alongside the verbatim surface string). User explicitly pulled this into
  this slice. Additive and inert (today's rebuild reads the strings), but it means a later split has each
  relation already anchored — zero re-inference. The refs are **positional**, so `edge_direction` swaps them
  whenever it reorients a triple, and one shared `dedup.remap_claim_refs` now rewrites *every* cross-claim
  reference (premises, targets, mention refs) in all three id-reassignment paths — so a new reference type
  can't be added in one path and silently dangle in another.

**Known limitation (surface in the design note):** a "mention" is keyed by surface form *within a document*,
because pass 1 already collapses same-name mentions per document. The proposal's per-occurrence mention ids
are therefore approximated — one document using one string for two different entities is not separable. This
is an under-reach, never an over-merge.

**Design-doc tails to enrich:** `spine/02` — extraction is now **two passes** (fill, then in-document
coreference), and the claim carries mention-keyed endpoint provenance. `spine/03` — RESOLVE gains a
prospective authoritative in-document signal that shortcuts the attribute scorer (pending the honor policy).

---

## RESOLVE — honouring in-document coreference, pass 2 of 2 (2026-07-19, `feat/ingest-coref`)

Completes the coreference feature by reconciling it with the **post-Phase-3** resolver (PR #35). Handoff +
the full before/after numbers: `tmp/conv/INGEST-to-RESOLVE-coreference-handoff.md`.

**Reassessment first — the case for this feature shrank, and that is recorded rather than glossed.** Phase 3
took `unknown` nodes 86 → **3** and merges 5 → **53**, resolving `CPMIEC`, `BIRM`/`Beijing Institute of Radio
Measurement` and `CASIC` deterministically via endpoint-as-mention + a containment/acronym bootstrap. Those
were the motivating examples in the INGEST-half decision block above; **a deterministic rule beats an LLM
pass wherever it reaches the answer**, so the honest residual is narrower: of the 9 remaining queue pairs,
~4 are genuine equivalences a quote could settle (two of them *descriptive ↔ designator* pairs sharing no
token — the slice no string method can reach) and 5 are traps that must stay apart.

- **`EXPLICIT_EQUIVALENCE` may bootstrap; `NAME_VARIANT` / `UNAMBIGUOUS_ANAPHOR` stay raise-only.** *User
  decision (options template).* This knowingly crosses Phase-3's **D-2.5** raise-only rule for one narrow
  category, justified because a coreference claim is *not* an ordinary identity assertion: it is a reading
  of one document's own discourse that must **quote the licensing span**. What the document *states* can
  merge; what the extractor *interprets* goes to a human. *Rejected:* full authoritative (reverses D-2.5
  outright and puts anaphora — the riskiest category — into automatic merging); pure raise-only (safe, but
  silently clips the proposal's thesis).
- **Opt-in via `resolution.yaml → coref_authoritative_evidence`, empty by default.** *Principle:* config-
  driven, and shipping a producer must never change anyone's topology by itself. "How much authority does
  the extractor's in-document reading carry" is an operator decision, not a code literal.
- **Authoritative ≠ unconditional.** A stated/configured `distinct-from` **drops** the pair; a type,
  namespace, or hard-attribute contradiction **demotes** it to the analyst queue rather than deleting it —
  the evidence still reaches a human. `scoring.has_hard_conflict` deliberately reuses the scorer's own
  `attribute_rules`, so "what counts as a contradiction" has one definition. Absence ≠ disagreement.
- **It joins the bootstrap, not the fixpoint.** *Principle:* put like with like — the bootstrap is where
  direct, high-precision identity statements already live (shared hard-ID, alias equivalence, exact name,
  containment/acronym), and it runs the same veto checks. The fixpoint's `auto` band still structurally
  excludes the source-asserted term, so D-2.5's enforcement is untouched for every other signal.
- **Coreference is consumed, not drawn** (`view/pipeline._assemble`), exactly as `same-as` now is: identity
  is answered by merging or by a candidate edge, never by a third parallel edge.
- **`Edge` carries the claim's tier-3 bag** so a triple can say something about *how it was derived*
  without RESOLVE importing INGEST (which would drag the LLM client into `rebuild()`'s import graph).

**Verified end-to-end:** with both halves enabled, a document stating "… Corporation (CPMIEC)" merges *"the
export agency"* into it — two mentions sharing **zero** tokens, unreachable by containment, acronym or
alias — with the coref edge consumed and merge provenance on the node. 658 pass, ruff + mypy clean.

**Still OFF by default.** The RESOLVE knob is set but inert; enabling the INGEST producer costs a second
extraction call per document and re-records every frozen bundle — **coordinate with EVAL's re-record**.

**Design-doc tails to enrich:** `spine/03` — RESOLVE now has three identity channels (deterministic
bootstrap, raise-only proposals, and opted-in authoritative in-document coreference), and the bootstrap is
the documented home for direct identity statements.

### Amendment (same branch, pre-merge): shipped fully gated, and a demo collision found

- **`coref_authoritative_evidence` ships EMPTY, not `[EXPLICIT_EQUIVALENCE]`.** The policy decision above
  stands and is fully built + tested; what changed is the shipped *default*. Two reasons:
  1. **Independent switches.** The producer is dormant; a pre-set honor policy would mean enabling the
     producer silently switches auto-merging on in the same motion — a loaded gun, not two gates.
  2. **A concrete collision, found by going looking for one.** `d10_sat_cloud_gap` states *"HT-233 (H-200)
     engagement radar array"* — a textbook `Full Name (SHORT)` apposition, exactly what
     `EXPLICIT_EQUIVALENCE` is built to catch. But that orphan alias is a **deliberate demo beat an analyst
     is meant to earn** (`cluster._descriptor_extension` says so in as many words). Auto-merging it would
     have silently deleted the beat. *Not measured* — the producer is dormant, so this is an exact pattern
     match, not an observation; that is precisely why it must be measured before opting in.

  Raise-only turns out to be the *better* demo behaviour anyway: the pair reaches the analyst queue **with
  its licensing quote**, so the human still earns the merge but is handed the exact sentence that justifies
  it — triage plus citation, which is what the brief grades, rather than an automatic merge.

- **Order of operations when enabling** (all three, together, with EVAL): enable the producer → re-record
  bundles → measure the false-merge rate on the 6 frozen scenarios (HT-233/H-200 explicitly) → only then
  consider opting a category into `coref_authoritative_evidence`.

**Design-note disclosure worth carrying:** the strongest honest framing of this feature post-Phase-3 is not
"it finds merges" — Phase 3's deterministic rules absorbed most of that — but "it reaches the *non-lexical*
pairs nothing else can, and it hands the analyst a citation for the rest." A deterministic rule beats an
LLM pass wherever it reaches the answer; the LLM's value is the slice where no string comparison exists.

### QA-T7 — Phase-4 residual sweep (choice · principle invoked · alternative rejected, 2026-07-20)

Worked the deferred-defect register (`tmp/conv/RESIDUAL-FIXES.md`) one item at a time. Five items closed,
two deliberately left open with a written diagnosis. Every call below leaned on a stated principle.

- **Refusal prose names entities, never objects (R-9).** The "this lens has no basing site" refusal could
  render a Python list repr and the internal lens id into text an analyst reads. Now it renders node
  names, comma-joined, and drops the lens id; the machine-readable ids stay in the `missing` field the UI
  already resolves. *Principle: escalate to the analyst — which only works if what reaches the analyst is
  legible.* *Rejected:* adding a `label` field to the subject-lens config to humanise the id — a config
  schema change to another module's surface for one sentence of prose, when dropping the id reads better.

- **Supersede ordering compares intervals, not upper-bound strings (R-5, D-P4.4 iii).** A target's time is
  the **union** of its claims' intervals; disjoint-and-earlier orders, identical exact instants
  contradict, identical vague intervals are unorderable → `candidate_supersede`, any other overlap
  contradicts, and a missing bound is never guessed. *Principle: the fabrication non-negotiable +
  recall-biased triage — a vague date must not be allowed to win an ordering it cannot support, and the
  honest outcome of an ambiguous overlap is the HITL queue, not an arrow.* *Rejected:* keeping `max` over
  a target's claims with a precision tiebreak — it leaves the late-restatement reversal intact, which is
  the more dangerous of the two defects because it silently un-retires a fact an analyst already acted on.
  Verified the flagship Rahwali beat is byte-for-byte unchanged before accepting the change.

- **The answer key was NOT regenerated to fix the generator (R-8).** Removed the four dropped sustainment
  items and the stale flex from the scenario spec, then **stopped**: measuring the spec against the frozen
  key showed six further divergences a regeneration would destroy, including a block the generator cannot
  emit at all. *Principle: data issues go to `tmp/conv/` for the data agent, and keep the demo
  deterministic — an oracle rewrite three days out is exactly the class of change that breaks a frozen
  demo.* *Rejected:* regenerating and diffing "just to see" — the generator overwrites the key wholesale
  even for a single-document run. Handoff: `tmp/conv/QA-T7-answer-key-generator-drift.md`.

- **A flex that claimed corroboration it does not have was reworded (R-14).** The `deep_tier_confirmed`
  expectation described a single-bundle fact as "multiply attested". *Principle: the non-negotiable —
  never overclaim; "confirmed" is structurally separated from "probable" and must rest on a stated
  reason.* The `confirmed` grade stands on the evidence-gate argument (one source naming supplier +
  component + relationship directly), which is now what the text says. *Rejected:* downgrading the grade
  to match the wording — that would have punished a genuinely direct source for our own bad sentence.

- **The independence weight double-application was NOT fixed (R-11 / D-P4.14).** Diagnosis confirmed: the
  weight is applied to both the magnitude and the look-count, making the code stricter than `spine/04`.
  Left untouched and written up as four options with a measured blast radius (26 of 294 elements move;
  the flagship path does not). *Principle: borderline-harmful → ask first, with options; and a credibility
  retune must not ride along inside an unrelated change.* Decision note:
  `tmp/conv/QA-T7-independence-weight-decision.md`.

- **The mis-laned `equips` edge was diagnosed, not fixed (R-1).** Root cause: `relane()` is correct;
  it never saw a `unit → variant` fact, because at write time only the *variant* end was typed — the other
  endpoint string is typed downstream by RESOLVE. Confirmed no "frozen bundles agree with current lane
  logic" invariant test exists (the location renormaliser is the only such guard, and it may not touch a
  predicate). *Principle: keep the demo deterministic and reproducible — the fix needs a keyed re-record
  that could break the alias binding hop 2 depends on, so the diagnosis is worth more than the fix.*

**Design-doc tails to enrich:** `spine/04` — record that the independence weight is deliberately applied
twice today (stricter than the text) until D-P4.14 is decided. `spine/08`/`spine/01` — the write-time
re-lane can only use types the *current document* declared, so lane correctness for cross-document
mentions is bounded by extraction-time typing; the durable fix is either registry-backed endpoint typing
or a post-resolution re-lane pass.
---

## QA T3b — fragmentation & merge-noise (2026-07-20, `qa/t3b-fragmentation`)

Six defects behind one complaint ("multiple Karachi nodes stay fragmented"). Full root-cause /
measurement write-up in `tmp/conv/T3b-fragmentation.md`; data observations in
`tmp/conv/T3b-to-DATA-typing-observations.md`. Measured: merge queue **40 → 8** candidates cold
(41 → 8 full), nodes 171 → 166, nameless nodes 11 → 0, substantive edges unchanged at 56,
`make test` 788 → 808 pass.

- **D-T3b.1 — The Karachi cluster is answered by a TYPE distinction, not a merge.** An Army Air Defence
  *Centre*, an air-defence *sector* and a coastal *belt* are three different kinds of thing; the defect
  was offering them to the analyst as candidate duplicates, and merging them would have been the real
  error. *Principle: model the ontology to what the queries need + false-merge discipline (over-merge is
  the expensive error).* **Alternative rejected:** treating it as a recall problem and reaching for the
  coreference gate — T1 had already measured that as unable to touch a cross-document cluster.

- **D-T3b.2 — `area_of_operations` is a `refines:` refinement of `basing_site`, not a rival type, and
  the edges' `to:` is left alone.** Widening `based-at`/`observed-at` to a polymorphic range would make
  `endpoint_types` ambiguous and un-type every genuine site endpoint. The base type keeps doing the
  laning; the refinement is stamped from the instance's name by one shared pure function both RESOLVE and
  the view call. *Principle: config-driven & extensible, not hardcoded; one source of truth (the
  `edge_instance_key` precedent).* **Alternative rejected:** a second polymorphic range; also rejected a
  code-side type list.

- **D-T3b.3 — Area recognition is head-anchored (last token), plus a curated `named_instances` list.**
  A substring rule would have retyped the corpus's one pad-precise site ("Probable Long-Range SAM
  Emplacement, Malir District, Karachi, **Sindh Province**, Pakistan") into an area — the exact inverse of
  `md/13`'s precision spec. *Principle: precision-first; a rule that is wrong on the load-bearing case is
  not a rule.* **Alternative rejected:** substring matching on area words.

- **D-T3b.4 — A shared neighbourhood is not identity evidence for an area type
  (`identity.relational: false`).** Two areas that both contain sightings of the same equipment share a
  neighbourhood *by construction* — that is a fact about the equipment's dispersal. This is what removes
  `Punjab ↔ Sindh`. *Principle: the merge decision is precision-first; recall is candidate-gen's job.*
  **Alternative rejected:** a blanket "different names ⇒ never merge" rail for areas, which would have
  blocked genuine variants such as "Karachi AD sector" ≡ "Karachi air defence sector".

- **D-T3b.5 — Cross-type pairs leave the analyst queue, with a `raise_only` escape hatch.** The type gate
  `_identity_pairs` / `_name_containment` / `_coref_pairs` already apply was missing from the scored
  candidate loop. A pair a *source* or the offline proposer explicitly asserts still reaches the analyst,
  because a cross-type identity assertion is exactly what a human should see. *Principle: HITL is
  attention-triage — a queue full of type errors is not triage; escalate ambiguity, not noise.*
  **Alternative rejected:** a hard veto with no escape, which would have made the resolver unable to
  surface a genuine extraction mis-typing.

- **D-T3b.6 — Contradictory endpoint typing is settled by the ontology's domain/range, never by a guess,
  and the tie-break is attach-only.** Where the declared domain/range narrows the contradiction to exactly
  one admissible type, the designed schema decides; where it admits both or neither, the refusal stands.
  Attach-only because the first version *minted* a new short designator, which the containment bootstrap
  then over-extended and fused a TEL canister into a TEL chassis. *Principle: when unsure, escalate —
  don't guess; over-merge is the expensive, adversarially-exploited error.* **Alternative rejected:**
  picking the most-claimed type (a popularity guess); also rejected minting under the surviving type.

- **D-T3b.7 — A different bill-of-lading number is a hard veto, not a low score, and it stays DRAWN.**
  Three distinct bills in one customs manifest were mutual merge candidates with no deterministic guard;
  a wrong merge collapses two import events and silently corrupts the supply-chain count. Absence of an
  identifier is not disagreement (the `has_hard_conflict` doctrine). *Principle: deterministic rules
  dispose; an invisible veto is indistinguishable from a missing edge.* **Alternative rejected:** a
  scoring penalty — probabilistic where the evidence is categorical.

- **D-T3b.8 — The relational term is discounted by the evidence under it (`relational_support_k`).**
  A Jaccard overlap is scale-free, so a one-element neighbourhood scored a perfect 1.0 and a single shared
  hub edge was landing pairs at exactly `hitl_low`. The knob states the invariant in the same form
  `resolution.yaml` states its others: *a perfect shared neighbourhood must rest on at least two shared
  neighbours to reach the analyst on its own.* It only ever lowers a score, so it can never create an
  auto-merge. *Principle: no magic numbers in code — thresholds are config; precision-first merging.*
  **Alternative rejected:** raising `hitl_low`, which would have punished every signal to fix one; also
  rejected an inverse-degree hub discount as more machinery than the measured defect needed.

- **D-T3b.9 — A node's display name comes from the analyst's curated registry entry, not from whichever
  claim replayed first.** `unit_hq9b` rendered as "Pakistan Air Force" — its *operator* — so the demo's
  climactic beat read "Pakistan Air Force moved from Nur Khan to Rahwali". `entities.yaml` already carried
  `display_name: "the PAF HQ-9B fire unit"` and ASK already honoured it; only the view did not, so the
  graph and the answers disagreed about what one node is called. *Principle: never invent a designator
  the corpus does not support — surface the one an analyst already justified in config.* **Alternative
  rejected:** leaving the node unnamed (T6's fallback — right instinct, unnecessary once the registry was
  found to hold the answer); also rejected using `canonical_name`, which is an identity string carrying
  parenthetical notes, not prose.

- **D-T3b.10 — An untyped endpoint renders under the designator the document used.** Its id *is* the
  surface form, so the information was on the node all along. A name is a display concern and does not
  make the node resolvable — that was fixed at the typing layer, not here. *Principle: every claim is
  one-click traceable; a raw id in the UI is a traceability failure.*

- **D-T3b.11 — Retyping landed WITH the map config, not before it.** `place_entity_types` was unset and
  defaulted to `{basing_site}`, so retyping alone would have silently deleted T5's new map coverage. It is
  now stated explicitly, `place_allowed_precision_classes` gains the mirror row
  (`area_of_operations: [district, city, province]` — an area must never snap to a pad), and
  `_refine_node_types` runs *before* place matching so the two types can carry different precision gates.
  Verified before/after: identical locations, identical (absent) place refs. *Principle: don't silently
  clip scope; a fix that breaks another agent's landed work is not a fix.*

- **D-T3b.12 — The flagship worked query changed shape; the assertion was relaxed to a floor and the
  change surfaced, not silently re-pinned.** Fixing the fragmentation moved the chokepoint nomination from
  a *fragment* (`Type 305B`, which carries no supplier edge) to the resolved `comp_ht233`, which does — so
  the trace now reaches CPMIEC in 2 hops instead of stopping at a component in 3. That maker edge is the
  corpus's planted false attribution (d23, refuted by d22); the system labels it `insufficient` and closes
  on "insufficient evidence to assess", so the thread now *exercises* the misinformation trap rather than
  stepping around it. The cost is two ORBAT hops of narrative. *Principle: borderline-harmful → surface it
  with options, don't decide it unilaterally; a test that pins a shape turns a data improvement red.*
  **Escalated** with three options in `tmp/conv/T3b-fragmentation.md` §5.

**Design-doc tails to enrich:**
- `artifacts/spine/03-resolution.md` — the merge score now has a **support** notion: the relational term is
  proportional to the number of shared neighbours up to `k`, so "shared neighbourhood" means shared
  *neighbourhoods*, not a shared link. Also record that identity signals are now **type-aware**: a node
  type may declare that neighbourhood is not identity evidence for it.
- `artifacts/spine/01-graph-and-ontology.md` — node types can declare **refinements** (`refines:`), a
  narrower reading of a base type recognised from an instance's name, which is how the designed schema
  expresses a distinction an edge's declared range cannot.
- `artifacts/md/13-location-normalization.md` — the per-node-type precision table now has a structural
  counterpart: `area_of_operations` is the type for the "somewhere in Punjab" rung, with its own
  `place_allowed_precision_classes` row, and it renders as an envelope rather than a pin.
- `artifacts/md/16-design-note-disclosures.md` — worth a line: the graph was passing the d22-vs-d23
  false-attribution trap *by accident* (the false edge was parked on an orphan fragment). Fixing
  fragmentation exposed it, and the credibility layer then handled it correctly. That is a better story
  than the trap never being reached.
---

## QA T6 — the provenance drawer's semantics (branch `qa/t6-drawer-semantics`, 2026-07-20)

Triggered by the orchestrator reading the live drawer and asking two things it could not answer:
*"what exactly is confirmed?"* and *"the replaced-by edge is between 2 bases — what is replaced?"*.
Full defect-by-defect account in `tmp/conv/T6-drawer-semantics.md`.

- **The drawer states the PROPOSITION, not the element name.** *Principle: every claim is one-click
  traceable, and nothing is asserted without provenance — a status hung over a bare node name grades
  nothing an analyst can judge.* Choice: derive the assertion under assessment (and each claim's own
  assertion) from the graph's own names/types and the claim payloads, strictly derivationally — a
  payload shape we cannot phrase renders nothing and lets the verbatim quote speak. Rejected: an LLM
  or template-generated summary of the claim (a paraphrase between the analyst and the evidence, and
  a fabrication surface in exactly the place the system exists to be trustworthy).

- **A status-less edge is not an evidence gap.** *Principle: "confirmed" is structurally separated
  from "probable", and an absence of evidence must never be drawn as knowledge — or vice versa.*
  `supersedes` / `same-as` / `distinct-from` carry no status **by design**; the UI was defaulting
  `null → insufficient` and so claimed a gap that does not exist. Now stated in words, with the
  independent-looks term dropped rather than printed as `0`.

- **The relocation names its subject everywhere it is drawn.** *Principle: never overclaim.* The
  backend's site→site `supersedes` edge is a deliberate projection of a supersession that lives on the
  `based-at` edge, and it already carries `attrs.subject`. Every consumer was discarding it, so the
  map read "base A was replaced by base B" — false. Fixed in the presentation layer (label, caption,
  drawer copy, and a click-through into the version link); the backend supersede logic is untouched.
  Rejected: removing the drawn edge (it is oracle-backed and it is the thing an analyst clicks).

- **Cited-but-unclustered claims are shown, labelled honestly.** *Principle: nothing the system rests
  on may be invisible.* The drawer model only walked independence clusters, so a status-less element's
  citations were silently dropped. They now render in an explicit *"Also cited · not counted as an
  independent look"* bucket — visible, and not miscounted as corroboration.

- **`GET /evidence/{id}` returns the source registry entry, and no invented name.** *Principle: the
  analyst must be able to weigh a source, and the system never invents what it does not hold.* A raw
  `source_id` was being shown as an attribution (`d17b_withheld_gap` — a filename). The registry has
  class + reliability grade but **no publisher name**, so the API returns the entry verbatim and the UI
  renders the class; an unregistered id shows as the bare id, marked unregistered. Rejected: a
  `GET /config/sources` route (outside the frozen endpoint list, ships 51 entries to render two chips),
  a server-side display string (puts English in the contract), and bundling `sources.yaml` into the SPA
  (drifts from the live hot-config store). Logged in `tmp/conv/API-to-FRONTEND-contract-log.md`.

**Left open, deliberately (not silently):** the retired `based-at` assertion still shows its
"To raise this / next coverage due" block, because that is the backend's computed `sufficiency` and
hiding a computed field in the UI is worse than showing an odd one — whether sufficiency should behave
differently for a superseded assertion is SCORE's call. And `stale` reads "aged past its shelf life"
even when the cause was supersession; distinguishing them needs a backend signal for *why*.

**Design-doc tails to enrich:** `product/00 §5.6` (the drawer's information hierarchy — the answer to
its OPEN question is *proposition first, then verdict, then the looks, then the claims*) and
`product/00 §3` (the supersede-vs-contradict visual language must carry the **subject** of the move,
not just the two endpoints).

**Data issue raised, not self-fixed:** `unit_hq9b` is named "Pakistan Air Force" in the live graph, so
the now-correct copy reads "Pakistan Air Force moved from PAF Base Nur Khan to Rahwali airfield" —
faithful to the graph, wrong about the world. Filed for DATA/RESOLVE in
`tmp/conv/T6-to-DATA-unit-hq9b-named-pakistan-air-force.md`.

---

## QA T9 — the flagship worked query (branch `qa/t9-hero-query`, 2026-07-20)

Triggered by T3b §5: fixing graph fragmentation re-shaped the flagship chain (3 hops → 2) and left it
terminating on the corpus's planted misinformation (`d23`, "CPMIEC manufactures the HT-233"). The system
rated that edge `insufficient` and closed on a refusal — correct behaviour, but it meant *the one worked
query no longer answered the question it poses*. Full enumeration of the alternatives, the chosen thread
and the verbatim answer in `tmp/conv/T9-hero-query.md`.

- **The flagship terminates on the ORIGIN maker, not on the chokepoint's own supplier.** *Principle:
  where evidence is absent or contradictory the system says so — and it must still deliver the
  best-evidenced answer it does hold, rather than punishing a known unknown by refusing outright.* The
  chain is now `Rahwali airfield → the PAF HQ-9B fire unit → HQ-9/P → CASIC`, three hops, every one of
  them `probable` and cited. HT-233's *own* component-level supplier stays an open Known Gap and is
  stated as one in the same answer. Rejected: (i) keeping the CPMIEC terminus (a flagship that ends on
  misinformation and a refusal); (ii) the 2-hop `observed-at` shortcut to CASIC (shorter, and it skips
  the formation entirely, so it cannot answer "which unit operates it"); (iii) the TEL-chassis → Taian
  chain (4 hops but the same failure mode — a terminal `insufficient` supplier link).

- **A supplier link is carried only if the edge that claims it clears a configured band — and every
  rejected link is PRINTED.** *Principle: nothing is asserted without provenance, and absence of
  evidence is never evidence of absence.* The real defect under T3b's finding was that
  `run_fixed_hero_path` took the first manufacturer-typed *neighbour* and discarded the *edge*, so a
  link the pipeline had already scored `insufficient` was walked as if it were a finding. Fixed by
  keeping the status with the candidate (`SupplierLink`) and gating on
  `credibility.assertable_status` — a status list, same shape and doctrine as the existing
  `supersede_floor.newer_status_allow`, and it **fails closed** when undeclared. Rejected: filtering
  weak links out at the gather step — that would make a planted false attribution indistinguishable, in
  the answer, from one that was never published, which is the opposite of the non-negotiable. The
  CPMIEC link is still gathered, still rated, and now renders as an explicit *"Weighed and not
  carried"* line with its own citation. The trap moved off the terminal position; it did not leave.

- **A subject lens declares its traversal lanes, not just its anchors.** *Principle: config-driven, not
  hardcoded; a subject is a query-time lens = anchor entities + a traversal/scoring pattern.* The
  ORBAT→origin lane set is now `subjects.yaml → trace_lanes`, handed to `find_paths` as its
  `edge_whitelist`; omitted, it falls back to the ontology's full traversable set. This is what keeps
  the trace on basing/induction/supply lanes instead of hopping the *sighting* lane (`observed-at`)
  straight past the unit. Rejected: an edge list literal in `agent/loop.py`.

- **The hop assertion stays a FLOOR (`MIN_HOPS`), now 3, with the full before/after in the test file.**
  *Principle: pinning an exact shape turns a data improvement into a red test.* T3b relaxed it from a
  hard 3 to a floor of 2 rather than silently re-pinning; T9 raises the floor and records the third
  entry in the same history block. Two new acceptance tests replace the old terminus assertion: the
  chain must end on a link inside the configured assertable band (status read from the view, band from
  config — no node or document named), and the below-band link must still appear, rated and cited.

**Left open, deliberately (not silently):**
- **The flagship refuses on a cold boot** — `site_rahwali` only exists once the two withheld 2025
  Rahwali passes are ingested. This is the designed choreography (`deploy/README.md` §"the beat":
  ask → refuse → ingest → alert → ask again) and it is a genuine adaptation demo, but it does mean the
  SPA's first affordance returns a refusal until the beat is run.
- **The old query wording is retained as `target_queries[1]`** so the previous phrasing still routes to
  the same deterministic path. Its old *value* — ending on a well-reasoned refusal — is not lost: it is
  now inside the flagship answer as the "weighed and not carried" line plus the HT-233 insufficiency
  close, which is strictly more informative than a dead end.
- **`rebuild()` emits the same edge id on several rows, each holding a different slice of the claims,
  and only one row is ever scored.** Found while asking why every `inducted-into` edge is `insufficient`:
  `e:var_hq9p:inducted-into:unit_paad` exists **four times**, with the ISPR official announcement stranded
  on an unassessed row while the row that *is* assessed carries only imagery and the planted d23 — hence
  `missing: official_announcement`. 7 ids duplicated, 9 surplus rows, 0 duplicate node ids. Very likely
  also why nothing on the corpus reaches `confirmed`, and it is why the ORBAT hop here runs on `equips`
  rather than `inducted-into`. **Not self-fixed** — SCORE/RESOLVE's, and repairing it changes the graph
  shape everywhere. Filed in `tmp/conv/T9-to-DATA-graph-gaps.md`; no edge in the chosen chain is affected.

**Design-doc tails to enrich:** `C/02-demo-thread.md` (the worked thread — updated in this branch) and
`spine/09-retrieval-and-tools.md` (the tool surface should state that a trace's terminus is
status-gated, and that rejected candidates are reported rather than filtered).
## QA T11 — a read side for the config layer (branch `qa/t11-config-read`, 2026-07-20)

- **A generic `GET /config/{section}`, not a `GET /observables`.** *Principle: config-driven &
  extensible — "architecture explicitly includes a configuration / framework layer for decision-making
  and HITL at any spine layer that needs it".* The presenting symptom was one rail label, but the
  cause was that the whole config layer was write-only. One generic read closes three logged gaps at
  once: the watching-catalogue bug, the frontend's read-modify-write blocker
  (`tmp/conv/FRONTEND-to-API-config-readmodifywrite.md`), and the T6-shaped "the SPA can't read
  section X" hole. Rejected: a narrow observables route (fixes the label, leaves the config editor
  blocked), per-section read DTOs (drift from the write shape on the first new field), and making the
  POST shallow-merge instead (credibility-only, and makes deleting a key impossible).

- **The read serves the live store, never `config/*.yaml`.** *Principle: the hot-config rule — nothing
  a user does in-app requires a restart.* A read off disk would be a different value from the one the
  next `rebuild()` uses the moment anyone edits config in-app. The test that proves the seam is
  `test_config_get_reflects_a_post_with_no_restart`; the product-level proof is a 4th observable armed
  over HTTP showing up in the rail after the refetch, with no restart and no page reload.

- **Optimistic concurrency is opt-in, not mandated.** *Principle: don't break a frozen contract for a
  hazard the demo doesn't have.* The POST expected no version handle, so `if_version` is optional:
  present ⇒ a stale write 409s instead of clobbering; absent ⇒ exactly the previous last-writer-wins
  behaviour. Rejected: a required `If-Match` (breaks every existing caller for a single-analyst app).

- **Every config section is readable — verified, not assumed.** *Principle: secrets live in `.env`,
  never in code, logs or config.* `config/*.yaml` greps clean of credential-shaped keys and
  `ConfigBundle` has no env-sourced field, so there is nothing to withhold — and a section that cannot
  be read cannot be edited, since editing is read-modify-write. The invariant to preserve going forward
  is "config carries no secrets", not "this endpoint happens to be safe".

- **Two true numbers beat one ambiguous one.** *Principle: never overclaim — and an underclaim is the
  same failure, quieter.* The rail derived "Watching" from the alert feed, so a system with three armed
  tripwires and nothing yet fired rendered `0 — none fired`, which a reviewer reads as "nothing is being
  monitored". It now states **armed** (from the catalogue) and **fired** (from the feed) separately:
  `3 armed · none fired` → `3 armed · 1 fired`. Rejected: showing the armed count alone (loses the
  fired distinction the review queue depends on) and inferring armed from the seeded demo constant
  (hardcoding config into the client).

- **Unknown is rendered as unknown, not as zero.** *Principle: where evidence is absent, say what is
  missing.* If the catalogue read fails the row degrades to an em-dash plus "armed count unavailable" —
  never a confident `0`. An empty catalogue that *was* read is a genuine `0 armed` and looks different.
  The derivation lives in a pure `watchSummary()` precisely so these rules are unit-tested rather than
  trapped in a component.

**Left open, deliberately:** ~~`WatchView` still lists only tripwires that have *fired*~~ — **closed by
the 2026-07-20 live-QA remnant sweep** (below): the panel now enumerates armed-but-quiet observables
against the new route and the stale note is gone. The two config-editing surfaces (credibility rubric,
define-a-tripwire) are now unblocked but remain unwired — handed to FRONTEND in `tmp/conv/T11-config-read.md`.

**Design-doc tails to enrich:** `spine/09 §"Hot-config & live-rebuild"` (the table lists what a user
*does*; it should also say that the configuration layer is **readable**, because read-modify-write is the
only safe way to edit a whole-section write) and `plan/sessions/API.md` scope 7 (now `GET|POST`).

---

### 2026-07-20 · Live-QA remnant sweep (frontend worktree, `feat/frontend-live`)

- **Demo-scripted affordances are hidden in live mode, not deleted.** *Principle: keep the demo
  deterministic & reproducible; demo narrative is hand-authored graded content.* The zero screen's two
  lower query chips are demo-script bindings (one opens the scripted Rahwali drawer by a demo-only id,
  one poses a subject-less question); in live mode they produced a 404 drawer and a context-free
  refusal. Live now shows only the hero query. Rejected: deleting them outright (destroys the scripted
  walk while residual #17's demo-vs-live boot decision is still open).
- **Map overzoom (z8–z10) over vendoring more tiles.** *Principle: reproducibility / no un-vendored
  requests.* Leaflet scales the vendored z7 tiles past their native ceiling — blurry basemap, crisp
  pins, zero new tile requests, one-line revert. Rejected: vendoring z8–z10 tiles for the AOI
  (heavier image, new asset pipeline, deadline-day risk).
- **`/node` + `/evidence` id params became `:path` converters.** *Principle: one-click-to-source is
  the non-negotiable.* Extraction mints descriptive ids containing `/`; ASGI decodes `%2F` before
  routing, so the drawer 404'd on a node that HAS provenance — an honesty bug wearing an
  infrastructure costume. OpenAPI path list unchanged; contract-log entry added. Rejected: renaming
  ids in the frozen corpus (a data mutation to dodge a routing fix).
- **The Watch panel now lists the armed catalogue.** *Principle: never overclaim, never underclaim.*
  "Watching 3" with no way to see the three was an unnamed claim; the panel now renders
  armed-but-quiet observables from the same `GET /config/observables` read the rail counts from, and
  the catalogue-unreadable case says so instead of rendering a confident nothing. (Closes the
  previous session's "left open" item.)
- **Withheld hero answer root-caused and fixed (Option C, user-approved).** *Principle: every claim
  one-click traceable to its exact source — and the honesty machinery must not withhold a faithful
  answer.* The entailment judge rejected 4/5 assembled sentences because it saw raw surface-form claim
  text while the answer speaks at the resolved layer (FD-2000 ≡ HQ-9/P, LR-SAM ≡ HQ-9/P are the
  corpus's own alias traps), plus two sentence classes (rebuild-derived metrics, weighed-and-rejected
  links) that are structurally not NLI-checkable. Fix: (1) hand the judge the resolver's OWN recorded
  raw→resolved equivalence as an IDENTITY line so it judges the RELATION not the identity; (2) exempt
  the two sentence classes from NLI (they keep deterministic citation validation). Rejected: skipping
  the judge entirely (weakens the graded entailment-validator story to a disclosure) and alias-context
  only (leaves the two structural sentences failing). The adversarial check survives — identity is
  bridged, the assertion is not. Flagship answer now renders 5/5; live-verified.
  `tmp/conv/QA-ask-withheld-entailment.md`.
- **d18 imagery provenance is faithful, filed for DATA-C.** The frozen bundle extracted the imagery
  ANALYSIS SUMMARY text; the `.png` is a specimen, never machine-read (bbox/frame slots null). Claim
  cards could surface source class (imagery · B) without any re-record —
  `tmp/conv/QA-d18-imagery-claim-provenance.md`.

**Design-doc tails to enrich:** `spine/09` (entailment validator: state the altitude problem and the
chosen fix once decided); `product/00-ux-brief` (watch panel = armed + fired, two sources).

---

### 2026-07-21 · General `graph_analyze` tool; hardcoded hero path removed (`feat/materiality-analysis`, PR #51)

- **The keyword-triggered scripted hero path is gone; the flagship is model-planned like any question.**
  *Principle: intelligence lives in the plan and the tools, never a special-cased path.* `ask()` no longer
  routes the flagship to a fixed script — one general `graph_analyze(subject_id, analysis)` tool (enum
  `chokepoint` / `supply_chain` / `sole_source`) does the deterministic multi-hop computation (reusing the
  materiality precompute + the ranking that had been trapped in the hero script), returns status labels +
  a claim behind every element (never a numeric confidence), and returns its own internal traversal as
  hops. Generic prompt guidance (what each status means + "use an analysis when one fits", no query named)
  steers the live agent to it; the 7 primitives keep full generality.
- **Keylessness / determinism — state of the world, so no later agent re-flags it.** The live flagship now
  **needs a key** and its exact wording/path **varies run to run — BY DESIGN**, not a regression or a
  keyless gap. Byte-reproducibility lives in the recorded `?mode=demo` walkthrough and the keyless
  worked-query regression (driven by a `run_analysis` helper), **not** a scripted/keyless flagship, and
  there is no scripted flagship path to restore. This supersedes the T9 scripted-hero decision and the old
  "the hero query must run the same every time" agreement. What keeps a live answer honest is the
  deterministic tool layer + the citation/sufficiency guardrails (and the entailment judge is now an opt-in
  flag, `credibility.entailment_judge_enabled`, default off — PR #49). Rejected: a materiality-aware
  assembler builder (a disguised hardcode of the chokepoint case) and keeping the hero path as a keyless
  fallback (re-introduces the special case).

## RESOLVE — per-type auto-merge floor activates Phase 2 for organisation types (2026-07-21, `experiment/phase2-resolution`)

- **D-P3.5.1 — The scored fixpoint (Phase 2) auto-merges nothing at the global bar, and that is a measured
  property of a single-subject corpus, not a bug.** *Principle: identity comes from the alias table +
  vetoes, never a fuzzy threshold guess.* `bands.auto_merge` (0.85) sits exactly at the deterministic
  weight ceiling (0.40+0.40+0.05), so Phase 2 can never cross the auto line. A sweep of the real
  `hq9p_primary` inputs showed **no global threshold is safe**: the top of the score distribution is
  *traps*, not merges (HQ-9 vs HQ-9B at 0.56; a Karachi site vs a Punjab compound at 0.52; PAF vs PAAD at
  0.50), and the one clean org merge (CPMIEC ≡ "China … Precision Machinery …", 0.53) is sandwiched among
  them. Re-weighting toward the relational signal or loosening `relational_support_k` makes it worse — on a
  single-subject corpus everything shares the HQ-9/P neighbourhood, so relational cannot discriminate and
  the name signal *rewards* the variant-family prefix collisions that ARE the traps.
- **D-P3.5.2 — The discriminator is TYPE, not score, so the auto floor is per-type (`auto_merge_by_type`).**
  Measured per type, two types have a clean gap between their genuine spelling-variant merges and their
  first same-type trap: `manufacturer` and `trading_org`, where a near-identical name reliably denotes one
  entity. A floor of **0.37** for those two types (global 0.85 unchanged for every other) auto-merges
  exactly the four evidence-checked pairs (CPMIEC≡CNPMIEC; Taian≡Taian/Wanshan; the two SINO-GALAXY
  spellings) with margin above every same-type trap (CASIC ≠ its 23rd Institute at 0.34; ORIENT ≠
  SINO-GALAXY at 0.29). `source` is deliberately EXCLUDED — cross-account persona links (@ISPR_Watch vs
  @Sherdil_Watch, 0.38) sit right among the genuine ones, so that stays a HITL call. The floor applies only
  when BOTH endpoints carry the listed type (a cross-type pair is never a spelling variant); `hitl_low`,
  the source-asserted auto-exclusion and every veto are untouched, so a trap that shares the type is still
  stopped by the vetoes, never by this floor. Absent map ⇒ global floor everywhere (byte-unchanged, G2).
- **D-P3.5.3 — Honest limit: this reduces fragmentation but does NOT lift confirmation.** The three merges
  drop the view from 175→172 nodes; the confirmed count stays at 13 (CPMIEC was already confirmed; Taian /
  SINO-GALAXY still don't reach two independent source-groups). The deeper confirmation starvation is
  driven by the trap-adjacent single-claim fragments that Phase 2 *cannot* safely merge — so it is a data /
  corroboration problem, not a threshold one. Regression-tested: 12 new tests (mechanism + real-corpus
  outcome), full suite 899 passed. Coverage gap logged separately: no test pins machine-derived `confirmed`
  status on the real corpus.

## RK-SPIKE — the identity re-key's three micro-decisions, closed (2026-07-24, `design/resolution-redesign`)

Closing S0 of the replumb (`artifacts/plan/01-replumb-implementation-plan.md` §7 RK-SPIKE). Method: two
independently-framed opus analyses (mechanism-first / failure-first) plus the orchestrator's own
pre-synthesis position, all against a verified code baseline; disagreements adjudicated and recorded. Full
rationale in `tmp/conv/rk-spike-DECISIONS.md`; the verified defects in `tmp/conv/rk-spike-verified-defects.md`;
the design rows are **D-13.17…D-13.20** in `artifacts/spine/13-*.md` §13.

| Decision | Why | → |
|---|---|---|
| **An "authoritative" coref category may bind only behind BOTH a deterministic code-verified gate AND a source-grade floor.** `EXPLICIT_EQUIVALENCE` (quote must contain both surface forms + a configured equivalence marker) and `UNAMBIGUOUS_ANAPHOR` (type-unique antecedent) are authoritative; **`NAME_VARIANT` is raise-only permanently** | An authoritative pair is a Phase-1 **bootstrap trigger**: it merges at hardcoded `1.0` and **bypasses banding entirely** (`resolve/cluster.py:462-465`), so **no cap restrains it**. Authorizing a category therefore authorizes an uncapped fusion on a *model-chosen label*. And a coref bind currently acts **harder** than the assertion it most resembles — a stated `same-as` is grade-floored *and* raise-only, while a bind reads **no grade at all** — an inversion; **stated ≠ trusted** (spine/13 §5) | **rejects** authoritative `NAME_VARIANT`: because a bind bypasses banding, it *is* the exact-normalized-name lane D-13.1 exists to delete, rebuilt on another predicate and immune to D-13.10's cap. **Overrules** the shipped config's second justification for `coref_authoritative_evidence: []` — preserving the d10 "HT-233 (H-200)" demo beat — as demo-preservation, forbidden as a design input (working-principles #1). The first justification (flip producer + consumer in one motion) survives as a comment. **Data pass owes** a re-carried beat: split the two designations across two documents, converting a *reading* demo into an *earned cross-document identity* demo |
| **The referent atom is *evidence about a grouping*, never the address of the provisional instance — and the rebuild may DECLINE the grouping** (de-group to claim-atom granularity + raise, on an intra-referent critical-discriminator conflict) | Without it, "atoms never split" + "referent atom = the address" makes **intra-document over-merge permanent**, contradicting spine/13 §4's "challengeable proposal" — disqualifying. This is already the shape the code emits: `ingest/coref.py:385-392` mints a **claim** id on `coref-same-as`, never an entity id | **rejects** minting one referent atom per *proposal* and addressing the instance by it. **Not implementable:** a per-link authoritative closure — the coref category is stamped per **cluster**, not per link. **New code, non-obvious:** the conflict is invisible in `Entity.attrs` (first-claim-wins scalar, `entities.py:189`), so the check must read `attr_history` |
| **A same-document stated-contrast pair is capped at a *band ceiling* of `probable` — ungraded — and the config value is a band name, not a float.** Absence of contrast is **neutral** | A coefficient is unsafe: at the shipped thresholds (`auto_merge 0.85` / `hitl_low 0.45`) a ×0.5 penalty drops a pair **two bands**, silently out of the analyst's queue. A band ceiling is threshold-independent and matches the existing `perishable_capped` / `raise_walls` idiom: *contrast means "not automatically", never "not at all."* Ungraded because a ceiling **cannot shatter** an existing cluster (it withholds one new fusion) — which removes the harm a grade gate would defend against | **rejects** riding the stated-`distinct-from` rail (hard, transitive, ungraded — `resolve/__init__.py:567-575`): **every ORBAT list contains an enumeration**, so widening it would shatter clusters. **rejects** parsing the claim-id prefix for doc-sameness (re-introduces the id-format coupling the re-key removes) and `Entity.source_ids` (that is the *publisher*) → **`Entity.doc_ids`**. **Finding that removes work:** Tier 1 **already** compares same-doc pairs (no doc filter exists anywhere in `resolve/**`), so half of F5 needs no code. **Adopted separately:** "two batteries" is the source **stating the OOB figure** → capture as a sourced `count` on the presence (D-13.13) |
| **A shared designation is NOT a unique identifier: `hard_id_fields.unique` becomes a list of composite AND-keys** — `(service_branch, designator)` identifies, a bare `designator` does not. One shared designation may never confirm a formation merge | Designations are **reused across armies and across time**. The composite key makes the operator requirement **structural in the identifier declaration** rather than dependent on a namespace check that is **broken in the Phase-2 fixpoint** (see G19). The codebase already embodies this asymmetry for bills of lading — differing identifiers veto, shared ones do not confirm | **rejects** treating a designation as a fast path to confirmed, and **rejects** merely declaring it a "non-perishable discriminator" (which would still lean on the broken namespace check). **Enabling change:** split `attribute_score` into two signals (`name` / `discriminator`) — already computed independently and fused at one `max` (`scoring.py:425-437`) — **without which D-13.10 cannot function at all** |
| **Gate amendments: G15/G16/G18 would each pass while the harm they name happens; a new G19 is added** (plan §5a) | **G16** must assert the absence of a **drawn relocation edge**: `based-at` is FUNCTIONAL and unit-keyed (`ontology.yaml:146`), so a formation over-merge makes two sites one unit's before/after, and `promote_supersessions` (`credibility/supersession.py:165-209`) promotes it, **pops the pair out of the analyst's queue** and **draws** the edge — an identity error becoming a **fabricated movement assessment with the human removed**. **G15** passes vacuously and misses the silent second-formation truncation (`basing.py:301`, an OOB undercount with **no merge**). **G18**'s `operated-by` half has **no predicate** to fire on, and the gate names no wall *channel*. **G19**: nothing gates cross-namespace fusion in the Phase-2 fixpoint | A gate that cannot fail is a gate that lies. **Ontology sub-scope limitation overruled:** `ontology.yaml:40-44` rests unit-only supersede keying on "correct while the corpus has no such simultaneous pair" — forbidden as a design input; tag the supersede key by `site_type` |
| **F9 accepted and disclosed, not fixed** — only *completed* merges carry relational weight; a `probable` anchor contributes **exactly 0** | The fix reintroduces a feedback loop threatening the monotone-termination argument the fixpoint rests on (`cluster.py:6-9`) and therefore G2 determinism — a bad trade in the very stage trying to make formation merges *harder*; and its absence errs toward honest fragmentation, which spine/13 §6 declares the goal. Both analysts independently agreed | **Design-note disclosure (required):** *relational scaffolding only helps where the anchor actually merges; a merely-`probable` anchor lends no support at all — a step function, not graceful degradation.* **And lever 2 is weaker still:** `places.augment` runs **after** `resolve_entities` (`resolve/__init__.py:181` vs `:177`), so place merges are invisible to `relational_score` — places are mechanically **not** the clean anchor spine/13 §6 names. Ordering fix belongs in S3 |
| **Three things the design depends on that do not exist — recorded so they are not assumed** | (i) **D-13.9(b) source-independence is absent from the merge path** — the machinery exists for *claim* corroboration but nowhere in `resolve/`; `identity_ledger`'s "independent identity **signal**" is about signal *classes* and is the thing most likely to be mistaken for it. (ii) **"Rarity-graded name" has no implementation anywhere**, yet D-13.2 and D-13.10 both rest on it. (iii) The raise-only **licensing quote is written but read nowhere** — so the mitigation both analyses use to justify raise-only does not yet exist | Plan §7 RK-COREF item 5 reads (i) as *configuration*; it is **new code**. Each is either scoped into S3 or disclosed — never assumed |
| **Terminology correction: "capped at *probable*" is not expressible as written** | Three bands (`cluster.py:96-101`), no `reject` verdict, and confirmed/probable/possible are a derived read of set membership (`schemas/stage_io.py:112-118`) where **only `same_as` fuses** | Read every such phrase as **"not fused; queued and reported"** — stronger and testable. Both cap *shapes* already exist and are proven, so **the co-location cap (G16) is a third instance of the `perishable_capped` shape, not new machinery** |

### RK-SPIKE adversarial review — closures C5–C10 + three corrections to my own work (2026-07-25)

A multi-agent adversarial review of the spike's own output (12 blind-case triage verdicts each attacked by an
independent skeptic — 3 overturned; six review dimensions, every high/critical finding refuted before
counting). Verdict + evidence: `tmp/conv/rk-spike-REVIEW-VERDICT.md`. **The review's chief value was breaking
three of the orchestrator's own artifacts.**

| Decision | Why | → |
|---|---|---|
| **C9 — an authoritative coref bind may instantiate only over entity ids attested in the contributing document** | D-13.17 gated the bind on a **document-scoped** precondition while the bind instantiates through a **graph-global** name/alias expansion — so the precondition did not bound the effect | Decisions (a) and (b) now **share** the `Entity.doc_ids` carrier; (a) must not ship without it |
| **C5 — the Tier-0 gate is per *link*; a cluster binds only over passing links, each failing link becoming a Tier-1 candidate pair** | The gate says the quote must contain "**both** members' surface forms" — a two-member formulation the spec never generalised to n-ary clusters. The implementer hit this before seeing any case | **rejects** both options previously weighed: all-or-nothing conjunction (one bad link demotes a good cluster to *n* singletons) and the per-link closure ruled out as unimplementable. A **partial** bind is strictly better than either |
| **C6 — `perishable` is declared per *(type, attribute)*** | Geography is perishable for a **formation** (units move), **constitutive** for a **presence** (a presence *is* operator+design+site+window), **identifying** for a **place** (coordinates). Without this no anchor or design can ever confirm, so spine/13 §6 lever 2 **cannot exist** — and that is a *missing rung*, in addition to the `places.augment` ordering bug already logged | The shipped `attribute_roles.<type>.<attr>` schema already supports the shape ⇒ one declaration, not new machinery. Both causes are real; both get fixed |
| **C7 — normalization is a prerequisite for walling on ANY slot; an unnormalizable stated critical value ⇒ no wall AND no fusion + a named gap** | R5.2 required normalization for **operator** while D-13.20 gave **designation** the strongest wall with no table at all (`3rd` vs `III` permanently unmergeable). spine/13 §7 already stated the prerequisite generally, so the narrowing was a drafting slip | The prototype was right that a false wall must not shatter a merge, and **wrong** to let the pair confirm instead. **The general principle: a gap must bind the fusion path, not merely annotate it** — a named gap beside an asserted assessment is decoration |
| **C8 — independence keys on evidential lineage, not document count** | "≥2 distinct documents" confirms two verbatim reprints of one source. Independence must inherit spine/04's independence groups; a cite-of-a-prior-report is same-group | **New code** in S3, not configuration (plan §7 read as though it were). Same root cause as **D11** (the flagship's *nominal* independence — different publisher/discipline ≠ an independent look at the phenomenon): one predicate fixes both |
| **C10 — a single-source relocation requires authoritative self-coreference AND the grade floor** | The prototype's switch was wider than its own rationale claimed (any single-member instance, ungated) | **rejects** "always require two sources" — that refuses a source authority over its own referent, which spine/13 §5 grants |
| **REJECTED — the prototype's "fusion is licensed by a structural trigger, never by a score"** | Invented, and stronger than the spec: D-13.9 specifies a **graded** path constrained by two guards. Converting a *negative cap* into a *positive whitelist of three triggers* changed the system in both directions and is what made designs unable to collapse and the anchor layer a dead end | **Keep** the half that is right — the guard is a hard **precondition on the fusion path**, not a score contributor (R3.1). **Reject** the whitelist |
| **The anaphor gate must be reformulated positively, or `UNAMBIGUOUS_ANAPHOR` reverts to raise-only** | Three findings converge: (i) the gate is an **absence** test over a model-produced, surface-deduplicated inventory, so **under-extraction makes it PASS** — its failure mode is anti-correlated with safety; (ii) it contradicts D-13.19's own doctrine that absence is never evidence; (iii) my decisive argument was **wrong** — raise-only does not "manufacture nameless orphans", it produces a `probable` HITL candidate one click from merge | Require a **named, declared, ontology-typed antecedent** and exactly one type-compatible mention, with `unknown`-typed endpoints **counting as compatible**. If the positive gate is not built, **analyst B's raise-only was right** and is the default |
| **D1 is understated: the over-merge also DELETES an honest refusal** | The same identity error does not merely add a fabricated relocation — it turns an edge correctly labelled `insufficient` (with a Known Gap naming the missing corroboration) into `stale` **with no gap at all**. It fabricates a claim *and* erases the system's own admission of ignorance | **G16 asserts three things** (C2): no confirmed formation merge · no drawn relocation · **no Known-Gap deletion and no `insufficient → stale`** |
| **Corrections to my own work — logged because a reviewer should see them** | (i) **Three matcher bugs**, one score-changing: `any_of` read the wrong key so it could **never pass**; `count_equals … 0` was structurally unpassable (scoring UNRESOLVED exactly when the implementation was *right*); per-case invariants were undispatched. **13/24 → 15/24.** (ii) My **anti-fabrication invariant did not catch fabrication** — it pooled stated values across *all* documents, so a value transplanted onto a thin instance passed; now scoped per instance, negative-control verified. (iii) **C1–C4 never left `tmp/conv`**, and **A1/A5 encoded the referent atom as the primary id key with the claim atom as a "fallback"** — the inverted, forbidden ordering, about to be frozen at S1 | *A check that cannot fail is a check that lies* — I criticised a gate for that and shipped two harness checks with the same flaw. A1/A5 are now **claim-atom-primary**; C1–C10 are folded into §5b and cited from the stage scopes; G19 and the G15/G16/G18 amendments are wired into the gate table, stage gate lists and owned test paths |

## RK-BAKEOFF — integration triage of the three blind hands (2026-07-25, `bakeoff/rk-impl`)

Merged the impl-blind spec gates (`bakeoff/rk-test`) onto the harness branch. 37 tests were red. **32 of
them were a binding artefact, not a defect**: the spec's name-discovery found two of its four surfaces
with incompatible signatures (`TypeError` before the assertion) and missed the other two entirely, so
those gates silently graded the deliberately-wrong NAIVE stand-in — while a single global `USING_STAND_IN`
flag printed *"checked against the shipped eval.extraction harness"* on every failure. **A red carrying a
false attribution is the same defect class as a green carrying a false claim**, and this one would have
sent the next reader to "fix" a module that was already correct. Fixed by an explicit binding layer
(`tests/bakeoff/_impl_binding.py`) plus per-surface provenance. Five genuine divergences remained.

| Ruling | Call | Reasoning | Alternative rejected |
|---|---|---|---|
| **The composite must respect metric direction** (IMPL DEFECT, severe) | Invert `lower_is_better` rates before they enter the weighted composite; refuse to composite a metric whose direction the candidates disagree on | `composite_series` summed raw values while ranking the composite higher-is-better. Measured: with fabrication weighted 4.5, a model fabricating 40% of the time scored **0.56 against a clean model's 0.32** — the harness actively selected for the behaviour the project calls disqualifying, and every per-metric line still read correctly. Latent under today's weights (no lower-is-better *rate* is weighted) but the next natural metric anyone adds is a rate of something bad | Leaving it as "latent, not reachable". A defect whose trigger is *adding an obvious metric* is a trap, not a non-issue |
| **A non-negotiable is a veto, not a weight** (test hand right) | Before `WINNER` is issued, the leader must not be *materially* worse than any rival on a metric named in `gates.non_negotiable_floors`; else `NON_NEGOTIABLE_REGRESSION` | Inside a composite these are heavy weights, and **any weight is a price a good-enough model can pay**. The winner re-freezes the graded oracle, writing ungrounded claims into the evidence layer wearing valid citations — nothing downstream catches that. The check reuses the existing margin rule, so it **invents no threshold** and only an already-established difference can veto | The implementer's refusal to pick a floor was right about *absolute* thresholds but does not cover the *relative* case, which needs no constant. Reuses the existing floors block as the declaration site rather than adding a second list |
| **A REQUIRED metric blocks the verdict; a merely weighted one is excluded and named** (test hand right, scoped) | New `required_metrics` config list → `INSUFFICIENT_CRITERIA`. Declared: `coref_binding`, `discriminator_capture` | Plan §8 splits this into a Wave-0 screen and a definitive pass *because* the two top-weighted criteria are unmeasurable today. A Wave-0 winner asserts the missing half could not have mattered — and **nobody re-runs a bake-off that already has a verdict**. This is the project's own "insufficient evidence to assess" rule turned on its own instrument. The block **lifts automatically** when they are measured | Blocking on *any* unavailable weighted metric (over-broad, would fire on cost/latency); and doing nothing (the impl's exclude-and-name), which is right for weights but not for a criterion declared decisive |
| **An out-of-bounds citation span is unfaithful** (impl right, SPEC FIXTURE wrong) | Fixed the test fixture, not the check | The fixture cited `(0, 96)` of a 95-char document. Python's forgiving slice is a language accident, not a licence: a span that does not exist is provenance that does not resolve, and one-click traceability is what makes this system's output admissible | Loosening the impl to tolerate overruns — that is the metric this project can least afford to make lenient |
| **The matcher's hyphenation weakness is PINNED, not tuned** (finding, deliberately not fixed) | Re-bracketed the thresholds (.50/.99) on the author's own claim pair; added a test asserting the current behaviour | Measured: `HT-233` vs `HT233` scores **0.5455**. `normalize_surface` rewrites `-_/` to a space (right for predicates), splitting `HT-233` into two tokens while `HT233` stays one; `token_sort_ratio` then punishes the split. This corpus's key surfaces are exactly that shape (HQ-9/P, HT-233, FD-2000), so a legitimate de-hyphenated variant scores a **non-match** — depressing recall for every candidate and adding variance | Re-tuning the kernel here. That changes every number the bake-off produces and would be done by someone who has now read the gold — the exact failure the matcher's own docstring warns against. It belongs to the gold owner, against a labeled sample |

**Also fixed (IMPL DEFECT, found only by running the real loader against the real gold):** the gold loader
read the sentinel string `"unknown"` as a *stated* discriminator. 349 of the slice's 500 discriminator
slots are that string, so `discriminator_capture`'s denominator swelled from 151 to 500 (a perfect model
scores ~0.30) and `discriminator_fabrication_avoidance` lost its denominator entirely — and **a model that
literally emits the word "unknown" would outscore one that correctly abstains**, rewarding the fabrication
the metric exists to catch. Null, absent and sentinel are now one case.

**Disclosure for the design note:** the bake-off **cannot run today**, and the blocker is not model keys.
The labeled gold (`rk-spike-claim-gold/1.0`) and the scorer's declared contract (`rk-bakeoff-claim-gold/1.x`)
are different schemas — different row keys, no `form` field, quoted-string spans instead of char offsets,
and 38 of 125 rows that are *negative* gold (NOT_A_CLAIM / ANTI_COREF / AMBIGUOUS / UNMODELLED) which would
cap a perfect model's recall at ~0.70 if loaded naively. Writing that translation is the next task and it
carries semantic calls that belong to the gold's owner, not to the scorer.

**Coref-binding — the top-weighted criterion — is unmeasurable, for a reason nobody had stated.** Gold
*exists* (32 doc-local clusters, 120 mentions); the earlier "zero coref annotations" finding is true only
of the frozen `answer_key.json`, which the bake-off does not use. What is missing is the **output channel**:
the model-facing extraction tool schema has no coref/cluster field anywhere (the only hits are docstring
prose), and `ClaimRecord.referent_id` is written by nothing — `dedup.py` only renames ids that already
exist. Every candidate would therefore emit an identical empty clustering, so scoring it would measure the
schema, not the model. This is a *stronger* statement than "no yardstick", because it names the fix: coref
becomes measurable the moment extraction offers a mention-cluster field (RK-COREF/S3), and the gold is
already sitting there waiting.

### RK-BAKEOFF (DATA) — the sub-oracle may not be more confident than the system it grades (2026-07-25)

Repair of `tmp/spike-rk/gold/sub-oracle.json` / `.md` under the user-ratified directive
`tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md`. The sub-oracle is the **yardstick** the three
bake-off candidates are scored against, so a defect in it is a defect in the measuring instrument, not a data
nit. Repair script (re-runnable, fails loudly rather than drifting the two artifacts apart):
`tmp/spike-rk/repair_sub_oracle.py`. Full record in the artifact's own `repair_log`.

| Decision | Why | → |
|---|---|---|
| **All twelve single-source entries capped at `probable`.** Measured, not assumed: exactly 12 entries rest on one slice document — 5 bare `confirmed` (`sl_e15/16/17/20/21`) and 7 **qualified** confirms (`sl_org_orient`, `sl_org_sinogalaxy`, `sl_org_alnoor`; `sl_event_118834/118835/119011`; `sl_e11`) | The running rule is `config/credibility.yaml` `min_independent_groups: 2`, enforced in `credibility/status.py::assign_status` against `_effective_looks()`. One document is one look. A yardstick that confirms on one look scores the system as **under-confident exactly where the system is being correctly cautious** — it inverts the measurement in the direction that flatters us | Post-repair the sub-oracle carries **6** `confirmed` entries, every one of which clears the rule with margin under the *stricter* effective-looks arithmetic (same-discipline groups count 0.5): 2.0–3.5 weighted looks. `sl_gap_ht233_maker` sits exactly at the 2.0 floor |
| **A QUALIFIED confirm is a status claim and is subject to the cap.** `status` now always holds one of the four declared vocabulary values; the qualification moved verbatim into a new `status_proposition` field | The parenthetical narrows the **proposition**, not the **status** — and narrowing a proposition buys no second look. Structurally it is also unsafe: any scorer normalising `status` reads a leading "confirmed" as `confirmed`, so a free-text status silently escapes the one rule the yardstick exists to hold. The strongest counter — *a primary record is self-evidencing for its own existence* — is real but is **not** a rule the running resolver implements, and this artifact's job is to state the ceiling the running system should reach | **rejects** treating the qualifier as a separate, exempt status tier. Analytic content is preserved, not deleted: the narrowed proposition is now a first-class field and is rendered in the `.md` |
| **Identifier-licensed identity does NOT bypass the two-look rule.** Scope: the whole sub-oracle, and any future slice oracle. A shared unique identifier inside ONE primary record (a bill of lading, a GD number, an SECP CUIN) is **one look**, however hard the identifier | The directive offered this bypass explicitly. Refused because **no such rule exists in the running resolver** — there is no identifier fast-path anywhere in `credibility/` — so writing one into the yardstick would make the yardstick disagree with the system by construction, which is the precise defect being repaired. It is also the wrong direction of error for a measuring instrument: the project already holds that *differing identifiers veto, shared ones do not confirm* (RK-SPIKE, 2026-07-24) | **Roadmap, not build:** if identifier-licensed confirmation is ever wanted, it belongs in the resolver first and in the oracle second, never the reverse. The five entries with the strongest claim to it (`sl_e15/16/17/20/21`) carry a note saying exactly that, so a reviewer sees a decision rather than an inconsistency |
| **`sl_e03` (`same-as` HQ-9/P ↔ HQ-9P) re-cited on the one row that supports it; its counter-evidence moved to the tension list as `sl_amb_07`** | The entry claimed `confirmed` on "three independent sources" while citing four rows, of which **one** supports the proposition (`d04-r02`, unhedged, variant level). `d02-r07` is a FAMILY-level parenthetical and is in fact the *FD-2000* row; `cs01-r01` is an `ATTR:family` row that never asserts the equivalence. `d19-r09` is **counter-evidence**: HQ-9BE ≡ HQ-9P, which chained with `d04-r07` (HQ-9/P ≠ HQ-9BE) entails HQ-9/P ≢ HQ-9P | **rejects** "counter-evidence overridden": it is held as a live, flagged contradiction, which is what the corpus is built to test. Status drops to `probable` (one look). The claim-gold row itself was already honest about the collision — the defect was in the sub-oracle's citation, not in the labels |
| **Not changed: independence DETECTION (deferred defect D11), and the flagship Rahwali confirm** | The rule (two independent looks ⇒ confirmed) is correct and stays; only the *keying* of independence on publisher/source-type rather than evidential lineage is roadmap (same root cause as C8, 2026-07-25) | The slice's Rahwali entry `sl_e09` was already `probable` **before** this repair — because the slice deliberately omits d18's first pass, not because anything was demoted here |

### RK-BAKEOFF integration triage — the gold adapter and the harness on one branch (2026-07-25)

Merged `bakeoff/rk-data` (the gold adapter) into `bakeoff/rk-impl` (the scorer). One conflict, in this
ledger, both append-only blocks kept. Suite green at **1698 passed / 7 skipped / 2 xfailed**; the data
hand's 4 scorer-gated tests now execute for real rather than skipping, which is why the skip count did not
rise. **Both deciding checks were re-derived independently rather than taken on report:** a candidate
emitting exactly the positive gold scores recall **1.0000** through the adapter, and a candidate that also
emits the 11 `not_a_claim` traps keeps recall 1.0000 while precision falls **1.0000 → 0.8553** — traps cost
precision and steal no recall. The instrument is sound.

| Ruling | Call | Reasoning | Alternative rejected |
|---|---|---|---|
| **The unwired precision exclusions are a measurement defect, not a footnote — and the scorecard must say so on every run** (SPEC GAP, quantified) | Added §5 to the rendered scorecard: precision is `matched/extracted`, three of the gold's four negative classes are declared neutral, and **nothing calls** `precision_exclusions`. A test asserts the disclosure and its position below the numbers | Measured, not estimated: a candidate emitting the 65 positive claims plus all 27 neutral-class spans scores precision **0.7065** against a wired **1.0000** — an unearned loss of **0.2935** (0.2262 for the 19 `UNMODELLED` rows alone). The note's "up to 11 precision points" was wrong on every construction. It does **not** cancel between candidates: the penalty scales with how much of a document a model reads, so it **favours the terser extractor** and lands on `surface_f1` (weight 3.0) — the same defect class as the composite-direction bug (a harness selecting for the behaviour the project calls bad) | **Wiring it here.** That redefines precision for every candidate and needs a weight decision for `trap_avoidance`, so it changes what every bake-off number means — the orchestrator's call, not the integration hand's. Also rejected: absorbing it silently, which reports a lower bound as a score |
| **`0.6960` is not the naive recall ceiling; `0.5200` is** (FIXTURE ARTEFACT in a justification, direction conservative) | Both figures now asserted separately, in the adapter docstring, the test, and the slice-limits note | 0.696 = 87/125 credits the perfect model with matching the **22 attribute rows** — rows the adapter excludes *precisely because the pipeline cannot express an attribute as a claim*. So it describes a model that cannot exist and understates the artefact by 0.18. Measured through the real matcher, a candidate emitting only what the pipeline can produce scores **0.5200**, so the adapter is worth **0.48** recall, not 0.30 | Deleting the 0.696 assertion. It is a true measurement of a real construction; the defect was the label "the same perfect model", so both are kept and distinguished rather than one replaced |
| **`NO_ELIGIBLE_CANDIDATE` on a text-only document set is correct behaviour, not a bug** (verified, no change) | Left alone | Running the harness on the 7 documents the slice cites yields no eligible candidate, because the slice cites `d17b_withheld_gap.txt` and **no image document** — so `image_calls_total=0`, the imagery gate reads UNKNOWN, and UNKNOWN blocks. A gate nobody exercised is not a gate anybody passed. Adding the real `.png` frame makes both scripted candidates eligible | Treating it as a gating defect and relaxing the gate to pass on an unexercised imagery path — that is the one gate this project can least afford to make lenient |

**End-to-end verified offline on the real inputs** (real adapted gold, real sub-oracle, 7 real corpus docs,
scripted no-network client, zero API calls): the coref precondition **refuses before any client is built**
when `coref_binding` is required and the channel is dormant, naming the flag; with the channel on and a
required metric genuinely unmeasured the verdict is **`INSUFFICIENT_CRITERIA`** with `winner=None`; with
nothing required and no separation it is **`NO_MEASURED_DIFFERENCE`**. The harness refuses to name a winner
in exactly the cases it should, and still reaches `WINNER` when a real separation exists.

### RK-BAKEOFF (DATA / GOLD OWNER) — the identifier match rule, decided against the labeled sample (2026-07-25)

The one knob that decides whether `HT233` counts as `HT-233` was deferred to this hand **twice**, with a
stated reason: re-tuning the match kernel moves every number the bake-off produces, so it must be settled
against a labeled sample rather than by whoever has just read the gold and is tempted to tune to it. Settled
here, by measurement over the **247 distinct surfaces** of the labeled slice — re-derived on every test run
by `backend/tests/gold_adapter/test_identifier_match_policy.py`, so no figure below is remembered.

**Both deciding checks are unmoved, and are now asserted under every setting of the new rule** (a perfect
model's surfaces are byte-identical to the gold's, so the rule must not be what produces the number): a
candidate emitting exactly the positive gold still scores recall and precision **1.0000** on 65 pairs, and a
trap-emitting candidate still keeps recall 1.0000 while precision falls to **0.8553 (65/76)**. Suite
**1712 passed / 7 skipped / 2 xfailed** (baseline 1697, +15 new tests, no regressions). Zero API calls.

| Ruling | Call | Reasoning (measured) | Alternative rejected |
|---|---|---|---|
| **Punctuation inside a letters-and-digits token is typographic, not a word boundary** | New `identifier_policy: designator_aware` in `config/bakeoff.yaml`. `HQ-9/P` ≡ `HQ9P`, `HT-233` ≡ `HT233`, `KPQA-HC-2020-118834` ≡ `KPQAHC2020118834`; prose is untouched (`AL-NOOR CARGO`, `fire-control/engagement`, `supplies-component`) and a date is not an identifier (`2024-11` stays split). Both readings are scored and the **better** is kept, so it can only ever add a match | The old kernel rewrote `-_/` to a space everywhere, splitting `HT-233` into two tokens while `HT233` stayed one; `token_sort_ratio` scored that pair **0.5455 — a non-match**. Across the labeled gold that cost **16 of 61** legitimately de-hyphenated designator surfaces at the 0.70 role floor and **24 of 61** at the 0.80 pair floor. This corpus's key surfaces are *all* that shape (HQ-9/P, HQ-9BE, HT-233, FD-2000, S-400), so the loss was systematic, charged every candidate, and added variance to a comparison already fighting non-determinism. Under the new rule: **0 of 61** below either floor | **Leaving it and stating the ceiling** (the third option offered). Refused because the loss is not a ceiling a reader can correct for — it is unevenly distributed across candidates by how often each renders a designator bare, so it is *variance*, not a constant offset. Also rejected: replacing the prose reading rather than taking the max, which lowered two legitimate article-only pairs (`HQ-9/P` vs `The HQ-9/P`, 0.75 → 0.667) below the floor |
| **A designator disagreement is a VETO, not a low score** | New `identifier_agreement: nested_or_equal`. Per role, the identifier token sets must be equal or nested (empty nests into anything, so prose is unaffected); nested rather than equal so `the FT-2000` may pair with `the FT-2000 (sometimes rendered FT-2000A)`; **not** prefix-tolerant, so `HQ-9` is not `HQ-9/P` | This is the finding that decided the whole call, and it inverts the reason the question was deferred. The worry was that catching `HT233` would start merging `HQ-9A` into `HQ-9B` — **the old kernel already did**: HQ-9A/HQ-9B 0.80, HQ-9B/HQ-9BE 0.91, FT-2000/FT-2000A 0.93, S-400/S-300 0.80, two different GD numbers 0.95, two different B/L numbers 0.95. One changed character in a six-character designator is a tiny edit distance, and splitting it into tokens lets the *shared* tokens carry the pair — so no threshold on fuzzy similarity can separate them. Genuinely-different designator pairs conflated at the role floor: **40 of 684 → 0**. Across all 30,371 cross pairs of the slice's surfaces, pairs above the role floor **128 → 84**, and those the gold labels as *different nodes* **30 → 9** | **Raising the role floor instead.** Under the glue all 61 legitimate variants score exactly 1.0000, so a higher floor looked free — but it is not: it would also drop the added-qualifier matches the config's own note defends (`Type-7 Coupler` vs `Type-7 Coupler assembly`, 0.7568). A veto scoped to the discriminator is the targeted fix; a higher floor is a blunt one |
| **The same rule governs the grounding proxies, not just the matcher** | `metrics._lexically_grounded` now asks the same question under the same readings | The half that mattered most, and it is on the **non-negotiable** lines. Measured against the real slice documents at the declared 0.85 floor, the prose reading scored a *faithful* de-hyphenated designator as ABSENT from the document that states it — `HT233` vs d19 **0.80**, `HQ9P` vs d02 **0.75**, `HQ9BE` **0.80**, `FD2000` **0.83**, the GD number **0.81** — i.e. it reported a model that quoted the page correctly as **fabricating**, on `citation_faithfulness` and `extract_only_stated`. All five now read 1.00 | **Scoping the fix to the matcher only.** That leaves the harness saying "this document does not state HT233" about a document that states HT-233 — a false fabrication finding, which is a worse error than the recall dent it was fixing. It cannot launder a real fabrication: gluing only deletes punctuation *inside* a letters-and-digits token, so an invented surface becomes groundable only if the document already states the same string in another rendering, which is what grounded means (asserted) |
| **What it costs, stated rather than absorbed** | Two same-node pairs in the slice stop matching, both to the veto, and both are pinned by an equality assertion so the cost cannot grow unnoticed | `the FT-2000` vs `FT-2000A` (0.7368 → veto): this gold declares them ONE node because d04 says "sometimes rendered", but in general a suffixed designator *is* a different variant (HQ-9B vs HQ-9BE), so the veto is right in the general case and wrong on this documented alias. `HT-233-band engagement-radar parameters` vs `HT-233 engagement radar` (0.7419 → veto): the glue swallows the adjacent hyphenated word, so `ht233band` ≠ `ht233`. Both err toward a **missed** match — the safer direction, for the reason the config already gives: misses add variance and variance makes the margin rule *more* reluctant to call a gap material, whereas leniency inflates every candidate and hides the fabrication line | **Recovering the FT-2000 alias with an alias table.** An alias-aware matcher hands the extractor credit for resolution work it did not do — the surface module's own stated rule |
| **The residual over-match is named, and it is not about designators** | Recorded in the slice-limits note as a limit on what a surface-F1 number means | **9 cross-node pairs still clear the role floor and every one is prose**: `the HQ-9B system` vs `the system` (0.80), `the PAF variant` vs `the Army variant` (0.8387), `the site` vs `the system` (0.7778), the Sialkot/Pasrur phrase pair (0.7789). Those are anaphora and an *operator* discriminator; a surface matcher can see neither. So the matcher **separates designators and does not separate referents** — a bake-off number is evidence about reading, not about entity resolution | Extending the veto to the operator/geography discriminators. That is resolution work in the matcher, out of scope for a measuring instrument, and the slice has too few such pairs to calibrate it |
| **The policy is declared and configurable, never emergent** | Both knobs live in `config/bakeoff.yaml` with the rule written in prose plus every number above; `MatchPolicy.describe()` prints them above every score; a rejected pair reports the reason `identifier` | The matcher's leniency IS the measurement, so it may not be a side effect of a normalisation helper's regex. `identifier_agreement: ignore` reproduces the pre-decision numbers — a measurement-policy control for a reader, not a compatibility path | Hard-coding the decided behaviour. A reader who cannot switch it off cannot tell how much of a score is the matcher's generosity |

The pinned tripwire that used to assert "a de-hyphenated designator is a non-match" did its job — it made
this a deliberate re-tuning rather than a silent drift — and is **re-armed pointing at the decided
behaviour**, now asserting *both* directions so neither can move quietly:
`test_a_dehyphenated_designator_matches_and_a_sibling_designator_does_not`.

### RK-BAKEOFF integration — the driver, and two defects the driver exposed (2026-07-25)

Both hands merged (`bakeoff/rk-data` into `bakeoff/rk-impl`; two conflicts, both pure import-line unions in
`matcher.py`/`metrics.py`, resolved as unions). Three test functions disappear relative to the merge base and
**all three are deliberate replacements**, verified individually rather than assumed: the data hand re-armed
its hyphenation tripwire, and the impl hand retired the "a null floor means no gate at all" and "the
scorecard discloses the exclusions are unwired" tests because it changed both of those behaviours. Suite
**1790 passed / 7 skipped / 2 xfailed**. Zero API calls.

**The three deciding checks were re-run independently** (own script, real loaders, real matcher, shipped
policy — not either hand's tests): a perfect model scores recall **1.0000**; a fabricator is penalised
(precision 1.0000 → **0.8553**, 0 of 11 traps credited as matches, 0 exclusions granted, trap line 0.0000)
and steals no recall; and the new third check passes — a **verbose-but-honest** model (positives + all 27
neutral spans) now scores precision **1.0000** where the raw denominator would have given 0.7065. The
inversion is gone: unwired, the instrument preferred the fabricator (0.8553) to the honest reader (0.7065).

| Decision | Call | Reasoning |
|---|---|---|
| **The driver derives its slice from the gold, never from a list typed into a CLI** | New `run` subcommand + `eval/extraction/driver.py`. The document set is the adapted gold's own `docs`/`doc_paths`; each document's source type and co-located frames come from the **pipeline's source registry**; a labeled document missing from either raises rather than being skipped | A document quietly added or dropped changes what a recall number means and is invisible on the scorecard. Deriving the slice from the answer file makes the two impossible to disagree. Source type is not guessable: it selects the extraction tool, so guessing it would measure the guess |
| **The real corpus image is not bolted on** | `d17b_withheld_gap` is registered with `d17b_withheld_gap.png` as a co-located frame (ING-8), so the imagery lane fires on the real frame the same way the seed recorder loads it. The driver refuses to run at all if the slice yields no frame | Without an image call the imagery gate reads UNKNOWN and disqualifies every candidate — a wasted budget. Refusing up front is the same discipline as the coref precondition |
| **The spend is stated as a floor and a ceiling, then reconciled against the actual** | `SpendPlan` prints candidates/docs/passes/runs and a call range before anything is spent; `RunScore.calls_total` (new) lets the driver close the loop with what was really spent, and it warns if the actual falls outside the projection | One of the three call classes is genuinely conditional — pass 2 does not dispatch on a document that yielded fewer than two mentions — so a single confident estimate would be wrong in one direction and would teach an operator to ignore the line. Measured on the dry run: **13 calls/run**, i.e. pass 2 fired on 5 of 7 documents |
| **A candidate already failing a dry gate is not paid for** | `driver.blocked_before_spending` reuses `gates.dry_gates` — the same function `preflight` prints — and the driver skips those candidates by default, naming them and why; `--include-blocked` buys their diagnostic numbers anyway | A gate is pass/fail to win, so calls spent on a gate-failing candidate cannot change the outcome. On the shipped config `openai-gpt-5-6-sol` fails `keyless_equals_live`, so this is **a third of the budget**. Reusing preflight's own function is what stops the driver from skipping a candidate preflight called fine. UNKNOWN counts as blocked, exactly as it does everywhere else |
| **DEFECT FOUND AND FIXED: three "unmeasured" reasons blamed the gold for the candidate's failure** | `coref_binding` and both discriminator metrics reported "the gold slice carries no coref_cluster labels" / "labels no stated discriminators" whenever their denominator was empty. But the denominator is empty *either* because the slice is unlabeled *or* because *nothing aligned* — and on this slice **51 of 65 claims carry cluster labels and 95 discriminator slots are labeled**, so the message was simply false. `DiscriminatorTally.aligned` (new) lets the two causes be told apart, and each now names the real one | This is the wrong-file failure the coref channel's own cause reporting already exists to avoid: it sends an operator to the answer key to fix an extraction problem. In a measuring instrument a misattributed cause is worse than a blank, because it looks like a finding. Found only by running the driver — no test covered it |
| **The dry run's `INSUFFICIENT_CRITERIA` is the client's limit, not the instrument's** | Verified separately that **both required metrics are measurable on this slice**: with a well-behaved oracle `coref_binding` reads 1.0000 over 51 graded pairs and `discriminator_capture` 1.0000 over 47 captures; a model that binds nothing reads UNMEASURED (never 0), and one that over-clusters scores a real, poor 0.1166 | The dry client is corpus-blind on purpose, so its claims do not align and the two required metrics cannot be reached — which would otherwise leave "will a real run reach a verdict at all?" unanswered before spending $10–25. It will |

**Cost of a real run, corrected.** Prior estimate ~225 calls assumed three candidates. With the
gate-blocked candidate skipped it is **2 candidates × 5 runs × 8–15 calls = 80–150 calls**, and the measured
call pattern (13/run) puts the likely figure at **~130**, rising toward 150 as a stronger model triggers
pass 2 on all 7 documents. With `--include-blocked` it is 120–225, measured 195. Roughly **$5–15**,
dominated by Opus 5.

### RK-COREF (S3) adversarial review — five blocking defects closed (2026-07-25)

A review of the S3 stage found five blockers. All five were reproduced by measurement before being fixed and
re-measured after. The flag-off baselines are unmoved throughout: golden md5
`bb6f16a516c31eb0846494b62271a601`, full-scenario 169/80/71/20, booted 160/73/66/18/450.

| Decision | Why | → |
|---|---|---|
| **The coreference bind AUTHORISATION is gated on the stage flag, and the shipped top-level `coref_authoritative_evidence` goes back to `[]`** — S3's opt-in lives only in `earned_identity.authoritative_categories`, which is read only while the flag is on | The flag gated every S3 *restraint* (co-location cap, name cap, contrast ceiling, relationship wall, referent decline, C9 doc-scoping) and gated none of the *authorisation*, so a shipped flag-OFF deployment ran S3's permission with none of S3's limits — **strictly less safe than flag-on**. Measured flag-off: two co-located formations fused at `confirmed` (flag-on: `probable`, capped), a pair the document explicitly CONTRASTS fused at `confirmed` (flag-on: `probable`), and a bind licensed by d1 spread onto a profile built only from d2 | **Reverses** the earlier position that "what restrains a bind is neither the list nor the flag, only the gate": the *gate* legitimately stays flag-independent (it is a property of the pair), but *which categories an operator has authorised* is a stage decision and now rides the flag. The pre-S3 top-level knob is still honoured whatever the flag says — an operator who wrote it meant it. **Four false-inertness claims corrected** (yaml block header, rconfig module comment, `EarnedIdentity` docstring, field docstring); a claim of inertness that is not enforced is worse than no claim |
| **`Entity.namespace()` reads `origin_country`, and the un-normalised branch folds case + punctuation** — **fixed FLAG-ON only; flag-off still fuses the pair, deliberately** | `origin_country` is **the only country attribute the corpus states** (on manufacturers and trading organisations); `country` is stated nowhere. Measured: two same-named coref-linked trading orgs, one CHINA and one Pakistan, fused at `confirmed`, while the identical pair keyed on `country` was refused — **that refusal was a flag-ON observation**, and the row previously read as though the `country` control held in both directions. G19's fixtures all spelled it `country`, which is why the gate was green while the harm it names happened | **Flag-ON is genuinely fixed**: the pair now refuses to fuse, matching the `country` control. **Flag-OFF that same pair still fuses at `confirmed`** — but so does the identical pair keyed on `country`, and so did both at pre-fix HEAD `52080a4`. This is **not `origin_country` residue**: the entire Phase-2 cross-namespace refusal sits behind `if not cfg.earned_identity_on: return None` (`resolve/cluster.py:635`), so **flag-off has no cross-namespace wall on that path for ANY namespace key, and never had one** — the gap is structural and pre-existing, not introduced or missed here. **Accepted deliberately**, on three grounds: (1) flag-off **is** the currently shipped system, so accepting it changes nothing that runs today; (2) ungating the refusal would move the very flag-off baseline the S3 equivalence gate exists to protect — a materially larger call belonging to the **cutover**, not to a blocker fix; (3) the stage-flag discipline is that S3 machinery rides the S3 flag, and the namespace wall **is** S3 machinery. Separately, adding the key alone split the corpus's own SINO-GALAXY pair ('CHINA' vs 'China') into two nodes (169 → 170), because C7's value normaliser is flag-gated. So the raw branch folds through the same `fold_value` the normaliser uses: **case is never a namespace difference, with the flag or without it** — the *folding* genuinely is unconditional, the *wall* is not. Folding is byte-inert on the corpus on its own. G19's Phase-2 refusal and its must-fuse control are parametrized over both keys |
| **The three identity ceilings are declared once, in the stage block** — `contrast_band_ceiling` (top level) retired in favour of `contrast_ceiling` | They were declared twice under two spellings and the reader consulted the top-level copy first, so **editing the stage block was a silent no-op** — in the block whose own header promises to hold every threshold, cap and floor the stage adds. Setting all three to `confirmed` there produced possible/probable/probable | Guarded structurally, not by name: no key inside the stage block may also be declared at the top level (two deliberate shared reads named and excepted) |
| **An S3 flag-off equivalence gate exists and PINS the flag rather than inheriting it** | `tests/gates/` held only `test_s1_*` and `test_s2_*`, and the S2 gate contains no reference to `earned_identity` — under the ordinary run it *looked* like an S3 gate while asserting nothing about S3. Nothing in CI could have caught the blocker above | A gate that reads ambient config asserts "whatever is configured behaves as configured" — true of every system, interesting about none. Two ambient-leakage fixtures pinned as well, taking a flag-ON run from 6 failures to 2, and both remaining failures are **real S3 signal** (the stage moving the corpus graph, which for S2/S3 is the expected direction) rather than stale assertions misfiring |
| **G18's spec file stands on its own wall; the "differing designation veto" test is renamed to what it actually asserts** | Mutation-measured: delete the wall and the file went 11 passed / 1 failed; delete G16's co-location cap too and it went 5 passed / 7 failed — six tests were satisfied by the *cap*, not the wall. And **no differing-designation veto exists**: `designator` ships `{role: supporting}`, so a differing designator merely halves the discriminator sub-signal | Fixed the way ruling M15 fixed G19 — an agreeing `parent_unit` lifts G16's cap through the cap's own documented escape hatch, leaving the wall as the only possible refusal (wall mutation now fails 7 of 12; cap mutation fails nothing). **Disclosed, not fixed:** implementing the ladder's top rung means promoting `designator` to `critical`, which walls on exact value comparison — the objection that kept `service_branch` inert until `value_normalization` existed, and there is no equivalence class for '8' / '8th' / '8 AD Bn' |

**Design-note disclosure (required):** the discriminator ladder's top rung — *differing designation vetoes* —
is **specified but not implemented**. A differing designator is a soft penalty; what withholds a co-located
formation merge is the co-location cap, which caps at `probable` and hands the pair to the analyst. That is a
weaker guarantee than the ladder claims, and the honest statement is that the analyst decides.

**Design-note disclosure (required):** the **namespace identity wall is inert in the configuration that
ships.** The whole cross-namespace fusion refusal — including the `origin_country` key added above — is S3
machinery behind the stage flag, which defaults **off**. So in the shipped default, two same-named
organisations differing only in their stated country of origin can still fuse into one node; with the flag on
they refuse. The wall is a property of the *stage*, not of today's running system, and the honest statement is
that this class of protection arrives at the S3 cutover, not before it.

**Two verification caveats (non-blocking, recorded so they are not re-derived as surprises):**

1. **The S3 flag-off equivalence gate's net is one assertion wide.** It catches the blocker-1 class of leak
   (S3 authorisation running without S3 restraint) on exactly **one** assertion — the config-surface one.
   Under that same mutation the real-corpus **node / edge / gap counts do not move**, so the graph-level
   assertions contribute no detection there. The gate is real, but its coverage of that class is a single
   surface, not the corpus numbers beside it.
2. **`colocation_ceiling: confirmed` behaves identically to `probable` — "set it to `confirmed` to lift the
   cap" is false.** The cap is applied on a **truthiness** test (`if earned.colocation_ceiling:`,
   `resolve/cluster.py:642`), so any non-empty value still caps; and `record_cap` routes everything that is
   not `possible` into the same `capped_probable` bucket, so `confirmed` is a no-op relabel of `probable`.
   Only an **empty** value lifts the cap. These are pre-existing cap semantics, not something S3 changed —
   logged because the natural reading of the knob is the wrong one.

### AH-1 — an unresolved anchor must be loud on both surfaces (2026-07-25)

A tripwire anchored on a node id that no longer resolves watched **nothing** and said **nothing**: measured
on the real corpus, the flagship `obs-basing-relocation` fires 1 alert; re-point its `watch_instances` at an
id no node carries and it fires 0, with no exception, no log line and no surface change. Latent today
because the shipped anchors resolve — **live** the moment RK-NAMECUT re-keys node ids. Full probe + numbers
in the branch's session notes; fix on `fix/anchor-resolution-honesty`.

| Decision | Why | → |
|---|---|---|
| **Scope semantics are PRESERVED; only the diagnosis is new.** An observable whose anchors all miss still returns its (non-matching) `watch_instances` set, never `None` | `None` means *unscoped* to `evaluator._in_scope` — **match everything**. Deleting the literal seed at `observable.py:242` would convert a silent-no-alerts bug into a silent-**ALL**-alerts bug: every `based-at` change in the graph firing a unit-relocation tripwire, attributed to a subject it is no longer scoped to | **rejects** "empty scope = disarm" and "empty scope = unscoped" alike. The failure is made **loud**, not different. Pinned by `test_all_anchors_missing_keeps_the_non_matching_scope_not_unscoped` |
| **The raw-config-string seed is removed from the *success* path** — a watch instance contributes the id it actually **resolved to** | The seed was a **masking bug**: `resolve_scope` returned a set containing `unit_hq9b` while the real node was excluded, so anyone debugging saw the expected id sitting in scope. A raw string that is not a view node id can never match `_watched` (always a real node id), so it was inert — inert but misleading | Behaviour-identical by construction (a raw string that *is* a node id resolves literally and arrives via the BFS anyway); verified against the 169/80/71/20 baseline and the flagship's 1 alert |
| **Three failure modes are named separately, because they have opposite consequences**: *watching nothing* (narrowed to an empty set) · *unscoped* (silently widened to the whole graph) · *partial* (one good anchor laundering a bad one) | "watching 0 nodes" and "now evaluating every element in the graph" are not the same warning, and a partially-scoped tripwire is the shape that hides longest in the field | The sentence is composed **once**, in `observable._scope_warning`, and every surface renders it verbatim — so the API and the SPA cannot drift on what the fault means |
| **In-app anchor validation is a WARNING carried on the response, not a 422** | An anchor may legitimately be armed *before* the entity exists — "arm the tripwire, then ingest the document that creates the node" is a real workflow, and a hard rejection breaks it. Silence, by contrast, breaks nothing except the analyst's trust | Live check, re-run on every read against the current view (hot-config: no restart, no cached verdict, no boot-time-only validation). It clears itself the moment coverage creates the entity — pinned by `test_the_check_is_live_not_boot_time` |
| **The lens's `meta.anchors_missing` (present since AR-2, consumed by nothing) is routed into a first-class Known Gap** | A grep across `frontend/` and `backend/chanakya/api/` found zero consumers outside `lens.py` and its tests, so an analyst got a quietly smaller graph. A Known Gap is the object this system already uses for "what we do not know": it rides on `GET /view`, the retrieval tools read it, and it sits off the confidence scale rather than as a low score | Emitted **only** when an anchor misses, so a healthy lens is byte-identical. `next_coverage_due` stays `None` — this is a scoping failure with no source cadence behind it, and inventing a date would be the fabrication the gap exists to prevent; it names the fix instead |

**Disclosure for the design note.** The SPA never requests `GET /view?subject=` (`useLiveSync()` is called with
no subject), so there is no lens surface in the UI for the Known Gap to render on today; it is honest in the
API and in ASK's tool reads, not on screen. The *observable* half of the same fault **is** on screen — the
Watch panel and the rail's "Watching" row — because that is the path the flagship demo actually walks.

### AH-2 — "awaiting coverage" is not "broken": the honesty fix must not cry wolf (2026-07-25)

Integration triage of AH-1 against the **shipped default boot state**, not a fixture. `config/sources.yaml`
withholds `d18`/`d19` from the seed *on purpose* so a reviewer can ingest them live and watch the flagship
tripwire fire — which means `site_rahwali` legitimately has no node at first paint. Measured on a real
`create_app()` boot, AH-1 therefore reported **three** anchor warnings reading "…is NOT being watched, and
silence about it is not an all-clear", turned all three Watch cards live-bordered and made the rail read
"3 armed · 3 anchor unresolved · none fired" — on a healthy system, one ingest away from firing correctly.
The alarm was loudest while nothing was wrong and fell silent the moment the demo alert fired.

That is not a cosmetic problem. A monitoring surface that cries wolf while healthy teaches its analyst to
ignore it, which is the same failure as silence arrived at from the other side — and it landed on the hero
demo path at first paint.

| Decision | Why | → |
|---|---|---|
| **A missing anchor is split into `pending_coverage` vs `dangling`**, and only `dangling` is a fault | The discriminator was already free: `resolve/anchor.py` consults `config.entities.as_map()` as its rung-2 registry. An anchor that **is** a declared entity with no view node is a *coverage* statement; one that is neither node id, nor registry entry, nor alias is a *broken reference* — the actual RK-NAMECUT threat model | "Correct the anchor id" is now attached only to ids there is something to correct about. `site_rahwali` at boot reports as a coverage gap that "binds itself when a document creates it. No edit is needed" |
| **Severity, not the length of `missing`, drives loudness** — `ScopeResolution.severity` ∈ ok / pending_coverage / dangling / watching_nothing / unscoped | The three AH-1 modes were kept apart in the *wording* but every surface still rendered every entry identically loud | The rail counts faults only (boot caption is byte-identical to before); the Watch panel renders `pending_coverage` in its neutral register as "AWAITING COVERAGE". An **unknown/absent** severity still counts as a fault — an underclaim is as dishonest as an overclaim |
| **The warning names the config object that actually declared the anchor** | Two of the three shipped observables declare **no** `watch_instances` and inherit every anchor from the lens, yet each was told "this tripwire… correct the anchor id" — sending the analyst to `config/observables.yaml`, where there is no anchor to correct. One lens typo produced N identical misdirected warnings | `declared_in` maps each anchor to `watch_instances` or `subject:<lens id>`, and the sentence points at `config/subjects.yaml` when that is the file to edit |
| **`arm-only` observables are excluded from `anchor_diagnostics`** | Both `_fire` and `arm` return on `ARM_ONLY` *before* calling `resolve_scope`, so the scope is provably never consulted. Blaming an anchor for a silence that `explain()` already attributes, correctly and separately, to arm-only mode is a false alarm about an unused value | Not hidden: `explain()` still reports that observable's anchors in full |
| **Two silent-unscoping holes AH-1 left are now diagnosed** — a `subject:` naming no lens, and a lens declaring `anchors: []` | Both yield "match everything" with no error (`anchors: []` has no `min_length`; a dangling subject id 404s everywhere else in the codebase but is accepted here). The tripwire evaluates the whole graph while claiming a subject | **Scope is untouched** in both cases — same `None`, same behaviour — exactly as AH-1 decided. Only the silence is removed. A tripwire with no subject *and* no `watch_instances` stays silent: that config asked for a global tripwire |
| **`propose_observable_from_text` now passes its view/config to `explain()`** | The analyst's confirm screen is the one moment a tripwire's anchors are reviewed before arming, and it was the single production surface where AH-1's check reported "not performed" | Both arguments were already in scope; one-line change |

**Verified after the fix:** 169 nodes / 80 edges / 71 events / 20 gaps · flagship `obs-basing-relocation`
still fires exactly 1 alert (`unit_hq9b`, `site_rawalpindi → site_rahwali`) · its scope is still
`{site_rahwali, unit_hq9b, unit_paad}` with `severity: ok` · `anchor_diagnostics` is `[]` on the full view ·
S1 golden byte-identity gate passes · `ruff check` clean (AH-1 had left 2 `I001` errors failing `make lint`
and `make check`) · mypy back to the base 289 · 1222 backend + 196 frontend tests, `tsc --noEmit` clean.

**Still true, still disclosed:** the lens half reaches no UI surface (see AH-1's disclosure) — it is honest
in `GET /view?subject=` and in ASK's tool reads only. ASK has no observable/alert tool, so it cannot see the
*observable* half either; both are roadmap, not build.

### RK-BAKEOFF — the GPT candidate promoted to a production client, so the bake-off is a real three-way (2026-07-26)

All three candidates worked — each passed a live smoke call and the recorded imagery gate on a real corpus
frame — but `openai-gpt-5-6-sol` **could not win**, and not for any reason about the model. Its client had
been written at `backend/eval/extraction/gpt_client.py`, in the tree that *measures* candidates, and
`openai` was declared nowhere in the shipped image. That fails `keyless_equals_live`, and the gate is right
to fail it: KEYLESS==LIVE is the promise that a reviewer with no API key gets the same graph the live system
produces, and it holds only when the frozen seed bundles were produced by the same code the live extractor
runs. Code parked beside the harness can be measured; it can never be the producer that freezes the seed.

So the bake-off was quietly a two-horse race wearing three declarations, and the fix belonged where the
gate pointed — never at the gate.

| Decision | Call | Reasoning |
|---|---|---|
| **The client moved onto the shipped ingest path** | `OpenAIExtractionClient` now lives in `chanakya/ingest/client.py` beside `GeminiExtractionClient` and `AnthropicExtractionClient`; `build_extraction_client` gained an OpenAI branch, **appended** after Gemini and Anthropic | Placement is the gate's whole subject. Appending rather than inserting means every existing keyed deployment resolves to exactly the client it resolved to before — the promotion adds a provider, it does not re-point production |
| **`openai` was added to the shipped image, not just the dev box** | New `[openai]` extra in `backend/pyproject.toml`, installed by the Dockerfile (`pip install "/src/backend[gemini,openai]"`) alongside `[gemini]`. The floor is `>=1.66` — the Responses API — because an older SDK installs cleanly and then 500s on the first live call | A provider whose SDK is missing from the container cannot run live in it, so it cannot be the code that froze the seed. This is the second half of the same gate, and it is a real dependency decision rather than a config edit |
| **`[openai]` rides along with `[dev]` in CI and `make install`** | `pip install -e ".[dev,openai]"` | The client's offline tests monkeypatch the real SDK module, and the gate proves live-capability *by importing*. Without the package the tests would error at collection and the gate would read FAIL for a reason about the runner rather than the code — either one is a measuring instrument reporting on itself |
| **Only now is `freezes_seed: true` true** | The candidate's declaration in `config/bakeoff.yaml` flipped `client_module` to `chanakya.ingest.client` and `freezes_seed` to `true`, with the reason recorded inline | The flag was `false` because the placement made it false. Flipping it *first* would have been the bent-gate version of this change: a declaration asserting a property the code did not have |
| **The pinned id survived the move, and no reasoning knob came with it** | The class still takes `model_id` with **no default** (a wrong-but-plausible id cannot ride along); `DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"` is the pinned id the factory passes. No sampling parameter and no `reasoning`/`reasoning_effort` is sent on any call | The provider's own suggested workaround for function tools on `/v1/chat/completions` is "set `reasoning_effort` to `none`" — which would benchmark a deliberately weakened model under a pinned id, and would ship that weakened model to production. The client uses `/v1/responses` instead and the model keeps its native reasoning |

**Nothing about the gate changed.** `gates.py`, `production_client_package` and the pass/fail semantics are
byte-identical; the candidate passes because the condition is now satisfied, not because it was loosened.

**Verified.** `preflight` reports **3/3 ELIGIBLE** — all three PASS `vlm_imagery_path` (on the already-paid
recorded probe), `keyless_equals_live`, `pinned_model_id` and `exercisable`; the three non-negotiable metric
gates remain ahead of every candidate, as they should. Full suite **1792 passed / 7 skipped / 2 xfailed**,
`ruff` clean, mypy unchanged at its pre-existing baseline. **Zero API calls were made** for this change.

**Corrects an earlier ledger line.** The 2026-07-25 RK-BAKEOFF integration entry says "on the shipped config
`openai-gpt-5-6-sol` fails `keyless_equals_live`, so this is a third of the budget", and its cost estimate
is built on two candidates being paid for. That is no longer the state: a real run now spends on **three**
candidates, so the projection returns to roughly **3 × 5 × 8–15 = 120–225 calls**, ~195 at the measured
13-calls-per-run pattern. The driver's skip-the-blocked behaviour is unchanged and simply has nobody to skip.

### RK-BAKEOFF — the live run: no verdict, one real bug fixed, and a rate limit that stopped it (2026-07-26)

The authorised three-way live run was attempted. **It did not complete, so there is no primary extractor
and none was chosen.** Full report: `tmp/conv/RK-BAKEOFF-RESULT.md`.

Preflight was genuinely 3/3 ELIGIBLE — the GPT promotion held up and nothing was excluded by configuration.
Three attempts were made and each died differently; the first two were our own defect.

| Decision | What was done | Why |
|---|---|---|
| **No winner is recorded, because none was measured** | `run_bakeoff` raised before `decide()` on every attempt, so **no metric was computed for any candidate**. Two candidates' raw claim bundles survive on disk; they are reported in the result doc explicitly as *not* a ranking | This is the project's non-negotiable turned on its own instrument. Claim count is not a scored metric and more is not better — an over-extractor emits more claims and scores worse on the three veto lines. Naming a primary extractor on surviving bundles would be the exact failure the gates exist to forbid |
| **A real concurrency bug in the shipped Gemini client, found and fixed** | `GeminiExtractionClient._sdk_client()` had an **unguarded lazy init**. `extract_many` fans across threads, so every thread built its own `genai.Client`; the orphans' `__del__` closed transports that sibling threads were still using. Surfaced as `[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]` (attempt 1) and `Cannot send a request, as the client has been closed` (attempt 2). Fixed with double-checked locking, keeping the laziness that keeps the optional dep optional | Both failures look like network faults and neither is one. This affects **any concurrent Gemini ingest**, which is the shipped path; it was invisible because it cannot happen sequentially. Anthropic and OpenAI build their SDK client in `__init__`, which is why Opus completed 5/5 runs on all three attempts. Verified 15/15 clean at concurrency 8 on the real lane, then confirmed by Gemini's 5/5 clean runs in attempt 3 |
| **Transport faults are retried; returned responses never are** | New `eval/extraction/resilience.py` wraps the live client factory and retries only calls that **never received an HTTP response**. A 429, a 500, a refusal, a reply with no forced tool call is raised on the first attempt | A run is ~195 billed calls in one un-resumable process, so a single blip must not discard the comparison. But retrying a *returned* response would launder `structured_output_reliability` — the metric that exists to expose exactly that — inside the instrument built to measure it. The predicate treats any exception carrying a status code or response as final, whatever it is named |
| **A 429 was NOT retried, and NOT scored against the model** | Attempt 3 died on `gpt-5.6-sol` with an account cap of **3 requests/minute** ("Limit 3, Used 3" — no payment method on the account) | Correct on both counts. It is a returned response, so the retry rule leaves it alone. And it is a fact about the **account's billing tier**, not the model — scoring it as unreliability would let the bake-off pick an extractor based on which entitlement the operator happens to hold. Lifting it is an operator action (fund the account) or a harness feature (per-provider rate limiting, which does not exist — there is one global `--concurrency`) |
| **Stopped instead of buying a fourth attempt** | Cumulative actual spend **~330 calls against an authorised 225 ceiling**, with **Opus paid 3× (~225 calls) rather than 1×**, because it completed five full runs on every attempt and was re-paid each time | The standing instruction is to stop and report rather than spend when the plan runs materially above budget. A fourth attempt is another ~195 calls and still a gamble against a cap that cannot be fixed from this repository |

**The instrument itself came out well.** The spend plan printed before every attempt was accurate to the
call; the dry run walked the whole path at zero cost and correctly returned `INSUFFICIENT_CRITERIA` from a
scripted client; preflight blocked nothing it should not have. `gates.py`, the weights, the margin rule and
the match policy were **not touched** at any point.

**Known limitation, and the highest-value next change if this is ever re-run at this cost:** the harness has
**no resume**. Per-candidate scores live only in memory, so one exception discards every call already bought
— which is how ~225 Opus calls became unusable. Checkpointing a completed candidate's `CandidateScore` would
close that; the retry wrapper only closes the transport-fault case.

**Also stated in the result doc, so a future verdict is not over-read:** five of the slice's six source types
appear exactly once; 16 of 65 gold claims carry a role surface appearing nowhere in their document, so
absolute recall is capped for any verbatim extractor and only comparative numbers mean anything; binding
precision rests on 8 items; and cost is UNPRICED by design — while the operationally decisive cost factor
turned out to be a rate limit, which no metric in the config models at all.

### RK-BAKEOFF — the run becomes survivable: resume, per-provider pacing, and the coref block lifts (2026-07-26)

Three attempts at the live three-way bake-off died three times — twice on a Gemini concurrency race (a real
shipped-path bug, since fixed), once on `openai.RateLimitError` from an account capped at **3 requests per
minute**. `anthropic-opus-5` finished all five of its runs on *every* attempt and was **paid for three
times**, because the harness held everything in memory: one exception discarded ~225 already-billed calls
and produced no scorecard at all. Nothing was scored. Three things changed, and none of them is a
workaround for the thing they protect.

**1. The coref block lifts by merge, not by deletion.** `coref_binding` is the top-weighted criterion and is
declared in `required_metrics`, so an unmeasurable one returns `INSUFFICIENT_CRITERIA` — a completed,
perfect run would still have bought nothing. Preflight had been reporting the channel `UNAVAILABLE
[gated_off]`, blaming `resolution.earned_identity.enabled`. That was **stale**: `design/resolution-redesign`
deleted the staging flags outright and made the identity machinery, coreference producer included,
unconditional. Merging it reports the channel **LIVE with nothing flipped**. The tempting alternative —
dropping `coref_binding` from `required_metrics` to force a verdict — was refused: it converts an honest gap
into a silent one.

The merge conflicted only in this ledger (both sides append; both blocks kept) and turned 8 tests red. Every
one was the flag-deletion **seam** the `coref_channel` module had documented in advance, so the seam was
executed rather than the tests relaxed: `FLAG`, `_EARNED_IDENTITY_KEY`, the `GATED_OFF` cause with its
branch and remedy, and `with_channel_on` are gone. What replaced the last of those is `without_channel`, and
the reversal is the point — with pass 2 unconditional an operator can no longer switch it *on*, so the
remaining decision is whether to **decline to pay** for it. `--no-coref` had quietly become a lie (it set a
variable the run then overwrote from the now-always-live channel, printed LIVE and spent the second call
anyway); it now suppresses the producer block on that run's bundle only, and reads as the config gap it is.

**2. Resume, keyed at the document.** Each document's claims *and* its call records are written the instant
it lands, and a later invocation reuses them. Both halves are stored because three criteria
(`structured_output_reliability`, both discriminator lines, cost/latency) are measured **at the call** and
never reach a `ClaimRecord` — a claims-only cache would resume into a run whose reliability line was
silently unmeasured. Two rules are non-negotiable and tested:

* **A resumed run says so.** `determinism` is a measured, weighted line; runs stitched across sittings were
  sampled over provider-side change as well as model variance. The scorecard carries a provenance section,
  stamps the `determinism` row `cross-invocation`, and names `--no-resume` as the way to buy a
  single-sitting number. A wholly-replayed scorecard is separately marked "replayed, not re-run".
* **Changed inputs are never reused.** The key is the pinned model id + the document set (identity *and*
  content) + a prompt/schema digest **derived** from the shipped system prompts and every tool's live
  `model_json_schema()` — not a hand-bumped constant, which is the kind nobody bumps on the commit where it
  mattered. A fourth component is the **producer kind**: `--dry-run` walks the identical path with a double
  that reports the candidate's real `model_id`, so without it every dry run would leave bundles a live run
  would happily reuse and the scorecard would rank three models on invented text with every gate green. Dry
  runs also now default to their own output directory, so they cannot overwrite a paid run's receipts.

**3. Per-provider pacing, declared in `config/bakeoff.yaml`.** One global `--concurrency` was the wrong
shape: a cap is a property of an *account*, not a model. `rate_limits.openai` is set to the measured 3
req/min with `max_concurrent: 1`; anthropic and google are deliberately absent (= unpaced), because
inventing a cap nobody has hit would slow a lane for a fact not in evidence. Each candidate holds its **own**
limiter, so the capped lane is the only slow one. `--concurrency` now bounds documents in flight rather than
raw calls; rate is the knob that matters against a cap.

**The retry discipline is unchanged and was deliberately not widened.** Retry transport faults only; a
returned response is never re-issued, whatever its status. A 429 *is* a returned response, so the honest
answer to a cap is to stay under it — retrying one would launder `structured_output_reliability` inside the
instrument built to expose it. Pacing is that discipline's other half, not an exception to it.

**Measured, not asserted.** A full `--dry-run` walks the whole path for zero calls and reaches
`INSUFFICIENT_CRITERIA` — the correct dry verdict, since the scripted double declines to cluster and aligns
with no gold, leaving `coref_binding`, both discriminator lines and `kind_tagging` honestly unmeasured. The
throttle is exercised in that dry run against a virtual clock, so the wall-clock projection is the harness's
own arithmetic rather than a number worked out on paper: the GPT lane costs **13m–24m40s of pacing alone**
(40–75 calls at 20s spacing), the other two lanes run at full speed beside it, and a three-way re-run is
therefore ~30 minutes end to end and ~195 calls — of which nothing already on disk is re-bought.

### RK-BAKEOFF — the bake-off ran, and it REFUSES to name a winner (2026-07-26, `bakeoff/rk-impl`)

**DECISION: no primary extractor is selected. `claude-opus-5` and `gemini-3.6-flash` are measured
indistinguishable; `gpt-5.6-sol` could not be measured. The incumbent arrangement stands unchanged, and any
change to it is a human judgement made outside this measurement and must be recorded as one.**

Preflight was **3/3 ELIGIBLE** with the coref channel **LIVE**, the plan printed **120–225 calls (~195)**
before spending, and the slice carried the real corpus image, so the imagery gate read evidence rather than
UNKNOWN. **~177 calls actually billed** (174 persisted: Opus 75, Gemini 75, GPT 24; ≤3 lost in flight) —
**under the projection** — over **37m14s** wall clock.

**The result.** Five runs each. Composite (weighted mean per run of the nine weighted rate metrics): Opus
**0.6252 ± 0.0140**, Gemini **0.6157 ± 0.0269**. Gap **0.0095** against a required margin of **0.0429** —
the gap is 4.5× *smaller* than the noise it must clear. Verdict `NO_MEASURED_DIFFERENCE`. Both required
metrics were measured, so this is a measured tie, not `INSUFFICIENT_CRITERIA`. Nothing was re-weighted,
excluded or relaxed to produce it, and **no winner was manufactured out of jitter** — which is this
project's own non-negotiable applied to its own instrument.

**The vetoes split, and that is the decision-relevant finding.** Gemini is materially better on two of the
three non-negotiables (`citation_faithfulness` +0.044; `extract_only_stated` +0.030 — which clears the
absolute floor by 0.0002 and is the weakest material call on the board). Opus is materially better on the
third (`trap_avoidance` +0.127 over a 0.091 margin — the most robust single finding, on an 11-trap
denominator) and on `graph_recall` (+0.050). So there is **no free tie-break**: any pick trades one
non-negotiable against another in the open, which is the veto rule working rather than deadlocking. The
top-weighted criterion, `coref_binding`, is squarely inside noise for both (~0.35) — a finding about the
task, not a separator.

**Both surviving candidates keep the two structural properties the replumb depends on**, so neither is what
separates them: each passes `vlm_imagery_path` on evidence (recorded probe + **5/5 standalone-image calls
this run**, i.e. 6/6), and each passes `keyless_equals_live` because its client lives on the shipped
`chanakya.ingest` path and is declared the seed producer — a frozen seed bundle it produces is therefore
what live produces. Both ids are pinned: `claude-opus-5` and `gemini-3.6-flash` are concrete, not floating
aliases. Whichever a human eventually picks from the tied pair, the VLM path and KEYLESS==LIVE hold by
construction.

**`gpt-5.6-sol` is unmeasured, not judged.** Its lane stopped at 11 of 35 documents on **two independent
OpenAI account entitlements**: 3 requests/minute, then — once pacing cleared that — **10,000 tokens/minute
against ~6,500-token extraction requests**, which admits roughly one call a minute. Finishing it would have
cost ~52 more calls (~226 total, past the authorised 225 ceiling) and ~50 minutes, chasing a wall that had
already moved once. Stopped and reported instead. **The rendered scorecard does not mention this candidate
at all** — a narrowed run reports only what it ran — so the record lives in `tmp/conv/RK-BAKEOFF-RESULT.md`,
and nothing about that model's extraction quality may be inferred in either direction.

**One config change, and it is not a measurement knob.** `rate_limits.openai` moved 3 → **2 req/min**:
pacing at *exactly* the account cap puts three starts inside every trailing minute, so the fourth races the
provider's window boundary and any jitter loses. Pace **under** a cap, never on it. No gate, weight, margin
rule or match-policy value was touched, and the retry discipline is unchanged — a returned 429 is still
never re-issued, because `structured_output_reliability` exists to score what a provider returns.

**Resume earned its keep.** Attempt A died on the RPM cap having completed both unpaced lanes; attempt B
re-entered with **81 of 105 document-extractions reusable** and re-bought none of them; the final scorecard
was rendered from a **zero-call replay** and is stamped "Replayed, not re-run". Both scored candidates were
sampled in one sitting, so `determinism` (a weighted, measured line) means what it normally means. The
previous sitting's identical failure discarded ~225 already-billed calls and produced nothing.

**What this cannot decide, recorded so it is not discovered later:** five of six source types appear
exactly once (a per-type claim is an anecdote); 16 of 65 gold claims carry a role surface appearing nowhere
in their document, so absolute recall is capped for any verbatim extractor and only comparative numbers
mean anything (`surface_f1` ≈ 0.20 for both is a floor artefact, not a reading score); binding precision
rests on 8 items; and **cost is UNPRICED** — the operationally decisive cost this run actually met was a
rate limit, which no metric models. More runs cannot break the tie: the margin's absolute floor is 0.03, so
a 0.0095 composite gap is structurally immaterial. **A harder, larger labeled slice — more traps, more
negative binding pairs — is the only lever that would separate them.**

Full scorecard, arithmetic and interpretation: `tmp/conv/RK-BAKEOFF-RESULT.md`; machine-readable output and
the paid receipts under `tmp/rk-bakeoff/run/`.

### DEFAULT-ON — the identity re-key stops being a staged flag, and the loopholes the flags were hiding (2026-07-25)

Three stages of the identity re-key had landed **behind flags that shipped OFF**
(`ontology.yaml → layer_routing.enabled`, `resolution.yaml → earned_identity.enabled`, and the coreference
producer riding the second). The shipped build therefore ran without the machinery, and two of the dormant
mechanisms were the ones that close a **fabrication path**: a sub-confirmed or provisional identity promoted a
supersession anyway, the analyst's candidate was popped off the queue as "machine-adjudicated", the retired
assertion was restated `stale` (which in this system's own vocabulary asserts it *was* once confirmed), and a
differing target drew a relocation edge nobody reported. A safety mechanism you can switch off is a safety
mechanism the shipped build does not have.

| Decision | Why | → |
|---|---|---|
| **Both stage flags are DELETED, not defaulted true** — and with them the `--earned-identity=on` pytest switch, the flag-discovery test harness (`FLAG_TOKENS` / `enable_layer_routing` / `flag_report`), the two `test_s*_flag_off_equivalence.py` gates, and the row-level `requires:` / `earned_role:` markers in `attribute_roles` | A flag that still exists is still a second behaviour to maintain, and the two flag-off equivalence gates asserted *backward compatibility* — the thing the deletion gives up on purpose. Standing user directive: no dual path, no compatibility mode | Tunables (thresholds, caps, ceilings, vocabularies, floors) stay in config by rule. A row carrying a retired stage marker, and an `earned_identity.enabled` / `.attribute_roles` key, are now **loud load errors** rather than silently ignored — so the arrangement cannot come back |
| **`supersede_floor.require_earned_identity` is deleted too** | A boolean with no number to tune is not a policy dial, it is a switch for turning a prohibition off | Both R1.4 prohibitions are unconditional; the four consequences are pinned by `test_both_prohibitions_fire_unconditionally_and_the_gap_register_never_repeats_itself` |
| **A cross-type / cross-namespace refusal now raises a NAMED GAP per endpoint** | The cross-type wall un-fused a pair and routed *neither* half anywhere — no edge, no queue item, no gap — which is indistinguishable from two mentions that never resembled each other. Refusing to assert is half the non-negotiable; the analyst receiving it is the other half | Gated on "the evidence otherwise FUSED this pair", so T3b-A's noise argument survives: a low-scoring cross-type coincidence still earns nothing |
| **A type disagreement between two sources is SURFACED, not resolved** (Part 3 fork) | Fusing asserts a type neither source states; fragmenting silently hides the disagreement. A type conflict is an evidentiary contradiction — the class this system exists to surface | The pair stays two nodes, reaches the queue *with* "not fusable: cross-type (…)" when a source asserted the identity, and both endpoints carry a gap naming the adjudication needed. The corpus's HT-233 (typed `component` in one document, `variant` in another) is now two nodes: `xfail(strict)` + data-refresh ledger, **not** a weakened wall |
| **T3b-A narrowed: a cross-type pair may reach the queue when an ASSERTION put it there** | `_identity_pairs` silently dropped every cross-type source-asserted `same-as`, while the LLM-proposal channel beside it kept them — so the escape hatch the collection loop documents was fictional for the source channel. A source stating that a component and a variant are one thing is an extraction error, a typing error, or deception; all three are findings | The pair can never fuse (the wall is unconditional in both phases), so what the assertion buys is a queue place with grounds and a named gap |
| **A ceiling's VALUE means what it says**, and a value outside the band vocabulary is refused at load | The three ceilings were read as a truthiness test: `confirmed` behaved exactly like `probable`, and only DELETING the key lifted a cap. Config that reads as a decision the code never took is worse than a missing feature | Both halves, deliberately: honouring `confirmed` is only safe once a typo (`possibly`, `off`) cannot quietly take the withholding path |
| **A withheld pair keeps its REASON** — written for both tiers, surviving `finalise`, retained irrespective of `possible_floor`, listed in `GET /coverage` as `withheld[]`, and rendered on the drawn candidate `same-as` edge | `candidate_reasons` was written only on the `hitl` branch and then filtered to the candidate queue, so a pair capped at `possible` kept its score and lost its grounds — the common case for `area_of_operations`, whose only honest signal is its name. And no surface rendered the reason at all: the queue asked "are these the same?" with no way to see why the machine would not answer | "Retained but never surfaced" is a quiet drop with a confidence attached |
| **A coreference refusal states the ground it actually used** | The rationale fell back to the fixed string "the category is raise-only by policy" whenever the producer had stamped no detail, while the resolver had just computed the real ground and discarded it — then invited the analyst to accept the merge "if you read it the same way", on a ground that was not the one used | `_raise_ground` recomputes `may_bind`'s four tests in order. The licensing quote is now appended **beside** any cap's reason rather than `setdefault`-dropped by it |
| **`trading_org.origin_country` is promoted to `critical`** | It was held back on the stated ground that "promoting needs value normalisation first" — and its normalisation rows (CHINA/PRC/CN → China) were already shipped, so the reason had expired. Two same-named trading organisations in two countries is the costliest over-merge an operator-scoped supply-chain map has | Three rails keep it safe: the C7 normaliser (a spelling is never a conflict), `critical_veto_min_grade` (an untrustworthy conflict RAISES instead of walling), and C7's third state |
| **`resolve/places.augment` is deleted** | Its only caller was the flag-off branch; place identity is decided pre-fixpoint now (RK-COREF item 11) | Dead conditional branches removed rather than left unreachable |

**Expected-red, all corpus-data staleness, all `xfail(strict)` with the regeneration named in the marker** —
no fixture, corpus file or answer key was edited (working principle #3): the flagship relocation beat (2 tests)
and the withheld-seed relocation (2 tests) are HELD because `unit_hq9b`'s four derived basings state
`site_type` as *centre* / *deployment site* / *airfield* / *prepared revetment complex / airfield site* and
`layer_routing.site_type_aliases` is empty, so ruling L1's third state withdraws every supersede nomination on
that subject and names a gap — which its own corpus gate
(`test_the_flagship_relocation_is_held_while_its_site_classes_are_unknown`) asserts as correct. Populating that
alias map is a DATA judgement about the kind-of-place axis (ruling L1 step 4), not a threshold an implementer
may guess, so it is filed rather than guessed. Ledger:
`tmp/conv/DEFAULTON-calibration-and-data-refresh.md`.

**Disclosure for the design note.** The hero relocation beat does not fire on the frozen corpus until the
site-class alias map is authored. That is the anti-fabrication machinery working as designed — the system
refuses to call a change of site a *movement* when it cannot read what kind of place either end is — but it
means the demo's marquee alert is currently a **held** pair with a named gap rather than a fired tripwire.

---

### DEFAULT-ON — the analyst's decision LANDS, and a refused one says so (2026-07-26, `defaulton/rk-impl`)

Every item here was found by driving the live API over the **real booted corpus** (183/111/37) with an ASGI
test client, and every one of them returned `200`. They share one shape: **the system accepted an
instruction and did not tell the truth about what it did with it.**

| Choice | Principle invoked | Alternative rejected |
|---|---|---|
| **A learned do-not-merge is keyed on ENTITY IDS, always** (the name-keyed bar is kept beside it only when the two names genuinely differ, because that one generalises) | HITL is load-bearing: *overrides mutate graph state, not just a log*. The names that reach the replay are the analyst's **display** labels, and for the project's headline pair they are not the resolver's entity names — so the bar mapped back to zero entities and a `reject` on the two co-located batteries left `GET /view` **byte-identical**. An id is exact and needs no round-trip through a label | Making the route ship resolver-visible names. That keeps the decision hostage to a naming round-trip; the id is what the analyst actually clicked |
| **The analyst's wall joins `veto`** — the hard, transitive channel — not just `wall_grounds` | Registering the *ground* without registering the *wall* is how a human's REJECT became a comment: the pair kept its queue place and the resolver went on proposing the fusion | Leaving it as a reason-only annotation and relying on `finalise` to refuse the union. That holds the graph correct and leaves the analyst answering the same question forever |
| **One canonical pair may not carry both verdicts.** A walled pair is not drawn as a `same-as` candidate; the suppressed proposal's confidence and ground ride the wall edge | Measured at 7 of 14 after a reject: `finalise` prunes over RAW ids while the view draws CANONICAL pairs, and two raw pairs routinely collapse onto one. The graph asserted "same" and "not same" about one pair at once | Dropping the suppressed proposal silently. The analyst then sees a wall and never learns there was a case for merging |
| **`POST /hitl/merge` returns an `AdjudicationReceipt`** — received / applied / on what ground — **derived by READING the rebuilt view**, and an un-applied instruction is also stamped on the drawn edge so it survives a reload | A silent `200` on a refused instruction is the *escalate* half missing on the **write** path. The cross-type rail refusing to fuse a `component` with a `variant` is correct; saying nothing about it is not | An `applied` flag derived from "did the write succeed". That reports success whenever the log append worked — which is exactly the claim that was false |
| **`HitlDecision.actor` is typed at the boundary** (`actor: 'audit'` → 422, not a 500 with a traceback) | A 500 makes a *rejected* adjudication indistinguishable from a server fault — the same confusion class as a dropped decision | Catching the `ValidationError` deeper in `writeback`. Validation belongs where the request arrives |
| **Every Known Gap carries a derived `coverage_statement`** — the date and the interval where the registry supports one, and otherwise which class *could* close it and why that class has no revisit date | The non-negotiable has two clauses. 34 of 37 gaps met the second with a bare `next_coverage_due: null`, which states nothing. **A fabricated collection date would itself be a fabrication**, and the worst kind, because it is actionable | Inventing a cadence, or leaving the null. An honest "no scheduled coverage; this closes only if a new source appears" is compliant; silence is not |
| **A slot absent from the slot→source-class map no longer means "any class can close it"** | Declared-empty means any class; *absent* means nobody has declared who could. Conflating them let an identity question inherit the satellite constellation's 7-day revisit and be reported as "next coverage due <date>" — a collection promise no satellite pass can keep | Keeping the permissive read for convenience |
| **One (node, statement) is one Known Gap**; the collapsed ids ride the survivor as `also_raised_as` | 14 identity gaps were 4 distinct (node, statement) pairs — one node received the identical sentence five times in a single drawer. Five renderings of one finding read as five findings, which is how a register teaches an analyst to skim it | Collapsing the record as well as the presentation |
| **A watch-list pair with no recorded reason gets its own honest ground** ("reached the review band on its own evidence and stopped short of the bar…", derived from its confidence against the configured bar) | `GET /coverage` is the ONLY channel carrying the `possible` tier, and it listed only pairs a *mechanism* had withheld — so 24 of 355 reached no surface at all. "No cap fired" is not a reason to be invisible; it is itself the reason | Continuing to omit them to avoid over-claiming a cap. The ground says explicitly that no cap was involved, so the over-claim is avoided without the drop |
| **A fragment proposed against BOTH sides of a hard wall says so**, and names the discriminator it is silent on | A single-claim unit stating no `service_branch` was a live candidate against both an Air Force and an Army formation the critical-attribute rail holds apart. **A missing discriminator must not read as permission to cross a wall** | Withholding those pairs. Settling which formation a mention names is exactly the judgement a human is in the loop for; what was missing is that the two proposals are mutually exclusive |
| **`stale` is conditioned on the assertion having reached the CONFIRMED magnitude** | "We knew this and the world has moved on" is a claim about the **past**. A mid-band assertion (probable floor ≤ conf < confirmed) was an open question the whole time, and relabelling it `stale` on supersession told the analyst it had been established when it never was | Leaving the bar at the `probable` floor (closes only the bottom of the hole) |
| **…but NOT on `min_independent_groups` — a stated partial close** | Tightening to the full confirmed bar strips `stale` from an assertion that reached the magnitude on a **single** look, which is the shape of this project's flagship relocation beat, across eight behavioural specs including the one named "the flagship shape". Rather than flip that quietly, the shortfall is **recorded**: such an assertion carries `superseded-single-look` in its gate vector. **Recorded, not surfaced** — `gate_vector` has no consumer outside its producing module, so that marker is audit-trail only (ledger item 7); what the analyst sees is *that* it was retired (`superseded_by`, `integrity_flags`), not how thinly | Flipping it silently, or claiming the defect fully closed |
| **The SPA renders a wall's ground** (`drawerIdentity` → the provenance drawer) and marks a queue item the analyst already answered that was not applied | `identityReason()` existed and was wired at exactly one call site, so a *wall's* ground reached no SPA surface at all — and a wall carries no confidence and no card, so the ground is the whole finding | Carrying it only on the API and filing the SPA half. Most walls here are DERIVED inferences the analyst is in the loop to check |

**Corrected in our own records (this is the point of the entry).** `tmp/conv/DEFAULT-ON-calibration-ledger.md`
item 1 and the two `xfail(strict)` reasons it backs asserted that the `possible` watch-list "reaches no
surface". That was **measurably false** — `GET /coverage` shipped and returned 331 of 355 pairs with both
endpoints, the confidence and the full reason. The entry is corrected in place (original struck, kept for
audit) and the markers now state the true residual: the tier is not drawn on `GET /view` (deliberate) and
**the SPA never calls `/coverage`**. A false claim inside a green artifact switches off the next reader's
scepticism, which is the one thing a calibration ledger exists to keep switched on.

**Declared red (no fixture, corpus or answer key edited).** `expected_view.json` predates
`coverage_statement`/`also_raised_as` and differs by exactly those two fields → 2 `xfail(strict)`; G2's real
property is still enforced by its siblings (two in-process rebuilds byte-identical, identical across three
`PYTHONHASHSEED`s). One supersede fixture carrying `assertion_confidence` 0.0 under a `probable` floor of 0.0
→ 1 `xfail(strict)`. Ledger items 5 and 6.

---

## FINAL TRIAGE — identity is UNCONDITIONAL, and an analyst's decision now MUTATES the graph (2026-07-26, `defaulton/rk-impl` → `design/resolution-redesign`)

The close-out of the DEFAULT-ON pass. Everything below was re-verified at triage against the running code
and a live boot, not accepted from the implementer's or the verifier's report.

### 1. Identity is unconditional — the flags are DELETED, and reintroducing one is a loud error

Both staging switches are **gone from the tree**, not defaulted to on. More importantly the loophole is
patched in both directions, so the flag cannot come back by accident:

- `supersede_floor.require_earned_identity` — deleted. `config/credibility.yaml` now carries an explicit
  *"There is NO KNOB here"* note in its place, and `credibility/supersession.py` states the doctrine: **a
  gate that closes a fabrication path is not a policy dial.** It was a boolean with no number to tune, i.e.
  a switch for turning a prohibition off.
- The row-level markers `requires: earned_identity` and `earned_role:` — deleted, and registered in
  `resolve/rconfig.py` as `_RETIRED_STAGE_KEYS`. A row carrying either is now a **construction-time
  `StageBlockError`**, on the stated ground that *a tolerated staging marker is a compatibility mode with a
  shorter name*, and that a silently-ignored `earned_role: critical` would quietly **demote a wall the
  author meant to declare**. Same doctrine applied to `earned_identity.*` keys with no consumer: refused at
  load rather than ignored.

That is the difference between "the flag defaults to on" and "there is no flag": the second cannot drift.

### 2. The analyst's decision lands — the HITL rule, mechanised

The project's HITL rule is that **overrides mutate graph state, not just a log**. Measured on the real
booted corpus, that was false in the most literal way available: a `reject` on the headline pair returned
`200` and left `GET /view` **byte-identical**. Three independent causes, all closed and all pinned by a new
corpus-driven gate spec (`tests/gates/test_the_analyst_decision_lands_spec.py`, 11 tests):

- the learned bar was keyed on **display names**, which are not the resolver's entity names — so it mapped
  back to zero entities. Now keyed on **entity ids**, always.
- the analyst's wall only decorated `wall_grounds` and never joined **`veto`**, the hard+transitive channel —
  so the resolver went on proposing the fusion the human had just refused.
- a refused instruction said nothing at all. `POST /hitl/merge` now returns an `AdjudicationReceipt` whose
  verdict is **derived by reading the rebuilt view**, never from "did the write succeed"; and an un-applied
  instruction is **stamped on the drawn edge**, so the acknowledgement survives a reload.

Measured, before → after, across all 14 candidate pairs: reject — 1 wholly inert, 8 still drawn, 0
acknowledged → **0 inert, 0 still drawn, 14/14 acknowledged**. Accept — 3 silently inert → **14/14
acknowledged**, with the 4 the cross-type rail correctly declines reporting `applied=false` and naming both
ontology types. Contradictory identity edges (one canonical pair asserted both same and not-same): **7 of 14
→ 0**, and still 0 after working the whole queue to empty and restarting over the accumulated log.

### 3. Rulings issued, and what they cost

| Ruling | What it settles |
|---|---|
| **A missing discriminator is not permission to cross a wall** | A fragment proposed against *both* sides of a hard wall now says so, names the twin proposal, states at most one can be true, and names the declared-critical attribute it is silent on (`service_branch` for the PAAD case). Both pairs stay adjudicable — deciding which formation a mention names is exactly the human's job |
| **An assertion that never reached `confirmed` cannot age into history** | `stale` means "we knew this and the world moved on" — a claim about the **past**. A mid-band assertion was an open question the whole time. **Partial close, stated twice over** — see §5 |
| **Declared-empty ≠ absent** in the slot→source-class map | Absent means *nobody declared who could close it*. Conflating the two let an identity question inherit the satellite constellation's 7-day revisit and be reported as a collection date no satellite pass can keep |
| **"No cap fired" is not a reason to be invisible** | 24 of 355 watch-list pairs reached no surface anywhere because only *mechanism*-withheld pairs recorded a reason. They now carry a ground derived from their own confidence, which states explicitly that no cap/wall/assertion was involved |
| **One (node, statement) is one Known Gap** | Five renderings of one finding read as five findings. Collapsed in *presentation only*; the suppressed ids ride the survivor as `also_raised_as` |
| **A gate that closes a fabrication path is not a policy dial** | §1 — why the two flags were deleted rather than defaulted |

### 4. Corrected in our own records — twice, and the second one is ours

The pass's own headline was correcting a **false claim in a green artifact** (ledger item 1 asserted the
`possible` watch-list "reaches no surface"; `GET /coverage` had shipped and returned 331 of 355 pairs with
endpoints, confidence and full reason text).

At triage the verifier found that this pass had then introduced **a fresh instance of the same thing**:
`gate_vector` is computed, and consumed by exactly one unit test — it is not on `NodeView`/`EdgeView`, not
in `GraphView`, not on the API, not in the SPA. Four strings claimed it let an analyst *see* how thinly a
retirement is evidenced, including `status.py`'s docstring line "for the provenance drawer". **All four are
corrected in place** (new ledger item 7); no behaviour was changed. What genuinely is visible on a retired
edge is `superseded_by` and `integrity_flags: ['superseded']`, both on the view schema and both read by the
SPA — so *that* it was retired reaches the analyst, *how thinly* does not. This is **pre-existing** (every
older marker is equally invisible) and **moot on both graded boots** (nothing exercises the supersede path
there), so it is filed, not built: putting the gate vector on the view schema is a new analyst surface, and
the endgame rule is *don't start new capability*.

Recording this because it is the second time in one pass that the failure was **a computed judgement that
never reaches the human**. That is the shape to look for here, and a green suite does not catch it.

### 5. Stated honestly: what is NOT closed, and what this corpus never exercises

- **The `stale` tightening is a partial close, on two counts.** It is conditioned on the confirmed
  *magnitude* but **not** on `min_independent_groups`, because the full bar flips this project's flagship
  relocation beat from "history" to "open question" across eight behavioural specs. And the compensating
  marker (`superseded-single-look`) is **audit-trail only**, per §4. Both halves are named rather than
  papered over. Closing the first is a one-line change plus a decision about those eight specs.
- **A machine cap can overrule an explicit human ACCEPT.** On the headline pair, `accept` returns
  `applied=false` — the co-location cap wins. This is the **safe** direction and is precisely what prevents
  the fabricated relocation, and it is acknowledged with an accurate ground rather than silently ignored.
  But it *is* a case where an override does not mutate state, which is the inverse of the HITL rule, so it
  is a deliberate exception to be **explained on the call, not discovered live**.
- **Unexercised on the frozen corpus** — stated so nobody reads a passing suite as evidence these work:
  `attrs.suppressed_candidate` fires on **0 of 34** walls at boot and 0 of 48 after working the queue; the
  supersede path is touched by **zero** elements on either boot (183/111 keyless, 196/123 full); the hero
  relocation beat remains **held** behind the unauthored `site_type_aliases` map (a DATA judgement, filed).
  These are tested on fixtures and inert on the real data — the "graded beats inert" category.
- **The frontend is unverified by any compiler.** `frontend/node_modules` is absent in the worktree, so
  neither `npm run typecheck` nor vitest ran against the SPA changes. They are additive and every new read
  is a `typeof`-guarded cast, but **run `npm ci && npm run typecheck` before the demo** — this is the one
  claim in the pass that nobody has tested.

### 6. Owed to the design note

Filed into `artifacts/md/16-design-note-disclosures.md`: the HITL inversion (a cap overruling a human
accept, and why that is the safe direction); the `stale` partial close and its audit-trail-only marker; and
the honest statement that several credibility/identity beats pass on fixtures while being inert on the
frozen corpus.

---

## RK-DATA — identity coverage authored, and the `site_type` map landed (2026-07-26, `rkdata/author`)

Three anti-fabrication mechanisms were built, tested on fixtures, and **provably inert on the real corpus
for want of input**. Verified independently before writing anything, across both scenarios (30 claim
bundles / 492 claims / 72 doc files): **zero** numbered or designated formations — the `unit` type held only
services and commands — **zero** equipment serials or registrations, and **zero** coreference annotations.
So the discriminator ladder, the coreference binding tier and gates G16/G18/G19 had nothing real to grip.
Six additive documents (`n01`–`n06`, `hq9p_primary`) close that. Full spec, per-document corruption
operators and the must-produce / must-refuse statement for each: `tmp/conv/RK-DATA-authoring-spec.md`.

### 1. `layer_routing.site_type_aliases` — three entries, and the omissions matter as much

**Choice.** Populated the map ruling L1 step 4 assigns to DATA: `centre`→`garrison`,
`deployment site`→`dispersal_site`, `prepared revetment complex / airfield site`→`airfield`. Measured on a
real rebuild: all four of `unit_hq9b`'s stated site classes now normalise, the flagship
**Rawalpindi→Rahwali relocation is restored** (`edge:unit_hq9b:based-at:airfield`, one supersede drawn), and
the **Karachi `garrison` and Sargodha `dispersal_site` basings de-conflict into concurrently-valid ones** —
no relocation between them. This closes the "hero relocation beat remains held behind the unauthored
`site_type_aliases` map" item filed in the FINAL TRIAGE §5 inert list above.

**Principle.** *Keep config in config; the honest fix is a fixed value in a config file.* The mapping is a
domain judgement about the kind-of-place axis, which is why the ruling assigned it to DATA rather than
letting an implementer guess a threshold.

**Alternative rejected.** Mapping all fifteen stated values. Nine of them carry **no kind-of-place content
at all** — they state how we learned of the site (`observed-imagery-site`, `stated_destination`), what is
parked there (`HQ-9/P site`, `air defense node`, `long-range SAM battery position`), an area class
(`candidate coverage area`, `air defence belt`, `forward SAM deployment area`) or an operator class
(`Pakistan Army/PAF joint-use facility`, whose only place-kind noun is the generic "facility"). Mapping
those would infer a kind of place from something that is not one, which is the exact over-merge direction
the fail-safe leans against, and two of them would have manufactured collateral relocations. They keep the
honest third state — held, no fusion, named gap — and the config comment names each omission and why.

**Two strict-xfail markers retired** in `backend/tests/acceptance/test_relocation_beat.py`, exactly as their
own "TO CLOSE" text instructed. The third state was **not** weakened.

**Residual, stated not hidden.** `site_rahwali` is described two ways in the corpus (`airfield` in d18,
`Pakistan Army/PAF joint-use facility` in d19) and which lands on the node depends on claim ordering. If the
re-record picks the operator-class string the flagship silently returns to held-with-a-gap — safe, but a
silent demo regression. Fix it on the data side; do not close it by mapping an operator-class string.

### 2. The ORBAT undercount trap — the thing the corpus most lacked

**Choice.** Authored two genuinely different, individuated batteries **co-located at one garrison** (22 AD
Regt under 3 AD Bde and 47 AD Regt under 11 AD Bde, both at Pano Aqil Cantonment), reported across separate
documents that never state the distinguishing field in the same place. **No planted lie — every report is
accurate.** They share design, site, operator branch and equipment class, i.e. every one of
`colocation_predicates` **by construction**, which is exactly what a naive resolver reads as overwhelming
identity evidence.

**Why it is anti-fabrication machinery and not ORBAT hygiene.** Fusing them makes their two positions one
unit's before-and-after; `based-at` is functional and unit-keyed, so the supersede path then **draws a
relocation that never happened**, marks the pair machine-adjudicated so it leaves the analyst's queue, and
**deletes the honest Known Gap** on the count. One identity error becomes a fabricated movement assessment
with the human removed from the loop.

**The correct output, stated so it can be graded:** two units not one (co-location cap holds at `probable`,
reinforced by n05's same-document stated contrast); **no relocation anywhere in the cluster**; and a
**named gap** on how many long-range fire units are at that cantonment, naming what is missing — an ORBAT
source attaching a formation to a *position*, or an equipment identifier tying a vehicle to a *unit*.

### 3. Two judgement calls a reviewer should re-derive rather than accept

- **`n04` splits source class from source grade** — `named-social` (a contributor vehicle register; low
  authority, R≈0.35, so nothing it *concludes* travels far) with STANAG **C** earned by its *process*:
  every entry photo-backed, disagreeing plate readings published rather than resolved silently, and the
  `8417`→`8477` misreading carrying its own correction log. Grade C is what lets a photographed, corrected
  plate reading clear the `bind_min_grade` / `critical_veto_min_grade` floors — right, because directness is
  the one thing that source class genuinely has.
- **d23's circular-corroboration chain was NOT extended with a fourth echo.** A fourth reshare exercises no
  mechanism the existing three don't, and the corpus already carries a six-post echo burst. What d23 lacked
  was the *other* side: a genuinely independent second look that **disagrees** (`n06`), which converts it
  from a single-mechanism test into a graded one — three citations collapse to one look, and a real second
  look in contradiction makes the count a **named gap with two sourced assessments attached**, never an
  average and never "trust the higher grade".

### 4. Not touched

`answer_key.json`, every existing document, every existing claim bundle (all 492 frozen claims intact),
and `SCENARIO_MANIFEST.json` (generation output; the re-record regenerates it). ~~`config/places.yaml`~~ and
~~"the new documents carry no claims"~~ are **both superseded by RK-DATA rev 4 below** — the missing
gazetteer row for the station was the defect that made the trap vacuous, and the six documents have since
been extracted with a real key. The
`superseded_derived_bundle_suffixes` comment says "RK-DATA removes the bundles from the corpus" — **not
done here**, because deleting claim bundles is outside this pass's mandate; the flag-gated skip already
handles it.

---

## RK-DATA rev 4 — the co-location trap, proved by experiment (2026-07-26, `rkdata/author`)

Two earlier versions of this trap were **vacuous**, and both times a reviewer found a different rail
intercepting the pair before the co-location cap could. The third reviewer found the last one the only way
it could be found — by **running the experiment** rather than reasoning about rails. This entry records
what that measured, what changed, and the result, because the label now carries two rounds of credibility.

### 1. The defect: a station with no identity anchor

`Pano Aqil` in any spelling appeared **nowhere** in `config/places.yaml`, while every other station this
corpus uses — Nur Khan, Rahwali, Karachi, Sargodha, Gujranwala — has a gazetteer row. Consequence, measured:
two mentions of one station could only meet on their *name*; `name_ceiling: possible` fires on a name-alone
pair; the stations stayed two nodes; the batteries standing at them shared no neighbour;
`colocation_only()` early-returns on `bd[RELATIONAL] <= 0`; **the cap never ran.** Worse than a miss — the
NAME ceiling withholds the pair from the analyst's queue as well as from fusion, so the trap produced no
HITL item at all, the exact opposite of its purpose.

### 2. The fix, and why this form

`pl_pano_aqil`, `precision_class: site` — the standing Rahwali Cantonment already has, and the load-bearing
field: `site` is inside `place_identity_precision_classes`, so "both resolved here" may become "both are
this place". A cantonment is a *thing*, not an area of rough whereabouts. The `site` radius is jitter
absorption around the centre, **not** the cantonment's extent, so the two revetted launch positions the
imagery read-out fixes 2.3 km and 3.4 km away stay their own emplacements and are raised for an analyst
rather than swallowed into the station.

**One variant is deliberately withheld** — `Panu Aqil` — on the `pl_nurkhan`/"Chaklala" pattern. Chosen
because it is the only spelling the corpus uses as a real location *value* rather than only inside a
spelling note (the register's carried-forward 33 AD Regt entry; the vehicle register's duplicate entry
AD/2025/019), so the withholding costs something real and is therefore a test. It is off the trap's path.

### 3. Two rows written, then WITHDRAWN on measurement — the finding is worth more than the rows

`pl_sukkur` and `pl_ghotki` were written as ordinary AREA anchors on the same reasoning the file already
carries for Karachi and Punjab: the documents state "Sukkur District, Sindh" verbatim, so the claim should
land somewhere. **Measured, they did active harm.** INGEST freezes a location phrase onto the entity, and
for a station written "Pano Aqil Cantonment, Sukkur District, Sindh" the phrase it froze was the ADMIN
PARENT. With a Sukkur row present the geocoder stamped the *city's* coordinate onto a station-level node;
`resolve_place` then matched the node's own toponym against `pl_pano_aqil` and **dropped the match**,
because the attached coordinate sat ~30 km away, outside the `site` radius. The station stopped resolving
to any anchor at all.

**The general rule this yields:** an area alias that can capture the admin-parent tail of a SITE-level
address will hand that site the area's coordinate, and a coarse coordinate on a fine node is not a harmless
approximation — **it is a veto on the node's own name.** The proper fix (prefer an exact curated toponym
over a coarser geocode of the same mention) is a place-layer change, not a gazetteer row. Roadmap.

### 4. The experiment, and its actual output

2×2 on the real corpus with real keyed extractions and the shipped config. Only two things varied: the
ceiling, and whether `pl_pano_aqil` exists.

| | `colocation_ceiling: probable` (shipped) | `colocation_ceiling: confirmed` (relaxed) |
|---|---|---|
| **anchor present (shipped)** | **not fused, QUEUED** — reason names the cap and names `equipment_fingerprint` / `parent_unit` as what would lift it | **FUSED** |
| **anchor removed (control)** | not fused, **not queued** — watch-list only, reason = name cap | not fused, **not queued** — name cap |

Top row is the bar, met: **the cap is the sole load-bearing restraint.** Bottom row reproduces the
reviewer's defect exactly and is the proof the anchor is what closes it. `relational` on the pair: **0.167
with the anchor, 0.0 without.** The transliteration demo is live rather than inert — with the anchor,
"Pano Aqil" / "Pano Aqil Cantonment" / "Pano Aqil Cantt" fold onto one station; without it they are three
stations. The withheld "Panu Aqil" stays its own un-anchored node, still to be earned.

### 5. What this cost, stated plainly

- **The six `n0*` documents now carry claims.** They were extracted with a real key (`claude-opus-4-8`,
  `--offline` geocoder) into six new `n0*.json` bundles. No existing bundle, document or `answer_key.json`
  was touched.
- **Three document changes were needed beyond the anchor**, and all three remove *extraction artefacts*
  rather than add evidence: §3.7 of the register now uses the same labelled-field convention as §3.4 (as
  prose it produced an entity with no edges at all); both battery mentions state the station in a form the
  extractor turns into a `based-at` rather than only a `home_garrison` attribute; and the two documents
  deliberately render the station *differently* (register "Pano Aqil Cantonment", ISPR "Pano Aqil Cantt")
  so the site merge can only happen through the gazetteer.
- **Known limitation, measured and NOT closed.** `places.place_matches` runs *before* endpoint minting, so
  a station named only as the object of a `based-at` never reaches the gazetteer even when its string is a
  seeded alias — which is why "Pano Aqil Cantonment, Sukkur District, Sindh" is still its own node. A
  RESOLVE pass-ordering issue, not a gazetteer one. Roadmap.
- **`coref_authoritative_evidence` is empty in the shipped config**, so a document's own coreference between
  a long mention and its later short form never binds. Noted because it was the first route tried for
  giving the trap pair a shared neighbour, and it is inert by configuration, not by accident.

### 6. Surviving adjudications stripped from the documents

The reviewer found three places where a document *argued the conclusion* instead of reporting an
observation. All replaced with observational forms, none deleted outright:

- `n05` — the 47 AD Regt note no longer says the regiment is "administered separately from 22 Air Defence
  Regiment notwithstanding the shared station and the shared equipment class". It now records only what a
  lineage sheet holds: a lineage, a commanding officer and an establishment table under that entry.
- `n04` — the duplicate entry's note no longer says the submission "was not caught by the de-duplication
  pass" ("failing to catch" presupposes there was a duplicate, which is the verdict). It states the
  observables only: same archive reference, same plate, same date, same occasion.
- `n04` — the frame note no longer explains *why* the entry exists ("8471 and 8477 are the pair our own
  8417 misreading would have muddled"). It records what the frame shows: both plates legible side by side,
  differing in the third digit.

### 7. A separate defect the experiment surfaced: `n04` was extracting ZERO claims

Found while making the corpus consistent, unrelated to the trap, and it had nothing to do with the
document. `source_type` is not only the credibility class — it is also what **selects the extraction
schema**. `n04` was filed `named-social` on the (recorded, deliberate) reasoning that a contributor vehicle
compilation has a social source's lack of standing. Filed as social, the register was handed the
**social-post tool** — handle, timestamp, status URL, body — which it cannot fill. The document extracted
**zero claims**: the plate-discrimination beat, the disputed chassis reading, the `8417`→`8477` correction
log and the duplicate entry were all mute.

**Fix: a new `contributor-register` row in `source_class_factors`** (`authority 0.20 / process 0.70 /
directness 0.75` ⇒ **R≈0.56**), and `n04` retyped onto it. The two existing rungs were both wrong in a way
that could not be fixed by picking between them: `named-social` has the right authority and the wrong form,
`curated-register` has the right form and SIPRI's authority — filing a hobbyist compilation as a treaty
database is credibility inflation in an anti-fabrication system, which is the wrong direction to err. The
new rung gives credit for **method and for having taken the photograph, never for standing**. Measured
after the change: **19 claims**, including the plate distinct-from pair and the `WS2400`/`TAS5380` chassis
disagreement. `reliability_grade: C` is unchanged.

### 8. A stale acceptance assertion, narrowed — and why this is not "editing a test to go green"

Running the suite over the new bundles turned one acceptance test red, and it took three document rewrites
to work out that **the data was not the problem**: each time a pair was removed, the same shape reappeared
from a different document ("Ghotki position" ⇄ its coordinate form, then "Pano Aqil Cantonment" ⇄ its admin
form, then "Okara Cantonment" ⇄ "Okara Cantonment, Punjab"). That is a structural pattern, not a bad string,
and chasing it further would have been exactly the "make the demo deterministic" smell CLAUDE.md warns about.

`test_no_source_asserted_signal_means_no_citation_to_click` asserted **"`source_asserted == 0` ⇒ the edge
cites nothing at all."** That mirrored the era when a candidate edge's `claim_ids` were
`scoring.identity_claim_ids` (the set that mirrors the score). `resolve.__init__` was later changed **on
purpose** to render `scoring.licensing_claim_ids` instead, and its own comment states the reason: a
raise-only coreference proposal *is* a source speaking to the pair, the referral is its entire product, and
under the narrower set it reached the analyst **with an empty drawer** — the one-click-to-source
non-negotiable failing on the one card where the sentence is the whole case. `licensing_claim_ids`'
docstring says the same thing from the other side.

So the assertion contradicted the shipped design, and had been passing only because the frozen corpus
happened to contain no coref-only candidate pair. The RK-DATA documents — the first written in a register
style that names a place both bare and with an admin tail, and the first carrying explicit coreference
prose — are simply the first to reach it.

**Narrowed, not deleted.** The test now pins the invariant the design actually holds: an edge scoring no
identity signal may cite a **coreference** claim, but must never cite a claim in which a source *asserted*
the identity — that would be the number and its evidence handle contradicting each other, which is what the
test was written to prevent. Renamed to `test_a_zero_score_never_cites_an_identity_assertion` so the name
states the invariant rather than the old mechanism. **The production code is untouched.**

### 9. Two more document defects the suite caught, both mine, both fixed in the documents

- **`n03` used ALL-CAPS position headings.** Entity ids are case-sensitive, so "SOUTH-EAST POSITION" (the
  heading) and "south-east position" (the prose) became two nodes of the same type and name — which is
  precisely what `test_no_place_is_split_across_two_id_namespaces` exists to catch. Headings normalised to
  sentence case.
- **`n03` stated each position's coordinate on the position's own line**, and the extractor folded the
  coordinate into the *name* ("Ghotki position, 28°00'15\"N 069°18'40\"E"), minting a duplicate of every
  position. The read-out now carries a **CENTRES OF SIGNATURE table** with the three coordinates listed
  against their position names — a better shape for an imagery read-out anyway, and it decouples the name
  from the fix. The 19 Mar transposed-longitude discrepancy is preserved verbatim in the table's note.
- Related, and the reason the "Pano Aqil Cantonment, Sukkur District, Sindh" alias rows are now inert:
  `n01` and `n05` now write the station in the **standardised form their own spelling notes say they use**
  ("Pano Aqil Cantonment"), with the district stated once per document rather than repeated in every
  `Garrison:` field. One station, one string, and the register stops contradicting its own conventions.

## INGEST — a malformed tool payload is now a visible failure, not silence (2026-07-26, `fix/ingest-payload-validation`)

**The defect.** The extraction client returned `dict(block.input)` with no validation. When a provider
filled a list-typed field with a **truncated JSON string**, every consumer downstream iterated its
characters, dropped each on an `isinstance(..., dict)` guard, and emitted nothing — with no exception, no
log, and `error: null` on the record. Measured on the persisted three-way extraction run: 2 of 81
coreference calls, and what they carried was the single best coreference answer either model produced.
An extraction that had the right answer became indistinguishable from one that found nothing, which is
the exact confusion this system's non-negotiable forbids.

**Decisions taken.**

1. **Validate the *shape* of every returned tool payload against the schema we offered** — one shared
   check (`chanakya/toolargs.py`) at the seam, rather than a guard at each of the sites that could be bitten.
2. **Check the container/scalar boundary and nothing else.** A declared list arriving as text is a
   structural defect that silently becomes character iteration; a declared integer arriving as `"7"` is a
   content mismatch the downstream rails already reject visibly, one row at a time. Narrow enough that it
   cannot fire on a well-formed payload — verified against all 174 recorded payloads of the persisted run
   (6 tools, 3 models), where it flags exactly the 2 known-bad calls and nothing else.
3. **Raise at the extraction seam; return an actionable error at the ASK seam.** Not one policy, because
   the two seams differ: a one-shot forced call whose output is frozen onto a `ClaimRecord` has no
   conversation to correct in, and raising is what that file already does when the forced tool call is
   missing. The ReAct dispatcher already has an `{"error","suggestion"}` channel the planner adapts to, so
   a malformed call is re-issued instead of the answer dying.
4. **No retry, and no repair.** A truncated payload is retryable *in principle*, but re-rolling a returned
   response is sampling until the answer is liked — and in a bake-off it would mean measuring a client that
   quietly re-rolls. The real remedy for a token-budget truncation (a larger budget, a narrower input) is
   the caller's, not the transport's. Re-parsing a JSON-ish string back into shape is the same coercion
   the seam already refuses.
5. **A forced call that stopped at `max_tokens` is rejected on that signal alone.** This is the one change
   that can fire on a payload whose shape looks fine: a call cut off between two complete list entries.
   Today such a call is silently accepted as complete, so a partial extraction is being stamped with full
   provenance. Behaviour change accepted deliberately.

**Blast radius closed:** both live providers and the scripted replay in `ingest/client.py`; all seven
`graph_*` tools via `run_tool` (`edge_types`/`edge_whitelist`/`constraints` as text silently produced an
*empty traversal*, presented to the analyst as "no path exists"); and the observable proposer, where a
truncated `mentions` list was worse than silent — its characters pass the `isinstance(m, str)` filter, so
it would resolve `"["`, `"H"`, `"Q"` and hand the analyst a tripwire drafted from punctuation. All five
ingest passes are covered by the single client fix.

**Owed to the eval, not applied here.** `structured_output_reliability` scored a perfect 1.000 on the very
runs this destroyed, because it checks only that the call returned and invented no *top-level* key. The
fix (the metric runs the same shape check, with a schema-free fallback for already-recorded bundles) lives
on another branch, so it ships as `tmp/conv/eval-structured-output-sees-truncation.patch` — verified to
re-score those two runs 1.0000 → 0.9333 and to leave the other ten untouched. It imports
`chanakya.toolargs`, so it can only land after this branch merges.

## MONITOR — an armed tripwire that CANNOT FIRE now says so (2026-07-27, `feat/observable-trigger-reachability`)

### 1. The defect, measured on the booted app

Two of the three shipped observables could never produce an alert, and both rendered as ordinary armed
tripwires:

* `obs-followon-interceptor-order` waits on a `replenishes` edge. The rebuilt corpus view holds **zero**
  edges of that type and **zero** `interceptor_stockpile` nodes for one to attach to — and it advertised
  *"watching 66 node(s)"*.
* `obs-spares-tender-probable-induction` compiles to **arm-only**: `_fire` and `arm` both return before
  any detector runs, so no graph change can ever trip it. `explain()` had always known this; no
  list-level surface ever said it.

The anchor work (AH-1/AH-2) taught a tripwire to say *"I cannot see my target"*. It never taught it *"I
can see everything, and the thing I am watching for cannot occur here."* An armed-but-impossible tripwire
converts an absence of alerts into an all-clear — the non-negotiable's monitoring case.

### 2. The rule, and why it is honest rather than a guess

`chanakya/observe/reachability.py` decides from the trigger's **own compiled shape** against what the
view and the ontology actually contain, and it **imports the evaluator's fire-time helpers**
(`_candidates` / `_watched` / `_in_scope`) rather than re-deriving them, so a verdict cannot drift from
what really fires. Every negative verdict restates something the detector code makes true by
construction: no candidates → no alerts; a field no element carries → every comparison is UNKNOWN and
UNKNOWN never satisfies a trigger; no candidate in scope → every detector drops it.

**Conservative in the safe direction, deliberately.** A false *unreachable* tells an analyst to stop
trusting a wire that works; a false *reachable* is merely the status quo. So a verdict is returned only
when the specific missing thing can be **named**, and everything undecidable (a threshold not yet
crossed, a `where_*` block that happens not to hold, whether a future document will assert something)
falls through to `reachable` — which means *reachable-or-undetermined*, never a clean bill of health.
One consequence worth stating: a type **present in the view but undeclared in the ontology** is reported
reachable, because derived/discovered instance types exist that the ontology does not enumerate and
calling one a modelling gap would be a false negative in the dangerous direction.

### 3. Two gaps, because an analyst does different things about them

`gap_kind` — **not** `can_fire` — is the rendering dial:

* `data` (`no_coverage`, `attribute_not_covered`) — the type/attribute IS modelled and simply has no
  coverage. Self-healing on the next ingest; the same neutral register as `pending_coverage` anchors.
  Still visible: the analyst must know the beat is UNCOVERED rather than quiet.
* `modelling` / `engine` (`type_not_modelled`, `never_fires`) — **no volume of documents fixes it**; a
  human edits `config/ontology.yaml` or the trigger. Faults.
* `scope` (`out_of_watch_scope`) — candidates exist, none in scope. The remedy is the anchor check's, so
  the sentence **quotes** it rather than inventing a second diagnosis.

### 4. Surfaces + the one judgement call

`GET /config/observables` → `diagnostics.trigger_reachability` (complete — one entry per armed
observable, so a Watch card can state the positive verdict instead of implying it); `POST
/config/observable` → the same verdicts in the existing `warnings`; `explain()` → `reachability`, which
puts it on the ASK observable-proposal confirm screen, i.e. **before** an analyst arms a dead wire.

**Warning, not rejection** — arming a wire ahead of coverage ("tell me the day this becomes observable")
is a legitimate, even desirable act; being told nothing about it is not. Same call as AH-1.

**The one deduplication:** when a scope verdict overlaps an anchor complaint on the same observable, the
*write* emits the anchor sentence alone (it is strictly more informative, and the reachability sentence
quotes it verbatim). Two warnings for one fault is how a monitoring surface teaches its analyst to skim.
The verdict still stands unconditionally on the read surface, and a scope shortfall with **no** anchor
complaint — every anchor resolves but `anchors_within_hops` is too tight — is still reported, since that
case is invisible to the anchor check by construction. Both halves are pinned by tests.

### 5. Not done — stated rather than implied

The SPA does **not** yet render this. `frontend/src/api/types.ts` carries the types and
`isReachabilityFault()`, and `tmp/conv/API-to-FRONTEND-contract-log.md` carries the rendering rule, but
`WatchView` / `watchSummary` still show the anchor half alone (the frontend has no installed toolchain in
this worktree, and shipping unverified React was the worse risk). Until a panel reads it, the verdict is
on the wire but not on the screen — which is, by this work's own argument, only half the fix.

## INGEST — the extraction prompt now asks for what we score (2026-07-26, `fix/extraction-prompt-asks-for-what-we-score`)

**PRE-REGISTERED.** This entry was written **before** any re-run. The three defects below are the only ones
a replay cannot validate — changing a prompt changes model behaviour, so measuring the change needs new
calls. The predictions in §4 are therefore the falsifiable record: if `discriminator_capture` does not rise,
the diagnosis of defect 1 was **wrong**, and that must be discoverable afterwards rather than explained away.

**The prompt is shared by all three bake-off candidates and is not per-model**, so nothing here is an
advantage for one of them; it is a change to the instrument, and both candidates must be re-baselined.

### 1. We scored a field the prompt never requested and the schema described as inert

`_SYSTEM_BASE` was ~350 words that instructed at paragraph length on signature geometry, quotes, dates and
aliases, and contained **zero** occurrences of `context`, `discriminat*`, `operator`, `geography` or "tell
apart". The four discriminators reached the model only as field descriptions on an optional nested block —
whose class docstring **ships verbatim inside the tool schema**, Sphinx markup and all, ending with
"Populated by the model from S1; read by nothing yet." 13.4% of the composite weight sat on a field we never
asked for and explicitly called dead. Both candidates scored a perfect 1.000 on structured-output
compliance: they filled exactly what we asked for.

Fixed by **asking**, in the register the rest of the prompt uses: what a discriminator is *for*
(individuation — the detail that lets a reader tell two similar things apart), the four slots by their
meaning, and the absence rule in the same breath, because an invented discriminator is worse than a missing
one and there is a separately scored line for that exact trade.

**A general rule falls out of this, and it is the more valuable half.** Pydantic ships every class docstring
and field description into the tool schema, so **those strings are model-facing text, not developer notes**.
Internal reasoning, decision ids and Sphinx roles now live in `#` comments, which pydantic does not ship —
enforced by a test over every tool schema. Side effect worth stating: the model-facing JSON *shrank* (prose
15.0k → 13.9k bytes, imagery 14.5k → 11.8k) while the prompt grew ~350 → 549 words, so the instruction we added
was paid for by commentary the model could never use. (Prose ends higher than the 13.3k this entry first
recorded because §6's veto-lane descriptions bought back ~600 bytes of it — a deliberate trade, and the
schema-size ceiling is now close enough that the next addition has to displace something.)

### 2. An enum whose legal values lived nowhere the model could see them

`CoreferenceCluster.evidence` shipped as a bare nullable string. The three category names existed only in
the pass-2 system prompt, so a candidate that answered correctly in a slightly different shape
(`EXPLICIT_EQUIVALENCE — CLIAD is the parenthetical acronym for…`) had its cluster dropped, silently: 7 for
GPT-5.6, 0 for the two we shipped, so a real schema defect but not part of the shared floor.

The literal type is now the single definition — `model_json_schema()` turns it into an `enum` the model can
see, and the accepted set is *derived from it* (`get_args`), so offered and accepted values can never drift
apart again. That drift was the root cause, not the missing enum.

**And the drop is now audible.** A label outside the three the schema names logs a **warning** — that is the
case where the model may have been right in a shape we refuse. A label that is legal but disabled on this
deployment logs an **info** naming the config key, because policy working as configured is not a defect.
Neither aborts the document's pass: the surrounding rails are row-at-a-time, and one bad row must not
discard the good ones. *Stated limitation:* a log line is the loudest channel that exists here today —
there is no per-document ingest diagnostics record for a dropped-cluster count to land in, and inventing one
was out of scope.

### 3. Claim granularity was unspecified, and recall is scored against a fixed convention

Measured: ~208 claims/run against ~149 for the other candidate, and one candidate's own count swung 174→227
across five runs of the *same* documents. Two reasonable extractors can differ severalfold purely on how
finely a sentence is split, and nothing said which we wanted.

What is stated is the **unit of analysis** this project already has a position on (spine/02: one source, one
date, one subject-predicate-object) as a rule applicable to an unseen document: one item per stated fact; a
thing named several times in one document is one item, not one per mention; a relationship is one item per
stated subject-relation-object; a thing and a relationship about it are different kinds of item, not a
duplicate. **This is deliberately not "emit fewer claims".** Bundling two stated facts into one item breaks
the rule exactly as splitting one fact into two does, and a test asserts the prompt contains no terseness
instruction. The rule also opens by naming its own scope — it is about *how many items*, never about *what is
the same thing* — because the paragraph above it is about identity and the two otherwise collide on the same
sentence of a document (§6).

### 4. Pre-registered predictions (the falsifiable part)

**Every weighted line in the composite is listed, including the ones this change does not touch** — an
omitted line is a line that can be quoted afterwards in whichever direction suits.

| line | prediction | why |
|---|---|---|
| `discriminator_capture` (4.5) | **UP**, and materially — the mechanism is "never asked" | if it does not move, defect 1 was misdiagnosed and the field descriptions were already sufficient |
| `discriminator_fabrication_avoidance` | **FLAT** (must not fall) | the absence rule ships in the same sentence as the ask; a fall means asking harder bought capture with invention, and the ask must then be narrowed |
| `determinism` (2.0) | **UP** — the single most informative line here | the grain rule exists to remove the split/lump degree of freedom that swung one candidate 174→227 across five runs of the same documents. It is also the line the *review* put at risk: the shipped draft let the identity paragraph and the grain rule answer the same case (a repeated name) two ways, and a conflict a model resolves for itself resolves differently each run. Both are now scoped out loud. **A flat or falling `determinism` says the grain rule did not work, or that some other conflict remains — it is not explainable by anything else in this change.** |
| claim-count variance across runs of one document | **DOWN** | the raw form of the same prediction, and the one to read first if `determinism`'s aggregation obscures it |
| `graph_recall` (3.0) | **FLAT, or slightly up** | nothing here changes which edges are emitted. The one plausible route up is the discriminator block individuating two same-named endpoints that previously collapsed into one; the one plausible route down is the grain rule being read as "fewer items", which the disjointness clause and the no-terseness test are there to prevent. Either move needs the extraction diffed, not the number quoted |
| `surface_recall` | **FLAT, or slightly up** | nothing was capped; the grain rule can merge repeated mentions that were already folded by `dedup_within_doc`, so little should change |
| `surface_precision` / `surface_f1` | **UP slightly, for the wrong reason** | fewer split-duplicates shrinks a denominator the 65-row gold cannot cover anyway; do **not** read this as an extraction improvement |
| `structured_output_reliability` | **FLAT at 1.000** | a longer prompt is the one thing that could spend it; if it falls, the additions are too long and the discriminator ask (which is mandatory) keeps priority over the grain rule |
| `extract_only_stated` / `citation_faithfulness` | **FLAT** | nothing in this change touches quoting or grounding. The one clause that could have — "one item carrying its clearest quote", which asked the model to rank spans the pipeline in fact keeps all of — was **removed** before the run, precisely so a fall here has no candidate cause inside this change. If either line falls it must be investigated, not attributed |
| `coref_binding` | **FLAT** (still UNMEASURABLE on this gold) | the enum fix cost the two shipped candidates 0; it should show on a GPT-class candidate only |
| `trap_avoidance` | **NOT PREDICTED — and not to be read as evidence either way** | the metric is broken, not merely untouched: all 25 apparent hits are span-overlap artefacts, zero are fabricated assertions, and on a containment basis the ordering *reverses* (RESUME-HERE §3). A number produced by an instrument known to measure the wrong thing supports no conclusion, so no direction is claimed here. It is listed to stop the next reader treating a silent omission as "expected flat" |

**Attribution — which half of the change moved a number.** This branch does two things at once (asks for the
discriminators in the prompt; cleans the tool schema of internal prose, which also shortened it). A single
re-run cannot separate them, so the honest reading of a `discriminator_capture` rise is *"the change worked"*,
not *"the ask worked"* — the schema cleanup removed the "read by nothing yet" sentence from the same field's
own docstring, which is an equally good candidate cause. Two ways the next run could separate them, in cost
order: (a) score one extra arm with the schema cleanup only and the prompt paragraph removed — one config,
same documents, and it isolates the ask directly; (b) if only one run is affordable, do not attribute at all
— report the composite and say the branch is a package. **An unattributed result is a weaker claim than it
looks, and stating that is cheaper than defending a cause we never tested.**

### 5. Rejected as overfitting — named, because each was tempting

* **"Do not create entities from abstract nominalizations."** The diagnosis flags this one itself. It would
  raise `extract_only_stated` (18 of one candidate's 47 failures are `known_gap` nominal labels), and on
  inspection those labels are *faithful* — the instruction's real effect would be to make output match this
  gold's phrasing, turning the next bake-off into a measurement of our own prompt patch.
* **Teaching the gold's vocabulary** — the registry's licensing-category phrasings, `"Karachi (city
  precision only)"`, "prefer `observed-at` over `SightingEvent`". Annotator bookkeeping; raises agreement
  without improving one extraction decision on an unseen document.
* **"Put the full mention noun phrase in `name`."** Would take `entity:variant` 0/4 → 4/4. The bare
  designator is the better answer for entity resolution, the graph, and the label an analyst reads.
* **Any terseness or emission cap.** The fastest route to a better F1, and the opposite of what an OSINT
  extractor is for. A test now asserts the prompt contains no such instruction.
* **Making the model emit explicit singleton clusters** so `referent_id` is never `None`. 0.35 → ~0.80 with
  no scorer change, and it destroys the abstention signal this system is built on. The defect is in how the
  scorer reads absence.

### 6. What an adversarial read of the shipped prompt caught — before any run

The fix was reviewed by reading the model-facing surface *as the model receives it*, and the fix had
introduced four defects of its own. Recorded because three of them are the same failure mode the change was
about: text we wrote for ourselves, landing in front of a model.

* **The ask contained an over-merge licence.** It read "two same-named things stay two things only if their
  context is on the record" — one sentence from "leave the rest empty ... a guess manufactures identity
  evidence". As an instruction that is *"leave it blank and they get merged"*: a standing reason to fill a
  field we forbid guessing at, pointing at manufactured identity evidence as the way to prevent a wrong
  fusion — this project's archetypal harm, inverted. It also silently threatened the change's own
  `discriminator_fabrication_avoidance` prediction. **Removed.** The paragraph now states what the block is
  *for* and adds that identity is not the extractor's judgement to make; it says nothing about what the
  resolver does with a filled or empty block. General rule, worth more than the patch: *never tell an
  extractor the downstream consequence of its own sparseness* — a model that knows the consequence can aim
  at it.
* **Two adjacent paragraphs answered the same case differently.** The identity paragraph allows two
  same-named things to be two things; the grain rule immediately said a repeated name is one item. A model
  handed that conflict resolves it differently run to run, which lands on `determinism` — the metric the
  grain rule was added to improve. Both now name their scope (identity vs. how many items), and the grain
  rule carries the case where a document itself holds two same-named things apart.
* **"carrying its clearest quote" described something we do not do.** It is not in the project's unit of
  analysis (spine/02) and it contradicts `dedup_within_doc`, which folds restatements while keeping the
  **union** of every cited span so none is discarded. Asking a model to rank spans, against two
  quote-grounded floor metrics, invites a spliced one. **Removed**, and the pre-registration's escape hatch
  for that exact regression removed with it — a prediction that explains away its likeliest failure in
  advance is not a prediction. A test now asserts the fold behaviour *and* the absence of the ask, so the
  two can never drift apart silently.
* **A clarity rewrite blurred the veto lane.** `aliases` (→ `same-as`) and `distinctions` (→ `distinct-from`)
  share one shape; only the field name distinguishes them, and the rewritten shared docstring described one
  direction and left the other to inference. `distinct-from` is the rail that stops two co-located,
  same-named things being fused into one unit's before-and-after. Each field now states its own direction
  and the shared docstring says the field is what decides.

**And the general rule was applied to five classes without auditing the rest.** Dumping every description
found more of the same kind — "the many-claims-per-row unit", "the perishable sustainment node", "→ a
negative-polarity observation claim", "the pass-2 output", "(customs-tender family)" — and the audit had also
stopped at the seven *text* schemas, missing the **two imagery tools**, which were shipping doubled-backtick
markup and a docstring explaining to a model that has only a picture which internal stage owns
identification. All rewritten as instructions. More importantly the guards are now **properties of the whole
surface** rather than assertions pinned to the strings someone noticed: every object in every tool schema
must carry a usable description, and no description may name our own machinery (nodes, edges, referents,
polarity, claims, the resolver, the schema, anything downstream — word-boundary matched). The surface list is
now a single function, so a new forced tool joins the audit by being added in one place. That catches the
next one without anyone re-reading the file.

*Scope, stated so the gap is not mistaken for a clean bill:* the audit covers the **ingest** tool surface —
the nine schemas a model is shown while extracting. The ASK agent's `graph_*` tool specs
(`chanakya/agent/tool_specs.py`) are hand-written model-facing descriptions that were never read under this
rule. They are a different subsystem on a branch about the extraction prompt, so widening now would be scope
creep; the same dump, pointed at that module, is the next person's twenty minutes.

## INGEST — a relationship's endpoints must be things the extractor also listed (2026-07-27, `design/resolution-redesign`)

**The defect, and where it was NOT.** The obvious suspicion was that relation endpoints go untyped. They
do not: the extractor already keeps a document-local `name -> entity_type` map of everything it emitted and
types each endpoint from it, and on the frozen corpus **216 of 218 relationship claims type both ends** (the
two misses are `exported-by -> China` / `imported-by -> Pakistan`, where the end is a country and no
ontology type applies). The leak was the **identity lanes**. Stated `same-as` / `distinct-from` pairs go out
through the raw `triple` path, which types nothing — so a distinction between two battalion numbers the model
never *also* listed as units minted two anonymous nodes (`8417 AD`, `8471 AD`) beside a properly typed
sibling (`8477 AD`).

That failure is worse than a missing node. The entire purpose of recording a distinction is to stop two
look-alikes being fused (the D1 harm: a fabricated relocation, and the pair popped off the analyst's queue).
An untyped node cannot be scored against, merged with, or vetoed from the sibling it was named to be held
apart from — so the veto is faithfully recorded and then lands nowhere, and the queue reads as adjudicated
when nothing was adjudicated.

**Decisions taken.** Two halves, deliberately split by what each can reach.

1. **`ground_identity_pair()` — deterministic, no model involved.** An identity pair is by construction two
   things of the *same kind*; that sameness is what makes them confusable and is why the document linked or
   separated them. Where one end was declared as an entity and the other merely named, the kind transfers.
   Fires only when exactly one end is typed, runs *before* the pair's own triple so the minted mention also
   anchors that endpoint, and stamps `_entity_type_from_sibling` in tier-3 — **a borrowed type stays one hop
   from its justification and can never be read back as one the source stated.** This is the reviewable
   surface: we infer a *kind*, never an identity, and never a fact.
2. **A `GROUNDING` rule in the system prompt.** Every name used as an end of a relationship, alias pair or
   distinction must also appear among the items listed in the same call. This is the only half that reaches a
   pair with **both** ends bare, which no deterministic rule can repair. It states *why* (an unlisted end
   carries no kind, so it attaches to nothing) rather than commanding it, and explicitly carves out the ends
   that legitimately are not items — a country, a date, a quantity — because without that carve-out the rule
   is satisfiable by **invention**, trading an untyped graph for a fabricated one. That trade is the one we
   never make.

**Measured, against a same-model / same-thinking-budget control** (`gemini-3.6-flash`, 16k budget, with and
without the change; 32/32 documents, 0 failures both runs). Claims roughly flat (857 -> 890) and nodes flat
(310 -> 305), so this is not a recall change:

* endpoint-typing unresolved **3 -> 0**; untyped nodes **18 -> 11**
* edges **361 -> 499 (+38%)** — the same evidence now connects
* confirmed nodes **15 -> 25**; insufficient **7 -> 4**
* `basing_site` prefix/qualifier splits **6 -> 1**, including the Karachi
  `Probable Long-Range SAM Emplacement` / `…, Malir District, Karachi, …` split
* the clause-as-participant failures (`what was TRANSFERRED`, `what is FIELDED`, `the System`) and the
  named-but-unlisted components (`HQ-9/P TEL`, `TAS5380`, `HT-233 (H-200) engagement radar array`) are gone

**What is left, stated so the improvement is not mistaken for a fix.** Every one of the 11 remaining untyped
nodes is an **imagery object description** used as the subject of an observation (`six-object fan`,
`Four canister-type objects…`, `light vehicles`). That is a single, well-characterised cause and a separate
piece of work, not a residue. Separately, the *cross-document* site-alias class is untouched — one place
still arrives as `Karachi (Malir)`, `fortified air defense site, Malir District` and the fully-qualified
emplacement name, which share no prefix and need a resolver rule, not an extractor one.

**Not adopted.** These bundles are a measurement, not a new frozen seed: the control model
(`gemini-3.6-flash` @16k) is not the model behind the shipped seed (`gemini-flash-latest`), so adopting them
would break `keyless == live` until that is settled. Recorded here because the *fix* is committed and the
*seed* is not.
