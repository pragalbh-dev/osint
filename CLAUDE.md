# CLAUDE.md — Chanakya OSINT (Sarvam take-home)

**Read this first, every session.** It's the boot context for any agent working here: what we're
building, the rules that never bend, where everything lives, and how to work. It points at the detailed
design; it does not restate it. When a decision here and a design doc disagree, the design doc wins —
and fix this file.

---

## What this is

A **working demo of an AI-based OSINT analysis & monitoring system**, built for the Sarvam AI · Chanakya
(defence / strategic-sector) **Senior Data Scientist** take-home. Built off the public IAF iDEX ADITI 4.0
Problem Statement 18, our own design. **Deliverable: a hosted, runnable web app** (not slides) + a 2–3
page design note + one worked query shown end-to-end on a call. **Due 20 Jul 2026, 12:00.** The brief and
all reasoning are in `artifacts/` (see map below).

**What is actually being graded** (internalise this — it governs every judgement call): *credibility,
triage, and adaptation* — "finding the grain in the chaff, keeping a human analyst in the loop, sustaining
that judgement as sources close and adversary methods change." **Depth over coverage.** Judgment and system
quality over any specific stack. A re-skinned commercial tool, a social-media-only monitor, or a system
that emits finished intelligence with no analyst in the loop is explicitly *not* good.

## The non-negotiable (disqualifying if broken)

Where evidence is **absent, ambiguous, or contradictory**, the system returns an explicit **"insufficient
evidence to assess"** — naming what is missing and when next coverage is due. **Fabricated or hallucinated
assessments in evidence-sparse cases are disqualifying.** This is mechanised by the evidence-requirement
templates in `artifacts/spine/04-credibility.md` — use them; never hand-wave a gap.

Corollaries every agent obeys: **every claim/node is one-click traceable to its exact source**; nothing is
asserted without provenance; "confirmed" is structurally separated from "probable"; when unsure, **escalate
to the analyst, don't guess**.

## What we're building

- **Use case: C** — an auditable **order-of-battle + supply-chain map** of one adversary air-defence
  capability, from open sources only. Primary subject **HQ-9/P (Pakistan)**, enriched with China HQ-9;
  S-400 as a design-note reference. Scope + rationale: `artifacts/C/00-overview.md`. **B (intent /
  I&W)** is a reasoning layer we *describe* plugging in, and *build only if time allows* — never at C's
  expense.
- **Architecture: one shared spine + a pluggable use-case layer.** ~70% of the graded value is the
  spine (built once); ~30% is C's layer. The pipeline contract:
  `data-gen → ingest → structure (w/ HITL) → source credibility → alert/observable → cited multi-hop QnA`,
  over a `designed ontology + queryable graph + cross-source entity resolution`.
- **Four load-bearing ideas** (if a design question is hard, it reduces to one of these):
  1. **Bi-level graph** — append-only **evidence layer** (immutable sourced claims = the audit trail) +
     derived **knowledge layer** (resolved entities/edges). Node confidence is *a function of* its claims.
     This makes traceability and confirmed-vs-probable fall out of the architecture. (`spine/01`)
  2. **Credibility → confirmed/probable** — per-claim confidence from source-class + corroboration +
     integrity + a "too-clean" penalty, propagated to node status. (`spine/04`)
  3. **HITL as attention-triage with propagating overrides** — one adjudication *service* any stage can
     call; overrides mutate graph state, not just a log. (`spine/05`)
  4. **Adaptation = freshness/coverage + a learning loop** — what makes this *monitoring*, not one-shot.
     (`spine/06`)
- **Three abstraction rules that keep the spine portable:** schema-flexible store (add types, no
  migration); **ingestion is source-typed, never use-case-typed**; **a subject is a query-time lens**
  (anchor entities + traversal/scoring pattern), not its own database. (`spine/01`, `spine/02`)
- **Unit of analysis = the sourced claim** (`Source S, dated D, asserts <subject,predicate,object>`), not
  the document, not a text chunk. The normalization into claims *is* the "right unit" work. (`spine/02`)

## Data strategy

