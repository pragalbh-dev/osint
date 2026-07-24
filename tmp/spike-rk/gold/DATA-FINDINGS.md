# RK-SPIKE — data findings: what the frozen corpus can and cannot exercise for the identity re-key

Authored by the independent DATA hand, 2026-07-24, on `spike/rk-data`. Companion to `claim-gold.md`,
`sub-oracle.md` and `abstract-shapes.md`.

**Nothing here was fixed.** The corpus, `answer_key.json` and `SCENARIO_MANIFEST.json` are untouched.
Where something looks like an error in frozen data, it is written down and — where material — repeated in
a note to the DATA-C agent under `tmp/conv/`.

Every claim below is grounded in a verifiable check over the frozen corpus. The greps are recorded so they
can be re-run.

---

## 1. Does any document state a formation-at-site basing? **No. The §B6 gap is CONFIRMED.**

This was the plan's flagged coverage gap, and it is real — more comprehensively than the plan assumed.

**Check 1 — numbered-unit designators, all 52 documents.** Searching every document for a numbered
military formation (`<n>(st|nd|rd|th)? <arm>? (Regiment|Battalion|Bn|Squadron|Battery|Brigade)`) returns
**exactly one hit in the whole corpus**: `11 Signal Regiment`, in `cd07_unit_collision.txt` — a British
Army signals unit in an off-subject chaff document, present precisely as a designator-string collision
decoy.

**Check 2 — basing verbs, all 52 documents.** Searching for `based at` / `based in` / `garrisoned at` /
`home garrison` / `stationed at` returns **exactly one hit in the whole corpus**, and it is the same
document: *"11 Signal Regiment is a British Army signals formation currently based at Blandford Camp,
Dorset"*.

So the only stated formation-at-site basing anywhere in the corpus belongs to a British signals unit that
has nothing to do with the subject. **For HQ-9/P and HQ-9B there is not one.**

**What the corpus has instead**, in descending order of closeness:

- `d02` names an organizational recipient with **no designation**: *"was formally inducted into service
  with a Pakistan Army Air Defence (PAAD) unit"* — and the venue is an establishment (the Army Air Defence
  Centre), not an operating position.
- `d19` names a **command** next to an **anonymous battery**: *"the first collection cycle to associate a
  PAF/Army Air Defence Command HQ-9BE ... battery with the location"*. A command is named; the formation is
  not. This is the borderline most likely to be misread as an ORBAT association, because a proper noun sits
  beside the word "battery".
- `cs01` counts formations and assigns them to a **command**, never to a site: *"two operational
  battalions ... assigned to the PAF's Central Air Command"*.
- `d17` states the inference and declines it: *"Battalion or brigade-level C2 integration with wider
  Punjab-based air defense architecture is inferred but not confirmed from imagery alone."*
- `d17b` states the absence outright: *"Site identity ... rests on prior open-source association rather
  than confirmed order-of-battle documentation; no unit markings or signage visible in any pass to date."*

**The answer key agrees, in its own words.** Every `based-at` edge in `answer_key.ground_truth` carries
`"basis": "derived"`, and the Karachi edge's note reads: *"DERIVED edge — no document states a named unit
at a named site."* Two independent routes — a corpus-wide grep and the oracle's own annotation — reach the
same conclusion.

**Consequence for the replumb.** The design's `based-at`-as-formation-citizen has **no positive training
or demo case in the frozen corpus**. Its stated-basing branch can only be exercised on authored data or on
abstract fixtures, and the RK-LAYER acceptance criterion "a *stated* `based-at` binds a formation
directly" cannot be demonstrated on this corpus at all. `abstract-shapes.json` is deliberately honest
about this: no fixture supplies it either, because there is nothing to abstract *from*.

**Recommendation (for RK-DATA, not actioned here).** The §B6 addition should be a crisp numbered-unit
ORBAT document plus one corroborating source — and the corroborating source must **name the same
designator**, because designator continuity is the only non-perishable discriminator in the design's
ladder, and nothing in the corpus currently supplies one.

---

## 2. Is there a document with two same-type instances that must not merge? **Not at formation level. That shape must be authored.**

