# RK-SPIKE — claim-gold slice (hand-labeled)

`schema_version: rk-spike-claim-gold/1.0` · machine-readable twin: `claim-gold.json`

Seven frozen-corpus documents, hand-labeled claim by claim. The slice is chosen for the
**hard shapes**, not for volume: every document earns its place by carrying a structural difficulty the
identity re-key has to survive.

**What a row is.** One row per claim the document *states*. `doc_ref_span` is copied verbatim from the
frozen corpus, with a line number for locatability. A label with no quotable span is not a label. Where a
document does not state something, the slot is `unknown` — never inferred from context. Where a span is
genuinely ambiguous, it is marked `AMBIGUOUS` with the reason, rather than resolved by guessing.

**Scoping rule, stated so the denominator is honest.** Rows cover every claim in the ontology's domain —
entities of declared node types, their declared attributes, relations among them, and stated
equivalence/anti-identity — plus two categories the plan asked for explicitly: `UNMODELLED:` (the document
states something the declared ontology cannot express) and `ANTI_COREF:` / `NOT_A_CLAIM:` (negative gold).
Purely ceremonial or administrative prose is excluded and the exclusion is listed per document, so a
scorer knows what was deliberately left out.

**`NOT_A_CLAIM:` and `ANTI_COREF:` rows are negative gold and matter as much as the positive rows.** The
first are spans that look claim-shaped and assert nothing — modals, enumerated alternatives, explicit
refusals to confirm, document noise; an extractor that emits a claim on one of them has fabricated it, and
fabrication is this project's one disqualifying failure. The second are mention pairs that must not be
bound into one referent. There are 17 negative-gold rows across the slice, plus 19 `UNMODELLED:`
rows recording relations the declared ontology cannot express and 2 explicitly unresolved pairs.

## Which document covers which shape

| Target shape | Document(s) |
|---|---|
| rich within-document coreference (Tier-0 workhorse) | d02_ispr_induction (primary); d19, d17b also carry chains |
| explicit stated equivalence | d05_customs_manifest (identifier-backed, strongest); d04 (prose alias); d02, d19 (hedged) |
| two distinct instances co-exist / anti-merge | d05 (three declarations, hard-ID licensed); d19 (two dispersal sites, enumerated); d04 (two variants, stated contrast); cs01 (a count with no individuation) |
| thin context -> must degrade to gap | d17b_withheld_gap (primary); d20 (unlocatable destinations); d05 (broker-note depot) |
| structured / tabular | d05_customs_manifest |
| low-grade / deceptive source | d20_supersede_spoof (grade E, adversary); cs01_stale_orbat (stale-as-current, grade C) |

**Target shapes the frozen corpus cannot supply** (each is a finding the data pass owes — detail in
`DATA-FINDINGS.md`):

1. **A stated formation-at-site basing.** No document in the slice — and, on a corpus-wide check, no
   document at all — names a *designated* formation and the site it is based at. Confirms the plan's
   §B6 gap.
2. **Two same-type FORMATION instances that must not merge.** The corpus has this shape at *site* level
   (d19's Sialkot/Pasrur), at *event* level (d05's three declarations) and at *design* level (d04's two
   variants) — but never two individuated formations. cs01 gives a cardinality, not two mentions. The
   OOB-undercount trap (two batteries at one garrison) is not authored.
3. **Any unit-level discriminator.** No designation, no serial, no unit marking anywhere. Five of the
   seven slice documents state its absence explicitly.
4. **Two genuinely independent sources on one instance.** Within the slice, d19 is the only document
   claiming multi-signal corroboration, and all of its signals sit inside one self-declared aggregator.

## Field and vocabulary reference

| Field | Meaning |
|---|---|
| `row_id` / `doc_id` | Stable row handle; source document. |
| `subject_surface` / `object_surface` | The surface strings as the document writes them — not canonical ids. |
| `predicate` | See the vocabulary below. |
| `tier3_attributes` | Verbatim attribute values the document supplies for this claim. |
| `doc_ref_span` | **Verbatim quote.** The evidence for the label. |
| `doc_ref_line` | Line number in the frozen document. |
| `polarity` | `positive` / `negative` / `unknown`. |
| `coref_cluster` | Doc-local cluster label assigned here; see each document's cluster table. |
| `discriminators` | `operator` / `geography` / `designation` / `time`. Filled **only** if the document states it; otherwise `unknown`. |
| `evidence_mode` | *(extra field)* How the document holds the claim — see below. |
| `notes` | Why the label is what it is; findings and traps. |

**`predicate` vocabulary**

- `<ontology edge_type>` — A relationship claim on a declared edge from config/ontology.yaml (based-at, observed-at, inducted-into, imported-by, exported-by, equips, supplies-component, manufactures, design-authority-for, component-of, replenishes).
- `same-as / distinct-from` — A stated equivalence / stated anti-identity. Routed through the merge channel, not as a triple. object_surface is the other surface form.
- `ENTITY_EXISTS` — The document asserts an entity of a declared node type exists. object_surface = the node type.
- `ATTR:<attr>` — The document states a value for a declared attribute of the subject. object_surface = the verbatim value.
- `EVENT:<EventType>` — The document states an occurrence of a declared event_type. object_surface = the participants.
- `UNMODELLED:<desc>` — The document states a relation or entity the declared ontology cannot express. A finding, not a failure — recorded so the gap is countable.
- `ANTI_COREF:<reason>` — Two mentions that must NOT be bound into one referent, where the licence is structural/semantic rather than a stated distinct-from. Negative gold for coref binding.
- `AMBIGUOUS:<question>` — A pair the document leaves genuinely unresolved. The correct output is the pair surfaced as unresolved with the missing discriminator named — neither a merge nor a distinct-from. The highest-value rows in the slice.
- `NOT_A_CLAIM:<reason>` — Span that looks claim-shaped but asserts nothing (modal, prospective, meta-commentary, refusal, document noise). NEGATIVE gold: an extractor that emits a claim here commits a precision error.

**`evidence_mode` values**

- `stated` — The document asserts it in its own voice, unhedged.
- `stated-hedged` — Asserted, but with an explicit epistemic hedge (reportedly / believed to be / assessed as).
- `stated-attributed` — The document reports someone else's assertion without endorsing it.
- `negative-observation` — The document asserts the ABSENCE of something it looked for.
- `derived-required` — The fact is not stated; reaching it requires inference beyond this document.
- `not-a-claim` — No assertion is made in this span.

**Coreference licensing categories** (the three real categories; per the verified code facts, these are the only ones any mechanism can derive today)

- `EXPLICIT_EQUIVALENCE` — the document states the identity (apposition, acronym expansion, "also known as", "formerly", "see also", a registry rename).
- `NAME_VARIANT` — the same designator rendered differently (punctuation, casing, abbreviation, spelling drift).
- `UNAMBIGUOUS_ANAPHOR` — a definite back-reference ("the unit", "the site", "it") with exactly one candidate antecedent in the discourse.
- `AMBIGUOUS` — the document does not settle whether two mentions co-refer. **These are the most valuable rows in the slice** and are called out per document.

**Mention strings in `documents[].coref_clusters[].mentions` are ANNOTATED, not always verbatim.** All 120 mentions occur verbatim in their document EXCEPT 13 (all in `d20_supersede_spoof`'s four clusters and `d17b-AMBIG-1`) which carry a trailing annotator locator in parentheses — "(Post 3)", "(Post 4, a retweet of Post 1)", "(this report's AOI)". The locator is which post the mention came from, which the flat text cannot otherwise express; it is annotation, not document text. Any scorer doing exact-match against document spans MUST strip a trailing parenthetical before comparing. Verified 2026-07-25: with that one normalization, 120/120 mentions and 120/120 licensing quotes are verbatim. `doc_ref_span` on the 125 claim rows needs no such normalization — 125/125 are verbatim as written, at the stated line.

**Two different cluster counts exist and must not be conflated.** `counts.coref_clusters: 32` is the size of the CURATED registry in `documents[].coref_clusters` — the multi-mention chains with a licensing category, licensing quote and mention list; that registry is the coref gold a bake-off would score against. Separately, the `coref_cluster` tag on claim rows takes 48 distinct values: the 32 registry clusters plus 16 ad-hoc tags minted for rows that sit outside a curated chain (`*-C*-gap`, `*-C*-source`, extra `*-AMBIG-*` tags, `-` for none). Those 16 are row bookkeeping, NOT scoreable coref clusters, and mostly have a single member. One registry cluster (`d17b-C2-baseline`, 4 mentions) is legitimately used by no claim row — it is a coref chain over prose that states no ontology-domain claim. Documented 2026-07-25; no labels changed.

**Slice totals:** 7 documents · 125 claim rows · 32 coreference clusters · 17 negative-gold rows · 19 `UNMODELLED:` rows · 27 negative-polarity claims.

---

## `d02_ispr_induction`

**Source:** official · grade **B** · bias *operator-state* · dated 2021-10-14  
**Path:** `corpus/scenarios/hq9p_primary/docs/d02_ispr_induction.txt`  
**Shapes covered:** rich within-document coreference (Tier-0 workhorse); explicit stated equivalence (acronym apposition); count-absence -> gap

The Tier-0 workhorse. One official press release carries **four** separate coreference chains
(the system, the unit, the site, the COAS) in 30 lines, three of them with a full
named-form -> short-form -> definite-back-reference ladder. It is also the doc where the
*absence* of a discriminator is stated out loud: the TEL count is explicitly withheld, and the
formation is never named. Grade B but an interested party (operator-state).

### Presence vs formation

