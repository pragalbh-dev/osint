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

**S3 is the first stage whose central mechanism has no input in the frozen data at all.** Coreference is off at both
switches, so **not one of the 492 frozen claims carries a coreference annotation of any kind** — no cluster, no
category, no licensing quote. That is not a coverage gap better documents would fix: a cluster is an *extraction
output*, so no source text can supply one, and three of this stage's fixture families (a mis-categorised bind, an
untyped second mention, a phantom member) are *extractor behaviours* that cannot be commanded even by a keyed
re-extract. For those the sandbox is not a convenience, it is the only possible test.

**But the coreference-adjacent *prose* is far richer than the missing annotations suggest**, and that changes the
picture in both directions. The corpus turns out to contain a clean positive anaphor case, a savage ambiguity case
where adjacency favours the wrong antecedent, prefix collisions on a single line, one designation attached to five
national contexts, and — the sharpest finding of this pass — **explicitly stated equivalences whose two surface forms
are dozens of lines apart or in two different fields of one record, so that no single quoted span can contain both.**
That last one means the equivalence gate's both-surface-forms conjunct has a real **false-negative class** in this
corpus: it will correctly withhold, and it will withhold often, on equivalences documents really do assert. The
analyst queue is therefore load-bearing, not a rare fallback.

Second, the structural holes S2 found are unchanged and now bite harder, because S3 is where they were to be paid off.
**One numbered body in 52 documents (an off-subject decoy), one stated basing (the same document), zero serials.** So
the co-location cap, the body-level identifier rungs and the decline path are **fixture-only**, and every gate this
stage adds (G16, G18, G19) is asserted against authored data. That belongs in the disclosures rather than being
discovered by a reviewer.

Third, the new material on expressiveness: **S2 closed five of the six gaps I filed** (there is now a `presence` node
type, an `operated-by` edge, a `customs-party` edge, a third `meta` layer value, and a sourced-`count` attribute
declared as never-derived-from-reports). **Four remain, each blocking an S3 shape** — §3. The sharpest is that the two
attribute roles C6 introduces *specifically so a presence and a place can confirm at all* are declared for **neither of
those two types**.

---

## 1. The coreference finding: nothing to test against, some of it untestable in principle, and one gate with a live false-negative class

### 1a. Both switches are shut, and the frozen claims carry nothing

Verified directly:

- **Producer** — the `coreference:` block in `config/credibility.yaml` is **commented out** in its entirety (its own
  comment says enabling it "costs a SECOND extraction call per document and re-records every frozen bundle").
- **Consumer** — `coref_authoritative_evidence:` in `config/resolution.yaml` is **`[]`**, so every cluster would be
  raise-only even if the producer ran.
- **Data** — searching all of `corpus/**` for the three annotation carriers and for the `coref-same-as` predicate
  returns **zero files**. The frozen claim bundles live at `corpus/scenarios/{hq9p_primary,hq9p_chaff}/claims/*.json`;
  the chaff scenario has no claim bundles at all, so all 492 claims are primary-side, and none mentions coreference.

The ruling's premise is therefore confirmed as data: **testing Tier-0/Tier-1 on real data requires a keyed re-extract**
— a second model call per document, re-recording every frozen bundle, confirmed non-deterministic.

### 1b. Three fixture families can never come from the corpus, however good the corpus gets

Worth separating from ordinary coverage talk, because it changes what the sandbox is *for*:

| Fixture | Why no source text can supply it |
|---|---|
| `F1g` (paraphrased quote), `F1b` (quote under-licenses), `F1c` (quote is an enumeration) | These are properties of a *model's output about* a document, not of the document. Note the producer already drops a cluster whose quote is not found in the text — so `F1g` deliberately tests the consumer against input that bypasses the producer, which is what any fixture-driven test does. |
| `F3c` (second candidate is `unknown`-typed) | "The extractor declined to type this mention" is an extraction outcome. No document can state it. |
| `F1f` (member not attested in the document) | An extractor defect: observable in production, never schedulable. |

### 1c. The cue vocabulary this category is usually built on is largely absent

