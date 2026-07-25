# RK-COREF (S3) — data findings: what the frozen corpus can and cannot exercise, and what is inexpressible

Authored by the independent DATA hand for S3, 2026-07-25, on `s3/rk-data`. Companion to `s3-shapes.json` and
`s3-shapes.md`. This hand wrote no production code and no tests, and did not read the implementer's or the test
author's branches.

**Nothing here was fixed.** `corpus/**`, `config/**`, `answer_key.json` and `SCENARIO_MANIFEST.json` are untouched.
Every claim below is grounded in a check over the frozen data or the shipped config; where something looks wrong it is
written down, not corrected. Continuous with `gold/DATA-FINDINGS.md` (spike) and `s2-fixtures/S2-DATA-FINDINGS.md`
(S2) — where those already established a fact I re-checked it rather than inheriting it, and I say so.

---

## 0. The one-paragraph version

**S3 is the first stage whose central mechanism has *no* input in the frozen data at all.** Coreference is off at both
switches, so **not one of the 492 frozen claims carries a coreference annotation of any kind** — no cluster, no
category, no licensing quote. That is not a coverage gap that better documents would fix: a cluster is an *extraction
output*, so no amount of source text can supply one, and three of this stage's fixture families (the mis-categorised
bind, the untyped second mention, the phantom member) are *extractor behaviours* that cannot be commanded even by a
keyed re-extract. The sandbox is therefore not a convenience; for those cases it is the only possible test.

Second, the structural holes S2 found are unchanged and now bite harder, because S3 is where they were supposed to be
paid off. **One numbered body in 52 documents (an off-subject decoy), one stated basing (the same document), zero
serials.** So the co-location cap, the composite-identifier rungs, the relationship wall and the decline path are
**all fixture-only** — every gate this stage adds (G16, G18, G19) is asserted against authored data, and that should be
stated out loud rather than discovered by a reviewer.

Third, and this is the new material: **S2 closed five of the six expressiveness gaps I filed** (there is now a
`presence` node type, an `operated-by` edge, a `customs-party` edge, a third `meta` layer value, and a sourced-`count`
attribute declared as never-derived-from-reports). **Four remain, and each blocks an S3 shape** — §3. The sharpest is
that the two attribute roles C6 introduces *specifically so a presence and a place can confirm at all* are declared for
**neither of those two types**: the role table covers five design-side types and has no entry for `presence` or for
`basing_site`. The rung the design calls missing is missing in the config too.

---

## 1. The coreference finding: there is nothing to test against, and some of it is untestable in principle

### 1a. Both switches are shut, and the frozen claims carry nothing

Verified directly:

- **Producer** — the `coreference:` block in `config/credibility.yaml` is **commented out** in its entirety (its own
  comment says enabling it "costs a SECOND extraction call per document and re-records every frozen bundle").
- **Consumer** — `coref_authoritative_evidence:` in `config/resolution.yaml` is **`[]`**, i.e. every cluster would be
  raise-only even if the producer ran.
- **Data** — searching the whole of `corpus/**` for the three annotation carriers (a cluster id, an evidence category,
  a quote on a coreference predicate) and for the `coref-same-as` predicate itself returns **zero files**. The frozen
  claim bundles live at `corpus/scenarios/{hq9p_primary,hq9p_chaff}/claims/*.json`; none of them mentions coreference.

So the premise of the ruling is confirmed as data, not as inference: **testing Tier-0/Tier-1 on real data requires a
keyed re-extract**, which is a second model call per document, re-records every frozen bundle, and is confirmed
non-deterministic.

### 1b. Three of the fixture families can never come from the corpus, however good the corpus gets

This is worth separating from ordinary coverage talk, because it changes what the sandbox is *for*:

| Fixture | Why no source text can supply it |
|---|---|
| `F1g` (quote is a paraphrase), `F1b` (quote under-licenses), `F1c` (quote is an enumeration) | These are properties of a *model's output about* a document, not of the document. Note also the producer already drops a cluster whose quote is not found in the text — so `F1g` is deliberately testing the consumer against input that bypasses the producer, which is exactly what a fixture-driven test does. |
| `F3c` (second candidate is `unknown`-typed) | "The extractor declined to type this mention" is an extraction outcome. No document can state it. |
| `F1f` (member not attested in the document) | An extractor defect: observable in production, never schedulable. |

For everything else the honest position is that the corpus supplies the *raw shape* and never the *annotation*.