**Formation, weakly.** The doc names an induction *into a unit* ("a Pakistan Army Air Defence
(PAAD) unit") — an organizational recipient, which is formation-shaped evidence, not a bare
equipment sighting. But the formation carries **no designation and no echelon**, and the place named
is an *establishment* (the Army Air Defence Centre) rather than a field site. So: a formation is
licensed to exist, its identity is not; and **no `based-at` is stated** — the induction happened at
a Centre, which is not a claim that the unit is *based* there. Any Karachi basing is
**derived-required**.

### AMBIGUOUS — flagged

1. `HIMADS = HQ-9/P` is hedged by "reportedly" — the doc does not commit.
2. `HQ-9P` / `FD-2000` appear only inside a **family** parenthetical ("the Chinese Hongqi-9
   (HQ-9P/FD-2000 family)"). That licenses a family-level alias set, **not** the variant-level
   identity `FD-2000 ≡ HQ-9/P`. Binding it at variant level over-reads the source.
3. "Army Air Defence" (the arm of service, L13/L19) and "a Pakistan Army Air Defence (PAAD) unit"
   (the formation, L11) are different referents that share almost every token. This is the highest-risk
   over-bind in the doc.

### Coreference clusters

**`d02-C1-system`** — referent: *variant* · 7 mention(s) · licence: **EXPLICIT_EQUIVALENCE + UNAMBIGUOUS_ANAPHOR**

  - “a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P”
  - “the newly commissioned system”
  - “The system”
  - “the system's engagement envelope”
  - “this state-of-the-art air defence system”
  - “the system's induction”
  - “the newly commissioned system”

  Licensing quote: > a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P

  The apposition licenses HIMADS<->this-system. The later definite NPs ('The system', 'the newly commissioned system') are unambiguous anaphors — exactly one system is in the discourse. Binding is tight; the *designator* attached to it is hedged.

**`d02-C2-unit`** — referent: *unit* · 4 mention(s) · licence: **UNAMBIGUOUS_ANAPHOR**

  - “a Pakistan Army Air Defence (PAAD) unit”
  - “the newly raised/re-equipped unit”
  - “troops of the unit”
  - “the officers of the unit”

  Licensing quote: > The COAS, addressing the officers and troops of the newly raised/re-equipped unit

  Definite 'the unit' with exactly one unit in the discourse. The acronym expansion 'Pakistan Army Air Defence (PAAD)' is an EXPLICIT_EQUIVALENCE but it names the *arm*, so it licenses the branch attribute, not the formation's identity.

**`d02-C3-site`** — referent: *basing_site* · 2 mention(s) · licence: **NAME_VARIANT**

  - “ARMY AIR DEFENCE CENTRE, KARACHI”
  - “the Army Air Defence Centre, Karachi”

  Licensing quote: > COAS VISITS ARMY AIR DEFENCE CENTRE, KARACHI

  Headline caps vs body title case — same referent, casing variant only.

**`d02-C4-person`** — referent: *UNMODELLED (no person node type)* · 4 mention(s) · licence: **EXPLICIT_EQUIVALENCE + UNAMBIGUOUS_ANAPHOR**

  - “The Chief of Army Staff (COAS), General Qamar Javed Bajwa”
  - “the COAS”
  - “He”
  - “The COAS”

  Licensing quote: > The Chief of Army Staff (COAS), General Qamar Javed Bajwa, today visited

  A textbook 4-mention chain (title apposition, acronym, pronoun) whose referent type the ontology does not declare. Perfect coref evidence with nowhere to land.

**`d02-AMBIG-1`** — referent: *unit vs arm-of-service* · 3 mention(s) · licence: **AMBIGUOUS**

  - “a Pakistan Army Air Defence (PAAD) unit”
  - “senior officers of Army Air Defence”
  - “Army Air Defence remains fully prepared”

  Licensing quote: > On arrival, the COAS was received by the General Officer Commanding and senior officers of Army Air Defence.

  AMBIGUOUS -> resolved to ANTI-COREF. 'Army Air Defence' is the arm of service; 'a Pakistan Army Air Defence (PAAD) unit' is one formation within it. Near-total token overlap, different referents, and the doc never contrasts them explicitly.

### Claim rows

**`d02-r01`** · `ENTITY_EXISTS`

  - subject: “Inter-Services Public Relations (ISPR)”
  - object: “source”
  - tier-3 attributes: `source_type` = “PRESS RELEASE”
  - span (L4): > Inter-Services Public Relations (ISPR)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C0-source`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: The artifact form is stated in the header line 'PRESS RELEASE' (L1); the issuer is L4. Grade and bias are registry values, NOT stated by the doc.

**`d02-r02`** · `ENTITY_EXISTS`

  - subject: “a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P”
  - object: “variant”
  - span (L11): > where a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P, was formally inducted into service
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d02-C1-system`
  - discriminators — operator: Pakistan Army Air Defence (PAAD) · geography: the Army Air Defence Centre, Karachi · designation: unknown · time: 14 October 2021
  - notes: 'reportedly' hedges the designator, not the existence.

**`d02-r03`** · `same-as`

  - subject: “High to Medium Air Defence System (HIMADS)”
  - object: “HQ-9/P”
  - span (L11): > a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d02-C1-system`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: EXPLICIT_EQUIVALENCE by apposition, hedged 'reportedly'. CAUTION: HIMADS is a capability CLASS ('high to medium air defence system'), not a designator — it must not become a global alias that pulls in every other HIMADS.

**`d02-r04`** · `inducted-into`

  - subject: “HQ-9/P”
  - object: “a Pakistan Army Air Defence (PAAD) unit”
  - span (L11): > was formally inducted into service with a Pakistan Army Air Defence (PAAD) unit
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C2-unit`
  - discriminators — operator: Pakistan Army Air Defence (PAAD) · geography: the Army Air Defence Centre, Karachi · designation: unknown · time: 14 October 2021
  - notes: The strongest claim in the doc. The object end is an UNNAMED formation — no designator, no echelon. This is formation-shaped evidence with no formation identity.

**`d02-r05`** · `ENTITY_EXISTS`

  - subject: “the Army Air Defence Centre, Karachi”
  - object: “basing_site”
  - tier-3 attributes: `site_type` = “Centre”; `coordinates` = “Karachi (bare parent-city toponym)”
  - span (L11): > today visited the Army Air Defence Centre, Karachi
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C3-site`
  - discriminators — operator: unknown · geography: Karachi (city precision only) · designation: unknown · time: unknown
  - notes: An establishment/training centre, not a firing position. Geography is city-precision at best; the doc gives no grid, no district.

**`d02-r06`** · `ATTR:family`

  - subject: “The system”
  - object: “Chinese Hongqi-9”
  - span (L15): > The system, believed to be a variant of the Chinese Hongqi-9 (HQ-9P/FD-2000 family) long-range surface-to-air missile
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d02-C1-system`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: 'believed to be' hedge.

**`d02-r07`** · `same-as`

  - subject: “HQ-9/P”
  - object: “FD-2000”
  - span (L15): > a variant of the Chinese Hongqi-9 (HQ-9P/FD-2000 family)
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d02-AMBIG-2`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **AMBIGUOUS.** The parenthetical names a FAMILY ('HQ-9P/FD-2000 family'), so it licenses a family-level alias set only. Reading it as the variant-level identity FD-2000 == HQ-9/P over-reads this document. d04 states it properly; d02 does not.

**`d02-r08`** · `ATTR:range_km`

  - subject: “The system”
  - object: “well beyond 100 km”
  - span (L15): > is understood to extend Pakistan's ground-based air defence envelope well beyond 100 km
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d02-C1-system`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: A statement about the *national air-defence envelope*, not a clean intercept-range figure for the round. Recording it as variant.range_km is already an interpretation.

**`d02-r09`** · `ATTR:service_branch`

  - subject: “a Pakistan Army Air Defence (PAAD) unit”
  - object: “Pakistan Army”
  - span (L11): > into service with a Pakistan Army Air Defence (PAAD) unit
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C2-unit`
  - discriminators — operator: Pakistan Army · geography: unknown · designation: unknown · time: unknown
  - notes: The ONE operator discriminator this doc supplies, and it is stated cleanly. Contrast cs01, which assigns the same design to the Pakistan AIR FORCE.

**`d02-r10`** · `ATTR:count_state`

  - subject: “a Pakistan Army Air Defence (PAAD) unit”
  - object: “"sufficient numbers"”
  - span (L17): > said only that "sufficient numbers" had been commissioned to meet operational requirements in the assigned area of responsibility
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d02-C2-unit`
  - discriminators — operator: Pakistan Army · geography: unknown · designation: unknown · time: unknown
  - notes: A background-briefing non-figure. count_state must stay the literal string; it is not a number and must never be coerced into one.

**`d02-r11`** · `ENTITY_EXISTS`

  - subject: “the exact number of batteries/launchers (TELs) inducted”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “battery/launcher (TEL) count”; `observability_ceiling` = “stated policy of non-disclosure”
  - span (L17): > The exact number of batteries/launchers (TELs) inducted was not disclosed, in keeping with the Army's standing practice of not releasing order-of-battle details for sensitive air defence assets.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d02-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Absence stated in the source's own voice, with the REASON. This is the model case for 'insufficient evidence, and here is why coverage will not improve'.

**`d02-r12`** · `NOT_A_CLAIM:prospective-modal`

  - subject: “further inductions”
  - object: “-”
  - span (L17): > and that further inductions may follow in a phased manner
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `-`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. A modal about the future. An extractor that mints a second induction/import event here has fabricated one.

**`d02-r13`** · `UNMODELLED:integrated-into-c2-network`

  - subject: “the newly commissioned system”
  - object: “the Command, Control, Communication and Intelligence Air Defence (CLIAD) network”
  - span (L13): > integration of the newly commissioned system within the Command, Control, Communication and Intelligence Air Defence (CLIAD) network
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C1-system`
  - discriminators — operator: Pakistan Army · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: the ontology has no C2/network node type and no integrated-into edge, so a stated architectural dependency is unrepresentable. Also a clean acronym apposition (EXPLICIT_EQUIVALENCE) that has nowhere to bind.

**`d02-r14`** · `UNMODELLED:person-visits-site`

  - subject: “The Chief of Army Staff (COAS), General Qamar Javed Bajwa”
  - object: “the Army Air Defence Centre, Karachi”
  - span (L11): > The Chief of Army Staff (COAS), General Qamar Javed Bajwa, today visited the Army Air Defence Centre, Karachi
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C4-person`
  - discriminators — operator: unknown · geography: the Army Air Defence Centre, Karachi · designation: unknown · time: 14 October 2021
  - notes: FINDING: the richest, least ambiguous coref chain in the doc (4 mentions incl. a pronoun) belongs to a type the ontology does not declare. A coref evaluator scored on ontology-typed mentions only would never see it.

**`d02-r15`** · `ANTI_COREF:arm-of-service-is-not-the-formation`

  - subject: “senior officers of Army Air Defence”
  - object: “a Pakistan Army Air Defence (PAAD) unit”
  - span (L13): > the COAS was received by the General Officer Commanding and senior officers of Army Air Defence
  - polarity: `negative` · evidence mode: `derived-required` · cluster: `d02-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD, and the doc's biggest over-bind trap: 'Army Air Defence' (arm) shares nearly every token with 'Pakistan Army Air Defence (PAAD) unit' (formation). The doc never contrasts them, so the licence to keep them apart is semantic, not stated.

**`d02-r16`** · `EVENT:InductionEvent`

  - subject: “HQ-9/P”
  - object: “participants: HQ-9/P; a Pakistan Army Air Defence (PAAD) unit”
  - tier-3 attributes: `count_state` = “"sufficient numbers"”; `location` = “Army Air Defence Centre, Karachi”; `event_time` = “2021-10-14”
  - span (L11): > Rawalpindi – 14 October 2021: The Chief of Army Staff (COAS), General Qamar Javed Bajwa, today visited the Army Air Defence Centre, Karachi, where a new High to Medium Air Defence System (HIMADS), reportedly the HQ-9/P, was formally inducted into service with a Pakistan Army Air Defence (PAAD) unit.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d02-C1-system`
  - discriminators — operator: Pakistan Army Air Defence (PAAD) · geography: the Army Air Defence Centre, Karachi · designation: unknown · time: 14 October 2021
  - notes: The event form of r04, kept as its own row because the event carries the location and the count_state that the bare relationship does not.

### Deliberately excluded from the rows

Ceremonial/administrative prose with no ontology-relevant content: the guard of honour and
group photograph (L23), the contact block (L26-30), and the Pakistan-China "defence cooperation"
sentiment (L19, a state-level relation with no declared node type).

---

## `d04_armyrec_ranges`

**Source:** trade_media · grade **C** · bias *third-party* · dated 2021-10  
**Path:** `corpus/scenarios/hq9p_primary/docs/d04_armyrec_ranges.txt`  
**Shapes covered:** two distinct instances co-exist (contrastive / anti-merge); explicit stated equivalence (name variants); negative-polarity acquisition claim

The contrastive case, argued explicitly. One trade article puts two same-family, same-country
designs side by side, discriminated **only by operator and range**, and then states in its own voice
that they are not the same thing. It also carries a clean negative: a third designator that is
*named* and *explicitly not acquired* — the false-merge trap with its refutation attached.

### Presence vs formation

**Neither, cleanly.** The doc talks about *deployments* and *variants*, never about a named
formation at a named site, and says so: it asked for "unit numbers, basing locations" and got no
answer. "The Army's battalions" (plural, L9) is a bare echelon plural with no designator and no
site — a count-shaped hint, not a formation. Nothing here licenses a `based-at`; nothing here even
licenses an `observed-at`, because no site is named.

### AMBIGUOUS — flagged

1. "Nearly three years after induction was first confirmed by open-source imagery" (L5) dates the
   first confirmed induction to ~2018-19, while d02 (also October 2021) reports the *formal*
   induction as 2021-10-14. Within this doc alone the induction time is genuinely under-determined,
   and the doc offers no reconciliation.
2. Whether CASIC is asserted as the manufacturer of **HQ-9/P** or only of **HQ-9BE** is ambiguous:
   the apposition "the manufacturer, China Aerospace Science and Industry Corporation (CASIC)" sits
   inside a sentence about the HQ-9BE range figure.
3. "the Chinese-origin HQ-9 family" (L5) is a *family* referent, not either variant. Binding it to
   HQ-9/P collapses the type/instance distinction the whole replumb is about.

### Coreference clusters

**`d04-C1-hq9p`** — referent: *variant* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE**

  - “a battery-level deployment reportedly designated HQ-9/P”
  - “HQ-9P”
  - “the export designation FD-2000”
  - “The Army variant”
  - “the Army's HQ-9/P”

  Licensing quote: > a battery-level deployment reportedly designated HQ-9/P (some regional trade reporting still uses HQ-9P, and the export designation FD-2000 continues to circulate in older brochures, particularly from the system's original 2015-era marketing push)

  The parenthetical states, in the author's voice, that HQ-9P and FD-2000 are other designations FOR THIS SYSTEM. This is the slice's cleanest prose alias statement.

**`d04-C2-hq9be`** — referent: *variant* · 5 mention(s) · licence: **UNAMBIGUOUS_ANAPHOR**

  - “a longer-ranged variant referred to in most recent trade literature as the HQ-9BE”
  - “this variant, procured under a separate contract”
  - “the PAF variant”
  - “the HQ-9BE variant”
  - “the PAF's HQ-9BE”

  Licensing quote: > the Pakistan Air Force is believed to operate a longer-ranged variant referred to in most recent trade literature as the HQ-9BE. PAF sourcing suggests this variant, procured under a separate contract

  'this variant' immediately follows its antecedent; 'the PAF variant' is licensed by the operator contrast the doc itself draws.

**`d04-C3-ft2000`** — referent: *variant* · 3 mention(s) · licence: **NAME_VARIANT**

  - “the FT-2000 (sometimes rendered FT-2000A)”
  - “the FT-2000”
  - “"FT-2000 batteries"”

  Licensing quote: > the FT-2000 (sometimes rendered FT-2000A)

  Explicit rendering variant. Note the third mention is inside a quoted claim the doc attributes to others and rejects.

**`d04-C4-casic`** — referent: *manufacturer* · 3 mention(s) · licence: **EXPLICIT_EQUIVALENCE**

  - “the manufacturer, China Aerospace Science and Industry Corporation (CASIC)”
  - “CASIC markets”
  - “CASIC promotional material”

  Licensing quote: > not clarified by either Islamabad or the manufacturer, China Aerospace Science and Industry Corporation (CASIC)

  Acronym apposition. Binds tightly as a name; what it is the manufacturer OF is the ambiguous part.

**`d04-ANTI-1`** — referent: *variant vs variant* · 2 mention(s) · licence: **AMBIGUOUS -> resolved by stated contrast**

  - “The Army variant”
  - “the PAF variant”

  Licensing quote: > despite the shared "HQ-9" family name, the Army and PAF systems appear to be genuinely separate procurement lines rather than a single system fielded twice — different missile rounds, reportedly different engagement radars

  THE contrastive-prior licence in the slice: an explicit 'not one thing fielded twice', hedged with 'appear to be'. Everything else about the two (family, country, maker, customer) agrees, so name+relational evidence pushes toward merge and only the stated contrast plus operator+range holds them apart.

### Claim rows

**`d04-r01`** · `ENTITY_EXISTS`

  - subject: “a battery-level deployment reportedly designated HQ-9/P”
  - object: “variant”
  - tier-3 attributes: `export_designator` = “HQ-9/P”; `family` = “HQ-9”; `operator_branch` = “The Pakistan Army's Air Defence Command”
  - span (L7): > The Pakistan Army's Air Defence Command operates a battery-level deployment reportedly designated HQ-9/P
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-C1-hq9p`
  - discriminators — operator: The Pakistan Army's Air Defence Command · geography: unknown · designation: unknown · time: October 2021
  - notes: 'reportedly designated' hedges the designator only.

**`d04-r02`** · `same-as`

  - subject: “HQ-9/P”
  - object: “HQ-9P”
  - span (L7): > some regional trade reporting still uses HQ-9P
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-C1-hq9p`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: EXPLICIT_EQUIVALENCE, unhedged. Slash-vs-no-slash variant.

**`d04-r03`** · `same-as`

  - subject: “HQ-9/P”
  - object: “FD-2000”
  - span (L7): > the export designation FD-2000 continues to circulate in older brochures, particularly from the system's original 2015-era marketing push
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-C1-hq9p`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: EXPLICIT_EQUIVALENCE at VARIANT level (contrast d02-r07, which is family-level only). This is the row that licenses the FD-2000 alias merge.

**`d04-r04`** · `ATTR:range_km`

  - subject: “The Army variant”
  - object: “in the region of 125 km”
  - span (L7): > The Army variant is generally credited with an engagement range in the region of 125 km
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-C1-hq9p`
  - discriminators — operator: The Pakistan Army's Air Defence Command · geography: unknown · designation: unknown · time: unknown
  - notes: Doubly hedged ('generally credited', 'in the region of') and disowned at L19 as 'indicative rather than authoritative'. Conflicts with cs01's 200 km for the SAME designator.

**`d04-r05`** · `ENTITY_EXISTS`

  - subject: “a longer-ranged variant ... the HQ-9BE”
  - object: “variant”
  - tier-3 attributes: `export_designator` = “HQ-9BE”; `family` = “HQ-9”; `operator_branch` = “the Pakistan Air Force”
  - span (L9): > the Pakistan Air Force is believed to operate a longer-ranged variant referred to in most recent trade literature as the HQ-9BE
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-C2-hq9be`
  - discriminators — operator: the Pakistan Air Force · geography: unknown · designation: unknown · time: October 2021
  - notes: 'is believed to operate'.

**`d04-r06`** · `ATTR:range_km`

  - subject: “the PAF variant”
  - object: “around 260 km”
  - span (L9): > with a publicly estimated maximum intercept range around 260 km, roughly double that credited to the Army's battalions
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-C2-hq9be`
  - discriminators — operator: the Pakistan Air Force · geography: unknown · designation: unknown · time: unknown
  - notes: Range is the second of the only two discriminators separating C1 from C2.

**`d04-r07`** · `distinct-from`

  - subject: “HQ-9/P”
  - object: “HQ-9BE”
  - span (L11): > It is worth stressing that despite the shared "HQ-9" family name, the Army and PAF systems appear to be genuinely separate procurement lines rather than a single system fielded twice — different missile rounds, reportedly different engagement radars
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-ANTI-1`
  - discriminators — operator: Pakistan Army vs Pakistan Air Force · geography: unknown · designation: unknown · time: unknown
  - notes: THE anti-merge row of the slice. Stated in the author's voice but hedged ('appear to be'). Grade C, single source. An honest system reaches 'probable distinct', not 'confirmed distinct', on this evidence alone.

**`d04-r08`** · `UNMODELLED:differs-in-component`

  - subject: “the Army and PAF systems”
  - object: “different missile rounds, reportedly different engagement radars”
  - span (L11): > different missile rounds, reportedly different engagement radars, and, per at least one regional analyst briefing seen by this publication, possibly different fire-control architectures
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-ANTI-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: the ontology can say A equips B, but cannot say 'A and A-prime differ in their equipping components without naming them'. The single most load-bearing piece of anti-identity evidence in the doc is unrepresentable.

**`d04-r09`** · `ENTITY_EXISTS`

  - subject: “the FT-2000 (sometimes rendered FT-2000A)”
  - object: “variant”
  - tier-3 attributes: `range_class` = “lower-tier, medium-range derivative”; `seeker` = “passive anti-radiation seeker”
  - span (L13): > CASIC markets a lower-tier, medium-range derivative — the FT-2000 (sometimes rendered FT-2000A) — which uses a passive anti-radiation seeker rather than the semi-active radar homing employed by the HQ-9 family proper
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-C3-ft2000`
  - discriminators — operator: unknown · geography: unknown · designation: FT-2000 / FT-2000A · time: unknown
  - notes: 'seeker' is NOT a declared variant attribute — recorded verbatim as a tier-3 attribute so the discriminating fact is not lost.

**`d04-r10`** · `distinct-from`

  - subject: “the FT-2000”
  - object: “the HQ-9 family proper”
  - span (L13): > which uses a passive anti-radiation seeker rather than the semi-active radar homing employed by the HQ-9 family proper
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-C3-ft2000`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: A stated technical differentia (seeker type) — the strongest form of anti-identity evidence available in this corpus, and it is on the DESIGN layer, not the instance layer.

**`d04-r11`** · `UNMODELLED:has-not-acquired`

  - subject: “Pakistan”
  - object: “the FT-2000”
  - span (L13): > There is no confirmed evidence that Pakistan has acquired the FT-2000
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d04-C3-ft2000`
  - discriminators — operator: Pakistan · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: no edge type can carry 'operator X does not operate design Y'. The ontology has no operated-by / fielded-by edge at all — operator is only an attribute — so this negative, which is the direct refutation of the false-merge trap, has nowhere to go.

**`d04-r12`** · `UNMODELLED:refutes-third-party-claim`

  - subject: “at least one erroneous claim in regional media that Pakistan operates "FT-2000 batteries"”
  - object: “this publication was unable to substantiate”
  - span (L13): > which has led to at least one erroneous claim in regional media that Pakistan operates "FT-2000 batteries" — a claim this publication was unable to substantiate through any primary Pakistani MoD or ISPR statement
  - polarity: `negative` · evidence mode: `stated` · cluster: `d04-C3-ft2000`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: a source explicitly refuting another source's claim is a first-class credibility signal, and there is no `refutes` / `contradicts`-with-target edge an extractor may emit (contradicts is derived-only).

**`d04-r13`** · `manufactures`

  - subject: “China Aerospace Science and Industry Corporation (CASIC)”
  - object: “the HQ-9BE”
  - span (L9): > is, as usual with Chinese export SAMs, not clarified by either Islamabad or the manufacturer, China Aerospace Science and Industry Corporation (CASIC)
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d04-C4-casic`
  - discriminators — operator: China · geography: unknown · designation: unknown · time: unknown
  - notes: **AMBIGUOUS which variant.** 'the manufacturer' is an apposition inside a sentence about the HQ-9BE range figure. It licenses CASIC-as-manufacturer-of-the-thing-under-discussion; whether that extends to HQ-9/P is not stated here.

**`d04-r14`** · `UNMODELLED:markets`

  - subject: “CASIC”
  - object: “the FT-2000”
  - span (L13): > CASIC markets a lower-tier, medium-range derivative — the FT-2000
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-C4-casic`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: 'markets' is not 'manufactures'. The ontology carries the distinction only as a manufacturer ATTRIBUTE (export_agent), so a stated marketing relation must either be dropped or silently upgraded to manufactures — the exact conflation d22/d23 exist to punish.

**`d04-r15`** · `UNMODELLED:prior-confirmation-time`

  - subject: “induction”
  - object: “nearly three years before October 2021”
  - span (L5): > Nearly three years after induction was first confirmed by open-source imagery
  - polarity: `positive` · evidence mode: `stated` · cluster: `d04-AMBIG-2`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: nearly three years before October 2021 (~2018-19)
  - notes: **AMBIGUOUS / cross-doc tension.** Dates first confirmed induction to ~2018-19, while d02 (same month) reports the formal induction as 2021-10-14. Recorded as stated; the reconciliation is not in this document. Flagged for DATA-C.

**`d04-r16`** · `ENTITY_EXISTS`

  - subject: “unit numbers, basing locations, or the precise contractual designations”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “unit numbers; basing locations; contractual designations”
  - span (L17): > Neither the Pakistan Army nor Air Force public affairs offices responded to requests for comment on unit numbers, basing locations, or the precise contractual designations used in the original procurement agreements.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d04-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: A stated collection gap covering exactly the three unit-level discriminators the replumb's priority ladder needs. Independent corroboration of the corpus-wide designation gap.

**`d04-r17`** · `UNMODELLED:has-not-confirmed`

  - subject: “Chinese state media”
  - object: “export of the HQ-9BE variant specifically to Pakistan”
  - span (L17): > Chinese state media, for its part, has never officially confirmed export of the HQ-9BE variant specifically to Pakistan
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d04-C2-hq9be`
  - discriminators — operator: China / Pakistan · geography: unknown · designation: unknown · time: unknown
  - notes: Absence of confirmation by an interested party — a credibility input with no carrier.

**`d04-r18`** · `ANTI_COREF:family-is-not-a-variant`

  - subject: “the Chinese-origin HQ-9 family”
  - object: “HQ-9/P”
  - span (L5): > Pakistan's use of the Chinese-origin HQ-9 family remains one of the more under-reported developments in South Asian air defence
  - polarity: `negative` · evidence mode: `derived-required` · cluster: `d04-AMBIG-3`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. The family term is the parent of BOTH C1 and C2 in this doc. Binding it to either variant is the type/instance collapse; the doc even says the two share the family name and are not one system.

### Deliberately excluded from the rows

The S-400/Triumf/SA-21 comparative aside (L15) and the low-RCS/jamming caveat prose — an
off-subject third-country system mentioned only for comparison, with no claim about it.

---

## `d19_rahwali_confirm`

**Source:** reference · grade **B** · bias *third-party* · dated 2025-04-04  
**Path:** `corpus/scenarios/hq9p_primary/docs/d19_rahwali_confirm.txt`  
**Shapes covered:** presence vs formation (the load-bearing case); explicit stated equivalence that the document itself disclaims; two other same-type instances (enumeration); multi-signal corroboration inside ONE document

The presence/formation crux, and the slice's most instructive equivalence. A grade-B digest
states equipment at a site across two optical passes plus an ELINT relay, gives a *count range* with
its own confidence caveat, names two other dispersal sites in passing — and states an alias
(`HQ-9BE` = `HQ-9P`) while simultaneously warning that the designator mapping is unreliable. It also
asserts a redeployment **without naming where from**.

### Presence vs formation

**Presence, not formation — and this is the borderline an implementer will get wrong.** The doc
says "this is the first collection cycle to associate a PAF/Army Air Defence Command HQ-9BE ...
battery with the location". A *command* is named; the *battery* is not. An anonymous battery
attributed to a named higher command is **not a named formation**, so this is an `observed-at`
presence with a count attribute, and any `based-at` is **derived-required**. The trap is that the
sentence reads like an ORBAT association because a proper noun ("Air Defence Command") sits next to
the word "battery".

The count is a **presence attribute with its own sourced evidence and its own stated confidence** —
"Six TEL-pattern vehicles" (observed, 27 Mar) and "6-8 TELs" (estimated, low confidence on the 8).
Those are two different claims and must stay two rows; collapsing them invents precision.

### AMBIGUOUS — flagged

1. **`HQ-9B` vs `HQ-9BE` is generic-vs-specific, not identity.** L15 states HQ-9BE "sometimes
   rendered HQ-9P"; L19 warns of "continuing inconsistency ... in how Pakistani service designators
   map to the PLA domestic HQ-9B baseline versus the CASIC export HQ-9BE marketing designation" and
   says the digest uses "HQ-9B" *generically*. So one document supplies an explicit equivalence AND
   an explicit warning that the mapping is unreliable. **The honest label is AMBIGUOUS.**
2. The ELINT "corroboration" is asserted as co-located ("the same location") while the doc also
   states the vendor released "no further geolocation detail". The co-location is the desk's
   characterization, not a verifiable fix.
3. "consistent with a recent redeployment" asserts a move with **no origin site named anywhere in
   the document**. The supersede's other endpoint is not in this source.

### Coreference clusters

**`d19-C1-site`** — referent: *basing_site* · 7 mention(s) · licence: **UNAMBIGUOUS_ANAPHOR**

  - “Rahwali airfield (Pakistan Army/PAF joint-use facility, ~10 km NW of Gujranwala along the GT Road corridor, Punjab)”
  - “the site”
  - “the same general locale”
  - “the same location”
  - “this site”
  - “the location”
  - “an HQ-9-family site”

  Licensing quote: > a second, non-imagery indicator has closed some of the ambiguity around the site

  Definite anaphora with one site in focus. BUT 'the same general locale' / 'the same location' are the doc ASSERTING co-location for the ELINT fix whose geolocation it says was never released — bind the mentions, flag the corroboration.

**`d19-C2-presence`** — referent: *presence (equipment at site)* · 4 mention(s) · licence: **UNAMBIGUOUS_ANAPHOR**

  - “the TEL and battery-command cluster”
  - “Six TEL-pattern vehicles”
  - “a PAF/Army Air Defence Command HQ-9BE (export variant, sometimes rendered HQ-9P in Pakistani service literature) battery”
  - “Battery strength at this site”

  Licensing quote: > Battery strength at this site is estimated at 6–8 TELs plus one engagement radar and associated command/guidance van

  Ties 'battery' to the TEL cluster within one sentence. The referent is a PRESENCE; no formation designator appears anywhere in the document.

**`d19-C3-radar`** — referent: *component* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE (hedged)**

  - “a large octagonal engagement radar signature, believed to be the HT-233 fire-control/engagement radar”
  - “the radar hardstand”
  - “HT-233-band engagement-radar parameters”
  - “one engagement radar”
  - “the HT-233 identification”

  Licensing quote: > a large octagonal engagement radar signature, believed to be the HT-233 fire-control/engagement radar associated with the HQ-9B system

  The identification is explicitly NOT endorsed: 'Analysts should still treat the HT-233 identification itself as the vendor's characterization, not independently re-derived by this desk.' Bind the mentions; do not inherit the desk's authority for the type ID.

**`d19-AMBIG-1`** — referent: *variant* · 4 mention(s) · licence: **AMBIGUOUS**

  - “HQ-9B”
  - “HQ-9BE”
  - “HQ-9P”
  - “the HQ-9/HQ-9B/HQ-9BE/HQ-9P designator family”

  Licensing quote: > readers tracking the HQ-9/HQ-9B/HQ-9BE/HQ-9P designator family should note continuing inconsistency across open sources in how Pakistani service designators map to the PLA domestic HQ-9B baseline versus the CASIC export HQ-9BE marketing designation; this digest uses "HQ-9B" generically per prior issues unless a source specifies otherwise

  **THE most valuable row in the slice.** The source states an equivalence and then disclaims the mapping in the same document, and declares one of the four surfaces a GENERIC label. Generic-vs-specific is a refines relation, not identity — and the ontology cannot express it between two variants.

**`d19-C4-othersites`** — referent: *basing_site (x2, contrastive)* · 1 mention(s) · licence: **ANTI_COREF (stated enumeration)**

  - “the previously tracked Sialkot-area and Pasrur dispersal sites”

  Licensing quote: > No new activity to report at the previously tracked Sialkot-area and Pasrur dispersal sites this period; both remain in a "last confirmed" state from the 07 March pass.

  'both' makes the cardinality explicit: two distinct sites, same type, same operator, same region, adjacent in one clause, each with essentially no discriminating context. They must not merge with each other or with Rahwali.

### Claim rows

**`d19-r01`** · `ENTITY_EXISTS`

  - subject: “Rahwali airfield”
  - object: “basing_site”
  - tier-3 attributes: `site_type` = “airfield; Pakistan Army/PAF joint-use facility”; `coordinates` = “~10 km NW of Gujranwala along the GT Road corridor, Punjab (relative form, no grid)”
  - span (L11): > Rahwali airfield (Pakistan Army/PAF joint-use facility, ~10 km NW of Gujranwala along the GT Road corridor, Punjab)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C1-site`
  - discriminators — operator: Pakistan Army/PAF joint-use (DISJUNCTIVE) · geography: ~10 km NW of Gujranwala along the GT Road corridor, Punjab · designation: unknown · time: reporting period 24–31 March 2025
  - notes: The operator slot is STATED BUT DISJUNCTIVE ('Army/PAF'). A disjunctive operator is not a usable discriminator and must not be silently resolved to either service.

**`d19-r02`** · `observed-at`

  - subject: “the TEL and battery-command cluster”
  - object: “Rahwali airfield, in the northeast dispersal area”
  - tier-3 attributes: `observation_date` = “27 March”; `platform` = “Planet SkySat, 0.5m”; `arrangement` = “a fan arrangement”
  - span (L11): > commercial EO imagery collected 27 March (Planet SkySat, 0.5m) confirms the TEL and battery-command cluster first detected on the single-pass collection reported earlier this quarter, in the northeast dispersal area
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C2-presence`
  - discriminators — operator: Pakistan Army/PAF joint-use (DISJUNCTIVE) · geography: northeast dispersal area, Rahwali airfield · designation: unknown · time: 27 March 2025
  - notes: A PRESENCE claim. 'confirms ... first detected on the single-pass collection reported earlier this quarter' references an earlier report NOT in this slice — so the 'confirmation' partly rests on out-of-slice evidence.

**`d19-r03`** · `ATTR:count_state`

  - subject: “the TEL cluster at Rahwali”
  - object: “Six TEL-pattern vehicles”
  - tier-3 attributes: `basis` = “observed, 27 March pass”
  - span (L11): > Six TEL-pattern vehicles remain in a fan arrangement consistent with prior HQ-9B associated deployments elsewhere
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C2-presence`
  - discriminators — operator: unknown · geography: Rahwali airfield · designation: unknown · time: 27 March 2025
  - notes: An OBSERVED count. Keep separate from r04's estimate — one is counted, one is inferred.

**`d19-r04`** · `ATTR:count_state`

  - subject: “Battery strength at this site”
  - object: “estimated at 6–8 TELs plus one engagement radar and associated command/guidance van”
  - tier-3 attributes: `stated_confidence` = “confidence in the "8" upper bound remains low”
  - span (L15): > Battery strength at this site is estimated at 6–8 TELs plus one engagement radar and associated command/guidance van, though the desk's confidence in the "8" upper bound remains low given intermittent TEL visibility across passes
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d19-C2-presence`
  - discriminators — operator: unknown · geography: Rahwali airfield · designation: unknown · time: reporting period 24–31 March 2025
  - notes: An ESTIMATED range with the source's own confidence caveat attached. spine/13 3a: the count is an attribute of the presence with its own sourced evidence — never derived from how many reports merged.

**`d19-r05`** · `observed-at`

  - subject: “a large octagonal engagement radar signature, believed to be the HT-233 fire-control/engagement radar”
  - object: “its prepared hardstand roughly 380 m east of the TEL cluster, Rahwali airfield”
  - tier-3 attributes: `radar_band` = “HT-233-band”; `geometry` = “large octagonal”; `offset` = “roughly 380 m east of the TEL cluster”
  - span (L11): > a large octagonal engagement radar signature, believed to be the HT-233 fire-control/engagement radar associated with the HQ-9B system, is again visible on its prepared hardstand roughly 380 m east of the TEL cluster
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d19-C3-radar`
  - discriminators — operator: unknown · geography: Rahwali airfield, hardstand 380 m E of TEL cluster · designation: HT-233 (vendor characterization) · time: 27 March 2025
  - notes: The ONLY designation-shaped discriminator in the doc, and the doc disowns it: 'the vendor's characterization, not independently re-derived by this desk'.

**`d19-r06`** · `equips`

  - subject: “the HT-233 fire-control/engagement radar”
  - object: “the HQ-9B system”
  - span (L11): > believed to be the HT-233 fire-control/engagement radar associated with the HQ-9B system
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d19-C3-radar`
  - discriminators — operator: unknown · geography: unknown · designation: HT-233 · time: unknown
  - notes: The doc's verb is 'associated with', which is weaker than `equips`. Recording it as equips is already an upgrade — flagged so a scorer does not credit the stronger reading.

**`d19-r07`** · `ENTITY_EXISTS`

  - subject: “a commercial ELINT aggregator feed”
  - object: “source”
  - tier-3 attributes: `source_type` = “commercial ELINT aggregator feed, relayed via a third-party maritime/air RF-monitoring service”; `operator` = “not disclosed to subscribers”
  - span (L13): > A commercial ELINT aggregator feed (operator not disclosed to subscribers, relayed via a third-party maritime/air RF-monitoring service) logged an emitter-on fix in the same general locale during the reporting window
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d19-C5-sources`
  - discriminators — operator: unknown · geography: the same general locale · designation: unknown · time: during the reporting window
  - notes: FINDING: the second 'independent' signal is an UNNAMED vendor relayed through an unnamed intermediary, and the doc admits 'no further geolocation detail released at this subscription tier'. Its independence is asserted, not demonstrable, and it lives inside the same document as the first signal.

**`d19-r08`** · `observed-at`

  - subject: “a repeat optical pass on 29 March”
  - object: “the radar hardstand occupied and TEL count unchanged, Rahwali airfield”
  - tier-3 attributes: `platform` = “different collection platform than the 27 March pass”
  - span (L13): > Separately, a repeat optical pass on 29 March (different collection platform than the 27 March pass) again shows the radar hardstand occupied and TEL count unchanged.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C2-presence`
  - discriminators — operator: unknown · geography: Rahwali airfield · designation: unknown · time: 29 March 2025
  - notes: A third observation, same discipline (optical), different platform. Platform-independence is not discipline-independence.

**`d19-r09`** · `same-as`

  - subject: “HQ-9BE”
  - object: “HQ-9P”
  - span (L15): > a PAF/Army Air Defence Command HQ-9BE (export variant, sometimes rendered HQ-9P in Pakistani service literature) battery
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d19-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **AMBIGUOUS.** Stated as a rendering variant here, then explicitly disclaimed at L19. Also collides head-on with d04-r07, which states HQ-9/P and HQ-9BE are DISTINCT. On the slice these two docs are in direct conflict and neither can be preferred on grade alone (B vs C, but d04 argues the point and d19 disclaims its own).

**`d19-r10`** · `ANTI_COREF:generic-label-not-a-designator`

  - subject: “HQ-9B”
  - object: “HQ-9BE”
  - span (L19): > this digest uses "HQ-9B" generically per prior issues unless a source specifies otherwise
  - polarity: `negative` · evidence mode: `stated` · cluster: `d19-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. The doc declares one of its own surfaces a GENERIC label. Generic and specific are a refines relation; merging them as same-as loses the distinction between the design family and the export variant.

**`d19-r11`** · `observed-at`

  - subject: “a PAF/Army Air Defence Command HQ-9BE ... battery”
  - object: “Rahwali”
  - tier-3 attributes: `first_association` = “first collection cycle to associate ... with the location”
  - span (L15): > this is the first collection cycle to associate a PAF/Army Air Defence Command HQ-9BE (export variant, sometimes rendered HQ-9P in Pakistani service literature) battery with the location, consistent with a recent redeployment rather than a long-standing emplacement
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C2-presence`
  - discriminators — operator: PAF/Army Air Defence Command (DISJUNCTIVE) · geography: Rahwali · designation: unknown · time: reporting period 24–31 March 2025
  - notes: **THE presence/formation borderline.** A named COMMAND + an anonymous BATTERY is not a named formation, so this is `observed-at`, not a stated `based-at`. Getting this wrong mints a formation the source never named.

**`d19-r12`** · `UNMODELLED:recently-redeployed-from-unstated-origin`

  - subject: “the HQ-9BE battery at Rahwali”
  - object: “(origin site not named anywhere in the document)”
  - span (L15): > consistent with a recent redeployment rather than a long-standing emplacement
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `d19-C2-presence`
  - discriminators — operator: unknown · geography: Rahwali (destination only) · designation: unknown · time: recent, relative to 2025-03
  - notes: FINDING: the doc asserts a relocation but names NO origin. `supersedes` is derived-only in the ontology, so an extractor has no lane for a stated state-change, and the second endpoint does not exist in this source at all. The relocation is a cross-document construction.

**`d19-r13`** · `UNMODELLED:not-previously-cited-as`

  - subject: “Rahwali”
  - object: “an HQ-9-family site”
  - span (L15): > Rahwali had not previously been cited in open reporting as an HQ-9-family site
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d19-C1-site`
  - discriminators — operator: unknown · geography: Rahwali · designation: unknown · time: unknown
  - notes: A first_seen / novelty claim — a real integrity input with no declared carrier.

**`d19-r14`** · `ENTITY_EXISTS`

  - subject: “Sialkot-area dispersal site”
  - object: “basing_site”
  - tier-3 attributes: `occupancy_state` = “"last confirmed" state from the 07 March pass”; `site_type` = “dispersal site”
  - span (L17): > No new activity to report at the previously tracked Sialkot-area and Pasrur dispersal sites this period; both remain in a "last confirmed" state from the 07 March pass.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C4-othersites`
  - discriminators — operator: unknown · geography: Sialkot area · designation: unknown · time: 07 March pass
  - notes: THIN: named region, no coords, no equipment claim, no operator. Existence only.

**`d19-r15`** · `ENTITY_EXISTS`

  - subject: “Pasrur dispersal site”
  - object: “basing_site”
  - tier-3 attributes: `occupancy_state` = “"last confirmed" state from the 07 March pass”; `site_type` = “dispersal site”
  - span (L17): > No new activity to report at the previously tracked Sialkot-area and Pasrur dispersal sites this period; both remain in a "last confirmed" state from the 07 March pass.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C4-othersites`
  - discriminators — operator: unknown · geography: Pasrur · designation: unknown · time: 07 March pass
  - notes: THIN, as r14.

**`d19-r16`** · `distinct-from`

  - subject: “Sialkot-area dispersal site”
  - object: “Pasrur dispersal site”
  - span (L17): > the previously tracked Sialkot-area and Pasrur dispersal sites this period; both remain in a "last confirmed" state
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C4-othersites`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Stated by enumeration + explicit cardinality ('both'). This is the corpus's cleanest two-same-type-instances-that-must-not-merge case — but at SITE level, not formation level.

**`d19-r17`** · `distinct-from`

  - subject: “the previously tracked Sialkot-area and Pasrur dispersal sites”
  - object: “Rahwali airfield”
  - span (L17): > No new activity to report at the previously tracked Sialkot-area and Pasrur dispersal sites this period
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C4-othersites`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Contrasted with Rahwali by the paragraph structure ('No new activity ... at the previously tracked' vs the Rahwali paragraph's new detection).

**`d19-r18`** · `ENTITY_EXISTS`

  - subject: “IISS Military Balance+ / Open-Source Airpower Monitor”
  - object: “source”
  - tier-3 attributes: `source_type` = “Weekly Imagery & Signals Digest”; `aggregator_of` = “open commercial imagery, subscriber ELINT relay reporting, and prior digest issues (14 Feb 2025, 07 Mar 2025)”
  - span (L22): > Compiled from open commercial imagery, subscriber ELINT relay reporting, and prior digest issues (14 Feb 2025, 07 Mar 2025).
  - polarity: `positive` · evidence mode: `stated` · cluster: `d19-C5-sources`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: Issue dated: 04 April 2025
  - notes: The doc self-declares as an AGGREGATOR of three feeds and prior issues of itself. Its internal 'two independent signals' are therefore all inside one aggregating source.

**`d19-r19`** · `NOT_A_CLAIM:explicit-non-endorsement`

  - subject: “the HT-233 identification”
  - object: “-”
  - span (L13): > Analysts should still treat the HT-233 identification itself as the vendor's characterization, not independently re-derived by this desk.
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d19-C3-radar`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. The doc refuses to endorse the type ID. An extractor that credits d19 as an independent HT-233 identification has ignored an explicit disclaimer.

**`d19-r20`** · `NOT_A_CLAIM:decoy-risk-reasoning`

  - subject: “an imagery-only assessment”
  - object: “-”
  - span (L13): > an imagery-only assessment carried real decoy risk given the PLA/PAF's documented use of inflatable and radar-reflective decoy TELs at dispersal sites elsewhere in the region
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `-`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. Methodological reasoning about decoys 'elsewhere in the region'. Not a claim that decoys are at Rahwali; an extractor must not mint a decoy observation here.

### Deliberately excluded from the rows

Distribution/subscription boilerplate (L5, L21-22) and the "prior digest issues" citation
list, which name dates but assert no facts about the subject.

---

## `d05_customs_manifest`

**Source:** customs · grade **C** · bias *commercial* · dated 2020-11  
**Path:** `corpus/scenarios/hq9p_primary/docs/d05_customs_manifest.txt`  
**Shapes covered:** structured / tabular (shape unlike prose); explicit stated equivalence backed by a REGISTRY IDENTIFIER; three same-type instances that must not merge (over-merge trap); thin destination from a handwritten annotation

The structured source, and the only place in the slice where identity is licensed by an
**identifier** rather than by wording. Three customs declarations share a consignee, a shipper, an
HS-code family and — for two of them — a **container number**, so every relational and name signal
points at merging them; only their distinct GD and B/L references keep them apart. It is also the
doc whose stated end-use is **civil**, which makes every military reading of it derived.

### Presence vs formation

**Neither.** No equipment is observed at a site and no formation is named. The only place-like
objects are a **port of discharge** and a **final destination** from a handwritten broker note — and
the ontology has no port/facility node type, so the port has to be forced into `basing_site` or
dropped. The destination ("Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area") is a
relative fix from an unscanned annotation: existence-only.

### AMBIGUOUS — flagged

1. The document's own cross-reference note — the one place it starts to state an
   identity-match — is **truncated mid-token**: "Consignee ORIENT ELECTRO TRADING (PVT) LTD / ORI".
   An equivalence that the source began and the artifact cut off.
2. "SINO GALAXY IMP. & EXP. CO." (line 41) has no direct licence; it is only reachable through the
   "see also" on line 22. Near-certain, but transitively licensed.
3. "ref dwg HT233-" is truncated by scan damage, sits in an annex flagged "scan quality poor", and
   is interleaved with a pasted email fragment. It is a drawing reference on one line item — **not**
   a statement that the consignment contains an HT-233.
4. "Bin Qasim Town, Karachi" (the forwarder's address) is a TOWN, not the port terminal.

### Coreference clusters

**`d05-C1-consignee`** — referent: *trading_org* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE**

  - “ORIENT ELECTRO TRADING (PVT) LTD”
  - “ORIENT ELECTRO TRADING (PVT) LTD”
  - “ORIENT ELECTRO TRADING PVT LTD”
  - “ORIENT ELECTRONIC TRADING CO”
  - “Consignee ORIENT ELECTRO TRADING (PVT) LTD / ORI”

  Licensing quote: > ORIENT ELECTRO TRADING PVT LTD (formerly ORIENT ELECTRONIC TRADING CO -- name change ref SECP CUIN 0087762, 2019)

  The ONLY identifier-backed equivalence in the slice: a corporate-registry rename with a CUIN, plus an NTN on the first mention. Punctuation variants ('(PVT) LTD' vs 'PVT LTD') are NAME_VARIANTs on top of it.

**`d05-C2-shipper`** — referent: *trading_org* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE (line 22) + NAME_VARIANT**

  - “SINO-GALAXY IMP/EXP CO. LTD”
  - “SINO-GALAXY IMPEX CO, LTD”
  - “SINO GALAXY IMP. & EXP. CO.”
  - “SINO-GALAXY IMPEX CO, LTD”
  - “zhang.wei@sinogalaxy-export.cn”

  Licensing quote: > (see also SINO-GALAXY IMPEX CO, LTD -- inv. #SG-20-4471)

  'see also' + a shared invoice number licenses IMP/EXP <-> IMPEX. The third surface ('SINO GALAXY IMP. & EXP. CO.', no hyphen, spelled-out ampersand) is licensed only TRANSITIVELY. The email domain is a weak fourth signal.

**`d05-C3-port`** — referent: *place / port of discharge* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE (parenthetical abbreviation) + NAME_VARIANT**

  - “PORT MUHAMMAD BIN QASIM (PQ)”
  - “BIN QASIM”
  - “Port Qasim”
  - “QICT PQ”
  - “CIF PQ”

  Licensing quote: > Port of Discharge: PORT MUHAMMAD BIN QASIM (PQ)

  The '(PQ)' apposition licenses the abbreviation; the other surfaces are casing/shortening variants of the same port. Five surfaces, one referent, zero prose.

**`d05-C4-events`** — referent: *contract_import_event (x3, contrastive)* · 3 mention(s) · licence: **ANTI_COREF (distinct stated identifiers)**

  - “GD No: KPQA-HC-2020-118834”
  - “GD No: KPQA-HC-2020-118835”
  - “GD No: KPQA-HC-2020-119011”

  Licensing quote: > Container:       TCNU7712204 (shared, see line 118834)

  **THE over-merge trap.** Same consignee, same shipper, same HS-code family, and 118834/118835 SHARE A CONTAINER — so name similarity and shared neighbourhood both argue for merging. Only the distinct GD and B/L references say no. The doc's own cross-reference ('shared, see line 118834') proves it treats them as two lines, not one.

**`d05-AMBIG-1`** — referent: *place* · 2 mention(s) · licence: **AMBIGUOUS -> ANTI-COREF**

  - “Bin Qasim Town, Karachi”
  - “PORT MUHAMMAD BIN QASIM (PQ)”

  Licensing quote: > Freight Fwdr:    AL-NOOR CARGO SERVICES, Bin Qasim Town, Karachi

  A town and a port terminal sharing a name. Also 'Karachi International Container Terminal / QICT PQ' puts 'Karachi' inside the name of a terminal at Port Qasim — the geographic false-merge trap, entirely inside one document.

### Claim rows

**`d05-r01`** · `ENTITY_EXISTS`

  - subject: “KPQA-HC-2020-118834”
  - object: “contract_import_event”
  - tier-3 attributes: `gd_no` = “KPQA-HC-2020-118834”; `filing_date` = “04-11-2020”; `bl_no` = “YMLUW189234567”; `hs_code` = “8526.91.00”; `vessel` = “MV YM INCEPTION  Voy: 0091E   Line: Yang Ming (SCAC YMLU)”; `packages` = “14 WOODEN CRATES, gross wt 9,870 kg”; `containers` = “TCNU7712204 / TCNU7712341 (2 x 40ft HC)”; `declared_value` = “USD 612,400 (CIF PQ)”; `port_of_discharge` = “PORT MUHAMMAD BIN QASIM (PQ)”
  - span (L12): > GD No: KPQA-HC-2020-118834          Filing Date: 04-11-2020
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: PORT MUHAMMAD BIN QASIM (PQ) · designation: KPQA-HC-2020-118834 / B/L YMLUW189234567 · time: 04-11-2020
  - notes: The GD number and B/L number ARE the event's identity — the only hard identifiers in the slice.

**`d05-r02`** · `ENTITY_EXISTS`

  - subject: “KPQA-HC-2020-118835”
  - object: “contract_import_event”
  - tier-3 attributes: `gd_no` = “KPQA-HC-2020-118835”; `filing_date` = “04-11-2020”; `bl_no` = “YMLUW189234568”; `hs_code` = “8526.92.00”; `vessel` = “MV YM INCEPTION  Voy: 0091E”; `packages` = “6 CRATES, gross wt 4,120 kg”; `containers` = “TCNU7712204 (shared, see line 118834)”; `declared_value` = “USD 188,900”; `port_of_discharge` = “BIN QASIM”
  - span (L35): > GD No: KPQA-HC-2020-118835          Filing Date: 04-11-2020
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: BIN QASIM · designation: KPQA-HC-2020-118835 / B/L YMLUW189234568 · time: 04-11-2020
  - notes: Shares a container and a vessel voyage with r01 — maximum relational pull toward a merge that would corrupt the supply-chain count.

**`d05-r03`** · `ENTITY_EXISTS`

  - subject: “KPQA-HC-2020-119011”
  - object: “contract_import_event”
  - tier-3 attributes: `gd_no` = “KPQA-HC-2020-119011”; `filing_date` = “09-11-2020”; `bl_no` = “COSU6178820410”; `hs_code` = “8526.91.00”; `vessel` = “MV COSCO SHIPPING ARIES  Voy: 118W  Line: COSCO”; `packages` = “9 CRATES, gross wt 6,005 kg”; `containers` = “CSNU4402217”; `declared_value` = “USD 244,150”; `port_of_discharge` = “Port Qasim”; `exam` = “GREEN CHANNEL -- NO PHYSICAL EXAMINATION”
  - span (L68): > GD No: KPQA-HC-2020-119011          Filing Date: 09-11-2020
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: Port Qasim · designation: KPQA-HC-2020-119011 / B/L COSU6178820410 · time: 09-11-2020
  - notes: Different vessel, different line, different container.

**`d05-r04`** · `distinct-from`

  - subject: “KPQA-HC-2020-118834”
  - object: “KPQA-HC-2020-118835”
  - span (L48): > Container:       TCNU7712204 (shared, see line 118834)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Licensed by distinct GD/B/L identifiers AND by the doc's own cross-reference treating them as two lines. THE canonical over-merge case.

**`d05-r05`** · `distinct-from`

  - subject: “KPQA-HC-2020-118835”
  - object: “KPQA-HC-2020-119011”
  - span (L68): > GD No: KPQA-HC-2020-119011          Filing Date: 09-11-2020
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Distinct identifiers, dates, vessels.

**`d05-r06`** · `distinct-from`

  - subject: “KPQA-HC-2020-118834”
  - object: “KPQA-HC-2020-119011”
  - span (L68): > GD No: KPQA-HC-2020-119011          Filing Date: 09-11-2020
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Same HS code as 118834 — the shape most likely to be merged.

**`d05-r07`** · `ENTITY_EXISTS`

  - subject: “ORIENT ELECTRO TRADING (PVT) LTD”
  - object: “trading_org”
  - tier-3 attributes: `role` = “Consignee”; `place_ref` = “Suite 4-C, Sharae Faisal Commercial Complex, Karachi”; `ntn` = “3298761-4”
  - span (L18): > Consignee:       ORIENT ELECTRO TRADING (PVT) LTD
                 Suite 4-C, Sharae Faisal Commercial Complex,
                 Karachi -- NTN 3298761-4
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C1-consignee`
  - discriminators — operator: unknown · geography: Suite 4-C, Sharae Faisal Commercial Complex, Karachi · designation: NTN 3298761-4 · time: 04-11-2020
  - notes: The NTN is a national tax number — a hard identifier. Nothing in the doc calls this firm a shell or a front; that reading is derived.

**`d05-r08`** · `same-as`

  - subject: “ORIENT ELECTRO TRADING PVT LTD”
  - object: “ORIENT ELECTRONIC TRADING CO”
  - tier-3 attributes: `registry_ref` = “SECP CUIN 0087762, 2019”
  - span (L73): > ORIENT ELECTRO TRADING PVT LTD (formerly ORIENT ELECTRONIC TRADING CO -- name change ref SECP CUIN 0087762, 2019)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C1-consignee`
  - discriminators — operator: unknown · geography: unknown · designation: SECP CUIN 0087762 · time: unknown
  - notes: EXPLICIT_EQUIVALENCE with a registry citation — the strongest identity licence in the whole slice. Note the surfaces differ by a whole token ('ELECTRO' vs 'ELECTRONIC'), so string similarity alone would under-bind it.

**`d05-r09`** · `ENTITY_EXISTS`

  - subject: “SINO-GALAXY IMP/EXP CO. LTD”
  - object: “trading_org”
  - tier-3 attributes: `role` = “Shipper”; `origin_country` = “CHINA”; `origin_port` = “Tianjin Xingang”
  - span (L21): > Shipper:         SINO-GALAXY IMP/EXP CO. LTD
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C2-shipper`
  - discriminators — operator: CHINA · geography: Origin: Tianjin Xingang · designation: unknown · time: 04-11-2020
  - notes: Country appears as 'CHINA' here and 'China' at line 76 — the exact casing drift the config warns walls would misfire on.

**`d05-r10`** · `same-as`

  - subject: “SINO-GALAXY IMP/EXP CO. LTD”
  - object: “SINO-GALAXY IMPEX CO, LTD”
  - tier-3 attributes: `shared_ref` = “inv. #SG-20-4471”
  - span (L22): > (see also SINO-GALAXY IMPEX CO, LTD -- inv. #SG-20-4471)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C2-shipper`
  - discriminators — operator: unknown · geography: unknown · designation: inv. #SG-20-4471 · time: unknown
  - notes: EXPLICIT_EQUIVALENCE via 'see also' plus a shared invoice number.

**`d05-r11`** · `same-as`

  - subject: “SINO GALAXY IMP. & EXP. CO.”
  - object: “SINO-GALAXY IMP/EXP CO. LTD”
  - span (L41): > Shipper:         SINO GALAXY IMP. & EXP. CO.
  - polarity: `positive` · evidence mode: `derived-required` · cluster: `d05-C2-shipper`
  - discriminators — operator: CHINA · geography: unknown · designation: unknown · time: 04-11-2020
  - notes: **AMBIGUOUS.** No direct licence for this surface; it is only reachable transitively through line 22. Same consignee/vessel/voyage makes it near-certain, but the certainty comes from context, not from a stated equivalence.

**`d05-r12`** · `ENTITY_EXISTS`

  - subject: “AL-NOOR CARGO SERVICES”
  - object: “trading_org”
  - tier-3 attributes: `role` = “Freight Fwdr”; `place_ref` = “Bin Qasim Town, Karachi”; `aeo_cert` = “PK-AEO-0231”
  - span (L32): > Freight Fwdr:    AL-NOOR CARGO SERVICES, Bin Qasim Town, Karachi
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C6-forwarder`
  - discriminators — operator: unknown · geography: Bin Qasim Town, Karachi · designation: AEO Cert No. PK-AEO-0231 · time: 2020-11
  - notes: Third org in the doc, identifier-backed (AEO certificate). Its AEO status is what auto-cleared the risk flag.

**`d05-r13`** · `UNMODELLED:port-of-discharge`

  - subject: “PORT MUHAMMAD BIN QASIM (PQ)”
  - object: “KPQA-HC-2020-118834”
  - tier-3 attributes: `terminal_handler` = “Pakistan International Bulk Terminal”
  - span (L13): > Port of Discharge: PORT MUHAMMAD BIN QASIM (PQ)
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C3-port`
  - discriminators — operator: unknown · geography: PORT MUHAMMAD BIN QASIM (PQ) · designation: unknown · time: 04-11-2020
  - notes: FINDING: the ontology declares no port/facility node type — only `basing_site` and its `area_of_operations` refinement — and no edge from an import event to a place. A port of discharge must be forced into basing_site (wrong kind of thing) or dropped.

**`d05-r14`** · `UNMODELLED:consignee-of`

  - subject: “ORIENT ELECTRO TRADING (PVT) LTD”
  - object: “KPQA-HC-2020-118834”
  - span (L18): > Consignee:       ORIENT ELECTRO TRADING (PVT) LTD
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C1-consignee`
  - discriminators — operator: unknown · geography: Karachi · designation: NTN 3298761-4 · time: 04-11-2020
  - notes: **MAJOR FINDING.** The doc's core structure is event <-> consignee <-> shipper, and NONE of it is expressible: `imported-by` goes contract_import_event -> unit (no unit here) and `exported-by` goes contract_import_event -> manufacturer (the shipper is a trading_org). There is no edge between contract_import_event and trading_org at all, so the entire supply-chain intermediary layer this document exists to expose has no lane.

**`d05-r15`** · `UNMODELLED:shipper-of`

  - subject: “SINO-GALAXY IMP/EXP CO. LTD”
  - object: “KPQA-HC-2020-118834”
  - span (L21): > Shipper:         SINO-GALAXY IMP/EXP CO. LTD
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C2-shipper`
  - discriminators — operator: CHINA · geography: unknown · designation: unknown · time: 04-11-2020
  - notes: As r14: `exported-by` requires a manufacturer at the far end; a trading_org shipper does not type.

**`d05-r16`** · `ATTR:event_subtype`

  - subject: “KPQA-HC-2020-118834”
  - object: “"RADAR APPARATUS PARTS / ELECTRONIC ASSEMBLY -- SPARE, FOR INDUSTRIAL NAVIGATION AID, NOT FOR RESALE, 1 LOT"”
  - tier-3 attributes: `hs_code` = “8526.91.00”
  - span (L27): > Description (as filed): "RADAR APPARATUS PARTS / ELECTRONIC ASSEMBLY -- SPARE,
                 FOR INDUSTRIAL NAVIGATION AID, NOT FOR RESALE, 1 LOT"
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 04-11-2020
  - notes: CRITICAL: the STATED end-use is CIVIL ('INDUSTRIAL NAVIGATION AID'; line 80 says 'CIVIL AIR NAVIGATION AID SYSTEM'). Every military reading of this document is derived, and the gold must not launder it into a stated fact.

**`d05-r17`** · `ATTR:model_designation`

  - subject: “SERVO DRIVE UNIT, AZ/EL, QTY 2”
  - object: “ref dwg HT233-”
  - span (L53): > Item 2  -- SERVO DRIVE UNIT, AZ/EL, QTY 2 .......... ref dwg HT233-
  - polarity: `positive` · evidence mode: `stated` · cluster: `d05-C5-ht233ref`
  - discriminators — operator: unknown · geography: unknown · designation: HT233- (TRUNCATED) · time: 04-11-2020
  - notes: **AMBIGUOUS and the must-degrade case.** The only textual link from this shipment to HT-233 is a drawing reference, truncated mid-token, inside an annex the doc labels 'scan quality poor', interleaved with a pasted email. It states a drawing reference on ONE line item. It does NOT state that the consignment is an HT-233 part, and any `equips`/`supplies-component` edge from it is derived, not stated.

**`d05-r18`** · `ENTITY_EXISTS`

  - subject: “Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area”
  - object: “basing_site”
  - tier-3 attributes: `site_type` = “Depot”; `coordinates` = “~12 km NNW of Kala Chitta / Attock Cantt area (relative, no grid)”; `provenance` = “handwritten annotation on file copy”
  - span (L62): > Delivery instructions (broker note, handwritten annotation on file copy):
  "consignee to arrange onward clearance -- final destination Air Defence
  Depot, ~12 km NNW of Kala Chitta / Attock Cantt area, coordinate with
  local agent before release"
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d05-C7-destination`
  - discriminators — operator: unknown · geography: ~12 km NNW of Kala Chitta / Attock Cantt area · designation: unknown · time: 2020-11
  - notes: THIN + low-integrity: a handwritten broker annotation, relative geography, two alternative anchors ('Kala Chitta / Attock Cantt'). Existence only; nothing observed there, nobody based there.

**`d05-r19`** · `ENTITY_EXISTS`

  - subject: “End-user certificate”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “end-user certificate (ref. letter DGDP/IMP/2020/2246, copy not scanned)”
  - span (L60): > End-user certificate on file: NOT ATTACHED TO GD (ref. letter DGDP/IMP/2020/2246
cited in broker cover note, copy not scanned)
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d05-C8-gap`
  - discriminators — operator: unknown · geography: unknown · designation: DGDP/IMP/2020/2246 · time: 2020
  - notes: The single document that would establish end-use is cited but absent. Names exactly what is missing — the insufficient-evidence template's ideal input.

**`d05-r20`** · `ATTR:count_state`

  - subject: “KPQA-HC-2020-119011”
  - object: “EXAM TYPE: GREEN CHANNEL -- NO PHYSICAL EXAMINATION”
  - span (L86): >   EXAM TYPE: GREEN CHANNEL -- NO PHYSICAL EXAMINATION
  Risk flag auto-cleared by AEO status of freight forwarder (AL-NOOR CARGO
  SERVICES -- AEO Cert No. PK-AEO-0231)
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d05-C4-events`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 09-11-2020
  - notes: No physical inspection occurred, and the risk flag was auto-cleared by the forwarder's status. A stated reason the declared contents were never verified — an integrity input, not a supply-chain fact.

**`d05-r21`** · `ANTI_COREF:town-is-not-the-port-terminal`

  - subject: “Bin Qasim Town, Karachi”
  - object: “PORT MUHAMMAD BIN QASIM (PQ)”
  - span (L32): > Freight Fwdr:    AL-NOOR CARGO SERVICES, Bin Qasim Town, Karachi
  - polarity: `negative` · evidence mode: `derived-required` · cluster: `d05-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. A town and a seaport terminal sharing a name inside one document.

**`d05-r22`** · `ANTI_COREF:terminal-name-contains-a-different-city`

  - subject: “Karachi International Container Terminal / QICT PQ”
  - object: “Karachi (the city) / Port of Karachi”
  - span (L7): > Terminal:        Karachi International Container Terminal / QICT PQ
  - polarity: `negative` · evidence mode: `derived-required` · cluster: `d05-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. A terminal at Port Qasim whose NAME begins with 'Karachi'. Name-based geography would put this shipment at the wrong port, ~35 km away.

**`d05-r23`** · `NOT_A_CLAIM:truncated-and-self-disclaimed`

  - subject: “CROSS-REFERENCE NOTE (internal PRAL data-matching, non-adjudicative)”
  - object: “-”
  - span (L91): > CROSS-REFERENCE NOTE (internal PRAL data-matching, non-adjudicative):
Consignee ORIENT ELECTRO TRADING (PVT) LTD / ORI
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d05-AMBIG-2`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **AMBIGUOUS by truncation.** The one place the document begins to state an identity-match is cut off mid-token AND explicitly labelled 'non-adjudicative'. An extractor must not complete the sentence for it.

**`d05-r24`** · `NOT_A_CLAIM:pasted-email-noise`

  - subject: “FrOm: zhang.wei@sinogalaxy-export.cn / Subject: RE: shipping docs pkg 2”
  - object: “-”
  - span (L54): >              -- FrOm: zhang.wei@sinogalaxy-export.cn
             Subject: RE: shipping docs pkg 2 attached pls confirm
             consignee addr for CD papers, urgent -- thx
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d05-C2-shipper`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD for the subject line and 'FrOm' casing garble. The email DOMAIN (sinogalaxy-export.cn) is a weak corroborating signal for the shipper cluster and is recorded there; the message body asserts nothing about the subject.

### Deliberately excluded from the rows

Vessel/voyage/SCAC codes, gross weights, package counts and declared values are recorded as
tier-3 attributes of their event rather than as separate claim rows; the WeBOC batch header (L6-9)
asserts nothing about the subject.

---

## `d17b_withheld_gap`

**Source:** imagery · grade **B** · bias *third-party* · dated 2025-06-11  
**Path:** `corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.txt`  
**Shapes covered:** thin context -> must degrade to gap; an EXPLICIT refusal to co-refer (the crown-jewel ambiguous case); negative observation as evidence

The must-degrade-to-gap document, and the only one in the slice where a source **explicitly
declines to say whether two mentions are the same thing**. A grade-B imagery report checks a site it
can only name by a nickname borrowed from forum chatter, finds nothing, states that it finds nothing,
states that no unit marking has ever been visible, and states that it cannot establish whether the
forum's site and its site are the same footprint. Every discriminator slot is either empty or
explicitly declared empty.

### Presence vs formation

**Presence, negated — and the formation is explicitly disclaimed.** The doc records a negative
`observed-at` (no TELs at the site on this pass). It then says outright that the site's identity as
"the forward HQ-9/P site" "rests on prior open-source association rather than confirmed
order-of-battle documentation; no unit markings or signage visible in any pass to date". That is a
source telling you, in its own voice, that **no formation evidence exists** — the designation
discriminator is not merely absent, it is *stated absent across every pass*. No `based-at` is
statable; deriving one here would be fabrication.

### AMBIGUOUS — flagged

1. **The crown jewel:** "whether the two references concern the same site footprint could not be
   independently established from the forum post's description alone, as it gives no coordinates and
   describes the location only as 'near the port road, same as always'." A source explicitly
   refusing to bind two mentions. Gold label: `AMBIGUOUS`, and the honest system outcome is a gap,
   not a merge and not a silent split.
2. The site's own description is **internally inconsistent**: the subject line says "Southern
   Approaches" and the nickname says "the old Rawalpindi-area site near the port road turnoff".
   Rawalpindi is in northern Punjab and has no port road. The geography discriminator is therefore
   *unusable*, not merely coarse — and it must not be averaged into a coordinate.

### Coreference clusters

**`d17b-C1-site`** — referent: *basing_site* · 5 mention(s) · licence: **UNAMBIGUOUS_ANAPHOR**

  - “a suspected forward SAM deployment area”
  - “The site in question — referred to in prior open reporting simply as "the old Rawalpindi-area site" near the port road turnoff, not the garrison itself”
  - “the suspected forward site”
  - “the fenced compound”
  - “the forward HQ-9/P site”

  Licensing quote: > The area consistent with the suspected forward site shows the previously noted perimeter berm and access road configuration largely unchanged from the 2024-11 baseline.

  Definite anaphora with one site in focus, so the mentions bind. But the referent has NO name, NO coordinates and a self-contradictory location description — it is a well-bound cluster with an unidentifiable referent, which is exactly the 'under-determined + gap' outcome the design wants.

**`d17b-C2-baseline`** — referent: *prior observation* · 4 mention(s) · licence: **NAME_VARIANT**

  - “chip from 2024-11 pass (same vendor, cataloged separately)”
  - “the 2024-11 baseline”
  - “the 2024-11 chip”
  - “Baseline imagery (2024-11)”

  Licensing quote: > Prior baseline reference: chip from 2024-11 pass (same vendor, cataloged separately)

  A dated artifact referred to four ways. Binds on the date token.

**`d17b-AMBIG-1`** — referent: *basing_site (two references, unresolvable)* · 2 mention(s) · licence: **AMBIGUOUS**

  - “the suspected forward site (this report's AOI)”
  - “"fresh HQ-9/P TEL deployment confirmed near port road site, imagery pending"”

  Licensing quote: > whether the two references concern the same site footprint could not be independently established from the forum post's description alone, as it gives no coordinates and describes the location only as "near the port road, same as always."

  **THE most valuable ambiguity in the slice.** The source states, in its own voice, that co-reference cannot be established, and names the reason (no coordinates). Neither merging nor asserting distinctness is faithful; the only faithful output is 'same footprint unestablished — coordinates missing'.

### Claim rows

**`d17b-r01`** · `ENTITY_EXISTS`

  - subject: “"the old Rawalpindi-area site" near the port road turnoff”
  - object: “basing_site”
  - tier-3 attributes: `site_type` = “suspected forward SAM deployment area”; `coordinates` = “NONE STATED”; `naming_basis` = “referred to in prior open reporting simply as ...”
  - span (L9): > The site in question — referred to in prior open reporting simply as "the old Rawalpindi-area site" near the port road turnoff, not the garrison itself — was tasked for revisit collection this cycle
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: "the old Rawalpindi-area site" near the port road turnoff (SELF-INCONSISTENT) · designation: unknown · time: 2025-06-11
  - notes: The site's only name is a quoted nickname from forum reporting. Geography is self-inconsistent (see the ambiguity note). No coordinates anywhere in the document.

**`d17b-r02`** · `distinct-from`

  - subject: “"the old Rawalpindi-area site"”
  - object: “the garrison itself”
  - span (L9): > "the old Rawalpindi-area site" near the port road turnoff, not the garrison itself
  - polarity: `positive` · evidence mode: `stated` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: A STATED distinct-from on a site with no coordinates — anti-identity evidence that arrives before any identity evidence does. Worth noting the wall must hold even though neither endpoint is locatable.

**`d17b-r03`** · `observed-at`

  - subject: “transporter-erector-launchers (TELs)”
  - object: “any of the hardstands or along the access spur (the suspected forward site)”
  - tier-3 attributes: `platform` = “commercial EO, sub-meter resolution, pansharpened”; `cloud_cover` = “~15%, partial obscuration along the northern tree line”; `pass` = “2025-06-11 (single pass, ~1030 local)”
  - span (L22): > No transporter-erector-launchers (TELs) are visible on any of the hardstands or along the access spur at the time of this pass.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: the suspected forward site (unlocatable) · designation: unknown · time: 2025-06-11
  - notes: THE negative observation. Absence looked for and reported — evidence, not silence.

**`d17b-r04`** · `observed-at`

  - subject: “a possible radar trailer footprint”
  - object: “The cleared laydown area (the suspected forward site)”
  - tier-3 attributes: `comparison` = “in the 2024-11 chip showed what was assessed as a possible radar trailer footprint”
  - span (L22): > The cleared laydown area that in the 2024-11 chip showed what was assessed as a possible radar trailer footprint is empty in the current image.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: the cleared laydown area · designation: unknown · time: 2025-06-11 vs 2024-11 baseline
  - notes: A CHANGE claim: something assessed as present in Nov-2024 is absent now. Note the prior assessment was itself hedged ('possible').

**`d17b-r05`** · `observed-at`

  - subject: “canvas-covered or tarped objects of TEL-consistent dimensions”
  - object: “either the northern or southern pad clusters”
  - span (L22): > No canvas-covered or tarped objects of TEL-consistent dimensions were identified on either the northern or southern pad clusters.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: northern and southern pad clusters · designation: unknown · time: 2025-06-11
  - notes: A deliberate check for concealment, reported negative — strengthens the negative observation rather than merely repeating it.

**`d17b-r06`** · `observed-at`

  - subject: “unusual vehicle staging, generator trailers, or the tented storage typically associated with missile canister or spares handling”
  - object: “anywhere within the fenced compound”
  - span (L24): > No unusual vehicle staging, generator trailers, or the tented storage typically associated with missile canister or spares handling was noted anywhere within the fenced compound this pass
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: the fenced compound · designation: unknown · time: 2025-06-11
  - notes: Third independent negative indicator.

**`d17b-r07`** · `ATTR:occupancy_state`

  - subject: “the suspected forward site”
  - object: “a negative TEL presence observation for the pass window noted”
  - tier-3 attributes: `occupancy_observed_date` = “2025-06-11”
  - span (L34): > Current imagery is assessed as a negative TEL presence observation for the pass window noted.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 2025-06-11
  - notes: Scoped to the pass window — the doc does not claim the site is empty in general.

**`d17b-r08`** · `ATTR:site_signature_geometry`

  - subject: “the suspected forward site”
  - object: “perimeter berm and access road configuration; hardstand pads; northern and southern pad clusters; a cleared laydown area”
  - tier-3 attributes: `change_vs_baseline` = “largely unchanged from the 2024-11 baseline”
  - span (L20): > The area consistent with the suspected forward site shows the previously noted perimeter berm and access road configuration largely unchanged from the 2024-11 baseline.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: the suspected forward site · designation: unknown · time: 2025-06-11
  - notes: The only positive characterization of the site: infrastructure geometry. This is the sole discriminating content available for cross-document matching.

**`d17b-r09`** · `ENTITY_EXISTS`

  - subject: “unit markings or signage”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “unit markings / signage — absent in ANY pass to date”; `observability_ceiling` = “never observed across the full pass history”
  - span (L40): > no unit markings or signage visible in any pass to date
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d17b-C3-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **The designation discriminator declared absent across the entire collection history.** The strongest statement in the corpus that the top rung of the discriminator ladder has no data to stand on.

**`d17b-r10`** · `NOT_A_CLAIM:identity-rests-on-prior-association`

  - subject: “Site identity as "the forward HQ-9/P site"”
  - object: “-”
  - span (L40): > Site identity as "the forward HQ-9/P site" rests on prior open-source association rather than confirmed order-of-battle documentation
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d17b-C1-site`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD, and the most important row in the doc: the source disclaims its own site-to-system association. Crediting d17b with an HQ-9/P site claim ignores an explicit disclaimer.

**`d17b-r11`** · `AMBIGUOUS:same-footprint-unestablished`

  - subject: “the suspected forward site”
  - object: “"near port road site" (the Telegram-linked OSINT aggregator post)”
  - tier-3 attributes: `forum_claim_time` = “post dated 11 June, timestamped 0640Z”; `collection_time` = “2025-06-11 ~1030 local”; `forum_geography` = “"near the port road, same as always" (no coordinates)”
  - span (L30): > whether the two references concern the same site footprint could not be independently established from the forum post's description alone, as it gives no coordinates and describes the location only as "near the port road, same as always."
  - polarity: `unknown` · evidence mode: `stated` · cluster: `d17b-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **THE crown-jewel ambiguous row.** The source explicitly refuses to bind, and names the missing discriminator (coordinates). Correct behaviour: emit the pair as unresolved with the reason, not as a merge and not as a distinct-from.

**`d17b-r12`** · `observed-at`

  - subject: “"fresh HQ-9/P TEL deployment confirmed near port road site, imagery pending"”
  - object: “near port road site”
  - tier-3 attributes: `attributed_to` = “an unnamed "regional source"”; `carrier` = “a Telegram-linked OSINT aggregator”
  - span (L30): > A separate item circulating on a Telegram-linked OSINT aggregator (post dated 11 June, timestamped 0640Z — i.e., roughly four hours before the collection above) asserted that "fresh HQ-9/P TEL deployment confirmed near port road site, imagery pending," citing an unnamed "regional source."
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d17b-AMBIG-1`
  - discriminators — operator: unknown · geography: near port road site (no coordinates) · designation: unknown · time: 2025-06-11 0640Z
  - notes: A POSITIVE claim, reported not endorsed, that directly opposes r03's negative — but the doc says the two may not even be about the same place. The contradiction is itself unresolvable, which is the honest finding.

**`d17b-r13`** · `UNMODELLED:does-not-corroborate`

  - subject: “The present collection”
  - object: “the forum assertion of fresh TEL deployment”
  - span (L30): > The present collection does not corroborate the assertion; whether the two references concern the same site footprint could not be independently established
  - polarity: `negative` · evidence mode: `stated` · cluster: `d17b-AMBIG-1`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: 'does not corroborate' is neither `corroborates` nor `contradicts` — a third state (checked and failed to confirm) that the evidence layer cannot express.

**`d17b-r14`** · `ENTITY_EXISTS`

  - subject: “follow-up tasking”
  - object: “known_gap”
  - tier-3 attributes: `next_coverage_due` = “within the next 5–7 days”; `missing_slots` = “persistence of the negative finding; second-vendor cross-reference for the same window”
  - span (L34): > a follow-up tasking is recommended within the next 5–7 days to confirm persistence of the negative finding, ideally cross-referenced against a second vendor's catalog for the same window
  - polarity: `positive` · evidence mode: `stated` · cluster: `d17b-C3-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: within the next 5–7 days of 2025-06-11
  - notes: A stated next-coverage window — literally the 'and when next coverage is due' half of the non-negotiable, supplied by the source.

**`d17b-r15`** · `NOT_A_CLAIM:enumerated-alternatives`

  - subject: “the negative finding”
  - object: “-”
  - span (L34): > This does not preclude the possibility of dispersal, maintenance rotation to an unobserved facility, or a collection-timing gap relative to the forum claim referenced in Section 4.
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `-`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. Three alternatives listed, none asserted. An extractor that mints a dispersal or rotation claim here has fabricated one.

### Deliberately excluded from the rows

Collection metadata (platform, cloud percentage, sun angle) is carried as tier-3 attributes of
the observation rows rather than as separate claims.

---

## `d20_supersede_spoof`

**Source:** social · grade **E** · bias *adversary* · dated 2025-06  
**Path:** `corpus/scenarios/hq9p_primary/docs/d20_supersede_spoof.txt`  
**Shapes covered:** low-grade / deceptive source (grade E, adversary, decoy-risk flagged); one 'document' containing 8 posts from 6 handles — apparent multiplicity, single origin; internal contradiction on the object of a relocation; cross-post AMBIGUOUS coreference across two designators

The deception case, and the slice's hardest coreference problem. Eight posts, six handles, one
origin. The same alleged relocation is described with **two different destinations**; the battery is
named with **two different designators** that another slice document says are distinct; three posts
are explicit refusals to assert; and the one post carrying imagery language is dated a month before
the claim it appears to rebut.

### Presence vs formation

**Presence only, and mostly negated or unsourced.** No post names a formation. "btry" and
"battery" are echelon words with no designator, no service branch, no parent unit. The document
therefore cannot license a formation at all — and the relocation it asserts is a **formation-level**
claim (a thing that persists through a move), so on this evidence the honest output is "presence
claim unsourced; formation continuity unresolved". `based-at` is not statable; even `observed-at` is
only statable at grade E with no coordinates.

### AMBIGUOUS — flagged

1. **Two designators, one site, overlapping window.** Post 1 says "the HQ9B btry that was sitting
   at Rahwali"; Post 2 says "HQ-9/P (HIMADS) battery co-located near Rahwali airbase". d04 states
   HQ-9/P and HQ-9BE are *distinct*; d19 states HQ-9BE is *sometimes rendered HQ-9P*. So whether
   Posts 1 and 2 are about one battery is genuinely unresolvable, and getting it wrong either merges
   two distinct variants' presences or splinters one battery into two.
2. **Two destinations for one move.** Post 1: "moved out toward the old Rawalpindi site". Post 4 —
   a retweet *of Post 1* — "redeployed near the port road area allegedly". Post 7: "gone to new loc"
   (unnamed). One claim, echoed, arriving with contradictory objects.
3. **Post 2 is dated 2025-05-09**, a month before the relocation claim it appears to rebut. It
   cannot function as a contemporaneous denial, though it reads like one.

### Coreference clusters

**`d20-C1-battery`** — referent: *presence (equipment)* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE (retweet) + NAME_VARIANT**

  - “the HQ9B btry that was sitting at Rahwali”
  - “HQ9B out of Rahwali”
  - “HQ9B battery gone from Rahwali”
  - “whole btry gone to new loc”
  - “the "Rahwali empty" claim”

  Licensing quote: > RT @faisal_defencewatch huge if confirmed. HQ9B out of Rahwali, redeployed near the port road area allegedly.

  Posts 1, 4, 5, 7 and 8 are one claim: Post 4 is an explicit retweet, Post 5 says 'Following up on yesterday's report', Post 7 is the same author, Post 8 links back to Post 1 'as the sole source'. The equivalence is at the CLAIM level, so it licenses collapsing the corroboration count to ONE — the opposite of what a naive count does.

**`d20-C2-skeptics`** — referent: *source commentary* · 3 mention(s) · licence: **NAME_VARIANT (n/a — distinct handles)**

  - “@IndoPacSentry (Post 3)”
  - “@SushantNMehta (Post 6)”
  - “@grey_falcon_osint (Post 8)”

  Licensing quote: > per the Rahwali 'left the base' claim going around — cannot confirm, would want imagery before believing it. single unverified source afaik.

  Three posts that assert nothing about the world and instead characterize the claim's sourcing. Negative gold for extraction, positive gold for credibility.

**`d20-C3-origin`** — referent: *source* · 4 mention(s) · licence: **EXPLICIT_EQUIVALENCE**

  - “@faisal_defencewatch (Post 1)”
  - “@faisal_defencewatch (Post 7)”
  - “h/t retweet by @PakSkiesWatch”
  - “@faisal_defencewatch's original post as the sole source”

  Licensing quote: > linking back to @faisal_defencewatch's original post as the sole source

  The document names its own single origin. This is the too-clean / echo-burst licence, stated by one of the participants.

**`d20-AMBIG-1`** — referent: *presence — designator conflict* · 3 mention(s) · licence: **AMBIGUOUS**

  - “the HQ9B btry that was sitting at Rahwali (Post 1, 2025-06-11)”
  - “HQ-9/P (HIMADS) battery co-located near Rahwali airbase (Post 2, 2025-05-09)”
  - “an HQ-9/P 'move' out of Rahwali (Post 6, 2025-06-12)”

  Licensing quote: > Satellite imagery from earlier this year confirms HQ-9/P (HIMADS) battery co-located near Rahwali airbase, Gujranwala — consistent with the reported 2025 redeployment.

  **The hardest ambiguity in the slice.** Same site, overlapping window, two designators that d04 calls distinct and d19 calls interchangeable. Neither merging nor splitting is defensible from this document; the discriminator that would settle it (a unit designation) is absent from all eight posts.

**`d20-AMBIG-2`** — referent: *destination site — internal contradiction* · 3 mention(s) · licence: **AMBIGUOUS**

  - “the old Rawalpindi site (Post 1)”
  - “near the port road area (Post 4, a retweet of Post 1)”
  - “new loc (Post 7, unnamed)”

  Licensing quote: > RT @faisal_defencewatch huge if confirmed. HQ9B out of Rahwali, redeployed near the port road area allegedly.

  A retweet that changes the destination. One claim, three mutually incompatible objects, and no coordinates for any of them. The relocation's second endpoint does not exist in a determinable form anywhere in the document.

### Claim rows

**`d20-r01`** · `UNMODELLED:relocated-from-to`

  - subject: “the HQ9B btry that was sitting at Rahwali”
  - object: “Rahwali -> the old Rawalpindi site”
  - tier-3 attributes: `hedge` = “sources telling me”; `corroboration_offered` = “convoy was seen night time”
  - span (L6): > "exclusive 🚨 sources telling me the HQ9B btry that was sitting at Rahwali has QUIETLY relocated, gone since early this wk, moved out toward the old Rawalpindi site. nobody talking abt it openly but convoy was seen night time. big move if true 👀"
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d20-C1-battery`
  - discriminators — operator: unknown · geography: Rahwali -> the old Rawalpindi site (neither locatable) · designation: unknown · time: gone since early this wk (post dated 2025-06-11)
  - notes: FINDING: `supersedes` is derived-only, so a STATED relocation has no extractor lane. The best the ontology can do is two presence claims — one negative at Rahwali, one positive at an unlocatable destination. Note the poster's own hedge 'big move if true'.

**`d20-r02`** · `observed-at`

  - subject: “the HQ9B btry”
  - object: “Rahwali”
  - span (L6): > the HQ9B btry that was sitting at Rahwali has QUIETLY relocated, gone since early this wk
  - polarity: `negative` · evidence mode: `stated-attributed` · cluster: `d20-C1-battery`
  - discriminators — operator: unknown · geography: Rahwali · designation: unknown · time: early week of 2025-06-11
  - notes: The negative half of r01. Grade E, adversary bias, unnamed sources, no imagery.

**`d20-r03`** · `observed-at`

  - subject: “the HQ9B btry”
  - object: “the old Rawalpindi site”
  - span (L6): > moved out toward the old Rawalpindi site
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d20-AMBIG-2`
  - discriminators — operator: unknown · geography: the old Rawalpindi site (no name, no coords, 'old' as the only qualifier) · designation: unknown · time: early week of 2025-06-11
  - notes: The positive half. 'toward' is not 'at' — even the claimed arrival is hedged into a direction of travel.

**`d20-r04`** · `observed-at`

  - subject: “HQ-9/P (HIMADS) battery”
  - object: “near Rahwali airbase, Gujranwala”
  - tier-3 attributes: `claimed_basis` = “Satellite imagery from earlier this year”; `imagery_attached` = “none”
  - span (L14): > "Satellite imagery from earlier this year confirms HQ-9/P (HIMADS) battery co-located near Rahwali airbase, Gujranwala — consistent with the reported 2025 redeployment. No sign of it leaving per open-source imagery."
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d20-AMBIG-1`
  - discriminators — operator: unknown · geography: near Rahwali airbase, Gujranwala · designation: unknown · time: 2025-05-09 (~14:20 IST)
  - notes: **AMBIGUOUS designator** (see d20-AMBIG-1). Cites imagery it does not show. Dated a MONTH BEFORE the relocation claim, so it cannot be read as a contemporaneous rebuttal.

**`d20-r05`** · `UNMODELLED:has-not-left`

  - subject: “HQ-9/P (HIMADS) battery”
  - object: “near Rahwali airbase”
  - span (L14): > No sign of it leaving per open-source imagery.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d20-AMBIG-1`
  - discriminators — operator: unknown · geography: near Rahwali airbase · designation: unknown · time: 2025-05-09
  - notes: An absence-of-departure claim, which is not the same as a presence claim and has no lane. Also predates the departure claim by a month.

**`d20-r06`** · `observed-at`

  - subject: “HQ9B”
  - object: “near the port road area”
  - tier-3 attributes: `provenance` = “RT of Post 1”
  - span (L30): > "RT @faisal_defencewatch huge if confirmed. HQ9B out of Rahwali, redeployed near the port road area allegedly. keeping eyes open. anyone near GRW area can confirm convoy movement pls DM 🙏🙏"
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `d20-AMBIG-2`
  - discriminators — operator: unknown · geography: near the port road area (no coords) · designation: unknown · time: 2025-06-11
  - notes: **CONTRADICTS r03 while retweeting it.** Same origin claim, different destination. This is the row that proves an echo can *mutate* content, not merely repeat it.

**`d20-r07`** · `ATTR:primary_origin_id`

  - subject: “@PakSkiesWatch (Post 4)”
  - object: “@faisal_defencewatch”
  - tier-3 attributes: `relation` = “RT”
  - span (L30): > RT @faisal_defencewatch huge if confirmed.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d20-C3-origin`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 2025-06-11
  - notes: Explicit retweet marker: this post is derivative and must not add corroboration weight.

**`d20-r08`** · `observed-at`

  - subject: “HQ9B battery”
  - object: “Rahwali”
  - tier-3 attributes: `claimed_basis` = “per my contact”; `self_declared_relation` = “Following up on yesterday's report”
  - span (L38): > "Following up on yesterday's report — HQ9B battery gone from Rahwali per my contact, redeployment underway, will not disclose more for opsec reasons. trust the process 🇵🇰"
  - polarity: `negative` · evidence mode: `stated-attributed` · cluster: `d20-C1-battery`
  - discriminators — operator: unknown · geography: Rahwali · designation: unknown · time: 2025-06-12
  - notes: **AMBIGUOUS independence.** Claims a separate contact ('per my contact') while self-declaring as a follow-up to the origin post. Cannot be scored as independent, cannot be proven derivative. The honest label is 'independence unestablished'.

**`d20-r09`** · `observed-at`

  - subject: “whole btry”
  - object: “Rahwali site basically empty now allegedly”
  - span (L54): > "to ppl asking for proof — I don't share sources sorry 🙏 but trust me its moved. Rahwali site basically empty now allegedly, whole btry gone to new loc. more soon inshallah"
  - polarity: `negative` · evidence mode: `stated-attributed` · cluster: `d20-C1-battery`
  - discriminators — operator: unknown · geography: Rahwali; destination 'new loc' (UNNAMED) · designation: unknown · time: 2025-06-12
  - notes: Same author as Post 1, one day later, with an explicit refusal to source and a third (unnamed) destination. Same origin, so no corroboration.

**`d20-r10`** · `ATTR:coordinated_inauthenticity_flag`

  - subject: “@faisal_defencewatch”
  - object: “I don't share sources sorry”
  - span (L54): > to ppl asking for proof — I don't share sources sorry 🙏 but trust me its moved
  - polarity: `positive` · evidence mode: `stated` · cluster: `d20-C3-origin`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 2025-06-12
  - notes: An explicit refusal to source, from the sole origin of the whole cluster. The single most decisive credibility fact in the document.

**`d20-r11`** · `ATTR:primary_origin_id`

  - subject: “@grey_falcon_osint (Post 8)”
  - object: “@faisal_defencewatch's original post as the sole source”
  - tier-3 attributes: `aggregator_of` = “"several people are sharing this now"”
  - span (L61): > Account reposted the "Rahwali empty" claim without independent verification, adding only that "several people are sharing this now" and linking back to @faisal_defencewatch's original post as the sole source.
  - polarity: `positive` · evidence mode: `stated` · cluster: `d20-C3-origin`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 2025-06-13
  - notes: THE echo-collapse licence: an aggregator naming the single source, and citing volume ('several people are sharing this') as if it were corroboration.

**`d20-r12`** · `NOT_A_CLAIM:explicit-refusal-to-assert`

  - subject: “the Rahwali 'left the base' claim”
  - object: “-”
  - span (L22): > "per the Rahwali 'left the base' claim going around — cannot confirm, would want imagery before believing it. single unverified source afaik. treating with caution 🤷"
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d20-C2-skeptics`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. Asserts nothing about the world; it characterizes the claim's sourcing. An extractor that mints a relocation claim from Post 3 has inverted the post's meaning.

**`d20-r13`** · `NOT_A_CLAIM:explicit-refusal-to-assert`

  - subject: “an HQ-9/P 'move' out of Rahwali”
  - object: “-”
  - span (L46): > "Seeing chatter about an HQ-9/P 'move' out of Rahwali. No imagery, no second source, one guy's thread going viral. Would treat as unconfirmed until proven otherwise — this happens every few months with this site."
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `d20-C2-skeptics`
  - discriminators — operator: unknown · geography: Rahwali · designation: unknown · time: 2025-06-12
  - notes: NEGATIVE GOLD, plus two credibility facts stated outright: 'no second source' and 'one guy's thread'. It also supplies a base rate ('this happens every few months with this site') that nothing in the ontology can carry.

**`d20-r14`** · `ENTITY_EXISTS`

  - subject: “the battery / the formation”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “unit designation; service branch; coordinates for either endpoint; any imagery”
  - span (L46): > No imagery, no second source, one guy's thread going viral.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `d20-C4-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: Every discriminator slot in this document is empty: no post names a service branch, a designation, or a coordinate. The relocation is a FORMATION-level claim asserted with zero formation evidence.

**`d20-r15`** · `ENTITY_EXISTS`

  - subject: “@faisal_defencewatch (Post 1)”
  - object: “source”
  - tier-3 attributes: `source_type` = “social post”; `handle_self_description` = “Faisal Baig | Defence & Security tracker”; `citation_url` = “[link unavailable, account locked/protected — h/t retweet by @PakSkiesWatch]”
  - span (L2): > Handle: @faisal_defencewatch (Faisal Baig | Defence & Security tracker)
Date: 2025-06-11
Status URL: [link unavailable, account locked/protected — h/t retweet by @PakSkiesWatch]
  - polarity: `positive` · evidence mode: `stated` · cluster: `d20-C3-origin`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: 2025-06-11
  - notes: The origin post's own URL is unrecoverable — the claim cannot be traced to a live artifact, only to a retweet of it.

**`d20-r16`** · `AMBIGUOUS:same-presence-as`

  - subject: “the HQ9B btry (Post 1)”
  - object: “HQ-9/P (HIMADS) battery (Post 2)”
  - span (L6): > the HQ9B btry that was sitting at Rahwali
  - polarity: `unknown` · evidence mode: `derived-required` · cluster: `d20-AMBIG-1`
  - discriminators — operator: unknown · geography: Rahwali (both) · designation: HQ9B vs HQ-9/P — CONFLICTING · time: 2025-06-11 vs 2025-05-09
  - notes: **The highest-value ambiguity in the slice.** d04 says these two designators name DISTINCT variants; d19 says one is sometimes rendered as the other. Same site, overlapping window, no unit designator anywhere. Faithful output: one presence at Rahwali with an unresolved designator, not two presences and not one merged battery.

### Deliberately excluded from the rows

Follower counts, emoji, hashtags and dead-link notes are provenance/integrity metadata rather
than claims about the subject.

---

## `cs01_stale_orbat`

**Source:** reference · grade **C** · bias *third-party* · dated 2015-06 (cached); page last modified 2013-03  
**Path:** `corpus/scenarios/hq9p_chaff/docs/cs01_stale_orbat.txt`  
**Shapes covered:** formation COUNT with zero individuating discriminators (the OOB shape); operator discriminator that CONFLICTS with the rest of the corpus; design-layer composition stated as if it were an observation; stale-as-current + unusable publication time

The order-of-battle shape, and the operator-conflict case. A cached 2015 database record
(source page last modified 2013) states a **count of formations** — "two operational battalions ...
with a third battalion reportedly in the delivery pipeline" — with **no designator, no site, and no
individuating mention for any of them**. It also assigns the HQ-9/P to the **Pakistan Air Force**,
where d02 and d04 assign it to the **Army**, and names **CPMIEC** as the manufacturer, which the
wider corpus refutes. Chaff, and load-bearing chaff.

### Presence vs formation

**Formation, as a bare cardinality.** This is the only slice document that talks about
formations as countable objects — and it does so without individuating any of them. There are not
two mentions to keep apart; there is **one claim with quantity two** (plus a prospective third). The
honest representation is `unit.count_state` on a single under-determined formation claim, not two
formation nodes. spine/13 3a is exactly right here: the count is an attribute with its own sourced
evidence, and it must never come from how many reports merged.

Basing is stated only as **areas**, never as sites: "within its strategic air defence belt covering
approaches to Karachi and the Sindh coastal sector", "positions oriented toward the Arabian Sea
approach", "a secondary battery near the Punjab border sector". Those are areas of responsibility.
No `based-at` and no `observed-at` is statable.

### AMBIGUOUS — flagged

1. The battery composition ("one command-and-control vehicle, six single-stage TEL ... vehicles
   each carrying four missile canisters, associated HT-233 phased-array engagement radars") is a
   **design-layer generic**, not an observation of any particular battery. Routing it to an instance
   would fabricate a sighting. It is the cleanest layer-routing test in the slice.
2. "the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)" is a clean
   apposition — and, on the wider corpus, **false** (CPMIEC is the export agent). Within this slice
   there is nothing to refute it, so a slice-scoped oracle must carry it at `possible` with the
   conflation flagged, never as an established edge.
3. "As of [publication date not machine-readable in cached header]" — the document declares that its
   own publication time is unrecoverable. The time discriminator is *stated unusable*.

### Coreference clusters

**`cs01-C1-hq9p`** — referent: *variant* · 5 mention(s) · licence: **EXPLICIT_EQUIVALENCE + UNAMBIGUOUS_ANAPHOR**

  - “The HQ-9/P”
  - “the HQ-9/P”
  - “the system”
  - “The missile itself”
  - “Pakistani HQ-9/P batteries”

  Licensing quote: > The HQ-9/P is the export variant of China's HQ-9 long-range surface-to-air missile system

  The opening sentence states the export-variant-of relation explicitly. Later definite NPs ('the system', 'The missile itself') are unambiguous anaphors.

**`cs01-C2-formations`** — referent: *unit (a COUNT, not individuated mentions)* · 3 mention(s) · licence: **AMBIGUOUS (cardinality without individuation)**

  - “two operational battalions”
  - “a third battalion reportedly in the delivery pipeline”
  - “per battalion equivalent”

  Licensing quote: > places Pakistani holdings at two operational battalions (approximately eight to twelve TEL launchers per battalion equivalent, figures vary by source) assigned to the PAF's Central Air Command, with a third battalion reportedly in the delivery pipeline

  **The OOB shape.** A count with no designator and no site for any member. There is nothing to co-refer and nothing to keep apart — which is precisely why a system that counts merged reports as formations gets the order of battle wrong in both directions.

**`cs01-C3-cpmiec`** — referent: *manufacturer* · 1 mention(s) · licence: **EXPLICIT_EQUIVALENCE**

  - “the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)”

  Licensing quote: > claimed by the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)

  A textbook acronym apposition that binds cleanly to a FALSE role. Clean syntax is not evidence of a true relation.

**`cs01-C4-areas`** — referent: *area_of_operations* · 3 mention(s) · licence: **ANTI_COREF (areas are not sites)**

  - “its strategic air defence belt covering approaches to Karachi and the Sindh coastal sector”
  - “positions oriented toward the Arabian Sea approach”
  - “a secondary battery near the Punjab border sector”

  Licensing quote: > the Pakistan Air Force's Air Defence Command is believed to operate the HQ-9/P within its strategic air defence belt covering approaches to Karachi and the Sindh coastal sector

  Head-anchored area words (belt, sector, approach). These are responsibilities, not places a battery sits; a relocation tripwire cannot fire on 'the Sindh coastal sector'.

### Claim rows

**`cs01-r01`** · `ATTR:family`

  - subject: “The HQ-9/P”
  - object: “China's HQ-9 long-range surface-to-air missile system”
  - span (L9): > The HQ-9/P is the export variant of China's HQ-9 long-range surface-to-air missile system
  - polarity: `positive` · evidence mode: `stated` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: China (origin) · geography: unknown · designation: unknown · time: unknown
  - notes: FINDING: the ontology DROPPED `variant-of`, so a stated design-family relation can only be flattened into a `family` attribute. The refines relation between a family and its export variant — the exact type/instance distinction the replumb is about — has no edge.

**`cs01-r02`** · `UNMODELLED:operates`

  - subject: “the Pakistan Air Force's Air Defence Command”
  - object: “the HQ-9/P”
  - span (L11): > the Pakistan Air Force's Air Defence Command is believed to operate the HQ-9/P within its strategic air defence belt covering approaches to Karachi and the Sindh coastal sector
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: the Pakistan Air Force's Air Defence Command · geography: strategic air defence belt covering approaches to Karachi and the Sindh coastal sector · designation: unknown · time: As of this writing (cached 2015-06; page modified 2013-03)
  - notes: **THE operator conflict.** d02 states the HQ-9/P was inducted into a Pakistan ARMY unit and d04 states the ARMY operates HQ-9/P while the PAF operates HQ-9BE. This document assigns HQ-9/P to the PAF, over the same city (Karachi). Operator is a critical-if-present discriminator, so this is a genuine wall-triggering conflict — and it arrives from a stale, low-grade source. Also FINDING: there is no `operated-by`/`operates` edge in the ontology at all, so the conflict can only be seen if operator is captured as an attribute on both sides.

**`cs01-r03`** · `ATTR:equipment_fingerprint`

  - subject: “Battery composition”
  - object: “one command-and-control vehicle, six single-stage TEL (transporter-erector-launcher) vehicles each carrying four missile canisters, associated HT-233 phased-array engagement radars, and a search/acquisition radar element”
  - tier-3 attributes: `basis` = “estimated”; `comparison` = “broadly mirroring the PLA's own HQ-9 regimental structure”
  - span (L11): > Battery composition is estimated at one command-and-control vehicle, six single-stage TEL (transporter-erector-launcher) vehicles each carrying four missile canisters, associated HT-233 phased-array engagement radars, and a search/acquisition radar element, broadly mirroring the PLA's own HQ-9 regimental structure.
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **A DESIGN-layer fact, not an instance observation.** Apply the layer-routing test: would this change if a different operator fielded the same design? No. Routing it to an instance would manufacture a sighting of six TELs that nobody observed.

**`cs01-r04`** · `ATTR:count_state`

  - subject: “Pakistani holdings”
  - object: “two operational battalions (approximately eight to twelve TEL launchers per battalion equivalent, figures vary by source)”
  - tier-3 attributes: `assigned_to` = “the PAF's Central Air Command”; `source_of_figure` = “a 2015 order-of-battle assessment compiled by a regional military balance publication”
  - span (L15): > A widely-cited figure — drawn from a 2015 order-of-battle assessment compiled by a regional military balance publication — places Pakistani holdings at two operational battalions (approximately eight to twelve TEL launchers per battalion equivalent, figures vary by source) assigned to the PAF's Central Air Command
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `cs01-C2-formations`
  - discriminators — operator: the PAF's Central Air Command · geography: unknown · designation: unknown · time: a 2015 order-of-battle assessment
  - notes: **The closest thing in the corpus to an ORBAT statement — and it still names no formation and no site.** A cardinality attributed to a third-party assessment, with an internal range on the launcher figure and an explicit 'figures vary by source'. This is a count claim, not two formation nodes.

**`cs01-r05`** · `ATTR:count_state`

  - subject: “a third battalion”
  - object: “reportedly in the delivery pipeline”
  - span (L15): > with a third battalion reportedly in the delivery pipeline
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `cs01-C2-formations`
  - discriminators — operator: the PAF's Central Air Command · geography: unknown · designation: unknown · time: as of the 2015 assessment
  - notes: A PROSPECTIVE formation. Counting it into an order of battle would over-count; dropping it silently would lose a stated pipeline signal. It belongs as a separate, clearly-prospective count row.

**`cs01-r06`** · `ENTITY_EXISTS`

  - subject: “unit strength”
  - object: “known_gap”
  - tier-3 attributes: `missing_slots` = “independent confirmation of unit strength since the 2015 assessment”; `staleness` = “This 2015 figure continues to be reproduced in subsequent trade press and conference briefing slides without apparent revision”
  - span (L15): > This 2015 figure continues to be reproduced in subsequent trade press and conference briefing slides without apparent revision, and analysts should note that no independent confirmation of unit strength has surfaced since that assessment was first circulated.
  - polarity: `negative` · evidence mode: `negative-observation` · cluster: `cs01-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: nothing since the 2015 assessment
  - notes: The document states its own staleness AND the circular-reprint mechanism that keeps the figure alive. A self-declared too-clean signal.

**`cs01-r07`** · `manufactures`

  - subject: “China Precision Machinery Import-Export Corporation (CPMIEC)”
  - object: “The missile itself / the HQ-9/P”
  - span (L17): > with a secondary anti-tactical ballistic missile (ATBM) capability against short-range ballistic missiles claimed by the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)
  - polarity: `positive` · evidence mode: `stated` · cluster: `cs01-C3-cpmiec`
  - discriminators — operator: China · geography: unknown · designation: unknown · time: unknown
  - notes: **Stated cleanly and — on the wider corpus — FALSE.** CPMIEC is the export agent, not the maker (d22 argues this explicitly; d23 is the same conflation). The gold labels what the document says; the sub-oracle must hold it at `possible` and record that the slice alone cannot refute it.

**`cs01-r08`** · `ATTR:range_km`

  - subject: “The missile itself”
  - object: “on the order of 200 km against aerodynamic targets”
  - span (L17): > The missile itself is reported to have a maximum engagement range on the order of 200 km against aerodynamic targets
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **Attribute conflict on the SAME designator:** 200 km here, 'in the region of 125 km' in d04, 'well beyond 100 km' in d02. Three sources, three figures, one name — the attribute-agreement signal is actively misleading on this corpus.

**`cs01-r09`** · `equips`

  - subject: “associated HT-233 phased-array engagement radars”
  - object: “the HQ-9/P battery”
  - tier-3 attributes: `component_class` = “phased-array engagement radar”
  - span (L11): > associated HT-233 phased-array engagement radars, and a search/acquisition radar element
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: unknown · geography: unknown · designation: HT-233 · time: unknown
  - notes: Stated inside the generic composition, so this is a DESIGN-layer equips claim. It is also the third hedged HT-233 mention in the slice ('associated'), none of which is an independent positive identification.

**`cs01-r10`** · `UNMODELLED:deployed-in-area`

  - subject: “the HQ-9/P”
  - object: “positions oriented toward the Arabian Sea approach; a secondary battery near the Punjab border sector”
  - span (L23): > Deployment sites are believed to include positions oriented toward the Arabian Sea approach and, per unconfirmed reporting, a secondary battery near the Punjab border sector, though this latter deployment has not been corroborated by satellite imagery analysis available to this desk.
  - polarity: `positive` · evidence mode: `stated-hedged` · cluster: `cs01-C4-areas`
  - discriminators — operator: unknown · geography: Arabian Sea approach; Punjab border sector (AREAS, not sites) · designation: unknown · time: as of the cached record
  - notes: Areas of responsibility, not sites — and the second one is explicitly uncorroborated by the desk. A basing edge here would be precision the source does not have. Note 'a secondary battery' is a FOURTH under-determined formation reference, again with no designator.

**`cs01-r11`** · `UNMODELLED:characterized-as-inducted`

  - subject: “Pakistani defence officials”
  - object: “"already inducted in limited numbers" (2013)”
  - span (L21): > Pakistani defence officials, speaking on condition of anonymity to a regional defence weekly, characterised the system in 2013 as "already inducted in limited numbers," a characterisation that has not been formally retracted or updated by either government since.
  - polarity: `positive` · evidence mode: `stated-attributed` · cluster: `cs01-C1-hq9p`
  - discriminators — operator: Pakistani defence officials (anonymous) · geography: unknown · designation: unknown · time: 2013
  - notes: **Cross-doc time conflict:** an induction 'already' complete in 2013, against d02's formal induction on 2021-10-14 and d04's '~2018-19 first confirmed'. Three irreconcilable induction dates across the corpus for one designator.

**`cs01-r12`** · `ATTR:count_state`

  - subject: “the system's operational status”
  - object: “described in near-identical language by a separate industry newsletter, suggesting continued reliance on the same underlying 2013 sourcing”
  - span (L21): > the system's operational status was described in near-identical language by a separate industry newsletter, suggesting continued reliance on the same underlying 2013 sourcing rather than fresh reporting
  - polarity: `positive` · evidence mode: `stated` · cluster: `cs01-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: The document identifies a second outlet as a REPRINT of the same 2013 sourcing — a too-clean / aggregator-circularity signal stated by the source itself.

**`cs01-r13`** · `NOT_A_CLAIM:publication-time-unrecoverable`

  - subject: “the cached record”
  - object: “-”
  - tier-3 attributes: `retrieved` = “Retrieved via cache: 04 June 2015 18:22 GMT”; `last_modified` = “original page last modified per server header — 11 March 2013 09:47 GMT”
  - span (L21): > As of [publication date not machine-readable in cached header]
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `cs01-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: STATED UNUSABLE
  - notes: **The time discriminator declared unusable by the document.** With report_time unrecoverable, freshness decay has to fall back on the cache-retrieval and last-modified headers — which are 2015 and 2013 respectively.

**`cs01-r14`** · `NOT_A_CLAIM:truncated-artifact`

  - subject: “the cached record”
  - object: “-”
  - span (L29): > *[cached fetch truncated — remainder of record unavailable; full text requires subscriber access]*
  - polarity: `unknown` · evidence mode: `not-a-claim` · cluster: `cs01-C5-gap`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: NEGATIVE GOLD. The record is cut off mid-sentence ('networked with the country's broader integrated air defence…'). An extractor must not complete it.

**`cs01-r15`** · `ANTI_COREF:count-is-not-two-individuated-formations`

  - subject: “two operational battalions”
  - object: “two formation nodes”
  - span (L15): > places Pakistani holdings at two operational battalions
  - polarity: `negative` · evidence mode: `derived-required` · cluster: `cs01-C2-formations`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: unknown
  - notes: **NEGATIVE GOLD, and the OOB lesson of the slice.** A cardinality is not two referents. Minting two formation nodes from this invents individuals the source never named; discarding the number loses the only order-of-battle figure in the slice. The faithful output is one under-determined formation claim carrying count_state = 2 (+1 prospective).

**`cs01-r16`** · `ENTITY_EXISTS`

  - subject: “South Asia Defence Monitor — Air Defence Systems Database”
  - object: “source”
  - tier-3 attributes: `source_type` = “Air Defence Systems Database (cached copy)”; `citation_url` = “Record ID: SADM-AD-0091”
  - span (L1): > South Asia Defence Monitor — Air Defence Systems Database (cached copy)
Record ID: SADM-AD-0091 | Retrieved via cache: 04 June 2015 18:22 GMT
  - polarity: `positive` · evidence mode: `stated` · cluster: `cs01-C6-source`
  - discriminators — operator: unknown · geography: unknown · designation: unknown · time: cached 2015-06-04; modified 2013-03-11
  - notes: A database record retrieved from a cache — two timestamps, neither of which is a publication date.

### Deliberately excluded from the rows

The Turkmenistan / Turkey T-LORAMIDS comparative paragraph (L27) and the Crotale/Spada legacy
mention (L9) — off-subject systems named only for context.

---
