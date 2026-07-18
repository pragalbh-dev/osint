# PROGRESS — Chanakya OSINT backend build

**The live board.** Any agent reads this (after `CLAUDE.md`) to know where things stand before starting.
**Each session maintains its own row + handoff note inside its PR; you review it with the diff, then merge**
(master §2 Rule 4, §9). A session touches only *its own* row/append, so PRs don't collide. Status ∈
`not-started · in-progress · in-review · merged · blocked`.

## Board

| ID | Session | Wave | Status | PR | Depends (merged) | Merged commit |
|----|---------|------|--------|----|--------------------|---------------|
| F0 | Foundation + store + rebuild skeleton + fixtures + gates + CI | 0 | not-started | — | — | — |
| X0 | Walking-skeleton deploy (EC2 + tunnel + GHCR) | 0 | merged | [#5](https://github.com/pragalbh-dev/osint/pull/5) | — | 0c364be |
| DATA-C | Corpus freeze + C config YAML | 0 | not-started | — | F0 (soft) | — |
| RESOLVE | Iterative relational entity resolution | 1 | not-started | — | F0 | — |
| SCORE | Confidence Resolver + Sufficiency/Known-Gap + materiality | 1 | not-started | — | F0 | — |
| MONITOR | Observable DSL engine | 1 | not-started | — | F0 | — |
| ASK | Bounded ReAct agent + citation validator | 1 | not-started | — | F0 | — |
| HITL | Adjudication service + writeback + 3 cards | 1 | not-started | — | F0 | — |
| INGEST | Source-typed LLM extraction + live-ingest + seed bundles | 1 | not-started | — | F0 (+DATA-C soft) | — |
| API | FastAPI layer | 2 | not-started | — | RESOLVE, SCORE, ASK, HITL, MONITOR, INGEST | — |
| EVAL | Acceptance harness (spine gate + demo flexes) | 2 | not-started | — | all Wave-1 + DATA-C + INGEST | — |
| SHIP | Production packaging & deploy | 2 | not-started | — | API (+X0, DATA-C, INGEST) | — |

## Contract amendments (F0-amendment PRs)
_Post-F0 changes to a frozen contract go here. Each entry: what changed, which contract §, which sessions must rebase._

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