### 1c. One live hazard the raw text does carry

The corpus contains a textbook `Full Name (SHORT)` apposition — and that particular apposition is a **deliberate demo
beat an analyst is meant to earn**. It is exactly what an equivalence bind catches, so switching the producer on with
`EXPLICIT_EQUIVALENCE` authoritative would auto-merge it and delete the beat. This is already recorded in the INGEST
handoff and in the spike's decisions (which overruled preserving the beat as a *design* input, and instead put the fix
on the data pass: split the two designations across two documents so the identity becomes earned rather than read).
**I am not touching it** — flagging only that the beat and the policy still collide in the frozen data as it stands.

---

## 2. Which of S3's eleven shapes the corpus can exercise

Per-fixture statuses (37 of them) are in `s3-shapes.json` / `s3-shapes.md`; this is the shape-level summary.

| # | Shape | Corpus? |
|---|---|---|
| 1 | `EXPLICIT_EQUIVALENCE` and its three gate failures | **No** — no annotations exist; and three of the seven are untestable in principle (§1b). The raw apposition prose exists, and is a demo beat (§1c) |
| 2 | `NAME_VARIANT` raise-only + the mark-vs-name collision | **Partially, and richly** — the mark-vs-name collision is the corpus's own central designator ambiguity, and the shipped containment knob states the doctrine in exactly those terms. The *bind* over it does not exist |
| 3 | `UNAMBIGUOUS_ANAPHOR` and the positive gate | **No.** Anaphoric prose is abundant; the gate reads a mention inventory that only exists once the producer runs. The two-same-kind-candidates case additionally cannot occur at body level — there is one numbered body in the whole corpus |
| 4 | The decline path (attribute and relationship) | **No**, twice over: nothing to decline, and the relationship half has one stated basing in 52 documents |
| 5 | The co-location cap (G16) | **No.** The corpus's largest structural hole, re-confirmed: no two individuated same-kind bodies anywhere; the nearest approach is a cardinality without individuation |
| 6 | The composite identifier (four directions) | **Partially at design level** (one designation, two operators, two countries — real). **Not at body level**: the top two rungs of the ladder have zero data |
| 7 | The unnormalizable critical value | **Yes, and live in the shipped config** — see §4a. This is the highest-value corpus-grounded item in this pass |
| 8 | Geography's three roles | **Split**: the presence half is the corpus's strongest suit; the titled-body-moves half cannot be built (no titles at either end of the relocation); the coordinate half is likely but I did not re-verify notations |
| 9 | Same-document contrast, and its absence | **Partially** — sourced order-of-battle figures are real and now have a declared destination; the enumeration of two *individuated* bodies is absent |
| 10 | Cross-operator / cross-kind non-fusion (G19) | **In kind** — one designator-string collision decoy is planted for exactly this. The alias-route hole came from code review, not from data |
| 11 | The thin mention | **Partially** — thin mentions and, better, *stated absences* of identity are real; the only-one-candidate condition that makes the fallacy irresistible is not |

**The one-line consequence for the stage:** every gate S3 adds — **G16, G18, G19** — is asserted against authored data.
The session card already says fixtures must be abstract; this pass confirms *why*, per gate, and it belongs in the
disclosures rather than in a footnote.

---

## 3. Expressiveness: what S2 closed, and the four gaps that still block an S3 shape

I filed six gaps for S2. **Five are closed in the shipped ontology** — verified today, not assumed:

- a **`presence`** node type now exists (`layer: instance`, `freshness_class: perishable`), with `instance-of` linking
  it back to the shared design and `materializes:` declared per-edge and opt-in;
- **`operated-by`** exists (`[unit, presence] → operator`), and an **`operator`** node type exists to be its range;
- **`customs-party`** exists (`contract_import_event → trading_org`, with a stated `party_role`), so the customs spine
  is representable and `trading_org` is no longer stranded — and `imported-by` now carries
  `requires_stated_endpoints: [to]`, which closes the fabrication half as well;
- the `layer` enum grew a third value (**`meta`**) rather than forcing places, sources and operators into a false
  binary;
- `presence.count` is declared **sourced-only**, with the comment stating it is *never* derived from how many reports
  merged — so the sourced figure S2 found homeless now has a destination.

That is a real improvement and it changes what S3 has to worry about. **Four gaps remain, and each one blocks a shape
in this file.**

