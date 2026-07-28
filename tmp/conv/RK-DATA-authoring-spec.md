# RK-DATA — identity-coverage authoring spec

**Branch:** `rkdata/author` · worktree `wt-RK-DATA` · 2026-07-26 (**rev 4** — the first revision whose trap is
measured end-to-end rather than argued from a code read; start at §0b)
**What this is:** six new corpus documents, five config mappings, and — the part that matters more than the
documents — **the statement of what the system must produce and what it must refuse for each**. That
specification is what the re-record and the oracle regeneration grade against.

**Additive only.** No existing document, no existing claim bundle, and `answer_key.json` were edited or
deleted. As of rev 4 the six new documents **do** carry claims: they were extracted with a real key
(`claude-opus-4-8`, `--offline` geocoder) into six new `n0*.json` bundles beside the frozen ones. §3 and §4
below remain a specification and a code-read argument written before that; **§0b is the measurement, and
where the two disagree the measurement wins.**

---

## 0b. What rev 4 changed — and the first version of this trap that is MEASURED, not argued

Rev 3 was still vacuous, and a third adversarial pass found it the only way it could be found: by **running
the experiment** instead of walking the rails on paper. Its finding was that relaxing the co-location cap
changed nothing, so the cap was not the restraint — the pair was being intercepted upstream by the NAME cap,
which is strictly worse, because `name_ceiling: possible` withholds the pair from the analyst's queue as well
as from fusion. Rev 4 closes that, and everything below is a measurement on the real corpus, real keyed
extractions, and the shipped config.

**The root cause: the station had no identity anchor.** `Pano Aqil` in any spelling appeared nowhere in
`config/places.yaml`, while every other station the corpus uses (Nur Khan, Rahwali, Karachi, Sargodha,
Gujranwala) has a row. Two mentions of one station could therefore only meet on their *name*; a name-alone
pair is capped at `possible`; the two stations stayed two nodes; the batteries standing at them shared no
neighbour; `colocation_only()` early-returns on `bd[RELATIONAL] <= 0`; the cap never ran.

**The fix: `pl_pano_aqil`, precision_class `site`** — the same standing Rahwali Cantonment has, and the field
that matters, because `site` is inside `place_identity_precision_classes` and may therefore constitute
identity. Four spellings seeded; **`Panu Aqil` deliberately withheld** on the `pl_nurkhan`/"Chaklala" pattern,
chosen because it is the only variant the corpus uses as a real location *value* rather than only inside a
spelling note. It is off the trap's path, so the cap remains the restraint.

**Two area anchors were written and then WITHDRAWN on measurement** (`pl_sukkur`, `pl_ghotki`). With a Sukkur
row present the geocoder stamped the *city's* coordinate onto the station node — INGEST had frozen the admin
tail "Sukkur District, Sindh" as that node's location phrase — and that coordinate, ~30 km from the station,
then contradicted the station's own toponym and killed the match outright. A coarse coordinate on a fine node
is not a harmless approximation; it is a veto on the node's own name. Full note in `config/places.yaml`.

**Three document changes were needed beyond the anchor, all of them removing extraction artefacts rather
than adding evidence:** §3.7 of the register now uses the same labelled-field convention as §3.4 (it was
prose, and produced an entity with no edges at all); both battery mentions now state the station in a form
the extractor turns into a `based-at` rather than only a `home_garrison` attribute; and the two documents
deliberately render the station *differently* — the register writes "Pano Aqil Cantonment", ISPR writes
"Pano Aqil Cantt" — so that the site merge can only happen through the gazetteer.

**THE EXPERIMENT (2×2; only two things varied — the ceiling, and whether `pl_pano_aqil` exists):**

| | `colocation_ceiling: probable` (shipped) | `colocation_ceiling: confirmed` (relaxed) |
|---|---|---|
| **anchor present (shipped)** | **not fused, QUEUED**, reason = co-location cap, naming `equipment_fingerprint`/`parent_unit` as what would lift it | **FUSED** |
| **anchor removed (control)** | not fused, **not queued** — watch-list only, reason = name cap | not fused, **not queued** — name cap |

