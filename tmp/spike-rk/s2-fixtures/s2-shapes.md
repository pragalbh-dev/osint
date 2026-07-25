# RK-LAYER (S2) — abstracted shape fixtures (implementation-blind)

`schema_version: rk-s2-abstract-shapes/1.0` · machine-readable twin: `s2-shapes.json`

**Read this file, not the corpus.** These fixtures exist so that the type/instance split, the presence and
formation citizens, and basing-as-a-derived-edge can be built and tested against the *structural difficulty*
of the real problem without anyone seeing the real data - because seeing it biases the implementer toward
tuning to it, and because for most of these shapes the real data contains nothing to see.

Every entity here is invented: a fictional regional water-and-power-infrastructure domain, continuous with
the vocabulary of the earlier `gold/abstract-shapes.json` set so the two can be read together. There are no
real designations, place names, manufacturers, document ids or source ids anywhere in this file.

What is preserved from the real problem is what matters for this stage:

- which facts in a mention are **design-level** (shared by every operator) and which are **instance-level**
  (operator-scoped), and how the two arrive lumped together;
- which instance **citizen** the evidence earns - a *presence* (equipment observed at a place) or a
  *formation* (a designation-bearing organizational body), and what makes the difference;
- how many mentions and how many **publishers** there are, and which reports are derivative of which;
- which discriminators - operator, geography, designation, time - are **present** vs **absent**, and which
  are *stated absent* (a much stronger fact than missing);
- source grades and dates, including the cases where the later source is the weaker one;
- where a **sourced figure** exists and where a count would have to be invented to produce one.

**No thresholds, scores, band names as values, or config keys appear anywhere in this file, by design.**
Each fixture states its required *outcome* in prose and, next to it, the **tempting-but-wrong** outcome -
because a fixture that only describes success cannot catch optimism. Choose the mechanism and the numbers on
general principle; the test author asserts them independently.

**Deviation from the earlier set's schema, deliberately:** fixtures here carry a `documents` **list** rather
than a single `text`. Most of this stage's difficulty is inherently multi-document - a derived basing has two
premises in two documents, a supersede has two reports, a count trap has five - and collapsing them into one
document would destroy the very thing being tested (that several reports are not several launchers, and that
one publisher is not two sources).


## What each fixture is for

| Shape | Fixture | What it is for |
|---|---|---|
| 1 | `F1a-straddle-blatant` | One mention carrying both design-level and instance-level facts, emitted by the extractor as a single design-typed node. The split trigger is present four times over. |
| 1 | `F1b-straddle-subtle-single-attribute` | The subtle straddle: a record that is legitimately design-level throughout except for ONE misplaced instance-layer attribute - and no site and no date anywhere. |
| 2 | `F2a-endpoint-materialization-presence` | An instance-layer sighting whose mention named only the DESIGN. It must materialize a provisional presence and hang the sighting on that, not on the shared design node. |
| 2 | `F2b-cross-layer-holding-mints-nothing` | The mirror of F2a: a country/operator-level holding, neither endpoint instance-typed. It must mint NOTHING - no presence, no formation, no site. |
| 3 | `F3a-bare-sighting-presence-only` | A bare equipment sighting at a site: presence only, never a formation - and the source itself states that the organizational evidence does not exist. |
| 3 | `F3b-formation-earned-derived-basing-two-premises` | A sighting PLUS organizational evidence tying the equipment to a NAMED body: a formation is earned, and a derived basing edge is materialized citing two premise claims. This is also the non-vacuous input G17 needs, because it makes the derived branch actually execute. |
| 3 | `F3c-stated-basing-good-source` | A STATED formation-at-site from a good-grade source: it binds the formation directly, at normal source credibility, with no premise pair and no derivation. |
| 3 | `F3d-stated-basing-low-grade` | The same stated formation-at-site, asserted by a grade-E anonymous account, dated later than F3c and naming a different site. Stated still runs through source grade - and the pair is a candidate relocation from the weakest source available. |
| 4 | `F4-count-trap-reports-are-not-launchers` | Five reports of the same equipment at the same site, of which three state no number at all. The naive count equals the number of reports - and it is wrong twice, in two different ways, both of which look plausible. |
| 5 | `F5a-two-candidate-formations-equal-evidence` | One sighting, two separately named candidate formations, equally evidenced, neither tied to the site. The correct outcome is two attributions, or one plus an explicitly named gap. Never a silent pick. |
| 5 | `F5b-two-candidate-formations-unequal-evidence` | The same two-candidate shape, but the second candidate is asserted by a grade-E anonymous account. Grading it down is correct; deleting it is not. |
| 6 | `F6a-site-type-deconfliction-stated` | One named formation, concurrently at a depot and at a forward station, both site kinds stated by the same good-grade source. Two valid basings - no relocation, no contradiction, no wall. |
| 6 | `F6b-site-type-absent` | The same two-site, one-body shape with NO site kind stated anywhere. Absent must not de-conflict. |
| 6 | `F6c-site-type-vocabulary-drift` | Site kind IS stated on every mention - in different words for the same kind of place, by different publishers. A raw-string key puts one site in two buckets and two different kinds of place in what looks like one. |
| 7 | `F7a-supersede-over-subconfirmed-identity` | Two anonymous presences that a co-location-friendly scorer wants to fuse, whose fusion turns two site edges into one body's before-and-after, promoting a relocation the analyst is never asked about - and deleting the named gap that said the identity was unresolved. |
| 7 | `F7b-supersede-legitimately-earned` | The same two site edges, but the identity is earned on a stated designation at both ends, by good sources, with the same site kind. The supersede should work - and must not manufacture relational evidence that the two sites are one place. |
| 8 | `F8a-customs-spine-inexpressible` | A customs declaration whose actual spine is event - consignee - shipper, so that the ontology gap is demonstrable rather than asserted: the relations the document states have no lane, and the relation it does not state is the one the schema offers. |
| 8 | `F8b-operator-relation-and-refutation-no-carrier` | A stated operator RELATION and a stated REFUTATION of one, neither of which has a carrier while operator exists only as an attribute. The second shape of the same anti-fabrication hazard as F8a. |

## Which of these the frozen corpus can exercise

| Fixture | Corpus |
|---|---|
| `F1a-straddle-blatant` | EXERCISABLE in kind. The corpus routinely lumps design and instance facts on one mention (a sighting document states family, designators and a site in one breath). It does not supply a case this clean, and no corpus document states the routing test in its own voice the way this fixture does ('regardless of operator'). |
| `F1b-straddle-subtle-single-attribute` | NOT EXERCISABLE as a clean single-attribute straddle. Corpus mentions straddle heavily but always with several misplaced facts at once, so the 'outnumbered trigger' case has to be authored. |
| `F2a-endpoint-materialization-presence` | EXERCISABLE, and the corpus's strongest suit: equipment-at-a-site sightings that name only a design are the dominant shape in the primary scenario. What the corpus does NOT supply is a site whose sighting names only the design AND whose operator is genuinely absent - most corpus sightings state or imply an operator somewhere in the document. |
| `F2b-cross-layer-holding-mints-nothing` | EXERCISABLE. The corpus has several genuine holding statements (an operator 'continues to field' a design; an operator 'is believed to operate' a design) and it also has the exact area-of-responsibility trap - places named only as sectors, belts and provinces, which the ontology already had to grow a refinement to keep out of the site lane. |
| `F3a-bare-sighting-presence-only` | EXERCISABLE, strongly - this is the corpus's most common shape, and one corpus document states the marking absence across its whole pass history in almost these words. The corpus also supplies a stated non-disclosure policy, so the 'will not close' reason is real data. |
| `F3b-formation-earned-derived-basing-two-premises` | PARTIALLY EXERCISABLE, and this is the corpus's largest hole. The corpus has the two premises as separate shapes (equipment-at-a-site sightings, and one induction into a named-ARM body) but the induction names no numbered body, so the derived basing has no designation to attach to. The designation rung of the discriminator ladder has zero data anywhere in the corpus. |
| `F3c-stated-basing-good-source` | NOT EXERCISABLE AT ALL. Verified independently: across all 52 scenario documents there is exactly one stated formation-at-site basing, and it belongs to an off-subject chaff unit in another country planted as a designator-collision decoy. Every basing in the answer key is annotated 'derived'. This fixture is the only place the acceptance criterion can be tested. |
| `F3d-stated-basing-low-grade` | EXERCISABLE for the credibility half - the corpus has a grade-E relocation spoof and a grade-D social sighting, and the supersede floor was built against them. NOT exercisable for the stated-basing half, because neither spoof names a formation: they name equipment. So the corpus can test 'a low-grade relocation claim must not promote' but not 'a low-grade STATED BASING must not promote'. |
| `F4-count-trap-reports-are-not-launchers` | PARTIALLY EXERCISABLE, better than expected. The corpus does carry structured sourced counts with min/max/approx on sighting events, and it has two reports of one site giving different figures, plus a document that states a count is unverifiable this pass. What it does NOT supply is the coincidence: nowhere does the number of reports collide with a plausible equipment count, so the naive implementation is never punished on the corpus. That collision has to be authored, and it is the whole point of this fixture. |
| `F5a-two-candidate-formations-equal-evidence` | NOT EXERCISABLE. Verified: the corpus has no two individuated same-type formations anywhere. Its nearest approaches are a cardinality without individuation ('two operational battalions' - one claim with a quantity, not two referents) and three documents that gesture at extra formations without naming any. This is the shape the gate most needs and the corpus most completely lacks. |
| `F5b-two-candidate-formations-unequal-evidence` | NOT EXERCISABLE, for the same reason as F5a - no two individuated formations exist. The grade-E-anonymous-source half is well represented in the corpus; the two-candidate half is not present at all. |
| `F6a-site-type-deconfliction-stated` | NOT EXERCISABLE. No corpus document places one body at two sites concurrently - the ontology comment itself rests the current unit-only keying on that absence, which is precisely the kind of design input this stage is forbidden to accept. |
| `F6b-site-type-absent` | EXERCISABLE for the absence itself - site kind is missing on a substantial share of corpus site mentions, and one corpus site appears three times in ONE document with the kind present once and absent twice. Not exercisable as a one-body-two-sites pair, for the same reason as F6a. |
| `F6c-site-type-vocabulary-drift` | EXERCISABLE, and already live in the frozen data - this is a verified corpus fact, not a hypothetical. Site kinds in the corpus are free text with no enumeration: the same airfield is described two different ways by two documents, and the two ends of the flagship relocation carry entirely different kind strings. A raw-string key would put them in different buckets. See the findings note; this is the highest-value corpus-grounded item in this set. |
| `F7a-supersede-over-subconfirmed-identity` | PARTIALLY EXERCISABLE. The corpus has the ingredients - two sites, one design, no designations, a relocation beat, and a supersede floor built against a low-grade spoof - but not the trap, because it contains no two co-located same-type formations to fuse. The chain from identity error to drawn relocation therefore cannot be demonstrated end to end on the frozen corpus, which is why it went unnoticed. |
| `F7b-supersede-legitimately-earned` | NOT EXERCISABLE as written. The corpus's relocation beat has no designation at either end - there is no numbered body anywhere in it - so a legitimately earned supersede cannot be constructed from it. Its relocation is earned on geography and imagery alone, which is precisely the class this shape is meant to distinguish from. |
| `F8a-customs-spine-inexpressible` | EXERCISABLE, and already true of the frozen corpus: the customs document's spine is exactly this, and it is unrepresentable today. Verified further - the trading-organization node type is named by NO edge type at all, in either direction, so a correctly typed consignee or shipper can only ever exist as an isolated node. The corpus also supplies the identifier-rich half genuinely: this is the one document where a shared hard identifier could decide an identity. |
| `F8b-operator-relation-and-refutation-no-carrier` | EXERCISABLE, and live in the frozen corpus: the operator relation is stated in relation form in at least two documents, the corpus contains a genuine cross-service operator conflict for one design, and it contains the exact refutation shape for the flagship false-merge trap - which today has nowhere to go. Verified: no operator relation exists in the ontology. |