### 3.1 The two attribute roles C6 exists to introduce have no type to attach to

`attribute_roles` in `config/resolution.yaml` declares roles for **`variant`, `unit`, `trading_org`, `component`,
`manufacturer`** — five design-side or body-side types. There is **no entry for `presence` and no entry for
`basing_site`.**

C6's whole point is that geography is *perishable* for a body, *constitutive* for a presence and *identifying* for a
place, and that the last two are "what lets a presence confirm at all" and "what lets a place confirm". **Both of the
types those two roles are about are absent from the table**, and the vocabulary is still the two-valued `perishable:
true|false`. So today the declaration cannot be written at all, in either of the two cases that matter. The intent is
visible one file away — the ontology annotates the place's coordinates attribute with "a place's coordinates identify
the place" — which makes this a *declaration* gap rather than a design gap, but it is the gap that `F8b`, `F8c` and
`F8d` all sit on.

### 3.2 The composite identifier has nowhere to be declared

`hard_id_fields` appears **nowhere in `config/**`** — verified by search — while being read by the resolution config
loader and the clusterer. So the mechanism D-13.20 chose to carry its load-bearing call (an identifier is a *composite*
AND-key; a bare designation is not an identifier) has no declaration site in the shipped config. Until it exists, the
`F6a`/`F6b` distinction — shared title earns nothing, operator-plus-title earns a confirm — is unexpressible, and the
fallback is the very thing D-13.20 forbids: a bare designation behaving like an identifier.

Related and worth stating beside it: `unit.service_branch` is currently declared **`role: supporting`** with the
comment that it is "a wall in principle, but the corpus states it unnormalised … Kept soft for now." That is a *stated
critical discriminator being softened because it could not be normalised* — which is `F7a`'s situation, and the
resolution taken is the **wrong one of the three states**: soft means fusable, where C7 requires neither-wall-nor-fuse
plus a named gap. Not a defect to fix here; the fixture is `F7a` and this is its real-world twin.

### 3.3 There is no contrastive lane, so a document's enumeration is inexpressible except as a hard veto

The ontology declares `coref-same-as` and it declares `distinct-from`. It declares **no `coref-distinct-from`**. So
"this document syntactically distinguishes these two mentions" has exactly two possible homes today: nowhere, or the
stated-`distinct-from` rail — which is **hard, transitive and ungraded**. Routing an enumeration onto that rail is the
one recommendation the spike explicitly rejected, because *every* order-of-battle list contains an enumeration and a
transitive veto built from them shatters legitimate identities. `F9a` is the fixture; the missing lane is why the
fixture's third tempting-but-wrong outcome is not hypothetical.

### 3.4 `operated-by` exists but no producer emits it, so half of the wall's rule is fixture-only

`operated-by` is declared **without `extractor: true`**, unlike `based-at` and `observed-at`. G18's rule is that a
**stated** `based-at`/`operated-by` conflict at overlapping times hard-walls a merge — and one of those two predicates
can never be stated by any document, because nothing emits it. This is C11 restated with the declaration in front of
me: either the extractor contract grows the field, or the gate should say in as many words that the `operated-by` arm
is fixture-only, and it goes in the disclosures. (The operator *attribute* is a separate carrier and does exist; the
gate is written about the relation.)

**Also noted, not pursued:** there is still no refinement relation between two designs (identity and exclusion are the
only two design-to-design lanes), which is why `F2b`'s honest outcome has to be "assert neither" — a base mark and a
more specific mark of it have no lane for the relation they actually stand in. And there is still no `person` type,
which the corpus's role-holder appositions would use.

---

## 4. Things that look wrong, or hazardous, in the frozen data and config

**Not fixed. Recorded.** Nothing here is material enough to file for the DATA-C agent beyond what is already filed —
see §6.

**4a. The unnormalised-operator hazard is live and has already been conceded in config.** The shipped role declaration
softens the body's branch discriminator *because* the corpus states it in three different forms. So the corpus really
does contain a stated critical discriminator that cannot be compared — `F7a`'s exact shape — and the workaround in
place is to make it fusable rather than to make it neither-fusable-nor-walling. S3 owns this declaration, so it is
S3's call; I am flagging that the config comment is the best available evidence that the shape is real.