The top row is the bar, met: the cap is the sole load-bearing restraint. The bottom row is the reviewer's
defect reproduced exactly, and is the proof that the anchor is what closes it. `relational` on the pair:
**0.167 with the anchor, 0.0 without.**

**And the transliteration demo is live rather than inert.** With the anchor, "Pano Aqil" / "Pano Aqil
Cantonment" / "Pano Aqil Cantt" fold onto one station node; without it they are three separate stations. The
withheld "Panu Aqil" stays its own un-anchored node, exactly as intended — it has to be earned.

**A separate defect the experiment surfaced: `n04` extracted ZERO claims.** `source_type` also selects the
extraction schema, so filing the vehicle register as `named-social` handed it the social-post tool
(handle/timestamp/status-URL/body), which it cannot fill — the plate-discrimination beat, the disputed
chassis reading and the correction log were all mute. Fixed with a new `contributor-register` source class
(R≈0.56 — credit for method and for having taken the photograph, never for standing); measured after: 19
claims. Unrelated to the trap; see `DECISIONS.md` §7 of the rev-4 entry.

**Three defects the SUITE caught, and one stale assertion.** `n03`'s ALL-CAPS position headings split every
position into two case-variant nodes; `n03`'s per-position coordinate lines made the extractor fold the fix
into the position's *name* (now a CENTRES OF SIGNATURE table); and `n01`/`n05` repeated the full admin form
in every `Garrison:` field, against their own spelling notes, minting a long-form duplicate of the station.
All three fixed in the documents. The fourth was **not** a data defect:
`test_no_source_asserted_signal_means_no_citation_to_click` asserted an invariant `resolve` had deliberately
superseded (candidate edges cite `licensing_claim_ids`, which includes a raise-only coreference, precisely
so such a proposal does not reach the analyst with an empty drawer). Narrowed to what the design does hold —
a zero-scoring edge may cite a coreference claim but never an identity assertion — and renamed. Production
code untouched. `DECISIONS.md` §§8-9 of the rev-4 entry.

**Known limitation, measured, not closed.** `places.place_matches` runs *before* endpoint minting, so a
station named only as the object of a `based-at` never reaches the gazetteer even when its string is a seeded
alias — which is why "Pano Aqil Cantonment, Sukkur District, Sindh" is still its own node. That is a RESOLVE
pass-ordering issue, not a gazetteer one, and it is on the roadmap.

---

## 0a. What rev 3 changed, and why

A second adversarial pass walked the rails against the shipped config and code rather than against this
document. Its verdict: the rev-2 design is right, and **two defects stopped it working**. Both are closed
here, and both were confirmed by measurement before being acted on — not accepted on assertion.

1. **The branch wording did not fold, and it defeated the trap.** n02's "Corps of Army Air Defence" returns
   `mapped=False` from the shipped `value_normalization` map. `service_branch` is a
   `normalization_required_attrs` slot, so `unnormalizable_critical_values` fires, the pair is refused on the
   **normalisation rail**, and `colocation_ceiling` is never consulted — the exact vacuity rev 2 existed to
   remove, reintroduced by a wording choice. Same root cause in n05, three more times, with a knock-on rev 2
   missed: n01 states 22 AD Regt's branch in a form that **does** fold, so leaving n05 unfolded split one
   regiment across two branch values. All four values restated in forms the shipped normaliser folds, with
   **no new alias row**. Measured fold table in §4.3.
2. **Documents still stated the answer, and the worst one defeated the trap outright.** n06 §3 wrote "we
   record the number of units at that cantonment as OPEN" — verbatim the conclusion the trap requires the
   system to derive, which lets the system source it from a document and turns the centrepiece into a
   reading-comprehension test. Removed, along with n06 §3's stated positions-are-not-units rule, three
   adjudications in n03, three in n04, and one in n05. **Each was replaced with its observational form**
   wherever a real document of that type would carry the observation; deleted outright only where the
   sentence was a conclusion with no observation under it. Per-document reasoning in §3.3–§3.6.

