# RK-DATA — identity-coverage authoring spec

**Branch:** `rkdata/author` · worktree `wt-RK-DATA` · 2026-07-26
**What this is:** six new corpus documents, one config mapping, and — the part that matters more than the
documents — **the statement of what the system must produce and what it must refuse for each**. That
specification is what the re-record and the oracle regeneration grade against.

**Additive only.** No existing document, no existing claim bundle, and `answer_key.json` were edited or
deleted. The new documents carry **no claims until the re-record extracts them**, which is inert and
expected. `SCENARIO_MANIFEST.json` still says `n_docs: 25`; the re-record regenerates it and I have
deliberately not hand-edited generation output.

---

## 1. The gaps, confirmed before writing anything

Checked across **both scenarios** — 30 frozen claim bundles / **492 claims**, and all document text under
`corpus/` (72 doc files, 29 raw specimen files).

| Claimed gap | How I checked | Result |
|---|---|---|
| **Zero numbered or designated formations** | enumerated every `unit`-typed entity in all frozen claims | **Confirmed.** 22 unit mentions, all services or commands: `Pakistan Air Force`, `PAF`, `Pakistan Army Air Defence Command`, `Army Air Defence Command`, `Army Air Defence`, `Pakistan Army Air Defence (PAAD)`, `Air Defence Command`, `Pakistan Army`, `People's Liberation Army Air Force`, `AIR HEADQUARTERS PROCUREMENT DIRECTORATE`, `PAF air defense units`. Not one designator. |
| **Zero equipment or unit serials/registrations** | attribute-name scan over all claims; regex sweep for serial/registration/chassis/hull/bort patterns over all doc text | **Confirmed.** No serial-bearing attribute exists in any claim. The only `Serial:` string in the whole corpus is `GIS-2022-0311-KHI` — an imagery *product* ID, not equipment individuation. |
| **Zero coreference annotations** | key scan for coref/mention/anaphor/antecedent across all bundles | **Confirmed.** Zero. |

So `formation_discriminators`, `hard_id_fields.unique.unit`, the coreference binding tier and gates
G16/G18/G19 are fixture-only on the real corpus. That is what these six documents close.

---

## 2. Deliverable 1 — the `site_type` mapping (the owed item)

**Spec read:** `tmp/conv/S2-DATA-to-DATAC-site-type-vocabulary.md`, ruling L1 step 4. S2 declares the closed
vocabulary and the fail-safe in `config/ontology.yaml → layer_routing`; **DATA owns mapping the values the
corpus actually states**. `site_type_aliases` shipped `{}`, so every stated value but `airfield` fell into
the third state and — correctly, per the fail-safe — the **flagship relocation was held with a named gap**.

### What I changed

`config/ontology.yaml → layer_routing.site_type_aliases`, three entries:

| Stated value (and where) | → class | Why |
|---|---|---|
| `centre` (d02, ISPR "Army Air Defence Centre, Karachi") | `garrison` | A corps/arm "Centre" in Pakistan Army usage is the permanent home establishment of the arm. `command_centre` reads the word in the wrong sense. |
| `deployment site` (d23) | `dispersal_site` | A site a battery is described as deployed *to*, as against its home station. |
| `prepared revetment complex / airfield site` (d17) | `airfield` | Two axes in one string. "prepared revetment complex" is the emplacement *within* the place; "airfield site" is the place (PAF Base Nur Khan). The place-kind noun governs. |

### What I deliberately did NOT map, and why

The omissions are as load-bearing as the entries; they are all documented in the config comment.
`observed-imagery-site` and `stated_destination` state **how we learned** of a site (provenance axis).
`HQ-9/P site`, `air defense node`, `long-range SAM battery position` state **what is parked there**.
`candidate coverage area`, `air defence belt`, `forward SAM deployment area` are **area classes** — a
different node type. `Pakistan Army/PAF joint-use facility` is an **operator class** whose only place-kind
noun ("facility") is generic: a depot, a plant and an airfield are all facilities. Mapping any of those
would infer a kind of place from something that is not one — the exact over-merge direction the fail-safe
leans against. They keep the honest third state.

