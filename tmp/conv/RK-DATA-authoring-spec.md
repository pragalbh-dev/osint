# RK-DATA — identity-coverage authoring spec

**Branch:** `rkdata/author` · worktree `wt-RK-DATA` · 2026-07-26 (rev 2, after adversarial review)
**What this is:** six new corpus documents, five config mappings, and — the part that matters more than the
documents — **the statement of what the system must produce and what it must refuse for each**. That
specification is what the re-record and the oracle regeneration grade against.

**Additive only.** No existing document, no existing claim bundle, and `answer_key.json` were edited or
deleted. The new documents carry **no claims until the re-record extracts them**. Everything in §3 and §4 is
therefore a **specification and a code-read argument, not a measurement**; §7 lists what has to be measured
and when.

---

## 0. What rev 2 changed, and why

An adversarial review checked the hard constraints with git rather than trusting rev 1, and found two things
this revision acts on.

**The centrepiece tested nothing.** Rev 1 named the 22 AD Regt / 47 AD Regt pair as the co-location trap.
It is not one. Several rails separate that pair on their own, so the cap never got to be the thing that
saved us, and a trap another rail already catches is not a trap. Worse, the causal story was wrong twice:
22 AD Regt already carries a garrison basing *and* a forward dispersal basing on its own, so fusing it with
47 adds nothing; and garrison-plus-dispersal is a concurrency, not a supersession, so no relocation follows
either way. **§4 is rebuilt around a different pair, and the harm is restated as what it actually is.**

**The documents stated the conclusion the system is graded on reaching.** Rev 1 ran 800–1200 words against
the corpus's 400–700, and the excess was meta-commentary ending in a terminal "what this means" section that
gave away the epistemic answer in the document's own voice. All six are rewritten to **present evidence and
stop**. Lengths are now 325–710 words, inside the corpus range (162–792).

One sub-claim of the review is **not** correct, and it is worth recording because it changes the mechanism.
The review says the 22/47 pair "rides `name_ceiling: possible`". It cannot: `cluster._name_alone` requires
`RELATIONAL == 0` as well as `DISCRIMINATOR == SOURCE_ASSERTED == 0`, so **the name cap can never fire on a
co-located pair at all** — sharing a site *is* a shared neighbour. That does not rescue the old trap (the
pair is still over-determined, and with differing names it never reaches the fusion line in the first
place), but it is load-bearing for the rebuild: the new pair's shared neighbourhood is exactly what keeps
the name cap out of the way so that the co-location cap is the rail that gets reached. See §4.3.

---

## 1. The gaps, confirmed before writing anything (unchanged from rev 1)

Checked across **both scenarios** — 30 frozen claim bundles / **492 claims**, and all document text under
`corpus/` (72 doc files, 29 raw specimen files).

| Claimed gap | How I checked | Result |
|---|---|---|
| **Zero numbered or designated formations** | enumerated every `unit`-typed entity in all frozen claims | **Confirmed.** 22 unit mentions, all services or commands (`Pakistan Air Force`, `Army Air Defence Command`, `Pakistan Army`, …). Not one designator. |
| **Zero equipment or unit serials/registrations** | attribute scan over all claims; regex sweep for serial/registration/chassis/hull/bort patterns over all doc text | **Confirmed.** The only `Serial:` string in the corpus is `GIS-2022-0311-KHI`, an imagery *product* ID. |
| **Zero coreference annotations** | key scan for coref/mention/anaphor/antecedent across all bundles | **Confirmed.** Zero. |

So `formation_discriminators`, `hard_id_fields.unique.unit`, the coreference binding tier and gates
G16/G18/G19 are fixture-only on the real corpus. That is what these six documents close.

---

## 2. Deliverable 1 — the `site_type` mapping

### 2.1 The three rows that came from the FROZEN corpus (rev 1, measured)

`config/ontology.yaml → layer_routing.site_type_aliases`:

| Stated value (and where) | → class | Why |
|---|---|---|
| `centre` (d02) | `garrison` | A corps/arm "Centre" in Pakistan Army usage is the permanent home establishment of the arm. |
| `deployment site` (d23) | `dispersal_site` | A site a battery is described as deployed *to*, as against its home station. |
| `prepared revetment complex / airfield site` (d17) | `airfield` | The place-kind noun governs; "prepared revetment complex" is the emplacement *within* the place. |

**Measured effect** (rebuilt the real corpus before and after): `unit_hq9b`'s four derived `based-at` edges
went from one-of-four site classes resolving to four-of-four, and the rebuild draws exactly one supersede,
`site_rahwali -> site_rawalpindi` on `edge:unit_hq9b:based-at:airfield`. The flagship relocation is
restored; the Karachi garrison and the Sargodha dispersal basing de-conflict into concurrently-valid basings
with no relocation between them. Full `backend/tests/view`, `tests/config`, `tests/api`, `tests/gates`,
`tests/acceptance` and `tests/resolve` pass, before and after rev 2. Two `xfail(strict=True)` markers on
`test_relocation_beat.py` XPASSed and were retired with a comment recording cause and fix.