Two further items. The **two `site_type` alias rows** rev 2 added are withdrawn: they were keyed to phrases
n03 uses verbatim, written by the same hand in the same pass, so they could not miss and therefore measured
nothing (§2.2). And the **harm description** is corrected at the source: `resolution.yaml`'s comment on
`colocation_ceiling` claimed the harm is a fabricated relocation, which **this trap cannot produce** — both
mentions are at one site, so there is no before/after to order. The comment now separates the always-present
undercount from the different-sites-only relocation, and §4.4 does not inherit the stronger claim.

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

### 2.2 The two rows added in rev 2, and WITHDRAWN in rev 3

Rev 2 added `revetted launch position → emplacement` and `unimproved hardstand → dispersal_site`, keyed to
phrases n03 uses **verbatim**. The review's follow-up is right and the rows are withdrawn.

The rev-2 reasoning was sound as far as it went: rev 1's n03 supplied the closed vocabulary as clean labelled
fields (`Position type: emplacement`), handing the extractor the controlled value, and needing no alias row
is not a win. But the remedy reproduced the defect one level down. Both sides of those two rows — the key,
and the document the key reads — were written by the same hand in the same pass, so the row **could not
miss**. A row that cannot miss measures nothing about whether the alias step absorbs a string it did not
anticipate; it records only that a phrase was copied correctly, while still fixing what n03 is allowed to say.

**Is the machinery therefore a no-op? No — but the *test* was.** The map still has to fire for n03's prose to
classify at all, and n03 contains no controlled value anywhere, so the vocabulary is not literally in the
document. What was vacuous is the *evidence* the rows were added to supply. That is a smaller defect than the
one rev 2 fixed, and it is fixable without touching the machinery.

**The fix is consistency with this file's own doctrine.** §2.3 applies *measure-first* to `cantonment`
because a predicted row could do damage. Applying measure-first to the row that could break the flagship, and
predict-and-mirror to the two rows that make our own new document look exercised, is the tell. So n03's site
kinds take the **third state** — no de-confliction, no fusion, named gap, safe by construction — until the
re-record shows what extraction actually emits, and the rows that landed are added then (§7 check 5). The
alias machinery is still exercised by the three §2.1 rows, each measured against a string the store had
actually emitted from a document nobody wrote for the purpose. Cost of the withdrawal: nil.

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
**Pakistan Army Air Defence** inventory. This is **carrier #2 of the co-location trap** (§4).

**Rev 3 — the branch wording, and why it is not cosmetic.** Rev 2 wrote that inventory as "Corps of Army Air
Defence". Measured against the shipped `earned_identity.value_normalization`, that string returns
`mapped=False`, which puts `service_branch` — a `normalization_required_attrs` slot — into C7's third state
and makes `unnormalizable_critical_values` fire. The pair is then refused by the **normalisation rail**, and
`colocation_ceiling` is never consulted. A safe outcome, and a **vacuous** one: the trap exists to be held by
the cap, and any other rail intercepting it first is exactly the defect rev 2 was written to remove. Rev 3
states the branch in a form the shipped normaliser folds and adds **no new alias row** to make the prose work
(see §4.3 for the measurement).

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
vocabulary verbatim; site kinds are now in the desk's own prose (rev 3 withdraws the two alias rows rev 2
declared for that prose — §2.2 — so they take the third state until measured). The
terminal §5 "what this report does not establish" lecture is gone; what survives is a **collection-notes
section in imagery idiom** — what is legible in the frames, and what was not collected.

Content: two revetted launch positions 5.6 km apart inside and on the margin of the cantonment, both
occupied on all three passes, six-object fan + octagonal radar at the north, four-object arc + rectangular
radar at the south-east; an unimproved hardstand in Ghotki ~27 km NNE, occupied on all three passes; a Nov
2023 archival frame on which the north is occupied and the other two are empty. The coordinate transcription
error and the three-unit distance drift are carried in place.

**Must produce:**
- `observed-at` occupancy evidence — equipment at a place — materialising **presences**.
- Site classes for the three positions, **or C7's third state** if the emitted strings do not map. §2.2's two
  predicted alias rows are withdrawn in rev 3; the rows that actually land are added after the re-record.
- A **named gap on the unit count at Pano Aqil**, sourced to this document's own collection notes.

