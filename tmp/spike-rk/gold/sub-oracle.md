# RK-SPIKE — per-slice SUB-ORACLE

`schema_version: rk-spike-sub-oracle/1.0` · machine-readable twin: `sub-oracle.json` · derived from `claim-gold.md`

This sub-oracle is what an honest system should end up with **given these seven documents and
nothing else**. It is derived from the hand-labeled claim rows in `claim-gold.md`, not copied from
`answer_key.json`.

**Why the full oracle is the wrong yardstick here.** `answer_key.ground_truth` describes 18 nodes and
23 edges assembled from 26 documents. Score a 7-document slice against it and the number you get is
mostly a statement about *which documents are in the slice* — identical noise for every extractor
candidate, and it would penalise a model for not knowing things its inputs never said. Worse, it
would *reward* an extractor for inventing oracle-shaped edges from documents that do not state them.
The slice-derived oracle measures the only thing an extractor can be responsible for: what these
pages actually say.

**Status semantics used below.** `confirmed` / `probable` / `possible` / `insufficient-evidence`, in
the project's sense: independence of sources, source grade, and perishability all bear on it. Two
reprints of one claim are one source. A perishable-only basis caps at `probable`. Where the honest
answer is *insufficient evidence to assess*, the entry says so and **names what is missing**.

**Scope caveat that is not a defect.** Several statuses here are *lower* than the full answer key's,
because the slice deliberately omits the corroborating documents (d18's first Rahwali pass, d01/d03's
induction corroboration, d22/d23's manufacturer correction). Those are slice-scope differences, not
disagreements — they are called out inline, and the genuine disagreements are collected at the end.

## The slice

| Document | Class | Grade | Bias | Date |
|---|---|---|---|---|
| `d02_ispr_induction` | official | B | operator-state | 2021-10-14 |
| `d04_armyrec_ranges` | trade_media | C | third-party | 2021-10 |
| `d19_rahwali_confirm` | reference | B | third-party | 2025-04-04 |
| `d05_customs_manifest` | customs | C | commercial | 2020-11 |
| `d17b_withheld_gap` | imagery | B | third-party | 2025-06-11 |
| `d20_supersede_spoof` | social | E | adversary | 2025-06 |
| `cs01_stale_orbat` | reference | C | third-party | 2015-06 (page 2013-03) |

**Slice totals.** 7 documents · 125 gold claim rows · 27 sub-oracle nodes · 24 sub-oracle
edge entries (of which 5 are explicitly *not derivable* and recorded as insufficient-evidence with
their missing premises named) · 6 flagged ambiguities. For comparison, the full `answer_key`
ground truth is 18 nodes / 23 edges over 26 documents — a different measurement, on a different
document set, and not interchangeable with this one.

---

## Nodes

### `sl_var_hq9p` — HQ-9/P

**Type:** variant · **Honest status on this slice: `confirmed`**

Surface forms evidencing it: “HQ-9/P”; “HQ-9P”; “FD-2000”; “the Army variant”; “the Army's HQ-9/P”; “High to Medium Air Defence System (HIMADS)”; “The system”; “the system”; “The HQ-9/P”; “The missile itself”; “HQ-9/P (HIMADS) battery”

Supporting rows: `d02-r02`, `d02-r03`, `d02-r06`, `d02-r07`, `d02-r08`, `d04-r01`, `d04-r02`, `d04-r03`, `d04-r04`, `cs01-r01`, `cs01-r08`, `d20-r04`

**Why that status.** Named by four independent sources across three source classes and three grades (d02 official/B, d04 trade/C, cs01 reference/C, d20 social/E), spread over ten years. Design-layer identity, non-perishable. Note that the sources AGREE on the name and DISAGREE on almost every attribute.

Alias set is licensed at variant level by d04 (HQ-9P, FD-2000); d02 licenses it only at FAMILY level. HIMADS is a capability class, not a designator — bind it doc-locally, never as a global alias.

### `sl_var_hq9be` — HQ-9BE

**Type:** variant · **Honest status on this slice: `probable`**

Surface forms evidencing it: “the HQ-9BE”; “a longer-ranged variant”; “the PAF variant”; “the PAF's HQ-9BE”; “this variant, procured under a separate contract”

Supporting rows: `d04-r05`, `d04-r06`, `d04-r07`, `d04-r13`, `d04-r17`, `d19-r09`, `d19-r11`

**Why that status.** Two sources (d04 trade/C, d19 reference/B), but they do not agree on what the designator means: d04 treats HQ-9BE as a distinct system from HQ-9/P, while d19 says it is 'sometimes rendered HQ-9P' and then disclaims its own designator mapping. Existence is well supported; the referent's boundaries are not.

**What is missing.** An authoritative designator mapping (which service designator maps to which PLA/CASIC baseline). Both sources say open reporting is inconsistent on exactly this.

d04 also states Chinese state media never confirmed the HQ-9BE export to Pakistan.

### `sl_var_hq9b_generic` — HQ-9B (used GENERICALLY by d19)

**Type:** variant · **Honest status on this slice: `possible`**

Surface forms evidencing it: “HQ-9B”; “the HQ-9B system”; “HQ9B”; “HQ9B btry”; “HQ9B battery”

Supporting rows: `d19-r02`, `d19-r06`, `d19-r10`, `d20-r01`, `d20-r02`, `d20-r06`, `d20-r08`

**Why that status.** d19 explicitly declares 'HQ-9B' a GENERIC label it applies for want of source specificity; d20 (grade E, adversary) uses 'HQ9B' with no elaboration. A generic label plus a grade-E usage does not individuate a design.

**What is missing.** Any source that states what HQ-9B denotes in Pakistani service, and whether it is the same object as HQ-9BE or its parent baseline.

Its relation to sl_var_hq9be is generic-vs-specific (a refines relation), NOT identity — and the ontology has no way to express refinement between two variants.

### `sl_var_ft2000` — FT-2000 (/ FT-2000A)

**Type:** variant · **Honest status on this slice: `possible`**

Surface forms evidencing it: “the FT-2000”; “FT-2000A”; “"FT-2000 batteries"”

Supporting rows: `d04-r09`, `d04-r10`, `d04-r11`, `d04-r12`

**Why that status.** One source (d04, trade/C). Its existence as a CASIC product is stated plainly, and it is the only design in the slice given a technical differentia (a passive anti-radiation seeker) — but nothing corroborates it.

**What is missing.** A second source on the FT-2000 itself.

The slice contains the false-merge trap AND its refutation: d04 states there is no confirmed evidence Pakistan acquired it, and that a media claim to the contrary was unsubstantiated.

### `sl_family_hq9` — HQ-9 / Hongqi-9 family

**Type:** (family — NOT a node type) · **Honest status on this slice: `confirmed (as a family label)`**

Surface forms evidencing it: “the Chinese-origin HQ-9 family”; “the Chinese Hongqi-9”; “the HQ-9 family proper”; “China's HQ-9 long-range surface-to-air missile system”; “the HQ-9/HQ-9B/HQ-9BE/HQ-9P designator family”

Supporting rows: `d02-r06`, `d04-r18`, `d19-r10`, `cs01-r01`

**Why that status.** Named by all four prose sources in the slice.

FINDING: the ontology carries family as a variant ATTRIBUTE, so the family is not a citizen and the family<-variant refinement cannot be drawn. Four documents refer to the family as a thing in its own right; the graph cannot.

### `sl_mfr_casic` — CASIC

**Type:** manufacturer · **Honest status on this slice: `probable`**

Surface forms evidencing it: “the manufacturer, China Aerospace Science and Industry Corporation (CASIC)”; “CASIC”; “the CASIC export HQ-9BE marketing designation”

Supporting rows: `d04-r13`, `d04-r14`, `d19-r09`

**Why that status.** Two sources name CASIC (d04 trade/C, d19 reference/B). d04's apposition calls it 'the manufacturer' but inside a sentence about the HQ-9BE; d19 mentions it only as the owner of an export marketing designation.

**What is missing.** A source in THIS SLICE that states CASIC manufactures HQ-9/P specifically. (The wider corpus has one — d21 'the baseline HQ-9 developed by CASIC' — but it is not in the slice.)

### `sl_mfr_cpmiec` — CPMIEC

**Type:** manufacturer · **Honest status on this slice: `possible`**

Surface forms evidencing it: “the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)”