### Measured effect (rebuilt the real corpus, before and after)

`unit_hq9b` carries four derived `based-at` edges. Before, only one of the four site classes resolved:

```
before:  Army Air Defence Centre, Karachi   'centre'                                    -> unknown (unmapped)
         Sargodha                           'deployment site'                           -> unknown (unmapped)
         site_rahwali                       'airfield'                                  -> airfield
         site_rawalpindi                    'prepared revetment complex / airfield site' -> unknown (unmapped)
```

Any unmapped class on any of a subject's basings collapses the whole subject to one bucket with no fusion,
so **no supersede edge existed**. After the three entries, all four resolve — `garrison`,
`dispersal_site`, `airfield`, `airfield` — and the rebuild draws exactly one supersede:

```
supersedes  site_rahwali -> site_rawalpindi
            source_edge_instance: edge:unit_hq9b:based-at:airfield
```

So both halves land: **the flagship Rawalpindi→Rahwali relocation is restored** (both ends are airfields,
one instance, a genuine change of position), and the **Karachi garrison and the Sargodha dispersal basing
de-conflict into concurrently-valid basings** in buckets of their own — no relocation is drawn between
them, which is the C1 rule doing its job. Full `backend/tests/view`, `tests/config` and `tests/api` pass
after the change, including the gate that pins the held-with-a-gap behaviour (it reads the two sites'
*classes* rather than assuming them, so it self-adjusts and now asserts the promoted edge).

### Two strict-xfail markers retired

`backend/tests/acceptance/test_relocation_beat.py` carried two `xfail(strict=True)` markers whose reason
text ended: *"TO CLOSE: the DATA pass populates `layer_routing.site_type_aliases` … then re-record. Do NOT
close it by weakening the third state."* With the mapping in place both **XPASS**, i.e. the relocation beat
now fires end-to-end with before/after and provenance, and exactly one alert on exactly the watched unit.
Strict xfail turns that into a failure on purpose, so that whoever closes the gap has to retire the marker
rather than leave a stale one. Both are removed and replaced with a comment recording the cause, the fix,
and that the third state was **not** weakened. The second of the two is worth keeping in mind as a guard:
it asserts the alert set is *only* the watched unit, so an over-eager mapping that manufactured collateral
relocations would fail there rather than pass quietly. That is a second reason the unmapped values stayed
unmapped.

**One residual fragility, stated rather than hidden.** `site_rahwali` is described two ways in the corpus —
`airfield` (d18) and `Pakistan Army/PAF joint-use facility` (d19) — and which one lands on the node depends
on claim ordering. If the re-record gives it the operator-class string, the flagship silently returns to
the held state. That is *safe* (held + named gap, never a fabricated move), but it is a silent regression
in the demo. The re-record should check it. Do **not** close it by mapping the operator-class string.

---

## 3. Deliverable 2 — the six documents

All are `corpus/scenarios/hq9p_primary/docs/`, registered in `config/sources.yaml`. Every one is
**synthetic-from-real-template**: the format and the messiness come from a real specimen, the entities and
values are varied synthetically. **No document contains a clean field, an ontology value, or a stated
verdict.** Places used are real (Pano Aqil / Panu Aqil / Pannu Aqil Cantonment, Sukkur District; Ghotki
District; the N-5) with synthetic coordinates and synthetic formations.

### Corruption operators — the enumerable set actually applied

Every operator below is one you can name out loud on a call. Per-document assignment is in §3.1–3.6.