**Must refuse:**
- To attribute either cantonment position, or the Ghotki hardstand, to **any named regiment**. No
  `inducted-into` edge runs from anything observed here to 22 or 47 AD Regt, so no derivation can reach one.
- To read the occupied Ghotki hardstand as evidence that either cantonment position was vacated — §2's
  per-pass occupancy for all three positions is the evidence, and the system draws the concurrency itself.
- To resolve `069°80'20"E` as a real coordinate.

**Rev 3 — three adjudications stripped from a document type that only OBSERVES.** An imagery desk records
what is in the frame and what is on the working sheets; it does not rule.

- *"…which is the same distance in a different unit and not a second measurement."* This adjudicates the
  corroboration-counting question — whether 14.6 nm and 17 statute miles are one look or two — which is the
  system's to answer. Replaced with the observation: the 11 Mar working sheet **gives the figure as** 14.6 nm.
  Both renderings are on the record; the arithmetic is the reader's.
- *"A minute value of 80 does not exist; the first form is the one this desk holds."* This resolves the
  malformed coordinate that **this document's own must-refuse says the system must refuse to resolve** — the
  document supplying the very ruling it forbids. Replaced with: both strings reproduced as they appear, the
  second noted as having circulated internally, and "this desk has not reconciled the two." The primary
  `Centre of signature` line stays, because *this is the coordinate we measured* is an observation, not a
  reconciliation.
- *"…including the passes on which the Ghotki hardstand is occupied."* A trailing clause that pre-argues the
  anti-relocation reading. Deleted, not replaced: §2 already states per-pass occupancy at all three
  positions, so the concurrency is fully derivable and the system now has to derive it.

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

**Rev 3 — three adjudications stripped; a spotter records, it does not conclude.** The observational fields
carry the same information and force the same answer, which is the point: the document supplies the evidence,
the system supplies the identity.

- *"Not a second vehicle and not a second sighting"* (the `AD/2025/019` tag). Replaced with what the register
  actually holds: the archive reference submitted with the duplicate entry, `PMV-A-4471`, **is the reference
  already carried at `AD/2025/017`**, and the plate, date and occasion as submitted are the same. Identical
  archive ref is stronger coreference evidence than the verdict was, and it is an observation. The tag also
  drops from `[DUPLICATE — …]` to `[ENTRY NOTE — …]`; "duplicate" is itself the conclusion.
- *"…it refers to this vehicle and there is no vehicle 8417 AD"* (correction log). The second half is an
  assertion about the world this register cannot make. Replaced with an assertion about its own holdings:
  "this list holds no entry and no photograph under that plate." The first half — at full resolution the
  third digit reads 7 — is retained, because what a frame shows at full resolution is exactly what a spotter
  register is for.
- *"Nothing in the archive answers it."* Replaced with the observation underneath it: no frame in the archive
  carries a unit marking on this vehicle, and no captioned material names a formation against it. Same
  refusal, sourced rather than declared.

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

**Rev 3 — three unfoldable branch values fixed, and one adjudication stripped.** n05 wrote `Pakistan Army,
Corps of Army Air Defence` on both regiments and `Pakistan Army, Pakistan Artillery` on 22 Medium Regiment.
None of the three normalises (measured, §4.3), so all three would have taken C7's third state. The knock-on
was worse than the sheet itself: n01 states 22 AD Regt's branch as `Pakistan Army, Air Defence`, which
**does** fold, so leaving n05 unfolded split **one regiment across two branch values** — a fabricated
distinction between two documents that agree. Both AD regiments now read `Pakistan Army, Air Defence`,
matching n01 exactly. 22 Medium Regiment reads `Pakistan Army` in the labelled slot with its arm carried in
the entry name (`22 Medium Regiment (Artillery)`), because no `Pakistan Army, <arm>` string folds except the
air-defence one — the arm belongs in the designation on a nomenclature sheet anyway, and putting it in a
labelled attribute slot would only reintroduce the unfoldable value under a different key.

