# PROGRESS — Chanakya OSINT backend build

**The live board.** Any agent reads this (after `CLAUDE.md`) to know where things stand before starting.
**Maintained by the user at merge time — never edited inside a PR** (so it can't conflict). See
`00-master-plan.md` §2, §9. Status ∈ `not-started · in-progress · in-review · merged · blocked`.

## Board

| ID | Session | Wave | Status | PR | Depends (merged) | Merged commit |
|----|---------|------|--------|----|--------------------|---------------|
| F0 | Foundation + store + rebuild skeleton + fixtures + gates + CI | 0 | not-started | — | — | — |
| X0 | Walking-skeleton deploy (EC2 + tunnel + GHCR) | 0 | not-started | — | — | — |
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
- **Hero-trace edge names** (`ASK`/`EVAL`) — `…imported-by → exported-by → supplies-component` must be
  reconciled against DATA-C's `ontology.yaml` + `answer_key.json`, which are authoritative for exact edge
  names (`C/02` notes the anchor is "to be verified against the generated corpus"). Resolve at DATA-C author
  time; ASK/EVAL bind to whatever the answer_key uses.
- **`make extract`** is SHIP's Makefile target; INGEST ships only the CLI entrypoint it invokes (INGEST flag #2).

## Handoff notes
_Appended at merge. Each entry: what shipped · decisions (principle→choice→alternative) · deviations from
plan · follow-ups · any gate fixtures added/extended._

### F0 (merged <commit>):