Full reasoning, with the checks that were run, is in `S2-DATA-FINDINGS.md`.

---

# Shape 1 — A straddling mention (design facts and instance facts in one mention)

---

## `F1a-straddle-blatant`

**Purpose.** One mention carrying both design-level and instance-level facts, emitted by the extractor as a single design-typed node. The split trigger is present four times over.

**Why it is hard.** Nothing in the sentence is wrong, mis-worded or hedged. The source is a good-grade primary and every fact in it is true. The only defect is that the extractor put operator-scoped facts on a node that every operator shares — so there is no textual signal to catch, only a layer mismatch.

**Scope items:** 2 (straddle split); 1 (per-attribute layer) · **refs:** spine/13 §5.1-5.2; A2/A4; acceptance: a straddling mention splits into linked design + instance nodes

### Documents

**`press-note-A`** — operator works bulletin · **grade:** B · **bias:** operator of the asset (interested party) · **dated:** 2025-03-12

```text
NORTHERN GRID WORKS - WORKS BULLETIN 14/2025
Dated: 12 March 2025

TRANSFER PLANT AT SITE K-4

The High-Volume Transfer Set TL-40, a Meridian Works Corporation design rated at a nominal
throughput of 140 units and carrying four canisters per skid, is now in service with Northern
Grid Works. Six skids of the type were on the hardstand at Site K-4 when the works party
visited on 12 March 2025.

The set's control cabinet is the RC-118 pattern, common to all TL-40 installations regardless
of operator.
```

### What the extractor emitted

One node, entity type = the design (TL-40), carrying: nominal throughput, canisters per skid, maker reference, control-cabinet pattern, operator, site reference, count, observation date.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| nominal throughput 140 units | **design** | unchanged if another operator fielded the same set |
| four canisters per skid | **design** | a property of the design |
| maker is Meridian Works Corporation | **design** | one maker for the design, whoever fields it |
| control cabinet is the RC-118 pattern | **design** | the source itself states it is common to all installations regardless of operator - the routing test is checkable in-source here |
| operator is Northern Grid Works | **instance** | the fact is exactly an operator scoping |
| six skids were on the hardstand at Site K-4 | **instance** | a located, dated, counted individual |
| observed on 12 March 2025 | **instance** | a design has no observation date |

### Discriminators

- **operator** — STATED ('Northern Grid Works')
- **geography** — STATED as a named site ('Site K-4'), no coordinates
- **designation** — ABSENT - no body is named at all
- **time** — STATED exactly (2025-03-12)

### Required outcome (prose — choose your own mechanism and values)

The one emitted node must become two linked nodes: the shared design, carrying only the four design facts, and one instance-layer citizen carrying operator, site, count and date. The instance-layer attributes must not remain on the design node, and the design node must stay the same node that any other operator's instance also links to - splitting must not fork the design. Because the source names no body, the instance that is created is a presence, not a formation, and the absence of a designation must be visible as an unfilled slot rather than as silence. Every fact on both nodes must still cite this one document.

### Tempting but wrong

- Keep one node and call it 'TL-40 (Northern Grid Works)' - a design node with an operator attribute. The graph then has one node per operator per design, so the shared design fragments and nothing links Northern Grid Works' set to the Water Authority's set of the same design.
- Split, but mint a second DESIGN node for the operator's variant. The straddle is fixed and the shared design is destroyed in the same motion.
- Move everything onto the instance and leave the design node empty, so the maker and throughput now belong to one operator's holding and have to be re-asserted for the next operator.
- Mint a formation because 'six skids ... at Site K-4' reads like an establishment. No body is named.

### Negative gold — spans that must produce NO claim

- The works-party visit is context, not a claim about the plant.
- 'in keeping with' style framing carries no fact.

**Corpus.** EXERCISABLE in kind. The corpus routinely lumps design and instance facts on one mention (a sighting document states family, designators and a site in one breath). It does not supply a case this clean, and no corpus document states the routing test in its own voice the way this fixture does ('regardless of operator').

---

## `F1b-straddle-subtle-single-attribute`

**Purpose.** The subtle straddle: a record that is legitimately design-level throughout except for ONE misplaced instance-layer attribute - and no site and no date anywhere.

**Why it is hard.** Seven of eight lines belong on the design node, so any heuristic that asks 'does this mention look like a design or an instance?' answers 'design' and keeps the operator line. The second difficulty is what the split produces: with no site and no time, there is nothing to make a sited presence out of, so a split that mints one invents a sighting.

**Scope items:** 2 (straddle split); 1 (per-attribute layer) · **refs:** spine/13 §5.1; D-13.3 dual-attribute split

### Documents

**`spec-sheet-B`** — manufacturer data sheet · **grade:** C · **bias:** manufacturer's own product literature · **dated:** 2024-09

```text
MERIDIAN WORKS CORPORATION - PRODUCT DATA SHEET
TL-40 HIGH-VOLUME TRANSFER SET (Rev. 3, September 2024)

Family:                   Vanguard
Nominal throughput:       140 units
Canisters per skid:       4
Control cabinet:          RC-118
Sensor fit:               active telemetry
Export designation:       V-40
Fleet operator of record: Water Authority
```

### What the extractor emitted

One design-typed node carrying: family, nominal throughput, canisters per skid, control cabinet, sensor fit, export designation, and 'fleet operator of record'.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| family Vanguard | **design** | lineage of the design |
| nominal throughput 140 units | **design** | a spec |
| canisters per skid 4 | **design** | a spec |
| control cabinet RC-118 | **design** | a fit common to the design |
| sensor fit: active telemetry | **design** | a spec |
| export designation V-40 | **design** | a designation of the design |
| fleet operator of record: Water Authority | **instance** | the only operator-scoped line in the record - and the whole split trigger |

### Discriminators

- **operator** — STATED ('Water Authority') - and it is the misplaced attribute
- **geography** — ABSENT entirely
- **designation** — ABSENT
- **time** — STATED only as the document's revision month (2024-09); no observation time exists

### Required outcome (prose — choose your own mechanism and values)

The single misplaced attribute must be detected and routed off the design node - one instance-layer attribute on a design-layer node is the trigger, and it does not become less of a trigger for being outnumbered. What it routes TO is the second half of the shape: the source gives no site and no observation, so the honest destination is an operator-level holding of the design, not a sited presence. If the only available destination is a presence, then the correct output is that the attribute is refused onto the design node and its want of a home is recorded as a gap - never a presence with an unknown site and an unknown time.

### Tempting but wrong

- Leave 'operator of record' on the design node because everything else in the record is design-level, so the record 'is' a design record. This is the exact misplacement the per-attribute layer exists to catch, and after it the shared design carries an operator - which is what makes two operators of one design collide.
- Fire the split and materialize a presence with site unknown and time unknown - a sighting that no source reported, at no place, on no date.
- Treat the export designation as instance-level because it is 'export' (i.e. operator-facing). It is a designation of the design; the routing test answers 'design'.

### Negative gold — spans that must produce NO claim

- 'Rev. 3' and the revision month are provenance, not facts about the plant.
- The data sheet is the manufacturer's own literature; nothing in it is corroboration of anything else in it.

**Corpus.** NOT EXERCISABLE as a clean single-attribute straddle. Corpus mentions straddle heavily but always with several misplaced facts at once, so the 'outnumbered trigger' case has to be authored.

---

# Shape 2 — Endpoint materialization (and the cross-layer holding that mints nothing)

---

## `F2a-endpoint-materialization-presence`

**Purpose.** An instance-layer sighting whose mention named only the DESIGN. It must materialize a provisional presence and hang the sighting on that, not on the shared design node.

**Why it is hard.** The only entity the source names is a design ('the TL-40 type'), so the naive binding - point the sighting's subject at the design node - is also the only binding the text literally licenses. What makes it wrong is not the text but the consequence: the shared design node accumulates every site anyone ever saw the type at, and every operator's sightings then share a neighbourhood, which is the input that makes unrelated instances look like one thing.

**Scope items:** 2 (endpoint materialization); 3 (presence citizen) · **refs:** spine/13 §5.3 worked example; A4; acceptance: an observed-at materializes a presence

### Documents

**`survey-C`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-04-08

```text
AERIAL SURVEY EXTRACT - MARROW BANK PUMPING STATION
Collected 08 April 2025, single pass, 0.5 m

Six skid-pattern units of the TL-40 type are visible on the north apron, in a fan arrangement.
One octagonal cabinet signature consistent with the RC-118 pattern sits on a prepared pad
approximately 300 m east of the skid group.

No markings, signage or vehicle numbers are legible at this ground sample distance.
```