**Rev 3 — the "cannot be allocated" instruction, stripped.** The 47 AD Regt note ended "Reporting of 'the air
defence regiment at Pano Aqil' is received in staff correspondence without further particulars and **cannot
be allocated between the two on what it carries**." The review judged this arguably in-idiom for a
nomenclature sheet. **Decision: strip it.** The idiom argument is real but loses on what it costs. A
nomenclature sheet's job is to say what the names are; this clause reaches past nomenclature into an
*allocation verdict about incoming reporting* — which is the precise question the trap requires the system to
hold open. Leaving it lets the system SOURCE non-allocability from a document instead of deriving it from the
absence of a designator, the same failure mode as n06's OPEN sentence, only quieter. And removing it costs
nothing: the observation the verdict rested on — such reporting arrives without a regimental number and
without a brigade — is retained verbatim, and it is what a real sheet would carry. Compare n01 §3.7, which is
**kept**: "the compiler has not been able to allocate the battery and carries it here unallocated" is a
register reporting its own holdings, which is why the entry sits in an unallocated section at all. Reporting
your own state is evidence; ruling on someone else's reporting is adjudication.

**(a) The designator collision — kept, and it is the live test.** `22 Air Defence Regiment` (Pakistan Army,
Air Defence), `22 Medium Regiment (Artillery)` (Pakistan Army, Okara) and a PAF
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
with **no** upper bound at all, and Pano Aqil as the worked example — now also noting the unallocated battery
n01 §3.7 carries.

**Rev 3 — §3 no longer states the answer, and this was the worst of the group.** Two sentences are deleted:

- *"We record the number of units at that cantonment as OPEN."* This is **verbatim the epistemic conclusion
  the trap requires the system to derive**. With it in the corpus the system can SOURCE the open count from a
  document rather than derive it from the absence of any allocating evidence, and the centrepiece stops
  testing the co-location cap and starts testing reading comprehension. Nothing replaces it — the open count
  is an output, not an observation, so there is no observational form to substitute.
- *"A prepared position is a place; a fire unit is a formation… One station can also host more than one unit,
  in which case two positions are two units."* This hands over the positions-are-not-units distinction that
  the paper's own §4 "must produce" list requires the SYSTEM to make. A methodological rule stated in the
  source is not the system drawing a distinction; it is the system copying one.

§3 is now **`3. THE PANO AQIL POSITIONS`** and reports only what the programme observed: two of its six
positions at that cantonment, ~5.5 km apart, both occupied on every pass in the most recent collection,
differing in engagement radar planform; two regiments and one unallocated battery recorded there by ORBAT
references; no source attaching any position to a named formation; no frame carrying a unit marking or a
formation caption. §4's result (a floor of three, no upper bound, and the alternatives it cannot rule out
between) is untouched — a paper stating its own count is in-idiom for the type; stating the *analyst's*
verdict about a cantonment it did not count is not.

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
launch positions 5.6 km apart with different radar fits, occupied on every pass; n06 independently counts two
prepared positions at that cantonment, both occupied on every pass of its most recent collection, differing
in radar planform, with no source attaching either to a named formation.

**In rev 3 no document states the conclusion.** Rev 2 had n06 write "we record the number of units at that
cantonment as OPEN", which let the system *source* the open count instead of deriving it (§3.6). That
sentence is gone. Everything above is an observation; the openness of the count is now an output the machine
owes, and if it does not produce it, the trap has caught a real failure rather than a copying failure.

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
| `cross_identity` — namespace | **no** | Both state `service_branch` in a form the shipped normaliser folds to the single canonical `pakistan army`, so `namespace_compatible` holds and the bootstrap's stricter `==` holds too. **Measured** — see the fold table below. |
| C7 normalisation rail (`unnormalizable_critical_values`) | **no**, in rev 3 | Rev 2's n02 wrote `Corps of Army Air Defence`, which the shipped map does **not** fold. `service_branch` is a `normalization_required_attrs` slot, so the third state fired, the pair was refused for unreadability, and the cap was never reached. Both sides now state a **mapped** value. |
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

**The branch fold, measured against the shipped config.** Loaded via
`ResolveConfig.from_bundle(ConfigStore.seed_from('config').snapshot())` and evaluated with
`earned_identity.normalise_value('service_branch', …)`. `fold-only` is `resolve.entities.fold_value`, the
weaker key `Entity.namespace` uses when the C7 normaliser is not in hand.