**Residual fragility, stated not hidden.** `site_rahwali` is described two ways in the corpus — `airfield`
(d18) and `Pakistan Army/PAF joint-use facility` (d19) — and which one lands depends on claim ordering. If
the re-record gives it the operator-class string, the flagship silently returns to held-with-a-gap. That is
*safe* but it is a silent demo regression. Check it; do not close it by mapping an operator-class string.

### 2.2 The two rows added in rev 2 (PREDICTED, not measured)

The review's point on n03 is the sharp one: rev 1's n03 supplied the closed vocabulary as clean labelled
fields (`Position type: emplacement`), which hands the extractor the controlled value verbatim. **Needing no
alias row is not a win — it means the alias machinery was never exercised.** n03 now writes its site kinds
the way an imagery desk writes them, and two rows are declared for the phrases it uses:

| Phrase in n03 | → class |
|---|---|
| `revetted launch position` | `emplacement` |
| `unimproved hardstand` | `dispersal_site` |

Both are kind-of-place phrases and nothing else, which is the only test a row has to pass. These rows are
**predictions about what extraction will emit**, not records of a string the store has seen. If the
re-record emits different strings, add the rows it actually emits.

### 2.3 The row deliberately NOT added

`cantonment` is a genuine kind-of-place noun, it would map cleanly to `garrison`, and n01/n02/n05 use it
constantly. It is **left unmapped anyway**, because it is also the noun several *existing* documents use
around the two ends of the flagship relocation (Rawalpindi Cantonment, Gujranwala Cantonment), and
`site_type` strings are re-derived at every re-record. A row added on prediction could hand
`site_rawalpindi` the class `garrison` while `site_rahwali` keeps `airfield`, split the flagship's two ends
into different buckets, and kill the supersede silently. The unmapped third state is safe by construction
(no de-confliction, no fusion, named gap). **Measure first, then map** — §7 check 4.

---

## 3. Deliverable 2 — the six documents

All are in `corpus/scenarios/hq9p_primary/docs/`, registered in `config/sources.yaml`. Every one is
**synthetic-from-real-template**: format and messiness from a real specimen, entities and values varied
synthetically. Places are real (Pano Aqil / Panu Aqil / Pannu Aqil Cantonment, Sukkur District; Ghotki
District; the N-5) with synthetic coordinates and synthetic formations.

**The rev-2 writing rule, applied to all six:** a document PRESENTS EVIDENCE and never STATES THE ANSWER.
Every terminal "what this means" section is deleted. Caveats survive only in the document's own idiom — a
spotter noting *"plate legible, chassis obscured"* is evidence; a spotter writing *"therefore these are the
same vehicle"* is adjudication, and every instance of the second kind is gone.

### Corruption operators — the enumerable set actually applied

1. **OCR / transcription digit confusion** — `8477 AD` misread `8417 AD`, with correction log.
2. **Coordinate transcription error** — `069°08'20"E` mistyped `069°80'20"E`, caught in the document.
3. **Transliteration variance** — Pano Aqil / Panu Aqil / Pannu Aqil / Pano Akil.
4. **Truncated / withheld field** — chassis prefix unresolved; appendix "not distributed".
5. **Date-format drift** — `18 Feb 2025` / `2025-03-19` / `27/03/2025` / `31/03/25` / `22/03/2025`.
6. **Copy-paste duplication** — a register index line under a second rendering; a vehicle entry re-entered under the other place spelling and struck through.
7. **Hedge attached to the wrong clause** — "reportedly in a short conversion period"; "reportedly having been arrived at by counting vehicles".
8. **Unit-of-measure drift** — 27 km / ~17 statute miles / 14.6 nm for one distance.
9. **Carried-forward unverified entries** — `(u)` rows; an entry that may be a duplicate of another.
10. **Currency / staleness drift** — lineage as at 2019 and present particulars as at Mar 2025, in one sheet.
11. **Designator rendering drift** — `22 Air Defence Regiment` / `22 Air Defence Regt`.
12. **Disagreeing readings published side by side** — two chassis prefixes; two redesignation years; two raising years.

---

### 3.1 `n01_orbat_register.txt` — ORBAT register (545 words)

`curated-register / B / third-party / 365d`, report_date 2025-03-31. Operators 3, 5, 6, 9, 10, 11.