1. **OCR / transcription digit confusion** — `8477 AD` misread as `8417 AD`, with the correction log.
2. **Coordinate transcription error** — `069°08'20"E` mistyped `069°80'20"E`, caught in the document.
3. **Transliteration variance** — Pano Aqil / Panu Aqil / Pannu Aqil / Pano Akil (a genuinely real variance).
4. **Truncated / withheld field** — chassis prefix unresolved, suffix only; appendix "not attached"; a phone number cut short.
5. **Date-format drift** — `18 Feb 2025` / `2025-03-19` / `27/03/2025` / `31/03/25` / `22/03/2025` in one corpus.
6. **Copy-paste duplication** — a register index line duplicated under a second rendering; a vehicle entry re-entered under the other place spelling and struck through.
7. **Hedge attached to the wrong clause** — "reportedly following the completion of conversion training" (hedge lands on the ceremony, not on the equipment); "reportedly having been arrived at by counting vehicles".
8. **Unit-of-measure drift** — 27 km / ~17 statute miles / 14.6 nm for one distance.
9. **Carried-forward unverified entries** — `(u)`-marked register rows, an entry that may be a duplicate of another arising from the spelling variance.
10. **Currency / staleness drift** — "lineage material is as at 2019 and has not been re-verified"; a closing date printed under current-tense prose.
11. **Designator rendering drift** — `22 Air Defence Regiment` / `22 Air Defence Regt` / `22 AD Regt` / `22 AD`.
12. **Disagreeing readings published side by side** — two contributors reading one chassis prefix differently; two histories giving different redesignation years.

---

### 3.1 `n01_orbat_register.txt` — the ORBAT register (formation-shaped input)

**Specimen modelled on:** IISS *Military Balance* country ORBAT tables + army-list / orbat-register layout;
in-corpus register standard is `cd07_unit_collision` (unit history and lineage reference).
`config/sources.yaml`: `curated-register / B / third-party / 365d`, report_date 2025-03-31.
**Operators applied:** 3, 5, 6, 9, 10, 11.

**What it plants.** The corpus's first **numbered, designated formations with parent formations**:
`22 Air Defence Regiment` (Pakistan Army, Air Defence; garrison Pano Aqil Cantonment; under **3 Air Defence
Brigade**) and `47 Air Defence Regiment` (same garrison; under **11 Air Defence Brigade**), plus `9`, `33`
and `56 Air Defence Regiment` as register texture. It also states, in the source's own voice, the C1
concurrency: 22 AD Regt's B Battery detached forward to the Ghotki dispersal site since Feb 2025 **while**
RHQ and the remaining batteries continue at the Pano Aqil garrison — "both locations are therefore current
simultaneously and the detachment should not be read as a move of the regiment."

**Must produce:**
- `unit` nodes carrying `designator`, `service_branch`, `parent_unit`, `echelon` — the first in the corpus.
  This is what gives `formation_discriminators` (`parent_unit`) and `hard_id_fields.unique.unit`
  (`service_branch` + `designator`) something to grip.
- A **STATED** `based-at` for each regiment at Pano Aqil Cantonment, site kind **`garrison`** (maps natively).
- The 22 AD Regt garrison basing **and** the Ghotki `dispersal site` basing as **two concurrently valid
  basings** — different site classes, so C1's wall does not fire and no relocation is drawn.
- The 33 AD Regt row must stay **unconfirmed** and uncounted (the register itself says it may be a
  duplicate arising from the spelling variance).

**Must refuse:**
- To merge 22 AD Regt with 47 AD Regt on shared garrison + shared equipment class + shared branch. These
  are the `colocation_predicates` by construction. The pair is capped at **`probable`** (G16) and reaches
  the analyst; it never auto-merges.
- To draw any relocation for 22 AD Regt between its garrison and the Ghotki dispersal site.
- To emit a battery or launcher count. The register states three times that it carries none.
- To treat `Pano Aqil` / `Panu Aqil` / `Pannu Aqil` as different stations.

---

### 3.2 `n02_ispr_panoaqil.txt` — the corroborating official release (+ clean coreference)

