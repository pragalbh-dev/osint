# RK-LAYER (S2) — data findings: what the frozen corpus and the shipped ontology can and cannot exercise

Authored by the independent DATA hand for S2, 2026-07-25, on `s2/rk-data`. Companion to `s2-shapes.json`
and `s2-shapes.md`. This hand wrote no production code and no tests.

**Nothing here was fixed.** `corpus/**`, `config/**`, `answer_key.json` and `SCENARIO_MANIFEST.json` are
untouched. Every claim below is grounded in a check over the frozen data or the shipped config; the checks
are recorded so they can be re-run. Where something looks like an error or a hazard in frozen data it is
written down, and the one material item is repeated in a note to the DATA-C agent under `tmp/conv/`.

---

## 0. The one-paragraph version

The spike's headline finding is **confirmed and can be strengthened**: across the 52 scenario documents there
is **one numbered formation** (an off-subject chaff decoy in another country), **one stated "based at"** (the
same document), and **zero serials or unit-level identifiers**. So five of S2's eight shapes — the stated
basing, the low-grade stated basing, both two-candidate-formation shapes, and both one-body-two-sites shapes —
**cannot be exercised on the corpus at all**, and a sixth (the derived basing) can only be exercised with the
designation slot empty. That is why the fixtures are abstract rather than a corpus slice.

The more consequential new finding is **not about coverage, it is about `site_type`** (§2). `site_type` is
free text with no enumeration, and in the frozen data it is used for at least four *different kinds of thing*.
The two ends of the flagship relocation carry entirely unrelated `site_type` strings, and one site carries two
different strings in two documents. **A supersede key tagged on the raw stated `site_type` string would
silently stop the flagship relocation from firing** — while looking deterministic and correct. That is the
single highest-value item in this pass and fixture `F6c` exists for it.

Third, the ontology has **more expressiveness gaps than D12 records** (§3), and each one has the same shape as
D12: a relation a source actually states has no lane, while an adjacent unsourced relation is easy. The
sharpest one is that the **trading-organization node type is named by no edge type at all, in either
direction** — so a correctly typed consignee or shipper can only ever be an isolated node.

---

## 1. Which of the eight shapes the corpus can exercise

The checks behind this table are in §1a–§1d.

| # | Shape | Corpus? |
|---|---|---|
| 1 | Straddling mention (design + instance facts in one mention) | **Yes**, abundantly — but never as a *single* misplaced attribute (`F1b`) |
| 2 | Endpoint materialization → provisional presence | **Yes** — the corpus's dominant shape. The cross-layer holding mirror is also present, including the area-of-responsibility trap |
| 3a | Bare sighting ⇒ presence only | **Yes**, strongly — and one document states the marking absence across its whole pass history |
| 3b | Formation earned + derived basing citing two premises | **Partially** — both premises exist as shapes, but *no numbered body anywhere*, so the designation slot is always empty |
| 3c | **Stated** formation-at-site, good source | **No. Not once.** |
| 3d | Same, **low-grade** source | **Half** — low-grade *relocation* spoofs exist; low-grade *stated basings* do not (the spoofs name equipment, not formations) |
| 4 | The `count` trap | **Partially** — real sourced counts exist, and two reports of one site disagree; but the *coincidence* (report count == a plausible equipment count) is absent, so a naive implementation is never punished |
| 5 | Two candidate formations for one sighting (D2) | **No.** Not at formation level, anywhere |
| 6 | `site_type` de-confliction (C1) | **No** as a one-body-two-sites pair. **Yes** for the absence and — importantly — **yes, live** for the vocabulary drift (§2) |
| 7 | Supersede over a sub-confirmed identity (D1) | **Partially** — every ingredient, but no two co-located same-type formations to fuse, so the chain cannot be shown end to end. Its earned mirror (`F7b`) is **not** exercisable: the corpus relocation has no designation at either end |
| 8 | Inexpressible sourced relations (D12) | **Yes, live** — and worse than recorded (§3) |