The corpus has this shape at three layers, and misses it at the one that matters most.

| Layer | Present? | Where | Licensing evidence |
|---|---|---|---|
| **Import event** | Yes, strongly | `d05` — three declarations `KPQA-HC-2020-118834` / `-118835` / `-119011` | Distinct GD **and** waybill numbers, plus the record's own *"(shared, see line 118834)"* cross-reference |
| **Site** | Yes | `d19` — *"the previously tracked Sialkot-area and Pasrur dispersal sites ... **both** remain in a 'last confirmed' state"* | A stated enumeration with explicit cardinality |
| **Design** | Yes | `d04` — HQ-9/P vs HQ-9BE | *"appear to be genuinely separate procurement lines rather than a single system fielded twice"* |
| **Formation** | **No** | — | — |

`d05` is the best over-merge trap in the corpus and worth keeping in any bake-off slice: the three
declarations share a consignee, a shipper cluster, a tariff-code family, a vessel voyage and — for two of
them — a **container number**. Name similarity and shared neighbourhood both argue for merging; only the
identifiers argue against. Merging any two silently halves the import count.

**What is missing is the OOB-undercount trap itself:** two *individuated* same-type formations that a
system could wrongly fuse — canonically, two batteries of the same system at one garrison. The nearest
approach is `d17`, which raises the possibility as an *uncertainty* rather than as two mentions:

> *"Number of fire units co-located at Nur Khan remains uncertain; only one revetment cluster has been
> positively resolved in the current pass set, though the base's perimeter extent ... leaves open the
> possibility of additional dispersed elements not captured within the current image footprints."*

That is excellent material for the *honest-gap* surface ("presence confirmed, formation count unresolved")
and useless as an anti-merge test, because there are no two mentions to keep apart. Three other documents
gesture at extra formations without individuating any either: `d15` (*"a third or additional battery may
have been contracted or delivered"*), `d14` (*unit numbers variously cited as "eight batteries" or "an undisclosed
number of fire units"*), `cs01` (*"a third battalion reportedly in the delivery pipeline"*).

**`cs01` is the shape the corpus does have, and it is a different problem worth naming:** a
**cardinality without individuation**. *"two operational battalions"* is one claim with a quantity, not
two referents. Minting two formation nodes from it invents individuals the source never named; discarding
the number loses the only order-of-battle figure in the slice. This is exactly spine/13 §3a's rule — the
count is a *sourced attribute*, never a function of how many reports merged — and `cs01` is the document
that makes it concrete. It is chaff, and it is load-bearing chaff.

**Recommendation.** The over-merge fixture must be **authored**: two batteries at one site, distinguished
only by a designation, so co-location-merges-into-one-formation is a demonstrable failure and the
designation is what prevents it. Fixture `S3` in `abstract-shapes.json` supplies the *structure* around it
(named command + anonymous section) but deliberately not the two-formation pair, since that pair does not
exist in the corpus to abstract.

---

## 3. Are there two genuinely independent sources on the same instance? **Yes, but thinner than it looks — and the flagship pair is not blind.**

Counting documents that touch each instance is misleading; what matters is whether the corroborations are
*derivative*.

**Rahwali (the flagship confirm).** Five documents mention Rahwali: `d11` and `ce01` (the recycled-parade
image deception — same origin as each other), `d20` (the grade-E supersede spoof), and the genuine pair
`d18` + `d19`. So the confirm rests on **two documents**, not five. And `d19` is **not a blind second
look** — it explicitly reads `d18`'s report:

> *"commercial EO imagery collected 27 March ... **confirms the TEL and battery-command cluster first
> detected on the single-pass collection reported earlier this quarter**"*

The *collections* are genuinely separate (d18 ≈ mid-March single pass; d19 = 27 and 29 March passes plus an
ELINT fix). The *analysis* is not: the second desk knew what the first had found and set out to confirm it.
That is normal tradecraft, and it is also exactly the kind of soft dependence the corroboration ledger's
independence machinery exists to catch. Worth stating out loud rather than counting as two clean signals.

**Inside `d19`, the "second independent signal" is weaker than the answer key's framing suggests.** The
document itself supplies the caveats:

- the ELINT is *"A commercial ELINT aggregator feed (operator not disclosed to subscribers, relayed via a
  third-party maritime/air RF-monitoring service)"* — an unnamed vendor through an unnamed intermediary;
