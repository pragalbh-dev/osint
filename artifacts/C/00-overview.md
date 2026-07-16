# Use Case C — Overview

**C = auditable order-of-battle + supply-chain map of one adversary military capability, from open sources
only.** The chosen graph-depth layer on top of the spine (`../spine/`). This folder holds C-specific
design; the reusable machinery lives in `../spine/`; real-world data scoping lives in
`../md/05-data-scoping-C.md`.

Each doc carries the tail: **Decisions · Open questions · Research directions.**

| Doc | Covers |
|---|---|
| `00-overview.md` (this) | scope, chosen subject, target queries, the C layer, gates |
| `01-materiality-ontology.md` | what's *material* for chokepoint/ORBAT; C's concrete node/edge schema |
| `02-demo-thread.md` | the one end-to-end worked thread + the demo flexes |

---

## Decisions

### What C is (and is not)
C is **external, adversary-capability-focused, planning-level** intelligence. You assemble a fragmented
open-source picture into one auditable ORBAT + supply chain for *one* capability, so IAF planners
understand:
- **What** they have (types, variants, units, radars, command nodes),
- **Where** it is (basing, geolocated),
- **How it's sustained** (manufacturer → import → induction → basing → spares/maintenance/training), and
- **where the dependencies and chokepoints are** — the analytic payoff.

It is **not**: counter-intelligence / domestic sleeper-cell / insider-threat (that's within-nation
security — different data, different ethics, not this brief); **not targeting-grade** (brief:
"Planning-awareness, not targeting-grade"); **not real-time tactical** (structural/longitudinal snapshot).

The military "why": an ORBAT is the *photo* (what/where now); the supply chain is the *X-ray* (can they
sustain it, regenerate losses, relocate — and what breaks it). **The chokepoint analysis is the
deliverable's teeth.**

### Chosen subject: HQ-9/P (Pakistan), enriched with China HQ-9; S-400 as design-note reference
Per the data scoping in `../md/05-data-scoping-C.md` §3. Rationale: a single bounded traceable import
(China → Pakistan) makes the full chain clean and demonstrable; **maximal entity-resolution messiness**
(HQ-9/P · HQ-9BE · FD-2000 · HT-233 · HIMADS · 红旗-9) which is C's graded marquee; English-language real
sources; freshest reporting (2025 combat use → a natural freshness demo); best social stream (satisfies
the non-text modality with real material). Enrich with China HQ-9 for the manufacturer-side ORBAT +
imagery/VLM (AMTI Woody Island). Keep S-400 as an adjacent reference to show the ontology generalises.

### Target queries (what the system must answer)
The **worked multi-hop query**: *"trace this deployed HQ-9/P battery back to its component supplier and
name the chokepoint"* — hops basing → induction → import → component/manufacturer, cited at each hop,
separating observed from inferred. Plus: *"is this holding confirmed or probable, and on what evidence?"*
and *"what do we NOT know here?"* (insufficient-evidence on a planted gap).

### The C layer & its signature rebuttal
C's ~30% layer on top of the spine is **graph depth**: the full lifecycle ontology instantiated,
resolution across ugly aliases, and epistemic honesty (provenance + confidence + freshness per node,
confirmed structurally separated from probable, gaps stated). **Signature rebuttal to beat:** *"how do you
know that node is real — confirmed or guessed?"* — deep enough when an interviewer can click anything and
get a truthful provenance/confidence/freshness answer.

### Depth ladder (the axes, from `../md/04-claude-chat.md` Q2 + our follow-ups)
1. **Ontology instantiation** — full chain traversable end-to-end (handled via the unit-of-analysis /
   materiality work, `01-materiality-ontology.md`).
2. **Resolution** — relational/analyst-grade, real alias traps handled (`../spine/03-resolution.md`).
3. **Provenance/confidence/freshness** — per-edge half-lives → confirmed/probable/stale
   (`../spine/04-credibility.md`).
4. **Insufficient-evidence** — evidence-requirement templates fire on a planted gap
   (`../spine/04-credibility.md`).
5. **Multi-hop query** — the worked trace above (`02-demo-thread.md`).
6. **Chokepoint/dependency reasoning** — falls out of graph structure (single-source in-degree,
   sole-supplier dependency), *think of it at every step* (`01-materiality-ontology.md`).
7. **M4/integrity** — geolocated photo → VLM + provenance → confirmed vs probable
   (`../spine/04-credibility.md`).

**Over-engineering trap:** model the ontology "as rich as the target queries require, no richer." Every
hour on provenance/confidence machinery beats an hour on ontology breadth.

---

## Open questions
- **Exactly how far the China-HQ-9 enrichment goes** vs staying a reference — bound it so it's depth, not
  scope-creep.
- **Which single observable** C demonstrates (see `02-demo-thread.md` / `../spine/07-...`).
- **How many nodes** make the graph legible-but-non-trivial for the demo (enough for a real 3-hop trace +
  a planted gap, not so many the map is noise).

## Research directions
- **Materiality / IAF-intel tradecraft** for SAM supply-chain chokepoint analysis (drives the ontology) —
  see `01-materiality-ontology.md`. Candidate standalone research task.
- Alias/false-merge hazards are already catalogued from live sources in `../md/05-data-scoping-C.md` §4.
