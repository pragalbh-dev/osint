# Spine — Overview

**What this folder is.** The *spine* is the reusable core that all three use cases (A/B/C) sit on. It's
what the brief says is actually being tested — "credibility, triage and adaptation … finding the grain in
the chaff, keeping a human analyst in the loop, sustaining that judgement." We build the spine once; each
use case is a thin analytic layer on top. Per `../md/04-claude-chat.md` (Q2), the spine is ~70% of the
graded value; the use-case layer is ~30%.

Each doc in this folder carries the same tail: **Decisions · Open questions · Research directions.**

---

## The pipeline (the abstraction contract)

```
data generation → ingest → structure (with HITL) → source credibility → alert/observable → cited multi-hop QnA
                    over a designed ontology + queryable graph + cross-source entity resolution
```

The commitment: build this abstraction cleanly the first time so extending to the next use case is fast —
each new use case should mostly be *specification* (which node/edge types, which observables, which
queries), not core rework.

## The four load-bearing ideas

Everything else hangs off these. If a design question is hard, it usually reduces to one of them.

1. **Bi-level graph** — an append-only **evidence layer** (immutable sourced claims, the audit trail) and a
   derived **knowledge layer** (the resolved entity/relationship graph). Node confidence is a *function of*
   the claims supporting it. This is what makes "one-click traceable to source" and "confirmed vs probable"
   fall out of the architecture instead of being bolted on. → `01-graph-and-ontology.md`
2. **Credibility → confirmed/probable** — a per-claim confidence built from source-class reliability +
   corroboration + integrity signals + a "too-clean" penalty, propagated to node/edge status. "Lead with
   credibility, not collection" rendered as structure. → `04-credibility.md`
3. **HITL as attention-triage with propagating overrides** — a single adjudication *service* any pipeline
   stage can call; high-confidence judgments auto-proceed, low-confidence/high-stakes ones escalate; the
   analyst's decision *mutates graph state*, not just a log. → `05-hitl-and-triage.md`
4. **Adaptation = freshness/coverage + a learning loop** — what makes this a *monitoring* system, not a
   one-shot analysis. Judgment stays honest as sources close (freshness decay, coverage gaps stated) and
   adversary methods change (deception resistance, extensibility). → `06-adaptation.md`

## The abstraction rules that keep the spine portable

These three decisions are what let "one graph, extendible subjects, C-first-without-boxing-us-in" all be
true at once (reasoning in `02-ingestion-and-unit.md`):

- **Schema-flexible store** — add node/edge types with no migration.
- **Ingestion is source-typed, never use-case-typed** — a customs doc ingests identically no matter who
  consumes it.
- **Subject = query parameter** — a subject is a saved *lens* (anchor entities + traversal/scoring
  pattern) over one graph, not its own database.

## The non-negotiable

Where evidence is absent, ambiguous, or contradictory, the system returns an explicit **"insufficient
evidence to assess"** — naming what is missing and when next coverage is due. Fabricated/hallucinated
assessments in evidence-sparse cases are disqualifying. This is operationalised by the
**evidence-requirement templates** in `04-credibility.md`.

---

## Gates (from `../md/04-claude-chat.md` Q2)

**Spine / pivot gate** (also the "can I now build a second use case" signal):
- the one worked query runs end-to-end reproducibly;
- the insufficient-evidence rule trips on a deliberately planted gap;
- every claim/node is one-click traceable to source;
- a HITL override propagates to downstream state;
- the pipeline re-points to a new subject/observable/question by editing config, not core code.

**Layer gate** (per use case): the use case's target-output fields are all present, and you can beat its
signature rebuttal. C's signature rebuttal: *"how do you know that node is real — confirmed or guessed?"*

## Build order & roadmap

- **Depth in batches.** Build the spine with 2–3 HITL control points wired deeply, get one thread running
  end-to-end, then add depth on top. Architecture supports *any* layer invoking HITL from day one (the
  service), even if only a few callers exist at first.
- **Use-case order.** C first (graph-depth; where the credibility discipline shines). Keep B as a layer
  that *consumes* C's chokepoint signals if time allows — a coherent two-step, not two disconnected demos.
- **Four-more-weeks answer** lives across the "Open questions / Research directions" tails and the
  roadmaps in `06-adaptation.md` and `../C/00-overview.md`.

## Map of this folder

| Doc | Covers |
|---|---|
| `01-graph-and-ontology.md` | one graph, bi-level model, ontology-as-designed-schema, subjects-as-lenses, extensibility |
| `02-ingestion-and-unit.md` | source-typed ingestion, unit of analysis, claim normalization, the 3 relevance layers, extendible subjects |
| `03-resolution.md` | relational/analyst-grade entity resolution, confidence bands, HITL routing, alias-table learning |
| `04-credibility.md` | credibility factors, corroboration, confirmed/probable/stale state machine, freshness half-lives, integrity/M4, evidence-sufficiency templates |
| `05-hitl-and-triage.md` | HITL control points, the adjudication service, triage routing |
| `06-adaptation.md` | learning loop, trace logging, adversary-methods (research), roadmap |
| `07-monitoring-retrieval-viz.md` | observables/tripwires, multi-hop cited QnA, visualisation |
| `08-detailed-design.md` | **PROPOSED** — concrete resolutions to every open question in 01–07 + the B-extensibility contract + schemas/formulas; pending ratification |

Use-case C specifics live in `../C/`. Real-world data scoping for C is in `../md/05-data-scoping-C.md`.