**What it plants.** The corpus's first numbered, designated formations with parents: `22 Air Defence
Regiment` (Pakistan Army, Air Defence; garrison Pano Aqil Cantonment; **3 Air Defence Brigade**) and
`47 Air Defence Regiment` (same garrison; **11 Air Defence Brigade**), plus `9`, `33`, `56` as texture. It
states 22 AD Regt's concurrency as a note (one battery forward at Ghotki since Feb 2025 *while* RHQ and the
remaining batteries stay at the garrison) without telling the reader what to conclude from it. **New in rev
2: §3.7, "Sub-units recorded without allocation"** — an undesignated *air defence battery* at Pano Aqil
Cantonment, Pakistan Army, echelon battery, long-range Chinese-origin equipment, sourced to cantonment board
correspondence and local press, which the compiler records it could not allocate to either regiment. This is
**carrier #1 of the co-location trap** (§4).

**Must produce:**
- `unit` nodes carrying `designator`, `service_branch`, `parent_unit`, `echelon` — the first in the corpus.
  This is what gives `formation_discriminators` (`parent_unit`) and `hard_id_fields.unique.unit`
  (`service_branch` + `designator`) something to grip.
- A **STATED** `based-at` for each regiment at Pano Aqil Cantonment.
- A third `unit` node for the §3.7 battery, with **no** `designator` and **no** `parent_unit`.
- The 33 AD Regt row stays **unconfirmed** and uncounted.
- `Pano Aqil` / `Panu Aqil` / `Pannu Aqil` resolve to one station.

**Must refuse:**
- To allocate the §3.7 battery to 22 or 47 AD Regt. The register records that it could not.
- To draw a relocation for 22 AD Regt between its garrison and Ghotki (different site classes ⇒ C1 gives two
  concurrently-valid basings).

**Not counted as a test.** The 22/47 keep-separate. It holds, but it is over-determined — see §4.1.

---

### 3.2 `n02_ispr_panoaqil.txt` — official release (325 words)

`official / B / operator-state / event-driven`, report_date 2025-02-18. Operators 3, 4, 5, 7.

**Rewritten in rev 2, and its job changed.** Rev 1 had ISPR visiting 22 Air Defence Regiment by name, which
made n02 the third document stating that regiment's garrison — the review's point that reaching `confirmed`
there could not distinguish working independence logic from three claims being counted. It is now a
live-firing validation release which, **in line with real ISPR practice, does not identify the parent
formation**: "an air defence battery at Pano Aqil Cantonment", equipped with the long-range system on the
Corps of Army Air Defence inventory. This is **carrier #2 of the co-location trap** (§4).

Consequence, stated plainly: 22 AD Regt's garrison basing is now stated by **two** sources, not three — n01
(third-party curated register) and n05 (operator-state official sheet). Two independent looks is a real test
of the independence logic; three was not.

**Must produce:**
- A `unit` node for the undesignated battery: name as stated, `service_branch` Pakistan Army, `echelon`
  battery, **no `designator`, no `parent_unit`** — and a `based-at` at Pano Aqil Cantonment.
- 22 AD Regt's garrison basing reaching at most what **two** independent looks earn.

**Must refuse:**
- To infer the battery's parent formation. The release says the parent is not identified.
- To disclose or infer a launcher / radar / round count. The release says none were disclosed.
- To read the separately-mentioned forward sub-unit as a relocation of the firing battery.
- To let the misplaced hedge ("reportedly in a short conversion period") attach to the equipment holding.

---

### 3.3 `n03_panoaqil_imagery.txt` — imagery read-out (619 words)

`satellite / B / third-party / 7d`, **no report_date** (three pass dates, no document date; ING-7 forbids
inferring one). Operators 2, 5, 8.

**Rewritten in rev 2.** The labelled `Position type:` fields are gone — they handed over the closed
vocabulary verbatim; site kinds are now in the desk's own prose and need the two alias rows in §2.2. The
terminal §5 "what this report does not establish" lecture is gone; what survives is a **collection-notes
section in imagery idiom** — what is legible in the frames, and what was not collected.

Content: two revetted launch positions 5.6 km apart inside and on the margin of the cantonment, both
occupied on all three passes, six-object fan + octagonal radar at the north, four-object arc + rectangular
radar at the south-east; an unimproved hardstand in Ghotki ~27 km NNE, occupied on all three passes; a Nov
2023 archival frame on which the north is occupied and the other two are empty. The coordinate transcription
error and the three-unit distance drift are carried in place.

**Must produce:**
- `observed-at` occupancy evidence — equipment at a place — materialising **presences**.
- Site classes `emplacement` (×2) and `dispersal_site` via the §2.2 alias rows.
- A **named gap on the unit count at Pano Aqil**, sourced to this document's own collection notes.

**Must refuse:**
- To attribute either cantonment position, or the Ghotki hardstand, to **any named regiment**. No
  `inducted-into` edge runs from anything observed here to 22 or 47 AD Regt, so no derivation can reach one.
- To read the occupied Ghotki hardstand as evidence that either cantonment position was vacated — the
  collection notes say no pass shows either unoccupied.
- To resolve `069°80'20"E` as a real coordinate.