- it releases *"no further geolocation detail ... at this subscription tier"*, so the co-location that
  makes it corroborating is the desk's characterization, not a checkable fix;
- the desk disowns the radar identification: *"treat the HT-233 identification itself as the vendor's
  characterization, not independently re-derived by this desk"*;
- and `d19` self-describes as an aggregator: *"Compiled from open commercial imagery, subscriber ELINT
  relay reporting, and prior digest issues."*

None of that makes the confirm wrong. Discipline-independence (optical + RF) is real and is the strongest
corroboration signal in the corpus. But **it all arrives inside one `source_id`**, so a credibility model
that counts source documents sees one source claiming three signals — and a model that counts the three
signals sees corroboration that no second party ever provided.

**Karachi.** `d07` (multi-pass imagery of equipment at a pad) and `d02` (induction into a named-arm unit at
a Centre) are genuinely independent and genuinely different claims — one is equipment-at-a-place, the other
is a unit induction. They do not corroborate each other; they are the two halves the derived basing edge
joins. `d08`/`cx01` are deceptions and `d09` is the contradiction half. The answer key models this
correctly with its `observed_layer` / `attribution_layer` split.

**Net:** the corpus supports independent corroboration of **equipment presence**. It supports it much less
well for **instance identity**, and not at all for **formation identity** (§1).

---

## 4. Does a unit-level discriminator appear anywhere? **No designation and no serial in the entire corpus.**

**Check 3 — identifier vocabulary, all 52 documents.** Searching for `serial no/number`, `hull number`,
`tail number`, `registration no/number`, `unit code`, `OB code` returns **zero hits**.

The only mentions of unit-level identity anywhere are statements that it is *absent*:

- `d17b`: *"no unit markings or signage visible in any pass to date"* — absent across the entire pass
  history, not just this one;
- `d02`: *"not disclosed, in keeping with the Army's standing practice of not releasing order-of-battle
  details for sensitive air defence assets"* — a stated policy, so this gap will not close from official
  sources;
- `d04`: *"Neither the Pakistan Army nor Air Force public affairs offices responded to requests for comment
  on unit numbers, basing locations, or the precise contractual designations"*;
- `d03`: *"Further details, including squadron designations and precise basing, are expected to emerge
  gradually"*;
- `d16`: *"I'd want at least a serial-number-level or facility-level detail before updating my assessment"*
  — an analyst asking for exactly the discriminator that does not exist.

**This is the most consequential finding for the re-key.** The design's discriminator priority ladder is
*designation > operator+geo > relational > name-as-recall*. On this corpus:

- the **designation** rung has **no data anywhere** — top priority, zero coverage;
- the **operator** rung is present but often **disjunctive or conflicting** (`d19`: *"Pakistan Army/PAF
  joint-use"*, *"PAF/Army Air Defence Command"* — two services joined by a slash; `cs01` assigns HQ-9/P to
  the PAF where `d02`/`d04` assign it to the Army);
- the **geography** rung is perishable by definition, so by the design's own perishable cap it cannot
  confirm a formation on its own;
- which leaves **relational** and **name** carrying formation identity — the two the design most wants to
  demote.

So "formation identity honestly stays unresolved" is not a conservative design choice on this corpus; it
is the *only* honest outcome available. The system should be judged on whether it says so clearly, and the
demo surface should lead with the gap rather than apologise for it. The upside is that this is a genuinely
realistic property of open-source order-of-battle work, and the design note can say so.

**Design-level designators are abundant** (HQ-9/P, HQ-9P, HQ-9B, HQ-9BE, FD-2000, FT-2000, HT-233,
Type 305B/H-200) — which is why the *design* layer resolves and the *instance* layer does not. The corpus's
identity difficulty is entirely on the instance side, and it is a **coverage** problem, not a matching
problem.