Supporting rows: `cs01-r07`

**Why that status.** One source (cs01, reference/C), stale (2013/2015 sourcing), and the claim is a clean apposition — syntactically strong, evidentially weak.

**What is missing.** Any corroboration. **And this is the important part: on this slice there is nothing that can refute it either.** The wider corpus refutes it explicitly (d22 argues CPMIEC is an export/foreign-trade entity, not a design bureau; d23 is the same conflation flagged as misinformation).

A slice-scoped oracle must therefore carry a claim the full corpus knows to be FALSE, at `possible`, with the conflation flagged. This is a genuine property of slice-based scoring, not a labelling error — and it is the reason a sub-oracle must never be presented as truth.

### `sl_comp_ht233` — HT-233 engagement radar

**Type:** component · **Honest status on this slice: `probable`**

Surface forms evidencing it: “the HT-233 fire-control/engagement radar”; “HT-233-band engagement-radar parameters”; “associated HT-233 phased-array engagement radars”; “ref dwg HT233-”

Supporting rows: `d19-r05`, `d19-r06`, `d19-r19`, `cs01-r09`, `d05-r17`

**Why that status.** Three sources mention it, but NOT ONE is an independent positive identification. d19 hedges ('believed to be') and then explicitly disowns the ID as 'the vendor's characterization'. cs01 says 'associated ... radars' inside a generic composition. d05 has a truncated drawing reference in a poor scan. Breadth without a single clean assertion.

**What is missing.** One source that positively identifies an HT-233 on its own authority. Also, its manufacturer: no slice document names a maker for it.

Functional role (engagement fire-control) is consistent across all three prose mentions.

### `sl_comp_tel` — TEL (transporter-erector-launcher)

**Type:** component · **Honest status on this slice: `confirmed`**

Surface forms evidencing it: “the TEL and battery-command cluster”; “Six TEL-pattern vehicles”; “transporter-erector-launchers (TELs)”; “batteries/launchers (TELs)”; “six single-stage TEL (transporter-erector-launcher) vehicles”

Supporting rows: `d02-r11`, `d19-r02`, `d19-r03`, `d19-r04`, `d17b-r03`, `d17b-r05`, `cs01-r03`

**Why that status.** Four independent sources across official, reference, imagery and (stale) reference classes. It is the one object every collection discipline in the slice can see.

Every COUNT of it is either withheld (d02), a hedged estimate (d19, cs01) or negative (d17b). The object is confirmed; the quantity never is.

### `sl_unit_paad` — an unnamed Pakistan Army Air Defence (PAAD) unit

**Type:** unit (formation) · **Honest status on this slice: `insufficient-evidence (for a formation IDENTITY)`**

Surface forms evidencing it: “a Pakistan Army Air Defence (PAAD) unit”; “the newly raised/re-equipped unit”; “the unit”

Supporting rows: `d02-r04`, `d02-r09`, `d02-r10`, `d02-r16`

**Why that status.** Exactly one source (d02, official/B but an interested operator-state party) states an induction into a unit. That licenses a formation to EXIST. It does not individuate one: no designation, no echelon, no parent unit, no site.

**What is missing.** **A unit designation** (the doc says order-of-battle detail is withheld as standing policy); an echelon; a garrison. Next coverage: none — the source states a policy of non-disclosure, so this gap will not close from this source class.

This is the honest OOB answer the design asks for: 'HQ-9/P induction into a Pakistan Army Air Defence unit is stated; the formation is unidentified and its count is undisclosed.'

### `sl_unit_orbat_count` — Pakistani HQ-9/P holdings: two operational battalions + a third in the pipeline

**Type:** unit (formation, as a CARDINALITY) · **Honest status on this slice: `insufficient-evidence`**

Surface forms evidencing it: “two operational battalions”; “a third battalion reportedly in the delivery pipeline”; “a secondary battery near the Punjab border sector”

Supporting rows: `cs01-r04`, `cs01-r05`, `cs01-r10`, `cs01-r15`

**Why that status.** One stale source (cs01, reference/C; page last modified 2013, cached 2015) reporting a third-party 2015 assessment, which the document itself says has never been independently confirmed and is reprinted without revision. It also assigns the holdings to the PAF, conflicting with d02/d04.

