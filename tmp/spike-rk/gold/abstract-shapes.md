# RK-SPIKE — abstracted shape fixtures (corpus-blind)

`schema_version: rk-spike-abstract-shapes/1.0` · machine-readable twin: `abstract-shapes.json`

**Read this file, not the corpus.** These fixtures exist so the characterize-and-cluster
prototype can be built against the *structural difficulty* of the real data without seeing the real data
— because seeing it biases you toward tuning to it. Every entity here is invented: a fictional
regional-infrastructure domain. There are no real designations, place names, manufacturers, document ids
or source ids anywhere in this file.

These seven fixtures carry the **structural difficulty** of the real slice with none of its
content. Everything is invented: a fictional regional-infrastructure domain with made-up plant
operators, sites, sections and equipment types. What is preserved from the real documents is what
matters for characterize-and-cluster:

- how many mentions there are, and which ones co-refer;
- **which category licenses each binding** — `EXPLICIT_EQUIVALENCE`, `NAME_VARIANT`, or
  `UNAMBIGUOUS_ANAPHOR` — and which bindings are genuinely `AMBIGUOUS`;
- which discriminators (operator / geography / designation / time) are **present** vs **absent**;
- source grade and dates, including staleness and report-vs-event divergence;
- the **presence vs formation** distinction (equipment seen at a place vs a named organizational
  body based there).

**No thresholds, scores or config values appear anywhere in this file, by design.** Each fixture
states the required *outcome* in prose. Choose the mechanism and the numbers on general principle;
the test author asserts them independently.

**One standing rule across all seven:** where a discriminator is not stated, it is `unknown` — never
inferred from context, and never treated as a conflict. Absence must leave an instance
under-individuated and flagged, not walled and not merged.

## What each fixture is for

| Fixture | What it is for |
|---|---|
| `S1-within-doc-coref-workhorse` | The Tier-0 workhorse: several coreference chains in one short document, including one acronym apposition, one full definite-anaphor ladder, one chain whose referent type is not in the ontology, and one near-identical pair that must NOT bind. |
| `S2-contrastive-twins-plus-refuted-third` | Two same-family designs, same country of origin, same maker, same customer, distinguished ONLY by operator and one numeric attribute — with an explicit 'not one thing fielded twice' — plus a third design that is named and explicitly NOT acquired. |
| `S3-presence-vs-formation-and-self-disclaimed-alias` | The load-bearing case. |
| `S4-structured-tabular-with-identifier-licensed-identity` | A structured record whose shape is nothing like prose: three near-identical rows that MUST NOT merge (licensed only by distinct identifiers, while a shared container pushes hard the other way), one identifier-backed rename, four surfaces for one counterparty, five surfaces for one place, a truncated reference, a name-collision place trap, and a self-disclaimed cross-reference note cut off mid-token. |
| `S5-thin-context-and-explicit-refusal-to-corefer` | The must-degrade-to-gap case, and the only fixture where the SOURCE ITSELF declines to say whether two mentions are the same thing. |
| `S6-low-grade-echo-with-mutating-content` | The deception case and the hardest coreference problem: one 'document' of eight posts from six handles that is really ONE claim echoed four times — where the echo MUTATES the destination — plus a designator conflict, three explicit refusals to assert, and one post dated a month earlier than the claim it appears to rebut. |
| `S7-cardinality-without-individuation` | The order-of-battle shape: a stale record that states a COUNT of organizational bodies with no designator and no site for any of them, assigns them to the WRONG operator relative to the other fixtures, states a generic composition as if it were an observation, names a role-holder falsely with perfect syntax, and declares its own publication date unrecoverable. |

---

## `S1-within-doc-coref-workhorse`

**Purpose.** The Tier-0 workhorse: several coreference chains in one short document, including one acronym apposition, one full definite-anaphor ladder, one chain whose referent type is not in the ontology, and one near-identical pair that must NOT bind.

**Source grade:** B · **bias:** operator-of-the-asset (interested party) · **dated:** 2021-10-14

### Fixture text

```text
PRESS NOTE — Northern Grid Authority (NGA)
Dated: 14 October 2021

DIRECTOR VISITS CENTRAL PUMPING ESTABLISHMENT, LOWFIELD

Lowfield - 14 October 2021: The Director of Regional Works (DRW), Mr A. Halloway, today visited
the Central Pumping Establishment, Lowfield, where a new High-Volume Transfer Set (HVTS),
reportedly the TL-40, was formally commissioned into service with a Northern Grid Works (NGW)
section.

On arrival, the DRW was received by the Officer in Charge and senior staff of Grid Works. He was
given a briefing on the operating employment and integration of the newly commissioned set within
the Regional Control and Telemetry (RCT) network.

The set, believed to be a variant of the Vanguard family (TL-40/V-40 family) of transfer plant, is
understood to raise regional throughput well beyond 60 units.

The exact number of pump skids commissioned was not disclosed, in keeping with the Authority's
standing practice of not releasing establishment detail for critical plant. An NGA official,
speaking on background, said only that "sufficient numbers" had been commissioned, and that further
commissioning may follow in phases.

The DRW, addressing the staff of the newly raised/re-equipped section, said the commissioning
reflected continued modernisation. Later he interacted with staff of the section and reviewed a
guard of honour with the officers of the section.
```

### Mention structure

**equipment** — 6 mention(s)

  - “a new High-Volume Transfer Set (HVTS), reportedly the TL-40”
  - “the newly commissioned set”
  - “The set”
  - “the set's ... (implicit)”
  - “the newly commissioned set (second occurrence)”
  - “the commissioning”

  Licence: EXPLICIT_EQUIVALENCE for the '(HVTS)' apposition; UNAMBIGUOUS_ANAPHOR for each later definite NP (exactly one set is in the discourse)

  Licensing quote: > a new High-Volume Transfer Set (HVTS), reportedly the TL-40

**organizational-body** — 4 mention(s)

  - “a Northern Grid Works (NGW) section”
  - “the newly raised/re-equipped section”
  - “staff of the section”
  - “the officers of the section”

  Licence: UNAMBIGUOUS_ANAPHOR ('the section', one section in the discourse); the '(NGW)' apposition licenses the parent-body NAME only

  Licensing quote: > addressing the staff of the newly raised/re-equipped section

**person (type not in the ontology)** — 4 mention(s)

  - “The Director of Regional Works (DRW), Mr A. Halloway”
  - “the DRW”
  - “He”
  - “The DRW”

  Licence: EXPLICIT_EQUIVALENCE (title apposition) + UNAMBIGUOUS_ANAPHOR (pronoun)

  Licensing quote: > The Director of Regional Works (DRW), Mr A. Halloway, today visited