| Stated value | canonical | mapped | fold-only |
|---|---|---|---|
| `Corps of Army Air Defence` — **rev 2 n02** | `corps of army air defence` | **False** | `corps of army air defence` |
| `Pakistan Army, Corps of Army Air Defence` — **rev 2 n05 ×2** | `pakistan army corps of army air defence` | **False** | `pakistan army corps of army air defence` |
| `Pakistan Army, Pakistan Artillery` — **rev 2 n05** | `pakistan army pakistan artillery` | **False** | `pakistan army pakistan artillery` |
| `Pakistan Army, Air Defence` — **n01, and rev 3 n05 ×2** | `pakistan army` | True | `pakistan army air defence` |
| `Pakistan Army Air Defence` — **rev 3 n02** | `pakistan army` | True | `pakistan army air defence` |
| `Pakistan Army` — **rev 3 n05 (22 Medium)** | `pakistan army` | True | `pakistan army` |
| `Pakistan Air Force` — n05 (22 AD Sqn) | `pakistan air force` | True | `pakistan air force` |
| `Pakistan Army, Artillery` — *considered and rejected* | `pakistan army artillery` | **False** | `pakistan army artillery` |
| `Air Defence` — *considered and rejected* | `air defence` | **False** | `air defence` |

Two sides fold to one value: **n01 §3.7 `Pakistan Army, Air Defence` and n02 `Pakistan Army Air Defence`
both return canonical `pakistan army`, mapped `True`.** `Pakistan Army Air Defence` was chosen over the
equally-valid `Army Air Defence` because it also folds to the **same fold-only key** as n01's form
(`pakistan army air defence`), so the two mentions share a namespace on the un-normalised path as well — the
choice is robust to whether the C7 normaliser is in hand at namespace-derivation time, where `Army Air
Defence` would only be robust with it.

**No alias row was added.** Every value used is already in the shipped `value_normalization` map for
`service_branch`. The two rejected rows above are why n05's 22 Medium Regiment carries its arm in the entry
name rather than in the labelled slot: no `Pakistan Army, <arm>` string folds except the air-defence one, and
inventing a row so our prose could keep its preferred shape is the move this whole pass exists to stop.

**And the pair does reach the fusion line, so the cap has something to do.** Identical normalised names in one
namespace is `TRIGGER_EXACT_NAME`, a **Phase-1 bootstrap** trigger that merges at hardcoded confidence 1.0 and
**bypasses banding entirely**. `fusion_blocked` is the one precondition both phases consult, so with the cap
removed this pair fuses at 1.0 with no band and no queue place. That is the falsifiable claim: **set
`colocation_ceiling` to `confirmed` and the two batteries become one node; leave it at `probable` and they do
not.**

### 4.4 The harm, stated as what it actually is

**No relocation is drawn.** Both mentions are at the same site, so a fused node has one basing and there is no
before/after for the supersede path to order. Rev 1 claimed a fabricated relocation here; that was wrong, and
this is the honest replacement — the undercount the trap is named for.