**Specimen modelled on:** real ISPR press-release format (`md/05` §2.4), in-corpus standard `d02_ispr_induction`.
`config/sources.yaml`: `official / B / operator-state / event-driven`, report_date 2025-02-18.
**Operators applied:** 3, 4, 5, 7, 11.

**What it plants.** A second, interest-independent look at the **same stated basing** — 22 Air Defence
Regiment at its Pano Aqil garrison — so a **STATED** `based-at` can legitimately reach `confirmed` instead
of only the capped derived kind. It carries a clean **EXPLICIT_EQUIVALENCE** with a marker from the
configured vocabulary and both surface forms in one span: *"22 Air Defence Regiment, also known as the
Indus Gunners"*, and a second: *"22 Air Defence Regiment (hereinafter referred to as the Regiment)"*. It
restates the concurrency in the operator's own voice ("holding both its garrison responsibilities and a
forward commitment at the same time").

**Must produce:**
- `confirmed` on `22 AD Regt based-at Pano Aqil Cantonment` — two looks, different origins, different bias
  vectors (third-party register + operator-state official), neither an aggregator of the other.
- An **authoritative** coref bind `22 Air Defence Regiment ≡ Indus Gunners`: the quote occurs verbatim,
  contains both surface forms and the configured marker `also known as`, and the source is grade B, clearing
  `bind_min_grade: C`.

**Must refuse:**
- To disclose or infer a battery/launcher count. The release says explicitly that none were disclosed and
  that none should be inferred; a system that produces one has fabricated it.
- To read the forward deployment as a relocation.
- To let the misplaced hedge ("reportedly following the completion of conversion training") attach to the
  equipment holding.

**On the anaphor, honestly.** "the Regiment" is genuine anaphora, but `UNAMBIGUOUS_ANAPHOR` requires
*exactly one* type-compatible mention in the document, and an `unknown`-typed mention counts as compatible
on purpose. This release also names 3 Air Defence Brigade and the Corps of Army Air Defence, so the anaphor
will very likely **fail** the positive gate. **Both outcomes are correct and both are acceptable:** the
`hereinafter referred to as` span is an `EXPLICIT_EQUIVALENCE` and binds on that path; if the anaphoric
link is evaluated separately and fails, the correct result is **raise-only** — a `probable` HITL candidate
with the licensing quote attached, one click from the merge. What must **not** happen is an authoritative
bind on the anaphor alone while a second compatible mention is present.

---

### 3.3 `n03_panoaqil_imagery.txt` — the co-location engine (imagery read-out)

**Specimen modelled on:** in-corpus `d17` / `d18` commercial-EO analyst read-outs (themselves modelled on
CSIS AMTI dated-imagery write-ups). `config/sources.yaml`: `satellite / B / third-party / 7d`, **no
report_date** — the document states three pass dates and no document date, and ING-7 forbids inferring one.
**Operators applied:** 2, 5, 8.

**What it plants.** The mechanism the co-location cap exists for. **Two prepared emplacements 5.6 km
apart** at one cantonment, both occupied on all three passes, both HQ-9-family signature:

| | coordinates | fit | site kind stated |
|---|---|---|---|
| north emplacement | 27°51'40"N 069°05'10"E | 6 TEL-type + **octagonal** (HT-233-type) radar | `emplacement` |
| south-east emplacement | 27°50'30"N 069°08'20"E | 4 TEL-type + **rectangular** radar, a different class of object | `emplacement` |
| Ghotki dispersal pad | 28°00'15"N 069°18'40"E (~27 km NNE) | 4 TEL-type + rectangular radar | `dispersal site` |

All three kind-words (`emplacement`, `dispersal site`, and `garrison` in n01/n02/n05) are **already in the
closed vocabulary verbatim** — so this coverage needs no new alias rows, which was deliberate.