**Rewritten must-refuse (review Finding 3).** Rev 1 said "MUST REFUSE to attribute either emplacement to any
unit". That **contradicts the system's own design**. `backend/chanakya/view/basing.py` deliberately
materialises `<unit, based-at, site>` from an occupancy observation plus a formation edge, precisely because
open sources rarely state formation-at-site; `credibility.yaml → basing_proposer` wires it as `observed-at`
+ `inducted-into` → `based-at`. So the honest requirement is not "no attribution", it is:

1. any attribution drawn here is a **derived inference**, stamped `derived-inference`, and **capped below
   `confirmed`** however well its premises corroborate;
2. it may name only a formation an `inducted-into` claim actually reaches — a service-level formation such
   as Pakistan Army Air Defence — and **never** 22 or 47 Air Defence Regiment, because no induction claim in
   this corpus reaches either;
3. where more than one candidate formation is associated with the observed equipment, `max_units_per_site: 1`
   truncates and **must** emit the `_truncation_gap` Known Gap naming the dropped candidates, with
   `missing_slots: ["unit.designator"]`. A silent pick is the undercount that has no merge in it at all.

**Not counted as a test.** "Two distinct `basing_site` nodes" is self-fulfilling — the two positions have
different names, different coordinates, different radar fits and are 5.6 km apart, so nothing proposes
merging them; the Ghotki hardstand at ~27 km is past `entity_geo_conflict_max_km.basing_site` (25 km) and is
vetoed geographically. Both are **background invariants**, recorded so a regression is visible, not claims
that a mechanism was exercised. Likewise "MUST REFUSE to emit a battery count": producing one would require
pure hallucination, so there is no mechanism behind it. Keep it as a fabrication guard; do not count it as
testing credibility machinery.

---

### 3.4 `n04_tel_fleet_register.txt` — vehicle spotter register (703 words)

`named-social / **C** / third-party / continuous`, report_date 2025-04-02. Operators 1, 3, 4, 5, 6, 12.

**The class/grade split is deliberate and is the one call here worth a reviewer's eye.** `named-social` is
what this *is* — a contributor compilation — and its low R (≈0.35) is correct: it has no authority, so
nothing it *concludes* travels far. STANAG **C** is earned by its **process**: every entry photo-backed with
an archive reference, disagreeing plate readings published rather than resolved silently, the misreading
carrying its own correction log. Grade C is what lets a photographed, corrected plate reading clear the
`bind_min_grade` / `critical_veto_min_grade` floors — right, because the plate is a *directly observed*
fact, and directness is the one thing this source class has.

**Rewritten in rev 2.** The `Same vehicle?: YES` / `Same vehicle as 017?: NO` adjudications are gone: a
spotter log records observations, it does not adjudicate. In their place are evidence lines — *"plate legible
and identical in both; chassis suffix 0173 legible in both; a weld repair on the left rear mudguard visible
in PMV-A-4471 and again in PMV-A-4602"*, and for entry 018, *"both plates are legible in PMV-A-4473, side by
side, and differ in the third digit"*. The closing "NOTE ON UNIT ATTRIBUTION" lecture is gone; a per-entry
`Unit marking: none legible` field carries the same fact as evidence.

**What it plants.** The corpus's first equipment fingerprint that individuates one physical object across
two sightings: TEL plate `8477 AD` at the Pano Aqil static display (18 Feb 2025) and on the Ghotki bypass
road move (22/03/2025), joined by three independent points. The near-miss `8471 AD` in the same frame. The
struck-through duplicate `AD/2025/019` under the other spelling. And an **ambiguous anaphor**: the commentary
names both 22 and 47 Air Defence Regiment, then discusses "the regiment".

**Must produce:**
- A **presence-level merge** across the two sightings of `8477 AD` — the strongest honest merge evidence in
  the corpus, and the one place a merge should be *earned* rather than capped.
- `equipment_fingerprint` on the relevant instance, so the discriminator ladder has a rung it can climb.
- Recognition that `8417 AD` and the struck-through `AD/2025/019` are the same vehicle and the same
  photograph — one vehicle, two sightings.

**Must refuse:**
- To bind "the regiment" to either 22 or 47 AD Regt. Two type-compatible antecedents ⇒ refusal, both mentions
  stay singletons, the pair goes to the analyst.
- To attribute `8477 AD` to any unit. `Unit marking: none legible` in every frame held.
- To conclude from one launcher's road move that a *regiment* moved.
- To resolve the chassis prefix. `WS2400` vs `TAS5380` is published unresolved; picking one is fabrication.

**Downgraded to a check, not a win (review Finding 3).** The `8477 AD` / `8471 AD` keep-separate is only
gradeable **if the resolver ever proposes the pair**. Two plates differing in one digit may or may not
survive blocking and reach a candidate pair at all. §7 check 6 records it as something to look for at
re-record rather than something claimed here.

---

### 3.5 `n05_regiment_lineage_note.txt` — lineage / nomenclature sheet (463 words)

