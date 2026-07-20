# CLAUDE.md — Chanakya OSINT (Sarvam take-home)

**Read this first, every session.** It's the boot context for any agent working here: what we're
building, the one rule that never bends, where everything lives, and how to work. Everything below the
non-negotiable is a **strong default, not a law** — if the situation in front of you argues otherwise, use
judgement, do the sensible thing, and say what you did. It points at the detailed design; it does not
restate it. When a decision here and a design doc disagree, the design doc wins — and fix this file.

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

This is the **one hard rule** in this file. Everything else is a default you may exercise judgement
against — this one you may not. Don't generalise its strictness onto the rest.

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

## Operating mode — endgame (from 2026-07-20)

The system is built and running. What's left is **finishing, fixing, and making the demo hold together** —
not designing. Read every working agreement below through that lens:

- **Bias to action on anything reversible.** A local fix, a threshold nudge, a copy change, a test, a
  fallback — just do it and report it. Don't open a question for a decision you could undo in a minute.
- **Smallest change that actually fixes it.** Prefer the targeted patch over the principled refactor.
  Re-architecting something that already works, or generalising for a use case we will never build, is now
  a *cost*, not depth.
- **Working beats ideal.** A pragmatic fix that makes the thread run end-to-end beats a clean design that
  lands after the deadline. Note the shortcut in `DECISIONS.md` or the design-note disclosures and move on —
  an honest, stated limitation is completely acceptable; a broken demo is not.
- **Escalate only what's genuinely expensive to undo:** anything that could fabricate or unground an
  assessment, corrupt the frozen corpus / answer key, break the hero demo path, or burn hours to reverse.
  Everything else is yours to call.
- **Don't start new capability.** Good ideas that don't fit the remaining time go to the roadmap section of
  the design note, not into the build.

## Working agreements (for every agent)

- **Read what's load-bearing, then build.** Skim the relevant spine/C doc before touching a module so you
  don't contradict it — but don't re-read the design corpus to make a small fix. Where a doc and the running
  code now disagree, **the running code is the fact**: note the drift, don't re-litigate the design.
- **Provenance is not optional.** Every claim carries source + date; every node/edge carries
  provenance + confidence + freshness. If you genuinely can't attach it, don't invent it — flag the gap and
  let the surface say so.
- **Keep config in config; don't build new seams now.** Credibility factors, freshness half-lives,
  thresholds, observables and ontology types already live in config — keep them there and don't bury fresh
  magic numbers in code. But the extensibility work is *done*: **no new abstraction layers for hypothetical
  use cases (A/B) at this stage.** If the honest fix is a fixed value in a config file, make it one and say
  so.
- **HITL is a service any layer can call, not per-stage code.** Route ambiguous / high-stakes items
  through the one adjudication service; overrides must propagate to downstream state.
- **Keep the demo deterministic & reproducible.** The hero query must run the same every time. This one is
  still worth protecting: when a change would make the demo non-repeatable, take the deterministic option —
  only raise it if determinism costs something real.
- **Finish what's modelled; don't model more.** New entity/edge types need a live query behind them, and
  that bar is effectively closed now. Depth today means the existing provenance / credibility / HITL /
  retrieval machinery *working reliably*, not more of it.
- **Record the decisions that matter.** Log to `DECISIONS.md` when a call changes system behaviour, trades
  something away, or is a shortcut a reviewer might poke at — plus anything belonging in the design-note
  disclosures. Routine implementation choices need no ledger entry. Surface the short list at the end of
  your work rather than narrating each call as you make it.
- **Ask only when you'd want the answer before spending an hour.** If a call is reversible, local, or cheap
  to redo, make it and report it. Save the options-template question for genuinely load-bearing forks —
  something that could fabricate or unground an assessment, break the frozen data or the hero demo, or eat a
  large slice of the remaining time. "Could conceivably be suboptimal" is not a reason to stop and ask.
- **Default to *not* expanding scope.** New capability, extra observables, extra learning mechanisms, B —
  roadmap, not build. Clipping something already in flight is fine if you say so plainly and log it as a
  limitation. The only thing that isn't fine is quietly shipping less than we claim.
- **Time is the binding constraint.** Prefer changes that reduce risk between here and the demo. Coding
  agents are still cheap and parallel — judgement and QA are the scarce resources — so spend agents freely
  on *verification and fixes*, and spend the scarce attention on what actually threatens the demo.
- **Choose subagent models deliberately.** Match the model to the task's reasoning demands: assign
  **Sonnet** when the task is genuinely Sonnet-level, and assign **Opus** when it needs Opus-level
  judgement or complexity. Never assign **Fable** to a subagent. Do not treat model choice as a default;
  make an informed choice for each delegated task.
- **Frozen data stays frozen — but don't block on it.** Don't unilaterally edit the corpus or
  `answer_key.json`; write an observation MD to `tmp/conv/` for the **data agent**. Then keep moving: work
  around the issue, note the workaround, and carry on rather than stalling the thread.
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