The document **names no formation at all** and says so four times. It enumerates the three readings it
cannot choose between (two units; one unit with two emplacements; one unit plus a training/depot holding),
notes the radar-planform difference is the best discriminator available and still does not settle it, and
states that the count at the cantonment "should be recorded as open rather than as one or as two". It also
pre-empts the fabricated-relocation reading directly: both emplacements were occupied on *every* pass,
including the passes on which the dispersal site was occupied.

**Must produce:**
- **Two distinct `basing_site` nodes.** 5.6 km apart is beyond every place-proximity merge radius and its
  HITL multiplier, so they must not fuse into one place. The Ghotki pad at ~27 km is beyond
  `entity_geo_conflict_max_km.basing_site` (25 km) — a geographic veto against fusing it with either.
- `observed-at` occupancy evidence only — equipment at a place — materialising **presences**, never a
  formation-level basing. The read-out states no formation, so there is nothing to state a `based-at` from.
- A **named gap on the unit count at Pano Aqil**, sourced to this document's own words.

**Must refuse:**
- To attribute either emplacement, or the dispersal pad, to any unit. Nothing in this document supports it.
- To emit a unit count of one or of two.
- To read the occupied dispersal pad as evidence that either emplacement was vacated — the document's own
  frames contradict that, and asserting it would be the fabricated relocation in its purest form.
- To resolve the `069°80'20"E` transcription error as a real coordinate (a minute value of 80 does not exist).

---

### 3.4 `n04_tel_fleet_register.txt` — the equipment fingerprint (serials)

**Specimen modelled on:** vehicle/aircraft **spotter registration logs** (the real `reg / type / unit /
date / place / photo-ref` line format used by spotter communities and by OSINT vehicle-documentation
registers), plus the in-corpus social register of `d08`.
`config/sources.yaml`: `named-social / **C** / third-party / continuous`, report_date 2025-04-02.
**Operators applied:** 1, 3, 4, 5, 6, 12.

**The class/grade split is deliberate and is the one call here worth a reviewer's eye.** `named-social` is
what this *is* — a contributor compilation — and its low R (≈0.35) is correct: it has no authority, so
nothing it *concludes* travels far. STANAG **C** is earned by its **process**, not its authority: every
entry is photo-backed with an archive reference, disagreeing plate readings are published rather than
resolved silently, and the misreading carries its own correction log. Grade C is what lets a photographed,
corrected plate reading clear the `bind_min_grade` / `critical_veto_min_grade` floors — which is right,
because the plate is a *directly observed* fact, and directness is the one thing this source class has.

**What it plants.** The corpus's first **equipment fingerprint that individuates one physical object across
two sightings**: TEL plate **`8477 AD`**, photographed at the Pano Aqil static display on 18 Feb 2025 and
again in a road move on the Ghotki bypass on 22/03/2025, tied together by **three independent points** —
the plate, the legible chassis suffix `0173`, and a distinctive weld repair on the left rear mudguard. It
also plants the near-miss: **`8471 AD`** photographed *in the same frame* alongside `8477 AD`, which is
exactly the pair the `8417` misreading would have muddled. And the **AMBIGUOUS ANAPHOR**: the commentary
names both 22 Air Defence Regiment and 47 Air Defence Regiment and then discusses "the regiment".

**Must produce:**
- A legitimate **presence-level merge** across the two sightings of `8477 AD` — this is the strongest
  honest merge evidence in the corpus, and the one place a merge should be *earned* rather than capped.
- `equipment_fingerprint` on the relevant instance, so the discriminator ladder finally has a rung it can
  actually climb.
- A **`distinct-from`-strength keep-separate between `8477 AD` and `8471 AD`.** They are legible in one
  frame side by side; fusing them on plate similarity is the over-merge this entry exists to catch.
- Recognition that the `8417 AD` form and the struck-through duplicate entry `AD/2025/019` are **the same
  vehicle and the same photograph** — one vehicle, two sightings, not three vehicles and not three sightings.

