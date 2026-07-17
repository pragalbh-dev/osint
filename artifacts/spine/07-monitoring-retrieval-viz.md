# Spine — Monitoring, Retrieval & Visualisation

Covers the three "output-side" spine components shared by all use cases: observable tripwires, the cited
multi-hop QnA agent, and visualisation. Kept together because for C they are thinner than the
credibility/graph core, but each is a brief requirement.

---

## Decisions

### Observables / tripwires (the monitoring requirement)
An **observable** is an analyst-defined condition that fires an alert when met (e.g. a logistics surge, a
comms blackout, a sustained fuel build-up; for C, a *new induction signal* or a *new basing appearing*).
- Analyst-defined (a HITL control point, `05-hitl-and-triage.md`) **as a live DSL condition over existing
  node/edge attributes + precomputed metrics — defined in-app, armed immediately, no app restart**
  (`09-retrieval-and-tools.md`). Reviewers set their own; the locked C tripwire is just the seeded example.
- Evaluated by a **post-`rebuild()` observable evaluator**: every `make ingest` / UI ingest → `rebuild()` →
  armed observables re-checked → crossings fire. Live ingestion is always available (extraction is the
  optional front-end).
- Firing produces an alert that goes to **disposition** (real / noise / needs-more), which feeds tripwire
  tuning (`06-adaptation.md`).
- The brief asks for **at least one** working observable to demonstrate the real-time-monitoring idea —
  scope to one good one, wired end-to-end and traceable, not a suite.

### Multi-hop cited QnA (the agent)
**Detailed design — tool surface, bounded loop, citation validator, query taxonomy, hot-config — in
`09-retrieval-and-tools.md` (research basis: `../md/14-multihop-retrieval-research.md`).** In brief:
- **Decompose** a non-trivial question into sub-questions, **traverse 2–3 hops** of the graph via a bounded
  ReAct tool-calling loop, return an answer that **cites the exact source behind every claim**.
- **Separate observed activity from inferred intent** — state what is seen vs what is reasoned.
- **Insufficient-evidence fires on a planted gap** — the agent must say what's missing and when coverage
  is due rather than guess (uses the evidence-requirement templates, `04-credibility.md`).
- C's worked query (textbook multi-hop, fully auditable): *"trace this deployed battery back to its
  component supplier and name the chokepoint"* — manufacturer → import → induction → basing, cited at each
  hop. Detail in `../C/02-demo-thread.md`.

### Visualisation
- **Geospatial** — an entity/ORBAT layer on a basemap (Bhuvan/ISRO in the reference build; any tile source
  for the demo), **confidence-coded** (confirmed vs probable vs stale visually distinct).
- **Graph explorer** — nodes/edges with click-through to provenance/confidence/freshness.
- The brief requires **at least one** visualisation; C benefits from both (map for basing, graph for the
  supply chain) but one done well beats two half-done.

---

## Open questions
- *(Resolved: **which observable** → LOCKED as the HQ-9B Rawalpindi→Rahwali occupancy state-change
  (`../C/02-demo-thread.md` Q1) — but now just the seeded example; observables are user-definable live,
  `09-retrieval-and-tools.md`.)*
- *(Resolved: **agent framework** → a plain **bounded ReAct tool-calling loop**, no framework;
  `09-retrieval-and-tools.md`.)*
- *(Resolved: **map stack** → Leaflet with vendored tiles; `../md/07-stack.md`.)*
- **"Observed vs inferred" rendering** — how the answer visually separates the two. TBD (a UX call).

## Research directions
- *(Done: cited/grounded graph-RAG patterns that keep per-hop provenance intact — see
  `09-retrieval-and-tools.md` + `../md/14-multihop-retrieval-research.md`.)*
- Confidence-coded geospatial conventions used in real intel products (symbology for
  confirmed/probable/suspected) — for a credible visualisation.