**ANTI-COREF pair** — 2 mention(s)

  - “a Northern Grid Works (NGW) section”
  - “senior staff of Grid Works”

  Licence: AMBIGUOUS -> must resolve to ANTI-COREF. 'Grid Works' is the parent body; 'a Northern Grid Works section' is one body within it. Near-total token overlap, different referents, and the document never contrasts them.

  Licensing quote: > the DRW was received by the Officer in Charge and senior staff of Grid Works

### Discriminators

- **operator** — STATED ('Northern Grid Works', 'Northern Grid Authority')
- **geography** — STATED but coarse — a named establishment in a named town, no coordinates
- **designation** — ABSENT — the section has no number and no echelon
- **time** — STATED exactly (2021-10-14)

### Presence vs formation

**Formation, weakly licensed.** The document states a commissioning INTO a named-type body, which is organizational evidence, not a bare sighting. But the body carries no designation, and the place is an establishment (a ceremony venue), not an operating position. So: a formation may exist; its identity may not be asserted; and no based-at is stated.

### Required outcome (prose — choose your own mechanism and values)

All four chains must be recovered as chains, including the pronoun. The equipment chain binds tightly (an apposition plus unambiguous definite anaphora); the acronym expansion licenses a name, not the body's identity. The alias implied by the FAMILY parenthetical ('TL-40/V-40 family') must be bound at family level only — reading it as the variant-level identity 'V-40 is the same object as TL-40' over-reads this source. The parent-body vs section pair must NOT bind, and the honest reason is semantic, not stated, so a system that only respects stated contrasts will get it wrong. The withheld skid count must surface as a gap that names the missing slot AND the reason it will not close (a stated policy of non-disclosure). 'further commissioning may follow in phases' must produce NO claim. The person chain is perfect coreference evidence with no ontology type to land on — the system must not discard the chain silently, and must not invent a node type for it.

### Negative gold — spans that must produce NO claim

- 'further commissioning may follow in phases' — prospective modal, no claim.
- the guard of honour and the reviewing — ceremonial, no claim.
- 'senior staff of Grid Works' must not bind to 'a Northern Grid Works (NGW) section'.

---

## `S2-contrastive-twins-plus-refuted-third`

**Purpose.** Two same-family designs, same country of origin, same maker, same customer, distinguished ONLY by operator and one numeric attribute — with an explicit 'not one thing fielded twice' — plus a third design that is named and explicitly NOT acquired.

**Source grade:** C · **bias:** third-party trade press · **dated:** 2021-10

### Fixture text

```text
A Closer Look at the TL-40 and TL-40X Installations
Staff correspondent - October 2021

Nearly three years after commissioning was first confirmed by aerial survey, the regional use of the
Vanguard family remains under-reported, even as both the Grid Works and the Water Authority (WA)
continue to field distinct variants of the set under different programme names.

Grid Works operates a skid-level installation reportedly designated TL-40 (some trade reporting
still uses TL40, and the export designation V-40 continues to circulate in older brochures). The
Grid Works variant is generally credited with a throughput in the region of 140 units.

Separately, the Water Authority is believed to operate a higher-capacity variant referred to in
recent trade literature as the TL-40X. This variant, procured under a separate contract, is credited
with a throughput around 290 units, roughly double that of the Grid Works sections. That figure is
not clarified by either the Authority or the manufacturer, Meridian Works Corporation (MWC).

It is worth stressing that despite the shared "TL-40" family name, the Grid Works and Water
Authority sets appear to be genuinely separate procurement lines rather than a single set fielded
twice - different impellers, reportedly different control cabinets, and possibly different telemetry
architectures.

Some confusion also stems from the fact that MWC markets a lower-tier derivative, the FV-200
(sometimes rendered FV-200A), which uses a passive float sensor rather than the active telemetry of
the TL-40 family proper. There is no confirmed evidence that this region has acquired the FV-200, and
it is mentioned mainly because trade materials list it alongside TL-40 variants, which has led to at
least one erroneous claim that "FV-200 skids" are in service - a claim this publication was unable to
substantiate.

Neither authority responded to requests for comment on section numbers, installation locations, or
the precise contractual designations. Readers should treat the figures above as indicative rather
than authoritative.
```

### Mention structure

**design A** — 5 mention(s)

  - “a skid-level installation reportedly designated TL-40”
  - “TL40”
  - “the export designation V-40”
  - “The Grid Works variant”
  - “the Grid Works sections”

  Licence: EXPLICIT_EQUIVALENCE — the parenthetical states, in the author's voice, that TL40 and V-40 are other designations FOR THIS SYSTEM

  Licensing quote: > reportedly designated TL-40 (some trade reporting still uses TL40, and the export designation V-40 continues to circulate in older brochures)

**design B** — 4 mention(s)

  - “a higher-capacity variant referred to in recent trade literature as the TL-40X”
  - “This variant, procured under a separate contract”
  - “the TL-40X”
  - “sets”

  Licence: UNAMBIGUOUS_ANAPHOR ('This variant' immediately follows its antecedent)

  Licensing quote: > referred to in recent trade literature as the TL-40X. This variant, procured under a separate contract

**design C (refuted acquisition)** — 3 mention(s)

  - “the FV-200 (sometimes rendered FV-200A)”
  - “the FV-200”
  - “"FV-200 skids"”

  Licence: NAME_VARIANT (explicit rendering variant)

  Licensing quote: > the FV-200 (sometimes rendered FV-200A)

**ANTI-COREF pair (the whole point)** — 2 mention(s)

  - “The Grid Works variant”
  - “the TL-40X”

  Licence: Stated contrast — 'appear to be genuinely separate procurement lines rather than a single set fielded twice'. HEDGED.

  Licensing quote: > despite the shared "TL-40" family name, the Grid Works and Water Authority sets appear to be genuinely separate procurement lines rather than a single set fielded twice

**ANTI-COREF: family vs variant** — 2 mention(s)

  - “the Vanguard family”
  - “TL-40”

  Licence: Semantic — the family term is the parent of BOTH designs in this document.

  Licensing quote: > the regional use of the Vanguard family remains under-reported

### Discriminators

- **operator** — STATED for both, and DIFFERENT (the two operators are the only clean separator)
- **geography** — ABSENT — no site is named anywhere
- **designation** — STATED at design level (TL-40 / TL-40X / FV-200); ABSENT at body level
- **time** — STATED as a month, and INTERNALLY INCONSISTENT: the opening line dates first confirmation to ~three years earlier than the document's own month

### Presence vs formation

