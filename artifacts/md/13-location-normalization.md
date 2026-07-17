# 13 — Location precision & the normalization system (C)

**Why this doc exists.** Two things were missing. (1) The corpus named every place as a **bare toponym
in one format** ("Rawalpindi", "Rahwali", "Karachi") — so the location-normalization component had
*nothing to normalize* and couldn't be demonstrated. (2) We never wrote down **how precise a location
has to be** for each kind of ORBAT / supply-chain node — and the answer is genuinely different per node
type (a design authority in Beijing does not need pad-level coords; a relocating fire-unit does). This
doc fixes both: the precision spec, and the ≥2-format seeding that makes the normalizer real.

It feeds `C/01-materiality-ontology.md` (what's material about a place), `spine/03`+`08 §3.9`
(resolution — place is just another entity type), and the data generator (`10-data-generation-strategy.md`).

---

## 1. What ORBAT / supply-chain actually needs from a location — per node type

Location precision is **not uniform**. Over-precision is the over-engineering trap (we don't need a
grid ref for a Beijing institute); under-precision breaks the observable (you can't fire a relocation
tripwire on "somewhere in Punjab"). The requirement is set by **what the node is FOR**:

| Node / edge type | Precision required | Why that precision (and not more) | How it shows up in sources |
|---|---|---|---|
| **Deployment site** (`based-at`, SAM battery / fire-unit) | **site / pad-level** (≤ ~100 m; must be confirmable in 10 m imagery) | the locked observable is a *location state-change*; two independent signals only corroborate if they resolve to the **same pad**; de-conflicts "moved" vs "second unit" | IMINT/geolocation grid or lat-long; base name (often **renamed** → alias); social "near <town>" |
| **Manufacturing / design authority** (`manufactures`, `supplies-component`) | **facility-level** (org **name + city + district**; coords only where OSINT already has them) | a supply-chain chokepoint is only *collection-taskable* if the candidate facility is named to district; but exact coords add nothing to the assessment and we don't have them → don't invent them | study/report names the institute + city/district; org has **multiple names** (2nd Academy = China Academy of Defence Technology = 航天科工二院) |
| **Port / transit node** (`imported-by`, customs) | **terminal / port-level** | port-of-entry drives the transfer thread; must distinguish adjacent facilities (consignee port ≠ end-user) | customs uses the **official port name** (Port Muhammad Bin Qasim); press says "Karachi" (parent city) |
| **Range / test / exercise site** (`ExerciseEvent`) | **site-level** (the NOTAM polygon) | perishable activity; the geometry *is* the evidence | NOTAM/NAVAREA **DMS polygon vertices** |
| **Admin / HQ / operator command** | **city-level** | it's an org home, not a targetable node | city name only |
| **Unobservable** (magazine depth, C2 topology) | **n/a — Known Gap** | genuinely not locatable in open sources → `observability_ceiling` marks it *permanently* gapped, not a coverage lapse | — |

**Rule of thumb:** precision is *demanded by the query/observable that touches the node*, not by the
node's grandeur. The relocating HQ-9B fire-unit is the most precision-hungry node in the whole graph;
the Beijing design authority — the "biggest" org — needs only city+district. This is the materiality
principle (`C/01`) applied to geography.

**Posture on real vs synthetic coordinates (locked, hybrid data strategy).** Anchor **base/port/facility
coordinates are real and public** (airbase and seaport coordinates are on Wikipedia / OpenStreetMap /
aviation DBs — trivially open). The **specific HQ-9 pad geolocation is synthetic-from-real**, tagged in
the answer key — same defensible posture as the customs file. We do **not** publish novel precise
geolocation of live SAM batteries; the pad offset is invented for the scenario. Canonical values live in
`config/places.yaml` (§6) with a `provenance: real|synthetic` field on every coordinate.

---

## 2. The normalization system = two deterministic stages + one resolution term

"Location normalization" is really **two problems**, and both plug into machinery the spine already has
(`08 §3.9`, §3.11) — location is not a new subsystem, it's the resolution layer with a geo attribute:

**Stage A — coordinate canonicalisation (deterministic parser, pre-resolution).**
Parse whatever notation a source used and emit one canonical form: **WGS84 decimal degrees**. Handles:

| Surface notation | Example (illustrative) | → canonical |
|---|---|---|
| Decimal degrees (DD) | `24.7869, 67.3410` | (24.7869, 67.3410) |
| Degrees-minutes-seconds (DMS) | `32°15′30″N 74°07′48″E` | (32.2583, 74.1300) |
| MGRS military grid | `43R FP 12345 67890` | (33.6xxx, 73.0xxx) |
| UTM | `43R 331000E 3720000N` | (…) |
| Maps URL / raw pair | `https://maps…?q=24.79,67.34` | (24.79, 67.34) |

This is the geographic sibling of the **transliteration normalizer** in `08 §3.9` — a deterministic
rule-based pre-processor run *before* resolution, never an LLM call inside `rebuild()`.

**Stage B — place resolution (the resolution layer, with a geodesic attribute term).**
A PLACE is an entity type; two place references resolve to one node when either:
- **toponym/alias match** against a seeded **place gazetteer** (`config/places.yaml`) — "Chaklala" ≡
  "Nur Khan" ≡ "OPRN" ≡ "PAF Base Nur Khan, Rawalpindi"; "Port Qasim" ≡ "Port Muhammad Bin Qasim" ≡
  "Bin Qasim"; **or**
- **geodesic proximity** — a parsed coordinate falls within a place's precision radius of a known node
  ⇒ same place. This makes **coordinate ≡ toponym** unification fall out of the existing
  `merge_score = 0.30·attribute + …` (§3.9) with the attribute term reading geodesic distance for place
  entities. A coordinate and a name that denote the same pad merge; two coordinates 35 km apart don't.

**Distinct-from is as important as same-as** (the FT-2000 trap, geographic edition): **Karachi Port
(Keamari)** and **Port Qasim (Bin Qasim)** are ~35 km apart and both get called "Karachi" — a naive
string merge fuses them and the transfer thread points at the wrong terminal. Proximity + gazetteer keep
them **distinct**; the ambiguous parent-city mention ("Karachi") resolves to the *metro*, not to either
specific terminal, and drops to HITL if a claim needs terminal-level identity.

**LLM stays a proposer, never the authority** (§3.11): the LLM may *propose* that an unseen place name is
an alias of a known node (raise-into-HITL only); the canonicalisation, the geodesic score, and the
merge/keep-separate bands are deterministic.

---

## 3. Surface-format taxonomy — what appears in the wild

A location reference in the raw corpus is one of: **(1)** common city toponym ("Karachi"); **(2)**
specific facility / port / cantonment name ("Port Muhammad Bin Qasim", "Rahwali Cantt"); **(3)**
historical / renamed alias ("Chaklala" → Nur Khan); **(4)** decimal-degrees; **(5)** DMS; **(6)** MGRS
grid; **(7)** UTM; **(8)** relative bearing-and-distance ("~12 km NNW of Gujranwala"); **(9)** admin
descriptor (district / tehsil / province); **(10)** maps URL / raw pair. The normalizer's job is to
collapse (1)–(10) that denote one place into one node, and *keep apart* the ones that don't.

Two enumerable **corruption operators** carry this in generation (`operators.yaml`):
`coordinate_precise` (render an exact coord in the source's natural notation) and `toponym_alias` (use a
real alternate/renamed/relative place name) — the deliberate counterpoints to the existing
`coordinate_absence`.

---

## 4. How the corpus seeds it — every demonstrated site in ≥2 formats

Four sites, chosen because they're already load-bearing (the observable, the worked query, the
chokepoint) — so normalization isn't a bolt-on demo, it's *required* for those threads to work:

| Site (canonical node) | Doc → format | What it demonstrates |
|---|---|---|
| **Nur Khan / Chaklala, Rawalpindi** (`site_rawalpindi`, relocation origin) | `d17` → **MGRS grid** + "PAF Base Nur Khan (formerly Chaklala)" | MGRS parsing + **renamed-base alias** |
| **Rahwali** (`site_rahwali`, relocation destination) | `d18` → **DMS coords**; `d19` → **toponym + relative** "Rahwali Cantt, ~12 km NNW of Gujranwala" | **coordinate ≡ toponym across two independent sources** — the observable only fires because they unify (load-bearing) |
| **Port Qasim / Karachi** (`site_karachi`, worked-query anchor + entry) | `d05` → **"Port Muhammad Bin Qasim"**; `d07` → **DD coords** + "Karachi"; `d02` → "Karachi" | alias unification + coord↔toponym + the **Karachi-Port vs Port-Qasim distinct-from trap** |
| **CASIC 2nd Academy / 23rd RI, Beijing** (`mfr_casic`, `mfr_23rd_ri`) | `d22` → **facility + city + district** ("CASIC Second Academy, Beijing (<district>)"; "Beijing Institute of Radio Measurement") | **facility-level precision for a manufacturing node** + org-name alias |

Coverage across the four: DD, DMS, MGRS, relative-bearing, facility/port alias, renamed-base alias,
parent-city ambiguity, and one distinct-from trap — a full normalization exercise, all earned in raw
text, none of it stated as a clean field.

---

## 5. The oracle (answer-key additions)

- `ground_truth.places[]` — the gazetteer of canonical nodes: `{place_id, canonical_name, kind,
  precision_class, canonical_dd, provenance, aliases[], admin, observability, note}`.
- Per location-bearing doc, `expect.location = {place_id, surface_form, format, precision}` — so the
  pipeline's parse+resolve is scored against ground truth.
- `flexes.location_normalization` — expected unifications (d18 DMS ≡ d19 toponym → `site_rahwali`;
  d05/d07/d02 → `site_karachi`) **and** the distinct-from (`karachi_port` ≠ `site_karachi`/Port Qasim).
- Site/mfr nodes gain a `place_ref` pointing into the gazetteer.

## 6. Config — the seeded gazetteer (`config/places.yaml`)

`config/places.yaml` is the pipeline's **seed** gazetteer (extensible config, per CLAUDE.md — not
hardcoded): canonical place nodes + known aliases + canonical coords (`provenance: real|synthetic`) +
precision class. **One alias is deliberately withheld from the seed** (the "Chaklala" renamed-base form)
so the resolver has to *earn* one place merge it wasn't handed — the geographic instance of the
adaptation / recall story in `08 §3.11` ("one planted alias not in the seeded table"). The eval oracle
(§5) carries the full truth; the seed does not.

---

## 7. Decisions logged (→ `DECISIONS.md`)

- **Location precision is per-node-type, set by the touching query/observable, not by node grandeur**
  (materiality applied to geography). *Principle: model exactly what the queries need.*
- **Anchor coords real+public; pad geolocation synthetic-from-real, tagged** *Principle: hybrid data
  strategy; provenance not optional.*
- **Normalization = deterministic coordinate-canonicaliser + place-resolution over a seeded gazetteer,
  reusing the resolution layer's merge machinery; LLM proposes aliases only.** *Principle: LLM proposes,
  rules dispose; extensible-not-hardcoded.*
- **Keep the Karachi-Port ≠ Port-Qasim distinct-from trap** (geographic FT-2000). *Principle: test design
  that lands traps in the HITL band; distinct-from is first-class.*