`official / B / operator-state / irregular`. Operators 3, 5, 7, 10, 12.

**Rewritten in rev 2.** Rev 1 spent most of its length on identity POLICY and instructed the reader ("THE
THREE CONFUSIONS THIS SHEET EXISTS TO PREVENT"; "they are not to be merged in any index"); its in-corpus
standard `cd07_unit_collision` states facts with hedges and never instructs. It is now a **register of
entries**: a principal entry, a lineage entry, a section listing the other formations bearing the number 22,
a related entry for the same station, and a station-name note. The prose that told the reader what to
conclude is deleted. The plants the review rated strongest are kept intact.

**(a) The designator collision — kept, and it is the live test.** `22 Air Defence Regiment` (Pakistan Army,
Corps of Army Air Defence), `22 Medium Regiment` (Pakistan Army, Pakistan Artillery, Okara) and a PAF
`22 Air Defence Squadron` are recorded as separate entries. **This is a live test of
`hard_id_fields.unique.unit = [service_branch, designator]`.** If extraction emits `designator` as the bare
number `22`, then `(Pakistan Army, 22)` is a complete composite AND-key shared across two different arms and
**the ladder's top rung lifts every cap and merges two different regiments**. If it emits the full
designation (`22 Air Defence Regiment` vs `22 Medium Regiment`), the key does not match and nothing lifts.
Falsifiable either way — and if the pair merges, the finding is that designator extraction is taking the
bare number, which is a defect to fix, not a threshold to tune.

**(b) A stated contrast at the same station** — 47 Air Defence Regiment recorded as a separate regiment under
a different brigade with its own lineage, CO and establishment. This is the same-document contrast
`contrast_ceiling` exists for.

**(c) Two equivalences** — "22 Air Defence Regiment, also known as the Indus Gunners" and "22 Air Defence
Regiment, formerly 22 Light Anti-Aircraft Regiment". Both markers (`also known as`, `formerly`) are in the
configured `equivalence_markers` vocabulary, both spans carry both surface forms verbatim, and grade B clears
`bind_min_grade: C`.

**Must produce:**
- A `CoreferenceContrast` on 22 AD Regt vs 22 Medium Regiment and on 22 AD Regt vs 47 AD Regt, capping each
  at `probable` — reaching the analyst with the licensing quote, never auto-merging.
- Alias binds `22 Air Defence Regiment ≡ Indus Gunners` and `≡ 22 Light Anti-Aircraft Regiment`.
- 22 AD Regt's garrison basing as the **second** of two independent looks (with n01).

**Must refuse:**
- To merge 22 Air Defence Regiment with 22 Medium Regiment, or with the PAF 22 Air Defence Squadron.
- To merge 22 with 47 Air Defence Regiment.
- To treat the detachment as a change of garrison.
- To carry the 2019 lineage dates as current facts.
- To reproduce the launcher / battery strength figure the sheet records as unsourced.

---

### 3.6 `n06_battalion_count_recount.txt` — independent recount (710 words)

`think-tank / B / third-party / irregular`, report_date 2025-05-12. Operators 4, 5, 7, 10.

**Rewritten in rev 2 — the plant kept, the rule stripped.** The review rates this the strongest gradeable
plant in the set, and is right: two sourced quantitative assessments, different methods, different grades, on
one attribute, where *both* naive rules give a wrong-but-statable answer (average them → ~3.5; prefer the
higher grade → adopt "not fewer than three" as a figure and silently drop the open bound). What is deleted is
the paper stating the aggregator-collapse rule outright — "It is not corroboration… one figure, from one
source, printed three times", and the closing sermon about floors becoming figures. Its partner `d23` merely
EXHIBITS the pattern; n06 now does the same. It reports **what is observable**: three outlets carry the
figure, all three attribute it to SIPRI, none reports collection of its own, two reproduce the surrounding
sentence near-verbatim. The system has to draw the conclusion.

Also kept: SIPRI's own two properties (delivery figures are *estimates*; the register counts **transfers**,
not **fielded** units), the withdrawal of the programme's own 2023 backgrounder, the imagery count (six
prepared positions: three persistent, two intermittent, one never occupied), the result stated as a floor
with **no** upper bound at all, and Pano Aqil as the worked example with the unit count recorded as **OPEN**
— now also noting the unallocated battery n01 §3.7 carries.

**Must produce:**
- `approximately 4 battalions` resolved to **one origin group**, not three looks.
- A **contradiction between two independent quantitative assessments** on one attribute → the holding count is
  a **named Known Gap**, not a confirmed number. That output is worth more than either number.
- The distinction the corpus has never carried: **prepared positions ≠ fire units**. Six positions must not
  become six units; three persistently occupied positions must not become exactly three units.

**Must refuse:**
- To count n06 as **corroboration** for "approximately 4 battalions".
- To publish a single battalion figure as confirmed.
- To supply an upper bound. n06 states none, so asserting one is fabrication.