**Neither.** No equipment is observed at a place and no organizational body is named. 'the Grid Works sections' is a bare plural with no designation and no site — a count-shaped hint, not a formation. Nothing licenses a based-at; nothing licenses even an observed-at, because no site exists in the text.

### Required outcome (prose — choose your own mechanism and values)

The two designs must NOT merge, and the honest confidence in keeping them apart should be tempered rather than absolute: everything about them agrees except operator and one number, the contrast is stated by a single mid-grade source, and the source hedges it. The three alias statements for design A must bind. The family term must bind to NEITHER design. The third design must exist as an entity while the claim that it is in service must be recorded as REFUTED — and note that a negative-existence claim of the form 'operator X does not operate design Y' has no relationship carrier if the ontology models operator only as an attribute; the implementer must decide where that goes rather than dropping it. The stated difference in unnamed sub-components is the strongest anti-identity evidence in the fixture and is likewise uncarriable as a relation — it must not be silently lost. The internal date inconsistency must survive as an inconsistency, not be resolved by picking one.

### Negative gold — spans that must produce NO claim

- The comparative aside about an unrelated third-party product family — no claim.
- 'the Vanguard family' must not bind to either variant.
- The retracted figures ('indicative rather than authoritative') must not be promoted to established attributes.

---

## `S3-presence-vs-formation-and-self-disclaimed-alias`

**Purpose.** The load-bearing case. A named higher command plus an ANONYMOUS sub-unit at a site (presence, not formation); two different counts (one observed, one estimated with a stated confidence caveat); an alias the document states and then disclaims; two other thin same-type sites enumerated; and a relocation asserted with NO origin.

**Source grade:** B · **bias:** third-party aggregator (self-declared) · **dated:** 2025-04-04

### Fixture text

```text
Regional Infrastructure Monitor - Weekly Survey & Telemetry Digest
Issue dated: 04 April 2025 (reporting period 24-31 March 2025)

NORTHERN CORRIDOR - PLANT BELT

Northgate Yard (Grid Works/Water Authority joint-use facility, ~8 km NW of Brightwater along the
trunk road corridor): aerial survey collected 27 March (0.5m) confirms the skid and control cluster
first detected on the single-pass survey reported earlier this quarter, in the northeast apron. Six
skid-pattern units remain in a fan arrangement consistent with prior TL-40X associated installations
elsewhere; a large octagonal control-cabinet signature, believed to be the RC-118 telemetry cabinet
associated with the TL-40X set, is again visible on its prepared pad roughly 250 m east of the skid
cluster - position essentially unchanged from that earlier single pass.

Of note this cycle: a second, non-survey indicator has closed some of the ambiguity around the site.
A commercial telemetry aggregator feed (operator not disclosed to subscribers, relayed via a
third-party monitoring service) logged an emitter-on fix in the same general locale during the
reporting window; the fix window is described by the vendor only as "high confidence, single pass"
with no further geolocation detail released at this tier. Separately, a repeat aerial pass on 29
March (different platform than the 27 March pass) again shows the pad occupied and skid count
unchanged. Analysts should still treat the RC-118 identification itself as the vendor's
characterization, not independently re-derived by this desk.

Establishment context: Northgate Yard had not previously been cited as a TL-40-family site; this is
the first survey cycle to associate a Water Authority/Grid Works Plant Command TL-40X (export
variant, sometimes rendered TL-40 in regional service literature) section with the location,
consistent with a recent relocation rather than a long-standing installation. Section strength at
this site is estimated at 4-6 skids plus one control cabinet and an associated telemetry van, though
the desk's confidence in the "8" upper bound remains low given intermittent visibility across passes.

No new activity to report at the previously tracked Calder-area and Redlow apron sites this
period; both remain in a "last confirmed" state from the 07 March pass.

Cross-reference: readers tracking the TL-40/TL-40X/TL40 designator family should note continuing
inconsistency across sources in how regional service designators map to the baseline TL-40X marketing
designation; this digest uses "TL-40" generically per prior issues unless a source specifies
otherwise.

Compiled from open commercial survey, subscriber telemetry relay reporting, and prior digest issues
(14 Feb 2025, 07 Mar 2025).
```

### Mention structure

**site** — 7 mention(s)

  - “Northgate Yard (joint-use facility, ~8 km NW of Brightwater ...)”
  - “the site”
  - “the same general locale”
  - “the location”
  - “this site”
  - “a TL-40-family site”
  - “Northgate Yard (second occurrence)”

  Licence: UNAMBIGUOUS_ANAPHOR — one site in focus throughout

  Licensing quote: > a second, non-survey indicator has closed some of the ambiguity around the site

**presence (equipment at site)** — 4 mention(s)

  - “the skid and control cluster”
  - “Four skid-pattern units”
  - “a ... Plant Command TL-40X ... section”
  - “Section strength at this site”

  Licence: UNAMBIGUOUS_ANAPHOR, tied within one sentence

  Licensing quote: > Section strength at this site is estimated at 4-6 skids plus one control cabinet and an associated telemetry van

**component (identification disclaimed)** — 4 mention(s)

  - “a large octagonal control-cabinet signature, believed to be the RC-118 telemetry cabinet”
  - “the pad”
  - “one control cabinet”
  - “the RC-118 identification”

  Licence: EXPLICIT_EQUIVALENCE, hedged — and then explicitly non-endorsed

  Licensing quote: > Analysts should still treat the RC-118 identification itself as the vendor's characterization, not independently re-derived by this desk

**AMBIGUOUS: generic vs specific designator** — 3 mention(s)

  - “TL-40 (used generically)”
  - “TL-40X (the specific export designation)”
  - “TL40”

  Licence: AMBIGUOUS — an equivalence is stated in one paragraph and the mapping is disclaimed in another, and one surface is declared a GENERIC label

  Licensing quote: > this digest uses "TL-40" generically per prior issues unless a source specifies otherwise

**two other same-type sites (enumerated)** — 2 mention(s)

  - “the previously tracked Calder-area ... site”
  - “... Redlow apron site”

  Licence: ANTI_COREF by stated enumeration with explicit cardinality

  Licensing quote: > the previously tracked Calder-area and Redlow apron sites this period; both remain in a "last confirmed" state

### Discriminators

- **operator** — STATED BUT DISJUNCTIVE — 'Water Authority/Grid Works', two operators joined by a slash. Not a usable discriminator, and must not be silently resolved to either.
- **geography** — STATED as a RELATIVE fix only ('~8 km NW of Brightwater along the trunk road corridor'); no grid, no coordinates
- **designation** — ABSENT at body level; the only designation-shaped token is the component type, which the source disowns
- **time** — STATED precisely for each observation (27 Mar, 29 Mar, reporting period 24-31 Mar)