Across the 27 chaff documents the strings `also known as`, `a.k.a.`, `i.e.`, `referred to as`, `also designated`,
`locally known as` and `variously rendered` occur **zero times** (the one `formerly` is a *role* change, not a name
equivalence). Equivalence in that half of the corpus is carried almost entirely by **parentheticals and slash-forms** —
a four-way equivalence inside one parenthesis; an export designation given in a parenthesis; an acronym and its
expansion in a parenthesis with a casing flip inside it; a research institute given two different numbers in one
parenthesis; a transliteration pair.

**Two consequences.** First, a marker vocabulary implemented as a list of lexical cues has very little purchase on this
data, and the parenthetical branch carries almost all the load — which is exactly the branch `F2c` shows can pass on a
wrong bind. Second, the corpus contains *both* uses of the same punctuation: parentheses that state an equivalence, and
a parenthesis that merely lists four marks of one family. Separating those two is the whole job, and it cannot be done
by looking for the bracket.

### 1d. The both-surface-forms conjunct has a false-negative class in this corpus — the sharpest finding of the pass

The gate requires both members' surface forms inside the licensing span. The frozen corpus contains genuine, explicitly
stated equivalences where that is **structurally impossible**:

- a customs document whose consignee field names a base and whose remarks field, **18 lines later and in a different
  field**, names the airbase at that base — with **no equivalence marker of any kind**. This is a merge an analyst is
  meant to earn (one side of it is a deliberately withheld alias), and the document demands it without stating it.
- a broker note reading *"same as shipper above per broker note dtd …"* — an explicit "same as" sitting roughly **58
  lines from its referent**, joining three name forms through a shared address.
