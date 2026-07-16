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
- **Architecture: one shared spine + a thin pluggable use-case layer.** ~70% of the graded value is the
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
| `artifacts/C/00-overview.md` | C scope, chosen subject, target queries, depth ladder, gates |
| `artifacts/C/01-materiality-ontology.md` | What's *material*; C's concrete node/edge schema (HQ-9/P) |
| `artifacts/C/02-demo-thread.md` | The one end-to-end worked thread + the demo flexes |
| `artifacts/product/00-ux-brief.md` | **Product/UX brief** for the design collaborator — functional inventory (screens/panels), the trust-status visual-language problem, the hero demo flow, and open design questions. Non-technical, domain-explained |
| `DECISIONS.md` | Guiding principles, locked-decisions ledger, open decisions, gates |

## Working agreements (for every agent)

- **Read before you build.** Before implementing any module, read its spine/C doc (table above). The
  hard thinking is done there; your job is to honour it, not re-derive or contradict it.
- **Provenance is not optional.** Every claim carries source + date; every node/edge carries
  provenance + confidence + freshness. If you can't attach it, stop and flag it.
- **Config-driven, not hardcoded.** Credibility factors, freshness half-lives, thresholds, observables,
  ontology types — all configurable (Module 1 is literally "credibility based on user-defined factors").
  No magic numbers buried in code.
- **HITL is a service, not per-stage code.** Route ambiguous / high-stakes items through the one
  adjudication service; overrides must propagate to downstream state.
- **Keep the demo deterministic & reproducible.** Freeze scenarios; favour minimal, reproducible choices
  over clever ones. The live query must run the same every time. Generator stays blind to the ontology.
- **Model exactly what the target queries need, no richer** — the over-engineering trap. Every hour on
  provenance/confidence discipline beats an hour on ontology breadth.
- **Record decisions.** When you make or change a non-trivial decision, append it to `DECISIONS.md`
  (and update the relevant design doc's tail). When you *close* an open question, move it there too.
- **Don't expand scope silently.** B, extra observables, extra learning mechanisms, scale features → the
  roadmap / "four more weeks", not the demo build, unless the user says otherwise.
- **Deadline awareness.** ~4 days. Build the spine with 2–3 HITL points deep, get one thread running
  end-to-end, then add depth. Depth in batches; a working thin thread beats a broken rich one.

## Status & stack

- **Locked:** use case C (HQ-9/P), spine+layer architecture, hosted web app, hybrid data strategy. See
  `DECISIONS.md`.
- **Stack: NOT decided.** Deferred until the spine scope is finalised (`artifacts/spine/`), so tools
  follow needs. Store choice (Neo4j / KùzuDB / in-memory NetworkX), agent framework, map/geo stack, and
  frontend are open — see `DECISIONS.md` → Open decisions. Demo scale (~10–15 docs) makes almost any
  choice viable; pick for schema-flexibility, easy provenance attachment, and reproducibility, not scale.
- **Secrets** live in `.env` (LLM API keys, etc.) — never commit them; keep them out of code and logs.
- Once a stack is chosen, add build/run/test commands to this section.