**4b. `site_type` is still free text used for four different kinds of thing** (established and verified in the S2
pass), and it now has a **second consumer**: `based-at` carries `instance_key_tag: site_type`, and C1 makes the
relationship wall fire *within one `site_type`*. So the same unenumerated free-text field now keys both the supersede
instance and the wall. My S2 finding was that a raw-string key would silently stop the flagship relocation from firing;
that finding now applies to the wall as well, and in the opposite direction — two basings that ought to conflict will
not, if their stated kind strings differ for no meaningful reason. `F4b` and `F4c` are the pair that pin this down.
Already filed for DATA-C as `tmp/conv/S2-DATA-to-DATAC-site-type-vocabulary.md`; no new note needed.

**4c. All 492 frozen claims are `polarity: "positive"`** (re-confirmed from the S2 pass). A stated refutation is the
strongest available anti-identity evidence and the frozen claim set contains none, though at least three documents
state one. Any test of refutation handling must use fixtures. Unchanged, and unchangeable while the corpus is frozen.

**4d. Every `based-at` in the answer key is annotated `"basis": "derived"`**, one with a note saying no document states
a named body at a named site (re-confirmed). This is the single fact behind the largest cluster of "not exercisable"
rows in §2, and it is not a corpus defect — it is what honest extraction of these documents produces.

**4e. Doc/code drift, harmless but worth a one-line fix while the file is open:** `spine/13` writes the instance-layer
body type as `fire_unit`; the shipped ontology has `unit`. Flagged in the S2 pass; still true. *The running code is the
fact.*

**4f. One thing I could not settle and would not guess at.** I did not re-verify the coordinate notations per document,
so `F8c`'s two-notations-one-point pair is authored rather than abstracted, and `F8d`'s one-name-two-points trap is
**probably absent** from the corpus — and if such a pair does exist, it would most likely be read as a data error
rather than as the identity trap it is. Worth a targeted check by whoever wires place resolution.

---

## 5. What the fixtures deliberately do not supply

Stated so absence is not mistaken for oversight.

- **No thresholds, scores, band names used as values, or config keys.** Machine-checked: the only decimal numbers
  anywhere in the fixture file are ground-sample distances inside invented survey documents. Outcomes are prose; the
  implementer picks mechanisms and numbers on general principle and the test author asserts them independently. Two
  outcome words are given behaviourally rather than as labels, on purpose: **withheld** means "not fused, and still in
  the analyst's queue with its reason legible", and **unresolved** means "the answer names what it does not know".
- **No code keys for the coreference annotations.** The fixtures carry a cluster, a category, a verbatim licensing
  quote and the truth about the bind, in neutral terms. The three fields those correspond to are code facts the
  implementer already has; naming them here would hand over the mapping as well as the data.
- **No claim JSON, no node ids, no edge names.** Fixtures describe what a *source states* and what the *extractor
  emitted*, in prose and in a per-mention inventory.
- **No corpus content.** Every entity is invented, in the same fictional regional-infrastructure domain as the spike's
  `gold/abstract-shapes.json` and `s2-fixtures/s2-shapes.json`, so all three read together.
- **One deliberate violation of this file's own invariant**, flagged in the data: `F1g`'s licensing quote is *not*
  verbatim in its document, because that is the fixture. A checker must honour the flag.

---

## 6. Deliverables, and the disclosure this stage owes

- `s3-shapes.json` / `s3-shapes.md` — **11 shapes, 37 fixtures, 50 invented documents, 21 hand-authored coreference
  clusters (7 sound; 14 defective across four defect kinds — over-bound, under-bound, quote-does-not-license,
  unlicensed-and-mis-categorised), 155 tempting-but-wrong outcomes, 55 negative-gold spans.** Every licensing quote is
  machine-checked verbatim against its document, with the one flagged exception.
- `S3-DATA-FINDINGS.md` — this file.
- **No note filed for the DATA-C agent.** The two material items I would have raised are already filed
  (`S2-DATA-to-DATAC-site-type-vocabulary.md`, and `FOR-DATA-C-sub-oracle-single-source-confirm.md`), and §4b is a
  second consumer of an item already in the first of those rather than a new observation. Everything else in §4 is
  either unchangeable while the corpus is frozen or belongs to S3's own config.
- **The disclosure the design note owes, in one sentence:** *the resolution machinery is validated on synthetic
  coreference, and real-world coreference binding accuracy is measured separately, on hand-labelled documents.* Add to
  it the finding in §2's last line — that all three gates this stage introduces are asserted against authored data,
  because the frozen corpus contains one numbered body, one stated basing and no coreference annotations at all.