**Must refuse:**
- To bind "the regiment" to either 22 AD Regt or 47 AD Regt. Two type-compatible antecedents are present;
  the honest answer is **refusal**, both mentions stay singletons, the pair goes to the analyst.
- To attribute vehicle `8477 AD` to any unit. The document states four separate times that it cannot be
  attributed and that anyone attributing it is adding something the register does not contain.
- To conclude from one launcher's road move that a *regiment* moved. One launcher is not a regiment, and
  this is the exact inference chain the document itself refuses.
- To resolve the chassis prefix. `WS2400` vs `TAS5380` is published as unresolved; picking one is fabrication.

---

### 3.5 `n05_regiment_lineage_note.txt` — the anti-coreference document

**Specimen modelled on:** regimental lineage / nomenclature reference sheet — the same specimen family as
in-corpus `cd07_unit_collision` (Royal Corps of Signals unit-history note) and army-list extracts.
`config/sources.yaml`: `official / B / operator-state / irregular`.
**Operators applied:** 3, 5, 7, 10, 12.

**What it plants.** Three things the corpus has never had.

**(a) A stated contrast across a designator collision.** "22 Air Defence Regiment is not 22 Medium
Regiment" — same service (Pakistan Army), same number, different arm, "a separate regiment, of a separate
arm". **This is a live test of `hard_id_fields.unique.unit = [service_branch, designator]`.** If
`designator` is extracted as the bare number `22`, then both units share `(Pakistan Army, 22)` — a complete
composite AND-key — and the top rung of the ladder **lifts every cap and merges two different regiments**.
If `designator` is extracted as the full designation (`22 Air Defence Regiment` vs `22 Medium Regiment`),
the key does not match and nothing lifts. Either way the document's own stated contrast caps the pair at
`probable` and queues it, so the wall holds — but **if this pair merges, the finding is that designator
extraction is taking the bare number, and that is a defect to fix, not a threshold to tune.**

**(b) A stated contrast between the two co-located regiments** — "It is nonetheless a separate regiment",
under a different brigade, "sharing a cantonment and sharing an equipment fit are not evidence of being one
regiment". This is the same-document contrast the `contrast_ceiling` exists for.

**(c) A true redesignation equivalence** — "22 Air Defence Regiment, formerly 22 Light Anti-Aircraft
Regiment, is the same regiment under a changed name and not a successor unit". Marker `formerly` is in the
configured vocabulary and both surface forms are in the span.

**Must produce:**
- A `CoreferenceContrast` on **22 AD Regt vs 22 Medium Regiment** and on **22 AD Regt vs 47 AD Regt**,
  capping each pair at `probable` — reaching the analyst with the licensing quote, never auto-merging.
  (`possible` is rejected at load for this key precisely so the escalation is not dropped.)
- A same-as / alias bind **22 Air Defence Regiment ≡ 22 Light Anti-Aircraft Regiment**.
- The general rule restated as a claim in its own right: a bare regimental number is never an identifier,
  numbers are reused across arms, and the PAF runs a separate numbered series.

**Must refuse:**
- To merge 22 Air Defence Regiment with 22 Medium Regiment on any evidence in this corpus.
- To merge 22 with 47 Air Defence Regiment.
- To treat the detachment as a change of garrison — the sheet says the garrison is unchanged and that both
  locations are current at once.
- To carry the 2019 lineage dates as current facts (the sheet flags them unverified since 2019).

---

### 3.6 `n06_battalion_count_recount.txt` — the independent recount (the d23 answer)

**Specimen modelled on:** think-tank occasional-paper / methodology note (RAND RR-series, CSIS Missile
Threat, IMINT&Analysis "counting SAM sites from imagery" register).
`config/sources.yaml`: `think-tank / B / third-party / irregular`, report_date 2025-05-12.
**Operators applied:** 4, 5, 7, 10.

