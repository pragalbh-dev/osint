# Spine — Monitoring, Retrieval & Visualisation

Covers the three "output-side" spine components shared by all use cases: observable tripwires, the cited
multi-hop QnA agent, and visualisation. Kept together because for C they are thinner than the
credibility/graph core, but each is a brief requirement.

---

## Decisions

### Observables / tripwires (the monitoring requirement)
An **observable** is an analyst-defined condition that fires an alert when met (e.g. a logistics surge, a
comms blackout, a sustained fuel build-up; for C, a *new induction signal* or a *new basing appearing*).
- Analyst-defined (a HITL control point, `05-hitl-and-triage.md`).
- Firing produces an alert that goes to **disposition** (real / noise / needs-more), which feeds tripwire
  tuning (`06-adaptation.md`).
- The brief asks for **at least one** working observable to demonstrate the real-time-monitoring idea —
  scope to one good one, wired end-to-end and traceable, not a suite.

### Multi-hop cited QnA (the agent)
- **Decompose** a non-trivial question into sub-questions, **traverse 2–3 hops** of the graph, return an
  answer that **cites the exact source behind every claim**.
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
- **Which observable for C** — leaning "a new/relocated basing node crossing into 'confirmed', or a
  sustainment-tender signal implying induction." Decide in `../C/02-demo-thread.md`.
- **Agent framework** — plain tool-calling loop vs a framework; keep it deterministic enough to run the
  same every demo. TBD; favour minimal + reproducible.
- **Map stack** — tile source + geo rendering lib. Deferred (demo-feasibility choice, not a graded one).
- **"Observed vs inferred" rendering** — how the answer visually separates the two. TBD.

## Research directions
- Cited/grounded graph-RAG patterns that keep per-hop provenance intact (so every claim in the answer
  traces to a source line).
- Confidence-coded geospatial conventions used in real intel products (symbology for
  confirmed/probable/suspected) — for a credible visualisation.