**This section does not inherit the config comment's claim.** `resolution.yaml`'s note on `colocation_ceiling`
described the harm as a formation over-merge making two sites one unit's before/after, with the supersede path
drawing a relocation and deleting the retired edge's Known Gap. That is a real harm of the cap's *general*
case and it is **conditional on the two mentions being at different sites** — which this trap, by
construction, is not. The comment has been amended to separate the two: the undercount is what always
follows; the fabricated relocation is the extra harm available only across two sites. What this trap produces
is the first list, in full, and none of the second.

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
4. **It propagates into the count answer.** n06 uses Pano Aqil as its worked example and counts two occupied
   prepared positions there, attaching neither to a formation. A fused node makes that cantonment read as one
   unit, against the corpus's own observations, and pushes the fire-unit floor in the direction a reader will
   then quote. In rev 3 n06 no longer *states* that the count is open, so this is the system's own reading of
   the observations being wrong — not a document being contradicted.

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
- ~~`config/places.yaml` — untouched.~~ **SUPERSEDED IN REV 4 — see §0b.** That call was wrong, and it was
  the defect that kept the trap vacuous: every other station in this corpus has a gazetteer row and this one
  did not, so the station could only be recognised by the string it was written in.
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

   **And the shared neighbour must be ONE node, not two names for one place.** If the two Pano Aqil site
   mentions do not themselves fuse — n01 §3.7 writes "Pano Aqil Cantonment, Sukkur District, Sindh", n02
   writes "Pano Aqil Cantonment, Sukkur District" — then the two batteries hold `based-at` edges to two
   *different* objects, and G18 compares them. `_same_place` is the only escape and it is narrow (same id,
   same gazetteer `place_id`, or alias-equivalent normalised names). Failing that, the C1 scope test cannot
   de-conflict either: **`cantonment` is deliberately unmapped** (§2.3), so `normalise_tag` returns
   `(absent_bucket, False)` on both sides, `known_a and known_b` is False, the differing-class escape is
   skipped, and — with the dates overlapping — `_relationship_walls` records a **RAISE**, C7's third state.
   `raise_walls` is a block-merge-and-review set consulted at the **top of the Phase-1 loop**, before
   `bootstrap_trigger` and therefore before `fusion_blocked`, so the pair is intercepted *ahead of the cap*
   and the trap is inert again — a safe outcome that tests the wrong thing. Verify the two site mentions
   resolve to one node; if they do not, the fix is on the data side (make both documents write the station
   identically, or seed the alias), never by mapping `cantonment` to buy a de-confliction.
2. **Which rail actually fires on the trap pair?** Grade the *rail*, not just the outcome. Expected: ceiling
   `probable`, rail `colocation_ceiling`, with a queue place. `name_ceiling` (ceiling `possible`,
   watch-listed, off the queue) is a **safe** outcome but means the trap is inert — the pair shared nothing.
   `cross_identity` means the two mentions were typed or namespaced apart. No record at all means they fused,
   which is the failure §4.4 describes.

   **2a. Is every shared predicate inside `colocation_predicates`?** The same dangerous direction as check 1,
   by a second door. `colocation_only` also returns `None` when
   `shared.issubset(set(earned.colocation_predicates))` is False — "some shared link is NOT a co-location
   link ⇒ real relational evidence" — so **one shared neighbour on an off-list predicate silences the cap
   entirely**, and the pair then falls through to a path with no ceiling on it. Measured against the shipped
   ontology, the unit-reachable predicates NOT on the list are exactly two: **`imported-by`**
   (`contract_import_event → unit`) and **`sustained-by`** (`unit → interceptor_stockpile | techdata_authority`,
   polymorphic object). Neither battery document names a contract or a stockpile, and `imported-by` carries
   `requires_stated_endpoints: [to]`, so this should not fire — but "should not" is what check 1 says too.
   Enumerate the shared-neighbour predicate set for the pair and confirm it is a subset of
   `[based-at, observed-at, instance-of, operated-by, equips, inducted-into]`. If an off-list predicate has
   crept in, the cap is silently gone; the fix is to find out which document put it there, not to widen the
   list — widening it would tell the cap that a shared supply relationship is mere co-location, which is the
   opposite of true.
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
5. **What `site_type` strings does n03 actually emit, and which rows should exist?** (§2.2.) The two
   predicted rows are **withdrawn**, so n03's three positions currently land in the third state — held, no
   de-confliction, no fusion, named gap: safe, and the site classes are inert until measured. Record the
   exact strings the re-record emits, then add a row **only** for a string that is a kind-of-place phrase and
   nothing else. Do not re-add a row keyed to wording we wrote for the purpose without saying so, and do not
   weaken the third state to make the classes appear.
6. **Is `8477 AD` / `8471 AD` ever proposed as a pair?** (§3.4.) The keep-separate is only gradeable if the
   resolver proposes it. If blocking never brings them together, record that plainly — it is not a win.
7. **Confirm 22 AD Regt's garrison basing now has exactly two independent looks** (n01, n05), not three
   (§3.2). Whatever status it reaches is then a real reading of the independence logic.
8. **Sanity-check the `n04` class/grade split** (`named-social` + STANAG C). Deliberate and reasoned in
   `config/sources.yaml`, but the one assignment here a reviewer should re-derive rather than accept.