**What it plants.** A genuinely independent second look at the quantity `d23` circulates. It traces
"approximately 4 battalions" to its origin (three outlets, all attributing to SIPRI, none with collection
of its own, two reproducing the sentence near-verbatim), restores the two caveats that fall out of the
retelling (SIPRI calls the figures **estimates**; the register counts **transfers**, not **fielded** fire
units), and then counts independently from archived imagery: **six prepared positions**, of which **three**
show persistent occupancy, two intermittent, one never observed occupied. Its result is deliberately a
**floor with an open upper bound** — "not fewer than three fire units, upper bound unresolved" — and it
explicitly declines to endorse the published figure. It uses Pano Aqil as its worked example of why
positions are not units, and records the count there as **OPEN**.

**Must produce:**
- The `approximately 4 battalions` figure resolved to **one origin group**, not three looks. n06 states the
  aggregator chain in terms the pipeline can act on.
- A **contradiction between two independent quantitative assessments** on the same attribute → the holding
  count is a **named Known Gap**, not a confirmed number. This is the correct output, and it is worth more
  than either number.
- A distinction the corpus has never carried: **prepared positions ≠ fire units**. Six positions must not
  become six units, and three persistently occupied positions must not become exactly three units either.

**Must refuse:**
- To count n06 as **corroboration** for "approximately 4 battalions". It disagrees with it and says so.
- To publish a single battalion figure as confirmed on this evidence.
- To silently drop the open upper bound. The document names that specific failure — "a floor quoted without
  its open bound becomes a figure within about two citations" — and the system reproducing it would be
  reproducing exactly the pathology it was given the document to catch.

---

## 4. The ORBAT undercount trap, end to end — the correct output

This is the single highest-value thing in the set, so it is stated once, plainly, across all six documents.

**The ground truth (no planted lie — every document is accurate):** there are **two** long-range air
defence regiments at Pano Aqil Cantonment, 22 AD Regt under 3 AD Bde and 47 AD Regt under 11 AD Bde. There
are **two** occupied prepared emplacements at that cantonment, 5.6 km apart, with different radar fits.
**No source in the corpus attaches either emplacement to either regiment.** One battery of 22 AD Regt is
concurrently forward at the Ghotki dispersal site, and its garrison basing remains current.

**The trap:** 22 and 47 share design, site, operator branch, service branch and equipment class. Every one
of `colocation_predicates` — `based-at`, `observed-at`, `instance-of`, `operated-by`, `equips`,
`inducted-into` — is shared **by construction**. A naive resolver reads that as overwhelming identity
evidence and fuses them. Once fused, the single unit has a garrison basing and a forward dispersal basing;
`based-at` is functional and unit-keyed, so the supersede path draws a **relocation that never happened**,
marks the pair machine-adjudicated so it leaves the analyst's queue, and **deletes the honest Known Gap**
on the count. One identity error becomes a fabricated movement assessment with the human removed.

**What the system must produce:**

1. **Two units, not one.** The co-location cap holds the 22/47 pair at `probable` (G16) and it reaches the
   analyst. The available discriminators do not lift it: `parent_unit` differs where it is stated
   (3 AD Bde vs 11 AD Bde), `equipment_fingerprint` exists for only one side, and `designator` and
   `echelon` are deliberately excluded from `formation_discriminators`. n05 adds a **stated contrast** in
   the document's own words, capping it again at `probable` from the other direction.
2. **No relocation, anywhere in this cluster.** For 22 AD Regt, garrison and dispersal site are different
   site classes, so C1 makes them two concurrently valid basings. For the two emplacements, no formation is
   attached to either, so there is no unit-keyed pair to supersede. For vehicle `8477 AD`, one launcher
   moving is not a formation moving.
3. **A named gap where the count is genuinely unresolved** — how many long-range AD fire units are at Pano
   Aqil Cantonment. n03 and n06 both state that this is open in their own words, and the gap must name
   what is missing (an order-of-battle source attaching a formation to a *position*, or an equipment
   identifier tying a vehicle to a *unit*) and survive as a gap rather than being closed by inference.

