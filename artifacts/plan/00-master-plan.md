# Chanakya OSINT — Backend Implementation Plan (MASTER)

**What this is.** The single build plan for everything **except the frontend**: the shared spine, the C
layer's config/content, the API, and deployment. It is the *contract-of-record* for a set of parallel
implementation sessions — each run by one Claude agent, in its own git worktree, opening one PR to `main`,
staying until it is merged, then destroying the worktree.

**How to read it.** This master doc carries the **frozen contracts** (schemas, stage interfaces, config
surface, tool signatures, API shapes), the **executable abstraction gates**, the **testing / deployment
standards**, the **concurrency + conflict-freedom model**, and the **worktree/PR/handoff workflow** — once,
here. Each `sessions/<ID>.md` is *thin*: it points back to the contract sections it implements and adds only
its file-ownership, tests, acceptance gate, and lifecycle. **When this plan and a design doc disagree, the
design doc wins — and fix this plan.** Design authority order: `DECISIONS.md` ledger → `spine/08` (schemas)
→ `spine/09` (retrieval/agent/hot-config) → `spine/04` (credibility) → `C/01` (C ontology) → `md/07-stack`
(stack/deploy) → `product/03` (data contracts).

**These contracts are a coordination floor, not a capability ceiling.** They exist so parallel agents don't
collide and so provenance/traceability stay honest — **not** to ration ambition or freeze later stages.
Later-stage internals are deliberately *under*-specified here: a session that sees a better approach — a new
dependency, richer / more production-grade machinery, a sharper contract — should **propose and coordinate
it**, not clip its own solution to fit a first draft. Add the library, build the capability *well*; just keep
the build deployable, keep the §5 gates green, and — only for a change to a *shared* contract a sibling reads
— coordinate it (§2 Rule 3) so no one is broken. Writing code is **not** the scarce resource here (many
agents run in parallel); design judgement, correctness, and QA are — so spend the latitude on making the
system genuinely good, not on staying minimal. This is an assignment to push toward a *real* system.

**The non-negotiable, carried into every session.** Where evidence is absent/ambiguous/contradictory the
system returns an explicit **"insufficient evidence to assess"** — naming what is missing and when next
coverage is due — as a first-class `Known Gap`, never a fabricated assessment. This is disqualifying if
broken. It is mechanised by the sufficiency templates (SCORE) + `check_sufficiency` (ASK) + the citation
validator (ASK), and guarded by gate G7/G8 (§5).

---

## 0. Scope

**In scope (this plan):**
- The shared **spine** modules: store, `rebuild()` view, resolution, credibility/status, sufficiency/Known-Gap,
  materiality precompute, observables, HITL adjudication, ingestion, retrieval agent.
- The **C layer** as *config + content* over the spine (ontology/sources/credibility/templates/subjects/
  observables YAML; the frozen corpus; pre-extracted claim bundles).
- The **API** (FastAPI: JSON view, provenance, HITL writeback, ingest, ask, `/health`, hot-config writes,
  `StaticFiles` mount for the SPA).
- **Deployment**: multi-stage Docker image, GHCR, EC2 + Cloudflare Tunnel, `make` targets, secrets, keyless
  boot, rollback.
- **Tests** at every layer + the acceptance harness (spine gate + demo flexes).

**Out of scope (a separate track):**
- The **React/Vite SPA** and its Cytoscape/Leaflet surfaces + the status×freshness×source-tier visual
  language. This plan provides the SPA's **seam only**: the JSON contracts (§4.8) it binds to, and the Docker
  Node-build stage + `StaticFiles` mount it drops into (`SHIP`, `API`).
- **Use Case B** (intent/I&W). Only the *pre-wirings* that are free now (events first-class, bi-temporal
  stamps, inference-as-claim-kind, declarative observables, absence-as-evidence, decomposed credibility) are
  built; B's ACH machinery is roadmap (`spine/08` §2.3).

---

## 1. Architecture recap (the invariants the whole plan rests on)

**Event-sourcing core.** Two append-only SQLite logs + a versioned/live config store, reduced to a NetworkX
view by a pure function:

```
EVIDENCE LOG  (append-only)   claims extracted from sources        ─┐
DECISION LOG  (append-only)   HITL adjudications + system events    ├─► rebuild() ─► KNOWLEDGE VIEW ─► JSON
CONFIG STORE  (live, versioned) ontology, weights, templates,       ─┘   (entities, edges, events,
                                lenses, observables                        statuses, materiality attrs)
```

Load-bearing invariants (each is enforced by a gate in §5):

1. **`rebuild(evidence_log, decision_log, config) → view` is a pure, deterministic function.** It runs
   `resolution → credibility → status → sufficiency → materiality-precompute` and emits the view + JSON.
   **No LLM call, no network, no clock, no randomness inside `rebuild()`.** (`spine/08` §1, §3.11; DECISIONS
   "LLM is proposer, never authority".)
2. **LLM proposes *upstream* of the log; deterministic rules dispose *inside* `rebuild()`.** Extraction,
   merge-candidate proposal, alias proposal, the soft "too-clean" narrative, and the agent's query planning
   are LLM. Everything that decides a number, a status, a merge, or a refusal is deterministic and
   config-driven. Extraction runs *before* the append, so the invariant holds even with live ingestion.
   **Placement rule (resolves the RESOLVE/INGEST tension):** an offline LLM *proposer/extractor* entrypoint
   may live inside a stage package (`resolve/propose_candidates.py`, `ingest/extract.py`) and import
   `anthropic` — but it is invoked *outside* the rebuild call-path (it writes frozen records the stage then
   consumes). The stage function `rebuild()` actually calls (`resolve()`, `score_claims()`, …) must never
   reach the LLM. G1 (§5) enforces this *behaviorally* (rebuild runs with the LLM patched to raise), not by
   banning the import from the package.