- a forwarder cue that **crosses a field boundary and names a third form on a prior document entirely** ("see also … on
  prior invoice set").
- a social thread where six posts assert sameness in six different wordings with **no repeated identifier at all** — the
  predicate does all the coreference work.

So the conjunct is right and it is not free: it will withhold on real equivalences, and it will do so most often
exactly where the corpus is most structured (the customs documents). The fixture that encodes this (`F1b`) requires
withholding *plus* surfacing the quote so an analyst can settle it in seconds — and this finding is why that second
half is not decoration.

The corpus also contains the **anti-equivalence** shape with a quote: one document names a spelling-variant pair and
explicitly withholds the merge pending a registration check. There is no lane for that today (§3.3).

### 1e. One coreference anchor the machinery cannot reach at all

Three social-media documents carry a **byte-identical image** (same content hash, same shared id) captioned with **four
mutually exclusive locations** and **three mutually exclusive statuses**. The thing that co-refers those three
documents is **the media object, not any text string** — so a text-only, document-local coreference pass cannot reach
it in principle, and a text-only Tier-1 will not either. Worth naming as a known limit rather than leaving it to be
discovered: the corpus's clearest cross-document coreference signal is invisible to the mechanism this stage promotes.

---

## 2. Which of S3's eleven shapes the corpus can exercise

Per-fixture statuses (37 of them, updated after a full read of both scenario halves) are in `s3-shapes.json` /
`s3-shapes.md`. Shape-level summary:

| # | Shape | Corpus? |
|---|---|---|
| 1 | `EXPLICIT_EQUIVALENCE` and its gate failures | **Annotations no; prose yes and consequential.** No cluster exists; three of the seven fixtures are untestable in principle (§1b). But §1c and §1d are live corpus facts that change how the gate should be expected to behave |
| 2 | `NAME_VARIANT` raise-only + the mark-vs-name collision | **Yes, in kind, abundantly.** Several one-line prefix collisions, one where the document then states the distinctness itself; a family with base/suffixed/hyphenation variants across documents; seven surface forms of one forwarder in a single document; one acronym with three different expansions across four documents |
| 3 | `UNAMBIGUOUS_ANAPHOR` and the positive gate | **Yes in prose, at system level.** The cleanest positive in the corpus is one document using a bare definite phrase five times with exactly one named antecedent of that kind. The worst ambiguity case has **four** same-kind antecedents where adjacency favours the wrong one. Not exercisable at body level (one numbered body in 52 documents) |
| 4 | The decline path (attribute and relationship) | **No**, twice over: nothing to decline, and the relationship half has one stated basing in 52 documents |
| 5 | The co-location cap (G16) | **No.** The corpus's largest structural hole, re-confirmed: no two individuated same-kind bodies anywhere |
| 6 | The composite identifier (four directions) | **Design level yes, body level no.** One designation across five national contexts; two design families as perfect two-operator/two-name squares in one line. Plus, for the time rung, a stated redesignation chain the document says is not consistently recorded — an unbounded alias sink |
| 7 | The unnormalizable critical value | **Yes, on both sides of one candidate merge** — see §4a. The highest-value corpus-grounded item in this pass |
| 8 | Geography's three roles | **Presence half: strongest suit. Place half: yes** (five coordinate notations on the primary side; and a one-name-two-positions case, §4f, usable as a shape but not as a clean test). Titled-body-moves half: no (no titles at either end of the relocation) |
| 9 | Same-document contrast, and its absence | **Sourced-count half yes, richly** (including a document stating two incompatible figures for one force in four lines). The enumeration of two *individuated* bodies: absent |
| 10 | Cross-operator / cross-kind non-fusion (G19) | **Yes** — a planted designator collision decoy; two legal entities of one shipping group on one line; a bare locative phrase used for sites in two different countries; person-name chains across three unrelated consignments |
| 11 | The thin mention | **Yes, strongly** — the corpus's thinnest document flips its object's identity twice in one sentence and its class in the last line. The only-one-candidate condition has to be authored |

**The one-line consequence for the stage:** every gate S3 adds — **G16, G18, G19** — is asserted against authored data.
The session card already says fixtures must be abstract; this pass confirms *why*, per gate, and that belongs in the
disclosures.

---

## 3. Expressiveness: what S2 closed, and the four gaps that still block an S3 shape

I filed six gaps for S2. **Five are closed in the shipped ontology** — verified today, not assumed:

- a **`presence`** node type exists (`layer: instance`, `freshness_class: perishable`), with `instance-of` linking it
  to the shared design and `materializes:` declared per-edge and opt-in;
- **`operated-by`** exists (`[unit, presence] → operator`), with an **`operator`** node type as its range;
- **`customs-party`** exists (`contract_import_event → trading_org`, with a stated `party_role`), so the customs spine
  is representable and `trading_org` is no longer stranded — and `imported-by` now carries
  `requires_stated_endpoints: [to]`, closing the fabrication half;
- the `layer` enum grew a third value (**`meta`**) rather than forcing places, sources and operators into a binary;
- `presence.count` is declared **sourced-only**, with the comment stating it is *never* derived from how many reports
  merged.

**Four remain, and each blocks a shape in this file.**

### 3.1 The two attribute roles C6 exists to introduce have no type to attach to

`attribute_roles` in `config/resolution.yaml` declares roles for **`variant`, `unit`, `trading_org`, `component`,
`manufacturer`**. There is **no entry for `presence` and none for `basing_site`.**

C6's whole point is that geography is *perishable* for a body, *constitutive* for a presence and *identifying* for a
place, and that the last two are what let a presence and a place confirm at all. **Both types those two roles are about
are absent from the table**, and the vocabulary is still two-valued. The intent is visible one file away — the ontology
annotates the place's coordinates attribute with "a place's coordinates identify the place" — so this is a declaration
gap rather than a design gap. It is the gap `F8b`, `F8c` and `F8d` all sit on.

### 3.2 The composite identifier has nowhere to be declared

`hard_id_fields` appears **nowhere in `config/**`** — verified by search — while being read by the resolution config
loader and the clusterer. So the mechanism D-13.20 chose to carry its load-bearing call (an identifier is a *composite*
AND-key; a bare designation is not) has no declaration site. Until it exists the `F6a`/`F6b` distinction is
unexpressible, and the fallback is exactly what D-13.20 forbids.

Related: `unit.service_branch` is declared **`role: supporting`** with the comment that it is "a wall in principle, but
the corpus states it unnormalised … Kept soft for now." That is a stated critical discriminator softened *because it
could not be normalised* — `F7a`'s situation, resolved to the **wrong one of the three states** (soft means fusable,
where C7 requires neither-wall-nor-fuse plus a named gap). Not a defect to fix here; §4a is its real-world twin.

### 3.3 There is no contrastive lane, so an enumeration is inexpressible except as a hard veto

