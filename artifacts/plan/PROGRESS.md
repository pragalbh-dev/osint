# PROGRESS — Chanakya OSINT backend build

**The live board.** Any agent reads this (after `CLAUDE.md`) to know where things stand before starting.
**Each session maintains its own row + handoff note inside its PR; you review it with the diff, then merge**
(master §2 Rule 4, §9). A session touches only *its own* row/append, so PRs don't collide. Status ∈
`not-started · in-progress · in-review · merged · blocked`.

## Board

| ID | Session | Wave | Status | PR | Depends (merged) | Merged commit |
|----|---------|------|--------|----|--------------------|---------------|
| F0 | Foundation + store + rebuild skeleton + fixtures + gates + CI | 0 | merged | [#1](https://github.com/pragalbh-dev/osint/pull/1) | — | 7a9e87b |
| X0 | Walking-skeleton deploy (EC2 + tunnel + GHCR) | 0 | merged | [#5](https://github.com/pragalbh-dev/osint/pull/5) | — | 0c364be |
| DATA-C | Corpus freeze + C config YAML | 0 | merged | [#8](https://github.com/pragalbh-dev/osint/pull/8) | F0 (soft) | 407f1c2 |
| RESOLVE | Iterative relational entity resolution | 1 | in-review | [#23](https://github.com/pragalbh-dev/osint/pull/23) | F0 | — |
| SCORE | Confidence Resolver + Sufficiency/Known-Gap + materiality | 1 | in-review | [#20](https://github.com/pragalbh-dev/osint/pull/20) | F0 (+ F0-amend [#18](https://github.com/pragalbh-dev/osint/pull/18)) | — |
| MONITOR | Observable DSL engine | 1 | in-review | [#11](https://github.com/pragalbh-dev/osint/pull/11) | F0 | — |
| ASK | Bounded ReAct agent + citation validator | 1 | in-review | [#14](https://github.com/pragalbh-dev/osint/pull/14) | F0 | — |
| HITL | Adjudication service + writeback + 3 cards | 1 | in-review | [#12](https://github.com/pragalbh-dev/osint/pull/12) | F0 | — |
| INGEST | Source-typed LLM extraction + live-ingest + seed bundles | 1 | in-review | [#17](https://github.com/pragalbh-dev/osint/pull/17) | F0 (+DATA-C soft) | — |
| API | FastAPI layer | 2 | in-review | [#25](https://github.com/pragalbh-dev/osint/pull/25) | RESOLVE, SCORE, ASK, HITL, MONITOR, INGEST | — |
| EVAL | Acceptance harness (spine gate + demo flexes) | 2 | not-started | — | all Wave-1 + DATA-C + INGEST | — |
| SHIP | Production packaging & deploy | 2 | not-started | — | API (+X0, DATA-C, INGEST) | — |

## Contract amendments (F0-amendment PRs)
_Post-F0 changes to a frozen contract go here. Each entry: what changed, which contract §, which sessions must rebase._

**MONITOR observable-scope amendment (2026-07-18, branch `f0/observable-watch-instances`):** added an
optional typed field **`watch_instances: list[str] = []`** to `ObservableDef` (master §4.4/§4.6) so an
analyst can watch an **explicit set of resolved entities** (multi-select or a text→observable proposer),
scope = lens ∪ watch_instances. Additive/optional → siblings need no change; **MONITOR/API/frontend**
consume it. Also aligned the golden `alert_delta.json` per-stage fixture from the stray `unit_x` →
`unit_acme` so the seeded `obs-relocation` (subject `lens-acme`, anchor `unit_acme`) actually scopes to
the watched unit; and reconciled the stale `spine/08` §3.10 control-point-5 note ("config-authored, not a
UI") to defer to the `spine/09` in-app define → arm-on-save → fire-on-next-rebuild model. **Board fix:**
corrected stale rows — F0 (merged #1/`7a9e87b`) and DATA-C (merged #8/`407f1c2`).

**Plan-authoring refinements (folded in before F0 is built — no rebase needed):**
- Added **`config/resolution.yaml`** as the 7th config file (merge weights/bands/blocking keys/alias-seed/
  transliteration) — master §4.4/§4.1; authored by DATA-C, schema in F0, consumed by RESOLVE. *(RESOLVE
  flagged the missing home.)*
- Reworded **gate G1** to guard the *rebuild call-path* behaviorally (rebuild runs with the LLM patched to
  raise), not to ban `anthropic` from a stage package — so RESOLVE/INGEST may house an offline proposer/
  extractor in-package. Master §1 invariant #2 + §5 G1. *(RESOLVE/INGEST flagged the tension.)*

**Post-F0 amendments (folded into the owning session's PR; dependents rebase):**
- **`ask()` gains two optional query-time inputs** — frozen entrypoint is now
  `ask(question, view, config, llm=None, claims=None) -> AskAnswer` (was `ask(question, view, config)`).
  Master §4.5. *Both additive & optional* — the existing/planned caller `ask(question, view, config)`
  (**API** session) is unaffected, so no rebase is required.
  - `llm` — the query-time `chanakya.agent.client.LLMClient` seam (mock/recorded in tests, settings-built
    at runtime, keyless → recorded-trace replay). *(user-approved the amendment route over injecting the
    client internally.)*
  - `claims` — a `claim_id → ClaimRecord` lookup. `rebuild()` emits a view that references claims by ID
    only; the record bodies (`kind`, `doc_ref`, source, dates) stay in the evidence log, but `get_evidence`
    (source/date/span) and observed-vs-inferred (from `kind`) need them. **API** passes
    `{c.claim_id: c for c in store.replay()}`. *(ASK call — necessary, additive, API-compatible; the
    view alone cannot cite a source/date/span or tag observed-vs-inferred.)*
  Lands in the **ASK** PR (`feat/ask`); `chanakya/agent/` is ASK-owned, so the edit is in-path — logged
  here per Rule 3 because the *signature* is a contract API reads. *(ASK, 2026-07-18.)*
- **`DocRef.line` + `ClaimRecord.attributes`** (`f0/ingest-schema-slots`, INGEST prep — PR #15) — a nullable
  `line:int` (1-indexed txt line locator, alongside the exact char `span`) on `DocRef`, and a nullable typed
  `attributes:dict` bag on `ClaimRecord` (tier-3 of INGEST's 3-tier attribute promotion: source-native
  context with no ontology home — HS-code/container#/BoL#). Master §4.2. Additive only → Wave-1 siblings pick
  up two new nullable fields on rebase; no code change required. F0 suite (63 tests) green.

**Places + merge-edge amendments (branch `f0/places-and-merge-edges`; dependents rebase onto `main`):**
- **`places` is the 8th loaded config section (`PlacesConfig`)** — master §4.1/§4.4. `config/places.yaml`
  is now served by the live config store (hot-config, `set_section("places", …)`) and consumed by RESOLVE;
  it was previously standalone/unloaded. `ConfigBundle` gains a `.places` field (additive). *(PR
  `f0/places-and-merge-edges`; RESOLVE flagged the gap.)*
- **`Partition` gains `candidates` (HITL-band pairs) + `merge_breakdown` (per-pair score breakdown) +
  `entity_canonical` (raw entity ref → canonical id)**; a `pair_key(a, b)` helper indexes
  `merge_confidence`/`merge_breakdown` — `schemas/stage_io.py`. Additive; the F0 stub still returns them
  empty → golden view byte-identical (G2). *(PR `f0/places-and-merge-edges`.)*
- **`resolve()` signature gains `decisions` (the replayed decision log)** —
  `resolve(claims, config, prev_view=None, decisions=None)`. It is RESOLVE's channel for the offline LLM
  proposer's frozen `merge_proposal` records + analyst `merge_adjudication(accept)`s that grow the alias
  table (spine/03:37 — resolution is a pure function of *evidence log, decision log, config*). Only
  `rebuild()` calls `resolve()`, so no sibling breaks; still LLM-free on the rebuild path (G1). *(PR
  `f0/places-and-merge-edges`.)*
- **`_assemble()` reconnects a merged entity's edges to its canonical node** via
  `Partition.entity_canonical` — edges attach by the *raw* triple subject/object (supersede.py), so a
  merge would otherwise dangle them. Empty map ⇒ identity ⇒ golden unchanged (G2). *(PR
  `f0/places-and-merge-edges`.)*
- **`rebuild()` renders the resolver's decisions as edges** — candidate `same-as` (HITL band) +
  `distinct-from` (both already G4-exempt + ontology-declared), carrying `merge_confidence` + breakdown;
  accepted merges stamp `resolved_from` provenance on the canonical node. Emitted *after* the status
  machine → never scored (G5). master §4.3. **Rebase note:** sessions reading the view (SCORE, MONITOR,
  ASK, API) + in-flight branches rebase onto `main` after this merges — purely additive (new edge types
  + a node attr), no field removed. *(PR `f0/places-and-merge-edges`.)*

## Known build-time reconciliations (F0 / build must resolve — not blockers)
- **F0 location descriptor** must carry `geocode_candidates` + `proposed_alias` so INGEST can freeze
  Nominatim/LLM place proposals onto the ClaimRecord upstream of the append (INGEST flag #1).
  **RESOLVED (already in F0):** `Location` on `main` already carries `geocode_candidates`, `proposed_alias`,
  `wgs84_lat/lon`, `precision_class`, `resolved_place_ref` — no amendment needed; INGEST fills the existing slots.
- **`ClaimRecord.extraction` field naming** — rename the ambiguous `version` → **`model`** (the extraction
  model id) so the frozen contract matches INGEST's `extraction.model`; final shape `{method: llm|vlm, model,
  model_conf}`. One-line F0-amendment, docs-only (backend greenfield). *(DECIDED 2026-07-18; see `md/15` §4 +
  DECISIONS §3; raised as its own F0-amendment PR.)*
  **DEFERRED (INGEST 2026-07-18):** the rename did NOT land on `main` (field is still `version`); renaming
  mid-Wave-1 churns `claim.py` + every consumer for zero demo benefit, so INGEST emits `{method, version,
  model_conf}` (model-id string in `version`) and `version`→`model` becomes a **post-INGEST** cleanup PR — not
  this amendment.
- **Hero-trace edge names** (`ASK`/`EVAL`) — `…imported-by → exported-by → supplies-component` must be
  reconciled against DATA-C's `ontology.yaml` + `answer_key.json`, which are authoritative for exact edge
  names (`C/02` notes the anchor is "to be verified against the generated corpus"). Resolve at DATA-C author
  time; ASK/EVAL bind to whatever the answer_key uses.
  **RESOLVED (DATA-C 2026-07-18):** hero path (traversed battery→origin) is
  `site_karachi ←based-at– unit_paad ←inducted-into– var_hq9p ←equips– comp_ht233 ←manufactures– mfr_casic`
  (canonical edge directions stored origin-ward; traverse bidirectionally). **`equips`** (Component→Variant)
  replaces the overloaded `supplies-component`, now **reserved Manufacturer→Component**. **No `candidate-*`
  edge types** — candidate-ness is a computed edge status (`possible`). Sustainment **split** into
  `techdata_authority` + `interceptor_stockpile`. Dropped `variant-of` (family = Variant attr) + `imported-via`.
  ASK/EVAL bind to these names.
- **`make extract`** is SHIP's Makefile target; INGEST ships only the CLI entrypoint it invokes (INGEST flag #2).

## Handoff notes
_Appended by each session in its PR (stamped with the merge commit at merge). Each entry: what shipped ·
decisions (principle→choice→alternative) · deviations from plan · follow-ups · any gate fixtures added/extended._

### F0 (merged <commit>):

### X0 (merged 0c364be — PR #5): Walking-skeleton deploy
- **Shipped:** self-contained `app_skeleton/` (FastAPI `/health` + minimal Vite placeholder SPA); multi-stage
  `Dockerfile` (`node:20-alpine` builds SPA → `python:3.12-slim` serves it + API); `docker-compose.yml`
  (`restart: unless-stopped`, `127.0.0.1` bind + `APP_PORT` override, `ANTHROPIC_API_KEY` via `env_file`,
  profile-gated `cloudflared`); `deploy/` (README runbook, `bootstrap-ec2.sh`, `verify.sh`, `prove-live.sh`).
  Public GHCR image `ghcr.io/pragalbh-dev/osint:skeleton` (digest `59cb67c748dd…`).
- **Proven live:** image → GHCR → Docker on EC2 (the moltbot box; Docker installed fresh, moltbot is native so
  untouched) → Cloudflare Tunnel; `/health`=200 and `/` serves the SPA locally, from an anonymous GHCR pull,
  and over a public https tunnel URL. Secret injected via `env_file`, empty in the raw image.
- **Decisions:** build context = `app_skeleton/` (strict ownership; SHIP repoints to repo root) · vanilla-JS
  Vite skeleton (leanest real Node build) · ephemeral `trycloudflare` for the proof + token-tunnel for the
  persistent URL · `APP_PORT` for co-location · `env_file` secret injection (never baked).
- **Deviations:** none (no F0-amendment). Rebased clean onto `main@9f18c07`; deploy merged as #5 (`0c364be`).
  A plan change rode along (Rule 4 flip — sessions maintain `PROGRESS.md` in-PR; primary checkout read-only);
  a merge race meant it landed via a small follow-up PR rather than #5 itself. This row/note is the first
  written under the new rule.
- **Follow-ups (SHIP):** repoint Docker context to repo root; bake `config/`+corpus+seed-SQLite+`backend/`/
  `frontend/`; swap `requirements.txt`→`backend/pyproject.toml`; own `:latest`; rollback drill; token-tunnel
  on the dedicated box for a persistent URL.
- **Gate fixtures:** none (X0 adds no `chanakya/` code; G1–G12 N/A).

### DATA-C (in-review, feat/data-c):
- **Shipped:** the **7 `config/*.yaml`** (ontology/sources/credibility/resolution/templates/subjects/
  observables) — validate + hot-round-trip through F0's config store; generator keyed on `ANTHROPIC_API_KEY`
  only (**G11 green**); **corpus/oracle/text fixes applied + verified** against `answer_key.json`; **F5
  confirmed deep-tier** added under an evidence gate (new doc `d24`); two `tmp/conv/` handoff docs
  (observations + flex-protection changelog).
- **Decisions (principle → choice → alt rejected):**
  - *Answer_key is authoritative + build-it-well* → renamed the overloaded hero edge to **`equips`** (vs
    keeping `supplies-component` overloaded across two node-type pairs); split **sustainment** into two node
    types (vs one merged type that can't carry two freshness classes).
  - *Bi-level, status-is-computed* → **no `candidate-*` edge types**; candidate-ness = edge status `possible`
    (vs baking candidacy into the edge type).
  - *Config-driven, no magic numbers (G6)* → all weights/thresholds/half-lives in `credibility.yaml`;
    integrity tables flattened, gates as an extra `gates:` field (vs hardcoding in SCORE).
  - *Non-negotiable — no fabricated certainty* → F5 confirmed deep-tier only via a source that **directly
    names supplier+component+relationship** (Taian/Wanshan TEL chassis, `d24`), not a bare sanctions listing;
    HT-233 chokepoint kept `candidate`/`UNKNOWN`; 23rd RI/4th Academy kept `possible`.
  - *`source_type` == credibility class* → `sources.yaml source_type` vocabulary matches
    `credibility.source_class_factors` keys (direct R lookup, no mapping layer).
- **Deviations from plan:** none affecting shared contracts (PROGRESS.md in-PR is the standard under the
  updated Rule 4). Full per-fixture **provenance-sidecar system** + the **ingest oracle-boundary guardrail**
  deferred (generator / INGEST scope, documented in the changelog).
- **Follow-ups:** EVAL must confirm the pipeline reaches the oracle's F5-confirmed + equips/split names at
  runtime; **H-200→HT-233 orphan alias** stays OUT of the resolver seed (earn/verify — adaptation demo);
  F7 structural cases (substitutable-by 3-state, MUCD, operational-status) represented-not-instantiated (roadmap).
- **Gate fixtures:** none added (config/corpus session; backend gates untouched, G11 re-verified green).

### MONITOR (in-review, feat/monitor — PR #11):
- **Shipped:** `chanakya/observe/**` — the declarative observable evaluator over `rebuild()` view deltas.
  `evaluate(prev_view, view, config) -> [Alert]` (frozen sig) + `arm()` (arm-on-save read-only pass +
  back-scan) + `explain()` (how an observable compiles — for the config UI / ASK proposer) +
  `read_dispositions()` (reads `alert_disposition` back into per-observable tuning stats). One generic DSL
  (eq/ne/lt/le/gt/ge/exists/not_exists + crossing as a delta mode) with named-`on` sugar → crossing /
  exists / match / **arm-only**, **no per-observable branch**. 40 module tests; full backend suite green
  (103); gates G1–G12 green; ruff + mypy clean.
- **Decisions (principle → choice → alt rejected):** see DECISIONS.md §6 → "MONITOR". Headlines: explicit
  `watch_instances` ∪ lens scope (F0-amend #9); `new_claim` = arm-only (honest boundary — claims aren't in
  the view); match on resolved `edge_instance`/`id` not designators; `fired_ts` left for the API
  (deterministic evaluate); lenient scope fallback (recall bias); disposition = MONITOR consumes / HITL
  writes / config vocabulary / nothing auto-retunes; **location seam built (geofence + "near-a-place"
  scope) but NOT demo-wired** (locked "build seam, roadmap the demo" call, 2026-07-18).
- **Deviations from plan:** none affecting shared contracts. One F0-amendment (#9, merged first): added
  optional `ObservableDef.watch_instances`, aligned the `alert_delta.json` fixture (`unit_x`→`unit_acme`),
  reconciled a stale `spine/08` §3.10 line, corrected the stale board rows (F0/DATA-C → merged).
- **Follow-ups (ASK):** ASK owns **`propose_observable_from_text()`** — free text → an `ObservableDef`
  draft, reusing `find_entity` to resolve named mentions to resolved ids (LLM proposes upstream; analyst
  confirms before arming). MONITOR pre-wired the target (`watch_instances` + `explain()`); this is an ASK
  scope addition, not built here. **(EVAL/roadmap):** wire the location geofence as a roadmap flex; the
  seam + `within_area` primitive are shipped and tested but no geofence observable is in the demo config.
- **Gate fixtures:** none added; extended none. Consumes F0's `per_stage/alert_delta.json` (aligned in #9)
  as the seeded before→after fire fixture. G1 (no network/LLM in `observe/`) + G6 (no scoring literals)
  re-verified green.

### ASK (in-review, feat/ask — PR #14):
- **Shipped:** the cited multi-hop QnA agent as a callable `ask(question, view, config, llm=None, claims=None)
  -> AskAnswer` in `chanakya/agent/` — the 7 deterministic `graph_*` tools (`context.py`+`tools.py`), their
  `strict` JSON schemas with when-NOT-to-use + `input_examples` (`tool_specs.py`), the provider-agnostic LLM
  seam (`client.py`: `LLMClient` protocol · `AnthropicClient` · `ScriptedClient` for offline/recorded),
  the bounded ReAct loop + deterministic fixed hero path (`loop.py`), deterministic answer assembly across
  query shapes (`assemble.py`), the entailment citation validator (`validate.py`), the `ask()` entrypoint,
  and `propose.py` (free text → `ObservableDef` draft — the MONITOR-handoff scope, below).
  **62 agent tests + 2 opt-in `@live`; full suite 165 pass/2 skip (post-rebase on MONITOR #11); ruff + mypy
  + all §5 gates green.**
- **Acceptance met:** hero query traces `based-at → inducted-into → equips → manufactures` citing a real
  claim at each hop; **HT-233 renders CANDIDATE (`substitutability_state=UNKNOWN` → `indeterminate`), never a
  confirmed sole-source**; planted-gap → reasoned insufficiency (`missing_slots` + `next_coverage_due` +
  Known Gap); validator rejects uncited / non-supporting / count-mismatch / not-entailed (mocked judge);
  `find_entity('HQ9P')` fires the "did you mean 'HQ-9/P'?" error; determinism verified (identical `model_dump`).
- **Wide query battery + coverage verdict:** all 10 spine/09 taxonomy shapes exercised (point · 1-hop ·
  multi-hop · filtered · aggregate · status/corroboration · gap · temporal · reverse · ranking) + 2
  adversarial (misspelling → refusal, no wrong bind; "confirmed sole-source?" → INDETERMINATE, absence ≠
  negative). **Every case is answered-with-citations or refused — never fabricated** (`tests/agent/test_battery.py`).
  **Coverage verdict:** the frozen 5-operator + `aggregate` `query_graph` surface over raw + materiality
  attrs served every shape by *composition* — **no surface extension (new operator/attr/tool) was required**.
  *(Added ops `!=`, `>`, `>=`, `in` beyond the spine/09 core `<,≤,=,exists,not_exists` — additive breadth,
  agent-local, no shared-contract change.)*
- **Observable proposer (MONITOR handoff, folded in):** `propose_observable_from_text(text, view, config,
  llm=None) -> ObservableProposal` (`agent/propose.py`) — free text → an `ObservableDef` **draft**. The LLM
  proposes the trigger intent + named mentions (a `draft_observable` structured tool call); `find_entity`
  resolves each mention → `watch_instances` (resolved node ids, **never designator strings**); an
  unresolvable mention is surfaced with its "did you mean" — **never silently wrong-bound**; MONITOR's
  `explain()` is attached for the confirm screen. **Never arms** (`needs_confirmation=True`): the analyst
  confirms, then MONITOR's `arm()`/`evaluate()` take over. Consumes F0-amend #9 (`ObservableDef.watch_instances`)
  + `chanakya.observe.{explain,arm}`; integration-tested against `observe.arm()` (a real cross-session check).
  Closes the ASK follow-up MONITOR handed over (DECISIONS §6 MONITOR).
- **Decisions (principle → choice → alt rejected):**
  - *Testability + keyless boot (invariant #2, §6)* → **F0-amendment**: `ask()` gains optional `llm` + `claims`
    (both additive; API caller unaffected) — see Contract amendments above. Rejected: internal-only client
    construction (un-injectable) / stuffing claims into `view.meta` (bloats `/view`).
  - *Answer_key authoritative (design-authority order)* → hero chain bound to `based-at/inducted-into/equips/
    manufactures`; ASK.md's `imported-by/exported-by/supplies-component` treated as stale.
  - *Non-negotiable — absence ≠ evidence of absence* → chokepoint-honesty fork closed along spine/09's leaning:
    `query_graph` reports matches + a separate `indeterminate` partition; UNKNOWN never counted as a negative.
  - *LLM plans, tools compute (spine/09)* → the answer text is assembled **deterministically from tool
    results** (citations a by-product), not from model prose; the entailment judge validates each assembled
    sentence. Rejected: trusting the LLM's free-form final answer.
  - *Deterministic + offline-testable (§6)* → entailment judge runs only for a live client; ScriptedClient
    (offline/recorded) paths use the deterministic validation part; autouse fixture strips keys for non-`@live`.
- **Deviations from plan:** none affecting shared contracts beyond the logged F0-amendment. `ask()` also
  serves point/1-hop/filter/status/reverse/ranking shapes (assemble builds cited answers from
  `query_graph`/`neighbors`/`get_node`/`get_evidence`, not only `find_paths`) — a capability add, not a
  contract change.
- **Follow-ups:** real-corpus loop-parameter calibration (hop cap / top-k / where LLM-pruning earns its cost)
  is a build-time tune once DATA-C/INGEST land (out of scope here, per ASK.md); the committed **recorded
  hero-trace** (a `ScriptedClient` transcript for keyless replay of the *free-loop* hero, distinct from the
  no-LLM fixed path) is best frozen against the real seeded view at Wave-2 (API/EVAL); API session calls
  `ask(...)` and passes `claims = {c.claim_id: c for c in store.replay()}`.
- **Gate fixtures:** none added/weakened (ASK owns `chanakya/agent/**` + `tests/agent/**`; G1 still green —
  runtime LLM is import-lazy and outside the rebuild call-path).

### HITL (in-review, feat/hitl):
- **Shipped:** the one cross-cutting adjudication service under `backend/chanakya/hitl/` —
  `service.py` (`enqueue` triage-gate + `dispose` analyst path) · `triage.py` (recall-biased
  escalate-vs-auto gate + `order_queue` with ★-pinning and raise-only frozen LLM rank) · `queue.py`
  (envelope builder over F0's `ReviewQueueItem` + transient `ReviewQueue`) · `writeback.py`
  (disposition → appended `DecisionRecord`, deterministic `event_id`, append-only) · `controlpoints.py`
  (all **8** control points catalogued in one service; 3 ★ wired deep — merge/status-override/alert —
  + the built analyst-initiated integrity flag; the other 4 named config/roadmap). 32 tests in
  `tests/hitl/**`; **full suite green (post-rebase on ASK #14 / MONITOR #11), ruff + mypy clean.**
- **Decisions (principle → choice → alt rejected):** see `DECISIONS.md` §6 "HITL". Headlines:
  - *Demo-reliability / don't fork a shared contract* → **`reject` = forced demote (`set_status→probable`),
    no F0-amendment** *(user 2026-07-18)*; the claim-exclusion machine-recompute is deferred to EVAL.
  - *Structural propagation (G12)* → **writeback only appends; `rebuild()` applies `effects`** (no per-stage
    fan-out).
  - *G1/G2* → **disposing path has no LLM/network/clock/RNG**; `event_id` derived from (item, option), `ts`
    supplied; the triage-rank LLM is offline/frozen/replayed (data, never a live call). `chanakya/hitl`
    imports no `anthropic`/`httpx`/`requests` (asserted in-test).
  - *Recall ≈ 1.0* → **auto-proceed only on positive safety on all of confidence/materiality/novelty**;
    any unknown escalates. ★ pinning + no-drop/no-inject enforced structurally in `order_queue`.
  - *Config-driven, minimal amendment surface* → **`TriageConfig` is HITL-owned + overridable**, not a new
    shared config section.
- **Deviations from plan:** (1) `reject` scoped to forced-demote (above) — session acceptance #1's
  machine-recompute deferred. (2) Integrity flag propagates at the **element** level via F0's existing
  `add_integrity_flag` (co-referring claims share one element) + carries a `flag_origin` intent; true
  per-claim + *future-claim* origin fan-out is SCORE's (a monitoring-grade gap, flagged for EVAL). **No
  F0-amendment; no shared-contract change; no frozen-file edits.**
- **Follow-ups (EVAL):** re-verify end-to-end once SCORE lands — (a) reject→confirmed→probable via the real
  status machine, (b) integrity origin fan-out across claims/future claims. Effect shapes HITL emits for
  siblings: `grow_alias`/`record_distinct`/`split_merge` (RESOLVE) · `set_status` (SCORE) ·
  `tune_tripwire` (MONITOR) · `add_integrity_flag`+`flag_origin` (SCORE).
- **Gate fixtures:** extended G12 coverage lives in `tests/hitl/test_acceptance.py` (F0's
  `tests/gates/test_g12_*` untouched and green); no gate weakened.
- **Board note:** F0/DATA-C rows read stale at branch time (F0 `not-started`, DATA-C `in-review`) though
  both were merged (PR #1/#8); left others' rows untouched per Rule 4 — the amendment PR #9 has since
  corrected them, picked up on rebase.
### INGEST (in-review, feat/ingest — PR #17): Source-typed extraction + live lane + keyless bundles
- **Shipped:** the full `chanakya/ingest/**` (12 modules, ~4.3k LOC, 172 tests; whole suite 337 pass, all
  gates G1–G12 green, ruff+mypy clean): source-typed **loaders** (`text, regions[]` + exact char-span+line /
  page+bbox provenance; Azure DocIntel OCR seam + born-digital poppler fallback); a **2-method extraction
  client** (Gemini-primary + Anthropic + scripted; provider-native forced-tool function-calling, no sampling
  params); **6 native-format extraction schemas + transformers** (prose / NOTAM / customs-BoL / tender /
  social / imagery-geoint) with a deterministic format sniffer, node-typing, 3-tier attribute promotion,
  verbatim-first `doc_ref`, and the **extract-raw guardrail**; **Date/Location/Quantity adapters** (explicit
  pre-append, opt-in geocoding); **image two-hash** (sha256 + PDQ + EXIF); the **subject-blind imagery VLM
  lane** (observation + guided signature→variant inference); **within-doc dedup + byte-stable readable ids**
  (with premise/target remap); the **concurrent live lane** (`ingest_document`: parallel extraction
  across+within docs → serial single-writer append → **injected** rebuild/observe); the **keyless seed**
  (`ingest_bundle`, `seed_store_from_bundles`, `extract_corpus` byte-stable bundles + `python -m
  chanakya.ingest` CLI).
- **Decisions (principle → choice → alt rejected):**
  - *G9 source-typed + decoupled* → the lane triggers rebuild/observe via **injected callables**, never an
    import (the `/ingest` API passes `chanakya.view.rebuild` + `chanakya.observe.evaluate`); the G9 gate
    caught the coupling, and the DI both satisfies it and makes the lane trivially unit-testable. Rejected:
    importing the stages.
  - *Native record format, not credibility `source_type`* → 6 format-keyed schemas + a deterministic text
    sniffer. Rejected: one schema per source_type (mis-routes NOTAM/tender).
  - *All-optional = anti-fabrication* → permissive schemas (no strict/required), empty fill → 0 claims;
    imagery count is a range-with-abstention (no single-integer slot → a fabricated count is structurally
    impossible).
  - *Concurrency without breaking determinism (G2)* → parallel extraction (`asyncio.to_thread` under a
    semaphore) then a serial deterministic id pass; ids byte-stable regardless of the race.
  - *Fix the general case, not the caller* → premise/target remap lives in `dedup.assign_claim_ids` (covers
    the lane AND the seed), not a per-caller patch.
- **Adversarial review:** a 6-lens review (→ verify) found 7 confirmed defects; **5 fixed** (imagery empty-
  site guardrail → affirmative-occupancy allowlist; provisional-id collision → per-chunk namespacing;
  network-in-claim-path → opt-in offline geocoding; event-type mistype → inferred from participants;
  stale-bundle drift → prune). Regression tests added.
- **Deviations from plan:** `doc_ref` shorthand `{file,span|row|frame}` → the full frozen `DocRef`;
  `observe.evaluate` is 3-arg `(prev_view, view, config)` (not the doc's 1-arg) — the lane binds the real
  signature; extraction ontology-org catch-all = `manufacturer` (no generic org type — see follow-ups).
- **Follow-ups:** (1) **real frozen bundles** need a keyed `make extract` (no API key in env now) — the seed
  CODE + CLI are built + tested with scripted clients; the committed `corpus/scenarios/*/claims/*.json` await
  the user's Gemini model id + key. (2) **geocoding is opt-in/offline by default** — for byte-stable Rahwali
  coords, inject a **gazetteer-backed geocoder** (`config/places.yaml`) at `make extract`; the bearing-offset
  is computed only when a geocoder is injected, else deferred to RESOLVE's gazetteer. (3) the `/ingest`
  endpoint should be a **sync `def`** (or add an async lane entrypoint) so `asyncio.run` isn't called from a
  running loop. (4) LOW review items: the customs **consignee is typed `manufacturer`** (routed to DATA-C via
  `tmp/conv` — needs a generic commercial-org node type); a quote-not-found `doc_ref` fallback may cite the
  entity name's first occurrence (minor mis-cite).
- **Gate fixtures:** none added/weakened; INGEST owns `chanakya/ingest/**` + `tests/ingest/**`. G9's meaning
  is preserved (the lane's DI keeps it green rather than weakening the gate).

### INGEST follow-up (feat/ingest-pdf-geo, stacked on #17): PDF-multimodal + geocoding wiring
- **Shipped** (from the deferred handoff `tmp/conv/INGEST-handoff-pdf-geocoding-keyless.md`; whole suite
  **403 pass** / 6 skip, all gates green, ruff+mypy clean; +24 tests):
  - **PDF path rebuilt to one non-brittle read** — no born-digital detection: `AZURE_*` present → Azure OCR
    (paged text+tables+figures, now **char-spanned** so page/bbox provenance survives — G4); else pymupdf
    text layer (poppler fallback). **Every page is always rendered to an image** (pymupdf), and text + page
    images feed **one multimodal `extract` call** (prose+tables+figures read together). Oversized docs are
    **page-window chunked** (guard `PDF_CHUNK_MAX_PAGES=8`/`_CHARS=60_000`) with filled dicts merged before
    one transform pass → one dedup batch (G2). `LoadedDoc.page_images` (`PageImage`) added.
  - **Client seam** `extract(*, …, images=[])` across the protocol + Gemini/Anthropic/scripted (additive,
    back-compatible — images passed only when present; `read_image` stays for the standalone-imagery lane).
  - **Two-stage geocoder** — `GazetteerGeocoder` (offline EXACT-match coord-cache over `config/places.yaml`:
    canonical_name/alias/icao/locode → `canonical_dd`, `source="gazetteer"`) → `ChainedGeocoder([gaz,
    Nominatim])`, threaded through `extract_document` → `em.location()` (all 7 site call-sites). Recorder
    defaults offline; the CLI (`make extract`) builds the live chain (`--offline` = gazetteer-only).
    `resolved_place_ref` stays `None` (identity is RESOLVE's). Local `gazetteer_key` normaliser is a
    **byte-identical, test-pinned copy** of RESOLVE's `normalize()` (RESOLVE unmerged → can't import; dedupe
    when it lands).
- **Validated LIVE** (real creds/network, controlled to ~1 page each): real **Azure OCR** through the loader
  (env-name wiring `AZURE_ENDPOINT`/`AZURE_API_KEY`, regions+bbox, `find→page` provenance resolves); real
  **Gemini multimodal** (`gemini-flash-latest`) reading a rendered figure page → claims that include a
  component read off the **drawn figure**, all page-provenanced; and real **Nominatim** — the chained
  gazetteer→Nominatim routing (seeded "PAF Base Nur Khan"→gazetteer offline; unseeded "Sialkot"→Nominatim,
  `source` tagged correctly) plus the **Rahwali relative-offset beat** ("~12 km NNW of Gujranwala" → geocode
  anchor + great-circle offset → ~2 km from the real Rahwali coord, well within RESOLVE's proximity radius;
  `resolved_place_ref` stays `None`).
- **Decisions:** see DECISIONS §6 INGEST "PDF-multimodal + geocoding follow-up" (8 build decisions incl. the
  local-normaliser rationale, the md/13 coordinate-cache refinement, the `gemini-flash-latest` fix).
- **Deps:** `pymupdf>=1.24` added to core (AGPL-3.0 — flagged for the design note `md/16`).
- **Design-doc tails to enrich:** `md/13` Stage-A/B split (add the INGEST coordinate-cache), `md/15` §4 (PDF
  path is now multimodal, not text-only), `md/16` (AGPL disclosure).
- **Follow-ups still open:** (1) re-record the frozen bundles with a keyed `make extract` now that the geocoder
  freezes anchor coords; (2) dedupe `gazetteer_key` ↔ RESOLVE `normalize` into one shared module once RESOLVE
  merges; (3) the chunk thresholds could graduate to a config section.

### SCORE (in-review, feat/score — PR #20; F0-amend PR #18):
- **Shipped:** the four scoring stages of `rebuild()` — `chanakya/credibility/**` (score_claims R×Π(integrity)×
  freshness · 3-axis independence grouping · noisy-OR + the confirmed/probable/possible/insufficient/
  contradicted/stale machine), `chanakya/sufficiency/**` (template eval → first-class Known Gap with generated
  `next_coverage_due`), `chanakya/materiality/**` (chokepoint criteria #1/#4/#6/#7/#10; UNKNOWN→candidate, never
  sole-source). **423 pass / 5 skip; ruff + mypy + gates G1–G12 green.** 43 SCORE acceptance tests.
- **F0-amendment (PR #18, `f0/score-amendments`; merge first, or SCORE carries it):** additive/optional +
  inert on the golden — `CredibilityConfig.as_of` + `chanakya/timeref.py` (clock-free eval "now"); rebuild
  rewind filter (past as_of hides not-yet-available claims); `apply_claim_exclusions` (HITL reject → drop the
  look upstream); `deception_gate_flags` + `score_claims(…, decisions)`. Also folded into SCORE's PR: pipeline
  reorder `check→assign_status` (so the status machine owns `insufficient` + enforces the sufficiency gate).
- **Decisions (principle → choice → alt rejected):** see DECISIONS.md §6 "SCORE". Headlines: freshness `as_of`
  = explicit config input (pinned / API-`now` / max-timestamp fallback), clock-free (G1/G2), past-as_of rewinds
  — *user-approved*; decoy cap is **single-pass-conditional** (a 2nd independent look resolves it — reconciles
  spine/04 "single-pass" + the INGEST inference net-effect + G7); `decay_base`/look-count/etc. are config knobs
  (G6), never code; inference claims share their premises' group (derivation ≠ corroboration).
- **HITL pickups landed (both):** analyst origin-flag penalises every claim of a `primary_origin_id` incl.
  claims ingested *after* the flag; reject-claim excludes the look so the machine re-derives confirmed→probable.
- **Fixture reconciliation (stages now compute real values):** regenerated `expected_view.json`; golden HITL
  override `probable→possible` (the machine already rates that edge probable, so the override was invisible);
  updated stub-baseline assertions in `test_stages_smoke`/`test_rebuild(meta)`/`test_lens`/G5/G8/G12 — **gate
  intents preserved (propagation, two-scores, first-class Known Gap, no-invalid-confirmed); none weakened.**
- **Follow-ups (EVAL):** re-verify reject→confirmed→probable + origin fan-out on the real corpus; confirm
  HT-233 stays candidate end-to-end. **(DATA-C):** own/tune the new `credibility.yaml` SCORE knobs. **(INGEST):**
  attribution-inference D asks answered (`tmp/conv` ACK) — grouping + single-pass decoy consume D as shaped.
- **Gate fixtures:** extended G7 (confirmed-gate property test in `tests/credibility/test_status.py`) + G8
  (materiality/sufficiency Known-Gap paths) coverage in SCORE's own tests; F0's `tests/gates/*` kept green
  (G8/G12/G5 baselines updated for real-stage output, never weakened).

## Contract amendments (SCORE, 2026-07-19)
- **F0-amend #18 (`f0/score-amendments`):** `CredibilityConfig.as_of` (master §4.4); new `chanakya/timeref.py`;
  `score_claims(resolved_claims, sources, config, decisions=None)` (master §4.3); rebuild gains a rewind filter
  + `apply_claim_exclusions` + `deception_gate_flags` populating `AssertionInput.gate_flags`. All additive/
  optional → siblings (RESOLVE/MONITOR/ASK/API) rebase with no code change; golden view byte-identical until
  the stages fill. **Pipeline reorder `check→assign_status`** rides in the SCORE PR (view/-internal; §4.3
  "illustrative" order reconciled so the confirmed gate can require sufficiency).

### RESOLVE (in-review, feat/resolve — retargeted to main after the #16 stacked-merge miss):
- **Shipped:** the real `resolve()` stage body (`chanakya/resolve/**`) — iterative relational collective ER:
  candidate-gen (blocking `type+namespace+name_token` + hard-ID + **relational-neighbour** blocking + alias)
  → **bootstrap** (shared unique-ID / alias-equiv / exact-name+namespace) → **relational fixpoint**
  (0.40 shared-neighbourhood term, iterate to no-new-auto-merge, monotone⇒terminates) → **location
  resolution** over the gazetteer (toponym/hard-ID/geodesic-proximity by precision class). Emits the
  Partition (`same_as`/`candidates`/`distinct_from`/`merge_confidence`+breakdown/`entity_canonical`).
  Modules: `rconfig` (literal-free config, G6), `normalize` (transliteration + Jaro-Winkler), `aliases`
  (derived table = seed ∪ replayed `merge_adjudication(accept)`), `entities`, `scoring`
  (attribute/relational/temporal/source_asserted + **relocation exclusion**), `cluster` (2-phase ER,
  **veto-guarded union**, flat `finalise`), `places`, `propose` (offline **raise-only** LLM proposer).
- **Acceptance criteria:** all green — FD-2000↔HQ-9/P auto-merge; FT-2000 mid-HITL-band; HQ-9/P⊥HQ-9BE
  distinct (incl. **transitively** through a bridge); fixpoint terminates; raise-only can't cross 0.85;
  alias grows from the log; Karachi-Port≠Port-Qasim (hard veto even with shared neighbourhood);
  Chaklala→pl_nurkhan earned (ICAO/proximity); Rahwali DMS≡relative. 102 tests, ruff+mypy, G1/G2/G5/G6/G10.
- **Decisions (principle → choice → alt rejected):**
  - *Precision-first + false-merge discipline* → **cluster-level cannot-link** (a union that would put a
    vetoed pair in one cluster is refused) instead of only a direct-pair veto check (which a bridge node
    bypassed); gazetteer `distinct_from` is a **hard veto computed before entity resolution**, not just an
    emitted edge (so two co-located/co-shipping ports still never fuse).
  - *Design fidelity (spine/03:37)* → `resolve()` consumes the **decision log** (F0-amendment) for the
    offline proposer's frozen `merge_proposal`s + replayed accepts; LLM is **raise-only, hard-clamped
    below auto-merge** structurally (band() can only reach HITL via the LLM, never auto).
  - *Reversible, non-destructive merges* → merges are an **overlay** (`same_as` + flat `entity_canonical`),
    never a rewrite of a claim's own `resolved_ref`; a no-merge run is byte-identical to F0's stub (G2).
  - *Relocation ≠ identity* → two entities that are co-endpoints of one supersede `edge_instance` are
    excluded from the relational term + score temporal-consistency 0 (a unit's two bases don't make the
    bases the same place) — reuses F0's supersede instance identity.
- **Deviations / F0-amendments consumed:** built on `f0/places-and-merge-edges` (PR #10) — `PlacesConfig`,
  `Partition.{candidates,merge_breakdown,entity_canonical}`, `resolve(..., decisions)`, `_assemble`
  endpoint-reconnect + resolution-edge rendering. **Rebase/retarget to `main` once #10 merges.**
- **Follow-ups:**
  - **DATA-C** (`tmp/conv/RESOLVE-config-and-oracle-observations.md`): remove FT-2000 from the
    `distinct_from` seed + confirm the corpus instantiates it; the 3 place/oracle drifts; author
    `attribute_rules` + `hard_id_fields` + `place_entity_types` config; dedup the proximity radii.
  - **INGEST contract:** state/occupancy-predicate claims (`based-at`, …) must carry a **slot-based
    `edge_instance`** (`"<predicate>:<subject>"`, object-free — as F0's golden fixture does) so RESOLVE
    detects relocations (co-targets of one instance) and SCORE's supersede fires. Single-target
    relationship claims may leave it unset (RESOLVE synthesises identity).
  - Place-based entity merge activates when INGEST freezes coords onto place-type entity attrs; the core
    `resolve_place()` matching is fully unit-tested against the gazetteer now.
- **Gate fixtures:** none weakened; added `tests/resolve/**` (incl. `test_review_regressions.py` locking
  7 defects an adversarial review pass caught). G1/G2/G5/G6/G10 re-verified green.

### API (in-review, feat/api): FastAPI layer over the merged Wave-1 modules
- **Shipped:** the single deployable app (`chanakya/api/**`, 34 API tests; whole suite **529 pass / 6
  skip**, gates G1–G12 green, ruff+mypy clean). `create_app()` (frozen sig; lazy `fastapi` so
  `import chanakya.api` stays light) → an `AppState` that seeds the live `ConfigStore` from `config/`,
  opens the evidence + decision logs, seeds evidence from committed bundles (keyless), and holds the
  rebuilt view + previous view + an accumulating alert feed. One `rebuild_and_swap()` is the single
  in-process mechanism behind hot-config / live-ingest / HITL propagation (atomic view swap, MONITOR
  fired on the delta, `fired_ts` stamped by the API — no restart, §1 inv. 3). Endpoints (master §4.8):
  `GET /health` (503→200 readiness gate, background boot in lifespan), `GET /view` (+`?subject=` lens),
  `GET /node/{id}`, `GET /evidence/{id}` (provenance drawer, claim→doc_ref), `POST /ask` (delegates to
  ASK, passes `claims={c.claim_id:c for c in store.replay()}`), `POST /ingest` (**sync def** — keyless
  bundle append + guarded keyed live lane), `POST /hitl/{merge|status|alert}` (reconstruct card → dispose
  → rebuild; effects propagate structurally, G12/G5), `POST /config/{section}` (hot-config + arm-on-save),
  and the SPA static seam (`frontend/dist/` mount w/ deep-link fallback, else placeholder).
- **Decisions (principle → choice → alt rejected):**
  - *Thin API, delegate LLM* → `/ask` + `/ingest` are the only LLM-touching endpoints and only by
    delegation; the API adds no reasoning and imports no `anthropic` at module load.
  - *AppState is the single view/alert owner* → the keyed ingest lane runs with `live_rebuild=False`; the
    API owns the one `rebuild_and_swap` (avoids a double rebuild + a view the app doesn't hold).
  - *Sync `/ingest` route* → the lane runs its own `asyncio` fan-out; an `async` route would `asyncio.run`
    from a running loop and crash. A `def` route is threadpooled by FastAPI → concurrency preserved.
  - *Honest keyless boot* → boot prefers committed bundles, else an **empty** graph the analyst populates
    via `/ingest` (never a fabricated corpus); seed is source-agnostic so SHIP's baked baseline drops in.
  - *Public-demo cost guard* → keyed live extraction is gated by `CHANAKYA_ENABLE_EXTRACTION` (default
    off); visitors land on the instant keyless bundle path (Gemini quota/rate-limit protection).
  - *Structural HITL (G5/G12)* → no endpoint sets status directly; `dispose` appends a `DecisionRecord`
    and the following `rebuild()` applies its effects. Status ladder: demote/promote step one level.
- **F0-amendments (additive/optional; logged below + in `tmp/conv/API-to-FRONTEND-contract-log.md`):**
  `ProvenanceDrawer.claims` (resolved evidence atoms → one-click-to-source) + `IngestRequest.source_type`
  (keyed lane needs the source class). Both non-breaking; frontend + siblings gain a field, no rebase.
- **Deviations / open items:** boot seeds **0 claims today** (no committed bundles yet — `make extract`
  pending, per EVAL/DATA); the hero-query acceptance is tested against the ASK hero fixture (the true
  corpus→rebuild→hero end-to-end is EVAL's remit). "`/ask` changes after a HITL demote" is demonstrated as
  `/view` propagation over HTTP (G12) + ASK determinism; the full ask-delta on the real corpus is EVAL's.
- **Follow-ups:** (SHIP) point Docker context at repo root, bake the seed + `frontend/dist`, wire `make
  run`; (DATA/EVAL) commit the extracted bundles so keyless boot yields the seeded baseline; (frontend)
  generate types from `GET /openapi.json` (the frozen contract); watch the contract-log for changes.
- **Gate fixtures:** none added/weakened (`api/` is outside the G6/G9/G10/G11 scan scope; G1 unaffected —
  no `anthropic` at import; the two amendments leave the golden view byte-identical — G2).

## Contract amendments (API, 2026-07-19)
Both additive/optional in-PR F0-amendments on `feat/api` (only the API + frontend consume these shapes;
Wave-1 siblings are unaffected → no rebase). Mirrored for the frontend in
`tmp/conv/API-to-FRONTEND-contract-log.md`.
- **`ProvenanceDrawer.claims: list[ClaimRecord] = []`** (master §4.8; product/03 C) — the drawer embeds the
  resolved evidence atoms its `clusters`/`opposing_claims` reference by id, so each claim carries its exact
  `doc_ref` (one-click-to-source). Rejected: a new lean claim projection (2nd shape) / a per-claim endpoint
  (N+1 + beyond §4.8).
- **`IngestRequest.source_type: str | None = None`** (master §4.8) — the keyed live lane needs the source's
  credibility class (`ingest_document(source_type=…)`); the keyless bundle path ignores it.