**What it must refuse to produce:** a single fused Pano Aqil unit; any `based-at` from either emplacement
to either regiment; a relocation between the two emplacements, or from either to Ghotki; a battery count
for Pano Aqil; a unit attribution for `8477 AD`; a merge of `8477 AD` with `8471 AD`.

**A failure here is not a scoring miss.** It is the system inventing a movement of a real formation and
removing the human who would have caught it.

---

## 5. Item 6 — how `d23`'s circular corroboration should be used, and my call

**Use it as it stands, unchanged.** `d23` is already a complete specimen of the thing: "approximately 4
battalions" carried by three trade outlets, all attributing to the SIPRI Arms Transfers Database "without
independent sourcing of their own", with SIPRI's own estimate caveat "not always carried forward by the
outlets citing it". The correct handling is that the three collapse into **one origin group** and the
figure gains no corroboration from being printed three times.

**My call: do NOT extend the chain with a fourth echo.** A fourth reshare adds no mechanism the existing
three do not already exercise, and the corpus already carries a six-post echo burst (d11–d13 + ce01–ce03)
for exactly that pattern. What `d23` genuinely lacked was **the other side of the test** — something that
proves the system can tell one look from three *and* can then handle what happens when a real second look
arrives and disagrees. That is `n06`. It converts d23 from a single-mechanism test (aggregator collapse)
into a graded one:

- three citations → **one look** → the figure stays `probable` at best, never `confirmed`;
- one genuinely independent look, with its own stated method, that **disagrees** →
- the count is a **named gap with two sourced, contradictory assessments attached**, escalated, not averaged.

Averaging them, or preferring the higher-graded source silently, would both be wrong. n06 is graded B and
d23 is graded D, so a naive "trust the better source" rule would simply adopt "not fewer than three" as a
figure and drop the open upper bound — which is the failure n06's own closing paragraph names.

---

## 6. What I did not touch

- `corpus/scenarios/*/answer_key.json` — untouched.
- Every existing document and every existing claim bundle — untouched. All 492 frozen claims intact.
- `SCENARIO_MANIFEST.json` — untouched (`n_docs` is generation output; the re-record regenerates it).
- `config/places.yaml` — untouched. The new sites carry explicit coordinates in their own documents; adding
  gazetteer entries would have pre-solved part of what the coordinate canonicaliser should be doing, and
  the proximity radii do the separation correctly at these distances.
- `layer_routing.superseded_derived_bundle_suffixes` says "RK-DATA removes the bundles from the corpus".
  **I have not**, because the hard constraint forbids deleting claim bundles. The flag-gated skip already
  handles it; removal is a separate, explicitly-authorised pass.

## 7. For the re-record and the oracle regeneration

1. **Extract n01–n06.** They carry no claims until then; everything in §3 is a specification, not a
   measurement, until the re-record produces claims.
2. **Check `site_rahwali`'s `site_type` survives as `airfield`** (§2 residual fragility). If it lands as
   `Pakistan Army/PAF joint-use facility`, the flagship silently returns to held-with-a-gap. Fix it on the
   data side, not by mapping an operator-class string.
3. **Check what `designator` extraction emits for `22 Air Defence Regiment`** (§3.5). Bare `22` makes the
   composite AND-key match across two different arms. That is the finding n05 was authored to surface.
4. **Confirm the three site-kind words survive extraction verbatim** — `garrison`, `emplacement`,
   `dispersal site`. All three are already in the closed vocabulary, so no new alias rows are needed *if*
   they survive. If extraction states a near-variant instead, the third state applies: **held, no fusion,
   named gap** — safe, but it leaves the co-location trap inert. Add the row and re-record; do not weaken
   the third state.
5. **Sanity-check the `n04` class/grade split** (`named-social` + STANAG C). It is deliberate and reasoned
   in `config/sources.yaml`, but it is the one assignment here a reviewer should re-derive rather than accept.
