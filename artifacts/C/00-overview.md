# Use Case C — Overview

**C = auditable order-of-battle + supply-chain map of one adversary military capability, from open sources
only.** The chosen graph-depth layer on top of the spine (`../spine/`). This folder holds C-specific
design; the reusable machinery lives in `../spine/`; real-world data scoping lives in
`../md/05-data-scoping-C.md`.

Each doc carries the tail: **Decisions · Open questions · Research directions.**


| Doc                          | Covers                                                                |
| ---------------------------- | --------------------------------------------------------------------- |
| `00-overview.md` (this)      | scope, chosen subject, target queries, the C layer, gates             |
| `01-materiality-ontology.md` | what's *material* for chokepoint/ORBAT; C's concrete node/edge schema |
| `02-demo-thread.md`          | the one end-to-end worked thread + the demo flexes                    |


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

### Enrichment bound (China-HQ-9) — LOCKED (Q5)

**Bounding rule:** a China-side node/edge is in-scope **iff it lies on a directed dependency/origin path
reachable from a fielded Pakistani HQ-9/P fire-unit** (via operates/fields→supplies-component,
reloaded-from+stocks-round→resupplied-by, design-authority-for, exported-by, overhauled-at,
software-controlled-by, trained-by, located-at) **OR is a `same-as`/`distinct-from`/`analog-of` resolution
anchor** for a primary entity. Enrichment adds **depth** (deeper tiers of the same battery's chain + the
OEM/origin/sustainment termini), never **breadth** (new subjects/theatres).

- **In-scope:** CASIC 2nd Academy (`design-authority-for`), CPMIEC as export-agent (`exported-by`), the
HQ-9/P production line, and **named** tier-2/3 suppliers only when an indicator names them (seeker, GaN
T/R modules, propellant, ICs, ceramics, Taian/Wanshan chassis) — unnamed sub-tiers stay Known Gap
candidates; the fielded/depended-on Components (HT-233, Type 120/YLC-2V, TEL, CP, round); the Variants as
design/resolution anchors (HQ-9/HQ-9A/HQ-9B as the `distinct-from` counterpart, HQ-9/P, HQ-9BE, FD-2000);
the China-side sustainment termini the battery depends on (interceptor line, return-to-China depot,
Tech-Data Authority, OEM schoolhouse); Contract events China→Pakistan; **S-400 only as an `analog-of`
reference capped at probable.**
- **Out-of-scope (scope-creep guard):** China's own PLAAF/PLAN HQ-9 ORBAT/basing/units; naval HHQ-9/reef
sites; other Chinese SAM families (except as `distinct-from` anchors); Chinese IADS C2 topology
(never-observable Known Gap only); the full Russian S-400 OB beyond the analog license.
- **Residual — RESOLVED (a data question):** how aggressively to hunt/name tier-2/3 suppliers is bounded by
the generator cases in `../md/05-data-scoping-C.md` §5.1 — seed ≥1 sanctions/tender-named sub-supplier
(→ confirmed chokepoint) + the rest as candidates; use a real listing if one exists, else
synthetic-from-real (defensible).

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

- *(Resolved: deep-tier hunting depth → a data question, bounded by `../md/05-data-scoping-C.md` §5.1 and
the enrichment residual above — no longer an open design call.)*
- **How many nodes** make the graph legible-but-non-trivial for the demo — see the **demo-scope subset** in
`01-materiality-ontology.md` (enough for a real 3-hop trace + a planted gap, not so many the map is noise).
- *(Resolved: enrichment bound → locked above (Q5); the single observable → locked in `02-demo-thread.md`
(Q1); confidence/freshness values → locked in `../spine/04-credibility.md` (Q2–Q4).)*

## Research directions

- **Materiality / IAF-intel tradecraft** for SAM supply-chain chokepoint analysis (drives the ontology) —
see `01-materiality-ontology.md`. Candidate standalone research task.
- Alias/false-merge hazards are already catalogued from live sources in `../md/05-data-scoping-C.md` §4.

