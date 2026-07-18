# Use Case C — Materiality & Ontology

What counts as *material* to capture (the defensible "right unit of analysis" for C) and C's concrete
node/edge schema for the HQ-9/P subject. **This is now research-backed** — derived from a workflow that
ran parallel tradecraft research (SAM ORBAT, sustainment/chokepoint, OSINT observability), synthesized a
spec, and hardened it through two adversarial critique+repair rounds (verdict: "structurally strong and
unusually honest… defensible as a collection-driver"). Sources at the bottom.

> **Read `../spine/04-credibility.md` alongside this** — the Confidence Resolver, evidence layer, and
> confirmed/probable machinery referenced throughout live there. This doc is the *ontology*; that doc is
> the *scoring*.

---

## Materiality principle (the defensible one-liner)

**Model only what is needed to answer C's three target queries** — (1) trace a deployed fire-unit through
its component *and* interceptor supplier to the **origin/OEM** node and read the structural chokepoint;
(2) state whether each assertion is **confirmed or probable** as a value *computed* by an explicit,
versioned, auditable resolver (reliability × credibility × origin-/discipline-/interest-independent
corroboration × artifact-integrity × freshness); (3) **expose what is unobservable**. So every entity
either lies on a battery→origin ORBAT/sustainment path, carries the provenance/confidence/freshness that
grades that path, or is an explicit first-class **Known Gap**. Ignorance is never printed as a dependency
*or* as an entity. Graph topology only *nominates* chokepoint candidates; substitutability state +
foreign-control + resolver confidence *confirm*. **The flagship deliverable is honestly framed as
prioritized collection tasking, not a claimed-complete single-point-of-failure map.**

**On "fire-unit" as the anchor:** the deployed **battery/fire-unit is the query *entry point*** (what you
actually observe in the field), **not** the scope. The trace fans out from it through *every* component it
fields (radar-by-role, launcher, missile round, command post) to their suppliers and up to origin; the
graph holds the **whole ORBAT** — all units + all components — not one battery.

Deliberately excluded (scope guard): the operational engagement/cueing layer, IADS C2 / data-link
topology (kept only as a never-observable Known Gap; `commanded-by` dropped), naval HHQ-9 / other-theatre
variants, and targeting-grade detail.

---

## Node types (14 — held at the draft count)

Freshness class in brackets drives decay (`../spine/04-credibility.md`). Knowledge-layer unless marked
EVIDENCE / CONFIG.

**Supply-chain / origin**
- **Manufacturer / design bureau** `[durable]` — prime, design bureau, production plant, export agent, or
  sub-tier supplier. The origin/OEM-leverage terminus, reachable *by edge* (`design-authority-for`,
  `exported-by`), not by string. Attrs: role, tier, `foreign_control` (resolver-gated; UNKNOWN→candidate
  +Known Gap, never default-to-OEM), named_examples (CASIC 2nd Academy; CPMIEC as export-agent),
  production_rate (evidence-graded range), confidence, provenance, freshness. *Architecture-inferred but
  unnamed sub-tier suppliers stay Known Gap candidates until a naming indicator promotes them.*
- **Component / subsystem** `[durable]` — radar (keyed by **functional_role**), launcher/TEL, command
  post, missile round, support vehicle. Attrs: component_class, `functional_role`
  (acquisition/early-warning | battle-management/surveillance | engagement/fire-control), model_designation
  (HT-233, Type 120, Type 305A/B, YLC-2V; 91N6E, 92N6, 96L6, 55K6E, 5P85), radar_band, host_chassis
  (string, *promotable* to its own support-vehicle Component when a single-vendor chassis sits on a
  critical path), observable_fingerprint, foreign_control (gated), confidence, provenance, freshness.
  *`functional_role` is the analytic pivot: an engagement radar upgrades a site to a live fire unit and is
  the SEAD aimpoint / intra-unit chokepoint.* A Component may be **composed of sub-components**
  (`component-of`) so BOM depth (radar → T/R module → GaN die → foundry) is traversable for deep-tier
  chokepoints; sub-component instances are mostly Known-Gap candidates in OSINT.
- **Variant** `[durable]` — a model/config carrying its bound interceptor set + radar config. Attrs:
  family (HQ-9 | S-400), base_designator, export_designator (HQ-9/P, HQ-9BE, FD-2000), aliases,
  range_class, associated rounds/radars. *Flagship resolution case: **HQ-9/P (~125 km) vs HQ-9B/HQ-9BE
  (~250–300 km)** — same family, same maker, routinely conflated across the exact source base; held apart
  by an explicit `distinct-from`. FD-2000 (HQ-9 marketing name) vs FT-2000 (a **distinct** anti-radiation
  family) is the easy secondary case; FT-2000 stays out of the HQ-9 export list.*
- **Contract / Import & Support event** `[durable]` — an acquisition/delivery event at formation-set
  granularity, with a support-contract subtype (spares, FSR, follow-on interceptor buys). Edge-connected to
  the recipient (`imported-by`) AND origin (`exported-by`) AND resupply layer (`replenishes`). Attrs:
  event_subtype (initial-import | follow-on-order | spares/FSR), quantities as **evidence-graded ranges**,
  `count_state` (ordered vs delivered — kept separate; SIPRI counts deliveries), variant_delivered,
  linked_unit. *A follow-on/spares event is the single strongest observable evidence of ongoing resupply
  dependence.*

**ORBAT / basing**
- **Unit / Formation** `[durable]` — ONE **recursive** type by echelon: brigade/regiment → battalion
  (divizion/ying) → **battery/fire-unit** (the atomic node owning equipment + occupying ground). Attrs:
  echelon, **designator (multi-valued: official designation + cover-designator/MUCD + bort/vehicle numbers
  + analyst-label)**, **service_branch** (Pakistan Army vs PAF — disambiguates the two HQ-9 lineages),
  parent_unit, equipment_fingerprint (counts as ranges; `count_state`: fielded vs nominal vs
  **combat-ready**), home_garrison, confidence, provenance, freshness. *Readiness has a structural home;
  true serviceability is never-observable → Known Gap, so a fielded count can't stand in for combat-ready.
  Units are aliased (incl. **adversarial cover designators**) and re-designated / re-subordinated /
  re-equipped over time — resolved with the same `same-as`/`distinct-from` machinery as systems; temporal
  changes (relocation, re-subordination, re-equip) via `supersedes`.*
- **Basing site** `[durable geometry / perishable occupancy]` — a location a unit occupies OR a sustainment
  facility sits at, modeled *separately from the occupant* so it's the shared join node for co-location.
  Attrs: coordinates, site_type (garrison | field/dispersal | training | depot/stockpile),
  site_signature_geometry (HQ-9 rectangular TEL-pad ring + central engagement-radar berm + perimeter road +
  outer EW berm; vs S-300P petal pads), occupancy_state, occupancy_observed_date, **decoy_risk_flag** (a
  single-pass signature match with decoy risk cannot alone confirm a live battery), confidence.

**Sustainment** (the supply-chain depth that answers "can they sustain / regenerate it")
- **Interceptor Stockpile & Resupply** `[perishable]` — interceptor inventory as a regeneration resource,
  bound to its round and its resupply source. Attrs: stocked_round, magazine_depth (range; usually
  never-observable → Known Gap), consumption_rate, days_of_supply, shelf_life/recert, resupply_lead_time,
  production_sole_source_flag, foreign_control (gated).
- **Maintenance / Depot Echelon** `[durable / force-revalidated]` — maintenance capability by echelon
  (field → intermediate → depot/overhaul & recert), incl. test & calibration (folded in as a capability,
  not a node). Attrs: echelon_level, capabilities, throughput, foreign_control, `dependency_dissolution_
  watch` (local-depot-standup/localization indicators force revalidation).
- **Technical-Data / Software & Calibration Authority** `[durable / force-revalidated]` — holder of TDPs,
  firmware/software update authority, crypto/mission-data keys, calibration reference. A
  *structurally-assertable* retained dependency: absent evidence of transfer, OEM is assessed to retain
  authority. *The highest-leverage, most invisible lever hardware possession hides.*
- **Training Establishment / Pipeline** `[durable / force-revalidated]` — regenerates trained people
  (crews vs technicians/instructors). Attrs: audience, throughput, in_country_vs_OEM, foreign_control.

**Evidence layer & config**
- **Source** `[n/a]` EVIDENCE — the open-source instrument/publisher. Attrs: source_type,
  primary_origin_id (circular-reporting detection), `aggregator_of` (an aggregator *inherits* its upstream
  origins — SIPRI + the press it compiles are **not** two independent origins), `bias_vector`
  (operator-state | exporter-state | third-party | commercial | adversary — two aligned sources, e.g.
  ISPR + Chinese state media, are **not** cross-interest corroboration), coordinated_inauthenticity_flag,
  `adversary_denial_flag` (an adversary asserting a fake second-source / denying a dependency is
  *discounted*, not taken at face value), reliability_grade (STANAG A–F), citation_URL.
- **Indicator** `[n/a]` EVIDENCE — an atomic sourced observation; the append-only unit strength/freshness
  compute on. Attrs: indicator_class, lifecycle_stage, observation_date, **valid_time** (real-world time
  the obs is about — powers supersedes vs contradicts), **resolved_entity_ref + edge_instance_ref** (match
  supersedes/contradicts on resolved identity + edge instance, never a designator string),
  artifact_integrity, first_seen (local PDQ hash-index — catches recycled photo; reverse-image = roadmap
  enrichment), caption_vs_image_consistency,
  evidentiary_strength (COMPUTED), freshness_class.
- **Confidence Resolver & Evidence-Requirement Template** `[n/a]` CONFIG (versioned; a function assertions
  *reference*, not an OB entity) — the transparent scoring function + thresholds that COMPUTE
  confirmed/probable/insufficient, plus per-assertion evidence templates that GENERATE the
  "what's-missing / next-coverage-due" statement. Full form in `../spine/04-credibility.md`.
- **Known Gap / Collection Requirement** `[n/a]` — FIRST-CLASS gap object so "what do we NOT know?" reads
  off nodes, not footnotes. **A Known Gap is a *known unknown*:** we know a dependency/entity *exists
  structurally* (a radar must have T/R modules → a supplier) but not its *identity* — recording that,
  instead of inventing a fake node or silently ending the chain at the prime, is the point; a naming
  indicator later *promotes* it to a real node. Homes never-observable facts (magazine depth, contract terms, C2 topology,
  true readiness), architecture-inferred-unnamed entities, and unfilled evidence-template slots. Carries
  `observability_ceiling` (confirmable | probable-max | never-observable) and `next_coverage_due` — this is
  the **collection-tasking output**.

## Edge types (grouped; freshness in brackets)

**Origin / supply-chain:** `manufactures` (Mfr→Component)[durable] · `design-authority-for` (Mfr→Variant)
[durable] · `supplies-component` (Mfr→Component)[prime durable / tier-2-3 **semi-durable, revalidate on
sanctions/tender/localization**] · `variant-of` (Component→Variant)[durable] · `exported-by`
(Contract→Mfr/export-agent)[durable] · `analog-of / derived-from-design` (Variant→Variant)[lineage
durable; what it *licenses* is capped at **probable** and decays] · `component-of / composed-of`
(Component→Component)[durable; semi-durable if re-spun — the **BOM/sub-component hierarchy** so deep-tier
chokepoints traverse radar→module→die; instances mostly Known-Gap candidates].

**ORBAT / basing:** `imported-by` (Contract→Unit)[event durable / holdings ~30mo] · `inducted-into`
(Variant→Unit)[possession-by-service durable / named-unit assignment perishable ~18mo] · `subordinate-to`
(Unit→Unit)[durable — sole standing-hierarchy edge; org subordination, **not** cueing architecture] ·
`based-at` (Unit→Site)[**perishable**: field 30d / garrison ~18mo] · `operates/fields` (Unit→Component)
[perishable — the equipment_fingerprint; roots the dependency subgraph] · `operational-status/readiness`
(Unit→engagement radar)[perishable ~3mo — **ordinal observed proxies**: observed-active(emitting) >
exercise-seen > present-only > maintenance-observed > unknown; true graded readiness (P-M-E-S-T / C-1…C-5)
is never-observable → Known Gap].

**Sustainment:** `located-at` (sustainment node→Site)[makes co-location a shared-node join] ·
`reloaded-from` (Unit→Stockpile)[perishable] · `stocks-round` (Stockpile→round)[type durable / depth
perishable] · `replenishes` (Contract→Stockpile/Mfr)[follow-on buy = observable resupply evidence] ·
`resupplied-by` (Stockpile→Mfr)[**authoritative rate/endurance edge**; consistency-checked same-node with
`manufactures`] · `overhauled-at` (Component→Depot)[durable / force-revalidated] · `trained-by`
(Unit→Training)[durable / force-revalidated] · `software-controlled-by` (Component→Tech-Data Authority)
[durable / force-revalidated] · `sustained-by` (Unit→sustainment)[coarse rollup only — **not** used for
chokepoint computation].

**Substitution / redundancy:** `substitutable-by` (three-state: **known-sole-source | known-alternates |
UNKNOWN**)[semi-durable — revalidate on sanctions/tender/localization] — generalized from Mfr→Mfr to **any
critical sustainment node → same-type node** (alt-supplier, alt-depot, alt-training, alt-round, alt-site);
an optional Component→Component form captures an **alt-part** (different component, same function). UNKNOWN
is the default and is **not** evidence of a SPOF; a known-alternate carrying an `adversary_denial_flag` is
discounted (a seeded fake second-source can't dissolve a real chokepoint).

**Resolution:** `same-as` (reversible, auditable merge; resolver **recomputes over the union of indicators
with origin dedup** so a merge can't manufacture corroboration from two echoes; merge-confidence caps the
node) · `distinct-from` (explicit do-not-merge; carries the HQ-9/P vs HQ-9BE flagship case).

**Evidence:** `evidenced-by` (node/edge→Indicator) · `corroborates` (Indicator→Indicator; only when
Sources are origin- AND discipline- AND interest-independent) · `contradicts` (same valid_time + same
resolved-entity×edge-instance only) · `supersedes` (time-ordered state change; emits *candidate-supersede*
when instance identity is uncertain, so "vacant@A" can't erase "occupied@B" for a mobile unit) ·
`derived-from` (Indicator→Source).

## Chokepoint criteria (topology *nominates*; evidence *confirms*)

1. **Sole-source in-degree, three-state gated** — in-degree 1 on a single sustainment-function edge, then
   read `substitutable-by`: **known-sole-source → CONFIRMED**; **UNKNOWN → CANDIDATE** (+Known Gap /
   collection task); known-alternates → not a chokepoint (subject to lead-time). Confirmed *does* fire from
   open-source evidence: a sanctions/export-control listing naming a sole supplier, an evidence-gated
   foreign_control=OEM read, or a follow-on-order proving continued single-source dependence.
2. **Articulation node on the sustainment-only subgraph** — NOMINATION only (a near-linear graph makes
   articulation near-vacuous; evidence-layer + possession edges excluded). Not the discriminator.
3. **Non-substitutable within the lead-time window** — UNKNOWN ≠ "no substitute"; an adversary-denial-
   flagged "alternate" doesn't count.
4. **Foreign-control severity escalation (resolver-gated)** — reach origin via `design-authority-for` +
   `exported-by`; evidence-backed OEM/adversary control → CONFIRMED severity; UNKNOWN → CANDIDATE. *The
   crux of the China→Pakistan dependency.*
5. **Low buffer / days-of-supply (interceptor path)** — days_of_supply vs consumption + lead-time on the
   authoritative `resupplied-by` edge; confirmed by follow-on-buy via `replenishes`; unobservable depth →
   insufficient-evidence + Known Gap, never a guessed bracket.
6. **Deep-tier chokepoint below the prime** — traverse the **BOM via `component-of`** + tier-2/3
   `supplies-component` (seeker, GaN T/R modules, propellant, ICs, beryllium-oxide ceramics, promoted
   chassis); confirmed only when a sanctions/tender indicator NAMES the supplier; else CANDIDATE.
7. **Confidence ceiling on inferred chokepoints (computed)** — all-inferred-from-architecture → capped at
   probable/candidate; `analog-of`-propagated (S-400→HQ-9) capped at probable.
8. **Cross-path co-location single point** — a Basing site that is both a unit's `based-at` and the only
   sustainment node's `located-at` — a genuine shared-**node** join.
9. **Single-in-degree radar chokepoint** — (a) intra-unit: one engagement radar = CONFIRMED SPOF / SEAD
   aimpoint (structural fact); (b) up-echelon shared surveillance radar = **org-inferred CANDIDATE** tied to
   the never-observable IADS Known Gap — *not* an operational-blinding claim.
10. **Confirmed vs candidate separation + collection-tasking framing** — partition all flagged nodes;
    state the expected confirmed:candidate ratio up front (deep-tier will be *predominantly candidates*).
    This is the answer to "isn't that just your ignorance printed as a finding?"

## Observability map (lifecycle → indicator → source → strength → gap)

| Stage / fact | OSINT indicator | Source | Strength | Typical gap |
|---|---|---|---|---|
| Manufacture / design attribution | prime + `design-authority-for`, radar-by-role | Jane's, IISS, expo marketing (Zhuhai/AAD) | **confirmed** (multi origin-indep refs) | production rate/plant, all sub-tier suppliers |
| Cross-family lineage | design derivation, `analog-of` license | RUSI/press histories | lineage confirmable; license **probable** | licenses patterns not HQ-9 numbers |
| Export / transfer | SIPRI register + origin-indep primary record; `exported-by` (CPMIEC) | SIPRI (aggregator!), press, gov records | probable on aggregator alone; **confirmed** only w/ cross-origin primary | SIPRI counts deliveries not orders; ranges only |
| Import / acquisition | ISPR ack, register, budget lines, AIS + port imagery | state media/PR, budget, maritime + EO | **confirmed** (possession) only w/ **cross-interest** corroboration | # fire units, contracted qty, package scope |
| Induction (marquee) | induction announcement (14 Oct 2021), parade/exercise footage | official PR + state media + a **non-aligned third origin** | possession-of-variant confirmable via 3rd origin; **named-unit assignment capped at probable** | FOC, crew-training, readiness (perishable) |
| Basing / deployment | commercial EO of the diagnostic HQ-9 signature; S-1 SAR emitter | Maxar/Planet read by CSIS AMTI, IMINT blogs | **probable** single-pass (decoy penalty); confirmed w/ repeat-pass OR ELINT + clean decoy | mobile relocation, decoys, load-out unreadable |
| Radar functional role | array geometry + siting; fire-control ELINT | IMINT tradecraft, ELINT | confirmed when IMINT + ELINT agree | as-fielded perf, ECCM modes, channel capacity |
| Sustainment siting | depot/stockpile construction imagery via `located-at` join | EO, procurement, press | probable; co-location SPOF w/ node-identity match | which facility serves which unit; throughput |
| Sustainment (spares/training/resupply) | tenders, training contracts, follow-on orders via `replenishes` | procurement portals, press, EO | probable; a follow-on delivery confirms continued dependence | actual stock, magazine depth, FSR/OEM-tech dependence |
| Chokepoint / sub-tier supplier | named in tender/sanctions/contract (CONFIRMED) else inferred (CANDIDATE) | sanctions lists, procurement, RUSI deep-tier | confirmed needs a NAMED sole-source | sub-tier almost never OSINT-visible → mostly candidates |
| Interceptor depth / readiness | **none reliable** → Known Gap (never-observable) | n/a | insufficient-evidence | per-battery depth, reserve stock, serviceability |
| Contract terms / localization | **none** (registers exclude terms) → Known Gap | n/a | insufficient-evidence | price, offsets, tech-transfer, localization clauses |
| C2 / IADS topology | press mention of the network (CLIAD) w/o topology → Known Gap | n/a | insufficient-evidence | data-link topology, joint-engagement maturity |
| Media authenticity (M4) | reverse-image first_seen, EXIF integrity, caption consistency, coordinated-inauthenticity + adversary-denial | forensic/provenance tools | integrity SIGNAL — applies credibility penalty, can OVERRIDE corroboration | fabrication-up AND concealment-down both defeat a bare count |
| Corroboration integrity | ≥2 origin- + discipline- + interest-independent indicators | STANAG/FM 34-3 via the Resolver | confirmed only when precedence rules met | circular reporting, aggregator inheritance, aligned pairs = FALSE corroboration |

---

## Demo scope (the 7-day slice vs the full spec)

The full ontology above is the **design-note / interview** artifact — it's what makes C defensible. The
running demo implements a **coherent subset over the frozen HQ-9/P corpus** (depth over coverage):
- **Nodes:** Manufacturer, Component (with functional_role), Variant, Contract/Import, Unit (recursive),
  Basing site, **both** highest-leverage sustainment nodes (Interceptor Stockpile & Resupply + Tech-Data /
  Software & Calibration Authority), + the evidence layer (Source, Indicator), Confidence Resolver (config),
  Known Gap.
- **Edges:** the flagship-trace edges + evidence edges + `same-as`/`distinct-from` + **one
  `substitutable-by`** (the seeded substitutability story) + **one deep-tier `component-of` /
  `supplies-component` branch** (one named sub-supplier + the rest as candidates).
- **Chokepoint criteria:** #1, #4, #7, #10 (the three-state sole-source, foreign-control, confidence
  ceiling, and the confirmed-vs-candidate separation) — these carry the story; #2/#8/#9b are design-note.
- **Confidence:** the resolver form with simplified constants (see `../spine/04-credibility.md`).
Everything else is the "four more weeks" roadmap. Keep this line sharp on the call: *the demo builds the
subset; the ontology defends the whole.*

## Decisions
- Materiality is derived **backward from the three target queries + tradecraft** — the defensible answer to
  "why these entities and no more."
- 14 node types, ~31 edges, 10 chokepoint criteria as above. Node count held; net +6 knowledge-layer edges
  vs the original draft, each required by a query or CONTEXT.
- *Supply-chain-review refinements (additive; mostly design-note, instances land as Known-Gap candidates —
  not demo-build burden):* added **`component-of`** (BOM depth), listed & **generalized `substitutable-by`**
  to any critical sustainment node (+ optional Component-level alt-part), made unit **`designator`
  multi-valued** incl. cover-designator, and made **`operational-status` ordinal**. The corpus seeds ≥1
  concrete instance of each so the mechanism fires (data cases in `../md/05-data-scoping-C.md` §5.1).
- Chokepoint = **structural nomination + evidence confirmation**, output as **prioritized collection
  tasking** (confirmed chokepoints + candidate gaps), never a claimed-complete SPOF map.
- Freshness is **symmetric**: people/knowledge sustainment edges are durable-by-default but
  force-revalidated on dissolution indicators, so decaying dependencies decay.
- Enrichment bound (China-HQ-9) locked in `00-overview.md` (Q5); confidence/freshness values in
  `../spine/04-credibility.md` (Q2–Q4).

## Open questions
- **Store choice** to represent recursive units + reversible merges + evidence layer (shared with
  `../spine/01-graph-and-ontology.md`) — *deferred by decision; decide later.*
- *(Resolved this session: **sustainment node → build BOTH** Interceptor Stockpile & Tech-Data Authority;
  **deep-tier hunting depth → a data question**, bounded by the generator cases in
  `../md/05-data-scoping-C.md` §5.1 — seed ≥1 sanctions/tender-named sub-supplier (confirmed) + the rest as
  candidates.)*

## Research directions / provenance
- ★ Materiality research **done** (this doc). Residual: a focused pass on *known HQ-9/P deep-tier
  suppliers* if we choose to hunt them (Q5 residual).
- Key sources the research leaned on: **RUSI — Bronk, *Modern Russian & Chinese IADS* (2020)**; **CSIS
  Missile Threat & AMTI** (imagery-backed HQ-9 ORBAT); **US Army OB doctrine** (unit identification =
  designation+type+size+subordination, globalsecurity FM 34-3 / IS3001); **ausairpower** HQ-9 battery
  radars; **geimint** IMINT site-signature tradecraft; **Quwa** (Pakistan HQ-9/P framing); army-technology,
  radartutorial. Alias/false-merge ground truth: `../md/05-data-scoping-C.md` §4. Full workflow output
  (research + synth + critiques): session task `wzh3zoiwk` transcript.