The ontology declares `coref-same-as` and `distinct-from`. It declares **no `coref-distinct-from`**. So "this document
syntactically distinguishes these two mentions" has two possible homes: nowhere, or the stated-`distinct-from` rail —
which is **hard, transitive and ungraded**. Routing an enumeration onto that rail is the one recommendation the spike
explicitly rejected, because every order-of-battle list contains an enumeration. `F9a` is the fixture. The same gap
strands the corpus's real **anti-equivalence with a quote** (§1d): a document that names a variant pair and withholds
the merge pending a check has no way to say so except the transitive veto.

### 3.4 `operated-by` exists but no producer emits it, so half of the wall's rule is fixture-only

`operated-by` is declared **without `extractor: true`**, unlike `based-at` and `observed-at`. G18's rule is that a
**stated** `based-at`/`operated-by` conflict at overlapping times hard-walls a merge — and one of those two predicates
can never be stated, because nothing emits it. C11 restated with the declaration in front of me: either the extractor
contract grows the field, or the gate should say in as many words that the `operated-by` arm is fixture-only, and it
goes in the disclosures.

**Also noted, not pursued:** there is still no refinement relation between two designs (identity and exclusion are the
only two design-to-design lanes), which is why `F2b`'s honest outcome has to be "assert neither" — a base mark and a
more specific mark of it have no lane for the relation they actually stand in. There is still no `person` type, and the
corpus has person-name chains across three unrelated consignments that would use one. And **identifier supersession is
itself a coreference relation the data requires**: two documents carry notice-replacement pairs (one notice cancelled
and replaced by another, with *different end times* between them) — one event, two identifiers, no lane.

---

## 4. Things that look wrong, or hazardous, in the frozen data and config

**Not fixed. Recorded.** One item is material and is filed for the data agent (§4g).

**4a. The unnormalizable-operator hazard is live *on both sides of one candidate merge* — and this corrects my first
assessment.** Two frozen documents place the same subject under two service commands whose names differ by one word:
one string is a **substring** of the other, **both are registered aliases of a single entity** in the shipped registry,
and the answer key says only one of the two services is correct. The same two documents also disagree on range, TEL
count, force level and seeker type for that one designation, with no cross-reference between them. So the corpus does
contain a stated critical discriminator that cannot be compared, on both sides of a merge the resolver will consider —
and the shipped config has already conceded it by softening the discriminator (§3.2). Three further hard-failure
abbreviations: two never expanded anywhere in 52 documents, and one that is a single edit from a different country's
acronym, so a normalizer that "corrects" it relocates the entity to the wrong nation.

**4b. `site_type` is still free text used for four different kinds of thing** (established in the S2 pass), and it now
has a **second consumer**: `based-at` carries `instance_key_tag: site_type`, and C1 makes the relationship wall fire
*within one `site_type`*. The same unenumerated free-text field now keys both the supersede instance and the wall. My
S2 finding was that a raw-string key would silently stop the flagship relocation from firing; it now applies to the
wall in the opposite direction too — two basings that ought to conflict will not, if their stated kind strings differ
for no meaningful reason. Already filed as `tmp/conv/S2-DATA-to-DATAC-site-type-vocabulary.md`.

**4c. All 492 frozen claims are `polarity: "positive"`** (re-verified: 492/492). The corpus contains at least one
explicit anti-equivalence and several refutations; none survived into the claim set. Any test of refutation handling
must use fixtures.

**4d. Every `based-at` in the answer key is annotated `"basis": "derived"`**, one noting that no document states a named
body at a named site (re-confirmed). This single fact is behind most of the "not exercisable" rows in §2, and it is not
a corpus defect — it is what honest extraction of these documents produces.

**4e. Doc/code drift, harmless:** `spine/13` writes the instance-layer body type as `fire_unit`; the shipped ontology
has `unit`. Flagged in the S2 pass; still true. *The running code is the fact.*

**4f. One aerodrome identifier is filed at two positions ~1,100 km apart — reported, with the caveat that makes it less
alarming than it first looked.** `cd05_civ_notam` files `OPKC` at `2452N06718E` (≈24.87 N, 67.30 E — Karachi) across
four separate Q-lines. `cd16_pak_civ_notam` files the **same** `OPKC` at `3358N07324E` (≈33.97 N, 73.40 E — the
Islamabad/Rawalpindi area), ~11 km from the `OPIS` fix in the same document. I verified both directly. The wrong
position lands in *the other of the two cities this subject's relocation question turns on*, so a geo-keyed place
resolver reading these would put a Karachi aerodrome in Rawalpindi.

