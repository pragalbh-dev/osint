# Use Case C — Demo Thread & Flexes

Covers: the one thread shown end-to-end (source → credibility → triage → analyst → geo-tagged output), and
the specific "moments" that prove the graded qualities. The corpus and the six graded scenarios that seed
these moments are specified in `../md/05-data-scoping-C.md` §5; this doc is how they're *staged* in a run.

---

## Decisions

### The one thread (brief: "show one thread end-to-end")
`source → credibility → triage → analyst → geo-tagged output`, driven by the worked multi-hop query:
**"trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint."**
Hops: `based-at` (site, confirmed by imagery) → `inducted-into` (unit) → `imported-by` (transfer/contract)
→ `supplies-component` / `manufactures` (radar/missile supplier) → chokepoint (structural dependency).
Every hop cited to its exact source; observed activity separated from inferred.

### The demo flexes (each maps to a graded quality and a planted scenario)
Scenario numbers refer to `../md/05-data-scoping-C.md` §5.

1. **Confirmed vs probable, on click** — the tender-implies-induction node shows as *probable*; the
   imagery-confirmed basing shows as *confirmed*. Proves epistemic honesty. *(Scenario 1 corroborated;
   Scenario 2 single-source.)*
2. **Insufficient-evidence on a planted gap** — cloud-covered/stale satellite frame over a site a social
   post claims is active → agent returns "insufficient evidence, missing overhead confirmation, next
   coverage due …" instead of guessing. Proves the non-negotiable. *(Scenario 5.)*
3. **M4 override — fabricated-but-corroborated caught** — a recycled/miscaptioned parade image reposted as
   "new deployment," with two "independent" reshares; the provenance/first-seen (or VLM) integrity signal
   overrides the corroboration count → node does **not** become confirmed. The single most memorable
   moment. *(Scenario 4.)*
4. **HITL merge adjudication + propagation** — the **FD-2000 ≠ FT-2000** false-merge (or
   HQ-9/P↔HQ-9BE↔FD-2000 ambiguity) surfaces at the confidence threshold; analyst accept/reject writes
   back, grows the alias table, and the downstream query answer changes. Proves real (propagating) HITL +
   the learning loop. *(Scenario 6.)*
5. **Freshness / stale** — a node confirmed from 2019/2016 imagery with no recent source shows as
   *confirmed-as-of-DATE / coverage-lapsed → probable (stale)*; a query flags degraded coverage. Proves
   adaptation to sources closing.
6. **The observable — LOCKED (Q1): a basing/occupancy STATE-CHANGE tripwire on the perishable `based-at`
   edge**, scoped to the documented **HQ-9B Rawalpindi→Rahwali (2025) relocation** for one named fire-unit.
   The full monitoring+credibility loop on the frozen corpus: (a) 2021 imagery = occupied@Rawalpindi
   (garrison half-life); (b) a single 2025 pass = occupied@Rahwali resolves only to **probable** because
   `decoy_risk_flag` caps a single-pass signature match; (c) a second discipline-independent + cross-interest
   origin (repeat pass OR ELINT emitter-active OR a non-aligned statement) with a clean decoy check lifts it
   to **confirmed**; (d) `supersedes` — matched on resolved unit×site instance, not designator — retires the
   stale Rawalpindi position, whose `based-at` auto-degrades to **stale** under the field/garrison half-life.
   Proves perishable-freshness decay + the decoy→probable cap + the ≥2-independent confirmed gate +
   supersedes-vs-contradicts, all at once. *(Secondary observables, probable-only paths: a follow-on
   interceptor order via `replenishes` confirming continued resupply dependence; a spares tender →
   "probable induction" showing the criterion-7 confidence ceiling.)*

### Visualisation for the thread
A **confidence-coded geospatial layer** (basing sites, confirmed/probable/stale visually distinct) plus a
**graph explorer** for the supply chain with click-through to provenance. One done well beats two
half-done (`../spine/07-monitoring-retrieval-viz.md`).

---

## Decisions (locked this session)
- **Query start node: the Karachi HQ-9/P battery** (Army Air Defence Centre, Karachi; ISPR induction
  14 Oct 2021) — the clean, well-sourced anchor for the flagship trace. *To be verified against the
  generated corpus.*
- **Demo run: several tested queries + bounded live headroom.** One primary scripted+tested worked query,
  a few more tested queries, plus headroom for a live free-form follow-up. **Discipline:** the graded
  moments (chokepoint trace, confirmed/probable, insufficient-evidence, M4 override) always run on *tested*
  queries; the live follow-up is a bonus, never load-bearing. This is safe because **graph traversal is
  deterministic** — only the LLM's question-decomposition/phrasing varies — so tested queries reproduce and
  a live one "mostly works."
- **Sustainment: build BOTH** Interceptor Stockpile & Resupply *and* Tech-Data / Software & Calibration
  Authority (data for both, per `../md/05-data-scoping-C.md` §5.1) — so both secondary observables are
  available (follow-on-order resupply signal; OEM firmware/localization dependency).

## Open questions
- **Store choice** — deferred by decision (decide later; shared with `../spine/01`).

## Research directions
- None new here — this doc consumes the spine + `01-materiality-ontology.md` + the data scoping. Revisit
  once the corpus is built to confirm each scenario has real seed material (`../md/05-data-scoping-C.md`
  §5 already maps scenario → source).