**Hybrid, messiness sourced from reality — never "LLM, make it messy."** Take real specimens (a real
NOTAM/NAVAREA string, real ImportYeti/Zauba BoL rows, the India MTD tender skeleton) as **format +
messiness templates**; vary entities/values synthetically. Apply messiness as **enumerable corruption
operators** you can enumerate on the call, not free-form. **Keep the generator blind to the ontology**
(it emits raw text/records, never your clean fields). Freeze **multiple scenarios** and let evaluators
pick one live. Seed in a few **real, uncurated documents**. Finished SAM systems are genuinely invisible
in public customs data — so the customs file is *synthetic-from-real-template*, and that's defensible, not
a cop-out. Full real-data catalogue, alias tables, and the six graded scenarios: `artifacts/md/05-data-scoping-C.md`.

## Repo map — read the relevant doc *before* building a module

| Path | What it is |
|---|---|
| `artifacts/*.pdf`, `artifacts/chat.txt` | Original source files (untouched) |
| `artifacts/md/00-index.md` … `04-claude-chat.md` | Cleaned source material: brief, agent chats, planning notes |
| `artifacts/md/05-data-scoping-C.md` | **Real-world data catalogue for C** — sources, access, alias tables, corpus + 6 graded scenarios |
| `artifacts/md/06-preflight-audit.md` | **Pre-implementation audit** — prioritized gaps (doc↔data drift, buildability, demo/timeline risk) + the ordered "close before writing code" checklist. Read before starting the build |
| `artifacts/md/07-stack.md` | **Stack (DECIDED) + deploy plan** — one choice per layer, EC2 + Cloudflare Tunnel hosting, both reviewer-deploy paths, clean-deploy strategy, build-stage sequencing |
| `artifacts/md/14-multihop-retrieval-research.md` | **Retrieval research reference** — cited (2025–26) landscape for multi-hop KGQA + tool-calling best practices (agentic traversal vs GraphRAG/vector/Text2Cypher; embeddings; determinism); source-quality flagged |
| `artifacts/md/13-location-normalization.md` | **Location precision spec + normalization system** — per-node-type precision (fire-unit→pad … design-authority→district), the ≥2-format corpus seeding, coord-canonicaliser + place-resolution design, the place gazetteer + distinct-from traps |
| `config/places.yaml` | **Seed place gazetteer** (extensible config) — canonical place nodes + aliases + WGS84 coords (real/synthetic/approximate) + precision class; one alias withheld for the earned-merge demo |
| `artifacts/md/17-corpus-catalogue.md` | **Corpus catalogue** — per-doc walkthrough of all 51 docs (24 signal + 27 chaff): doc type, KG source/grade/bias, info, real-vs-planted (+ how), pipeline/demo value; the graph it builds; coverage of the 6 graded scenarios; honest gap list |
| `artifacts/md/16-design-note-disclosures.md` | **Design-note disclosures** — running list of honest tradeoffs/limitations to state out loud in the 2–3p design note (synthetic-data limits, relabeled imagery, candidate-chokepoint, calibration, scope); the design-note agent folds these in |
| `artifacts/md/questions.md` | Open-question scratchpad |
| `artifacts/spine/00-overview.md` | Spine map + the four load-bearing ideas + gates + build order |
| `artifacts/spine/01-graph-and-ontology.md` | One graph, bi-level model, designed-schema/discovered-instances, subjects-as-lenses |
| `artifacts/spine/02-ingestion-and-unit.md` | Source-typed ingestion, sourced-claim unit, 3 relevance layers |
| `artifacts/spine/03-resolution.md` | Relational entity resolution, confidence bands, HITL routing, alias-table learning |
| `artifacts/spine/04-credibility.md` | **Load-bearing** — credibility, corroboration, confirmed/probable/stale, freshness, insufficient-evidence templates, M4/integrity |
| `artifacts/spine/05-hitl-and-triage.md` | The adjudication service, 8 control points (★ = build deep), recall-biased triage |
| `artifacts/spine/06-adaptation.md` | Freshness/coverage decay, learning loop, trace logging, roadmap |
| `artifacts/spine/07-monitoring-retrieval-viz.md` | Observables/tripwires, cited multi-hop QnA agent, visualisation |
| `artifacts/spine/08-detailed-design.md` | **PROPOSED** detailed design — resolves all spine open questions (store, schemas, formulas, thresholds) + B-extensibility contract; pending user ratification |
| `artifacts/spine/09-retrieval-and-tools.md` | **Retrieval & tool surface (DECIDED)** — bounded ReAct multi-hop loop, ~7 `graph_*` tools, materiality precomputed in `rebuild()`, entailment citation validator, query taxonomy, hot-config / live-rebuild + user-defined observables. Research basis in `md/14` |
| `artifacts/C/00-overview.md` | C scope, chosen subject, target queries, depth ladder, gates |
| `artifacts/C/01-materiality-ontology.md` | What's *material*; C's concrete node/edge schema (HQ-9/P) |
| `artifacts/C/02-demo-thread.md` | The one end-to-end worked thread + the demo flexes |
| `artifacts/product/00-ux-brief.md` | **Product/UX brief** for the design collaborator — functional inventory (screens/panels), the trust-status visual-language problem, the hero demo flow, and open design questions. Non-technical, domain-explained |
| `DECISIONS.md` | Guiding principles, locked-decisions ledger, open decisions, gates |
| `artifacts/plan/00-master-plan.md` (+ `sessions/`, `PROGRESS.md`) | **Backend implementation plan** — 12 worktree/PR sessions (everything except frontend), the frozen inter-module contracts, the 12 executable abstraction gates, waves + conflict-free file-ownership. Read before implementing any backend module. Code lives in `backend/`. |