**What is missing.** Any post-2015 confirmation of unit strength; a designator for ANY of the battalions; a site for any of them; and a resolution of the Army-vs-PAF operator conflict.

**Must NOT become two formation nodes.** A cardinality is not two referents. The faithful representation is one under-determined formation claim carrying count_state = 'two operational battalions' plus a separate prospective-third row.

### `sl_site_karachi_centre` — Army Air Defence Centre, Karachi

**Type:** basing_site · **Honest status on this slice: `probable`**

Surface forms evidencing it: “the Army Air Defence Centre, Karachi”; “ARMY AIR DEFENCE CENTRE, KARACHI”

Supporting rows: `d02-r05`, `d02-r16`

**Why that status.** One source (d02, official/B) names it as the venue of the induction. An official source naming its own establishment is strong for existence, but it is one source and the geography is city-precision.

**What is missing.** Coordinates or a district; any second source; any observation of equipment there.

It is a CENTRE (an establishment), not a firing position — a different KIND of place from a dispersal pad. Merging it with a Karachi-area SAM site would conflate two kinds of thing.

### `sl_site_rahwali` — Rahwali airfield

**Type:** basing_site · **Honest status on this slice: `probable`**

Surface forms evidencing it: “Rahwali airfield”; “Rahwali”; “near Rahwali airbase, Gujranwala”; “the site”; “this site”; “the location”

Supporting rows: `d19-r01`, `d19-r02`, `d19-r05`, `d19-r08`, `d19-r11`, `d20-r02`, `d20-r04`, `d20-r06`

**Why that status.** Site existence is well stated by d19 (reference/B) with a relative fix and a site type; d20 (social/E) refers to it repeatedly. But d19 is ONE source document, and its internal 'second, non-imagery indicator' is an unnamed vendor relayed through an unnamed intermediary with no geolocation released. Occupancy evidence is perishable, so it caps at probable regardless.

**What is missing.** A grid or coordinates (d19 gives only '~10 km NW of Gujranwala along the GT Road corridor'); a genuinely separate reporting source.

**Slice-scope note, not a disagreement:** the full answer key marks Rahwali `confirmed` on d18+d19. d18 (the first single pass) is deliberately outside this slice, so the slice-honest status is `probable`.

### `sl_site_sialkot` — Sialkot-area dispersal site

**Type:** basing_site · **Honest status on this slice: `insufficient-evidence`**

Surface forms evidencing it: “the previously tracked Sialkot-area ... dispersal site”

Supporting rows: `d19-r14`, `d19-r16`, `d19-r17`

**Why that status.** One passing mention in one document, in a sentence reporting that nothing happened there.

**What is missing.** Coordinates, site type beyond 'dispersal site', any equipment observation, any operator, and the content of the '07 March pass' it refers to (not in the slice).

Must not merge with sl_site_pasrur: d19 states the cardinality explicitly ('both').

### `sl_site_pasrur` — Pasrur dispersal site

**Type:** basing_site · **Honest status on this slice: `insufficient-evidence`**

Surface forms evidencing it: “the previously tracked ... Pasrur dispersal sites”

Supporting rows: `d19-r15`, `d19-r16`, `d19-r17`

**Why that status.** As sl_site_sialkot — a name inside a negative-activity sentence.

**What is missing.** Everything except the name and the region.

These two are the slice's cleanest 'two same-type instances that must not merge' pair — adjacent in one clause, same region, same type, near-zero discriminating context, and distinguished ONLY by the source's explicit 'both'.

### `sl_site_old_rawalpindi` — "the old Rawalpindi-area site" / "the old Rawalpindi site" / "the port road area"

**Type:** basing_site · **Honest status on this slice: `insufficient-evidence`**

Surface forms evidencing it: “"the old Rawalpindi-area site" near the port road turnoff”; “a suspected forward SAM deployment area”; “the suspected forward site”; “the fenced compound”; “"the forward HQ-9/P site"”; “the old Rawalpindi site”; “near the port road area”; “"near port road site"”; “new loc”

Supporting rows: `d17b-r01`, `d17b-r02`, `d17b-r03`, `d17b-r07`, `d17b-r08`, `d17b-r11`, `d17b-r12`, `d20-r03`, `d20-r06`, `d20-r09`

**Why that status.** Two sources refer to something in this space (d17b imagery/B, d20 social/E), but nothing locates it. d17b has no coordinates and its own description is internally inconsistent ('the old Rawalpindi-area site' vs a 'port road turnoff' and a 'Southern Approaches' subject line). d20 supplies three mutually incompatible names for the destination of one alleged move. d17b explicitly refuses to say whether its site and the forum's site are the same footprint.

**What is missing.** **Coordinates** — named as the missing item by d17b itself. Also a site name, an operator, and any unit marking (d17b: none visible in any pass to date). Next coverage: d17b recommends a follow-up tasking 'within the next 5–7 days' of 2025-06-11, cross-referenced against a second vendor's catalog.

**This is the slice's model insufficient-evidence entry.** The correct output is not one site, and not several — it is 'a suspected forward site whose identity cannot be established; coordinates missing; next coverage due within 5-7 days of 2025-06-11'. d17b also states a distinct-from against 'the garrison itself', which must hold even though neither endpoint is locatable.

### `sl_site_ad_depot` — Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area

**Type:** basing_site · **Honest status on this slice: `insufficient-evidence`**

Surface forms evidencing it: “final destination Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area”

Supporting rows: `d05-r18`

**Why that status.** A handwritten broker annotation on a file copy, in one commercial-grade document. Relative geography against two alternative anchors, no name, no grid.

**What is missing.** A grid; corroboration from any other source; the end-user certificate that would establish the consignment's destination (d05 states it is NOT attached).

Nothing is observed there and nobody is based there. Existence-of-a-mention only.

### `sl_org_orient` — ORIENT ELECTRO TRADING (PVT) LTD

**Type:** trading_org · **Honest status on this slice: `confirmed (as an entity)`**

Surface forms evidencing it: “ORIENT ELECTRO TRADING (PVT) LTD”; “ORIENT ELECTRO TRADING PVT LTD”; “ORIENT ELECTRONIC TRADING CO”

Supporting rows: `d05-r07`, `d05-r08`, `d05-r14`, `d05-r23`