### What the extractor emitted

An instance-layer sighting edge from the design ('TL-40') to the site ('Marrow Bank pumping station'), plus a cabinet sighting from the component pattern ('RC-118') to the same site.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| six skid-pattern units of the TL-40 type on the north apron | **instance** | a located, dated observation - the presence citizen |
| the type is the TL-40 | **design** | names which design the presence is of |
| an RC-118-pattern cabinet on a prepared pad ~300 m east | **instance** | a second located observation, of a component, at the same site |
| no markings, signage or vehicle numbers legible | **instance** | a STATED absence of organizational evidence, scoped to this pass's resolution |

### Discriminators

- **operator** — ABSENT - the survey names no operator
- **geography** — STATED as a named station with an on-site bearing and distance, no coordinates
- **designation** — EXPLICITLY DECLARED ABSENT - 'no markings, signage or vehicle numbers are legible'
- **time** — STATED exactly (2025-04-08, single pass)

### Required outcome (prose — choose your own mechanism and values)

A provisional presence must be materialized at Marrow Bank; the sighting binds to it; the presence links to the shared design node; and the shared design node itself must acquire no location. The cabinet sighting materializes its own presence at the same site - two presences, because the ontology separates the design of a set from the design of a component, and one pad bearing does not fuse them. With no operator stated, the presence is under-individuated and must say so: a presence whose operator slot is unfilled is the honest output, not a presence attributed to the operator that the rest of the corpus happens to talk about most.

### Tempting but wrong