## Working agreements (for every agent)

- **Read before you build.** Before implementing any module, read its spine/C doc (table above). The
  hard thinking is done there; your job is to honour it, not re-derive or contradict it.
- **Provenance is not optional.** Every claim carries source + date; every node/edge carries
  provenance + confidence + freshness. If you can't attach it, stop and flag it.
- **Config-driven & extensible, not hardcoded.** Credibility factors, freshness half-lives, thresholds,
  observables, ontology types — all configurable (Module 1 is literally "credibility based on user-defined
  factors"). No magic numbers buried in code. **Architecture explicitly includes a configuration /
  framework layer for decision-making and HITL at *any* spine layer that needs it** — the ontology is
  extensible, and so are the (ACH-style) reasoning frameworks, the credibility rubric, and observables. If
  something you build could extend to another use case (A/B), build it as an extensible seam rather than
  hardcoding it to C — **but confirm that extensibility choice with the user first (options template)**;
  build the seam, not the other use cases' content.
- **HITL is a service any layer can call, not per-stage code.** Route ambiguous / high-stakes items
  through the one adjudication service — invocable at any spine layer that needs it; overrides must
  propagate to downstream state.
- **Keep the demo deterministic & reproducible.** Freeze scenarios; the live query must run the same every
  time; the generator stays blind to the ontology. When a choice trades reproducibility against a richer or
  cleverer approach, **ask the user** — don't silently default to the minimal option.
- **Model the ontology to what the target queries need — don't invent entity/edge types with no query
  behind them.** But build what you *do* model *fully*: depth on provenance, credibility, HITL, and the
  retrieval agent is the point, not a cost. Richer *machinery* (more robust, more auditable, more
  production-grade) is good; richer *taxonomy-for-its-own-sake* is the trap. When in doubt, build the
  capability well rather than clipping it.
- **Record & surface decisions.** As you work, **note every decision that leans on a guiding principle**
  (`DECISIONS.md` §1) — the choice, the principle it invoked, the alternative rejected. **Surface that
  list at the end of the work**, don't only bury it in a commit: append it to `DECISIONS.md` and flag
  which design-doc tails should be enriched with it. When you *close* an open question, move it there too.
- **Borderline-harmful → ask first, with options.** If a decision could be harmful to *any* aspect
  (correctness, credibility, demo-reliability, scope, timeline, reproducibility, extensibility), do **not**
  decide it yourself — put it to the user as an **options template** (concrete choices + tradeoffs, e.g.
  via the question tool), never a bare open question. Reserve unilateral calls for the clearly-safe.
- **Don't expand scope silently — but don't silently clip it either.** When the build needs more than the
  current scope (B, extra observables, extra learning mechanisms, scale features), don't just defer it to
  the roadmap and don't just build it — **surface it and get the user's permission** (options template)
  before expanding. Expansion is the user's call, not a silent yes or a silent no.
- **Deadline awareness.** ~4 days. Build the spine with 2–3 HITL points deep, get one thread running
  end-to-end, then add depth. Depth in batches; a working thin thread beats a broken rich one. **But note
  the bottleneck:** we run **multiple coding agents in parallel, so writing code is *not* the scarce
  resource** — brainstorming, design judgement, and QA are. Spend the scarce thinking time there; don't
  ration *capability* as if one dev were typing it all. And remember this is an **assignment: push as far
  toward a real, production-grade system as the time allows** — the brief itself calls for that, not a toy
  demo.
- **Choose subagent models deliberately.** Match the model to the task's reasoning demands: assign
  **Sonnet** when the task is genuinely Sonnet-level, and assign **Opus** when it needs Opus-level
  judgement or complexity. Never assign **Fable** to a subagent. Do not treat model choice as a default;
  make an informed choice for each delegated task.
- **Data issues → `tmp/conv/`, don't self-fix.** When any agent hits a corpus / `answer_key.json` / data-model
  issue it shouldn't fix itself, write an observation MD to `tmp/conv/` for the **data agent** to resolve —
  don't edit the frozen corpus or answer_key unilaterally.
- **Keep the orchestrator's context lean — delegate.** Push heavy reading, searching, and multi-file
  investigation into **subagents** and read back only their *conclusions*, not the raw files — this is how the
  driving agent stays fast and focused, not merely how work parallelises. **Size each subagent to the smallest
  model that suffices** for its task (a doc-read, a lookup, or a mechanical rendering rarely needs the biggest
  model); reserve the large models — and your own scarce context — for the judgement that genuinely demands
  them. Effective delegation to right-sized models is a context-management tool, not just a speed one.
- **Talk to the user (the orchestrator) in plain, intuitive language — never dump code/schema at them.** The
  user directs the work and reasons about it conceptually; they are *not* reading the source. In any message
  to the user, explain the *why*, the tradeoff, and the *so-what* using concepts and analogies — not verbatim
  code, schema/field lists, YAML, or `file:line` dumps. When a mechanism matters, describe what it does, not
  how it's spelled. Raw code, schemas, and precise citations belong in the files, the design docs, and the
  handoff notes for other agents — translate them out of the chat. (Depth is still expected; keep it in the
  artifacts, keep the conversation human.)
- **Commits: no AI co-author.** Do **not** add a `Co-Authored-By: Claude …` trailer (or any AI/assistant
  co-author / "Generated with" line) to commit messages or PR bodies. Author commits as the human committer only.

## Status & stack

- **Locked:** use case C (HQ-9/P), spine+layer architecture, hosted web app, hybrid data strategy. See
  `DECISIONS.md`.
- **Stack: DECIDED (2026-07-17)** — full detail in `artifacts/md/07-stack.md`; retrieval/agent design in
  `artifacts/spine/09-retrieval-and-tools.md`; ledger in `DECISIONS.md` → "Stack & retrieval". One line:
  **SQLite append-only logs + NetworkX rebuilt view** (KùzuDB-behind-the-view = scale path) · **LLM-only
  extraction, live at ingest** (seeded baseline for keyless boot; Gemini optional) · **no runtime
  embeddings** (alias + BM25 + fuzzy) · **bounded ReAct tool-calling agent** (~7 `graph_*` tools, materiality
  precomputed in `rebuild()`, entailment citation validator; no `temperature` — 400 on Opus 4.8) · FastAPI
  serving JSON + the built SPA same-origin · React/Vite + Tailwind/shadcn · Cytoscape.js · Leaflet vendored
  tiles · one multi-stage Docker image · **hosted on one always-on EC2 + Cloudflare Tunnel** · reviewers run
  it **both** ways (prebuilt GHCR image + `git clone && make run`).
- **Hot-config rule:** nothing a user does in-app (define an observable, edit credibility weights/thresholds,
  extend the ontology, ingest a doc) requires an app restart — `rebuild()` is a live in-process op reading a
  live config store. Ingestion is always available; extraction is the optional (keyed) front-end.
- **Secrets** live in `.env` (`ANTHROPIC_API_KEY`, optional `GEMINI_API_KEY`) — never commit them; keep them
  out of code and logs.
- **Planned CLI (add real build/run/test commands here once built):** `make extract` · `make build`
  (rebuild the view) · `make ingest DOC=…` · `make ask Q="…"` · `make run` (docker build + serve). Nothing
  is built yet — this section becomes the command reference at Stage 1.