---

## 4. THE CO-LOCATION TRAP, REBUILT

### 4.1 Why the old trap was vacuous, and what replaces it

**Old pair: 22 AD Regt / 47 AD Regt.** It is separated by rails that fire before the co-location cap is ever
consulted, and each is sufficient alone:

- the two names differ, so the **Phase-1 exact-normalised-name bootstrap never triggers**, and Phase-2's
  fuzzy path tops out below `auto_merge: 0.85` for a pair whose `designator` and `parent_unit` both
  disagree — so **nothing would fuse them anyway**, and a cap guarding a door nobody walks through guards
  nothing;
- `designator` 22 vs 47 is an attribute conflict, dragging `_conflict_penalty` across both attribute
  sub-signals;
- `parent_unit` 3 AD Bde vs 11 AD Bde disagrees, so `agreeing_discriminators` is empty in the direction that
  would *lift* the cap while the conflict has already suppressed the score;
- n01 and n05 each state the separateness within one document, so the pair is a **stated contrast** on the
  raise-only channel, which blocks bootstrap and auto-merge unconditionally.

And the harm story was wrong. 22 AD Regt **already** carries a garrison basing and a forward dispersal basing
on its own, so fusing 47 into it adds no second site; and garrison-plus-dispersal is a **concurrency** under
C1 (`wall_scope_attr: site_type` puts them in different buckets), so no relocation is drawn either way. The
pair stays in the corpus — a real ORBAT fact and a genuine `contrast_ceiling` exercise — but it is **not the
trap**, and §3.1 / §3.5 no longer claim it as one.

**New pair: the undesignated air defence battery at Pano Aqil, reported once by n01 §3.7 and once by n02.**
This is what real reporting looks like when two similar units sit at one station and nobody writes down which
is which. Neither document gives a number, a letter or a parent — because the register genuinely could not
allocate it, and because ISPR genuinely does not identify parent formations. Both give the same station, the
same branch, the same equipment class, and the same words for the thing.

### 4.2 What the corpus establishes, and what it does not

**It establishes that more than one such sub-unit is at that cantonment.** n01 §3.4 places two long-range AD
regiments there and records that both hold batteries at the cantonment; n03 shows two occupied revetted
launch positions 5.6 km apart with different radar fits, occupied on every pass; n06 records the unit count
at that cantonment as OPEN.

**It does not establish which battery either mention is.** No document allocates either one. So the two
mentions are genuinely either one battery reported twice or two batteries reported once each, and **nothing
in the corpus discriminates**. That is not a defect in the data; it is the analytic situation, and it is
exactly the situation the non-negotiable governs: evidence ambiguous ⇒ do not decide, name what is missing,
escalate to the analyst.

### 4.3 Rail by rail — why nothing but the cap catches it

For each mechanism that could refuse the pair, why it does not fire. Read against
`chanakya/resolve/cluster.fusion_blocked` — which consults, in order, `cross_namespace_or_type` →
`name_ceiling` → `colocation_ceiling` — and `cluster.colocation_only`.

| Rail | Fires? | Why not |
|---|---|---|
| `cross_identity` — type | **no** | Both mentions are `unit`. |
| `cross_identity` — namespace | **no** | Both state `service_branch` Pakistan Army, which C7 folds to one value, so `namespace_compatible` holds and the bootstrap's stricter `==` holds too. |
| `name_ceiling: possible` | **no** | `_name_alone` requires `RELATIONAL == 0`. The two share resolved neighbours (the Pano Aqil Cantonment site; the long-range design), so `RELATIONAL > 0` and the name cap is structurally unreachable. **This is the rail rev 1's trap was said to ride, and it cannot fire on any co-located pair.** |
| `contrast_ceiling` — stated contrast | **no** | No document distinguishes these two mentions; neither has a name to distinguish. n01 §3.7 states non-*allocation* (to the two regiments), which is not a statement of non-identity between the two battery mentions. |
| G18 relationship-conflict wall (`based-at`, `operated-by`) | **no** | Both are at the **same** site under the same operator, so there is no stated conflict at overlapping times to wall on. This is why the pair must sit at one site rather than one-per-emplacement: two different sites would wall, and the wall — not the cap — would be doing the work. |
| Geographic veto `entity_geo_conflict_max_km` | **no** | Same site; separation 0 km. |
| Curated `distinct_from` | **no** | The table carries `HQ-9/P` rows only; `places.yaml` carries the Karachi-Port pair. Neither touches units. |
| `critical_attribute_conflict` / `constitutive_difference` | **no** | The one `critical` unit attribute is `service_branch`, and both state Pakistan Army — agreement, not conflict. |
| Hard-id top rung `_shared_unique_id` | **no** | `unit`'s unique keys are `[service_branch, designator]` and `[service_branch, designator, parent_unit]`, both **composite AND-keys**: every component must be stated on both sides. Neither document gives a designator, so neither key completes, and absence is never agreement. |
| `agreeing_discriminators(formation_discriminators)` | **no** | `formation_discriminators` is `[equipment_fingerprint, parent_unit]`. Neither is stated on either side, and absence never lifts. (`designator`, `echelon` and `home_garrison` are deliberately excluded from that list, so their presence or agreement lifts nothing.) |
| `_conflict_penalty` | **no** | Nothing disagrees, so the score is not suppressed — which is the point: this pair *scores*. |
| **`colocation_ceiling: probable`** | **YES** | `colocation_only` returns a non-empty shared-predicate tuple: both are `unit` (in `formation_types`, not `presence_types`), `RELATIONAL > 0`, every shared predicate is inside `colocation_predicates`, no shared unique id, no agreeing discriminator. **Sole restraint.** |