**Why that status.** A customs declaration is the primary record of its own filing, and this entity carries TWO registry identifiers (NTN 3298761-4, SECP CUIN 0087762) plus an address. The rename is stated with its registry reference. Identifier-backed identity does not need a second source.

**What is missing.** Its role in any military supply chain. **Nothing in the slice states it.**

Called a 'shell'/'front' nowhere in the document — that reading is derived. The three surface forms differ by a whole token ('ELECTRO' vs 'ELECTRONIC'), so string similarity alone would under-bind them; the CUIN is what licenses the merge.

### `sl_org_sinogalaxy` — SINO-GALAXY IMP/EXP CO. LTD

**Type:** trading_org · **Honest status on this slice: `confirmed (as an entity)`**

Surface forms evidencing it: “SINO-GALAXY IMP/EXP CO. LTD”; “SINO-GALAXY IMPEX CO, LTD”; “SINO GALAXY IMP. & EXP. CO.”; “zhang.wei@sinogalaxy-export.cn”

Supporting rows: `d05-r09`, `d05-r10`, `d05-r11`, `d05-r15`

**Why that status.** Shipper of record on three declarations, with a 'see also' equivalence and a shared invoice number tying two surfaces together, plus a matching email domain.

**What is missing.** Whether it manufactures anything (it is a trading/IMP-EXP entity by its own name).

Country appears as 'CHINA' twice and 'China' once — the value-normalization case, inside one document.

### `sl_org_alnoor` — AL-NOOR CARGO SERVICES

**Type:** trading_org · **Honest status on this slice: `confirmed (as an entity)`**

Surface forms evidencing it: “AL-NOOR CARGO SERVICES”

Supporting rows: `d05-r12`, `d05-r20`

**Why that status.** Freight forwarder of record on two declarations with an AEO certificate number (PK-AEO-0231) — an identifier-backed entity in a primary record.

**What is missing.** Any connection to the subject beyond forwarding these consignments.

Its AEO status is what auto-cleared the risk flag on the third declaration — an integrity fact about the RECORD, not about the goods.

### `sl_event_118834` — GD KPQA-HC-2020-118834

**Type:** contract_import_event · **Honest status on this slice: `confirmed (that the declaration exists)`**

Surface forms evidencing it: “GD No: KPQA-HC-2020-118834”; “B/L No: YMLUW189234567”; “line 118834”

Supporting rows: `d05-r01`, `d05-r04`, `d05-r06`, `d05-r13`, `d05-r14`, `d05-r15`, `d05-r16`

**Why that status.** A customs GD extract is the primary record of the declaration; the GD and B/L numbers are its identity.

**What is missing.** What was actually in it. The stated description is a CIVIL end-use ('FOR INDUSTRIAL NAVIGATION AID'), the end-user certificate is not attached, and no physical exam is recorded for this line.

Confirmed-as-a-record is NOT confirmed-as-a-military-import. The distinction is the whole point of this document.

### `sl_event_118835` — GD KPQA-HC-2020-118835

**Type:** contract_import_event · **Honest status on this slice: `confirmed (that the declaration exists)`**

Surface forms evidencing it: “GD No: KPQA-HC-2020-118835”; “B/L No: YMLUW189234568”; “GD 118835”

Supporting rows: `d05-r02`, `d05-r04`, `d05-r05`, `d05-r17`, `d05-r19`

**Why that status.** As 118834.

**What is missing.** Its contents beyond the filed description; the Annex A line-item detail is present but the scan is explicitly 'poor' and one designator is truncated.

**Shares container TCNU7712204 and the same vessel voyage with 118834.** Maximum relational pull toward an over-merge that would corrupt the import count. The document's own '(shared, see line 118834)' cross-reference proves it treats them as two lines.

### `sl_event_119011` — GD KPQA-HC-2020-119011

**Type:** contract_import_event · **Honest status on this slice: `confirmed (that the declaration exists)`**

Surface forms evidencing it: “GD No: KPQA-HC-2020-119011”; “B/L No: COSU6178820410”

Supporting rows: `d05-r03`, `d05-r05`, `d05-r06`, `d05-r20`

**Why that status.** As 118834. Different vessel, line, container and date.

**What is missing.** Contents; no physical examination was performed (GREEN CHANNEL).

Same consignee, same shipper cluster, same HS code as 118834 — the pair most likely to be wrongly merged on name+neighbourhood alone.

### `sl_gap_tel_count` — TEL / battery / launcher count

**Type:** known_gap · **Honest status on this slice: `confirmed (the gap is real)`**

Surface forms evidencing it: “The exact number of batteries/launchers (TELs) inducted was not disclosed”; “"sufficient numbers"”; “estimated at 6–8 TELs”; “no unit markings or signage”

Supporting rows: `d02-r10`, `d02-r11`, `d19-r03`, `d19-r04`, `d17b-r03`, `cs01-r04`, `cs01-r06`

**Why that status.** Four independent sources touch the count and none establishes it: d02 states it is withheld as standing policy, d19 gives a range and disowns its own upper bound, d17b observes zero, cs01 reprints a 2015 figure never independently confirmed.

**What is missing.** An authoritative launcher/battery count. **Observability ceiling: probable-max** — d02 states the non-disclosure is standing policy, so the gap will not close from official sources.

The count must never be inferred from how many reports merged. In this slice the number of *reports* is 4 and the number of *confirmed launchers* is 0.

### `sl_gap_designation` — unit designation / order-of-battle documentation

**Type:** known_gap · **Honest status on this slice: `confirmed (the gap is real, and it is corpus-wide)`**

Surface forms evidencing it: “unit numbers, basing locations, or the precise contractual designations”; “no unit markings or signage visible in any pass to date”; “confirmed order-of-battle documentation”; “not releasing order-of-battle details for sensitive air defence assets”

Supporting rows: `d02-r11`, `d04-r16`, `d17b-r09`, `d17b-r10`, `d20-r14`, `cs01-r06`

**Why that status.** **Five of the seven slice documents independently state that unit-level identity is not available**, three of them naming it explicitly: d02 (withheld as policy), d04 (asked, no answer), d17b (no markings in any pass to date), d20 (no designator in any of eight posts), cs01 (no confirmation since 2015).

**What is missing.** A unit designation, a serial, or any ORBAT reference for the subject. Nothing in the slice — and, on inspection, nothing in the corpus — supplies one.

