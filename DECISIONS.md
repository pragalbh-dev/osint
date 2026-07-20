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