### 1a. Numbered formations — one hit in 52 documents, and it is a decoy

Searching every scenario document for a numbered military formation (a number, optional ordinal, up to three
intervening words, then Regiment / Battalion / Bn / Squadron / Battery / Brigade / Company) returns **exactly
one designated formation**: `11 Signal Regiment`, in the chaff document `cd07_unit_collision.txt` — a British
Army signals unit planted as a designator-string collision decoy. Everything else that matches is a **bare
echelon word with no designator** ("a China HQ-9 battery", "the S-400 battery", "six fire units").

One nuance the spike did not state: `corpus/raw/reference/wikipedia_s400.txt` — a real, uncurated seed
reference, *not* one of the 52 scenario documents — does contain real numbered regiments and a real stated
basing. If any pass ever ingests `corpus/raw/reference/**` alongside the scenarios, the corpus's designation
coverage changes character (real foreign units, no relation to the subject). Worth knowing; not a defect.

### 1b. Stated basing — one hit, the same document

`based at` / `based in` / `garrisoned at` / `home garrison` / `stationed at` returns **one** scenario hit:
*"11 Signal Regiment is a British Army signals formation currently based at Blandford Camp, Dorset"*. For the
subject there is not one. Independently, **every `based-at` edge in the answer key is annotated `"basis":
"derived"`**, and one carries the note *"DERIVED edge — no document states a named unit at a named site."*
Two independent routes, same answer.

So the S2 acceptance criterion *"a **stated** `based-at` binds a formation directly"* **cannot be
demonstrated on this corpus**. `F3c` is the only place it can be tested, and it is authored rather than
abstracted, because there is nothing in the corpus to abstract from.

### 1c. Serials and unit-level identifiers — zero

`serial no/number`, `hull number`, `tail number`, `registration no/number`, `unit code`, `OB code`, `vehicle
number` return **zero** military hits across all 52 documents. The single hit is a *company* registration
number in a chaff commercial document. The only mentions of unit-level identity in the corpus are statements
that it is **absent** — including one stating the absence across an entire pass history, and one stating a
non-disclosure *policy*, which means the gap will not close from official sources.

Consequence, unchanged from the spike and worth repeating because S2's fixtures depend on it: the **top rung
of the discriminator ladder has no data**, so on the real corpus formation identity honestly stays
unresolved. Every fixture here that turns on a designation (`F3b`, `F3c`, `F5a`, `F5b`, `F7b`) is therefore
testing a code path the corpus can never reach.

### 1d. The `count` trap — better represented than expected, but the trap itself is absent

Sourced counts **do** exist in the frozen claims, and in a good shape: they live on `SightingEvent` payloads
as structured quantities with `value` / `min` / `max` / `approx` / `unit` / `count_state`. The corpus supplies:

- one site reported twice with **different** figures (four object clusters on one pass, six TEL-pattern
  vehicles on a later one);
- a range whose own author distrusts its upper bound (*"6–8 TELs … confidence in the '8' upper bound remains
  low"*);
- a report that states a count **cannot** be established this pass (cloud obscuration);
- one document stating the same figure twice for one site in two different phrasings.

What is missing is the **coincidence**: nowhere does the number of reports about a site collide with a
plausible equipment count. So a `count = how many reports merged` implementation would produce a visibly
absurd answer on the corpus and be caught by eye — which means the corpus cannot *test* the rule. `F4`
engineers the collision twice over (three count-silent reports, so the naive answer is a plausible three;
then five reports, so the naive answer falls **inside** the only stated range and looks corroborated).

---

## 2. MATERIAL — `site_type` is free text used for four different kinds of thing, and a raw-string supersede key would kill the flagship relocation

This is new, it is verified against the frozen data, and it is directly S2's business (scope item 5 / R1.3 /
C1). It is **not** a data error; it is a property of the data that a naive implementation of the site-kind
key would walk straight into.

