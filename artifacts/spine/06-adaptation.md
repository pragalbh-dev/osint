# Spine — Adaptation

Covers: "sustaining that judgement as sources close and adversary methods change." The fuzzy graded axis,
made concrete. Adaptation is largely **credibility and triage that update themselves over time** — it's
what makes this a *monitoring* system, not a one-shot analysis.

---

## Decisions

### Two forces the system must adapt to
1. **Sources close** — a source goes dark / restricted (customs portal stops publishing, account deleted,
   government stops disclosing). Response: **freshness decay + coverage monitoring.** Node confidence
   decays with time-since-last-corroboration (per-edge half-life, `04-credibility.md`); the system tracks
   which sources feed which nodes and, when a class goes quiet, flags the affected subgraph as *degrading
   coverage* and states "next coverage due." Already required by C's target output (as-of stamps, gaps).
2. **Adversary methods change** — new shell names/transliterations, coordinated corroboration, planted
   signals, new goods-descriptions. Response: **deception resistance + extensibility.**

### The meta-rule: degrade gracefully and visibly, never silently
A system that keeps confidently asserting a 2019 disposition as current has *failed to sustain judgement*
even though nothing crashed. When it can't see, it says so — the non-negotiable, expressed over time.

### Learning-loop mechanisms (implement one for the demo, roadmap the rest)
- **Growing alias table** — HITL merge/split decisions written back so the same case auto-resolves next
  time (`03-resolution.md`). *(Recommended demo mechanism — cheap and visible.)*
- **Credibility-weight updates / dynamic per-source rating** — a source's `track_record` factor moves
  on its confirmed/refuted history, so reliability is *earned over time*, not fixed. **Roadmap
  (four-more-weeks), but the recommended *next* extension if time allows** — the seam is already
  pre-wired: the `track_record` factor exists in the resolver rubric (`04-credibility.md`, `08` §3.4)
  at a neutral prior, and the decision log already records the confirmed/refuted history it consumes.
  So it's a bolt-on, not a rebuild. (This is also the stronger answer to "isn't your source-tiering
  just hardcoded?" — the demo shows a configurable factor rubric; this shows it learning.)
- **Tripwire-threshold tuning** — from alert dispositions (`07-monitoring-retrieval-viz.md`).
- **Resolution-threshold tuning** — from merge accept/reject rates.
- **New deception-pattern detectors** — added as checks when a pattern is discovered.
- **Schema extension** — human-gated new types/edges (`01-graph-and-ontology.md`).

### Trace logging: design the interface now, defer the tool
Every HITL decision and every LLM-stage call **emits a structured trace event** (item, context, options,
choice, outcome). For the demo, an **append-only decision log + the alias table + the credibility store**
is enough to *show the loop closing*. Tooling like **Braintrust / LangSmith is deferred** — it earns its
place later for **eval-driven regression** of the LLM stages (extraction, disambiguation, assessment) when
iterating prompts against a labelled trace set. Decision: build the emit-interface; pick the sink later.

---

## Open questions
- **Which single learning mechanism to demo** — leaning the alias table (visible, low-risk, ties merge →
  future auto-resolution in one screen).
- **How much of the loop is "online"** — demo shows the mechanism exists + one closed instance; genuine
  online learning is out of scope for a week.
- **Trace sink choice** — deferred (see above).

## Research directions
- **Adversary-methods-change / counter-deception — deserves its own deep analysis when scoping.** This is
  research-hard. Questions: what deception patterns matter for a supply-chain ORBAT (front-company
  rotation, dual-use relabelling, planted + self-referential corroboration, withheld signals); which are
  cheaply detectable now vs roadmap; how "too-clean" and independence checks are made robust rather than
  gameable. Candidate standalone research task. Cross-refs: `04-credibility.md` (too-clean, coordinated
  inauthenticity), Use Case B's threat model (`../md/04-claude-chat.md` Q4).
- Braintrust/LangSmith-style eval harnesses for LLM-stage regression — for the "four more weeks" section.

## Roadmap parking (four-more-weeks / next-if-early)
- Additional HITL control points beyond the demo's ★ three.
- More learning mechanisms wired (credibility-weight + tripwire tuning).
- The cost-only relevance prefilter + resolution blocking for scale (`02-ingestion-and-unit.md`).
- B as a reasoning layer consuming C's chokepoint signals (`00-overview.md` build order).
