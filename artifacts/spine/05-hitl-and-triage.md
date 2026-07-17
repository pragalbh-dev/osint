# Spine — HITL & Triage

Covers: what the human-in-the-loop control points are, how HITL is built so *any* stage can invoke it, and
how triage decides what escalates vs auto-proceeds.

---

## Decisions

### HITL is a cross-cutting service, not per-stage code
A single **adjudication service** any pipeline stage can call:
`enqueue(item, context, options, writeback_callback)` → a review queue the analyst works → the choice
fires `writeback` that **mutates graph state** *and* **emits a trace event** (`06-adaptation.md`). Build it
once; wiring a new HITL point is then a few lines. This is what makes "any layer in the spine that needs
HITL can go for it" true from day one, even if only 2–3 callers exist at first.

### The principle: system proposes, analyst disposes; escalate the ambiguous
High-confidence judgments **auto-proceed**; low-confidence / high-stakes junctions **escalate to the
human**. HITL *is* triage applied to the analyst's scarce attention — don't waste them on the easy 90%,
escalate the ambiguous 10%. (The tool is "one of the inputs to the overall Intelligence architecture" —
decision-support, not autonomous.)

### Overrides must propagate, not just log
The difference between real HITL and a decorative "analyst approved" line: an override changes downstream
state. Demo target — analyst rejects a claim → node drops confirmed→probable → the multi-hop query answer
changes.

### The control points (full set)
Build 2–3 deeply for the demo; the rest are the *same service* with different payloads.
1. **Credibility configuration** — analyst sets credibility factors/weights (Module 1). Before data flows.
2. **Merge adjudication** ★ *(C marquee)* — sub-threshold merges: accept / reject / split.
3. **Ontology extension** — new type/edge proposals: add / map-to-existing / discard.
4. **Confirmed↔probable override** ★ — promote/demote or reject a claim; propagates.
5. **Observable definition** — analyst defines tripwire conditions.
6. **Alert disposition** ★ — fired tripwire: real / noise / needs-more; feeds tuning.
7. **Assessment review** — final cited assessment accepted/annotated before it becomes "intelligence."
8. **Integrity flags** — M4 signal fired: decide whether to discount. Two callers of the same adjudication
   service: **system-triggered** (a structural deception detector fires) and **analyst-initiated** (an
   analyst spots a fake post on their own and flags it — today's HITL is system-triggered only, so this is
   a new entry point, not a new mechanism). Either caller enqueues the same item shape; the writeback is
   identical. Because dedup groups claims by `primary_origin_id`, flagging a source/origin as fake
   propagates automatically to every co-referring claim on that origin the next `rebuild()` — no per-claim
   fan-out logic needed.

★ = the three recommended for deep demo build (merge, override, alert disposition).

### Triage routing — recall-biased
Triage is a configurable routing function deciding escalate-vs-auto-proceed. Inputs: **confidence band**,
**materiality** (does it touch a chokepoint?), **novelty** (unseen entity/alias?). Principle — *efficiency
without loss of intelligence*: tune the **precision** of what auto-proceeds; hold the **recall of
escalation near 1.0** (when in doubt, escalate rather than drop). "Grain in the chaff" at the workflow
level: protect the scarce analyst while never silently discarding a possible signal.

**LLM is raise-only inside triage — it ranks, it never removes.** The escalate-vs-auto boundary is a
deterministic gate (confidence band + materiality + novelty); recall≈1.0 lives *there*, not in the LLM. On
top of that gate, a **config-versioned NL triage rubric** is what the LLM *applies* to items already raised
into the review queue, to **rank** them (which of the escalated items an analyst should look at first) —
it may never pull an item back out of review, and it may never move the escalate-vs-auto boundary itself.
Ranking runs once, offline, against the frozen rubric version and is **replayed**, not recomputed live, so
the queue order is reproducible run to run. Caveat for the demo: under finite analyst capacity, ranking can
still effectively bury a low-ranked-but-real item if the queue is long — so the ★ marquee control points are
**deterministically pinned** to the top of the review queue regardless of LLM rank, rather than trusting
rank alone to surface them.

---

## Open questions
- **UI surface for the demo** — a real review-queue view vs a scripted "analyst acts here" step. Leaning a
  minimal real queue for the ★ points so propagation is visibly demonstrable.
- **Trace schema** — the exact structured event emitted per decision (shared with `06-adaptation.md`).
- **Batching** — do similar low-confidence items get grouped for one analyst pass? (efficiency). TBD.

## Research directions
- HITL patterns for knowledge-graph curation / active-learning-style prioritisation of what to review
  first (maximise intelligence gained per analyst-minute).
- "Finding the grain in the chaff" is realised across *relevance* (`02-ingestion-and-unit.md`),
  *credibility* (`04-credibility.md`), *this triage*, retrieval, and alerting — write it up as a
  cross-cutting property in the design note, not one component.