**The values, as they actually appear on `basing_site` / `area_of_operations` claims:**

| Kind of thing the value denotes | Example values in the frozen corpus |
|---|---|
| A kind of **place** (what the key needs) | `garrison`, `airfield`, `centre`, `dispersal site`, `deployment site` |
| **Provenance of the mention** | `observed-imagery-site`, `stated_destination` |
| The **equipment** at it | `HQ-9/P site`, `long-range SAM battery position`, `air defense node` |
| An **area class** | `candidate coverage area`, `air defence belt` |
| A **descriptive phrase** | `prepared revetment complex / airfield site`, `Pakistan Army/PAF joint-use facility` |

There is **no enumeration anywhere** — not in `config/ontology.yaml` (the attribute is declared as a bare
entry), not in `config/resolution.yaml`, and not in code. The most common single value in the corpus,
`observed-imagery-site`, is stamped by the imagery ingest path and denotes *how we learned about the site*,
not what kind of place it is.

**The three consequences, in increasing severity:**

1. **The two ends of the flagship relocation are in different buckets.** The origin carries
   `prepared revetment complex / airfield site`; the destination carries `airfield` in one document and
   `Pakistan Army/PAF joint-use facility` in another. Tag the supersede instance key on the raw stated string
   and the before-edge and after-edge no longer share a key, so the relocation **is never seen as one
   instance and never fires**. The failure is silent, and it looks like correct de-confliction.
2. **One site is two buckets.** The destination alone has two different `site_type` strings from two
   documents, so even absent any relocation, the same site does not key stably.