**This is the single most consequential entry in the sub-oracle.** The discriminator ladder's top rung (designation) has no data anywhere in this slice to stand on, so every formation-level merge in the corpus must be decided on operator + geography + relational evidence, all of which is perishable or disjunctive. That is why formation identity honestly stays unresolved.

### `sl_gap_ht233_maker` — HT-233 manufacturer

**Type:** known_gap · **Honest status on this slice: `confirmed (the gap is real, on this slice)`**

Supporting rows: `d19-r05`, `cs01-r09`, `d05-r17`, `cs01-r07`

**Why that status.** Three documents mention the HT-233 and none names a maker for it. The only manufacturer claim anywhere near it in the slice (cs01's CPMIEC) is about the MISSILE, not the radar, and is itself a conflation.

**What is missing.** A production entity for the HT-233 array. Not stated by any slice document.

Arrived at independently of the full answer key, which reaches the same conclusion from d22. Encouraging: the honest gap is reachable from a 7-doc slice that does not contain the authoritative study.

### `sl_areas` — Karachi/Sindh coastal sector; strategic air defence belt; Arabian Sea approach; Punjab border sector; PUNJAB AIR DEFENCE BELT

**Type:** area_of_operations · **Honest status on this slice: `probable (as areas)`**

Surface forms evidencing it: “its strategic air defence belt covering approaches to Karachi and the Sindh coastal sector”; “positions oriented toward the Arabian Sea approach”; “near the Punjab border sector”; “PAKISTAN — PUNJAB AIR DEFENCE BELT”

Supporting rows: `cs01-r02`, `cs01-r10`, `d19-r01`

**Why that status.** Two sources name areas of responsibility. As AREAS they are ordinary; as SITES they would be false precision.

**What is missing.** Nothing — the honest content is exactly 'an area', and that is what is stated.

Head-anchored area words (belt, sector, approach). These must never satisfy a basing edge: a relocation tripwire cannot fire on 'the Sindh coastal sector'.

---

## Edges

### `sl_e01` — `inducted-into`: sl_var_hq9p → sl_unit_paad

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d02-r04`, `d02-r16`

**Why that status.** One source (d02, official/B) states it plainly and dates it. But the source is an interested operator-state party, and the object end is an unnamed formation, so the edge is only as individuated as its endpoint.

**What is missing.** A second, non-interested source on the induction; a designation for the unit.

Slice-scope note: the full corpus corroborates this with d01 and d03, neither in the slice.

### `sl_e02` — `distinct-from`: sl_var_hq9p → sl_var_hq9be

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d04-r07`, `d04-r08`

**Why that status.** Stated explicitly and argued (operator, range, rounds, radars) — but by ONE source at grade C, and hedged ('appear to be'). Anti-identity from a single trade-press source reaches probable, not confirmed.

**What is missing.** A second source on the distinction, or a primary procurement document. d04 itself says it asked and got no answer.

**Direct conflict inside the slice:** d19-r09 states HQ-9BE is 'sometimes rendered HQ-9P'. So one slice document says these are two systems and another says one is sometimes called the other. Neither wins on grade alone (C-that-argues vs B-that-disclaims-itself). The faithful output is a flagged contradiction held for an analyst — not a merge and not a wall.
**Disagreement with the full answer key:** it marks this `confirmed`; on the slice it is `probable` at best, and the slice also contains the counter-evidence.

### `sl_e03` — `same-as`: sl_var_hq9p → HQ-9P

**Basis:** stated · **Honest status on this slice: `confirmed`**

Supporting rows: `d04-r02`, `d02-r07`, `d19-r09`, `cs01-r01`

**Why that status.** Three independent sources treat the slash/no-slash forms as one designator, and d04 states it outright ('some regional trade reporting still uses HQ-9P'). Non-perishable, design-layer.

### `sl_e04` — `same-as`: sl_var_hq9p → FD-2000

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d04-r03`, `d02-r07`

**Why that status.** d04 states it at VARIANT level ('the export designation FD-2000 continues to circulate'). d02 supports it only at FAMILY level ('the Chinese Hongqi-9 (HQ-9P/FD-2000 family)'), which is weaker evidence for the same proposition.

**What is missing.** A second variant-level statement. Note d04 also says FD-2000 is a marketing label, which is a reason the mapping may be loose rather than exact.

This is the alias-merge the corpus's demo depends on; on the slice it is honestly `probable`, and one clean source is what carries it.

### `sl_e05` — `distinct-from`: sl_var_ft2000 → sl_var_hq9p

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d04-r10`, `d04-r11`, `d04-r12`

**Why that status.** One source, but it supplies a technical differentia (passive anti-radiation vs semi-active radar homing) AND a negative acquisition claim AND an explicit refutation of the contrary media claim. That is the strongest single-source anti-identity case in the slice.

**What is missing.** Corroboration. Nothing else in the slice mentions FT-2000 at all.

The false-merge trap and its refutation arrive in the same document.

### `sl_e06` — `manufactures`: sl_mfr_casic → sl_var_hq9be

**Basis:** stated · **Honest status on this slice: `possible`**

Supporting rows: `d04-r13`

**Why that status.** One source, and the assertion is an apposition ('the manufacturer, ... (CASIC)') inside a sentence about a range figure — it names CASIC as the manufacturer of the thing under discussion rather than asserting the relation directly.

**What is missing.** A direct statement that CASIC manufactures this variant; corroboration.

Which variant the apposition scopes over is genuinely ambiguous — see the claim-gold note on d04-r13.

### `sl_e07` — `manufactures`: sl_mfr_cpmiec → sl_var_hq9p

**Basis:** stated · **Honest status on this slice: `possible`**

Supporting rows: `cs01-r07`

**Why that status.** One stale grade-C source, stated cleanly as an apposition.

**What is missing.** Corroboration — and, crucially, nothing in the slice can refute it either.

**FALSE on the wider corpus** (CPMIEC is the export agent; d22 argues this explicitly). Carried here at `possible` with the conflation flagged, to make the point that a slice-scoped oracle is a measurement instrument, not a statement of truth.

### `sl_e08` — `equips`: sl_comp_ht233 → sl_var_hq9b_generic

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d19-r06`, `cs01-r09`

**Why that status.** Two sources associate the HT-233 with the HQ-9 family/HQ-9B. Both use 'associated with' rather than a stronger verb, and d19 explicitly disowns the type ID as a vendor's characterization.

**What is missing.** One unhedged, independently-derived statement that the HT-233 equips this design.

Recording 'associated with' as `equips` is already an upgrade of the source's verb — flagged so a scorer does not credit the stronger reading.

### `sl_e09` — `observed-at`: sl_comp_tel → sl_site_rahwali

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d19-r02`, `d19-r03`, `d19-r08`

**Why that status.** Stated by d19 (reference/B) on two dated optical passes (27 and 29 March) from different platforms, plus an ELINT emitter fix. But all three signals arrive inside ONE source document that self-describes as an aggregator, the ELINT vendor is unnamed with no geolocation released, and occupancy is perishable — which caps a perishable-only basis at probable by design.

**What is missing.** A reporting source independent of this digest. Platform-independence within one aggregator is not source-independence.

**Slice-scope note:** the full answer key reaches `confirmed` using d18+d19; d18 is outside this slice.

### `sl_e10` — `observed-at`: sl_comp_ht233 → sl_site_rahwali

**Basis:** stated · **Honest status on this slice: `possible`**

Supporting rows: `d19-r05`, `d19-r19`

**Why that status.** One document, and it explicitly declines to endorse the identification: 'the vendor's characterization, not independently re-derived by this desk'. What is observed is 'a large octagonal engagement radar signature'; that it is an HT-233 is attributed.

**What is missing.** An independent type identification.

The geometry (large octagonal, on a prepared hardstand ~380 m east of the TEL cluster) is the well-sourced part; the designator is not.

### `sl_e11` — `observed-at`: sl_comp_tel → sl_site_old_rawalpindi

**Basis:** stated · **Honest status on this slice: `confirmed as a NEGATIVE observation for the 2025-06-11 pass window`**

Supporting rows: `d17b-r03`, `d17b-r05`, `d17b-r06`, `d17b-r07`

**Why that status.** d17b (imagery/B) looked for TELs, tarped TEL-sized objects, staging and generator trailers, and reports none of them, with the cloud fraction and the confidence-by-segment stated. A well-scoped negative from a grade-B source is strong evidence *for the window it covers*.

**What is missing.** Nothing, for the stated scope. For the broader question 'is the site vacated' the document itself names the residual: dispersal, maintenance rotation to an unobserved facility, or a collection-timing gap. Next coverage: 5-7 days from 2025-06-11.

**The subject end is confirmed and the object end is not.** The equipment absence is solid; the SITE it is absent from cannot be identified (see sl_site_old_rawalpindi). A negative observation at an unidentifiable place cannot retire an occupancy elsewhere.

### `sl_e12` — `observed-at`: sl_var_hq9p → sl_site_rahwali

**Basis:** stated · **Honest status on this slice: `possible`**

Supporting rows: `d20-r04`

**Why that status.** One grade-E, adversary-bias, decoy-risk-flagged social post citing satellite imagery it does not show.

**What is missing.** The imagery it cites; any second source; coordinates.

Also carries the slice's hardest ambiguity: whether this HQ-9/P battery and d20's 'HQ9B btry' at the same site are one presence is unresolvable (see sl_amb_01).

### `sl_e13` — `based-at`: (any formation) → (any site)

**Basis:** NOT STATED ANYWHERE IN THE SLICE · **Honest status on this slice: `insufficient-evidence`**

Supporting rows: *none — this edge is not derivable from the slice.*

**Premises it would need.** Would require: an `observed-at` presence claim + organizational evidence naming the formation at that site.

**Why that status.** **No document in the slice states a named formation at a named site.** d02 names a unit but at an induction ceremony in an establishment, not a basing. d19 names a COMMAND and an anonymous battery. d17b states there is no ORBAT documentation and no unit marking in any pass. d20's eight posts name no formation. cs01 counts battalions and assigns them to a COMMAND, never to a site.

**What is missing.** **A numbered-unit ORBAT reference** — a source that names a designated formation and the site it is based at. Nothing in the slice provides one; on inspection, nothing in the corpus does either (see DATA-FINDINGS).

Every `based-at` edge in the full answer key is marked `basis: derived` — the oracle agrees. This confirms the plan's §B6 coverage gap from the data side.
The honest surface output is the design's own template: *'HQ-9/P presence at <site> probable; formation identity and count unresolved; unit-designation coverage needed.'*

### `sl_e14` — `supersedes`: sl_site_rahwali → sl_site_old_rawalpindi

**Basis:** NOT STATED (and contradicted within the slice) · **Honest status on this slice: `insufficient-evidence`**

Supporting rows: `d19-r12`, `d20-r01`, `d20-r03`, `d20-r06`, `d20-r09`

**Premises it would need.** Would require: two dated presence observations with temporal exclusivity, plus a continuity signal (a designation reappearing, or an explicit credibility-gated transition claim).

**Why that status.** d19 asserts 'a recent redeployment' but names NO origin site. d20 asserts a move out of Rahwali but gives THREE incompatible destinations ('the old Rawalpindi site', 'near the port road area', an unnamed 'new loc') from one grade-E origin echoed four times, and d17b's negative observation is at a site it cannot identify. Direction of travel is asserted in both directions by different documents.

**What is missing.** A locatable origin or destination; a unit designation to carry continuity through the move; a non-derivative second source. d20's own participants say it: 'No imagery, no second source, one guy's thread going viral.'

**The right answer on this slice is 'possible relocation, formation unresolved' — and arguably not even that**, because the two endpoints cannot both be pinned. This is exactly the honest ladder in spine/13 §6, and the slice degrades to its bottom rung.

### `sl_e15` — `distinct-from`: sl_event_118834 → sl_event_118835

**Basis:** stated (distinct identifiers) · **Honest status on this slice: `confirmed`**

Supporting rows: `d05-r04`

**Why that status.** Two distinct GD numbers and two distinct B/L numbers in a primary record, plus the document's own cross-reference treating them as separate lines. Identifier-level anti-identity is the strongest form available.

**The over-merge trap:** they share a consignee, a shipper cluster, a vessel voyage and a CONTAINER. Name similarity and shared neighbourhood both argue for merging; only the identifiers say no. Merging them would silently halve the import count.

### `sl_e16` — `distinct-from`: sl_event_118834 → sl_event_119011

**Basis:** stated (distinct identifiers) · **Honest status on this slice: `confirmed`**

Supporting rows: `d05-r06`

**Why that status.** Distinct GD/B/L, different vessel, line, container and date.

Same consignee and same HS code — the pair most exposed to a name-and-neighbourhood merge.

### `sl_e17` — `distinct-from`: sl_event_118835 → sl_event_119011

**Basis:** stated (distinct identifiers) · **Honest status on this slice: `confirmed`**

Supporting rows: `d05-r05`

**Why that status.** As above.

### `sl_e18` — `distinct-from`: sl_site_sialkot → sl_site_pasrur

**Basis:** stated (enumeration with explicit cardinality) · **Honest status on this slice: `probable`**

Supporting rows: `d19-r16`

**Why that status.** d19 names both in one clause and says 'both remain in a last confirmed state' — explicit cardinality. But it is one source, and neither endpoint has any discriminating content, so the wall rests entirely on the enumeration.

**What is missing.** Coordinates for either site; a second source on either.

**The slice's cleanest 'must not merge' pair at instance level.** Same type, same region, adjacent in one clause, near-zero context. A resolver that leans on name+region would merge them; only the stated enumeration prevents it.

### `sl_e19` — `distinct-from`: sl_site_old_rawalpindi → the garrison itself

**Basis:** stated · **Honest status on this slice: `probable`**

Supporting rows: `d17b-r02`

**Why that status.** Stated in an aside by a grade-B source ('not the garrison itself'). One source, and the endpoints are not locatable — but an explicit anti-identity statement is what it is.

**What is missing.** Identification of either endpoint.

Notable shape: **anti-identity evidence arriving before any identity evidence**. The wall must be representable even when neither node can be pinned.

### `sl_e20` — `same-as`: sl_org_orient → ORIENT ELECTRONIC TRADING CO

**Basis:** stated (registry rename with CUIN) · **Honest status on this slice: `confirmed`**

Supporting rows: `d05-r08`

**Why that status.** A corporate-registry rename cited with its identifier (SECP CUIN 0087762, 2019) in a primary customs record. Identifier-licensed identity does not need corroboration.

The surfaces differ by a whole token, so string similarity would UNDER-bind. This is the one place in the slice where the fast path to confirmed identity (a shared unique identifier) genuinely exists.

### `sl_e21` — `same-as`: sl_org_sinogalaxy → SINO-GALAXY IMPEX CO, LTD

**Basis:** stated ('see also' + shared invoice number) · **Honest status on this slice: `confirmed`**

Supporting rows: `d05-r10`

**Why that status.** An explicit 'see also' plus a shared invoice reference (#SG-20-4471) in a primary record.

The THIRD surface ('SINO GALAXY IMP. & EXP. CO.') is licensed only transitively — see d05-r11, which is honestly labelled derived-required.

### `sl_e22` — `imported-by`: sl_event_118834 → (a unit)

**Basis:** NOT STATED · **Honest status on this slice: `insufficient-evidence`**

Supporting rows: *none — this edge is not derivable from the slice.*

**Premises it would need.** Would require a document naming the receiving unit.

**Why that status.** No unit appears anywhere in d05. The consignee is a trading org; the stated final destination is an unnamed depot from a handwritten note.

**What is missing.** A named receiving unit; the end-user certificate (stated NOT attached).

**FINDING:** the ontology has no edge from `contract_import_event` to `trading_org`, so the relation the document DOES state (event <-> consignee <-> shipper) is unrepresentable, while the relation it does NOT state (event -> unit) is the only one the schema offers. The schema pushes toward asserting the thing that isn't sourced.

### `sl_e23` — `exported-by`: sl_event_118834 → (a manufacturer)

**Basis:** NOT STATED · **Honest status on this slice: `insufficient-evidence`**

Supporting rows: *none — this edge is not derivable from the slice.*

**Premises it would need.** Would require the shipper to be a manufacturer.

**Why that status.** The shipper of record is an IMP/EXP trading company, by its own name. Nothing states it makes anything.

**What is missing.** A manufacturer anywhere in the chain.

Type mismatch, not a data gap: `exported-by` ranges over `manufacturer`, and the document's exporter is a `trading_org`.

### `sl_e24` — `equips / supplies-component (HT-233 from the d05 consignment)`: sl_event_118835 → sl_comp_ht233

**Basis:** NOT STATED — derived at best · **Honest status on this slice: `insufficient-evidence`**

Supporting rows: `d05-r17`, `d05-r16`

**Premises it would need.** Would require: 'ref dwg HT233-' on one annex line item + the HS-8526 radar-parts description + the Air Defence Depot destination, combined against an external premise that HT-233 is an HQ-9 radar.

**Why that status.** The only textual link is a drawing reference TRUNCATED mid-token, on ONE of four line items, in an annex the document labels 'scan quality poor', interleaved with a pasted email. The declared end-use is explicitly CIVIL. No physical examination was performed. The end-user certificate is not attached.

**What is missing.** An untruncated part/drawing reference; the end-user certificate (ref. letter DGDP/IMP/2020/2246, 'copy not scanned'); a physical examination record; any statement of military end-use.

**This is the must-degrade case for the supply chain.** The document supports 'a consignment of radar-apparatus parts, declared civil, with one truncated drawing reference resembling HT233' — and no more. Turning that into a supply-chain edge is exactly the fabrication the non-negotiable forbids.

---

## Flagged ambiguities — the pairs an honest system must NOT resolve silently

### `sl_amb_01` — HQ9B (d20 P1) vs HQ-9/P (d20 P2) at Rahwali — one presence or two?

**Verdict: `insufficient-evidence`** · rows: `d20-r16`, `d20-r04`, `d20-r01`

Same site, overlapping window, two designators. d04 states the two designators name DISTINCT systems; d19 states one is 'sometimes rendered' as the other and then disclaims its own mapping. No post in d20 supplies a unit designation, a service branch or a coordinate. Missing: a unit-level discriminator. Faithful output: one presence at Rahwali with an UNRESOLVED designator — neither two presences nor one merged battery.

### `sl_amb_02` — d17b's site vs the forum's 'port road site' — same footprint?

**Verdict: `insufficient-evidence (stated as such by the source)`** · rows: `d17b-r11`, `d17b-r12`, `d17b-r13`

The source itself refuses to bind them and names the reason: the forum post 'gives no coordinates and describes the location only as "near the port road, same as always"'. This is the only place in the slice where a document explicitly declines to resolve a coreference. Missing: coordinates. Correct behaviour: surface the pair as unresolved with the reason attached — not a merge, not a distinct-from.

### `sl_amb_03` — HQ-9B (generic) vs HQ-9BE (specific) — identity or refinement?

**Verdict: `insufficient-evidence`** · rows: `d19-r09`, `d19-r10`

One document supplies an equivalence AND declares one of the two surfaces a generic label it applies 'unless a source specifies otherwise'. Generic-vs-specific is a refinement, not identity — and there is no way to express refinement between two variants in the ontology, so the choice is a wrong merge or a wrong split. Missing: an authoritative designator mapping.

### `sl_amb_04` — Operator of the HQ-9/P: Army (d02, d04) or Air Force (cs01)?

**Verdict: `probable Army; the conflict is real and must be flagged, not averaged`** · rows: `d02-r09`, `d04-r01`, `cs01-r02`, `cs01-r04`

d02 (official/B, 2021) states induction into a Pakistan ARMY Air Defence unit; d04 (trade/C, 2021) states the Army operates HQ-9/P and the PAF operates HQ-9BE; cs01 (reference/C, 2013-15 sourcing) states the PAF's Air Defence Command operates the HQ-9/P over the same city. Two recent sources including an official one against one stale source: Army is `probable`. Operator is a critical-if-present discriminator, so this is a genuine wall-triggering conflict — and the honest handling is to flag it, because the stale source is not merely wrong-by-grade, it is EIGHT YEARS EARLIER and the operator could have changed.

### `sl_amb_05` — Induction date: 2013, ~2018-19, or 2021-10-14?

**Verdict: `insufficient-evidence for a single induction date`** · rows: `cs01-r11`, `d04-r15`, `d02-r04`

cs01: officials characterised the system in 2013 as 'already inducted in limited numbers'. d04 (Oct 2021): 'Nearly three years after induction was first confirmed by open-source imagery' (~2018-19). d02 (Oct 2021): formally inducted 2021-10-14. Three irreconcilable dates for one designator. These are plausibly three DIFFERENT events (initial limited delivery, first imagery confirmation, formal induction ceremony), but no document says so. Missing: a source that distinguishes them.

### `sl_amb_06` — Range of the HQ-9/P: >100 km, ~125 km, or ~200 km?

**Verdict: `probable ~125 km; attribute agreement is actively misleading here`** · rows: `d02-r08`, `d04-r04`, `cs01-r08`

Three sources, three figures, one designator, and every one hedged ('understood to', 'generally credited', 'reported to have'). d04 disowns its own figure at L19 as 'indicative rather than authoritative'. Consequence for identity: numeric attribute AGREEMENT cannot be a merge signal on this corpus, and numeric DISAGREEMENT cannot be a wall — the sources disagree about the same object.

---

## Where this sub-oracle differs from `answer_key.json`

Recorded, not acted on. The frozen answer key and corpus are untouched. Two of the four
entries are slice-scope artefacts and are labelled as such; two are worth a look by DATA-C/EVAL.

### 1. answer_key.ground_truth contains NO trading_org node, and none of d05's three import events.

**Detail.** The oracle's 18 nodes include one `contract_import_event` (`import_2021`, 'China->Pakistan HQ-9/P transfer', evidence_date 2021). d05 states THREE distinct declarations dated Nov 2020, plus three identifier-backed trading orgs (consignee, shipper, forwarder) and a corporate rename. None of that appears in the ground truth, even though `config/ontology.yaml` documents d05's three bills as a hard-attribute rail and `md/17` lists d05's demo value as 'relational (not string) resolution shell -> HT-233'.

**Classification.** Coverage mismatch, not an error — the 18-node oracle is hero-trace scoped.

**Consequence.** **This is the concrete argument for the sub-oracle.** Score a slice containing d05 against the full oracle and every correct thing an extractor reads out of the customs manifest counts as noise, while the oracle's `import_2021` counts as a miss on a document that never mentions it.

**Action.** Recorded for DATA-C/EVAL. No change requested to frozen data.

### 2. `distinct-from var_hq9p <-> var_hq9be` is `confirmed` in the oracle; the slice supports at most `probable`, and the slice also contains counter-evidence.

**Detail.** The distinction rests on d04 alone (trade_media, grade C) and is hedged in the source ('appear to be genuinely separate procurement lines'). Meanwhile d19 (grade B) says HQ-9BE is 'sometimes rendered HQ-9P in Pakistani service literature' and warns of 'continuing inconsistency' in the designator mapping.

**Classification.** Possible over-confidence in the oracle — flagged, not asserted.

**Consequence.** If the flagship distinct-from is graded `confirmed` while the corpus contains a grade-B source blurring the same designators, a correct system that reports a flagged contradiction looks like a failure against the key.

**Action.** Recorded for DATA-C/EVAL. Worth a look alongside the existing answer-key-grounding pass.

### 3. `manufactures mfr_casic -> var_hq9p` has no supporting statement inside the slice.

**Detail.** d04 names CASIC 'the manufacturer' in an HQ-9BE sentence; d19 mentions only the CASIC export marketing designation. Corpus-wide the edge IS grounded (d21: 'the baseline HQ-9 developed by ... (CASIC)'; d17/d18/d07 use 'the CASIC HQ-9B/HQ-9' attributively), but that evidence is outside the slice.

**Classification.** Slice-scope difference, NOT an oracle error.

**Consequence.** Graph-recall for this edge must be measured against the sub-oracle, where it is correctly absent at the HQ-9/P end.

**Action.** No action. Recorded so the difference is not mistaken for a finding.

### 4. Every `based-at` edge in the oracle is `basis: derived`, and the oracle says so in prose.

**Detail.** `answer_key.json` states on the Karachi edge: 'DERIVED edge — no document states a named unit at a named site.'

**Classification.** Agreement, and a useful one.

**Consequence.** The oracle independently confirms the §B6 ORBAT gap. The sub-oracle reaches the same verdict from the documents alone.

**Action.** None. Cited in DATA-FINDINGS as corroboration.
