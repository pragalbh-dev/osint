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
| RESOLVE | Iterative relational entity resolution | 1 | not-started | — | F0 | — |
| SCORE | Confidence Resolver + Sufficiency/Known-Gap + materiality | 1 | not-started | — | F0 | — |
| MONITOR | Observable DSL engine | 1 | in-review | [#11](https://github.com/pragalbh-dev/osint/pull/11) | F0 | — |
| ASK | Bounded ReAct agent + citation validator | 1 | not-started | — | F0 | — |
| HITL | Adjudication service + writeback + 3 cards | 1 | not-started | — | F0 | — |
| INGEST | Source-typed LLM extraction + live-ingest + seed bundles | 1 | not-started | — | F0 (+DATA-C soft) | — |
| API | FastAPI layer | 2 | not-started | — | RESOLVE, SCORE, ASK, HITL, MONITOR, INGEST | — |
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

## Known build-time reconciliations (F0 / build must resolve — not blockers)
- **F0 location descriptor** must carry `geocode_candidates` + `proposed_alias` so INGEST can freeze
  Nominatim/LLM place proposals onto the ClaimRecord upstream of the append (INGEST flag #1). If F0's schema
  omits these, it is a one-line F0-amendment.
- **`ClaimRecord.extraction` field naming** — rename the ambiguous `version` → **`model`** (the extraction
  model id) so the frozen contract matches INGEST's `extraction.model`; final shape `{method: llm|vlm, model,
  model_conf}`. One-line F0-amendment, docs-only (backend greenfield). *(DECIDED 2026-07-18; see `md/15` §4 +
  DECISIONS §3; raised as its own F0-amendment PR.)*
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