3. **Present-and-absent within one document.** One site name appears three times in a single document as
   three separate `basing_site` entity claims — `site_type` present on one, absent on two. Since attribute
   collection is first-claim-wins, **whether the key is even defined depends on claim ordering**. (The
   three-claims-for-one-site fragmentation is F8/S3's business, not S2's; the ordering dependence of the key
   is S2's.)

**What this does not say.** It does not say the key should not be tagged by site kind — R1.3's reasoning
stands. It says the tag must be on a **normalized class**, that the mapping must be editable data rather than
literals in code (the vocabulary is open-ended: every publisher adds to it), and that an unmappable or absent
value must fall to the safe side rather than de-conflicting on an unrecognised string. `F6a` / `F6b` / `F6c`
are the three directions this has to satisfy at once, and they are mutually constraining: **a rule that reads
the stated string literally passes `F6a` and fails the other two silently.**

Filed for DATA-C as `tmp/conv/S2-DATA-to-DATAC-site-type-vocabulary.md`, because it also constrains the
RK-DATA coverage additions: a §B6 ORBAT document that states a site kind in yet another free-text phrasing
adds coverage and no testability.

---

## 3. Ontology expressiveness gaps that block a shape from being expressible at all

D12 is one case. There are **six**, and every one has D12's shape — *a relation a source states has no lane,
while an adjacent relation no source states is easy*. Listed in order of how badly each blocks an S2 shape.
S2 owns `config/ontology.yaml`, so these are its calls to make; several are already in its scope list.

### 3.1 `trading_org` is named by **no edge type at all** — stronger than D12 as recorded

Machine-checked over `config/ontology.yaml`: of the 13 node types, five are named by no `from`/`to` in any
edge type. Three of those are fine (`source`, `indicator`, `known_gap` attach structurally), and
`area_of_operations` inherits its lanes by refining `basing_site`. **`trading_org` is genuinely stranded.**

So D12's *"no edge connects `contract_import_event` to `trading_org`"* is the visible half. The full statement
is that a correctly typed consignee, shipper or forwarder **can only ever exist as an isolated node**, in any
direction, with any counterparty. Meanwhile `imported-by` (`contract_import_event → unit`) is easy and no
customs document states a unit, and `exported-by` (`contract_import_event → manufacturer`) is easy and the
shipper is a trading org by its own registered name. The pressure toward relabelling a shipper as a
manufacturer, or minting a recipient unit, is structural. `F8a`.

### 3.2 `operated-by` does not exist, and neither does any carrier for a stated non-operation

Already D7 / S2 scope item 5, restated with the data behind it. Operator is the ladder's second rung, and the
corpus states it as a **relation** at least as often as an attribute (*"the PAF's Air Defence Command is
believed to operate the HQ-9/P"*, *"the Pakistan Air Force is believed to operate a longer-ranged variant"*).
With no relation, two sources stating different operators for one design produce two attribute values on two
nodes that may not even be the same node, and never meet as a conflict.

The sharper half: **all 492 claims in the frozen corpus have `polarity: "positive"`.** The claim schema has a
polarity field and nothing negative was ever recorded — so *"there is no confirmed evidence that Pakistan has
acquired the FT-2000"*, which is the direct refutation of the flagship false-merge trap, went nowhere. A
stated refutation is the strongest available anti-identity evidence and it currently has neither a lane nor a
precedent. `F8b`.

### 3.3 There is no node type for the presence citizen, and `observed-at`'s subject end is design-typed

`observed-at` is declared `[variant, component] → basing_site`. **Both subject types are design-layer types.**
So the instance-layer edge that §5.3 says must materialize a provisional presence has, today, **no
instance-layer node type to materialize into** — the instance layer's only citizens in the ontology are
`unit` (the formation), `interceptor_stockpile` and arguably `contract_import_event`.

This is the load-bearing consequence of S2's own scope item 3, and it is worth stating plainly because the
plan describes the presence as a *citizen* rather than as a *type*: whatever mechanism materializes it, the
endpoint-layer rule ("endpoint layers fall out of the endpoint types") cannot be satisfied by the current
declarations, because the declared endpoint type is design-layer. `F2a`.

### 3.4 No node type declares a numeric equipment `count`, so the corpus's sourced figures have no destination

Verified: `quantity` and `magazine_depth` are stated on **zero** corpus claims. `unit.count_state` is
non-numeric (its corpus values are `fielded`, `estimated`, `complete`, `sufficient numbers`).
`contract_import_event.quantity` is the only numeric quantity slot and it is scoped to an import event.

Meanwhile the *documents* state equipment counts repeatedly and the *claims* carry them — as structured
quantities on `SightingEvent` payloads, i.e. in the event layer, not as an attribute of any node type. So the
sourced count that D-13.13 wants on the presence exists in the evidence and has nowhere to land in the
knowledge layer. This is the anti-fabrication hazard in mirror image: **a sourced figure with no lane is as
dangerous as an unsourced relation with one**, because the figure gets dropped and something else fills the
slot. `F4`.

### 3.5 `layer: design | instance` cannot classify five of the 13 node types

Scope item 1 requires a `layer` on every node type. Five types are §3's *"other kinds — places, sources,
events — are their own kinds"*: `source`, `indicator`, `known_gap`, `basing_site`, `area_of_operations`. A
two-valued enum forces a false choice on each, and the choice is not cosmetic: §5.4 says **endpoint layers
fall out of endpoint types**, so whatever `basing_site` is tagged determines whether `based-at`
(`unit → basing_site`) reads as an instance-layer edge or as a cross-layer one — which is exactly the test
that decides whether an endpoint materializes (`F2a`) or mints nothing (`F2b`). Either the enum needs a third
value, or places need a stated convention. Flagged, not decided — it is S2's call.

### 3.6 No refinement relation between two designs

`variant-of` was deliberately dropped and family is carried as an attribute, so there is **no lane for
"design B is a refinement/export rendering of design A."** The only available design-to-design relations are
identity (`same-as`) and exclusion (`distinct-from`), which are the two answers a refinement is *not*. This
bites in the corpus: a grade-B source says one designator is *"sometimes rendered"* as another while the
answer key marks the pair `confirmed distinct-from`, and the honest outcome — an unresolved refinement
relation held for an analyst — is unrepresentable. Not an S2 shape, but the same hazard class, and it is why
`F1b` keeps the export designation on the design layer rather than treating it as a second design.

Also noted and not pursued: no `person` node type (the corpus has clean role-holder appositions with nothing
to bind to), and no port/terminal/facility type (a discharge point has to be forced into `basing_site`).

---

## 4. Things that look like errors, or like drift, in the frozen data

**Not fixed. Recorded.** The one material item is §2, filed for DATA-C. Everything below is either benign
drift or an item the spike already filed; I re-checked each rather than inheriting it.

**4a. Doc/code drift on the formation type name.** `spine/13` writes the instance-layer body type as
`fire_unit` (§3, §5.1, §5.3). The shipped ontology has `unit`. Harmless, but S2 is adding `layer` keys to
every node type against a doc that names a type that does not exist — worth a one-line correction while the
file is open. *The running code is the fact.*

**4b. `site_type` semantics (see §2).** Not an error; a hazard. Two sub-items are closest to being errors:
one site's `site_type` is a *design* designation (`HQ-9/P site`) and another's is a *provenance* descriptor
(`stated_destination`). Both are category errors relative to what the C1 key needs, and both are defensible
as faithful extraction of what the document said.

**4c. One site name, three separate entity claims, one document, `site_type` on only one of them.** Recorded
in §2.3. This is per-mention fragmentation (F8, owned by S3) intersecting with S2's key. Not a corpus defect
— it is what the extractor did with a document that names the same site three times.

**4d. All 492 claims are `polarity: "positive"`.** Recorded in §3.2. Either the corpus contains no negative
assertions (it does — at least three documents contain explicit refutations) or negatives were dropped at
extraction. Since the corpus is frozen this is a *known limitation of the frozen claim set*, not a fix
request, but it means any test of refutation handling must use fixtures.

**4e. Re-confirmed from the spike, unchanged, no action:** the answer key carries no trading-organization node
and none of the customs document's three declarations (best read as hero-trace scoping, already filed); the
flagship `distinct-from` is graded confirmed on one hedged grade-C source while a grade-B source blurs the
same designators (already filed); three irreconcilable induction dates; three hedged range figures for one
designator; casing/format drift inside a single document. I verified each still holds and add nothing.

---

## 5. What the fixtures deliberately do not supply

Stated so a reader does not mistake absence for oversight.

- **No thresholds, scores, band names used as values, or config keys.** Outcomes are prose. The implementer
  picks mechanisms and numbers on general principle; the test author asserts them independently. Giving
  numbers would collapse the three-hands separation, which is the whole point of this hand existing.
- **No claim-JSON, no node ids, no edge names in the fixture payloads.** Fixtures describe what a *source
  states* and what the *extractor emitted*, in prose and in a per-fact routing table. Handing over a
  ready-made claim shape would be handing over the implementation.
- **No corpus content.** Every entity is invented, in a fictional regional-infrastructure domain continuous
  with the earlier `gold/abstract-shapes.json` set so both can be read together.
- **Nothing about `rebuild()`'s purity beyond the fixture's own requirement.** `F3b` is built to make the
  derived-basing branch actually execute (an observation premise plus an organizational premise in two
  documents), which is what G17 needs to be non-vacuous. Whether the gate is an input-driven test or a static
  call-graph scan is not this hand's call.

---

## 6. One-line summary per deliverable

- `s2-shapes.json` / `s2-shapes.md` — 18 fixtures across the 8 shapes, 27 invented documents, 71
  tempting-but-wrong outcomes, 33 negative-gold spans.
- `S2-DATA-FINDINGS.md` — this file.
- `tmp/conv/S2-DATA-to-DATAC-site-type-vocabulary.md` — the one material item for the data agent.
