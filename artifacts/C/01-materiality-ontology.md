# Use Case C — Materiality & Ontology

Covers: what counts as *material* to capture (the defensible answer to "right unit of analysis" for C),
and C's concrete node/edge schema instantiated for the HQ-9/P subject. This is the front-loaded *design*
work that is graded and that coding agents can't do for you.

---

## Decisions

### Materiality is derived backward from the target queries + doctrine
"Capture any entity material for chokepoint detection." Material = *anything on a path the target queries
must traverse, or that constrains sustainment/regeneration.* Deriving this defensibly is the graded work;
the defense is *"I modeled exactly what the chokepoint/ORBAT questions require, no more"* (avoids the
over-engineering trap). This requires a short research pass on tradecraft (below) so it's defensible, not
guessed. It is one of the axes of depth (`00-overview.md`).

### Node types (the lifecycle)
Designed schema (not LLM-discovered; see `../spine/01-graph-and-ontology.md`):
- **Manufacturer / design bureau** — e.g. CASIC / CPMIEC (HQ-9); Almaz-Antey (S-400 ref).
- **Component / subsystem** — e.g. HT-233 engagement radar, TEL/launcher, missile rounds, command post.
- **Variant** — HQ-9/P (Army, ~125 km) vs HQ-9BE (PAF, 260–280 km); export designation FD-2000.
- **Contract / import event** — the transfer/procurement record (SIPRI transfer row; synthetic-from-real
  customs/tender).
- **Unit / formation** — the operating unit (e.g. Army Air Defence Centre Karachi).
- **Basing site** — geolocated deployment location.
- **Sustenance node** — spares / maintenance depot / training facility.
- **Radar / command node** — treated as component or standalone per query need (note the radar↔system
  conflation trap, HT-233 vs FD-2000).

### Edge types
`manufactures` · `supplies-component` · `variant-of` · `imported-by` (contract→recipient) ·
`inducted-into` (system→unit) · `based-at` (unit→site) · `sustained-by` (unit/system→sustenance node) ·
`commanded-by`. Each edge carries provenance + confidence + freshness and a **freshness half-life by type**
(`../spine/04-credibility.md`): durable (`manufactures`, `variant-of`, `supplies-component`) vs perishable
(`based-at`, `inducted-into`, unit readiness).

### Chokepoint / dependency reasoning falls out of structure
A chokepoint is a **structural property**, not a hardcoded label: a node with **single-source in-degree**
on a critical path, or a **sole supplier** for a component the whole capability needs. "Think of it at
every step" means: while designing each type/edge, ask *"does this let the graph reveal a dependency or
chokepoint?"* — if not, it may not be material.

### Confirmed vs probable, instantiated
E.g. a **tender for "spares"** implies an inducted system → **probable**, never confirmed. Satellite
imagery of launchers at a geolocated site **confirms** basing (promotes probable→confirmed). The
acquisition trail (customs/tender) and the deployment evidence (imagery) are the two ends of the same
chain; the multi-hop query links them.

---

## Open questions
- **Radar/command modelling** — separate node type vs component subtype? Decide by whether a query needs
  to reason about the radar independently (leaning: component with a `radar` role flag).
- **Granularity of "component"** — subsystem level (radar, TEL, missile) is likely the right stopping
  point for chokepoint questions; going to piece-part level is over-engineering unless a query needs it.
- **How to represent variant forks from one import** — one PK import → HQ-9/P (Army) + HQ-9BE (PAF): model
  as two `variant-of` children of one import event? (yes, leaning).
- **Exact half-life defaults** per edge type (shared open item with `../spine/04-credibility.md`).

## Research directions
- **★ Materiality / tradecraft research task** — what an IAF/air-defence intelligence analyst treats as
  material for a SAM supply-chain + chokepoint assessment: what disambiguates units/formations, what
  sustainment dependencies matter (spares lead-times, radar/missile production bottlenecks, training
  pipeline), what makes something a genuine chokepoint vs a nominal supplier. Output feeds this schema and
  the resolution relational signals (`../spine/03-resolution.md`). *Candidate to run as a research
  subagent.*
- Real designator/variant/alias structure for HQ-9 family + S-400 is already catalogued from live sources
  in `../md/05-data-scoping-C.md` §4 (use as the resolution/alias ground truth).