### Presence vs formation

**Presence, not formation — and this is the borderline that gets misread.** A named COMMAND sits next to an anonymous SECTION. A command is named; the section is not. An anonymous body attributed to a named higher command is NOT a named formation, so this is equipment-at-a-place with a count, and any basing of a named body is derived. The sentence reads like an establishment association purely because a proper noun sits next to the word 'section'.

### Required outcome (prose — choose your own mechanism and values)

The site chain and the presence chain must bind. The presence must NOT be promoted to a named organizational body — the honest output is 'equipment presence at this site is well supported; the operating body and its count are unresolved'. The two counts must stay two distinct claims (one observed on a dated pass, one an estimate whose own upper bound the source distrusts); collapsing them into a single number invents precision the source refuses. The component identification must be recorded as attributed, not as the desk's own finding. The generic-vs-specific designator pair must come out as AMBIGUOUS: it is a refinement relation, not identity, and if the schema cannot express refinement between two designs then the honest result is an unresolved pair, not a merge and not a split. The two other sites must not merge with each other or with the main site, and note that the only thing keeping them apart is the source's word 'both'. The asserted relocation has NO origin anywhere in the document, so the state change is not expressible as a two-ended fact from this source alone. Finally: three signals inside ONE document are not three independent sources — the document self-describes as an aggregator, and the second 'independent' signal is an unnamed vendor relayed by an unnamed intermediary with no geolocation released.

### Negative gold — spans that must produce NO claim

- 'an aerial-only assessment carried real decoy risk ... elsewhere in the region' style reasoning — methodological, asserts nothing about THIS site.
- The non-endorsement sentence must not be read as an identification.
- Distribution/subscription boilerplate.

---

## `S4-structured-tabular-with-identifier-licensed-identity`

**Purpose.** A structured record whose shape is nothing like prose: three near-identical rows that MUST NOT merge (licensed only by distinct identifiers, while a shared container pushes hard the other way), one identifier-backed rename, four surfaces for one counterparty, five surfaces for one place, a truncated reference, a name-collision place trap, and a self-disclaimed cross-reference note cut off mid-token.

**Source grade:** C · **bias:** commercial record · **dated:** 2020-11

### Fixture text

```text
REGIONAL PORT AUTHORITY - INBOUND DECLARATION EXTRACT
Terminal:        Brightwater International Freight Terminal / BIFT NG
Period Covered:  01-NOV-2020 to 30-NOV-2020

-----------------------------------------------------------------------------
DEC No: NGQA-HC-2020-204471          Filing Date: 04-11-2020
Point of Discharge: NORTHGATE HARBOUR BASIN (NG)
Vessel: MV CLEARWATER  Voy: 0091E
Waybill No: CLWW307556104

Receiver:        BRAMWELL ELECTRO TRADING (PVT) LTD
                 Suite 4-C, Kingsway Commercial Complex,
                 Brightwater -- REG 5107443-9
Sender:          HALCYON IMP/EXP CO. LTD
                 (see also HALCYON IMPEX CO, LTD -- inv. #HG-20-8362)
Sender Ctry:     CALDONIA (Origin: Eastport)

Tariff Code:     9914.61.00
Description (as filed): "SENSOR APPARATUS PARTS / ELECTRONIC ASSEMBLY -- SPARE,
                 FOR INDUSTRIAL METERING AID, NOT FOR RESALE, 1 LOT"
Container:       BXLU5530918 / BXLU5531042 (2 x 40ft HC)
Freight Fwdr:    ASHLAND CARGO SERVICES, Northgate Basin Town, Brightwater

-----------------------------------------------------------------------------
DEC No: NGQA-HC-2020-204472          Filing Date: 04-11-2020
Point of Discharge: NORTHGATE BASIN
Vessel: MV CLEARWATER  Voy: 0091E
Waybill No: CLWW307556105

Receiver:        BRAMWELL ELECTRO TRADING (PVT) LTD
Sender:          HALCYON IMP & EXP. CO.
Sender Ctry:     CALDONIA

Tariff Code:     9914.62.00
Container:       BXLU5530918 (shared, see line 204471)

Annex A / Line-Item Detail (attached to DEC 204472, page 2 of 2 -- scan quality poor):
  Item 1  -- WAVEGUIDE ASSY, QTY 4
  Item 2  -- SERVO DRIVE UNIT, QTY 2 .......... ref dwg RC118-
             -- FrOm: j.tam@halcyon-export.cd
             Subject: RE: shipping docs pkg 2 attached pls confirm addr, urgent
  Item 3  -- INTERFACE MODULE, QTY 1

End-user certificate on file: NOT ATTACHED TO DEC (ref. letter RPA/IMP/2020/7180
cited in broker cover note, copy not scanned)
Delivery instructions (broker note, handwritten annotation on file copy):
  "receiver to arrange onward clearance -- final destination Plant Depot,
  ~14 km NNE of Kestrel Ridge / Ashcombe Yard area"

-----------------------------------------------------------------------------
DEC No: NGQA-HC-2020-205318          Filing Date: 09-11-2020
Point of Discharge: Northgate Basin
Vessel: MV STONEHAVEN  Voy: 118W
Waybill No: STHV4290337815

Receiver:        BRAMWELL ELECTRO TRADING PVT LTD (formerly BRAMWELL ELECTRONIC
                 TRADING CO -- name change ref REGISTRY CUIN 0031905, 2019)
Sender:          HALCYON IMPEX CO, LTD
Sender Ctry:     Caldonia

Tariff Code:     9914.61.00
Container:       MRTU8817663

Remarks (system-generated, exam order):
  EXAM TYPE: GREEN CHANNEL -- NO PHYSICAL EXAMINATION
  Risk flag auto-cleared by trusted-trader status of freight forwarder (ASHLAND
  CARGO SERVICES -- Cert No. RG-TT-0774)

-----------------------------------------------------------------------------
CROSS-REFERENCE NOTE (internal data-matching, non-adjudicative):
Receiver BRAMWELL ELECTRO TRADING (PVT) LTD / BRA
```

### Mention structure