**The caveat, which I checked before filing and which a first pass missed:** `cd16` *is* tagged in the answer key with a
`code_string_noise` corruption class, is marked `off_subject`, and its stated expectation is "right country, zero
materiality → no claim". So it is genuinely ambiguous whether the mismatch is the intended noise or an unnoticed error
— and either way it cannot reach the graph through claims while that expectation holds. **Reported rather than
escalated**, in `tmp/conv/S3-DATA-to-DATAC-notam-position-and-mention-detection.md`. The residual risk is narrow and
worth naming: any pass that reads chaff navigation-warning position fixes as place evidence inherits it.

**4g. The one genuinely material item: OCR splits words mid-token in the fixed-width customs documents.** Entity names
are broken across line boundaries in at least six places across both halves of the corpus (a product description split
mid-word, a compound term split across a hyphen, a letter dropped from the middle of a word, a shipper's name split
across two lines, and the same class in one primary document). **Any mention detector that works line-by-line over
these documents will systematically under-detect exactly the entity names that matter** — and coreference operates on
the mention inventory, so this is a prerequisite for the customs half rather than a cosmetic issue. Related: one
document buries the subject's designator inside an opaque contract reference (`…/AD/HQ9-ph2/…`), which is the only
place in that document where the subject appears at all — a tokenizer that splits on `/` finds it and one that does not
never sees it. Filed with §4f.

**4h. Cross-namespace bridges that are real edges rather than errors, and will be walked.** One bare locative phrase is
used for sites in **two different countries** (a missile-launch rumour in one, the subject's own site in the other) and
appears in both halves of the corpus — the sharpest cross-namespace hazard in the data, and notable because one of the
documents states its own unresolvable identity *about that exact phrase*. Separately: an identical 8-digit tariff code
is shared by a civilian consumer-electronics consignment and a defence consignment, so tariff-code linking is worthless
here by construction; a freight agent is a **genuine** shared node bridging two irrelevant documents (a real edge a
graph-expansion step will walk, not a false merge); and two legal entities of that group appear on one line and must
not merge. None of these is a defect. All of them are inputs G19 and the materiality filter will meet.

**4i. Zero of the 27 chaff documents gives a grid, MGRS or decimal coordinate for any military object.** The only
coordinates on that half are civil-aerodrome notice fixes and one crane. Every chaff military site is a bare toponym,
so site coreference there has **no geometric fallback** — and one chaff post says exactly why that hurts ("which
village exactly, it is a big district"). Contrast the primary half, where a double-digit number of claims carry
resolved WGS84 across five notations.

---

## 5. What the fixtures deliberately do not supply

Stated so absence is not mistaken for oversight.

- **No thresholds, scores, band names used as values, or config keys.** Machine-checked: the only decimal numbers
  anywhere in the fixture file are ground-sample distances inside invented survey documents. Outcomes are prose; the
  implementer picks mechanisms and numbers on general principle and the test author asserts them independently. Two
  outcome words are given behaviourally rather than as labels, on purpose: **withheld** means "not fused, and still in
  the analyst's queue with its reason legible", and **unresolved** means "the answer names what it does not know".
- **No code keys for the coreference annotations.** The fixtures carry a cluster, a category, a verbatim licensing
  quote and the truth about the bind, in neutral terms. Naming the three code fields would hand over the mapping as
  well as the data.
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
- `tmp/conv/S3-DATA-to-DATAC-notam-position-and-mention-detection.md` — the two items worth the data agent's time
  (§4f, reported with its caveat; §4g, the line-splitting one, which is the genuinely material one). The other two
  candidates were already filed (`S2-DATA-to-DATAC-site-type-vocabulary.md` and
  `FOR-DATA-C-sub-oracle-single-source-confirm.md`) and are not duplicated.
- **The disclosure the design note owes, in one sentence:** *the resolution machinery is validated on synthetic
  coreference, and real-world coreference binding accuracy is measured separately, on hand-labelled documents.* Add to
  it §2's last line — that all three gates this stage introduces are asserted against authored data, because the frozen
  corpus contains one numbered body, one stated basing and no coreference annotations at all — and §1e, that the
  corpus's clearest cross-document coreference signal is an image rather than a string, and is invisible to a text-only
  pass.