**One partial exception, and it is on the commercial side:** `d05` carries real hard identifiers — a tax
number (`NTN 3298761-4`), a registry rename (`SECP CUIN 0087762`), a trusted-trader certificate
(`PK-AEO-0231`), declaration and waybill numbers. So the "shared unique identifier is the fast path to
confirmed identity" mechanism has *exactly one* place in the corpus where it can genuinely fire, and it is
the customs manifest. If that path is to be demonstrated at all, it will be demonstrated on `d05`.

---

## 5. Things that look like errors, or like drift, in the frozen data

**Not fixed. Recorded. The two material ones are also filed for DATA-C.**

### 5a. MATERIAL — `answer_key.ground_truth` has no `trading_org` node and none of `d05`'s three import events

The oracle's 18 nodes contain a single `contract_import_event` (`import_2021`, *"China→Pakistan HQ-9/P
transfer"*, `evidence_date: 2021`). `d05` states **three** distinct declarations dated **November 2020**,
plus three identifier-backed trading orgs (consignee, shipper, forwarder) and a corporate rename. None of
that appears in the ground truth — even though `config/ontology.yaml` documents d05's three bills at length
as the hard-attribute rail, and `md/17` lists d05's demo value as *"relational (not string) resolution
shell → HT-233"*.

This is best read as **hero-trace scoping**, not an error. But it has a direct measurement consequence, and
it is the cleanest argument for the sub-oracle: score a slice containing `d05` against the full oracle and
every correct thing an extractor reads out of the customs manifest counts as noise, while `import_2021`
counts as a miss on a document that never mentions it. **Graph-recall for the bake-off must use the
sub-oracle.** Filed for DATA-C/EVAL.

### 5b. MATERIAL — the flagship `distinct-from` is graded `confirmed` on one hedged grade-C source, and the corpus contains counter-evidence