**receiver** — 5 mention(s)

  - “BRAMWELL ELECTRO TRADING (PVT) LTD”
  - “BRAMWELL ELECTRO TRADING (PVT) LTD”
  - “BRAMWELL ELECTRO TRADING PVT LTD”
  - “BRAMWELL ELECTRONIC TRADING CO”
  - “Receiver BRAMWELL ELECTRO TRADING (PVT) LTD / BRA”

  Licence: EXPLICIT_EQUIVALENCE — a registry rename cited with its identifier; plus NAME_VARIANT for punctuation. NOTE the surfaces differ by a WHOLE TOKEN ('ELECTRO' vs 'ELECTRONIC'), so string similarity alone under-binds.

  Licensing quote: > BRAMWELL ELECTRO TRADING PVT LTD (formerly BRAMWELL ELECTRONIC TRADING CO -- name change ref REGISTRY CUIN 0031905, 2019)

**sender** — 5 mention(s)

  - “HALCYON IMP/EXP CO. LTD”
  - “HALCYON IMPEX CO, LTD”
  - “HALCYON IMP & EXP. CO.”
  - “HALCYON IMPEX CO, LTD”
  - “j.tam@halcyon-export.cd”

  Licence: EXPLICIT_EQUIVALENCE via 'see also' + a shared invoice number for two surfaces; the third surface is licensed only TRANSITIVELY; the email domain is a weak fourth signal

  Licensing quote: > (see also HALCYON IMPEX CO, LTD -- inv. #HG-20-8362)

**place (point of discharge)** — 5 mention(s)

  - “NORTHGATE HARBOUR BASIN (NG)”
  - “NORTHGATE BASIN”
  - “Northgate Basin”
  - “BIFT NG”
  - “NG”

  Licence: EXPLICIT_EQUIVALENCE for the '(NG)' abbreviation apposition + NAME_VARIANT for the casing/shortening variants

  Licensing quote: > Point of Discharge: NORTHGATE HARBOUR BASIN (NG)

**three records (MUST NOT MERGE)** — 3 mention(s)

  - “DEC No: NGQA-HC-2020-204471”
  - “DEC No: NGQA-HC-2020-204472”
  - “DEC No: NGQA-HC-2020-205318”

  Licence: ANTI_COREF by distinct stated identifiers (declaration numbers AND waybill numbers), reinforced by the record's own cross-reference treating two of them as separate lines

  Licensing quote: > Container:       BXLU5530918 (shared, see line 204471)

**ANTI-COREF place traps** — 3 mention(s)

  - “Northgate Basin Town, Brightwater (a TOWN, the forwarder's address)”
  - “NORTHGATE HARBOUR BASIN (a terminal)”
  - “Brightwater International Freight Terminal (a terminal whose NAME begins with a different settlement's name)”

  Licence: Semantic — a town and a harbour basin sharing a name, and a terminal named after a settlement it is not in

  Licensing quote: > Freight Fwdr:    ASHLAND CARGO SERVICES, Northgate Basin Town, Brightwater

### Discriminators

- **operator** — STATED as country of the sender, with CASING DRIFT ('CALDONIA' twice, 'Caldonia' once) — the value-normalization case, inside one record
- **geography** — STATED for the discharge point (five surfaces, one referent) and RELATIVE-ONLY for the final destination ('~14 km NNE of Kestrel Ridge / Ashcombe Yard area', from a handwritten note, with TWO alternative anchors)
- **designation** — STATED as hard identifiers for the records and the parties (declaration numbers, waybills, a registry CUIN, a trusted-trader certificate) — and TRUNCATED for the one technical reference ('ref dwg RC118-')
- **time** — STATED exactly per record (04-11-2020, 04-11-2020, 09-11-2020)

### Presence vs formation

**Neither.** No equipment is observed at a place and no organizational body is named. The only place-like objects are a point of discharge and a destination from a handwritten annotation. If the schema has no node type for a port or terminal, the discharge point has to be forced into a site type that means something else, or dropped.

### Required outcome (prose — choose your own mechanism and values)

The three records must remain three. This is the fixture's whole point: they share a receiver, a sender cluster, a tariff-code family, a vessel voyage, and — for two of them — a CONTAINER, so both name similarity and shared neighbourhood argue for merging, and only the identifiers argue against. A system whose identity evidence is dominated by name and neighbourhood will merge them and silently corrupt the count; the honest handling is that two records which each state a reference and state DIFFERENT ones are held apart before any graded judgement runs. Conversely the receiver's rename MUST merge, even though the surfaces differ by a whole token, because an identifier licenses it — so the same fixture requires the identifier to be decisive in both directions. The five place surfaces must collapse to one referent while the town and the same-named terminal must NOT be pulled in. The truncated technical reference must remain a reference on ONE line item and must NOT become a claim about what the consignment contains: the declared purpose is explicitly civil metering, no physical examination was performed, and the end-user certificate is stated as not attached. The cross-reference note is cut off mid-token AND self-labelled non-adjudicative — the system must not finish the sentence.

### Negative gold — spans that must produce NO claim

- The pasted email subject line and the 'FrOm' casing garble — document noise. The email DOMAIN is a weak signal for the sender cluster; the message body asserts nothing.
- The truncated cross-reference note must not be completed or acted on.
- 'SENSOR APPARATUS PARTS ... FOR INDUSTRIAL METERING AID' is a STATED CIVIL purpose. Any other reading is derived and must be labelled as such.

---

## `S5-thin-context-and-explicit-refusal-to-corefer`

**Purpose.** The must-degrade-to-gap case, and the only fixture where the SOURCE ITSELF declines to say whether two mentions are the same thing. Every discriminator slot is empty or explicitly declared empty, the geography description is internally inconsistent, and the central observation is a negative.

**Source grade:** B · **bias:** third-party · **dated:** 2025-06-11

### Fixture text

```text
AERIAL SURVEY SUMMARY - COMMERCIAL DERIVED
Subject: Plant Infrastructure, Southern Approaches - Site Activity Check

1. Purpose

This report provides a visual update on a suspected forward plant staging area previously flagged in
open discussion threads as associated with the TL40 transfer system in regional use. The site in
question - referred to in prior open reporting simply as "the old Ashcombe-area site" near the harbour
road turnoff, not the yard itself - was tasked for revisit following unconfirmed claims of a skid
relocation.

2. Collection Details

Survey date: 2025-06-11 (single pass, ~1030 local)
Cloud cover: ~10%, partial obscuration along the northern tree line
Prior baseline reference: chip from 2024-11 pass (same vendor, cataloged separately)

3. Observations

The area consistent with the suspected forward site shows the previously noted perimeter berm and
access road configuration largely unchanged from the 2024-11 baseline.

No skid units are visible on any of the pads or along the access spur at the time of this pass. The
cleared laydown area that in the 2024-11 chip showed what was assessed as a possible cabinet trailer
footprint is empty in the current image. No covered or tarped objects of skid-consistent dimensions
were identified on either the northern or southern pad clusters.

No unusual vehicle staging, generator trailers, or tented storage was noted anywhere within the
fenced compound this pass.

4. Comparative Note

A separate item circulating on an open aggregator channel (post dated 11 June, timestamped 0640Z -
roughly four hours before the collection above) asserted that "fresh TL40 skid deployment confirmed
near harbour road site, imagery pending," citing an unnamed "regional source." No imagery accompanied
that post, and the claim predates the pass documented in Section 2. The present collection does not
corroborate the assertion; whether the two references concern the same site footprint could not be
independently established from the post's description alone, as it gives no coordinates and describes
the location only as "near the harbour road, same as always."

5. Assessment

Current imagery is assessed as a negative skid presence observation for the pass window noted. This
does not preclude dispersal, maintenance rotation to an unobserved facility, or a collection-timing
gap relative to the aggregator claim. A follow-up tasking is recommended within the next 5-7 days,
ideally cross-referenced against a second vendor's catalog for the same window.

6. Caveats

- Single pass; no complementary sensor cross-check this cycle.
- Site identity as "the forward TL40 site" rests on prior open association rather than confirmed
  establishment documentation; no body markings or signage visible in any pass to date.
```

### Mention structure

**site** — 5 mention(s)

  - “a suspected forward plant staging area”
  - “The site in question - referred to in prior open reporting simply as "the old Ashcombe-area site" near the harbour road turnoff, not the yard itself”
  - “the suspected forward site”
  - “the fenced compound”
  - “"the forward TL40 site"”

  Licence: UNAMBIGUOUS_ANAPHOR — one site in focus throughout. NOTE: a well-bound cluster whose referent is nonetheless unidentifiable.

  Licensing quote: > The area consistent with the suspected forward site shows the previously noted perimeter berm and access road configuration largely unchanged

**baseline artifact** — 4 mention(s)

  - “chip from 2024-11 pass (same vendor, cataloged separately)”
  - “the 2024-11 baseline”
  - “the 2024-11 chip”
  - “prior imagery”

  Licence: NAME_VARIANT — binds on the date token

  Licensing quote: > Prior baseline reference: chip from 2024-11 pass (same vendor, cataloged separately)

**AMBIGUOUS: two site references, explicitly unresolvable** — 2 mention(s)

  - “the suspected forward site (this report's area of interest)”
  - “"near harbour road site" (the aggregator post)”

  Licence: AMBIGUOUS — and the source says so IN ITS OWN VOICE, naming the missing discriminator

  Licensing quote: > whether the two references concern the same site footprint could not be independently established from the post's description alone, as it gives no coordinates

### Discriminators

- **operator** — ABSENT entirely
- **geography** — STATED BUT SELF-INCONSISTENT — the subject line says 'Southern Approaches' while the site's only name places it in an 'old Ashcombe-area' with a 'harbour road turnoff'. NO coordinates anywhere. The slot is UNUSABLE, not merely coarse, and must not be averaged into a position.
- **designation** — EXPLICITLY DECLARED ABSENT — 'no body markings or signage visible in any pass to date'. Not merely missing: stated missing across the entire collection history.
- **time** — STATED precisely for the pass (2025-06-11 ~1030 local), for the baseline (2024-11), and for the competing claim (11 June 0640Z — four hours EARLIER)

### Presence vs formation

**Presence, negated — and the formation is explicitly disclaimed.** The report records a negative equipment-at-site observation, then states outright that the site's identity rests on prior open association rather than confirmed establishment documentation, and that no body marking has ever been visible. That is a source telling you no organizational evidence exists. Deriving an organizational basing here would be fabrication.

### Required outcome (prose — choose your own mechanism and values)

The site mentions must bind into one cluster, and the cluster must nonetheless come out as UNIDENTIFIED — a well-bound referent that cannot be placed. This is the 'under-determined + gap' outcome, and it is the whole reason the fixture exists: binding correctly and still declining to identify is the right answer, not a failure. The negative observation must be evidence, scoped to the pass window the source scopes it to, and must NOT be generalised into 'the site is empty'. The explicit refusal to co-refer must survive as an unresolved pair with the reason attached (no coordinates) — neither a merge nor a stated distinctness. The competing positive claim must be recorded as attributed, and the fact that it PREDATES the survey by four hours must be preserved, because it means the two are not strictly in contradiction. The site's own distinct-from statement ('not the yard itself') must hold as a wall even though neither endpoint is locatable — anti-identity evidence can arrive before any identity evidence does. The stated follow-up window is the 'when next coverage is due' half of a gap and must be carried, not dropped. Finally, note that 'the present collection does not corroborate the assertion' is a THIRD state — checked and failed to confirm — which is neither corroboration nor contradiction.

### Negative gold — spans that must produce NO claim

- 'This does not preclude dispersal, maintenance rotation ..., or a collection-timing gap' — three alternatives listed, none asserted.
- The site-identity disclaimer must not be read as a site-to-system claim.
- Collection metadata (cloud fraction, sun angle) is context, not claims.

---

## `S6-low-grade-echo-with-mutating-content`

**Purpose.** The deception case and the hardest coreference problem: one 'document' of eight posts from six handles that is really ONE claim echoed four times — where the echo MUTATES the destination — plus a designator conflict, three explicit refusals to assert, and one post dated a month earlier than the claim it appears to rebut.

**Source grade:** E · **bias:** hostile / promotional; flagged for deception risk · **dated:** 2025-06

### Fixture text

```text
POST 1
Handle: @northgate_watch
Date: 2025-06-11
Status URL: [link unavailable, account locked/protected - h/t repost by @plantspotter]
Text: "exclusive sources telling me the TL40X skid grp that was sitting at Northgate has QUIETLY
relocated, gone since early this wk, moved out toward the old Ashcombe site. nobody talking abt it
openly but convoy was seen night time. big move if true"

POST 2
Handle: @r_kestrel
Date: 2025-05-09
Status URL: (live link)
Text: "Aerial imagery from earlier this year confirms TL-40 (HVTS) skid group co-located near
Northgate yard, Brightwater - consistent with the reported 2025 relocation. No sign of it leaving per
open imagery."

POST 3
Handle: @corridorsentry (hobby account, ~3,100 followers)
Date: 2025-06-11
Text: "per the Northgate 'left the yard' claim going around - cannot confirm, would want imagery
before believing it. single unverified source afaik. treating with caution"

POST 4
Handle: @plantspotter (fan-run spotting page)
Date: 2025-06-11
Status URL: [status link not recoverable - post since deleted/edited]
Text: "RT @northgate_watch huge if confirmed. TL40X out of Northgate, redeployed near the harbour
road area allegedly. keeping eyes open."

POST 5
Handle: @plantanalystX (self-described "open source plant analyst")
Date: 2025-06-12
Text: "Following up on yesterday's report - TL40X skid group gone from Northgate per my contact,
relocation underway, will not disclose more. trust the process"

POST 6
Handle: @r_kestrel
Date: 2025-06-12
Text: "Seeing chatter about a TL-40 'move' out of Northgate. No imagery, no second source, one guy's
thread going viral. Would treat as unconfirmed until proven otherwise - this happens every few months
with this site."

POST 7
Handle: @northgate_watch
Date: 2025-06-12
Text: "to ppl asking for proof - I don't share sources sorry but trust me its moved. Northgate site
basically empty now allegedly, whole grp gone to new loc. more soon"

POST 8 [PARAPHRASED]
Handle: @corridor_aggregate (small aggregator account)
Date: 2025-06-13
Paraphrase: Account reposted the "Northgate empty" claim without independent verification, adding
only that "several people are sharing this now" and linking back to @northgate_watch's original post
as the sole source.
```

### Mention structure

**the equipment group (ONE claim, echoed)** — 5 mention(s)

  - “the TL40X skid grp that was sitting at Northgate”
  - “TL40X out of Northgate”
  - “TL40X skid group gone from Northgate”
  - “whole grp gone to new loc”
  - “the "Northgate empty" claim”

  Licence: EXPLICIT_EQUIVALENCE at the CLAIM level — Post 4 is an explicit repost of Post 1, Post 5 self-declares as a follow-up to it, Post 7 is the same author, Post 8 names Post 1 as the sole source

  Licensing quote: > linking back to @northgate_watch's original post as the sole source

**AMBIGUOUS: two designators, one site, overlapping window** — 3 mention(s)

  - “the TL40X skid grp ... at Northgate (Post 1, 2025-06-11)”
  - “TL-40 (HVTS) skid group co-located near Northgate yard (Post 2, 2025-05-09)”
  - “a TL-40 'move' out of Northgate (Post 6, 2025-06-12)”

  Licence: AMBIGUOUS — and the ambiguity is unresolvable from this document: another fixture (S2) says these two designators name DISTINCT designs, while a third (S3) says one is 'sometimes rendered' as the other

  Licensing quote: > Aerial imagery from earlier this year confirms TL-40 (HVTS) skid group co-located near Northgate yard

**AMBIGUOUS: three incompatible destinations for ONE move** — 3 mention(s)

  - “the old Ashcombe site (Post 1)”
  - “near the harbour road area (Post 4 — a REPOST of Post 1)”
  - “new loc (Post 7, unnamed)”

  Licence: AMBIGUOUS — a repost that CHANGES the destination

  Licensing quote: > RT @northgate_watch huge if confirmed. TL40X out of Northgate, redeployed near the harbour road area allegedly.

**refusals to assert (negative gold)** — 3 mention(s)

  - “Post 3 ('cannot confirm, would want imagery')”
  - “Post 6 ('Would treat as unconfirmed until proven otherwise')”
  - “Post 8 ('without independent verification')”

  Licence: n/a — these assert nothing about the world

  Licensing quote: > cannot confirm, would want imagery before believing it. single unverified source afaik.

### Discriminators

- **operator** — ABSENT from all eight posts — no operating body is ever named
- **geography** — One end named ('Northgate'); the other end has THREE incompatible names and no coordinates for any of them
- **designation** — ABSENT — 'grp' and 'group' are size words with no identifier, no parent body
- **time** — STATED per post, and one post (the imagery-citing one) is dated A MONTH EARLIER than the claim it appears to rebut

### Presence vs formation

**Presence only, and mostly negated or unsourced — while the CLAIM is formation-level.** A relocation is a claim about something that persists through a move, which is organizational. No post names an organizational body, so the document asserts a formation-level fact with zero formation evidence. The honest reading is 'presence claim unsourced; continuity unresolved'.

### Required outcome (prose — choose your own mechanism and values)

Apparent multiplicity must collapse to ONE origin. Six handles and eight posts must not read as six sources: one is an explicit repost, one self-declares as a follow-up, one is the same author, one is an aggregator that names the origin as its sole source, and three assert nothing at all. A system that counts posts as corroboration will confirm a single unsourced claim — which is the failure this fixture exists to catch. The three refusals must produce NO claims; note that one of them inverts if misread, since it *mentions* the relocation in order to doubt it. The destination must come out UNRESOLVED: one claim arriving with three incompatible objects, none locatable, and one of the incompatibilities introduced BY the repost — so an echo can mutate content, not merely repeat it. The two designators at one site in an overlapping window must come out ambiguous rather than merged or split, because the discriminator that would settle it (a body designation) is absent from every post. The month-early imagery post must not be treated as a contemporaneous rebuttal. Finally, the origin author's explicit refusal to source, and the aggregator's use of sharing VOLUME as if it were corroboration, are the decisive credibility facts and must be visible in the output rather than buried.

### Negative gold — spans that must produce NO claim

- All three refusal posts.
- 'several people are sharing this now' — volume is not corroboration.
- Follower counts and dead-link notes are provenance metadata, not claims.

---

## `S7-cardinality-without-individuation`

**Purpose.** The order-of-battle shape: a stale record that states a COUNT of organizational bodies with no designator and no site for any of them, assigns them to the WRONG operator relative to the other fixtures, states a generic composition as if it were an observation, names a role-holder falsely with perfect syntax, and declares its own publication date unrecoverable.

**Source grade:** C · **bias:** third-party · **dated:** cached 2015-06; source page last modified 2013-03

### Fixture text

```text
Regional Plant Systems Database (cached copy)
Record ID: RPS-PL-0447 | Retrieved via cache: 12 May 2015 07:41 GMT
[Note: original page last modified per server header - 24 February 2013 16:08 GMT]

TL-40 High-Volume Transfer Set

Overview

The TL-40 is the export variant of the Vanguard high-volume transfer set. Regional interest in a
high-volume transfer layer to supplement ageing low-lift plant has been reported since the mid-2000s.

As of this writing, the Water Authority's Plant Command is believed to operate the TL-40 within its
southern transfer belt covering approaches to Brightwater and the coastal sector. Set composition is
estimated at one control vehicle, four single-stage skid units each carrying six canisters,
associated RC-118 cabinets, and a monitoring element, broadly mirroring the originating operator's own
regimental structure.

Force Levels

A widely-cited figure - drawn from a 2015 establishment assessment compiled by a regional balance
publication - places regional holdings at two operational sections (approximately six to ten
skid units per section equivalent, figures vary by source) assigned to the Water Authority's Central
Command, with a third section reportedly in the delivery pipeline. This 2015 figure continues to be
reproduced in subsequent trade press without apparent revision, and no independent confirmation of
strength has surfaced since.

The set itself is reported to have a maximum throughput on the order of 230 units, with a secondary
capability claimed by the manufacturer, Castellan Precision Import-Export Corporation (CPIEC).

Acquisition Background

Officials, speaking on condition of anonymity, characterised the set in 2013 as "already commissioned
in limited numbers," a characterisation that has not been formally retracted since. As of [publication
date not machine-readable in cached header], the operational status was described in near-identical
language by a separate industry newsletter, suggesting continued reliance on the same underlying 2013
sourcing rather than fresh reporting.

Installation sites are believed to include positions oriented toward the coastal approach and, per
unconfirmed reporting, a secondary group near the northern border sector, though this latter
installation has not been corroborated by survey available to this desk.

*[cached fetch truncated - remainder of record unavailable; full text requires subscriber access]*
```

### Mention structure

**the design** — 5 mention(s)

  - “The TL-40”
  - “the TL-40”
  - “the set”
  - “The set itself”
  - “the operational status”

  Licence: EXPLICIT_EQUIVALENCE (the opening states the export-variant-of relation) + UNAMBIGUOUS_ANAPHOR for the later definite NPs

  Licensing quote: > The TL-40 is the export variant of the Vanguard high-volume transfer set.

**AMBIGUOUS: bodies as a CARDINALITY, not as mentions** — 4 mention(s)

  - “two operational sections”
  - “per section equivalent”
  - “a third section reportedly in the delivery pipeline”
  - “a secondary group near the northern border sector”

  Licence: AMBIGUOUS — cardinality WITHOUT individuation. There are no two mentions to keep apart; there is one claim with a quantity, plus a prospective one, plus a fourth under-determined reference.

  Licensing quote: > places regional holdings at two operational sections (approximately six to ten skid units per section equivalent, figures vary by source) assigned to the Water Authority's Central Command, with a third section reportedly in the delivery pipeline

**a falsely-attributed role, stated with perfect syntax** — 1 mention(s)

  - “the manufacturer, Castellan Precision Import-Export Corporation (CPIEC)”

  Licence: EXPLICIT_EQUIVALENCE (acronym apposition) — clean syntax binding to a role the entity's own name contradicts ('Import-Export Corporation')

  Licensing quote: > claimed by the manufacturer, Castellan Precision Import-Export Corporation (CPIEC)

**ANTI-COREF: areas are not sites** — 3 mention(s)

  - “its southern transfer belt covering approaches to Brightwater and the coastal sector”
  - “positions oriented toward the coastal approach”
  - “near the northern border sector”

  Licence: Semantic — head-anchored area words (belt, sector, approach) denote responsibilities, not places a set sits

  Licensing quote: > believed to operate the TL-40 within its southern transfer belt covering approaches to Brightwater and the coastal sector

### Discriminators

- **operator** — STATED — and it CONFLICTS with fixtures S1/S2, which assign this design to the other authority. Operator is critical-if-present, so this is a genuine conflict, arriving from a stale low-grade source.
- **geography** — AREAS ONLY — belts, sectors and approaches. No site, no coordinates. A relocation trigger cannot fire on 'the coastal sector'.
- **designation** — ABSENT for every one of the four body references
- **time** — DECLARED UNUSABLE by the document itself ('[publication date not machine-readable in cached header]'). Only a cache-retrieval stamp (2015) and a last-modified header (2013) exist, and they are two years apart.

### Presence vs formation

**Formation, as a bare cardinality.** The only fixture that treats organizational bodies as countable objects, and it individuates none of them. Basing is stated only as areas of responsibility. Nothing licenses either a body-at-a-site or an equipment-at-a-site claim.

### Required outcome (prose — choose your own mechanism and values)

The count must NOT become two body nodes: a cardinality is not two referents, and minting two invents individuals the source never named — while discarding the number loses the only establishment figure available. The faithful output is one under-determined organizational claim carrying the count as a sourced attribute, plus a separate, clearly PROSPECTIVE row for the third. The generic composition must route to the DESIGN layer, not to any instance: apply the routing test — would this fact change if a different operator fielded the same design? It would not. Routing it to an instance manufactures a sighting of six skid units that nobody observed. The operator conflict with the other fixtures must be flagged rather than averaged or silently overridden by grade, and the reason matters: this source is not merely lower-grade, it is EIGHT YEARS EARLIER, so the operator could genuinely have changed. The role attribution is a clean apposition binding to a role the entity's own name contradicts — clean syntax is not evidence of a true relation, and on this fixture alone there is nothing available to refute it, so it must be carried weakly and flagged, never established. The areas must not satisfy any site-level claim. The numeric attribute here conflicts with the SAME designator's value in S1 and S2, so numeric agreement cannot be a merge signal and numeric disagreement cannot be a wall.

### Negative gold — spans that must produce NO claim

- The truncated tail ('*[cached fetch truncated...]*') — the record is cut off mid-sentence and must not be completed.
- The comparative paragraph about unrelated programmes.
- 'As of [publication date not machine-readable in cached header]' — the time slot is stated unusable and must not be filled with the cache-retrieval date as though it were a publication date.

---

## Cross-fixture notes

**Three things only become visible across fixtures, and they are deliberate.**

1. **S2 says two designators name distinct designs; S3 says one is 'sometimes rendered' as the other;
   S6 uses both designators at one site in an overlapping window.** No single fixture can resolve
   this. Run together, they are the cross-document identity problem in miniature, and the honest
   outcome is a flagged contradiction held for a human — not a merge, not a wall.
2. **S1/S2 assign the design to one operator; S7 assigns it to the other, eight years earlier.** The
   operator discriminator must be able to *conflict*, and the conflict must survive as a conflict.
   Resolving it by source grade alone is wrong here, because the low-grade source is also the old one.
3. **The numeric capacity attribute differs across S1, S2 and S7 for the same designator.** So on this
   data, numeric attribute agreement is not evidence of identity and numeric disagreement is not
   evidence against it. Any mechanism that leans on attribute agreement must survive that.

**And one shape that is absent on purpose, because the real corpus does not contain it:** nowhere in
these seven fixtures does a source name a *designated* organizational body AND the site it is based
at. S1 names a body without a designation or a site; S3 names a higher command and an anonymous
section; S7 counts sections and assigns them to a command, never to a place. Every basing is
therefore derived. If a fixture is later needed where a *stated* body-at-site basing reaches full
confirmation, it has to be authored — it cannot be abstracted from anything that exists.