**And the pair does reach the fusion line, so the cap has something to do.** Identical normalised names in one
namespace is `TRIGGER_EXACT_NAME`, a **Phase-1 bootstrap** trigger that merges at hardcoded confidence 1.0 and
**bypasses banding entirely**. `fusion_blocked` is the one precondition both phases consult, so with the cap
removed this pair fuses at 1.0 with no band and no queue place. That is the falsifiable claim: **set
`colocation_ceiling` to `confirmed` and the two batteries become one node; leave it at `probable` and they do
not.**

### 4.4 The harm, stated as what it actually is

**No relocation is drawn.** Both mentions are at the same site, so a fused node has one basing and there is no
before/after for the supersede path to order. Rev 1 claimed a fabricated relocation here; that was wrong, and
this is the honest replacement — the undercount the trap is named for:

1. **The count is silently halved.** One `unit` node stands where the corpus's own sources put two or more
   sub-units at that cantonment. This is the same failure class `basing.py`'s `_truncation_gap` docstring
   calls out — "an order-of-battle undercount with no merge involved" — reached here *with* a merge.
2. **The analyst is removed.** A fused pair is machine-adjudicated and leaves the review queue, so the one
   genuinely open allocation question in the corpus stops being asked. The system answers, in its own voice,
   a question every source it holds declined to answer.
3. **An identity the corpus does not contain gets inherited.** n01's §3.7 entry carries register-sourced
   equipment and sourcing particulars; n02's carries an operator-state firing record. Fused, one node claims
   both provenance chains as one battery's, and the register's own "could not allocate" flag is closed by
   machine rather than by evidence.
4. **It propagates into the count answer.** n06 uses Pano Aqil as its worked example and records the unit
   count there as OPEN. A fused node makes that cantonment read as one unit, contradicting the corpus's own
   recorded OPEN and pushing the fire-unit floor in the direction a reader will then quote.

**What the system must produce:** the pair **withheld from fusion**, recorded at ceiling `probable` on rail
`colocation_ceiling`, **in the analyst's queue** with the reason naming what would lift it
(`equipment_fingerprint` or `parent_unit`), and the Pano Aqil sub-unit count carried as an **open named gap**
rather than resolved to one.

**What it must refuse:** to fuse the two battery mentions; to allocate either to 22 or 47 AD Regt; to emit a
battery count for Pano Aqil; to attribute `8477 AD` to any unit; to merge `8477 AD` with `8471 AD`.

**A failure here is not a scoring miss.** It is the system answering an allocation question every one of its
sources refused to answer, and taking the human out of the one decision that was actually theirs.

---

## 5. Item 6 — how `d23`'s circular corroboration should be used

**Use it as it stands, unchanged.** `d23` is already a complete specimen: "approximately 4 battalions" carried
by three trade outlets, all attributing to SIPRI "without independent sourcing of their own", with SIPRI's own
estimate caveat "not always carried forward by the outlets citing it".

**Do NOT extend the chain with a fourth echo.** A fourth reshare adds no mechanism the existing three do not
already exercise, and the corpus already carries a six-post echo burst (d11–d13 + ce01–ce03). What `d23`
lacked was **the other side of the test** — a real second look that disagrees. That is `n06`, which converts
d23 from a single-mechanism test into a graded one: three citations → one look → never `confirmed`; one
genuinely independent look that disagrees → the count is a **named gap with two sourced contradictory
assessments attached**, escalated, not averaged. n06 is grade B and d23 is grade D, so a naive "trust the
better source" rule adopts "not fewer than three" as a figure and drops the open bound — which is why the
paper deliberately states no upper bound at all.

---

## 6. What I did not touch

- `corpus/scenarios/*/answer_key.json` — untouched.
- Every **existing** document and every existing claim bundle — untouched. All 492 frozen claims intact. Only
  the six `n0*.txt` documents I authored were rewritten.