- Attach the sighting directly to the shared design node because that is the only entity the source named. The design then 'is at' a place; every later sighting of the type piles onto the same node; and two operators' sightings acquire a shared neighbour, manufacturing relational evidence that they are the same individual.
- Materialize a FORMATION because 'six skid-pattern units in a fan arrangement' is a section-shaped observation. Nothing organizational is stated, and the source says outright that no markings are legible.
- Fill the absent operator from context (the design's usual operator elsewhere). That is inference presented as observation.
- Fuse the skid presence and the cabinet presence into one 'installation' node because they are 300 m apart at one site. The source gives two separate signatures and one relative bearing, not one object.

### Negative gold — spans that must produce NO claim

- The ground sample distance and pass count are collection metadata, not claims.
- 'consistent with the RC-118 pattern' is a hedged identification of a pattern, not an assertion that this is an RC-118.

**Corpus.** EXERCISABLE, and the corpus's strongest suit: equipment-at-a-site sightings that name only a design are the dominant shape in the primary scenario. What the corpus does NOT supply is a site whose sighting names only the design AND whose operator is genuinely absent - most corpus sightings state or imply an operator somewhere in the document.

---

## `F2b-cross-layer-holding-mints-nothing`

**Purpose.** The mirror of F2a: a country/operator-level holding, neither endpoint instance-typed. It must mint NOTHING - no presence, no formation, no site.

**Why it is hard.** It is the same grammatical shape as a sighting - an operator, a design, and a place-like noun phrase - so a materializer keyed on 'an operator and a design appear together' fires on it. And the place-like phrase ('its inland transfer network') is an area of responsibility, which is the single most common thing to be mistaken for a site.

**Scope items:** 2 (endpoint materialization - the mirror) · **refs:** spine/13 §5.3 contrast clause; D12 (imported-by should require a stated unit)

### Documents

**`holding-D`** — national utility annual plant report · **grade:** B · **bias:** operator of the asset (annual report) · **dated:** 2025-01

```text
CALDONIA NATIONAL WATER UTILITY - ANNUAL PLANT REPORT 2024

The utility fields the TL-40 high-volume transfer set across its inland transfer network.
Fleet-wide throughput and availability figures are reported in Annex 2. No installation-level
detail is published.
```

### What the extractor emitted

A holding relation from the operator to the design, plus a candidate site named 'inland transfer network'.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| the utility fields the TL-40 | **cross-layer holding** | operator to design - neither end is an instance, so nothing is implied about any individual |
| 'across its inland transfer network' | **neither** | an area of responsibility, not a place a set sits |
| no installation-level detail is published | **gap** | a stated policy of non-disclosure - the reason this gap will not close from this source |

### Discriminators

- **operator** — STATED (the national utility)
- **geography** — ABSENT - only an area of responsibility
- **designation** — ABSENT
- **time** — STATED as a reporting year (2024)

### Required outcome (prose — choose your own mechanism and values)

A holding edge to the shared design, and nothing else materialized. No presence, because no site and no observation exist; no formation, because no body is named; no site node for the transfer network, because a network of responsibility is not a place. The stated non-publication should surface as a gap that names both the missing slot (installation-level detail) and the reason it will not close here.

### Tempting but wrong

- Materialize a presence for 'the inland transfer network' - one un-locatable pseudo-site that then collects every fleet-level claim and can never be confirmed or refuted by imagery.
- Mint a national-level formation ('the utility's transfer force') so the holding has an instance endpoint. That is an organizational individual nobody sourced.
- Read the holding as evidence for whichever presences of the design already exist, and back-fill their operator slots from it. A country fielding a type is not a statement about any particular sighting.

### Negative gold — spans that must produce NO claim

- The Annex 2 cross-reference asserts nothing.
- 'Fleet-wide throughput and availability figures' - no figure is given, so no attribute.

**Corpus.** EXERCISABLE. The corpus has several genuine holding statements (an operator 'continues to field' a design; an operator 'is believed to operate' a design) and it also has the exact area-of-responsibility trap - places named only as sectors, belts and provinces, which the ontology already had to grow a refinement to keep out of the site lane.

---

# Shape 3 — Presence vs formation (four sub-cases)

---

## `F3a-bare-sighting-presence-only`

**Purpose.** A bare equipment sighting at a site: presence only, never a formation - and the source itself states that the organizational evidence does not exist.

**Why it is hard.** A count plus a site plus a cabinet reads like an establishment, and the temptation to name the body is strongest exactly where the evidence for it is weakest. The fixture also supplies the second half of the non-negotiable - a next revisit date - so a gap here has both halves available and there is no excuse for an unnamed one.

**Scope items:** 3 (presence never forces a formation); 6 (named gap) · **refs:** spine/13 §3a; D-13.13/D-13.14; G15 amended (regression clause)

### Documents

**`survey-E`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-03

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 03 May 2025, single pass

Four skid units and one control cabinet are visible on the east pad. The perimeter berm and
access spur are unchanged from the previous pass.

No unit markings or signage are visible in any pass of this site to date. Site identity rests
on prior open association rather than on any establishment document. Next scheduled revisit:
17 May 2025.
```

### What the extractor emitted

An instance-layer sighting from the design to the site, with a count.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| four skid units and one control cabinet on the east pad | **instance** | the presence |
| no unit markings or signage visible in ANY pass to date | **gap** | a stated absence across the whole collection history, not just this pass |
| site identity rests on prior open association, not on an establishment document | **gap** | the source disclaiming its own organizational basis |
| next scheduled revisit 17 May 2025 | **gap** | the 'when next coverage is due' half of a gap |

### Discriminators

- **operator** — ABSENT
- **geography** — STATED as a named station, no coordinates
- **designation** — EXPLICITLY DECLARED ABSENT across the entire pass history
- **time** — STATED exactly (2025-05-03)

### Required outcome (prose — choose your own mechanism and values)

One presence at Hollowmere with a sourced count, and no formation of any kind. The absence of organizational evidence must become a named gap - naming the unfilled slot (which body, if any, operates this plant), the reason it is unfilled (no markings in any pass; identity rests on prior association), and the next coverage date the source supplies. A system that produces a presence and says nothing about the missing body has passed the letter of 'no formation' and failed the mission, because the analyst is not told that the order-of-battle question is open.

### Tempting but wrong

- Derive a basing for 'the Hollowmere section' or 'the resident detachment' - a body assembled out of the site's own name. This is fabrication with a plausible-sounding subject.
- Promote the presence to a formation because it has a count. A count is a property of equipment; an organization is a different kind of thing.
- Produce the presence silently, with no gap. The source stated the absence explicitly, so failing to carry it is losing evidence the document actually contains.
- Read 'unchanged from the previous pass' as a second, corroborating observation. It is this desk's own comparison against its own earlier pass.

### Negative gold — spans that must produce NO claim

- The berm and access spur being unchanged asserts continuity of the site, not of any body.
- 'Site identity rests on prior open association' must not be read as a site-to-design claim.

**Corpus.** EXERCISABLE, strongly - this is the corpus's most common shape, and one corpus document states the marking absence across its whole pass history in almost these words. The corpus also supplies a stated non-disclosure policy, so the 'will not close' reason is real data.

---

## `F3b-formation-earned-derived-basing-two-premises`

**Purpose.** A sighting PLUS organizational evidence tying the equipment to a NAMED body: a formation is earned, and a derived basing edge is materialized citing two premise claims. This is also the non-vacuous input G17 needs, because it makes the derived branch actually execute.

**Why it is hard.** The derivation is sound and still weaker than it looks, and the fixture is built so that weakness is visible: neither document says the equipment SEEN at Hollowmere is the equipment TAKEN ON CHARGE by the 7th Transfer Section. Both name only the design, so the premise chain runs through the design layer. A derivation that presents its conclusion at the confidence of its premises is over-claiming, and a derivation that hides the design-mediated step is unauditable.

**Scope items:** 3 (formation earned); 4 (basing as a rebuild-derived edge) · **refs:** spine/13 §5.3; D-13.6; G17 extended (non-vacuous fixture); acceptance: a derived based-at cites its two premise claim-atoms and mints nothing

### Documents

**`survey-E`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-03

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 03 May 2025, single pass

Four skid units and one control cabinet are visible on the east pad. The perimeter berm and
access spur are unchanged from the previous pass.

No unit markings or signage are visible in any pass of this site to date. Site identity rests
on prior open association rather than on any establishment document. Next scheduled revisit:
17 May 2025.
```

**`bulletin-F`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-04-20

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 09/2025
Dated: 20 April 2025

TL-40 transfer plant has been taken on charge by the 7th Transfer Section.

The Section's location is not published, in keeping with standing practice on establishment
detail.
```

### What the extractor emitted

From the survey: an instance-layer sighting (design at site). From the bulletin: an organizational relation (design taken on charge by a named body). No document emits a basing.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| four skid units at Hollowmere on 2025-05-03 | **instance** | premise 1 - the sighting |
| TL-40 plant taken on charge by the 7th Transfer Section (2025-04-20) | **instance** | premise 2 - the organizational evidence that earns a formation |
| the Section's location is not published | **gap** | a stated policy withholding exactly the fact the derivation is substituting for |
| neither document says the sighted plant IS the plant on charge | **derivation weakness** | the premise link is design-mediated and must remain visible |

### Discriminators

- **operator** — STATED (Northern Grid Works, in the bulletin)
- **geography** — STATED for the sighting only; the bulletin gives no location
- **designation** — STATED ('7th Transfer Section') - the only fixture pair where the top rung of the ladder has data
- **time** — STATED exactly on both (2025-05-03 sighting, 2025-04-20 bulletin)

### Required outcome (prose — choose your own mechanism and values)

A formation is earned - a named body now exists as an organizational individual - and a derived basing edge is materialized between it and the site. That edge must cite BOTH premises, so one click reaches the sighting and one reaches the bulletin; it must be marked as derived rather than stated; it must carry lower confidence than either premise, and must not be promotable to the status a stated basing can reach; and it must be materialized fresh on each rebuild without any claim being minted or appended. The design-mediated step must be inspectable, and the bulletin's withheld location should surface as the gap the derivation is standing in for. Two rebuilds of the same inputs must produce the same edge.

### Tempting but wrong

- Emit the derived basing as though a source stated it - one flat basing assertion at full source credibility. The two premises then disappear and an inference is indistinguishable from an observation.
- Cite only the sighting (or only the bulletin). A single-premise citation is not traceable to the reasoning that produced the edge.
- Mint the derived basing as a claim and append it to the evidence log during the rebuild. That puts a reversible, config-dependent decision into the immutable record, and it is exactly the append G17 forbids.
- Let the derived basing corroborate the sighting. They are not two sources; one is computed from the other.
- Allow the derived edge to reach the same status a stated, independently corroborated basing can reach.

### Negative gold — spans that must produce NO claim

- 'in keeping with standing practice' is the reason for a gap, not a fact about the Section.
- The Section's existence is stated; its location is not, and must not be back-filled from the sighting as though stated.

**Corpus.** PARTIALLY EXERCISABLE, and this is the corpus's largest hole. The corpus has the two premises as separate shapes (equipment-at-a-site sightings, and one induction into a named-ARM body) but the induction names no numbered body, so the derived basing has no designation to attach to. The designation rung of the discriminator ladder has zero data anywhere in the corpus.

---

## `F3c-stated-basing-good-source`

**Purpose.** A STATED formation-at-site from a good-grade source: it binds the formation directly, at normal source credibility, with no premise pair and no derivation.

**Why it is hard.** Not hard to read - hard because it exists nowhere in the frozen corpus, so every code path that handles it is unexercised, and three comments in the running config still assert that no source states basing. A system built only against the corpus will treat this document as an anomaly and either re-lane it into a sighting or route it through the derivation machinery it does not need.

**Scope items:** 3 (formation citizen, stated path) · **refs:** spine/13 §5.3 'two provenance paths'; acceptance: a stated based-at binds a formation directly

### Documents

**`bulletin-G`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-02-06

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 03/2025
Dated: 06 February 2025

The 3rd Transport Company is based at Site K-4 (depot), where it has been established since
2019. The Company's transfer plant is maintained under depot arrangements at the same site.
```

### What the extractor emitted

A basing relation from a named body to a named site, directly.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| the 3rd Transport Company is based at Site K-4 | **instance** | a stated formation-at-site - the formation citizen, stated rather than derived |
| Site K-4 is a depot | **instance** | the site kind, stated - the discriminator shape 6 turns on |
| established since 2019 | **instance** | a start time for the basing, stated |
| plant maintained under depot arrangements at the same site | **instance** | a second, weaker organizational statement about the same pair |

### Discriminators

- **operator** — STATED (Northern Grid Works, the bulletin's own publisher)
- **geography** — STATED as a named site WITH a stated site kind
- **designation** — STATED ('3rd Transport Company')
- **time** — STATED as a start year (2019) plus the bulletin date (2025-02-06)

### Required outcome (prose — choose your own mechanism and values)

The formation binds to the site directly, as a stated observation rather than an inference: no premise pair is required, the derivation machinery must not be involved, and the edge runs through ordinary source credibility so that an independent second source naming the same body at the same site can carry it to the corroborated end of the scale. The stated site kind must be captured, because shape 6 needs it. The publisher is the operator itself, which is a bias to record - an interested party is authoritative about its own establishment and is not a second opinion on it.

### Tempting but wrong

- Re-lane the stated basing into an equipment sighting because 'sources do not state basing'. That downgrades a directly stated organizational fact into a weaker one and loses the formation.
- Route it through the derivation and demand two premises, so the strongest available basing evidence in the whole set is capped like an inference.
- Treat the second sentence ('plant maintained under depot arrangements at the same site') as an independent corroboration. It is the same source, the same paragraph, one origin.
- Take the operator's own bulletin as unbiased simply because it is well-graded.

### Negative gold — spans that must produce NO claim

- 'under depot arrangements' asserts a maintenance arrangement, not a second basing.

**Corpus.** NOT EXERCISABLE AT ALL. Verified independently: across all 52 scenario documents there is exactly one stated formation-at-site basing, and it belongs to an off-subject chaff unit in another country planted as a designator-collision decoy. Every basing in the answer key is annotated 'derived'. This fixture is the only place the acceptance criterion can be tested.

---

## `F3d-stated-basing-low-grade`

**Purpose.** The same stated formation-at-site, asserted by a grade-E anonymous account, dated later than F3c and naming a different site. Stated still runs through source grade - and the pair is a candidate relocation from the weakest source available.

**Why it is hard.** It is textually the strongest kind of statement in the whole set - a named body, a named site, no hedging - and the weakest kind of evidence. A pipeline that treats 'stated' as a licence rather than as a class of claim will bind it exactly as it binds F3c. Worse, because it post-dates F3c and names a different site, the ordinary machinery for a moved body will read the pair as a relocation and, if it promotes, will retire a well-sourced basing on the authority of an anonymous post.

**Scope items:** 3 (stated is not trusted); 7 (supersede over an unearned identity) · **refs:** spine/13 §5.3 'stated != trusted'; R1.4; D1

### Documents

**`bulletin-G`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-02-06

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 03/2025
Dated: 06 February 2025

The 3rd Transport Company is based at Site K-4 (depot), where it has been established since
2019. The Company's transfer plant is maintained under depot arrangements at the same site.
```

**`post-H`** — forum post · **grade:** E · **bias:** anonymous, flagged for deception risk · **dated:** 2025-05-30

```text
POST - @corridor_whispers (account created 2025-05, 41 followers)
Date: 2025-05-30
Text: "everyone knows the 3rd Transport Coy sits at Hollowmere now. moved months ago. not
saying more. trust me" 
```

### What the extractor emitted

A second basing relation for the same named body, to a different site, at a later date.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| the 3rd Transport Coy sits at Hollowmere now | **instance** | a stated basing, from a grade-E anonymous account with no history |
| 'moved months ago' | **instance** | an unsourced relocation assertion with no origin and no date |
| 'not saying more. trust me' | **credibility** | an explicit refusal to source, which is the decisive credibility fact here |

### Discriminators

- **operator** — ABSENT from the post
- **geography** — STATED as a bare site name, no site kind, no coordinates
- **designation** — STATED, in an abbreviated surface ('3rd Transport Coy')
- **time** — STATED for the post (2025-05-30); the claimed move is 'months ago', i.e. unusable

### Required outcome (prose — choose your own mechanism and values)

The claim must be recorded, attributed, and must land far short of where F3c's grade-B stated basing lands - the difference between them must come from the source grade and the refusal to source, not from one being 'stated' and the other not, because both are stated. It must not retire, supersede or contradict the well-sourced basing on its own, and it must not be discarded either: the honest output is an unresolved question held for the analyst, carrying the reason. The abbreviated designation surface should reach the same body as F3c's - that much is a reading, not a judgement - but the identity of the body is the only thing this post contributes.

### Tempting but wrong

- Wave it through because a source stated it. 'Stated' is a provenance class, not a credibility grade.
- Promote the pair to a relocation because the post is newer and the sites differ. A relocation drawn on a grade-E anonymous post, retiring a grade-B establishment bulletin, is the failure this fixture exists to catch.
- Drop the post as junk. It names a body and a site; it belongs in the record as an attributed claim with its grade and its refusal-to-source visible.
- Read 'moved months ago' as a dated relocation. There is no origin and no date.

### Negative gold — spans that must produce NO claim

- Follower count and account age are provenance metadata, not claims.
- 'trust me' asserts nothing about the world.

**Corpus.** EXERCISABLE for the credibility half - the corpus has a grade-E relocation spoof and a grade-D social sighting, and the supersede floor was built against them. NOT exercisable for the stated-basing half, because neither spoof names a formation: they name equipment. So the corpus can test 'a low-grade relocation claim must not promote' but not 'a low-grade STATED BASING must not promote'.

---

# Shape 4 — The count trap (k reports != k launchers)

---

## `F4-count-trap-reports-are-not-launchers`

**Purpose.** Five reports of the same equipment at the same site, of which three state no number at all. The naive count equals the number of reports - and it is wrong twice, in two different ways, both of which look plausible.

**Why it is hard.** Two coincidences are engineered in. Before 21 May there are exactly three count-silent reports, so a report-counting implementation says three - a perfectly plausible number of skids, asserted by nobody. After 2 June there are five reports, and five sits inside the only stated range, so the wrong answer now looks corroborated by the source that actually gave a figure. There is no point at which the naive answer looks absurd.

**Scope items:** 3 (count is a sourced attribute, default unknown) · **refs:** spine/13 §3a; D-13.13; D-13.19 (count capture)

### Documents

**`survey-J`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-04

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 04 May 2025

Skid units are present on the east pad. Individual units are not resolvable at this ground
sample distance; a count is not established by this pass.
```

**`press-K`** — trade press item · **grade:** C · **bias:** third-party trade press · **dated:** 2025-05-09

```text
Transfer Plant Reported Back at Hollowmere
Staff correspondent - 9 May 2025

A recent survey is understood to show transfer plant on the pad at Hollowmere. Neither the
operator nor the surveyor would comment on numbers.
```

**`post-N`** — forum post · **grade:** D · **bias:** hobby spotting account · **dated:** 2025-05-14

```text
POST - @pad_watch
Date: 2025-05-14
Text: "plant is back on the pad at Hollowmere, drove past and saw it myself. no idea how many,
couldn't stop." 
```

**`survey-L`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-21

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 21 May 2025

Six skid-pattern units are visible in a fan arrangement on the east pad.
```

**`survey-M`** — aerial survey digest · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-06-02

```text
SURVEY DIGEST - HOLLOWMERE FORWARD STATION
Issue dated 02 June 2025

Plant strength at the east pad is estimated at four to six skid units plus one cabinet. The
desk's confidence in the upper bound is low, given intermittent visibility across passes.
```

### What the extractor emitted

Five instance-layer sightings of the same design at the same site, on five dates, from four distinct publishers. Two carry a figure; three carry none.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| 'a count is not established by this pass' (2025-05-04, grade B) | **instance** | a report with an explicitly declared absent count |
| 'neither would comment on numbers' (2025-05-09, grade C) | **instance** | a second count-silent report, and a stated reason it is silent |
| 'no idea how many' (2025-05-14, grade D) | **instance** | a third count-silent report |
| 'six skid-pattern units are visible' (2025-05-21, grade B) | **instance** | the first and only point figure - a sourced count |
| 'estimated at four to six ... confidence in the upper bound is low' (2025-06-02, grade B) | **instance** | a second, RANGED figure whose own upper bound the source distrusts |

### Discriminators

- **operator** — ABSENT from all five
- **geography** — STATED as one named site and one named pad across all five - they are about the same place
- **designation** — ABSENT from all five
- **time** — STATED exactly on each, spanning 2025-05-04 to 2025-06-02

### Required outcome (prose — choose your own mechanism and values)

The count must come only from the two reports that state a figure, and each must remain its own dated, sourced claim: an observed point figure on one pass, and a range on a later pass whose upper bound its own author distrusts. Before the first figure arrives the count is unknown, and 'unknown' must be representable and shown as such - an unfilled slot, not a number. The number of reports must never reach the count under any code path. The two figures do not have to be reconciled; they are two dated observations of a thing that can genuinely change, and if they are reconciled at all it must be visibly, with both retained. Note also that five reports here are four publishers, one of which is reporting another's survey - so report multiplicity is not corroboration multiplicity either.

### Tempting but wrong

- count = number of merged reports (three, then five). Both values are plausible skid counts and one falls inside the stated range, so the bug is invisible in review and invisible on the surface.
- count = max of the stated figures, or the midpoint of the range. Both invent precision the sources refuse; the range's own author says the upper bound is not to be trusted.
- Take the newest figure and drop the older, so a range with a distrusted bound silently replaces a clean point observation.
- Default the count to one because something was seen. A default that asserts a number where no source gave one is the same failure as the report count, in smaller print.
- Treat the trade-press item as a fifth independent observation. It reports a survey rather than making one.

### Negative gold — spans that must produce NO claim

- 'plant on the pad' with no number contributes no count, only a presence.
- The drive-past post contributes no count and no geolocation.

**Corpus.** PARTIALLY EXERCISABLE, better than expected. The corpus does carry structured sourced counts with min/max/approx on sighting events, and it has two reports of one site giving different figures, plus a document that states a count is unverifiable this pass. What it does NOT supply is the coincidence: nowhere does the number of reports collide with a plausible equipment count, so the naive implementation is never punished on the corpus. That collision has to be authored, and it is the whole point of this fixture.

---

# Shape 5 — The D2 case - two candidate formations for one sighting

---

## `F5a-two-candidate-formations-equal-evidence`

**Purpose.** One sighting, two separately named candidate formations, equally evidenced, neither tied to the site. The correct outcome is two attributions, or one plus an explicitly named gap. Never a silent pick.

**Why it is hard.** There is no merge anywhere in this shape, which is why it is invisible to every gate that watches identity. Nothing is over-merged and nothing is mis-scored; a candidate is simply dropped, and an order-of-battle undercount is the least visible error a system of this kind can make, because the output looks confident and complete. Both bulletins are the same publisher, the same grade and the same form, so there is no defensible tie-break available - which is the point.

**Scope items:** 6 (the D2 clause - no silent formation pick) · **refs:** D2; R2.1; G15 amended (the clause that bites)

### Documents

**`survey-L`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-21

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 21 May 2025

Six skid-pattern units are visible in a fan arrangement on the east pad.
```

**`bulletin-Q`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-03-02

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 05/2025
Dated: 02 March 2025

TL-40 transfer plant has been taken on charge by the 7th Transfer Section. No location is
published.
```

**`bulletin-R`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-04-11

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 08/2025
Dated: 11 April 2025

TL-40 transfer plant has been issued to the 12th Transfer Section. No location is published.
```

### What the extractor emitted

One sighting (design at site) and two organizational relations (design to two different named bodies). No document links either body to the site.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| six skid units at Hollowmere on 2025-05-21 | **instance** | the single sighting |
| TL-40 plant taken on charge by the 7th Transfer Section (2025-03-02) | **instance** | candidate formation 1 - no site stated |
| TL-40 plant issued to the 12th Transfer Section (2025-04-11) | **instance** | candidate formation 2 - no site stated, same publisher, same grade, same form |
| nothing states which body's plant was seen at Hollowmere | **gap** | the missing slot that makes both attributions candidates rather than facts |

### Discriminators

- **operator** — STATED and IDENTICAL for both candidates - so operator cannot separate them
- **geography** — STATED for the sighting only; ABSENT for both candidates
- **designation** — STATED and DIFFERENT for the two candidates - the only thing that distinguishes them, and it distinguishes them completely
- **time** — STATED on all three; the two bulletins are six weeks apart and neither is superseded

### Required outcome (prose — choose your own mechanism and values)

Both candidates must survive the build. Either two attributions are recorded, each flagged as competing with the other and neither treated as settled, or one is recorded and the second is named in a gap that says a second candidate formation exists, identifies it, and says why it was not attributed. A truncation that records nothing is the defect. Whatever is emitted must be traceable back to the discarded or demoted candidate, because the analyst's question here is precisely 'is this one section or two?' - and the two differing designations are, on this evidence, the strongest reason to believe the answer is two.

### Tempting but wrong

- Keep the 'best-evidenced' candidate and drop the other with no record. Every other rejection path in this area records a reason; this one is silent, which makes it the one an audit cannot find.
- Merge the two Sections into one formation because they share an operator, a design and a site neighbourhood. They differ on the one discriminator that separates organizations, and merging them also gives them one basing instance - which is how shape 7's harm becomes reachable from here.
- Pick the newer bulletin as 'current' and treat the older as superseded. Nothing says the plant left the 7th Section; two issues can both be true, and an issue-and-transfer would be a third claim nobody made.
- Attribute the sighting to both and present the result as two confirmed basings. Two attributions must be two candidates, not two facts.

### Negative gold — spans that must produce NO claim

- Neither bulletin states a location; the site must not be back-filled onto either body.
- Bulletin sequence numbers are provenance, not evidence of supersession.

**Corpus.** NOT EXERCISABLE. Verified: the corpus has no two individuated same-type formations anywhere. Its nearest approaches are a cardinality without individuation ('two operational battalions' - one claim with a quantity, not two referents) and three documents that gesture at extra formations without naming any. This is the shape the gate most needs and the corpus most completely lacks.

---

## `F5b-two-candidate-formations-unequal-evidence`

**Purpose.** The same two-candidate shape, but the second candidate is asserted by a grade-E anonymous account. Grading it down is correct; deleting it is not.

**Why it is hard.** This variant is where a correct-looking implementation goes wrong, because here there IS a defensible tie-break - the grades differ - and 'pick the better-evidenced one' produces the right attribution by the wrong mechanism. The distinction the fixture tests is between a candidate that was weighed and demoted with its reason visible, and one that vanished. Only the first can be revisited when a better source arrives.

**Scope items:** 6 (the D2 clause - demotion is not deletion) · **refs:** D2; R2.1

### Documents

**`survey-L`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-05-21

```text
AERIAL SURVEY EXTRACT - HOLLOWMERE FORWARD STATION
Collected 21 May 2025

Six skid-pattern units are visible in a fan arrangement on the east pad.
```

**`bulletin-Q`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-03-02

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 05/2025
Dated: 02 March 2025

TL-40 transfer plant has been taken on charge by the 7th Transfer Section. No location is
published.
```

**`post-S`** — forum post · **grade:** E · **bias:** anonymous, flagged for deception risk · **dated:** 2025-04-11

```text
POST - @grid_leaks (no posting history before 2025-04)
Date: 2025-04-11
Text: "TL40 plant went to 12 Transfer Section, heard it from someone inside. no docs sorry" 
```

### What the extractor emitted

One sighting and two organizational relations, one grade B and one grade E, naming different bodies.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| six skid units at Hollowmere on 2025-05-21 | **instance** | the single sighting |
| plant taken on charge by the 7th Transfer Section (grade B) | **instance** | candidate 1 |
| 'TL40 plant went to 12 Transfer Section, heard it from someone inside. no docs sorry' (grade E) | **instance** | candidate 2 - same claim shape, weakest possible evidence, explicit refusal to source |

### Discriminators

- **operator** — STATED for candidate 1; ABSENT for candidate 2
- **geography** — ABSENT for both candidates
- **designation** — STATED and DIFFERENT
- **time** — STATED on both; the weak claim is the later one

### Required outcome (prose — choose your own mechanism and values)

The strong candidate carries the attribution and the weak one is demoted rather than deleted: it stays in the record as an attributed claim, with its grade and its refusal to source visible, and it is named in the gap or the competing-candidate list so that a later corroborating source can revive it rather than having to rediscover it. The reason for the demotion must be the source grade, stated as such - not the fact that a cap on candidates happened to keep the first one.

### Tempting but wrong

- Delete the weak candidate because it is weak. The right answer arrives with no audit trail, and the implementation is now indistinguishable from the one that silently truncates - it just happens to be sorted correctly today.
- Give the weak claim an attribution of its own with equal standing, on the grounds that no silent pick is allowed. 'Never a silent pick' is not 'never a graded judgement'.
- Let the later date beat the better grade.

### Negative gold — spans that must produce NO claim

- 'heard it from someone inside' is an assertion of access, not of fact.
- 'no docs sorry' asserts nothing and is a credibility fact.

**Corpus.** NOT EXERCISABLE, for the same reason as F5a - no two individuated formations exist. The grade-E-anonymous-source half is well represented in the corpus; the two-candidate half is not present at all.

---

# Shape 6 — site_type de-confliction (C1) - stated, absent, and drifting

---

## `F6a-site-type-deconfliction-stated`

**Purpose.** One named formation, concurrently at a depot and at a forward station, both site kinds stated by the same good-grade source. Two valid basings - no relocation, no contradiction, no wall.

**Why it is hard.** Every generic signal says relocation: one body, two sites, overlapping times, the later mention newer than the earlier. The only thing that says otherwise is that the two places are different KINDS of place, which is a semantic fact about sites and not a property of the basing pair at all. And the same declaration has to serve two opposite purposes - it must stop this pair being read as a relocation, while still letting two candidate bodies at two depots at overlapping times be read as different bodies.

**Scope items:** 5 (based-at supersede key tagged by site_type) · **refs:** R1.3; C1; G18 under C1's rule

### Documents

**`bulletin-T`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-04-14

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07/2025
Dated: 14 April 2025

The 3rd Transport Company, whose home depot is Site K-4 (depot), has maintained a detachment
at Hollowmere forward station (forward station) since 14 April. Both the depot establishment
and the detachment remain current as at the date of this bulletin.
```

### What the extractor emitted

Two basing relations for one named body, to two sites, with overlapping validity, each site carrying a stated kind.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| 3rd Transport Company's home depot is Site K-4 (depot) | **instance** | basing 1, with a stated site kind |
| 3rd Transport Company has maintained a detachment at Hollowmere forward station (forward station) since 14 April | **instance** | basing 2, with a stated and DIFFERENT site kind |
| 'both ... remain current as at the date of this bulletin' | **instance** | the source stating concurrency in its own voice - the fixture's licence |

### Discriminators

- **operator** — STATED (the bulletin's publisher)
- **geography** — STATED for both sites, each WITH a site kind
- **designation** — STATED, one body
- **time** — STATED and OVERLAPPING - the source says both are current

### Required outcome (prose — choose your own mechanism and values)

Two live basings for one formation, both retained, with no relocation drawn, no supersession, and no contradiction recorded. The de-confliction must rest on the site kind, so that the same rule still fires the other way for two bodies at two places of the SAME kind at overlapping times. The word 'detachment' should not create a second formation - it is the same body present in two places, which is what a forward detachment is.

### Tempting but wrong

- Read it as a relocation from the depot to the forward station, retire the depot basing, and draw a move the source explicitly denies by saying both remain current.
- Wall the two as different bodies, on the reasoning that one body cannot be at two places at overlapping times. That is the over-read the site-kind rule exists to prevent, and it splits a correctly identified formation in half.
- Mint a separate 'detachment' formation so each basing has its own subject. The graph now shows two bodies where the source describes one, and the order of battle is over-counted.
- Record a contradiction and route it to the analyst as a conflict. There is no conflict; there is a concurrency the source states.

### Negative gold — spans that must produce NO claim

- The bulletin number and date are provenance.
- 'since 14 April' dates the detachment's start, not the depot basing's end.

**Corpus.** NOT EXERCISABLE. No corpus document places one body at two sites concurrently - the ontology comment itself rests the current unit-only keying on that absence, which is precisely the kind of design input this stage is forbidden to accept.

---

## `F6b-site-type-absent`

**Purpose.** The same two-site, one-body shape with NO site kind stated anywhere. Absent must not de-conflict.

**Why it is hard.** The evasion direction here is over-merge, and absence is the cheapest way to reach it: if an unstated site kind reads as its own bucket, then every pair whose sites are undescribed becomes two happy concurrent basings and no relocation ever fires again - including a real one. The failure is silent, global, and looks like tidiness.

**Scope items:** 5 (state the absent site_type default and fail safe) · **refs:** R1.3; C1; plan §7 item 5

### Documents

**`bulletin-U`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-02-06

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 03B/2025
Dated: 06 February 2025

The 3rd Transport Company is at Site K-4.
```

**`bulletin-V`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-04-14

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07B/2025
Dated: 14 April 2025

The 3rd Transport Company is at Hollowmere.
```

### What the extractor emitted

Two basing relations for one named body, two sites, two dates, no site kind on either.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| 3rd Transport Company is at Site K-4 (2025-02-06) | **instance** | basing 1, no site kind stated |
| 3rd Transport Company is at Hollowmere (2025-04-14) | **instance** | basing 2, no site kind stated |
| no source states what kind of place either site is | **gap** | the missing slot the de-confliction rule needs, and the reason this pair cannot be resolved either way |

### Discriminators

- **operator** — STATED (same publisher for both)
- **geography** — STATED as bare site names, NO site kind, no coordinates
- **designation** — STATED, one body
- **time** — STATED, and it is genuinely ambiguous whether the two intervals overlap - neither states an end

### Required outcome (prose — choose your own mechanism and values)

Absent site kind must read as unknown, and unknown must not license 'two valid basings'. The pair has to land on the safe side: either the pair is treated as one basing instance in question - a relocation-or-two-basings that the analyst is asked about - or the build refuses to key it at all and says so. What it must not do is quietly conclude that the two sites are different kinds of place and therefore compatible. The missing slot must be named, and the fact that neither basing states an end date is part of why the question is open.

### Tempting but wrong

- Treat unknown as its own bucket, so absent site kinds always de-conflict. Every relocation in the system silently stops firing, and the more sparsely described the source, the more confident the wrong answer.
- Infer the site kind from the site's NAME ('Site K-4 sounds like a depot'). That is fabricating the discriminator the rule turns on.
- Fall back to the pre-existing behaviour and draw the relocation, on the grounds that unknown means 'nothing to de-conflict on'. Defensible-sounding, but it asserts a move on no evidence of one; the honest outcome is a question, not either answer.

### Negative gold — spans that must produce NO claim

- Neither bulletin says the Company left anywhere.

**Corpus.** EXERCISABLE for the absence itself - site kind is missing on a substantial share of corpus site mentions, and one corpus site appears three times in ONE document with the kind present once and absent twice. Not exercisable as a one-body-two-sites pair, for the same reason as F6a.

---

## `F6c-site-type-vocabulary-drift`

**Purpose.** Site kind IS stated on every mention - in different words for the same kind of place, by different publishers. A raw-string key puts one site in two buckets and two different kinds of place in what looks like one.

**Why it is hard.** This is the variant that breaks a working relocation in production rather than in theory. The site kind is free text: the same depot is 'depot' to its operator and a 'logistics and storage establishment' to a register, and the same forward pad is 'forward station' to one and a 'prepared forward pad / field station' to the other. Keying on the stated string is defensible, deterministic, and wrong in both directions at once - it de-conflicts pairs that should not, and it splits one site into two buckets so that a genuine move between two differently-described places quietly stops being a move.

**Scope items:** 5 (based-at supersede key tagged by site_type) · **refs:** R1.3; C1; value normalization (resolution.yaml)

### Documents

**`bulletin-G`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-02-06

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 03/2025
Dated: 06 February 2025

The 3rd Transport Company is based at Site K-4 (depot), where it has been established since
2019. The Company's transfer plant is maintained under depot arrangements at the same site.
```

**`register-W`** — curated establishment register · **grade:** B · **bias:** third-party curated register · **dated:** 2025-02-20

```text
REGIONAL WORKS ESTABLISHMENT REGISTER - extract, 20 February 2025

Site K-4 - logistics and storage establishment. Resident body: 3rd Transport Company.
```

**`bulletin-T`** — operator establishment bulletin · **grade:** B · **bias:** operator of the asset · **dated:** 2025-04-14

```text
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07/2025
Dated: 14 April 2025

The 3rd Transport Company, whose home depot is Site K-4 (depot), has maintained a detachment
at Hollowmere forward station (forward station) since 14 April. Both the depot establishment
and the detachment remain current as at the date of this bulletin.
```

**`register-X`** — curated establishment register · **grade:** B · **bias:** third-party curated register · **dated:** 2025-04-24

```text
REGIONAL WORKS ESTABLISHMENT REGISTER - extract, 24 April 2025

Hollowmere - prepared forward pad / field station. Detachment present: 3rd Transport Company.
```

### What the extractor emitted

Basing relations for one body across two sites, where each site's kind is stated twice, in two different vocabularies.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| Site K-4 (depot) - operator's bulletin | **instance** | site kind, vocabulary 1 |
| Site K-4 - logistics and storage establishment - register | **instance** | the SAME site, the same kind of place, a different surface string |
| Hollowmere forward station (forward station) - operator's bulletin | **instance** | site kind, vocabulary 1 |
| Hollowmere - prepared forward pad / field station - register | **instance** | the SAME site, the same kind of place, a different surface string |

### Discriminators

- **operator** — STATED
- **geography** — STATED, with the site kind present on every mention and spelled differently on every publisher
- **designation** — STATED, one body
- **time** — STATED across February to April 2025

### Required outcome (prose — choose your own mechanism and values)

De-confliction must survive the vocabulary: the two descriptions of the depot must land in the same bucket as each other, the two descriptions of the forward pad likewise, and the depot and the forward pad must land in different buckets. Where a stated kind cannot be mapped confidently to a known class, the pair must fall to the safe side of shape 6b rather than being de-conflicted on an unrecognised string. Whatever mapping is used has to be editable data rather than a literal in code, because this vocabulary is open-ended and every new publisher adds to it.

### Tempting but wrong

- Key on the raw stated string. One site becomes two buckets, so a real relocation between two differently-described places is recorded as two concurrent basings and the move is never surfaced. This is the failure mode that would silently retire a working relocation beat.
- Normalize by string similarity, so 'logistics and storage establishment' and 'prepared forward pad / field station' - which share no meaning - are separated correctly by luck, while 'forward station' and 'field station' are conflated or separated by token overlap rather than by kind.
- Take the operator's vocabulary as canonical because it is the operator. It is one publisher's wording, and the register's is just as stated.

### Negative gold — spans that must produce NO claim

- The register is a curated third party; its agreement about a site's KIND is not corroboration of the body being there.

**Corpus.** EXERCISABLE, and already live in the frozen data - this is a verified corpus fact, not a hypothetical. Site kinds in the corpus are free text with no enumeration: the same airfield is described two different ways by two documents, and the two ends of the flagship relocation carry entirely different kind strings. A raw-string key would put them in different buckets. See the findings note; this is the highest-value corpus-grounded item in this set.

---

# Shape 7 — The D1 tail - supersede over a sub-confirmed identity, and its earned mirror

---

## `F7a-supersede-over-subconfirmed-identity`

**Purpose.** Two anonymous presences that a co-location-friendly scorer wants to fuse, whose fusion turns two site edges into one body's before-and-after, promoting a relocation the analyst is never asked about - and deleting the named gap that said the identity was unresolved.

**Why it is hard.** No component lies and no source is planted. Two real, well-graded surveys of two real, similar, nearby installations are enough. Every signal that normally means 'same thing' is present - same design, same operator, same region, near-identical descriptions - and the one signal that would separate them, a body designation, is stated absent on both. The harm is not the merge; it is what the merge unlocks downstream, and it arrives as a positively-asserted movement claim with the human removed. The second half is subtler: an honest 'insufficient evidence' attached to the older edge becomes 'stale' when the edge is retired, so the gap that documented the uncertainty is destroyed by the act that depended on it.

**Scope items:** 7 (R1.4 - the supersede must not remove the analyst over an unearned identity) · **refs:** D1; R1.1; R1.2; R1.4; G16 amended

### Documents

**`survey-Y1`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-01-18

```text
AERIAL SURVEY EXTRACT - CALDER APRON
Collected 18 January 2025

A group of TL-40 skid-pattern units and one cabinet are visible on the apron. Operator assessed
as Northern Grid Works from the access-road markings. No body designation is visible.
```

**`survey-Y2`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-03-27

```text
AERIAL SURVEY EXTRACT - REDLOW APRON
Collected 27 March 2025

A group of TL-40 skid-pattern units and one cabinet are visible on the apron, in a fan
arrangement. Operator assessed as Northern Grid Works from the access-road markings. No body
designation is visible. Redlow lies approximately 11 km from the Calder apron.
```

### What the extractor emitted

Two sightings of the same design at two sites, on two dates, from one publisher, with an operator assessed on both and no designation on either. A named gap exists on the earlier site edge recording that the operating body is unresolved and when the next pass is due.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| TL-40 skid units and a cabinet at the Calder apron (2025-01-18) | **instance** | presence 1 |
| TL-40 skid units and a cabinet at the Redlow apron (2025-03-27), ~11 km away | **instance** | presence 2 |
| operator assessed as Northern Grid Works on both, from access-road markings | **instance** | an ASSESSED, not stated, operator - identical on both, so it pushes toward identity while being the weaker kind of evidence |
| no body designation visible at either site | **gap** | the discriminator that would settle it is stated absent on both sides |
| a named gap on the earlier edge: operating body unresolved, next coverage due | **gap** | the honest insufficient-evidence record that must survive whatever happens to the edge |

### Discriminators

- **operator** — ASSESSED (not stated) and IDENTICAL - pushes toward a merge, on the weakest available basis
- **geography** — STATED as two named aprons ~11 km apart - different places, and close enough to look like one deployment area
- **designation** — STATED ABSENT on both - so the top rung of the ladder has nothing
- **time** — STATED exactly, ten weeks apart, with no overlap and no end dates

### Required outcome (prose — choose your own mechanism and values)

The two presences must not be fused into one formation on this evidence, so no shared basing instance is created and no before-and-after pair exists to promote. If a supersession is nevertheless proposed, it must not be machine-adjudicated: the pair stays with the analyst, no relocation edge is drawn, and the credibility of the newer assertion is not allowed to stand in for the identity of its subject - the floor grades the claim, not the sameness of the two bodies. The older edge's named gap must survive intact; an unresolved identity must not be converted into a stale fact by the act of retiring the edge. The honest output is two presences, an open question about whether they are one body, and both gaps still standing.

### Tempting but wrong

- Fuse the two presences because the descriptions are near-identical and the design, operator and region all agree, then promote the resulting before-and-after because the newer survey clears the credibility floor. One identity error becomes a positively asserted movement, and the analyst is told it was adjudicated.
- Draw the relocation because the two targets differ. Differing targets are what makes the claim interesting, not what licenses it.
- Delete the retired edge's Known Gap as no longer applicable. The gap was about the identity, which is exactly what has not been established; deleting it turns an honest 'insufficient evidence' into a confident 'stale'.
- Pop the pair out of the analyst's queue as machine-adjudicated. Machine promotion is only legitimate over an identity the system actually earned, and here it earned nothing.
- Treat the assessed operator as a stated one. It is the surveyor's read of road markings.

### Negative gold — spans that must produce NO claim

- 'Operator assessed as' is an assessment, not a stated operator.
- The 11 km figure locates the two aprons relative to each other; it says nothing about whether one body occupies both.

**Corpus.** PARTIALLY EXERCISABLE. The corpus has the ingredients - two sites, one design, no designations, a relocation beat, and a supersede floor built against a low-grade spoof - but not the trap, because it contains no two co-located same-type formations to fuse. The chain from identity error to drawn relocation therefore cannot be demonstrated end to end on the frozen corpus, which is why it went unnoticed.

---

## `F7b-supersede-legitimately-earned`

**Purpose.** The same two site edges, but the identity is earned on a stated designation at both ends, by good sources, with the same site kind. The supersede should work - and must not manufacture relational evidence that the two sites are one place.

**Why it is hard.** A gate written only against F7a will forbid the machinery outright, and then a real, well-evidenced relocation - the thing the system is for - stops being detectable. This fixture is the other direction, and it also carries the trap that follows a correct relocation: once one body is linked to both sites, the two sites share a neighbour, so a scorer that reads shared neighbourhood as identity evidence will start proposing that the origin and the destination are the same place. A dated relationship to two different neighbours at two different times is not one relationship.

**Scope items:** 7 (the mirror - an earned supersede must still work); 5 (carry forward the relational mitigation) · **refs:** R1.4; D-13.6; co_instances / relational mitigation

### Documents

**`survey-Z1`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-01-18

```text
AERIAL SURVEY EXTRACT - CALDER APRON (forward station)
Collected 18 January 2025

TL-40 skid-pattern units of the 7th Transfer Section are visible on the apron; the Section's
board is legible at the gate. Northern Grid Works.
```

**`survey-Z2`** — aerial survey extract · **grade:** B · **bias:** commercial survey vendor · **dated:** 2025-03-27

```text
AERIAL SURVEY EXTRACT - REDLOW APRON (forward station)
Collected 27 March 2025

TL-40 skid-pattern units of the 7th Transfer Section are visible on the apron; the Section's
board is legible at the gate. Northern Grid Works. The Calder apron was re-imaged on the same
pass and is empty.
```

### What the extractor emitted

Two basings for one NAMED body at two sites of the same kind, on two dates, with the destination pass also re-imaging the origin and finding it empty.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| 7th Transfer Section's skid units at the Calder apron, gate board legible (2025-01-18) | **instance** | basing 1, identified by a stated designation rather than by co-location |
| 7th Transfer Section's skid units at the Redlow apron, gate board legible (2025-03-27) | **instance** | basing 2, same designation, same operator, same site kind |
| the Calder apron was re-imaged on the same pass and is empty | **instance** | a dated negative observation at the origin - the evidence that makes this a move rather than two basings |

### Discriminators

- **operator** — STATED on both, identical
- **geography** — STATED as two named aprons, both described as forward stations - the SAME site kind, so shape 6 does not de-conflict them
- **designation** — STATED and IDENTICAL on both - the identity is earned here, not assumed
- **time** — STATED exactly, with a dated vacancy at the origin on the later pass

### Required outcome (prose — choose your own mechanism and values)

The relocation should be drawn: one body, one basing instance, an earlier edge retired and a later one current, with the origin's dated vacancy supporting the move. Promotion is legitimate here because the identity rests on a stated designation at both ends rather than on the two sightings being near each other. Two things must not follow from it. First, the retired edge's gaps and provenance must remain readable - retiring an edge is not erasing its history. Second, the fact that one body is now attached to both sites must not become evidence that the two sites are the same place, or that either presence at one site is the same individual as a presence at the other: the relationship to the origin and the relationship to the destination are two dated relationships, and a re-keying that collapses them into one shared neighbour link would manufacture exactly that.

### Tempting but wrong

- Forbid the promotion because the gate learned from F7a to distrust all supersessions. The system then cannot report the one movement it has genuinely earned.
- Let the two sites merge, or become merge candidates, on the strength of their new shared unit neighbour. The relocation created that neighbour; using it as identity evidence is circular and would collapse the origin and destination of every move the system detects.
- Treat the origin's empty re-image as a contradiction of the earlier sighting. A dated vacancy after a dated presence is a change, not a conflict.
- Drop the origin basing entirely once superseded, so the order of battle loses the body's history.

### Negative gold — spans that must produce NO claim

- The gate board is the licensing evidence for the designation, not a separate claim about the site.
- 'same pass' is collection metadata; the origin's vacancy is the claim.

**Corpus.** NOT EXERCISABLE as written. The corpus's relocation beat has no designation at either end - there is no numbered body anywhere in it - so a legitimately earned supersede cannot be constructed from it. Its relocation is earned on geography and imagery alone, which is precisely the class this shape is meant to distinguish from.

---

# Shape 8 — Inexpressible sourced relations (D12's customs spine, and operator)

---

## `F8a-customs-spine-inexpressible`

**Purpose.** A customs declaration whose actual spine is event - consignee - shipper, so that the ontology gap is demonstrable rather than asserted: the relations the document states have no lane, and the relation it does not state is the one the schema offers.

**Why it is hard.** The pressure is structural, not a bug in any component. Faced with a document that states a consignee and a shipper and no military unit, an extractor scored on coverage has two ways to produce output and both are wrong: relabel the shipper as a maker so an available edge fits, or invent a recipient so another one does. A schema that makes the sourced relation inexpressible and the unsourced relation easy is not neutral - it pushes toward asserting what nobody said.

**Scope items:** 5 (ontology additions: the event-to-trading-org edge; re-examine imported-by) · **refs:** D12; spine/13 §10; plan §7 item 5

### Documents

**`customs-AA`** — inbound customs declaration extract · **grade:** C · **bias:** commercial record · **dated:** 2020-11

```text
REGIONAL PORT AUTHORITY - INBOUND DECLARATION EXTRACT
Terminal: Brightwater International Freight Terminal

DEC No: NGQA-HC-2020-204471            Filing Date: 04-11-2020
Point of Discharge: NORTHGATE HARBOUR BASIN
Waybill No: CLWW307556104

Receiver:      BRAMWELL ELECTRO TRADING (PVT) LTD - REG 5107443-9
Sender:        HALCYON IMPEX CO, LTD
Sender Ctry:   CALDONIA
Freight Fwdr:  ASHLAND CARGO SERVICES - Cert No. RG-TT-0774

Tariff Code:   9914.61.00
Description (as filed): "SENSOR APPARATUS PARTS / ELECTRONIC ASSEMBLY - SPARE, FOR INDUSTRIAL
               METERING AID, NOT FOR RESALE, 1 LOT"

Delivery instructions (broker note, handwritten annotation on file copy):
  "receiver to arrange onward clearance - final destination Plant Depot, ~14 km NNE of Kestrel
  Ridge / Ashcombe Yard area"

End-user certificate on file: NOT ATTACHED TO DEC.
```

### What the extractor emitted

An import event with a declaration reference; a consignee organization; a shipper organization; a forwarder organization; a destination from a handwritten broker note. No unit and no manufacturer appears anywhere in the document.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| declaration NGQA-HC-2020-204471 filed 04-11-2020 | **instance** | the event, identified by a hard reference |
| receiver is Bramwell Electro Trading (Pvt) Ltd, registration 5107443-9 | **instance** | a STATED relation from the event to a trading organization - and there is no edge for it |
| sender is Halcyon Impex Co, Ltd, of Caldonia | **instance** | the second STATED relation from the event to a trading organization - also with no edge |
| freight forwarder is Ashland Cargo Services, trusted-trader certificate RG-TT-0774 | **instance** | a third organization in the spine, likewise uncarriable |
| declared purpose is civil industrial metering spares, not for resale | **instance** | a STATED civil purpose; any other reading is derived and must be labelled so |
| final destination from a handwritten broker note, given only as a relative bearing from two alternative anchors | **instance** | a place claim of the weakest available kind, from an annotation |
| end-user certificate NOT attached | **gap** | a stated absence of the document that would settle end use |

### Discriminators

- **operator** — STATED only as the sender's country
- **geography** — STATED for the discharge point; RELATIVE-ONLY and doubly-anchored for the destination
- **designation** — STATED as hard identifiers for the event and the parties - the one place in this whole set where an identifier can decide identity
- **time** — STATED exactly (2020-11-04)

### Required outcome (prose — choose your own mechanism and values)

Both stated relations - event to consignee and event to shipper - must survive the build with their provenance intact, which means the schema has to be able to express them. Neither organization may be retyped as a maker to fit an available lane, and no recipient body may be invented to fit another. If nothing can carry a stated relation, the honest output is an explicitly recorded expressiveness gap naming the relation that could not be represented - never a silent drop and never a coerced edge. The declared civil purpose is what the document states; the handwritten destination is an annotation with two alternative anchors and must not become a confirmed site; and the missing end-user certificate is a gap with a named missing slot.

### Tempting but wrong

- Type the shipper as a manufacturer so the available exporter edge fits. This fabricates a design-and-manufacture relation from a document that describes a freight movement, and it does so while looking like careful schema compliance.
- Invent a recipient body - named after the depot in the broker note, or after the operator the rest of the collection talks about - so the recipient edge fits. The document names no unit at all.
- Drop both relations silently because no lane exists. That loses the only supply-chain relation the document actually states, and the loss is invisible.
- Read the goods description's stated civil purpose as cover and record a military end use. That is an inference presented as the document's content, on a document that also states no examination was performed and no end-user certificate is attached.
- Treat the handwritten destination as a site with a position, by averaging its two alternative anchors.

### Negative gold — spans that must produce NO claim

- The tariff code is a filing datum, not a statement about contents.
- The broker's handwritten note is the weakest thing in the record and must not be promoted by being the most specific.

**Corpus.** EXERCISABLE, and already true of the frozen corpus: the customs document's spine is exactly this, and it is unrepresentable today. Verified further - the trading-organization node type is named by NO edge type at all, in either direction, so a correctly typed consignee or shipper can only ever exist as an isolated node. The corpus also supplies the identifier-rich half genuinely: this is the one document where a shared hard identifier could decide an identity.

---

## `F8b-operator-relation-and-refutation-no-carrier`

**Purpose.** A stated operator RELATION and a stated REFUTATION of one, neither of which has a carrier while operator exists only as an attribute. The second shape of the same anti-fabrication hazard as F8a.

**Why it is hard.** Operator is the discriminator directly below designation in the ladder, and sources state it as a relation at least as often as they state it as an attribute. With no relation to carry it, a stated operator has to be flattened into an attribute of whichever node the extractor happened to pick, and a stated NON-operation has nowhere to go at all - so the cleanest refutation in the document, which is what would keep two designs apart, is the fact most likely to be dropped.

**Scope items:** 5 (ontology additions: operated-by) · **refs:** D7; D12 (same hazard class); G18 names operated-by

### Documents

**`press-BB`** — trade press item · **grade:** C · **bias:** third-party trade press · **dated:** 2025-02

```text
Who Actually Runs the TL-40X?
Staff correspondent - February 2025

The Water Authority's Plant Command is believed to operate the TL-40 within its southern
transfer belt. There is no confirmed evidence that the Water Authority operates the TL-40X, and
the Authority declined to comment on the point.
```

### What the extractor emitted

An operator attribute on one design; nothing at all for the refutation.

### Per-fact layer routing

| Stated fact | Routes to | Why |
|---|---|---|
| the Water Authority's Plant Command is believed to operate the TL-40 | **instance** | a stated operator RELATION between an organization and a design, hedged |
| 'within its southern transfer belt' | **neither** | an area of responsibility, not a place |
| there is no confirmed evidence that the Water Authority operates the TL-40X | **instance** | a stated NEGATIVE - a refutation with no relation to attach to, and the strongest anti-identity evidence in the document |
| the Authority declined to comment | **gap** | a named reason the gap does not close from this source |

### Discriminators

- **operator** — STATED as a relation, hedged ('is believed to'), for one design; and stated NEGATIVELY for the other
- **geography** — AREA ONLY - a belt, which is a responsibility rather than a place
- **designation** — STATED at design level for both; ABSENT at body level
- **time** — STATED as a month (2025-02)

### Required outcome (prose — choose your own mechanism and values)

The stated operator relation must be representable as a relation, carrying the source's hedge, so that a conflicting operator statement from another source can meet it head-on as a relationship conflict rather than as two attribute values on nodes that may or may not be the same node. The refutation must also land somewhere - a stated 'this operator does not operate that design' is evidence, and it is the kind of evidence that keeps two similar designs apart. If neither has a carrier, the honest output is a recorded expressiveness gap naming what could not be represented, not a silent drop and not a coerced attribute. The belt must not become a site.

### Tempting but wrong

- Flatten the stated relation into an operator attribute on whichever node was convenient, so that two sources stating different operators for one design produce two attribute values on two nodes and never meet as a conflict.
- Drop the refutation because negatives have no lane. The single most useful anti-identity fact in the document disappears, and the two designs are left with nothing keeping them apart except a hedge.
- Record the refutation as a positive claim with inverted polarity on some other edge, so that a later reader sees an operation relation whose sign depends on a field nobody reads.
- Turn 'southern transfer belt' into a site so the operator relation has somewhere geographic to live.

### Negative gold — spans that must produce NO claim

- 'is believed to' is a hedge that must survive onto the claim.
- 'declined to comment' asserts nothing about operation and is a reason a gap stays open.

**Corpus.** EXERCISABLE, and live in the frozen corpus: the operator relation is stated in relation form in at least two documents, the corpus contains a genuine cross-service operator conflict for one design, and it contains the exact refutation shape for the flagship false-merge trap - which today has nowhere to go. Verified: no operator relation exists in the ontology.

---

## Cross-fixture notes

**Four things only become visible across these fixtures, and they are deliberate.**

1. **F3c and F3d are the same assertion at opposite grades, and F3d post-dates F3c at a different site.** Run
   together they are the whole of "stated is not trusted" plus a live supersede candidate: an anonymous
   post that, if treated as a stated basing on equal footing, retires a good-grade establishment bulletin.
   Neither fixture alone shows that.
2. **F5a's merge temptation is F7a's precondition.** If the two candidate sections in F5a are fused because
   they share an operator, a design and a site neighbourhood, they acquire one basing instance - and every
   harm in F7a becomes reachable from a shape that contains no relocation at all. The two shapes are one
   failure chain, which is why an order-of-battle undercount is not merely hygiene.
3. **F6a, F6b and F6c must be satisfied by ONE declaration, and they pull in three directions.** F6a needs
   differing site kinds to de-conflict; F6b needs absence not to; F6c needs the mapping to survive an
   open-ended free-text vocabulary. Any two of the three are easy to satisfy alone. A rule that reads the
   stated string literally passes F6a and fails the other two silently.
4. **F7a forbids what F7b requires.** The distinguishing fact is not the strength of the newer assertion -
   it is the same in both - but whether the identity of the subject was earned on a designation or assumed
   from proximity. A gate that keys on assertion credibility rather than on subject identity will get both
   fixtures wrong in opposite directions and look consistent doing it.

**And one property the whole set shares:** where a discriminator is not stated, it is unknown - never
inferred from context, never treated as a conflict, and never allowed to license a convenient outcome.
Absence must leave a citizen under-individuated and flagged, not de-conflicted, not merged, and not
back-filled.