`answer_key.ground_truth` marks `distinct-from var_hq9p ↔ var_hq9be` as `confirmed` (*"flagship: ~125km
Army vs ~260km PAF"*). The evidence is `d04` alone — `trade_media`, grade C — and the source hedges it:
*"appear to be genuinely separate procurement lines"*. Meanwhile `d19`, at grade **B**, says HQ-9BE is
*"sometimes rendered HQ-9P in Pakistani service literature"* and warns of *"continuing inconsistency
across open sources in how Pakistani service designators map to the PLA domestic HQ-9B baseline versus the
CASIC export HQ-9BE marketing designation"*.

So the corpus contains a grade-B source blurring exactly the designators the oracle confirms as distinct.
A system that surfaces this as a flagged contradiction held for an analyst is behaving *correctly* and
will look like a failure against the key. Flagged, not asserted — this belongs with the existing
answer-key-grounding pass. Filed for DATA-C/EVAL.

### 5c. Three irreconcilable induction dates for one designator, with no document reconciling them

- `cs01`: officials characterised the system **in 2013** as *"already inducted in limited numbers"*;
- `d04` (October 2021): *"Nearly three years after induction was first confirmed by open-source imagery"* →
  ≈2018-19;
- `d02` (14 October 2021): formally inducted **2021-10-14**.

These are plausibly three *different* events — an initial limited delivery, a first imagery confirmation,
and a formal induction ceremony — which would be excellent, realistic messiness. But **no document says
so**, and the oracle carries a single `evidence_date: 2021`. Worth a deliberate decision: either it is
intended layered messiness (in which case the design note should own it) or `d04`'s opening line drifted.
Recorded; no change requested.

### 5d. `d17b`'s location description is internally inconsistent

The subject line reads *"Air Defense Infrastructure, Southern Approaches"* while the site's only name is
*"the old Rawalpindi-area site" near the port road turnoff*. Rawalpindi is in northern Punjab and has no
port road; "port road" is a Karachi feature elsewhere in the corpus (`d08`: *"near the port road, Karachi
side"*; `cx01`: *"near the port road area in Karachi"*).

**This is probably deliberate and correct**, because `d17b` is quoting forum reporting and `d20` shows the
spoof itself conflating *"the old Rawalpindi site"* (post 1) with *"the port road area"* (post 4 — a
retweet of post 1). Inheriting an incoherent description from an incoherent source is realistic.

Either way there is a real consequence: **the geography discriminator for this site is unusable, not merely
coarse**, and must not be averaged into a position. `d17b` states the missing item itself — *"it gives no
coordinates"*. Recorded so it is not "fixed" into coherence by a later pass, which would destroy the
deception beat.

### 5e. Three different range figures for one designator, every one hedged

`d02`: *"well beyond 100 km"* · `d04`: *"in the region of 125 km"* (disowned in the same document as
*"indicative rather than authoritative"*) · `cs01`: *"on the order of 200 km"*.

Almost certainly intended messiness, and useful. The consequence for the re-key is worth stating: on this
corpus **numeric attribute agreement cannot be a merge signal and numeric disagreement cannot be a wall**,
because independent sources disagree about the same object. Any mechanism leaning on attribute agreement
must survive that.

### 5f. Casing and formatting drift is real and inside single documents

`d05` alone writes the shipper country as `CHINA` (twice) and `China` (once), the port five ways
(`PORT MUHAMMAD BIN QASIM (PQ)` / `BIN QASIM` / `Port Qasim` / `QICT PQ` / `CIF PQ`), and the consignee
three ways. This is exactly the value-normalization case `config/resolution.yaml` warns about, and the
corpus supplies it **within one document**, which is the cheapest possible place to exercise a
normalizer. Good news, recorded as such.

### 5g. `cs01` carries the CPMIEC-as-manufacturer conflation, same as `d23`

*"claimed by the manufacturer, China Precision Machinery Import-Export Corporation (CPMIEC)"* — a clean
acronym apposition binding to a role the wider corpus refutes (`d22` argues CPMIEC is an export and
foreign-trade entity, not a design bureau). This is presumably intentional: a second instance of the same
conflation, in a *stale* document rather than a *low-grade* one, so the refutation has to work on a
different axis. Recorded as a feature, and noted in the sub-oracle because a slice containing `cs01` but
not `d22` will carry a claim the full corpus knows to be false.

---

## 6. Two structural gaps in the ontology that the slice makes unavoidable

Not data errors — schema gaps the documents walk straight into. Listed because they change what the data
can exercise. Nineteen claim rows in the slice are marked `UNMODELLED:`; these are the two that recur.

**6a. `d05`'s core structure is unrepresentable.** The document's spine is *event ↔ consignee ↔ shipper*.
`imported-by` runs `contract_import_event → unit` (no unit appears in `d05`) and `exported-by` runs
`contract_import_event → manufacturer` (the shipper is a `trading_org`, by its own name). **There is no
edge between `contract_import_event` and `trading_org` at all.** So the only supply-chain relation the
document *states* has no lane, while the relation it does *not* state (event → unit) is the one the schema
offers. The schema pushes toward asserting the unsourced thing — worth knowing before an extractor is
graded on this document. Ports are the same story: there is no port/facility node type, only `basing_site`
and its `area_of_operations` refinement.

**6b. There is no `operated-by` edge, so operator conflicts are only visible as attributes.** Operator is
the design's second-priority discriminator, and it appears in the corpus as a *relation* as often as an
attribute (`cs01`: *"the Pakistan Air Force's Air Defence Command is believed to operate the HQ-9/P"*;
`d04`: *"the Pakistan Air Force is believed to operate a longer-ranged variant"*). With no such edge, the
Army-vs-PAF conflict in §4 can only fire if operator is captured as an attribute on both sides — and the
same absence means `d04`'s *"There is no confirmed evidence that Pakistan has acquired the FT-2000"*, the
direct refutation of the flagship false-merge trap, has nowhere to go at all.

---

## 7. Sequencing note

Per plan §10, this pass **documents and does not execute**. No corpus file, config file, `answer_key.json`
or `SCENARIO_MANIFEST.json` was modified. The full regeneration needs a user-approved, EVAL-coordinated
`DECISIONS.md` entry with the old oracle archived first; nothing here anticipates that decision.

Two items are filed to `tmp/conv/` for the DATA-C agent (§5a and §5b). The §B6 authoring recommendation
(§1) and the over-merge fixture recommendation (§2) belong to RK-DATA's coverage additions and are stated
here as findings, not as work started.