- `SCENARIO_MANIFEST.json` — untouched (`n_docs` is generation output; the re-record regenerates it).
- `config/places.yaml` — untouched. The new sites carry explicit coordinates in their own documents; adding
  gazetteer entries would pre-solve part of what the coordinate canonicaliser should be doing.
- `layer_routing.superseded_derived_bundle_suffixes` says "RK-DATA removes the bundles from the corpus".
  **I have not**, because the hard constraint forbids deleting claim bundles. The flag-gated skip already
  handles it; removal is a separate, explicitly-authorised pass.
- `earned_identity` and every ceiling / threshold / weight in `config/resolution.yaml` — untouched. The trap
  is built to fit the shipped rails, not the other way round.

---

## 7. For the re-record and the oracle regeneration

Everything in §3 and §4 is a specification and a code-read argument. These are the measurements that have to
follow, in order. Checks 1 and 2 decide whether the centrepiece is live at all.

1. **Does the trap pair share a resolved neighbour?** The single load-bearing precondition, and the first
   thing to look at. `colocation_only` returns `None` when `bd[RELATIONAL] <= 0` — "nothing shared ⇒ nothing
   for co-location to explain" — so **if the two battery nodes share no neighbour, the cap does not fire.**
   Worse: if they also agree on any non-taxonomic attribute (`home_garrison` is the likely one) then
   `_name_alone` is false as well, **neither** cap fires, and the exact-name bootstrap **fuses them
   silently**. Both n01 §3.7 and n02 state the station and the equipment class, so there are two chances at a
   shared neighbour — but it must be verified, not assumed. If it fails, the fix is on the data side (make
   both documents state the same site), never by weakening a cap.
2. **Which rail actually fires on the trap pair?** Grade the *rail*, not just the outcome. Expected: ceiling
   `probable`, rail `colocation_ceiling`, with a queue place. `name_ceiling` (ceiling `possible`,
   watch-listed, off the queue) is a **safe** outcome but means the trap is inert — the pair shared nothing.
   `cross_identity` means the two mentions were typed or namespaced apart. No record at all means they fused,
   which is the failure §4.4 describes.
3. **What does `designator` extraction emit for `22 Air Defence Regiment`?** (§3.5.) A bare `22` makes
   `(Pakistan Army, 22)` a complete composite AND-key across two different arms and lifts every cap — the
   finding n05 was authored to surface. Also confirm **no `designator` is invented for the undesignated
   battery on either side**: one invented on both would complete the same key and lift the trap's only rail.
4. **`site_type` — the interaction that could not be measured before the re-record.** The §2.1 mapping was
   measured on a store where n01–n06 carry no claims. After the re-record, existing documents' site labels
   and the new documents' interact, and that cannot be guessed at. The specific pairs to look at:
   - **`site_rahwali`** — does it land `airfield` (d18) or `Pakistan Army/PAF joint-use facility` (d19)? The
     second silently returns the flagship to held-with-a-gap. Fix on the data side, not by mapping an
     operator-class string.
   - **`site_rawalpindi`** — what string does it land now? If the re-record emits `cantonment` (n01/n02/n05
     use the noun heavily and extraction prompts are shared), it stays **unmapped** by design (§2.3) and the
     flagship holds. Only after measuring both ends should `cantonment: garrison` be considered, and only if
     it does not split the flagship's two buckets.
   - **Pano Aqil Cantonment vs the two n03 positions** — does name containment fuse a position node into the
     cantonment node? If so, n03's two positions collapse and §3.3's background invariant is broken. It would
     also change what the trap pair shares, which feeds back into check 1.
   - **Any subject acquiring a second `garrison`-class basing.** `basing.py` derives `based-at` for every
     formation an `inducted-into` edge reaches, at every site the equipment is observed. If a newly-created
     regiment node acquires induction reach, it can pick up derived basings at Karachi (`centre` → `garrison`)
     *and* at Pano Aqil — two basings in **one** class bucket, which is a supersede, which is a **relocation
     that never happened**. Enumerate every unit's basings per class bucket after the re-record.
5. **Do the two new alias rows match what extraction emits?** (§2.2.) `revetted launch position` and
   `unimproved hardstand` are predictions from n03's wording. If different strings land, add the rows that
   landed; if a near-variant lands unmapped, the third state applies — held, no fusion, named gap: safe, but
   the site classes go inert. Do not weaken the third state.
6. **Is `8477 AD` / `8471 AD` ever proposed as a pair?** (§3.4.) The keep-separate is only gradeable if the
   resolver proposes it. If blocking never brings them together, record that plainly — it is not a win.
7. **Confirm 22 AD Regt's garrison basing now has exactly two independent looks** (n01, n05), not three
   (§3.2). Whatever status it reaches is then a real reading of the independence logic.
8. **Sanity-check the `n04` class/grade split** (`named-social` + STANAG C). Deliberate and reasoned in
   `config/sources.yaml`, but the one assignment here a reviewer should re-derive rather than accept.