3. **Hot-config / live-`rebuild()`.** Nothing a user does in-app requires a restart. `rebuild()` is an
   in-process op (ms at demo scale) triggered by any ingest / decision / config write; config lives in a
   live store the API writes to, never a baked file. Only *new code* needs a redeploy. (`spine/09`.)
4. **Bi-level, two-scores-never-averaged.** Append-only immutable **evidence layer** (sourced claims) +
   derived **knowledge layer**. `merge_confidence` (identity, on the `same-as` edge) and
   `claim_credibility`/`assertion_confidence` (truth, on the resolved node/edge) are distinct objects,
   never blended. (DECISIONS "two scores, two objects".)
5. **Unit = the sourced claim.** Provenance attaches per claim; claims are immutable, never merged/edited
   (only *entities* merge, via `resolved_ref`); retraction is an appended claim. One-click node→claim→
   doc-span traceability is structural.
6. **Subject = a query-time lens; ingestion is source-typed, not use-case-typed; the store is
   schema-flexible.** Re-pointing to a new subject/observable/question is a config edit, not core code.

**Stack (LOCKED — `md/07-stack`, DECISIONS "Stack & retrieval").** SQLite logs + NetworkX rebuilt view ·
LLM-only extraction available offline (seeded baseline for keyless boot) **and live at ingest** · no runtime
embeddings (alias + BM25 + `rapidfuzz`) · Anthropic `claude-opus-4-8` direct (optional Gemini), **no
`temperature`/`top_p`/`top_k`** (HTTP 400 on Opus 4.8) · bounded ReAct tool-calling agent, ~7 `graph_*`
tools, materiality precomputed in `rebuild()`, entailment citation validator · FastAPI single process serving
JSON + built SPA same-origin · one multi-stage Docker image · **one always-on EC2 + Cloudflare Tunnel**,
image on **GHCR** · reviewers run it **both** ways (`docker run ghcr…` and `git clone && make run`) · secret
`ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) via `.env`, never committed/baked.

---

## 2. Concurrency model & the conflict-freedom guarantee

The whole point of F0 is to make Wave-1 sessions **provably conflict-free** so they can be built in parallel
worktrees and merged in any order.

**Rule 1 — F0 freezes the shared *surface* (shapes + interfaces), so siblings compose without collision.**
F0 is merged to `main` *before any other code session starts*. It creates and owns, permanently:
- `pyproject.toml` with the **locked baseline dependency set** declared up front (§4.1) — a working floor,
  **not a ceiling**. A session that needs another library **adds it** (append to the deps list; prefer the
  stdlib or an existing dep first; flag it in the PR so the image/deploy stay in sync). `pyproject.toml` is
  the one deliberately-shared file where additive edits are welcome — an appended dep line merges trivially.
- `chanakya/schemas/**` (all record + config + view + API models), `chanakya/config/**` (loader + live
  config store), `chanakya/store/**` (SQLite logs), `chanakya/view/**` (`rebuild()` orchestration + stage
  interfaces + **stub implementations** + lens scoping + JSON export).
- One **stub package per stage** so downstream sessions only *edit files inside their own module dir* — they
  never create a file in a shared parent: `chanakya/{resolve,credibility,sufficiency,materiality,observe,
  agent,ingest,hitl,api}/__init__.py` each exist as a stub after F0.
- `tests/fixtures/**` (golden synthetic fixtures), `tests/gates/**` (the abstraction-gate suite, §5),
  `.github/workflows/**` (CI), `Makefile` skeleton (targets stubbed).

**Rule 2 — disjoint ownership.** Every post-F0 session owns a set of paths that no other session touches
(§4.1 file-ownership map). Because ownership is disjoint, a rebase onto updated `main` is always clean and
merge order is irrelevant. (The one deliberate exception is `pyproject.toml`, for *additive* dependency lines
— Rule 1; additive list edits merge trivially, and a rare conflict there is seconds to resolve.)

**Rule 3 — coordinate changes to a *shared* contract; don't silently fork it.** The frozen surface exists
only because siblings *depend* on it, so if a session needs to change a shared contract another session reads
(a schema field, a stage signature, the config surface, an API shape), it doesn't just edit it inside its own
PR and diverge — it opens a small **contract-amendment PR** first (you review; usually a quick yes), that
lands, then dependents pick it up on rebase. This is lightweight coordination to keep the compose-guarantee
intact — **not** a discouragement: propose the better contract. It **does not** apply to adding a dependency,
to a session's own *internal* design, or to richer machinery inside its owned paths — those are the session's
call, no amendment needed. Log a shared-contract amendment in `PROGRESS.md` and `DECISIONS.md`.

**Rule 4 — `PROGRESS.md` stays out of PRs.** You (the merge authority) update it at merge time. This removes
the only remaining shared-file write, so *no PR ever edits a file another PR edits*.

**Result.** You can open as many or as few worktrees as you want, in any order after F0, and no PR will
conflict. CI reruns the full suite on every push, so a clean rebase that would break a sibling is caught
automatically before you merge.

---

## 3. Session DAG & build order

| ID | Session | Wave | Depends on (merged) | LLM | Owns (top-level) |
|----|---------|------|---------------------|-----|------------------|
| **F0** | Foundation: scaffold, schemas, config store, **SQLite store**, `rebuild()` skeleton + lens, golden fixtures, gate suite, CI | 0 | — | no | `pyproject`, `chanakya/{schemas,config,store,view}`, all stub pkgs, `tests/{fixtures,gates}`, CI, `Makefile` skeleton |
| **X0** | Walking-skeleton deploy: trivial FastAPI+`/health`, multi-stage Dockerfile, compose, GHCR push, EC2 + `cloudflared`, live URL | 0 | — | no | `Dockerfile`, `docker-compose.yml`, `deploy/`, `app_skeleton/` |
| **DATA-C** | Freeze+commit corpus (d15+, images, chaff); reconcile generator; author the 6 `config/*.yaml` for HQ-9/P | 0 | F0 (config schemas, soft) | no | `corpus/**` (docs/manifests), `tools/**`, `config/*.yaml` |
| **RESOLVE** | Iterative relational ER: candidate-gen (LLM raise-only) + `merge_score` + bands + bootstrap→fixpoint + alias table + location resolution | 1 | F0 | offline | `chanakya/resolve/**`, `tests/resolve/**` |
| **SCORE** | Confidence Resolver (per-claim × noisy-OR + status machine + freshness + supersede/contradict + gates) + Sufficiency/Known-Gap + materiality precompute | 1 | F0 | no | `chanakya/{credibility,sufficiency,materiality}/**`, their tests |
| **MONITOR** | Observable DSL evaluator + armed-registry + re-eval on rebuild + seeded relocation observable + Alert objects | 1 | F0 | no | `chanakya/observe/**`, `tests/observe/**` |
| **ASK** | Bounded ReAct loop + 7 `graph_*` tools + entailment citation validator + first-class refusal + fixed hero path | 1 | F0 | runtime | `chanakya/agent/**`, `tests/agent/**` |
| **HITL** | Adjudication service + decision-log writeback + 3 card payloads + recall-biased triage + analyst-initiated integrity flag + propagation | 1 | F0 | no | `chanakya/hitl/**`, `tests/hitl/**` |
| **INGEST** | Source-typed LLM extraction → ClaimRecord + extract-raw guardrail + Dates/Locations bases + live-ingest lane + pre-extracted seed bundles | 1 | F0 (+DATA-C sources.yaml, soft) | offline+live | `chanakya/ingest/**`, `tests/ingest/**`, `corpus/**/claims/**` |
| **API** | FastAPI: view JSON, provenance, 3 HITL writeback, ingest, ask, `/health` gated on `rebuild()`, hot-config writes, `StaticFiles` seam | 2 | RESOLVE, SCORE, ASK, HITL, MONITOR, INGEST | no | `chanakya/api/**`, `tests/api/**` |
| **EVAL** | Acceptance harness: corpus→pipeline→answer_key; spine-gate 5 criteria; 6 demo flexes e2e | 2 | all Wave-1 + DATA-C + INGEST | no | `tests/acceptance/**`, `eval/**` |
| **SHIP** | Production packaging: multi-stage image bakes config/corpus/seed-logs + SPA seam; `make {extract,build,ingest,ask,run}`; GHCR+EC2; rollback | 2 | API (+X0, DATA-C, INGEST) | no | extends `Dockerfile`/`compose`/`Makefile`/`deploy/` |

**Recommended order given "you review & merge each"** (minimises your idle time; all Wave-1 are optional-order):
1. **F0** solo (gate for everything). Kick off **X0** and **DATA-C** in parallel with it (zero code dep).
2. Drain **Wave 1** at your chosen concurrency. Suggested pairing if running 2–3 at a time: (RESOLVE, SCORE)
   → (INGEST, MONITOR) → (ASK, HITL). SCORE is the densest; RESOLVE is the marquee; do them while fresh.
3. **API** + **EVAL** in parallel, then **SHIP**.

**Dependency notes.** Every Wave-1 session builds against F0's *frozen contracts + golden fixtures*, not
against sibling code — so none blocks another. The only *soft* couplings (for the final artifact, not for
development): INGEST's committed seed-bundle is produced against the real store/config after F0+DATA-C;
API/EVAL/SHIP integrate merged Wave-1 code. Develop against fixtures; integrate at Wave 2.

---

## 4. Frozen contracts (the shared reference)

> These are frozen by **F0** as a **coordination floor** — the shapes siblings agree on so they compose
> without collision. Subplans implement against them and cite section numbers rather than re-deriving
> schemas; if one genuinely needs to evolve, that's a small contract-amendment (§2 Rule 3), not a fork — the
> contract is meant to *improve*, not to handcuff. Numeric constants (weights, thresholds, half-lives) are
> **config defaults, not code constants** — authored in `config/*.yaml` by DATA-C, validated against these
> schemas.

### 4.1 Package layout & file-ownership map

```
# ── repo root ──
backend/                            # ALL Python backend code, tests, deps live here (the separate backend dir)
  pyproject.toml          F0*       # baseline deps: pydantic, networkx, anthropic, google-genai(opt), fastapi,
                                    #   uvicorn, pyyaml, python-dateutil, rapidfuzz, rank-bm25, geopy,
                                    #   pytest, pytest-cov, ruff, mypy, httpx (test), respx (test).
                                    #   *Shared file: any session may APPEND deps it needs (additive; §2 R1).
  chanakya/
    schemas/              F0        # §4.2 records + value objects (Date/Location/Quantity) + config/view/API models
    config/               F0        # loader + live config store (read/write, seed-from-yaml)
    store/                F0        # §4.2 SQLite evidence+decision logs; append/query/seed/replay
    view/                 F0        # rebuild() orchestration + stage interfaces + STUBS + lens + JSON export
    resolve/              RESOLVE
    credibility/          SCORE
    sufficiency/          SCORE
    materiality/          SCORE
    observe/              MONITOR
    agent/                ASK
    hitl/                 HITL
    ingest/               INGEST    # incl. the Date/Location/Quantity normalization ADAPTERS (§4.2)
    api/                  API
  tests/
    fixtures/             F0        # golden synthetic evidence+decision logs + expected view JSON
    gates/                F0        # the abstraction-gate suite (§5)
    <module>/             owned by that module's session
    acceptance/           EVAL
  eval/                   EVAL
frontend/                           # OUT OF SCOPE (SPA) — API serves its build via StaticFiles; SHIP's Docker Node stage builds it
config/*.yaml             DATA-C    # ontology, sources, credibility, resolution, templates, subjects, observables
config/places.yaml        (exists)  # DATA-C may extend
corpus/scenarios/*/docs/  DATA-C    # frozen docs + manifests + answer_key
corpus/scenarios/*/claims/ INGEST   # pre-extracted claim bundles (keyless ingest)
tools/                    DATA-C    # existing generator/gather (stays ontology-blind, G11)
Dockerfile, compose       X0(skeleton) → SHIP(production)   # Node builds frontend/, Python installs backend/
Makefile                  F0(skeleton) → SHIP(real targets)
deploy/                   X0
.github/workflows/        F0
artifacts/plan/PROGRESS.md  (you, at merge)   # never in a PR
```

**Rooting convention.** The Python package lives at **`backend/`**; `config/`, `corpus/`, `tools/`, and the
deploy files (`Dockerfile`, `docker-compose.yml`, `Makefile`, `deploy/`) stay at repo root (the app resolves
`config/`+`corpus/` via a settings path defaulting to repo root; the Docker build COPYs them in). **In the §3
DAG and every `sessions/<ID>.md`, an owned path written `chanakya/<m>/**` or `tests/<m>/**` is rooted at
`backend/`** (i.e. `backend/chanakya/<m>/**`). F0 scaffolds the `backend/` tree.

### 4.2 Record schemas (`chanakya/schemas/`) — verbatim from `spine/08` §3.1–§3.3 + `C/01`

**Claim record (evidence log)** — the unit of analysis:
```yaml
claim_id:      c-000123                    # human-readable, e.g. "d05-row12" (spine/09 tool hygiene)
source_id:     src-ispr-2021-10-14         # → Source registry entry
doc_ref:       {file, span|row|page|bbox|frame|region}  # exact cited line / row / PDF page+bbox / image region
kind:          observation | inference | retraction
polarity:      positive | negative         # negative = observed absence (B pre-wiring #5)
asserts:       entity | relationship | event
payload:       (subject, predicate, object) | entity-descriptor | event-descriptor
event_time:    2021-10-14                  # ≡ C/01 valid_time; interval allowed; nullable+flagged
report_time:   2021-10-14
ingest_time:   2026-07-17
resolved_ref:  {entity_id, edge_instance}  # supersede/contradict match on THIS, never a string
extraction:    {method: llm|vlm, model, model_conf}     # model = extraction model id; model_conf = 1.0 for the demo
premises:      [claim_ids]                  # inference only
targets:       claim_id                     # retraction only
```
Event types are first-class (`{event_type, time-interval, location, participants}`): `TransferEvent`,
`InductionEvent`, `SightingEvent`, `ExerciseEvent`. Structural edges (`based-at`) are *states derived from
events*. **Claim-dedup:** same assertion restated within one doc = one claim + multiple `doc_ref` spans;
same assertion across docs = separate claims (never merged).

**Source registry entry** (`source_id` points here): `source_type`, `reliability_grade` (STANAG A–F),
`primary_origin_id`, `aggregator_of`, `bias_vector` ∈ {operator-state, exporter-state, third-party,
commercial, adversary}, `coordinated_inauthenticity_flag`, `adversary_denial_flag`, `cadence`, `citation_URL`.

**Decision / trace record (decision log)** — replay input + audit + learning, one schema:
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

**Derived assertion state (knowledge view)** — every edge/event carries: supporting claim IDs *grouped by
independence*, opposing claims, confidence breakdown (source-class base · integrity flags · independence
groups · freshness factor), `status`, freshness (`last_support_time`, half-life, decay factor), latest
sufficiency evaluation. Nodes additionally carry **precomputed materiality attrs** (§4.3). Status/confidence
are **computed, never stored on the node**.

**Known Gap node** (`C/01`): `what_missing`, `observability_ceiling` ∈ {confirmable, probable-max,
never-observable}, `next_coverage_due`. **Alert object** (MONITOR): `observable_id`, `subject`, `before`,
`after`, `severity`, `fired_ts`, `disposition?`.

**Value objects on the claim payload — shapes F0-frozen, normalization adapters INGEST-owned.** Three payload
fields carry structure that needs normalization. Locking the split now, since it straddles F0↔INGEST↔RESOLVE:

- **`Date`** (`event_time`/`report_time`/`ingest_time`) — adapted from `financial.py`'s **`DateSpec`/`Period`**
  pattern (`ally-pipelines/.../schemas/financial.py` §478–666). A point date is `ExactDate {iso_date, raw}`
  (keep the ISO sanitizer that clamps `2024-11-31`→`-30`) **or** `LabelDate {raw, granularity ∈
  year|half|quarter|month|day, year, quarter?|half?|month?}`; an **interval** `event_time` is a `Period
  {period_type: as_of|range, as_of|start|end: DateSpec}`. Carry `raw` + `boundary_source ∈ {explicit,
  derived_from_label, relative, model_guess}` for provenance. **OSINT deltas from the financial model:** drop
  the fiscal machinery (`FiscalContext`/`YearLabelType`) — **calendar only**; **add a `relative` form**
  ("last week", "recently") the INGEST adapter resolves **against the claim's `report_time`** into a dated
  `Period` + an `approximate` (circa/reported) flag. Proposer/disposer split, same as everywhere: **the LLM
  supplies `raw` + the structured label; the INGEST date adapter deterministically derives the ISO
  boundaries** (label→dates, relative→`report_time`-anchored). Powers freshness (SCORE, on the resolved
  date/interval) + supersede/contradict ordering.
- **`Location`** — the raw stated string(s) + surface-format hint, **plus the canonical stored form**
  `{wgs84_lat, wgs84_lon, geocode_candidates[], precision_class, resolved_place_ref?}`.
- **`Quantity`** — evidence-graded ranges `{value|min|max, unit, count_state ∈ ordered|delivered|fielded|
  nominal|combat-ready, approx}` (TEL counts, ~125 km, magazine depth).
- **Names/designators are NOT field-normalized** — captured raw, normalized by the **resolution layer**
  (RESOLVE: transliteration + alias + relational merge). Do not double-handle them at the field level.

**Shape vs. normalization — the locked rule.** The *model shapes* above are **F0-frozen** (in `schemas/`,
embedded on `ClaimRecord`, read downstream — SCORE reads `Date`, RESOLVE reads `Location`). The *normalization
adapters* are **INGEST-owned** and **run at extraction, pre-append — never as pydantic on-instantiation
validators.** (Critical: a validator would fire Nominatim/parsing on *every* deserialization, including when
`rebuild()` loads claims from the log → network in the rebuild path → breaks **G1**. The adapter is invoked
once at extraction; its output is persisted onto the record; reload does no work.) The **LLM extraction
models** the reviewer feeds the model (the function-calling schema) are INGEST's and *compose* these F0 value
objects — the LLM fills the raw/stated fields, the adapter fills the canonical slots.

**Location normalization happens DURING extraction (locked).** The canonical stored form is the geocode
(WGS84) — but **most source docs state only a place *name* or a relative reference ("~20 km NW of Sargodha"),
not coordinates**, so we cannot assume a coord is present: the INGEST `Location` adapter **normalizes at
extraction** — deterministic multi-format coord-canonicalisation (DD/DMS/MGRS/UTM/URL → WGS84) for docs that
*do* give a coord, **and Nominatim geocoding of names/relative refs** for the ones that don't — freezing the
WGS84 form + candidates onto the claim (frozen into the pre-extracted bundles too → keyless ingest hits no
network). The deterministic **place-resolution** (match canonical coords + toponyms to the gazetteer place
nodes; `distinct-from` traps like Karachi-Port ≠ Port-Qasim; the earned Chaklala alias) stays in **RESOLVE**
at rebuild. Exact precision/handling (Nominatim behaviour on the real strings, misses, ambiguity → HITL) is
tuned empirically on the corpus inside the INGEST session.

### 4.3 `rebuild()` pipeline + stage interfaces (`chanakya/view/`)

F0 defines `rebuild()` calling five pure stages, each a stable function signature implemented by its session;
F0 ships trivial stubs so the skeleton runs from day one:

| Stage | Signature (illustrative) | Implemented by |
|-------|--------------------------|----------------|
| resolution | `resolve(claims, config, prev_view) -> Partition {resolved_ref per claim, same-as/distinct-from}` | RESOLVE |
| credibility | `score_claims(resolved_claims, sources, config) -> {claim_credibility per claim}` | SCORE |
| status | `assign_status(assertions, groups, config) -> {assertion_confidence, gate_vector, status}` | SCORE |
| sufficiency | `check(assertion, claims, config) -> {satisfied, missing_slots, next_coverage_due, ceiling}` | SCORE |
| materiality | `precompute(view, config) -> node attrs {chokepoint_count, chokepoint_status, substitutability_state}` | SCORE |

Also F0-owned and real (not stubbed): **supersedes-vs-contradicts** resolution on `resolved_ref` (differ in
`event_time` → supersede→stale; same → contradict→HITL; uncertain instance → candidate-supersede);
**lens scoping** `apply_lens(view, subject) -> scoped_view` (N-hops-from-anchors + materiality filter — a
*required* build item at ~51 docs so distractors don't leak); **JSON export** matching §4.8. Stage
call-order is fixed: `resolve → score_claims → (group by independence) → assign_status → check → precompute`.

### 4.4 Config surface + live config store

Seven files, seeded from YAML into a **live, writable config store** the API mutates (hot-config):
`ontology.yaml` (node/edge/event types) · `sources.yaml` (registry: class, reliability_grade, cadence,
bias_vector, aggregator_of/primary_origin_id) · `credibility.yaml` (R-factor rubric + weights, integrity
penalties, thresholds 0.50/0.80, half-lives) · `resolution.yaml` (merge_score weights 0.30/0.40/0.15/0.15,
bands 0.85/0.55, blocking keys, seeded alias table, transliteration rules) · `templates.yaml`
(evidence-requirement templates per assertion type) · `subjects.yaml` (lenses: anchors, hop/materiality
rules, target queries) · `observables.yaml` (declarative tripwires incl. seeded relocation). **All numeric
knobs live here, never in code (gate G6).**

### 4.5 Agent tool surface (`chanakya/agent/`) — `spine/09`

Seven namespaced tools, `strict:true`, 3–4-sentence descriptions with *when-NOT-to-use*, typed params
(`node_id` not `node`), `input_examples` on `query_graph`, human-readable claim IDs, actionable errors:
`find_entity(text, type_hint?)` · `get_node(id)` · `neighbors(id, edge_types[], direction, limit, offset)` ·
`find_paths(src, dst, edge_whitelist?, max_hops≈4)` · `query_graph(anchor?, pattern, constraints[],
aggregate?)` (typed `<,≤,=,exists,not_exists` over raw + materiality attrs; returns matches + claim IDs +
a separate `indeterminate` partition — never drops UNKNOWN) · `get_evidence(node_or_edge_id)` ·
`check_sufficiency(scope)`. Bounds: hop≤4, top-k≈3, hard iteration cap, explicit LLM sufficiency-termination.
Fixed `link→gather→query_graph→cite` hero path primary; free loop for follow-ups; recorded trace = network
fallback. **Citation validator = entailment** (every cited claim exists, supports its hop, *and entails* the
sentence; counts match the tool's evidence set); empty result → `check_sufficiency` → reasoned insufficiency,
never a confident negative.

### 4.6 Observable DSL (`chanakya/observe/`) — `spine/09`

An observable is a condition in a small DSL over existing node/edge attrs + precomputed metrics (equality /
threshold / crossing / exists over the demo node types). Lifecycle: **define** (config or API) → **arm**
(evaluate against current graph on save; optional back-scan) → **fire** on next `rebuild()` → **disposition**
(real/noise/needs-more) feeds tuning. Declarative spec (`spine/08` §3.8): `{observable_id, subject,
trigger:{on, edge_type, match_on:[resolved_unit, site_instance], anchors_within_hops}, severity,
disposition}`. Seeded example = the Rawalpindi→Rahwali `based-at` occupancy state-change; secondary
`replenishes`/tender observables ship config-only.

### 4.7 HITL adjudication service (`chanakya/hitl/`) — `spine/05`, `spine/08` §3.10

One service, one signature: `enqueue(item, context, options, writeback) → decision → mutate view + emit
trace`. Writeback appends a decision-log entry; the next `rebuild()` applies `effects` (propagation is
structural). Reusable review-queue envelope: `{type, subject, context{confidence, materiality, novelty},
options, effects, actor, ts}`. **Three deep card payloads (build now):** merge (accept/reject/split → grows
alias table), status-override (promote/demote/reject → propagates), alert-disposition (real/noise/needs-more).
All 8 control points exist in the service; 5 are config/roadmap. Triage is **recall-biased** (hold recall of
escalation ≈ 1.0); ★ items deterministically pinned to the top (never trust LLM rank). Analyst-initiated
integrity flag = a caller of the same service; flagging a `primary_origin_id` propagates to all co-referring
claims on next rebuild.

### 4.8 API endpoints + view-JSON shapes (`chanakya/api/`) — `product/03`, `md/07`

FastAPI single process, same-origin. Endpoints (final names fixed in F0's API models):
`GET /view` (rebuilt graph JSON — §4.2 node/edge shapes) · `GET /node/{id}` + `GET /evidence/{id}`
(provenance drawer: claim clusters grouped by independence, integrity flags, freshness, status) ·
`POST /ask` (cited multi-hop answer: decomposition, per-hop citations, observed-vs-inferred tags, refusal
payload) · `POST /ingest` (raw doc → live extract+append+rebuild+observable-eval; or a pre-extracted bundle
keyless) · `POST /hitl/{merge|status|alert}` (writeback) · `POST /config/*` (hot-config writes: observable,
weights, thresholds, ontology types) · `GET /health` (200 only after `rebuild()`). View-JSON must satisfy
`product/03` A–H shapes (Claim, Node/Edge, Provenance drawer, Review-queue item, Ask answer, Observable,
Known Gap, Config surfaces). Field **names** may still move — treat `product/03` as the shape-of-record and
reconcile in F0's API models.

---

## 5. Executable abstraction gates (F0's `tests/gates/`, run in CI on every PR)

The abstraction design is enforced by tests, not prose. Every PR must keep all gates green; a shortcut that
bypasses the structure **fails CI**, not review. Each gate maps to an invariant (§1) / DECISIONS rule.

| Gate | Checks | Catches (violation signature) |
|------|--------|-------------------------------|
| **G1 rebuild-purity** | monkeypatch `socket`, `anthropic`, `time`, `random` to raise → `rebuild()` still runs to completion over the fixtures (primary, behavioral guard). Structural: the stage entry functions `rebuild()` calls (`resolve`,`score_claims`,`assign_status`,`check`,`precompute`) must not *reach* the LLM/network in their call-path — an offline `propose_*`/`extract` entrypoint in the same package, not imported by the stage, is allowed | any LLM/network/clock/RNG **invoked during** the rebuild call-path |
| **G2 rebuild-determinism** | same (logs, config) → byte-identical JSON across 2 runs | hidden nondeterminism (dict-order, set iteration, timestamps) |
| **G3 append-only store** | store exposes no UPDATE/DELETE; claims immutable; retraction is an appended claim | mutating/deleting claims; provenance at doc granularity |
| **G4 unit=claim traceability** | every node/edge in the view JSON carries ≥1 claim_id resolving to a real claim→doc_ref | naked assertions; provenance not per-claim |
| **G5 two-scores separation** | `merge_confidence` never feeds `assertion_confidence`; status is set only by the gate machine (no direct writes) | blending identity & truth confidence; hand-set "confirmed" |
| **G6 no-magic-numbers** | scoring/threshold/half-life literals absent from `credibility/`, `resolve/`, `materiality/`, `observe/` core; all read from config | a hardcoded threshold/weight/half-life in code |
| **G7 confirmed-gate** | cannot reach `confirmed` without sufficiency-satisfied AND ≥2 independent groups AND ≥0.80 AND clean gates (property test over fixtures) | probable masquerading as confirmed |
| **G8 insufficient-first-class** | a planted-gap fixture yields a `Known Gap` node with `missing_slots`+`next_coverage_due`, off the confidence scale; refusal prose is a template, not regenerated | fabricated assessment in an evidence-sparse case |
| **G9 ingestion source-typed** | import-boundary: `chanakya/ingest` must not import `subjects`/ontology-instance content; no branch keyed on subject | use-case-typed ingestion; hard relevance gate at ingest |
| **G10 subject-as-lens** | no per-subject table/namespace; core traversal takes subject config as a param; re-point = config edit | a bespoke "HQ-9/P graph"; subject baked into traversal |
| **G11 generator-blind** | `tools/generate` emits only raw text (no ontology import; no clean-field emission) | generator emitting structured entities/clean names |
| **G12 HITL-propagation** | a status-override decision appended to the log changes the view on rebuild (confirmed→probable→answer changes) | override written to a log without mutating state |

F0 seeds each gate with fixtures; a session that adds behaviour adds/extends the relevant gate fixture but
never weakens a gate.

---

## 6. Testing standards

- **Framework:** `pytest`; per-module tests under `tests/<module>/` built against F0's golden fixtures
  (`tests/fixtures/`), not against sibling code.
- **Fixtures:** F0 ships a small hand-authored evidence+decision log + the expected view JSON + per-stage
  fixtures (resolution input→partition; claim set→assertion_confidence; assertion→status/known-gap; two
  views→alert). These are synthetic and stable — decoupled from the C corpus so unit tests don't depend on
  DATA-C.
- **Determinism:** golden-file tests on the view JSON; every stage is a pure function tested in isolation.
  LLM-touching code (INGEST, RESOLVE candidate-gen, ASK) is tested with **recorded/mocked** LLM responses
  (`respx`/fixture transcripts) so tests are offline and deterministic; a separate opt-in `@live` marker
  exercises the real API when a key is present.
- **Coverage:** the scoring paths (credibility, status gates, sufficiency, noisy-OR, supersede/contradict)
  and the citation validator carry the highest bar; assert exact arithmetic (two 0.6→0.84; echoes→one group;
  gate caps at probable).
- **Acceptance (EVAL):** runs the frozen corpus end-to-end through ingest→rebuild→ask and checks against
  `answer_key.json` (nodes/edges/statuses/flexes), asserts the **spine-gate 5 criteria** and the **6 demo
  flexes**. This is the top-level gate; a Wave-2 merge requires it green.
- **Every PR:** `ruff` + `mypy` + `pytest` (incl. all §5 gates) green before you merge.

---

## 7. Deployment-readiness standards

- **One multi-stage image** (Node builds the SPA → static; Python runs FastAPI serving the static bundle +
  API). Frozen seeded SQLite baseline + `config/` + corpus baked in. `docker run` locally == the EC2 box.
- **X0 first (Day 0):** trivial route + `/health` + placeholder SPA → GHCR → `docker compose` + `cloudflared`
  on EC2 → confirm the https URL loads. Pays down image/registry/tunnel/TLS/secret cost before feature work.
- **Make targets (SHIP):** `make extract` · `make build` (rebuild view) · `make ingest DOC=…` ·
  `make ask Q="…"` · `make run` (docker build + serve). Reviewers run **both** paths.
- **Keyless boot + the three reviewer run-modes** (all over the *same* ingest lane — the reviewer chooses):
  **(1)** boot from the **seeded baseline** — default, **keyless**, instant → explore + run the hero query;
  **(2)** *at initial run*, **optionally trigger extraction from the raw corpus** (keyed — `make extract`,
  then run) so the graph is **built from raw docs live**, demonstrating the whole extraction→resolve→score
  pipeline rather than a pre-baked log; **(3)** *at runtime in the running app*, **ingest a new document**
  (`POST /ingest` or `make ingest DOC=…`) → live-extract (keyed) or append a pre-extracted bundle (keyless)
  → `rebuild()` → observables fire. **Ingestion is always available; extraction is the optional keyed part**
  — (2) and (3) are the graded *monitoring* axis, not a scripted reveal. Modes (1) and (2) converge on the
  **same graph** (the committed bundles are the frozen output of extracting the same corpus).
- **Secrets:** `ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) via `.env`/compose env var, gitignored,
  never baked. Bedrock-via-EC2-instance-role is the design-note prod path.
- **Health/readiness:** `/health` returns 200 only after `rebuild()`; `restart: unless-stopped`; rollback =
  pin the previous GHCR tag. Map tiles vendored; no external network on a graded beat; recorded hero-trace
  fallback for the Ask beat.
- Every session must leave the build **deployable** — its module imports cleanly, tests pass, and any
  dependency it adds installs cleanly in the image and doesn't break keyless boot or the vendored/offline
  demo path. **Adding a dependency is fine** — append it to `pyproject.toml` (prefer the locked stack or an
  existing dep first), and flag it in the PR so the image + deploy stay in sync. The "locked stack" names the
  *load-bearing* choices (store, view engine, agent shape, hosting); it is **not** a ban on helper libraries.

---

## 8. Worktree / PR workflow (per session)

Each session is one agent, one worktree, one PR, one merge, then teardown.

1. **Branch + worktree** off latest `main` (F0 already merged):
   `git worktree add ../wt-<ID> -b feat/<id>` (e.g. `feat/score-confidence-resolver`).
2. **Onboard** (see §9): read `CLAUDE.md` → `PROGRESS.md` → `sessions/<ID>.md` → the design docs it names →
   the §4 contract sections it implements.
3. **Implement e2e** inside owned paths only (§4.1). Keep all §5 gates + `ruff`/`mypy`/`pytest` green
   locally. Never edit a frozen/shared file; if you must, stop and raise an **F0-amendment PR** (Rule 3).
4. **Open PR to `main`** using the PR template (below). CI runs lint + type + full test suite + gates.
5. **Stay until merged.** Rebase onto `main` whenever a sibling merges (always a clean rebase given disjoint
   ownership); address review. **You (the user) are the sole merge authority** — the agent does not
   self-merge.
6. **After merge:** append the session's outcomes to its handoff note; you update `PROGRESS.md`; the agent
   runs `git worktree remove ../wt-<ID>` and deletes the branch.

**Branch naming:** `feat/<id>` lowercase (`feat/f0-foundation`, `feat/resolve`, `feat/score`, `feat/ask`, …).
**PR title:** `[<ID>] <one-line>`. **PR body template:**
```
## Session <ID> — <title>
Implements: §<contract sections> of 00-master-plan.
Owned paths: <list>            # reviewer verifies nothing outside this changed
Design docs honoured: <list>
### Acceptance (from sessions/<ID>.md)
- [ ] <criterion 1> …
### Gates
- [ ] G1–G12 green   - [ ] ruff/mypy/pytest green   - [ ] no frozen-file edits (or: F0-amendment #NN)
### Decisions taken (principle → choice → alternative rejected)   # → also appended to DECISIONS.md
### Handoff notes / follow-ups
```

---

## 9. Handoff & progress mechanism

**`PROGRESS.md`** (repo-root, *not* in any PR — you maintain it at merge time) is the live board any agent
reads to know where things stand. One row per session + a handoff-notes log:

```
| ID | Status | PR | Owns | Depends | Merged commit | Handoff note ↓ |
Status ∈ not-started · in-progress · in-review · merged · blocked
## Handoff notes
### <ID> (merged <commit>): what shipped · decisions · deviations from plan · follow-ups · gate additions
```

**Onboarding path for any agent (fresh context):** `CLAUDE.md` (boot) → `PROGRESS.md` (current state +
prior handoff notes) → `sessions/<ID>.md` (its task) → the design docs that session names → §4 of this
master. That chain is sufficient to start with no prior conversation.

**Decision discipline (per working agreements):** each session records guideline-driven decisions (choice ·
principle invoked · alternative rejected) in its PR body and appends them to `DECISIONS.md`; when it closes
an open question, it moves it into the ledger. Contract amendments are logged in both `PROGRESS.md` and
`DECISIONS.md`.

---

## 10. Session index

Thin, self-contained subplans (one per session), each pointing back to §4/§5 here:

- `sessions/F0.md` — Foundation, store, `rebuild()` skeleton, fixtures, gate suite, CI *(exemplar; read first)*
- `sessions/X0.md` — Walking-skeleton deploy
- `sessions/DATA-C.md` — Corpus freeze + C config content
- `sessions/RESOLVE.md` — Iterative relational entity resolution
- `sessions/SCORE.md` — Confidence Resolver + Sufficiency/Known-Gap + materiality precompute
- `sessions/MONITOR.md` — Observable DSL engine
- `sessions/ASK.md` — Bounded ReAct agent + citation validator
- `sessions/HITL.md` — Adjudication service + writeback + cards
- `sessions/INGEST.md` — Source-typed LLM extraction + live-ingest
- `sessions/API.md` — FastAPI layer
- `sessions/EVAL.md` — Acceptance harness
- `sessions/SHIP.md` — Production packaging & deploy
