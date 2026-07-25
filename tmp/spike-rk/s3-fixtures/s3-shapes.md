# RK-COREF (S3) - the coref-baked synthetic sandbox, and S3's other hard shapes

> **SYNTHETIC SANDBOX - HAND-AUTHORED COREFERENCE. Every entity, place, organisation, designation, document and source in this file is invented. Nothing here is corpus content, nothing here may enter the frozen corpus, and nothing here may be scored in any recall metric measured against the answer key. Most importantly: the coreference annotations in this file were written by hand, so this file is a FIXTURE FOR THE RESOLUTION MACHINERY and is NEVER evidence that coreference extraction works. 'The sandbox passes' and 'the extractor binds correctly' are two different claims and only the second one is what the mission rests on.**

Authored by the independent DATA hand for S3 on `s3/rk-data`, 2026-07-25. Companion to `s3-shapes.json` (the machine-readable form, identical content) and `S3-DATA-FINDINGS.md` (what the frozen corpus can and cannot exercise). This hand wrote no production code and no tests.

## The boundary that must not blur

| | |
|---|---|
| **what this file CAN test** | The consumer. Given coreference handles - a cluster, its category, and its verbatim licensing quote - does the resolution machinery behave? Do the per-category gates fire, does the grade floor bind, does a bad grouping get declined, do the caps and walls hold, does the licensing quote reach an analyst? |
| **what this file can NEVER test** | The producer. Whether a real model reading real prose emits correct handles - how often it over-binds, under-binds, or quotes a span that does not license its own bind. Every cluster here was authored by a human who knew the answer, so even the deliberately wrong ones are wrong in ways a human imagined. |
| **why the distinction is load-bearing** | The re-plumb MOVES the load-bearing extraction burden onto coreference and discriminator capture rather than lifting it (F6). So a suite that validates the resolver against hand-made clusters can go entirely green while the dominant risk sits untested - the shape of a gate that cannot fail. |
| **where producer quality is measured instead** | Against the hand-labelled claim-gold slice, on real documents, post-S3 - and it must be reported separately, never folded in with these results. |
| **what to disclose** | That the resolution machinery is validated on synthetic coreference, and that real-world coreference binding accuracy is measured separately on hand-labelled documents. |

## What this file is, and what it refuses to hand over

**Read this file, not the corpus.** These fixtures exist so the identity machinery of S3 can be built and
tested against the *structural difficulty* of the real problem - offline, keyless, deterministically, and without a
keyed re-extract. Coreference is off in the shipped system, so the frozen bundles carry **no coreference annotations at
all**; turning the producer on means re-recording every bundle through a confirmed non-deterministic model pass that has
broken the flagship query before. This file removes that dependency from the critical path.

Every entity here is invented: the same fictional regional water-and-power-infrastructure domain as the earlier
`gold/abstract-shapes.json` and `s2-fixtures/s2-shapes.json` sets, so all three can be read together. The design is the
`TL-40` transfer set, its component is the `RC-118` cabinet, the operators are `Northern Grid Works` and the
`Water Authority`, and the places are `Redlow`, `Ashgate`, `Calder`, `Tarnholt` and `Marrow Bank`.

What is preserved from the real problem is what matters at this stage:

- which **coreference category** a bind arrives under, what its **licensing quote** actually says, and whether the quote
  supports the bind at all;
- whether a cluster is **correct**, **over-bound**, **under-bound**, or licensed by a quote that says something else -
  because a sandbox of only-correct coreference tests optimism, and the decline path can only fire on bad input;
- which **discriminators** are present, absent, or *stated absent* (a much stronger fact than missing), and whether a
  stated one can be **compared** at all;
- how many **documents** and how many independent **publishers** there are, and which reports are derivative;
- source grades, including the cases where the clean assertion comes from the weakest source in the collection;
- where a **sourced figure** exists, and where a figure would have to be invented to produce one.

**One property of the real extractor shapes every cluster in this file.** A mention is keyed by surface form within one
document, so two occurrences of the same string in one document are already one mention. Every cluster here therefore
binds *different* surface forms - which is not a simplification but a constraint the fixtures had to be authored around,
and it is worth knowing that one document using a single label for two different things is invisible to coreference by
construction (an under-reach, never an over-merge).

**No thresholds, scores, band names used as values, or config keys appear anywhere, by design.** Each fixture states its
required *outcome* in prose and, beside it, the **tempting-but-wrong** outcomes - because a fixture that only describes
success cannot catch optimism. Two of the outcomes are also worth stating as behaviour rather than as labels: "withheld"
means the pair is not fused but stays in the analyst's queue with its reason legible, and "unresolved" means the answer
names what it does not know rather than picking.

### Constraints this file holds itself to

- All entities are invented. No real designations, place names, organisations, document ids or source ids.
- No thresholds, scores, band values or config keys anywhere. Outcomes are prose; the implementer picks the mechanism and the numbers on general principle, and the test author asserts them independently.
- Every fixture carries both a required outcome and the tempting-but-wrong outcomes it must not produce.
- Where a source does not state something, the fixture value is absent or unknown - never a plausible guess.
- Coreference annotations are given in neutral terms (a cluster, a category, a verbatim licensing quote, and the truth about whether the bind is sound). The code keys they correspond to are deliberately not named here.

### How to read a cluster's `bind_truth`

| Value | Meaning |
|---|---|
| `correct` | The bind is sound and (except where a grade floor or a category rule intervenes) should stand. |
| `over_bound` | The cluster joins things that are not the same, or reaches members it has no licence over. |
| `under_bound` | The cluster is smaller than the truth - typically because the document supplies no antecedent. Under-binding is the honest failure; it must not be repaired by guessing. |
| `quote_does_not_license` | The quoted span is genuine and does not assert what the category claims. |
| `unlicensed_and_miscategorised` | The quote cannot be found in the document at all, and the category is wrong too. |

**Counts.** 11 shapes · 37 fixtures · 50 invented documents · 21 hand-authored coreference clusters (7 correct, 11 over_bound, 1 quote_does_not_license, 1 under_bound, 1 unlicensed_and_miscategorised) · 155 tempting-but-wrong outcomes · 55 negative-gold spans.

**Self-check.** Every licensing_quote occurs verbatim in the text of the document it cites. F1g-quote-is-a-paraphrase carries quote_verbatim_in_document: false. That fixture exists precisely to test what happens when a quote cannot be located, so a checker must honour the flag rather than reporting it as a defect in this file.

## What each fixture is for

| Shape | Fixture | What it is for |
|---|---|---|
| 1 | `F1a-explicit-equivalence-clean` | The reference case the whole category exists for: one document states two equivalences outright, in its own voice, with both surface forms inside the quoted span and a parenthetical wrapping one of them. |
| 1 | `F1b-quote-missing-one-surface-form` | A cluster labelled as a stated equivalence whose quoted span names only ONE of the two members and asserts no equivalence at all. The bind happens to be TRUE in the world - which is exactly what makes it dangerous. |
| 1 | `F1c-quote-is-an-enumeration-not-an-equivalence` | The mirror of F1b: the quoted span contains BOTH surface forms - and still licenses nothing, because the only relation it asserts is that both things were present, and it explicitly calls them two types. |
| 1 | `F1d-clean-equivalence-from-the-weakest-source` | A textbook stated equivalence, correctly categorised, correctly quoted, marker and all - asserted by an anonymous forum account. The deterministic gate passes; the source is the weakest class in the corpus. |
| 1 | `F1e-partial-bind-one-link-licensed-of-two` | A three-member cluster whose quote licenses exactly one of its two links. The third member is a bare descriptor at a different site that the document declines to identify. |
| 1 | `F1f-member-not-attested-in-the-document` | A cluster with a phantom third member: a surface form that appears nowhere in the document, carried in because the extractor knew the design by another of its names. |
| 1 | `F1g-quote-is-a-paraphrase` | A quote that reads exactly like the document and appears nowhere in it, attached to a cluster that is also mis-categorised: the pair is an anaphor, labelled as a stated equivalence. |
| 2 | `F2a-name-variant-obvious-but-still-not-automatic` | Three spellings of one design mark in one document - hyphen, space, and closed up. The most obviously correct bind in the whole file, and the one that must never be automatic. |
| 2 | `F2b-mark-vs-name-nothing-may-be-asserted` | A base design mark and a more specific mark of which it is a prefix, both fielded by the same operator, with a stated figure that the document explicitly refuses to attribute to either. |
| 2 | `F2c-mark-parenthetical-passes-the-marker-gate` | The same mark collision, arriving as a stated equivalence - and passing every conjunct of the deterministic gate: verbatim span, both surface forms, a parenthetical marker, good-grade source. |
| 2 | `F2d-name-variant-across-two-kinds-of-thing` | A place name reused in a company name, bound as a spelling variant - the commonest naming pattern there is, and a cross-type fusion if it lands. |
| 3 | `F3a-anaphor-positive-gate-passes` | The reference anaphor: one named, declared, typed body in the document, one pronoun-like mention referring to it, and no other candidate of a compatible kind anywhere in the text. |
| 3 | `F3b-anaphor-two-candidates-of-the-same-kind` | One document, two named bodies of the same kind, then a bare anaphor - and a real fact attached to it that belongs to exactly one of them. |
| 3 | `F3c-anaphor-second-candidate-is-unknown-typed` | One named, declared body; one anaphor; and between them a mention the extractor could not type at all. The gate must treat the untyped mention as a candidate and therefore fail. |
| 3 | `F3d-anaphor-with-no-named-antecedent-at-all` | A document whose only actor is a bare descriptor - and which states, in its own voice, that neither the body nor its parent is named anywhere. |
| 4 | `F4a-decline-on-an-attribute-conflict` | An impeccably licensed equivalence - verbatim span, both surface forms, a marker, a good-grade source - between two mentions that carry different stated operators. The register is simply wrong. |
| 4 | `F4b-decline-on-a-relationship-conflict` | The same shape with the conflict in a relation rather than an attribute: one register binds two bodies and states each of them at a different station of the same kind, over one overlapping season. |
| 4 | `F4c-non-critical-differences-must-not-decline` | The mirror of F4a and F4b: a well-licensed grouping whose members differ on a site KIND, on observation dates and on counts - none of which is a conflict. It must survive. |
| 5 | `F5a-co-location-presence-merges-formation-does-not` | Two individuated groups of the same design at one station, under one operator, reported by two unrelated vendors, with no body named by either. The shape a real site produces constantly and this corpus never does. |
| 5 | `F5b-co-location-and-the-relocation-it-would-fabricate` | F5a plus a third report, three weeks later, putting the same design and operator at a different site. This is the harm chain the co-location cap exists to prevent, with every link live. |
| 6 | `F6a-shared-designation-different-operators` | One body title, two operators, two sites, two good-grade sources - each publishing about its own establishment. Nothing links them but the string. |
| 6 | `F6b-composite-stated-on-both-sides-confirms` | The mirror of F6a and the earned mirror of the co-location trap: the operator-plus-title pairing is stated on both sides, by two sources with genuinely independent looks. |
| 6 | `F6c-differing-designation-vetoes` | Two differently titled bodies of one operator, at one station, over overlapping dates - everything agrees except the one thing that individuates them. |
| 6 | `F6d-title-reissued-after-a-stated-disestablishment` | The same operator, the same title, six years apart, with an explicit disestablishment in between - and the later source says in its own words that the title was re-raised. |
| 7 | `F7a-operator-stated-on-both-sides-and-uncomparable` | One site, one design, one period - and the operator stated on both sides in two house styles that no normalizer can reconcile: a directorate title with a regional qualifier, and an initialism with a branch qualifier. |
| 7 | `F7b-normalization-reconciles-and-the-merge-proceeds` | The mirror of F7a: the same two-house-style shape, but the difference is case, punctuation and a legal suffix - reconcilable by a declared general rule. |
| 7 | `F7c-containment-is-not-agreement` | An operator name that literally contains another: a joint directorate of two operators, against one of its parents. Containment says match; the world says a third organisation. |
| 8 | `F8a-place-is-perishable-for-a-body` | One body, one operator, one title, two stations seven months apart - with the later source stating the move in its own words. |
| 8 | `F8b-place-is-constitutive-for-a-presence` | Three sightings, identical in design, operator and figure: two at different places, and two at the same place by two unrelated vendors. |
| 8 | `F8c-coordinates-identify-a-place` | Two differently named place mentions whose stated coordinates are the same point, given in two different formats and at two different stated precisions. |
| 8 | `F8d-one-name-two-points-and-one-with-no-point` | The mirror of F8c: one station name attached to two positions tens of kilometres apart, plus a third mention of the same name with no position at all. |
| 9 | `F9a-enumeration-with-a-stated-count` | One document, one operator, one design, two bodies named only by their stations - and the source enumerates them as two and gives each its own figure. |
| 9 | `F9b-no-contrast-is-neutral` | The same two bodies in one document with no enumeration, no 'separate', and no stated total - two mentions and nothing syntactic to read either way. |
| 10 | `F10a-same-title-two-operators-must-not-fuse` | An identical body title published by two different operators about their own establishments, at two different sites. The most dangerous over-merge class on an operator-scoped map, in its simplest form. |
| 10 | `F10b-one-name-three-kinds-of-thing` | One distinctive name doing three jobs in one document: a station, the company that runs it, and the district it stands in. |
| 10 | `F10c-the-alias-route-must-be-gated-too` | F10a's two same-titled bodies plus an alias table - including one entry whose two sides are the same string, and a third document using a short form with no operator attached. |
| 11 | `F11a-thin-mention-must-stay-under-determined` | A single sentence naming a design and nothing else - no place, no holder, no date - arriving into a graph that holds exactly one well-evidenced instance of that design. |

## Which of these the frozen corpus can exercise

| Fixture | Corpus |
|---|---|
| `F1a-explicit-equivalence-clean` | NOT EXERCISABLE as a coreference fixture - the frozen bundles carry no annotation of any kind, so there is no cluster, category or quote to test against and the only route to one is a keyed re-extract. Two things about the raw prose are worth knowing, though. The corpus does contain textbook long-name-plus-parenthetical appositions - and one of them is a deliberate demo beat an analyst is meant to earn, so switching the producer on would auto-bind it. And the *cue vocabulary* this category is usually built on is largely absent: across half the corpus the phrases 'also known as', 'a.k.a.', 'i.e.', 'referred to as' and 'also designated' occur zero times. Equivalence there is carried almost entirely by parentheticals and slash-forms, so a marker vocabulary built as a list of lexical cues has little purchase on this data and the parenthetical branch carries the load. |
| `F1b-quote-missing-one-surface-form` | NOT EXERCISABLE as a bind - but the corpus makes this fixture's *rule* far more consequential than it looks, and this is the sharpest corpus finding of the pass. The frozen data contains genuine, explicitly stated equivalences whose two surface forms are dozens of lines apart, or in two different record fields of one structured document, or where the cue names a third form on a *prior* document entirely. In those cases NO single span can contain both surface forms - so the both-forms-in-the-quote conjunct has a real FALSE-NEGATIVE class in this corpus: it will correctly withhold, and it will withhold on equivalences the document really does assert. The fixture's required outcome is still right (withhold, and let an analyst see the quote); what the corpus adds is that this path will be busy, and that the queue is therefore load-bearing rather than a rare fallback. |
| `F1c-quote-is-an-enumeration-not-an-equivalence` | EXERCISABLE IN KIND, and better represented than expected: the corpus contains parentheses that ENUMERATE several related marks in one breath (four marks of one family inside a single parenthesis) as well as parentheses that state a genuine equivalence. Both shapes therefore live in the frozen data, which is exactly the pair a marker vocabulary has to separate. The mislabelled cluster over the enumerating one does not exist and cannot be produced on demand. |
| `F1d-clean-equivalence-from-the-weakest-source` | PARTIALLY EXERCISABLE - in spirit, not in form. The weakest source tier is genuinely present in the corpus (reshares, a relocation spoof, anonymous social sightings), and the inversion this fixture protects against is checkable in the shipped config rather than hypothetical: a stated identity assertion is grade-floored AND raise-only, while a coreference bind reads no source grade at all. What the corpus cannot supply is a weak-tier document carrying a clean, correctly-categorised equivalence. |
| `F1e-partial-bind-one-link-licensed-of-two` | NOT EXERCISABLE. Requires a cluster with more than two members; the frozen data has no clusters at all. |
| `F1f-member-not-attested-in-the-document` | NOT EXERCISABLE, and not producible to order either - a cluster member absent from its own document is an extractor defect, so it can be observed but never scheduled. Authoring it is the only way to test the rail before the defect occurs in production. |
| `F1g-quote-is-a-paraphrase` | NOT EXERCISABLE, with a wrinkle worth knowing: the producer already rails this at emission - a cluster whose quote cannot be found in the document is dropped before it is written. So this fixture is deliberately testing the CONSUMER against input that bypasses the producer, which is precisely the situation any fixture-driven test creates. |
| `F2a-name-variant-obvious-but-still-not-automatic` | PARTIALLY EXERCISABLE. The raw variant material is real - the corpus carries casing and format drift for one designator inside a single document (verified in the S2 pass) - but no labelled cluster exists over it. |
| `F2b-mark-vs-name-nothing-may-be-asserted` | EXERCISABLE IN KIND, and abundantly - richer than the S2 pass suggested. The corpus carries several one-line prefix collisions between a shorter mark and a longer one (including a pair where the shorter is a literal prefix of the longer and the document then states their distinctness in its own voice), plus a family whose base mark, a suffixed mark and a hyphenation variant appear across documents. The shipped containment knob states the doctrine in exactly these terms. What is NOT exercisable is the labelled bind: the pair never arrives as a cluster, so the gate is never offered the case. |
| `F2c-mark-parenthetical-passes-the-marker-gate` | PARTIALLY EXERCISABLE, and the corpus is more dangerous here than I first wrote. It contains parentheticals that state a real equivalence between two marks AND a parenthetical that merely lists four marks of one family - so both the licensing and the non-licensing use of the same punctuation are live in the frozen data, and a marker vocabulary that accepts any parenthetical will bind the second kind. The specific input this fixture authors - a narrowing mark inside a parenthetical on the SUBJECT design - is not in the corpus, and cannot be conjured without a re-extract that may or may not produce it. |
| `F2d-name-variant-across-two-kinds-of-thing` | NOT VERIFIED in this pass. Place names reused inside organisation names do occur in the corpus's commercial material, but I did not confirm a pair that a name route would actually join, so treat this fixture as authored rather than abstracted. |
| `F3a-anaphor-positive-gate-passes` | EXERCISABLE in substance. One corpus document uses a bare definite noun phrase five times for a body named exactly once at the top, with the only nearby distractors non-coreferent by kind - the cleanest positive case for the anaphor gate anywhere in the corpus. The gate's own input (a mention inventory) still only exists once the producer runs, so the annotation half remains authored. |
| `F3b-anaphor-two-candidates-of-the-same-kind` | EXERCISABLE at design/system level - corrected from my first assessment. One corpus document offers FOUR same-kind antecedents before a bare referring expression, and adjacency favours the WRONG one (the phrase sits immediately after a distractor and denotes something else); another has two referring expressions in a single sentence pointing at two different referents. So the ambiguity case is real and severe in the prose. It remains not exercisable at BODY level, where the corpus has one numbered body in 52 documents. |
| `F3c-anaphor-second-candidate-is-unknown-typed` | NOT EXERCISABLE. It needs a mention the extractor declined to type, which is an extraction outcome, not a property of the source text - so the corpus cannot supply it at all, whatever it contains. |
| `F3d-anaphor-with-no-named-antecedent-at-all` | EXERCISABLE in substance, better than expected. One corpus document uses a referring expression for an organisation it never names at all, and the corpus supplies the stronger version of the fixture's second half - documents that STATE the absence of identity, including one stating it across a whole pass history and one stating a non-disclosure policy, so the 'this will not close' reason is real data rather than an authored flourish. |
| `F4a-decline-on-an-attribute-conflict` | NOT EXERCISABLE. The decline path needs a grouping to give up, and the frozen data contains no groupings. |
| `F4b-decline-on-a-relationship-conflict` | NOT EXERCISABLE, twice over. There are no clusters to decline, and the relationship half has no input either: across 52 documents there is exactly one stated body-at-site basing and it belongs to an off-subject decoy in another country (verified in the S2 pass by two independent routes - a text search, and the answer key annotating every basing as derived). |
| `F4c-non-critical-differences-must-not-decline` | NOT EXERCISABLE. Needs one body stated at two places of different kinds concurrently; no corpus document places one body at two sites at all. |
| `F5a-co-location-presence-merges-formation-does-not` | NOT EXERCISABLE, and this is the corpus's largest structural hole - verified twice now. There are no two individuated same-kind bodies anywhere in the frozen data; the nearest approach is a cardinality without individuation (a single claim carrying a quantity of bodies, not two referents). The co-location cap therefore has no corpus input at all. |
| `F5b-co-location-and-the-relocation-it-would-fabricate` | NOT EXERCISABLE end to end, which is why the harm chain went unnoticed for so long. Every ingredient is in the corpus separately - two sites, one design, no titles, a relocation beat, and a supersede floor built against a weak-tier spoof - but with no two co-located same-kind bodies to over-merge, the chain from identity error to drawn relocation to deleted gap cannot be demonstrated on the frozen data. The gate is fixture-only. |
| `F6a-shared-designation-different-operators` | EXERCISABLE at design level, and richly - one designation string is attached to five different national contexts, another is fielded by three operators with three different contract values attached to what the sources all call 'the deal', and two design families each appear as a perfect two-operator/two-name square stated in a single line. At BODY level it is not exercisable: one numbered body in 52 documents, and it is a planted designator collision belonging to a foreign army. |
| `F6b-composite-stated-on-both-sides-confirms` | NOT EXERCISABLE. The composite needs an operator-plus-title pairing stated on both sides; the corpus states no body title for the subject at all, so the top two rungs of the discriminator ladder have zero data. Every basing in the answer key is annotated derived, and one carries a note saying no document states a named body at a named site. |
| `F6c-differing-designation-vetoes` | NOT EXERCISABLE - it needs two differently-titled bodies of one operator, and the corpus has no two titled bodies of any operator. |
| `F6d-title-reissued-after-a-stated-disestablishment` | PARTIALLY EXERCISABLE - corrected. The corpus does contain a stated chain of amalgamations and redesignations of one body across decades, with the document itself saying the chain is not consistently recorded and that accounts differ on the final date. That is an unbounded alias sink: a transitive closure over 'was redesignated as' has no floor there, which is the same hazard this fixture guards from the other side. What is missing is the clean version - a stated disestablishment followed by a re-raising of the same title - and the body in question is the off-subject decoy, so nothing about the subject can be tested this way. |
| `F7a-operator-stated-on-both-sides-and-uncomparable` | EXERCISABLE, on both sides of one candidate merge - a direct correction to what I first wrote. Two corpus documents place the SAME subject under two service commands whose names differ by one word, where one name is a substring of the other, both strings are registered aliases of a single entity in the shipped registry, and the answer key says only one of the two services is right. The same pair of documents disagrees on five other facts about that one designation with no cross-reference between them. The corpus adds three more hard-failure abbreviations: two that are never expanded anywhere in 52 documents, and one that is a single edit away from a different country's acronym, so a normalizer that 'corrects' it moves the entity to the wrong nation. The shipped config has already conceded the shape by declaring the discriminator soft - which is the wrong one of the three states. |
| `F7b-normalization-reconciles-and-the-merge-proceeds` | EXERCISABLE. The corpus carries case and punctuation drift on organisation and country names across documents - one country appears in two spellings, and one document drifts internally - which is exactly the reconcilable half. The config also already records that a naive comparison on one of these would false-wall a real pair. |
| `F7c-containment-is-not-agreement` | EXERCISABLE. Joint-use compounds naming two services in one string occur in the corpus (primary side only - zero in the chaff half), so the containment trap has real material. And the operator collision in F7a is a second, sharper instance of the same shape: one command name literally contains the other while denoting a different service. |
| `F8a-place-is-perishable-for-a-body` | PARTIALLY EXERCISABLE. The corpus has a two-ended relocation beat with dated basings at both ends, so the perishable half of the geography question is live. It has no title at either end, so the fixture's actual subject - one TITLED body that moves - cannot be built from it; the corpus relocation is earned on geography and imagery alone. |
| `F8b-place-is-constitutive-for-a-presence` | EXERCISABLE, and the corpus's strongest suit: equipment-at-a-site sightings are its dominant shape, including one site reported twice with different figures and the same design reported at more than one site. The one thing to check when using real data here is source independence between the two same-site reports, which the corpus makes genuinely non-trivial. |
| `F8c-coordinates-identify-a-place` | EXERCISABLE - upgraded. The primary half of the corpus carries resolved coordinates on a double-digit number of claims across five different notations, which is precisely the reconcile-the-notation-before-comparing requirement. The chaff half carries no coordinates for any military object at all - every chaff site is a bare toponym - so geometric place resolution has no fallback there, and one chaff post says why that hurts ('which village exactly, it is a big district'). |
| `F8d-one-name-two-points-and-one-with-no-point` | EXERCISABLE IN KIND, with a caveat I checked myself. The frozen data does contain one aerodrome identifier filed at two positions in two documents roughly 1,100 km apart - and the wrong one lands in the other of the two cities this subject's relocation question turns on. But the second document is tagged in the answer key with a code-string-noise corruption class, is marked off-subject, and is expected to yield no claim at all, so it is unclear whether the mismatch is the intended noise or an unnoticed error, and either way it cannot reach the graph through claims while that expectation holds. So: the shape is real in the source text, it is not usable as a clean test, and the residual risk belongs to any pass that reads chaff navigation-warning position fixes as place evidence. The unpositioned-namesake half is common - places with no coordinates are frequent throughout. |
| `F9a-enumeration-with-a-stated-count` | PARTIALLY EXERCISABLE, and the sourced-count half is richer than the S2 pass found: the corpus states order-of-battle figures repeatedly, including one document stating two incompatible figures for one force in four lines (a per-battery TEL count and a per-battalion range, with the two echelon words never equated), one stating a count with the unit type left as a slash-pair, one stating '3 (or possibly 4, sources vary)', and one stating a figure with two competing organising words for what the figure counts. The destination now exists too - the shipped ontology declares the count attribute sourced-only and never derived from reports merged. What is absent is the enumeration of two INDIVIDUATED bodies in one document, so the contrast channel itself has no corpus input. |
| `F9b-no-contrast-is-neutral` | PARTIALLY EXERCISABLE. Same-document pairs with no contrast are abundant - one site name appears three times as three separate mentions in a single document (verified in the S2 pass) - but not as two candidate BODIES, which is the pair this fixture judges. |
| `F10a-same-title-two-operators-must-not-fuse` | EXERCISABLE IN KIND, and deliberately planted - one designator-string collision decoy, a foreign body whose title collides with subject-side strings, with the answer key stating the document must not be read as being about the subject. Every discriminating signal sits outside the numeral. Being off-subject limits what it demonstrates, but it is the one place in the corpus where this gate can bite on real data. |
| `F10b-one-name-three-kinds-of-thing` | EXERCISABLE - corrected and stronger than I first wrote. The corpus carries two legal entities of one shipping group on a single line (a national agent and a European carrier) which must not merge; a research institute named two different ways in one parenthesis, colliding by naming pattern with a different organisation's institutes that the answer key says must stay distinct; and - the sharpest cross-boundary case in the corpus - one bare locative phrase used for sites in two different countries, in both halves of the corpus, one of them a missile-launch rumour and the other the subject's own site. |
| `F10c-the-alias-route-must-be-gated-too` | NOT EXERCISABLE as authored, and I checked: the seed place gazetteer holds 74 alias entries and NONE has the same string on both sides, so the self-referential entry in this fixture is invented to make the route testable. What the corpus does supply is what an ungated transitive alias route would eat: a redesignation chain the document itself says is not consistently recorded, a person-name chain of five spellings that would join a civilian import, a second civilian import and a defence consignment, and two truncated telephone numbers sharing a prefix - a false edge built from a redaction artefact. |
| `F11a-thin-mention-must-stay-under-determined` | EXERCISABLE, strongly - upgraded. The corpus's thinnest document types its object only as 'some kind of solid-fuel job', flips its identity twice in one sentence, gives its location as two nameless definite descriptions, dates it from a recycled older image, and flips its whole class in the final line. Elsewhere the corpus has a post stating 'no date given in that post btw, no location either, just \"a designated site\"', a document with no date at all, and a commissioning event with a precise date and an undisclosed garrison. The one condition the corpus cannot supply is the fixture's sharpest edge - a thin mention arriving where exactly ONE candidate instance exists - because the corpus holds several presences of the subject design. |

## What only shows up across fixtures

**Ten things only become visible across these fixtures.**

1. **Exactly one fixture in the equivalence shape requires an automatic bind** (`F1a`). Six require a refusal. That
   ratio is deliberate: hand-authored clusters are all implicitly correct, so a sandbox that mostly rewards binding
   would test optimism and would never fire the decline path.
2. **`F1c` and `F2c` are the same defect at two strengths, and they constrain the marker vocabulary from both sides.**
   Both satisfy "the quote contains both surface forms" while licensing nothing. `F1c` fails because no marker is
   present; `F2c` **passes** the marker test on a parenthetical and is still wrong. So a marker vocabulary that is only a
   list of tokens and punctuation cannot separate them - the second needs a rule about what the parenthetical *contains*
   (another name for the same thing, or a narrowing mark of it).
3. **`F3c` and `F11a` are one fallacy at two scales.** In `F3c` "no other candidate was found in this document" is read
   as "no other candidate exists"; in `F11a` "only one candidate exists in our graph" is read as "unambiguous". Both are
   claims about our own reach dressed as claims about the world, and both fail hardest when coverage is thinnest.
4. **`F4a` and `F4b` forbid exactly what `F4c` requires**, and the distinguishing fact is not how *much* the members
   differ but *which kind* of difference it is. A decline path keyed on the magnitude or count of differences gets all
   three wrong while looking consistent.
5. **`F5b` and `F8a` require opposite outputs from a nearly identical input.** Both are one design, one operator, two
   sites, successive dates. In `F8a` a move must be drawn; in `F5b` drawing one is fabrication. The difference is never
   the strength of the later report - it is whether the identity was earned on something that individuates a body.
6. **The four `F6` fixtures must be satisfied by ONE identifier declaration pulling in four directions**: a shared title
   alone earns nothing (`F6a`), the operator-plus-title composite earns a confirm (`F6b`), a differing title vetoes
   (`F6c`), and a stated discontinuity in time outranks the composite (`F6d`). Any three are easy alone; a rule that
   treats the title as an identifier passes `F6b` and `F6c` and fails the other two.
7. **The three `F7` fixtures are three answers to one comparison** - untestable, testable-and-equal, testable-and-
   neither. A normalizer built on containment passes `F7b` and fails `F7c`; one built on exact match passes `F7c` and
   fails `F7b`; one that treats an untestable value as absent fails `F7a` *while looking correct on the other two*.
8. **`F8a` and `F8b` are the same field with opposite meanings** for two kinds of thing: for a body, place expires; for
   equipment at a place, the place is part of what the thing is. One global setting cannot serve both, and whichever one
   is chosen breaks the other fixture. `F8c`/`F8d` add the third part - a place's coordinates identify it - which is what
   lets a presence and a place confirm at all.
9. **`F9b` is `F5a` with a document boundary removed**, and it must end the same way. That is the point of the pair: the
   absence of a stated contrast changes nothing, so a same-document pair with no contrast is judged exactly as a
   cross-document pair would be.
10. **`F10c` is the reason the other two `F10` fixtures are not sufficient.** Its operator and kind gates are all present
    and correct, and none of them is on the path that fires. A gate proven on the direct-name path can be entirely
    honest and entirely useless.

**And one property the whole set shares:** where a discriminator is not stated, it is unknown - never inferred from
context, never treated as a conflict, and never allowed to license a convenient outcome. Absence leaves a thing
under-individuated and flagged; it does not de-conflict, does not merge, and does not get back-filled. Several fixtures
go further and contain a *stated* absence ("no section titles legible", "this item does not say which mark", "neither
the section nor its parent is named"), which is stronger evidence than silence and must be kept as data rather than
discarded as prose.

---

# Shape 1 - EXPLICIT_EQUIVALENCE - the licensing quote and the three ways it fails

## `F1a-explicit-equivalence-clean`

**Scope:** 1 (Tier-0 coref required), 2 (D-13.17 auto-bind policy)  
**Refs:** D-13.17 (equivalence gate); the licensing quote (written but read nowhere); acceptance: authoritative binds pass a deterministic gate AND a grade floor

**Purpose.** The reference case the whole category exists for: one document states two equivalences outright, in its own voice, with both surface forms inside the quoted span and a parenthetical wrapping one of them.

**Why it is hard.** Nothing here is hard except what it proves by contrast: this is the ONE shape in this file where an automatic bind is correct, so it is the control against which the six failures below are read. It also quietly carries two traps - the document co-refers a design AND a component in the same breath, and it names an operator on a line of its own that licenses no bind at all.

### Documents

**`register-CC`** - curated establishment register, source grade **B**, regional regulator's compiled register (no stake in either operator), dated 2025-03-04

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 11/2025
Compiled 04 March 2025

Redlow pumping station, north apron: transfer plant of the High-Volume Transfer Set (TL-40) type is recorded.
The set's control cabinet, the Regional Cabinet 118 (RC-118), is recorded on a prepared pad to the east.

Operator of record for both entries: Northern Grid Works.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-CC) | High-Volume Transfer Set | `design` |  |
| `m2` (register-CC) | TL-40 | `design` |  |
| `m3` (register-CC) | Regional Cabinet 118 | `component` |  |
| `m4` (register-CC) | RC-118 | `component` |  |
| `m5` (register-CC) | Redlow pumping station | `place` |  |
| `m6` (register-CC) | Northern Grid Works | `operator_org` |  |

### Hand-authored coreference clusters

**`cc-1`** (register-CC) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`correct`**

> transfer plant of the High-Volume Transfer Set (TL-40) type is recorded

Both surface forms sit inside the quoted span; the parenthetical wraps one of them; the span is verbatim.

**`cc-2`** (register-CC) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m3`, members `m4`, bind truth **`correct`**

> The set's control cabinet, the Regional Cabinet 118 (RC-118), is recorded on a prepared pad to the east.

Same shape one type down: a component's long name and its short mark.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED ('Northern Grid Works'), for both register entries |
| geography | STATED as a named station and an apron; no coordinates |
| designation | ABSENT - no body is named anywhere in the extract |
| time | STATED only as the register's compilation date (2025-03-04); no observation date |

### Required outcome (prose - choose your own mechanism and values)

Both binds are automatic: each quote is verbatim, contains both members' surface forms, and contains an equivalence marker. The two design mentions become one design and the two component mentions become one component - and the quote that licensed each bind is retained and reachable from the result, because an analyst reviewing a merge must be able to read the sentence that caused it. Nothing else in the extract binds: the design and the component are two different kinds of thing and share only the phrase 'the set's', and the operator line licenses no identity at all. Because no body is named, no formation exists here; the register's compilation date is not an observation date.

### Tempting but wrong

- Bind the design to the component because the document introduces the cabinet as 'the set's control cabinet' - a possessive relation read as an identity.
- Treat the operator line ('Operator of record for both entries') as licensing a bind between the two entries, which is a relation about custody, not identity.
- Bind, and then discard the quote once the merge is made. The quote is the only artefact that lets a human check the bind, and a merge whose reason cannot be read is not auditable.
- Date the plant's presence to the compilation date, giving an observation no source made.

### Negative gold - spans that must produce NO claim

- 'Compiled 04 March 2025' is provenance, not a fact about the plant.
- 'north apron' individuates a location within the station; it is not a second station.

**Corpus:** NOT EXERCISABLE as a coreference fixture - the frozen bundles carry no annotation of any kind, so there is no cluster, category or quote to test against and the only route to one is a keyed re-extract. Two things about the raw prose are worth knowing, though. The corpus does contain textbook long-name-plus-parenthetical appositions - and one of them is a deliberate demo beat an analyst is meant to earn, so switching the producer on would auto-bind it. And the *cue vocabulary* this category is usually built on is largely absent: across half the corpus the phrases 'also known as', 'a.k.a.', 'i.e.', 'referred to as' and 'also designated' occur zero times. Equivalence there is carried almost entirely by parentheticals and slash-forms, so a marker vocabulary built as a list of lexical cues has little purchase on this data and the parenthetical branch carries the load.

## `F1b-quote-missing-one-surface-form`

**Scope:** 2 (D-13.17 auto-bind policy)  
**Refs:** D-13.17 (equivalence gate: the quote must contain BOTH surface forms); the ruling's required negative case: 'a quote missing one surface form'

**Purpose.** A cluster labelled as a stated equivalence whose quoted span names only ONE of the two members and asserts no equivalence at all. The bind happens to be TRUE in the world - which is exactly what makes it dangerous.

**Why it is hard.** Every soft signal agrees: the category says equivalence, the source is good-grade, the quote is genuinely verbatim, and a human reader knows the two names denote one design. The only thing missing is the licence - the sentence quoted is a sentence about market position, not about identity. A gate that trusts the label over the span passes here, and once it passes there is no cap anywhere to restrain it.

### Documents

**`press-DD`** - trade press item, source grade **B**, trade press, no stake, dated 2025-03-19

```
CALDONIA PLANT MONTHLY - 19 March 2025

Northern Grid Works has taken delivery of further transfer plant for the northern scheme.
The High-Volume Transfer Set is the mainstay of the operator's transfer fleet.
Elsewhere in the scheme, TL-40 skids at Calder depot are being re-cabinetted.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (press-DD) | High-Volume Transfer Set | `design` |  |
| `m2` (press-DD) | TL-40 | `design` |  |
| `m3` (press-DD) | Northern Grid Works | `operator_org` |  |
| `m4` (press-DD) | Calder depot | `place` |  |

### Hand-authored coreference clusters

**`dd-1`** (press-DD) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`quote_does_not_license`**

> The High-Volume Transfer Set is the mainstay of the operator's transfer fleet.

Verbatim, good grade, and the bind is true in the world - but the span contains one surface form and no equivalence marker. Nothing in the document states that the two names are one design.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED ('Northern Grid Works') |
| geography | STATED for the second mention only ('Calder depot') |
| designation | ABSENT |
| time | STATED as the item's publication date (2025-03-19) |

### Required outcome (prose - choose your own mechanism and values)

The bind must not be automatic. The span the extractor quoted does not license it: one of the two surface forms is absent from the quote and no equivalence is asserted anywhere in the document. The two design mentions therefore stay apart for now, the pair reaches an analyst carrying the quote, and the analyst can see at a glance that the quote does not support what was claimed - which is the whole point of carrying it. Under-binding here is the honest outcome even though the two names really are one design: the system's job is to state what its sources state.

### Tempting but wrong

- Bind because the category label says EXPLICIT_EQUIVALENCE. The label is the extractor's claim; the quote is the evidence for it, and checking the label against itself is a gate that cannot fail.
- Bind because the two names are obviously the same design to any reader. That knowledge came from outside this document - and the next time the same reasoning fires it will be wrong and unfalsifiable.
- Bind because a good-grade source is speaking. Grade governs how much to believe an assertion; it cannot supply an assertion that was never made.
- Discard the pair because the gate failed. The evidence is real and an analyst can settle it in seconds; dropping it converts a cheap human decision into a permanent silent gap.

### Negative gold - spans that must produce NO claim

- 'has taken delivery of further transfer plant' states no count and no location.
- 'are being re-cabinetted' is a works activity, not a sighting of plant at Calder on a date.

**Corpus:** NOT EXERCISABLE as a bind - but the corpus makes this fixture's *rule* far more consequential than it looks, and this is the sharpest corpus finding of the pass. The frozen data contains genuine, explicitly stated equivalences whose two surface forms are dozens of lines apart, or in two different record fields of one structured document, or where the cue names a third form on a *prior* document entirely. In those cases NO single span can contain both surface forms - so the both-forms-in-the-quote conjunct has a real FALSE-NEGATIVE class in this corpus: it will correctly withhold, and it will withhold on equivalences the document really does assert. The fixture's required outcome is still right (withhold, and let an analyst see the quote); what the corpus adds is that this path will be busy, and that the queue is therefore load-bearing rather than a rare fallback.

## `F1c-quote-is-an-enumeration-not-an-equivalence`

**Scope:** 2 (D-13.17 auto-bind policy), 4 (same-doc contrast)  
**Refs:** D-13.17 (equivalence gate: both forms AND a configured marker); the ruling's required negative case: 'a licensing quote that does not support the bind'

**Purpose.** The mirror of F1b: the quoted span contains BOTH surface forms - and still licenses nothing, because the only relation it asserts is that both things were present, and it explicitly calls them two types.

**Why it is hard.** 'Both surface forms are in the quote' is the conjunct most likely to be implemented alone, because it is the easy one to check. This fixture is the case where that conjunct is satisfied and the truth is the opposite of the bind: the sentence distinguishes the two designs and attaches a different figure to each. A gate missing the marker requirement fuses two designs and then has two counts to reconcile on one node.

### Documents

**`survey-EE`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-04-02

```
AERIAL SURVEY EXTRACT - ASHGATE TRANSFER YARD
Collected 02 April 2025, single pass, 0.5 m

Two set types are present on the yard hardstand: the TL-40 and the TL-44 are both visible, six skids of the former and two of the latter.

No markings or signage are legible at this ground sample distance.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (survey-EE) | TL-40 | `design` |  |
| `m2` (survey-EE) | TL-44 | `design` |  |
| `m3` (survey-EE) | Ashgate transfer yard | `place` |  |

### Hand-authored coreference clusters

**`ee-1`** (survey-EE) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> the TL-40 and the TL-44 are both visible, six skids of the former and two of the latter

Verbatim, both surface forms present, good grade - and no equivalence marker. The sentence's own framing ('Two set types are present') asserts the opposite of the bind.

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT - the survey names no operator |
| geography | STATED ('Ashgate transfer yard', 'yard hardstand') |
| designation | ABSENT |
| time | STATED exactly (collected 2025-04-02) |

### Required outcome (prose - choose your own mechanism and values)

The bind must be refused. Two surface forms in one span is a necessary condition and not a sufficient one: an equivalence marker must be present, and here there is none - the span is an enumeration. Both designs survive as two designs, the six skids attach to the first and the two skids to the second, and the document's own contrast is retained as what it is: this source distinguishing two things it saw together. That contrast is local to this document and must not become a general prohibition that splits clusters elsewhere.

### Tempting but wrong

- Pass the gate on 'both surface forms present' alone, fusing two genuinely different designs on a sentence that says they are different.
- Fuse and reconcile the two figures into eight skids of one design - a count no source states, on a design no source saw eight of.
- Treat the enumeration as a hard, transitive do-not-merge, so that every other cluster mentioning either design is now split by a contrast stated in one survey. An establishment list is nothing but enumerations; a transitive veto built from them shatters legitimate identities.
- Attach the operator from a neighbouring document because a survey with no operator 'must' be the operator whose site it is.

### Negative gold - spans that must produce NO claim

- 'No markings or signage are legible' is a stated absence of identifiers - a fact worth keeping, and not a fact about either design's identity.
- 'single pass, 0.5 m' is collection metadata.

**Corpus:** EXERCISABLE IN KIND, and better represented than expected: the corpus contains parentheses that ENUMERATE several related marks in one breath (four marks of one family inside a single parenthesis) as well as parentheses that state a genuine equivalence. Both shapes therefore live in the frozen data, which is exactly the pair a marker vocabulary has to separate. The mislabelled cluster over the enumerating one does not exist and cannot be produced on demand.

## `F1d-clean-equivalence-from-the-weakest-source`

**Scope:** 2 (D-13.17 auto-bind policy: the grade floor)  
**Refs:** D-13.17 (a grade floor set above the stated same-as floor); an authoritative bind fuses uncapped - no cap restrains it

**Purpose.** A textbook stated equivalence, correctly categorised, correctly quoted, marker and all - asserted by an anonymous forum account. The deterministic gate passes; the source is the weakest class in the corpus.

**Why it is hard.** This is where a gate-only policy inverts the credibility system. A source-stated equivalence from a graded source is held to a floor and reaches an analyst; an anonymous post read by the extractor as an equivalence would fuse at full confidence with no cap and no queue. The weakest source in the collection becomes the strongest merge path in the system, and nothing downstream can undo it.

### Documents

**`post-FF`** - forum post, source grade **E**, anonymous forum account, unverifiable, dated 2025-04-06

```
[boardpost] user "grid-spotter" - 06 April 2025

nobody official will say it but the Vanguard-pattern set at Tarnholt IS the TL-40, i.e. the High-Volume Transfer Set - same skid, same cabinet, different paperwork.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (post-FF) | TL-40 | `design` |  |
| `m2` (post-FF) | High-Volume Transfer Set | `design` |  |
| `m3` (post-FF) | Tarnholt | `place` |  |
| `m4` (post-FF) | Vanguard | `design_family` |  |

### Hand-authored coreference clusters

**`ff-1`** (post-FF) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`correct`**

> the TL-40, i.e. the High-Volume Transfer Set

Every deterministic conjunct passes: verbatim, both surface forms, an explicit marker. Only the grade of the asserting source is wrong.

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT |
| geography | STATED loosely ('at Tarnholt') |
| designation | ABSENT |
| time | STATED as the post's date (2025-04-06) |

### Required outcome (prose - choose your own mechanism and values)

The deterministic gate passes and the bind must still not be automatic, because the only thing asserting the equivalence is an anonymous unverifiable account. The pair reaches an analyst with its quote and its source class visible, and it must remain visible: withholding an automatic merge must not push the pair out of the review queue altogether, because a suppressed pair is indistinguishable from a pair no one ever proposed. Note that the bind is correct - the fixture is not about the claim being false, it is about which sources are allowed to move the graph on their own.

### Tempting but wrong

- Bind because the gate passed. A structural gate tests whether the document says it; the grade tests whether the saying is worth anything.
- Bind because the post is 'internally consistent' or 'detailed' ('same skid, same cabinet') - fluency is not provenance.
- Drop the post as noise. It is a sourced assertion with a quote and a date; the honest handling is to grade it, not to delete it.
- Apply a penalty large enough that the pair leaves the analyst's queue. Withholding a merge means 'not automatically', never 'not at all'.

### Negative gold - spans that must produce NO claim

- 'nobody official will say it' is the poster's framing, not evidence of official suppression.
- 'different paperwork' asserts nothing checkable.

**Corpus:** PARTIALLY EXERCISABLE - in spirit, not in form. The weakest source tier is genuinely present in the corpus (reshares, a relocation spoof, anonymous social sightings), and the inversion this fixture protects against is checkable in the shipped config rather than hypothetical: a stated identity assertion is grade-floored AND raise-only, while a coreference bind reads no source grade at all. What the corpus cannot supply is a weak-tier document carrying a clean, correctly-categorised equivalence.

## `F1e-partial-bind-one-link-licensed-of-two`

**Scope:** 2 (D-13.17 auto-bind policy), C5 (per-link gate, partial bind)  
**Refs:** C5 (the gate is per link; a cluster binds only over passing links; each failing link becomes a candidate pair)

**Purpose.** A three-member cluster whose quote licenses exactly one of its two links. The third member is a bare descriptor at a different site that the document declines to identify.

**Why it is hard.** The category is stamped on the cluster, not on the links, so the natural implementation is all-or-nothing - and both all-or-nothing answers are wrong here. Binding all three imports an identity the document explicitly withholds ('is not further identified in this bulletin'); refusing the whole cluster throws away a bind the source did make in so many words.

### Documents

**`bulletin-GG`** - operator works bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-15

```
NORTHERN GRID WORKS - WORKS BULLETIN 22/2025
Dated: 15 April 2025

The High-Volume Transfer Set (TL-40) at Redlow remains in service.
The uprated set now at Ashgate is of the same family and is not further identified in this bulletin.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-GG) | High-Volume Transfer Set | `design` |  |
| `m2` (bulletin-GG) | TL-40 | `design` |  |
| `m3` (bulletin-GG) | The uprated set | `unknown` | a bare descriptor at a second site; the document says it is of the same family and is not further identified |
| `m4` (bulletin-GG) | Redlow | `place` |  |
| `m5` (bulletin-GG) | Ashgate | `place` |  |

### Hand-authored coreference clusters

**`gg-1`** (bulletin-GG) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, `m3`, bind truth **`over_bound`**

> The High-Volume Transfer Set (TL-40) at Redlow remains in service.

The quote licenses anchor-to-m2 and says nothing whatever about m3. One cluster, two links, one licence.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity (the operator's own bulletin) |
| geography | STATED for both members ('at Redlow', 'now at Ashgate') |
| designation | ABSENT |
| time | STATED as the bulletin's date (2025-04-15) |

### Required outcome (prose - choose your own mechanism and values)

The cluster binds over the licensed link only. The first two mentions become one design; the third does not ride in on the cluster's category - it becomes a candidate pair carrying the same quote, so an analyst can see both what was licensed and what was assumed. Nothing may be asserted about the Ashgate set beyond the bulletin's own words: same family, uprated, deliberately not identified. 'Same family' is a lineage statement, not an identity, and the document's refusal to identify it is itself a fact worth keeping.

### Tempting but wrong

- Bind all three because the cluster's category is authoritative. The third member then inherits an identity from a sentence that does not mention it.
- Refuse the whole cluster because one link fails, discarding an equivalence the source stated outright.
- Infer that the uprated set is a TL-40 because it is 'of the same family' - the inference the document pointedly declines to make.
- Treat 'The uprated set' as a fourth design and mint it as a peer of the TL-40, so the graph gains a design no source names.

### Negative gold - spans that must produce NO claim

- 'remains in service' is a status statement, not a new sighting.
- 'is not further identified in this bulletin' is a stated limit of this source - keep it as such.

**Corpus:** NOT EXERCISABLE. Requires a cluster with more than two members; the frozen data has no clusters at all.

## `F1f-member-not-attested-in-the-document`

**Scope:** 2 (D-13.17 auto-bind policy), C9 (bind only over ids attested in the contributing document)  
**Refs:** C9 (an authoritative bind may instantiate only over entity ids attested in the contributing document)

**Purpose.** A cluster with a phantom third member: a surface form that appears nowhere in the document, carried in because the extractor knew the design by another of its names.

**Why it is hard.** The quote is verbatim and licenses the real link, so the cluster looks clean and the phantom rides in behind a passing gate. The harm is not local: a bind expands through global name matching, so a document-local reading reaches out and fuses whatever else in the graph answers to that third name - including things this document never saw.

### Documents

**`register-HH`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-04-24

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 17/2025
Compiled 24 April 2025

Calder depot: the High-Volume Transfer Set (TL-40) is recorded, operator Northern Grid Works.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-HH) | High-Volume Transfer Set | `design` |  |
| `m2` (register-HH) | TL-40 | `design` |  |
| `m3` (register-HH) | V-40 | `design` | DOES NOT APPEAR IN THE DOCUMENT AT ALL - the extractor supplied it from elsewhere |
| `m4` (register-HH) | Calder depot | `place` |  |
| `m5` (register-HH) | Northern Grid Works | `operator_org` |  |

### Hand-authored coreference clusters

**`hh-1`** (register-HH) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, `m3`, bind truth **`over_bound`**

> Calder depot: the High-Volume Transfer Set (TL-40) is recorded, operator Northern Grid Works.

Verbatim quote, both real surface forms, a marker, good grade - and a third member the document never mentions. A document-local reading cannot reach a name the document does not contain.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED ('Northern Grid Works') |
| geography | STATED ('Calder depot') |
| designation | ABSENT |
| time | STATED as the compilation date (2025-04-24) |

### Required outcome (prose - choose your own mechanism and values)

The licensed link binds; the phantom member is refused and nothing is minted for it. A bind read out of one document may only range over the things that document actually names - otherwise a single reading propagates through the whole graph via names the source never used. The refusal should be visible rather than silent, because a cluster member that is not in its own document is an extractor defect worth counting.

### Tempting but wrong

- Bind all three because they are all the same design in the wider graph - importing outside knowledge into what is defined as a document-local reading.
- Mint a mention for the phantom so the cluster is well-formed, which launders the defect into data.
- Expand the bind through every entity in the graph that answers to any of the three names, so one register line silently merges instances from documents that share none of its content.
- Discard the whole cluster, losing the equivalence the register did state.

### Negative gold - spans that must produce NO claim

- The register's compilation date is not a sighting date.

**Corpus:** NOT EXERCISABLE, and not producible to order either - a cluster member absent from its own document is an extractor defect, so it can be observed but never scheduled. Authoring it is the only way to test the rail before the defect occurs in production.

## `F1g-quote-is-a-paraphrase`

**Scope:** 2 (D-13.17 auto-bind policy)  
**Refs:** D-13.17 (the quote must occur verbatim in the document); note: the producer already rails this at emission - this fixture tests the consumer, which is fed directly

**Purpose.** A quote that reads exactly like the document and appears nowhere in it, attached to a cluster that is also mis-categorised: the pair is an anaphor, labelled as a stated equivalence.

**Why it is hard.** The paraphrase is faithful in substance, so every check except literal presence passes - category, marker, both surface forms, grade. And the mis-categorisation is invisible unless the quote is actually read against the text: the moment you compare them, you see the document never stated an equivalence, it used a pronoun. Two defects, one detection.

### Documents

**`bulletin-JJ`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-05-02

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 09/2025
Dated: 02 May 2025

2 Transfer Section holds the transfer plant at Redlow pumping station.
The section's plant is of the Vanguard family.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-JJ) | 2 Transfer Section | `formation` |  |
| `m2` (bulletin-JJ) | The section | `formation` | an anaphoric mention, not a second name |
| `m3` (bulletin-JJ) | Redlow pumping station | `place` |  |
| `m4` (bulletin-JJ) | Vanguard | `design_family` |  |

### Hand-authored coreference clusters

**`jj-1`** (bulletin-JJ) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`unlicensed_and_miscategorised`**  ⚠ **quote is NOT verbatim in the document (deliberate)**

> 2 Transfer Section, also called the section, holds the transfer plant at Redlow pumping station.

DELIBERATE EXCEPTION to this file's verbatim invariant. The span is a plausible paraphrase of the document's first line and does not occur in it. The category is also wrong: this is an anaphor.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity (the operator's own bulletin) |
| geography | STATED ('Redlow pumping station') |
| designation | STATED ('2 Transfer Section') |
| time | STATED as the bulletin's date (2025-05-02) |

### Required outcome (prose - choose your own mechanism and values)

A span that is not literally in the document licenses nothing, and that check must come before category and grade are considered - otherwise the most confident-looking evidence in the system is the evidence no one can locate. The equivalence bind is refused. Separately, the underlying pair may still be a perfectly good anaphoric bind on its own route, judged by the anaphor test rather than by a fabricated equivalence: refusing the bad licence must not also destroy the good one. And a cluster whose quote cannot be found is an extractor defect that should be counted, not quietly dropped.

### Tempting but wrong

- Accept the quote because it faithfully reflects the sentence. Once 'close enough' is allowed, the audit trail stops being a trail.
- Accept because category, marker and grade all pass - three passing conjuncts do not repair a missing one.
- Refuse the bind and also discard the pair, when the same two mentions are exactly what the anaphor route is for.
- Bind on the anaphor route without checking it, so the mis-categorisation is corrected by luck rather than by a test.

### Negative gold - spans that must produce NO claim

- 'is of the Vanguard family' is a design-level lineage fact and says nothing about the section's identity.

**Corpus:** NOT EXERCISABLE, with a wrinkle worth knowing: the producer already rails this at emission - a cluster whose quote cannot be found in the document is dropped before it is written. So this fixture is deliberately testing the CONSUMER against input that bypasses the producer, which is precisely the situation any fixture-driven test creates.

# Shape 2 - NAME_VARIANT - permanently raise-only, and the mark-vs-name collision

## `F2a-name-variant-obvious-but-still-not-automatic`

**Scope:** 2 (D-13.17: NAME_VARIANT raise-only permanently)  
**Refs:** D-13.17 (an authoritative NAME_VARIANT would rebuild the exact-normalized-name auto-merge lane on a new predicate); the name signal's ceiling at every layer

**Purpose.** Three spellings of one design mark in one document - hyphen, space, and closed up. The most obviously correct bind in the whole file, and the one that must never be automatic.

**Why it is hard.** Refusing this feels like refusing to do arithmetic, which is exactly why the rule has to be structural rather than a judgement call. A normalized-name equality is not a corroborating second signal; it is the name signal restated in stronger language. Authorise it and the merge path the whole redesign exists to delete is back, wearing a different predicate and immune to the cap that replaced it. The fixture also hides a second temptation: the three spellings sit at three different sites.

### Documents

**`digest-KK`** - aerial survey digest, source grade **B**, commercial survey vendor's monthly digest, dated 2025-05-08

```
REGIONAL SURVEY DIGEST - 08 May 2025

Redlow pumping station: TL-40 skids on the north apron (six).
Ashgate transfer yard: TL 40 skids on the yard hardstand (four).
Calder depot: TL40 skids under cover (count not established).
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (digest-KK) | TL-40 | `design` |  |
| `m2` (digest-KK) | TL 40 | `design` |  |
| `m3` (digest-KK) | TL40 | `design` |  |
| `m4` (digest-KK) | Redlow pumping station | `place` |  |
| `m5` (digest-KK) | Ashgate transfer yard | `place` |  |
| `m6` (digest-KK) | Calder depot | `place` |  |

### Hand-authored coreference clusters

**`kk-1`** (digest-KK) - category **`NAME_VARIANT`**, anchor `m1`, members `m2`, `m3`, bind truth **`correct`**

> Redlow pumping station: TL-40 skids on the north apron (six).

The bind is right about the design and the document never says so - the extractor is reading orthography. The quoted span is simply where the anchor was found; it licenses nothing.

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT throughout |
| geography | STATED for all three mentions - and DIFFERENT for each |
| designation | ABSENT |
| time | STATED as the digest's date (2025-05-08); no per-site collection dates |

### Required outcome (prose - choose your own mechanism and values)

No automatic bind, however cleanly the strings normalize - the category is a reading of orthography, not something the document asserts, and it stays a proposal for a human permanently. The pairs reach the analyst with the quote. Independently of the design question, the three sited groups are three different presences at three different places and must never become one: whatever happens to the design mentions, the equipment at Redlow, Ashgate and Calder stays three things. The 'count not established' entry is a stated unknown, not a zero and not a missing field.

### Tempting but wrong

- Auto-bind because normalization makes the three strings identical. That is the widest merge path in the system, it bypasses every cap, and it is precisely what a per-category policy exists to keep shut.
- Fuse the three sited groups because their design mentions merged, producing one presence at three places.
- Add the two stated figures into a single fleet count of ten, or read 'count not established' as zero.
- Treat the digest as three independent looks at one site because it has three lines.

### Negative gold - spans that must produce NO claim

- 'REGIONAL SURVEY DIGEST' is the publisher, not a source-independent second look at any of the three sites.
- '(count not established)' asserts a stated unknown - keep it, do not fill it.

**Corpus:** PARTIALLY EXERCISABLE. The raw variant material is real - the corpus carries casing and format drift for one designator inside a single document (verified in the S2 pass) - but no labelled cluster exists over it.

## `F2b-mark-vs-name-nothing-may-be-asserted`

**Scope:** 2 (D-13.17: NAME_VARIANT raise-only), 6 (the discriminator ladder)  
**Refs:** the containment doctrine: an extra WORD describes the same thing more fully; an extra MARK is a different thing; the ruling's required negative case: 'a mark-vs-name collision'; SPEC CORNER - see the note in this fixture's outcome

**Purpose.** A base design mark and a more specific mark of which it is a prefix, both fielded by the same operator, with a stated figure that the document explicitly refuses to attribute to either.

**Why it is hard.** A prefix relation is neither equality nor difference, and both of the confident readings are wrong. String similarity says 'the same'; a designation-conflict rule says 'different'. The document licenses neither, and it goes out of its way to say which mark the six sets are is unknown - so a system that resolves the identity in either direction will also, silently, attribute a real figure to the wrong thing.

### Documents

**`press-LL`** - trade press item, source grade **C**, trade press, recycles operator briefings, dated 2025-05-14

```
CALDONIA PLANT MONTHLY - 14 May 2025

Northern Grid Works fields both the TL-40 and the uprated TL-40/M across the northern scheme.
Six of the fleet are at Redlow; this item does not say which mark.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (press-LL) | TL-40 | `design` |  |
| `m2` (press-LL) | TL-40/M | `design` |  |
| `m3` (press-LL) | Northern Grid Works | `operator_org` |  |
| `m4` (press-LL) | Redlow | `place` |  |

### Hand-authored coreference clusters

**`ll-1`** (press-LL) - category **`NAME_VARIANT`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> Northern Grid Works fields both the TL-40 and the uprated TL-40/M across the northern scheme.

The extractor read the shared prefix as a spelling variant. The quoted span in fact says the operator fields BOTH, and calls one of them uprated.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED ('Northern Grid Works') - and the same for both marks |
| geography | STATED loosely ('at Redlow') for the six sets only |
| designation | STATED for both, and one is a prefix of the other |
| time | STATED as the item's date (2025-05-14) |

### Required outcome (prose - choose your own mechanism and values)

Nothing fuses and nothing is asserted in either direction. One designation being a prefix of a more specific one is not an equivalence, and it is not a stated distinction either - so the output must contain neither a merge nor a manufactured 'these are different systems' claim. Two designs survive. The six sets at Redlow cannot be attributed to either mark, and the document says so in its own words: that is a named gap ('which mark is unstated'), not a figure to be assigned to whichever mark is better attested. SPEC CORNER worth flagging to the other hands: the category with no gate is the one this collision arrives under, so there is no gate here to fail - the protection has to come from the ladder and from the caps, not from a licensing check.

### Tempting but wrong

- Fuse because one string contains the other. Containment is the right instinct for an extra descriptive word and the wrong one for an extra mark, and only a declared rule can tell them apart.
- Treat the differing designations as a hard, transitive prohibition, so every legitimate cluster mentioning the base mark is split by a trade-press sentence.
- Attribute the six sets to the base mark because it is the more common string in the graph - the figure belongs to whichever mark the source meant, and the source declined to say.
- Record the uprated mark's second rail on the base design, which is how a design node acquires a spec no source gave it.

### Negative gold - spans that must produce NO claim

- 'across the northern scheme' is an area of responsibility, not a site.
- 'this item does not say which mark' is a stated limit of the source - keep it as a gap, not as silence.

**Corpus:** EXERCISABLE IN KIND, and abundantly - richer than the S2 pass suggested. The corpus carries several one-line prefix collisions between a shorter mark and a longer one (including a pair where the shorter is a literal prefix of the longer and the document then states their distinctness in its own voice), plus a family whose base mark, a suffixed mark and a hyphenation variant appear across documents. The shipped containment knob states the doctrine in exactly these terms. What is NOT exercisable is the labelled bind: the pair never arrives as a cluster, so the gate is never offered the case.

## `F2c-mark-parenthetical-passes-the-marker-gate`

**Scope:** 2 (D-13.17 auto-bind policy), 3 (the decline path as second line of defence)  
**Refs:** D-13.17 (a parenthetical wrapping one form counts as an equivalence marker); the containment doctrine (WORD vs MARK); C3 / D-13.18 (the decline path)

**Purpose.** The same mark collision, arriving as a stated equivalence - and passing every conjunct of the deterministic gate: verbatim span, both surface forms, a parenthetical marker, good-grade source.

**Why it is hard.** This is the sharpest fixture in the file, because the gate as specified PASSES and the bind is still wrong. A parenthetical is an equivalence marker when it wraps another name for the same thing and a narrowing qualifier when it wraps a more specific mark, and the two are indistinguishable without a rule about what the parenthetical contains. It is also the fixture that shows why a second line of defence is needed: the same register sentence states different rail counts for the two marks, so a system that binds here has an intra-cluster attribute conflict available to catch what the gate missed.

### Documents

**`register-LM`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-05-22

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 22/2025
Compiled 22 May 2025

Ashgate transfer yard: the TL-40 (TL-40/M) sets on the yard hardstand are recorded, operator Northern Grid Works.
Four skids are recorded. The uprated mark carries a second canister rail; the base set carries one.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-LM) | TL-40 | `design` |  |
| `m2` (register-LM) | TL-40/M | `design` |  |
| `m3` (register-LM) | Ashgate transfer yard | `place` |  |
| `m4` (register-LM) | Northern Grid Works | `operator_org` |  |

### Hand-authored coreference clusters

**`lm-1`** (register-LM) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> the TL-40 (TL-40/M) sets on the yard hardstand are recorded

Passes verbatim, both-surface-forms and parenthetical-marker. The parenthetical narrows the reference to a mark; it does not equate two names.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED ('Northern Grid Works') |
| geography | STATED ('Ashgate transfer yard', 'yard hardstand') |
| designation | STATED for both, one a prefix of the other |
| time | STATED as the compilation date (2025-05-22) |

### Required outcome (prose - choose your own mechanism and values)

The bind must not stand. A parenthetical earns its status as an equivalence marker from what it contains: another name for the same thing, not a narrowing mark of it - so the marker vocabulary has to be able to refuse this shape, and if it cannot, the deterministic gate is passing on the strength of punctuation. Two designs survive; the four skids belong to whichever mark the register meant and it does not say. If the bind is not refused at the gate, the second line of defence must catch it: the same sentence gives the two marks different rail counts, and a grouping whose own members contradict each other on a design-level attribute must be declined and raised rather than kept. Both routes are acceptable; keeping the bind is not.

### Tempting but wrong

- Accept any parenthetical as an equivalence marker. The gate then passes on typography, and every 'base mark (specific mark)' rendering in the corpus becomes an automatic uncapped merge.
- Bind, and store the two rail counts as one design's attribute history without noticing they conflict - the conflict becomes invisible if only the first value recorded is kept.
- Refuse, and also throw away the register's real content (which marks are at the yard, and how many skids).
- Resolve the ambiguity by picking the more specific mark because it is more informative.

### Negative gold - spans that must produce NO claim

- 'Four skids are recorded' is a sourced figure whose subject is ambiguous between the two marks - keep the figure and the ambiguity together.

**Corpus:** PARTIALLY EXERCISABLE, and the corpus is more dangerous here than I first wrote. It contains parentheticals that state a real equivalence between two marks AND a parenthetical that merely lists four marks of one family - so both the licensing and the non-licensing use of the same punctuation are live in the frozen data, and a marker vocabulary that accepts any parenthetical will bind the second kind. The specific input this fixture authors - a narrowing mark inside a parenthetical on the SUBJECT design - is not in the corpus, and cannot be conjured without a re-extract that may or may not produce it.

## `F2d-name-variant-across-two-kinds-of-thing`

**Scope:** 2 (D-13.17), 9 (G19 cross-type non-fusion)  
**Refs:** G19 (cross-type non-fusion, both phases); spine/13 sec.3 (collapse happens only within a layer)

**Purpose.** A place name reused in a company name, bound as a spelling variant - the commonest naming pattern there is, and a cross-type fusion if it lands.

**Why it is hard.** The two strings really do share their distinctive token, and the sentence puts them in the same clause, so every lexical signal fires. The type difference is the only thing standing between the graph and a node that is simultaneously a site and a company - and the type of one mention is exactly what a name-similarity route never consults. The document's real content is also a relation that may have nowhere to live.

### Documents

**`register-MM`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-05-20

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 21/2025
Compiled 20 May 2025

Redlow pumping station is operated by Redlow Works Ltd under contract to Northern Grid Works.
Transfer plant on site: TL-40, six skids.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-MM) | Redlow pumping station | `place` |  |
| `m2` (register-MM) | Redlow Works Ltd | `operator_org` |  |
| `m3` (register-MM) | Northern Grid Works | `operator_org` |  |
| `m4` (register-MM) | TL-40 | `design` |  |

### Hand-authored coreference clusters

**`mm-1`** (register-MM) - category **`NAME_VARIANT`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> Redlow pumping station is operated by Redlow Works Ltd under contract to Northern Grid Works.

A place and an organisation, bound on a shared token. The quoted span states a custody relation between them, which is the strongest possible evidence that they are two different things.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED twice, and they are two different organisations in two different roles |
| geography | STATED ('Redlow pumping station') |
| designation | ABSENT |
| time | STATED as the compilation date (2025-05-20) |

### Required outcome (prose - choose your own mechanism and values)

Refused on type, by every route including any route through a name or alias table: a place and an organisation are different kinds of thing and no amount of string agreement makes them one. Both survive. The sentence's real content is a two-step custody chain - a site operated by a contractor under contract to another organisation - and if there is no lane for that relation, the absence must be reported as a gap rather than flattened into 'the site's operator is the contractor' or 'the contractor is the operator of record'. A sourced relation with nowhere to go is the same hazard as an unsourced relation with a lane: something else fills the slot.

### Tempting but wrong

- Fuse on the shared distinctive token, giving the graph one node that is both a station and a company.
- Fuse because one name contains the other.
- Record the contractor as the site's operator of record, quietly promoting a contracted operator over the named principal.
- Drop the custody relation because it has no lane, so the document's actual content vanishes and only the identity error remains.

### Negative gold - spans that must produce NO claim

- 'under contract to' is a commercial relation, not an identity and not a chain of ownership of the plant.

**Corpus:** NOT VERIFIED in this pass. Place names reused inside organisation names do occur in the corpus's commercial material, but I did not confirm a pair that a name route would actually join, so treat this fixture as authored rather than abstracted.

# Shape 3 - UNAMBIGUOUS_ANAPHOR - the gate must be positive, and unknown counts as compatible

## `F3a-anaphor-positive-gate-passes`

**Scope:** 2 (D-13.17: the positive anaphor gate)  
**Refs:** D-13.17 (type-unique antecedent); the positive reformulation: a named, declared, ontology-typed antecedent, exactly one type-compatible mention; the fragmentation lever that anaphora carry

**Purpose.** The reference anaphor: one named, declared, typed body in the document, one pronoun-like mention referring to it, and no other candidate of a compatible kind anywhere in the text.

**Why it is hard.** It is the control for the three failures below, and it carries the argument for why refusing anaphora wholesale is not the safe option: the facts hang on the anaphoric mention, so an unbound anaphor becomes a nameless body whose only content is six skids on an apron - self-inflicted sparsity that then gets reported as a collection gap, mis-tasking the analyst.

### Documents

**`bulletin-NN`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-05-27

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 12/2025
Dated: 27 May 2025

2 Transfer Section is established at Redlow pumping station with effect from 27 May 2025.
The section holds six TL-40 skids on the north apron.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-NN) | 2 Transfer Section | `formation` | named, declared, typed - the only body-kind mention in the document |
| `m2` (bulletin-NN) | The section | `formation` | the anaphor |
| `m3` (bulletin-NN) | Redlow pumping station | `place` |  |
| `m4` (bulletin-NN) | TL-40 | `design` |  |

### Hand-authored coreference clusters

**`nn-1`** (bulletin-NN) - category **`UNAMBIGUOUS_ANAPHOR`**, anchor `m1`, members `m2`, bind truth **`correct`**

> The section holds six TL-40 skids on the north apron.

Exactly one named, declared, type-compatible antecedent exists in the document, and no other mention of a body-like kind - including none of unknown kind.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity (the operator's own establishment bulletin) |
| geography | STATED ('Redlow pumping station', 'the north apron') |
| designation | STATED ('2 Transfer Section') |
| time | STATED as an effective date (2025-05-27) |

### Required outcome (prose - choose your own mechanism and values)

The bind is automatic and the gate must be satisfied by finding something, not by failing to find anything: there is a named, declared, type-compatible antecedent, and exactly one candidate it could mean. The facts carried by the anaphoric mention attach to the named section. The stated figure is a sourced count of what the section holds - it is not a count of mentions, reports or documents. The effective date of an establishment is not an observation date for the skids.

### Tempting but wrong

- Refuse anaphora as a class 'to be safe', which manufactures a nameless body holding six skids and then reports our own grain choice as missing coverage.
- Bind the anaphor to the station because the place is the nearest preceding noun.
- Bind on the strength of the shared word 'section' between the two surface forms - that is the name signal, not the anaphor gate, and it will happily bind two different sections.
- Read the effective date as the date the six skids were seen.

### Negative gold - spans that must produce NO claim

- 'with effect from' marks an establishment date, not a sighting.

**Corpus:** EXERCISABLE in substance. One corpus document uses a bare definite noun phrase five times for a body named exactly once at the top, with the only nearby distractors non-coreferent by kind - the cleanest positive case for the anaphor gate anywhere in the corpus. The gate's own input (a mention inventory) still only exists once the producer runs, so the annotation half remains authored.

## `F3b-anaphor-two-candidates-of-the-same-kind`

**Scope:** 2 (D-13.17: the positive anaphor gate)  
**Refs:** D-13.17 (type-unique antecedent); the ruling's required negative case: 'two candidate antecedents of the same type'; never a silent pick

**Purpose.** One document, two named bodies of the same kind, then a bare anaphor - and a real fact attached to it that belongs to exactly one of them.

**Why it is hard.** Both candidates are equally good: same kind, same operator, same sentence, one line earlier. Any tie-break an implementation reaches for - first mentioned, nearest, better evidenced - produces a confident attribution with no evidence behind it, and the error is invisible afterwards because the output looks exactly like a correct bind.

### Documents

**`bulletin-PP`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-06-03

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 14/2025
Dated: 03 June 2025

2 Transfer Section and 5 Transfer Section are both re-roled with effect from 03 June 2025.
The section will take over the Ashgate transfer yard.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-PP) | 2 Transfer Section | `formation` |  |
| `m2` (bulletin-PP) | 5 Transfer Section | `formation` |  |
| `m3` (bulletin-PP) | The section | `formation` | the anaphor |
| `m4` (bulletin-PP) | Ashgate transfer yard | `place` |  |

### Hand-authored coreference clusters

**`pp-1`** (bulletin-PP) - category **`UNAMBIGUOUS_ANAPHOR`**, anchor `m1`, members `m3`, bind truth **`over_bound`**

> The section will take over the Ashgate transfer yard.

The extractor bound the anaphor to the first-mentioned candidate. Two type-compatible named antecedents exist, so the anaphor is not unambiguous and the category's own condition is unmet.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity (one operator's own bulletin) |
| geography | STATED ('the Ashgate transfer yard') |
| designation | STATED for both candidates, and they differ |
| time | STATED as an effective date (2025-06-03) |

### Required outcome (prose - choose your own mechanism and values)

The gate fails and no bind is made. The Ashgate takeover is a real sourced fact whose subject is one of two named bodies, and the honest output records it against an unresolved subject with the ambiguity named - two candidates, which one unstated, and what would settle it. Never a pick, and never a quiet drop: two candidates means two attributions or one plus an explicitly named gap.

### Tempting but wrong

- Bind to the first-mentioned or nearest candidate. Both are properties of the prose, not evidence about the world.
- Bind to whichever body already has more evidence in the graph, which makes well-attested bodies absorb facts belonging to their neighbours.
- Drop the Ashgate fact for want of a subject, losing a sourced statement about the order of battle.
- Mint a third body for 'the section', so the graph gains an establishment no source names.

### Negative gold - spans that must produce NO claim

- 'are both re-roled' is a change of role, not a change of location for either body.

**Corpus:** EXERCISABLE at design/system level - corrected from my first assessment. One corpus document offers FOUR same-kind antecedents before a bare referring expression, and adjacency favours the WRONG one (the phrase sits immediately after a distractor and denotes something else); another has two referring expressions in a single sentence pointing at two different referents. So the ambiguity case is real and severe in the prose. It remains not exercisable at BODY level, where the corpus has one numbered body in 52 documents.

## `F3c-anaphor-second-candidate-is-unknown-typed`

**Scope:** 2 (D-13.17: the positive anaphor gate)  
**Refs:** the positive reformulation: unknown-typed endpoints COUNT as type-compatible, so a second undeclared mention fails the gate; the ruling's requirement: an unknown-typed second mention must fail the gate; an absence test fails open exactly when the extractor under-reaches

**Purpose.** One named, declared body; one anaphor; and between them a mention the extractor could not type at all. The gate must treat the untyped mention as a candidate and therefore fail.

**Why it is hard.** This is the fixture the gate is most likely to pass wrongly, and the reason is structural: an implementation that asks 'is there a second mention of the SAME declared type?' finds none, because the second candidate has no declared type. So the gate is weakest precisely when the extractor is weakest - the failure mode is anti-correlated with safety. There is a decoy too: the anaphor's surface form echoes the antecedent's own words, which invites binding on the name instead of on the gate.

### Documents

**`bulletin-QQ`** - operator works bulletin, source grade **B**, operator of the asset (interested party), dated 2025-06-10

```
NORTHERN GRID WORKS - WORKS BULLETIN 31/2025
Dated: 10 June 2025

2 Transfer Section completed the changeover at Redlow pumping station on 10 June 2025.
The Tarnholt party assisted.
The section will remain at Redlow through the summer works.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-QQ) | 2 Transfer Section | `formation` |  |
| `m2` (bulletin-QQ) | The Tarnholt party | `unknown` | the extractor could not determine what kind of body this is - it is undeclared, not absent |
| `m3` (bulletin-QQ) | The section | `formation` | the anaphor |
| `m4` (bulletin-QQ) | Redlow pumping station | `place` |  |

### Hand-authored coreference clusters

**`qq-1`** (bulletin-QQ) - category **`UNAMBIGUOUS_ANAPHOR`**, anchor `m1`, members `m3`, bind truth **`over_bound`**

> The section will remain at Redlow through the summer works.

A second mention of unknown kind sits between antecedent and anaphor. An unknown kind is compatible with every kind, so a second candidate exists and the anaphor is not type-unique.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity |
| geography | STATED ('Redlow pumping station') |
| designation | STATED for the antecedent only |
| time | STATED exactly for the changeover (2025-06-10) |

### Required outcome (prose - choose your own mechanism and values)

The gate must fail. A mention whose kind the extractor did not determine is a candidate, not a non-candidate: unknown is compatible with everything, so the presence of one untyped body-like mention is enough to make the anaphor ambiguous. No bind; the pair reaches an analyst with the quote; the summer-works residence is not attributed. The general principle the fixture exists to protect: a gate whose condition is 'nothing else was found' passes most easily when the extractor found least, so the condition has to be stated positively - one named, declared, compatible antecedent and no other candidate, counting untyped mentions among the candidates.

### Tempting but wrong

- Skip untyped mentions when counting candidates, so the gate passes exactly when extraction was weakest.
- Bind because the anaphor's words ('the section') echo the antecedent's name. That is a string match dressed as discourse, and in F3b the same reasoning binds to the wrong body.
- Type the Tarnholt party by guessing from its name so the ambiguity disappears - an invented type that then licenses a bind.
- Refuse the bind and also drop the changeover fact, which is well-sourced and belongs to the named section.

### Negative gold - spans that must produce NO claim

- 'The Tarnholt party assisted' names an actor without saying what kind of body it is - record the mention, not a guess at its kind.

**Corpus:** NOT EXERCISABLE. It needs a mention the extractor declined to type, which is an extraction outcome, not a property of the source text - so the corpus cannot supply it at all, whatever it contains.

## `F3d-anaphor-with-no-named-antecedent-at-all`

**Scope:** 2 (D-13.17: the positive anaphor gate), 7 (under-determined + named gap)  
**Refs:** the positive gate (a NAMED, declared antecedent must exist); D-13.8 (absent discriminator: under-individuated + named gap, never fabricated); D-13.13 (never reify what no source names)

**Purpose.** A document whose only actor is a bare descriptor - and which states, in its own voice, that neither the body nor its parent is named anywhere.

**Why it is hard.** There is nothing to bind to inside the document, so the pressure moves outward: elsewhere in the graph there is exactly one section that fits, and 'the only candidate' is very easy to mistake for 'the unambiguous candidate'. It is not - uniqueness in our data is an artefact of our coverage. The second temptation is the opposite error: dropping a real, dated, sourced delivery because its subject has no name.

### Documents

**`press-RR`** - trade press item, source grade **C**, trade press, no stake, dated 2025-06-17

```
CALDONIA PLANT MONTHLY - 17 June 2025

The section responsible for the Tarnholt transfer plant took delivery of two further skids this month.
Neither the section nor its parent directorate is named in the works programme.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (press-RR) | The section | `formation` | a bare descriptor; no name anywhere in the document |
| `m2` (press-RR) | its parent directorate | `unknown` | also unnamed, and the document says so explicitly |
| `m3` (press-RR) | Tarnholt | `place` |  |

### Hand-authored coreference clusters

**`rr-1`** (press-RR) - category **`UNAMBIGUOUS_ANAPHOR`**, anchor `m1`, members *(none - single-member)*, bind truth **`under_bound`**

> The section responsible for the Tarnholt transfer plant took delivery of two further skids this month.

A single-member cluster: the extractor found an anaphoric subject and no antecedent to attach it to, because the document contains none. Correct behaviour by the producer; the question is what the consumer does with it.

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT, and STATED ABSENT ('neither the section nor its parent directorate is named') |
| geography | STATED ('the Tarnholt transfer plant') |
| designation | ABSENT, and STATED ABSENT |
| time | STATED loosely ('this month'), publication 2025-06-17 |

### Required outcome (prose - choose your own mechanism and values)

No bind to any named body, inside this document or outside it. The honest output is an under-determined holder carrying a dated, sourced delivery of two skids at Tarnholt, explicitly flagged as unnamed, plus the gap the document itself supplies - and a stated absence is a stronger fact than a missing field, so 'neither the section nor its parent is named in the works programme' is worth recording as evidence about where the coverage stops. It must never be attached to the one section elsewhere in the graph that would fit, and it must not be dropped for want of a subject. A single-member cluster licenses nothing on its own - in particular it can never license a move.

### Tempting but wrong

- Attribute the delivery to the only section in the graph that fits. This is the anaphor fallacy at graph scale: being the only candidate we hold is a fact about our collection, not about the world.
- Drop the delivery because there is no subject, losing a real sourced figure.
- Mint a body called 'the section' and treat it as an establishment, so an unnamed actor becomes a node with a name no source used.
- Read the document's statement that nothing is named as an absence of information, rather than as the information it is.

### Negative gold - spans that must produce NO claim

- 'this month' is not a date; it bounds one to the publication month at best.
- 'two further skids' is a delivery increment, not a total holding.

**Corpus:** EXERCISABLE in substance, better than expected. One corpus document uses a referring expression for an organisation it never names at all, and the corpus supplies the stronger version of the fixture's second half - documents that STATE the absence of identity, including one stating it across a whole pass history and one stating a non-disclosure policy, so the 'this will not close' reason is real data rather than an authored flourish.

# Shape 4 - The decline path - a cluster that passes every gate and must still be given up

## `F4a-decline-on-an-attribute-conflict`

**Scope:** 3 (D-13.18: the rebuild may DECLINE a grouping)  
**Refs:** D-13.18 (the referent is evidence about a grouping, never the address; no atom splits, the grouping declines); C3 (the conflict check must read every stated value, not the first one recorded); the ruling: the decline path can only fire on bad input

**Purpose.** An impeccably licensed equivalence - verbatim span, both surface forms, a marker, a good-grade source - between two mentions that carry different stated operators. The register is simply wrong.

**Why it is hard.** Everything upstream passes, so this is the fixture that decides whether an automatic bind is reversible. If the grouping cannot be given up, one register sentence permanently fuses two operators' installations, which is the single most damaging over-merge class for an operator-scoped map. And the conflict is easy to make invisible: if only the first operator value encountered is kept and the second is discarded as a duplicate attribute, the merged thing looks perfectly consistent and the fixture passes vacuously.

### Documents

**`register-SS`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-06-24

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 26/2025
Compiled 24 June 2025

Ashgate transfer yard, bay 1: the north bay set is recorded, operator Northern Grid Works.
Ashgate transfer yard, bay 4: the south bay set is recorded, operator Water Authority.
The north bay set, also carried in this register as the south bay set, is a single Vanguard-pattern installation split across two bays.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-SS) | the north bay set | `presence` | carries operator Northern Grid Works |
| `m2` (register-SS) | the south bay set | `presence` | carries operator Water Authority |
| `m3` (register-SS) | Ashgate transfer yard | `place` |  |
| `m4` (register-SS) | Northern Grid Works | `operator_org` |  |
| `m5` (register-SS) | Water Authority | `operator_org` |  |

### Hand-authored coreference clusters

**`ss-1`** (register-SS) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> The north bay set, also carried in this register as the south bay set, is a single Vanguard-pattern installation split across two bays.

Every conjunct of the gate passes and the grouping is still wrong: its two members are stated to be held by two different operators. The bind is well-licensed evidence about a grouping - and evidence can be outweighed.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both members - and they DIFFER (the conflict) |
| geography | STATED, and the same site for both ('Ashgate transfer yard', two bays) |
| designation | ABSENT - no body is named |
| time | STATED as the compilation date (2025-06-24); the entries share it |

### Required outcome (prose - choose your own mechanism and values)

The grouping is declined. The two mentions fall back to being two things, the pair is raised for an analyst with the licensing quote and the reason - a stated operator conflict inside a proposed identity - and nothing is deleted: the register's equivalence statement survives as evidence that was considered and outweighed, which is what makes an automatic bind a proposal rather than a fact. The decline depends on both stated operator values being retained; a store that keeps the first and drops the second cannot see the conflict at all, and this fixture is the test of that.

### Tempting but wrong

- Bind because every gate passed and treat the result as settled. An automatic bind that no later check can reverse makes intra-document over-merge permanent - the one outcome the design calls disqualifying.
- Keep the first operator value and discard the second as a duplicate attribute, so the conflict never becomes visible and the merged installation looks clean.
- Resolve the conflict by preferring the operator that appears more often in the graph, or the one whose bulletin is better graded.
- Delete the losing mention, or delete the equivalence claim, so the audit trail no longer shows that a bad bind was proposed and rejected.
- Split the underlying claim atoms as well. Nothing about the mentions was wrong; it is the grouping that fails.

### Negative gold - spans that must produce NO claim

- 'is recorded' is the register's own verb - two bay entries in one register are not two independent looks.
- 'split across two bays' is the register's interpretation of what it holds, not an observation.

**Corpus:** NOT EXERCISABLE. The decline path needs a grouping to give up, and the frozen data contains no groupings.

## `F4b-decline-on-a-relationship-conflict`

**Scope:** 3 (D-13.18 / C3: the decline fires on relationship conflicts too), 8 (the relationship wall)  
**Refs:** C3 (relationship conflicts use the same overlapping-time test the wall uses, under C1's site-kind rule); C10 (a single source licenses a move only when it authoritatively co-refers its own mentions)

**Purpose.** The same shape with the conflict in a relation rather than an attribute: one register binds two bodies and states each of them at a different station of the same kind, over one overlapping season.

**Why it is hard.** A conflict checker that only looks at attributes passes this cluster silently, and the harm is worse than a bad merge: two basings of one body at overlapping times is exactly the input a before-and-after reading turns into a move. So the same defect that fails to decline also fabricates a relocation, from a source that never described one. The dates overlap rather than succeed each other, which is the only thing separating this from a legitimate relocation.

### Documents

**`register-TT`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-07-01

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 27/2025
Compiled 01 July 2025

2 Transfer Section is established at Redlow pumping station for the 2025 season (April to September).
The Calder section is established at Calder pumping station for the 2025 season (April to September).
2 Transfer Section, also carried in this register as the Calder section, is one establishment.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-TT) | 2 Transfer Section | `formation` | stated at Redlow pumping station, April to September 2025 |
| `m2` (register-TT) | the Calder section | `formation` | stated at Calder pumping station, April to September 2025 |
| `m3` (register-TT) | Redlow pumping station | `place` |  |
| `m4` (register-TT) | Calder pumping station | `place` |  |

### Hand-authored coreference clusters

**`tt-1`** (register-TT) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`over_bound`**

> 2 Transfer Section, also carried in this register as the Calder section, is one establishment.

Gate-clean. The conflict is in the two stated basings: two stations of the same kind, one overlapping season, one claimed body.

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT on both mentions - the register does not state one |
| geography | STATED for both, DIFFERENT places, SAME kind of place, OVERLAPPING period |
| designation | STATED for one member ('2 Transfer Section'), a descriptor for the other |
| time | STATED as a season on both ('April to September'), i.e. overlapping, not successive |

### Required outcome (prose - choose your own mechanism and values)

The grouping declines on the relationship conflict, using the same overlapping-time test the hard wall uses, and for the same reason: one body cannot be established at two stations of the same kind over one period on this source's own account. The two bodies stand apart, the pair is raised with an analyst-visible reason naming which relation conflicted, and no move is drawn between the two stations - nothing states a move, and overlapping periods are not a sequence. Note what makes the kinds matter: two stations of the same kind conflict, whereas a station and a forward standing would be two valid concurrent basings, which is the next fixture.

### Tempting but wrong

- Check attributes only, so a relationship conflict binds silently and the wall and the decline drift apart into two different notions of conflict.
- Read the two basings as a before and an after and draw a relocation - fabricating a move out of an overlap, and removing the analyst from a decision no source made.
- Keep the bind and drop one of the two basings as a duplicate, which is the same fabrication with the evidence hidden.
- Wall the pair without saying why: an invisible refusal is indistinguishable from a pair that was never considered.

### Negative gold - spans that must produce NO claim

- '(April to September)' bounds a season; it is not two separate dated observations.
- The register's own cross-reference is a claim about identity, not a claim about either basing.

**Corpus:** NOT EXERCISABLE, twice over. There are no clusters to decline, and the relationship half has no input either: across 52 documents there is exactly one stated body-at-site basing and it belongs to an off-subject decoy in another country (verified in the S2 pass by two independent routes - a text search, and the answer key annotating every basing as derived).

## `F4c-non-critical-differences-must-not-decline`

**Scope:** 3 (D-13.18: what is NOT a conflict), C1 (a differing site kind is not a conflict)  
**Refs:** C1 (the wall fires within one site kind; a differing kind is not a conflict, so a body at a station and a forward standing is two valid basings); D-13.8 (absence is unknown, never a conflict)

**Purpose.** The mirror of F4a and F4b: a well-licensed grouping whose members differ on a site KIND, on observation dates and on counts - none of which is a conflict. It must survive.

**Why it is hard.** A decline path tuned by fear fires here, and the damage is symmetrical to over-merging: an establishment that legitimately holds plant at its station and at a summer forward standing gets split, both halves lose half their evidence, and the fragmentation is then read as genuine evidential uncertainty. Two dated, differing counts at two places are two facts, not a contradiction and not a drawdown.

### Documents

**`bulletin-UU`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-07-08

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 17/2025
Dated: 08 July 2025

2 Transfer Section is established at Redlow pumping station and, for the summer works, at the Tarnholt forward standing.
2 Transfer Section, also carried as the Redlow section in the works programme, is one establishment.
Plant held: six skids at Redlow (recorded 12 June 2025), four at Tarnholt (recorded 02 July 2025).
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-UU) | 2 Transfer Section | `formation` |  |
| `m2` (bulletin-UU) | the Redlow section | `formation` |  |
| `m3` (bulletin-UU) | Redlow pumping station | `place` |  |
| `m4` (bulletin-UU) | the Tarnholt forward standing | `place` |  |

### Hand-authored coreference clusters

**`uu-1`** (bulletin-UU) - category **`EXPLICIT_EQUIVALENCE`**, anchor `m1`, members `m2`, bind truth **`correct`**

> 2 Transfer Section, also carried as the Redlow section in the works programme, is one establishment.

Gate-clean AND true. The differences between the members are of the kinds that are not conflicts.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity, and the same for both |
| geography | STATED for both - two places of DIFFERENT kinds, concurrently |
| designation | STATED ('2 Transfer Section') |
| time | STATED as two different recording dates for the two holdings (2025-06-12, 2025-07-02) |

### Required outcome (prose - choose your own mechanism and values)

The grouping stands. A body established at a station and, for the summer, at a forward standing has two valid concurrent basings; differing kinds of place are not a conflict, differing observation dates are not a conflict, and two figures for two places are two sourced figures. No move is drawn, neither basing retires the other, and each figure keeps its own date and place. The rule this protects: a decline path that fires on any difference at all is worse than none, because it shatters exactly the identities the stage exists to earn.

### Tempting but wrong

- Decline on any difference between members, splitting a correct identity and then reporting the split as genuine uncertainty.
- Read six skids in June and four in July as a change in one holding and draw a drawdown or a move.
- Add the two figures into a holding of ten, which no source states.
- Pick one of the two places as 'the' basing and retire the other, deleting a sourced basing and the reason it existed.

### Negative gold - spans that must produce NO claim

- 'for the summer works' bounds a basing in time; it does not make the basing provisional or unsourced.
- '(recorded 12 June 2025)' dates the figure, not the establishment.

**Corpus:** NOT EXERCISABLE. Needs one body stated at two places of different kinds concurrently; no corpus document places one body at two sites at all.

# Shape 5 - The co-location trap - two instances of one design at one site under one operator

## `F5a-co-location-presence-merges-formation-does-not`

**Scope:** 7 (the co-location cap, G16)  
**Refs:** D-13.14 / G16 (shared design+site+operator: presence merge fine, formation merge not fused); C2 (G16 asserts on the observable outcome: no confirmed formation merge, node count preserved, no drawn relocation); the honest analyst-facing answer shape: presence confirmed, body count unresolved, coverage needed

**Purpose.** Two individuated groups of the same design at one station, under one operator, reported by two unrelated vendors, with no body named by either. The shape a real site produces constantly and this corpus never does.

**Why it is hard.** Every discriminator the system holds agrees - design, site, operator - and agreement on shared properties is not evidence of individual identity: a station can host two sections of the same kind. The two errors available are opposite and both look like answers: fuse into one body and undercount the order of battle, or assert two bodies from two reports and invent one. The honest output is the one that names what it does not know, and it is also the least satisfying to display.

### Documents

**`survey-VV`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-07-11

```
AERIAL SURVEY EXTRACT - REDLOW PUMPING STATION
Collected 11 July 2025, single pass, 0.5 m

Six TL-40 skids are visible on the north apron in a fan arrangement, within the Northern Grid Works station boundary.

No markings, signage, section titles or vehicle numbers are legible at this ground sample distance.
```

**`survey-WW`** - aerial survey extract, source grade **B**, a second, unrelated commercial survey vendor, dated 2025-07-14

```
AERIAL SURVEY EXTRACT - REDLOW PUMPING STATION, EAST APRON
Collected 14 July 2025, own pass, 0.4 m

Four TL-40 skids are visible on prepared pads on the east apron, some 900 m from the north apron across the station perimeter road, within the Northern Grid Works station boundary.

No markings or section titles are legible. This pass did not cover the north apron.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (survey-VV) | Six TL-40 skids (north apron) | `presence` |  |
| `m2` (survey-VV) | Redlow pumping station | `place` |  |
| `m3` (survey-VV) | Northern Grid Works | `operator_org` |  |
| `m4` (survey-WW) | Four TL-40 skids (east apron) | `presence` |  |
| `m5` (survey-WW) | Redlow pumping station, east apron | `place` |  |
| `m6` (survey-WW) | Northern Grid Works | `operator_org` |  |

### Coreference

No coref cluster is involved: the two reports are in two documents, so nothing is doc-local here. This fixture is the cross-document half - it exists to be judged on discriminators alone.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED and IDENTICAL in both reports |
| geography | STATED - one station, two different aprons ~900 m apart |
| designation | ABSENT in both, and STATED ABSENT ('no section titles legible') |
| time | STATED exactly (2025-07-11 and 2025-07-14), three days apart |

### Required outcome (prose - choose your own mechanism and values)

A presence-level merge is acceptable and expected: 'transfer plant of this design, held by this operator, at this station' is one fact two vendors independently saw. What must not happen is a body-level confirmation - no source names a body, and confirming one needs a body-level discriminator that no source supplies. No move is drawn between the two aprons: a second location inside one station perimeter is not a relocation, and neither vendor describes one. The number of bodies at the station is unresolved and must be reported as such - not one, not two - in the shape 'plant present at this station on these dates; body count unresolved, one or two candidates; body-title coverage needed'. Both stated figures survive with their own dates and aprons; a combined total is a derivation, not a sourced figure, and it must carry both premises and the possibility that the two passes overlap - the second vendor says its pass did not cover the north apron, which is what makes the figures additive at all rather than two looks at one group.

### Tempting but wrong

- Confirm one body because design, site and operator all agree. This is the trap itself: shared properties are recall signals, and a body-level identity has to be earned on something that individuates bodies.
- Report 'one section at Redlow' as an order-of-battle line, which undercounts the adversary - the harmful direction for this mission.
- Report 'two sections at Redlow' because there are two groups. No source states a body at all, let alone two.
- Draw a move from the north apron to the east apron because the later report is at a different apron.
- Delete or downgrade the gap that records the body count as unresolved once the second report arrives - a second sighting does not resolve an identity it does not name.
- Treat the two vendors as one source because both are commercial survey vendors, so the presence never confirms either.

### Negative gold - spans that must produce NO claim

- 'No markings, signage, section titles or vehicle numbers are legible' is a stated absence of identifiers - strong evidence about coverage, and not a body-level discriminator.
- 'This pass did not cover the north apron' bounds the second report's scope; it is not evidence that the north apron group had gone.

**Corpus:** NOT EXERCISABLE, and this is the corpus's largest structural hole - verified twice now. There are no two individuated same-kind bodies anywhere in the frozen data; the nearest approach is a cardinality without individuation (a single claim carrying a quantity of bodies, not two referents). The co-location cap therefore has no corpus input at all.

## `F5b-co-location-and-the-relocation-it-would-fabricate`

**Scope:** 7 (the co-location cap, G16's three absences)  
**Refs:** G16 as amended (no confirmed formation merge; node count preserved; NO drawn relocation; no Known-Gap deletion and no insufficient-to-stale transition on the retired edge); D-13.14 (this cap is anti-fabrication machinery, not order-of-battle hygiene); C10 (a bare single-member instance never licenses a move)

**Purpose.** F5a plus a third report, three weeks later, putting the same design and operator at a different site. This is the harm chain the co-location cap exists to prevent, with every link live.

**Why it is hard.** The three-report set is where an identity error stops being a graph-tidiness matter. If the two Redlow groups were fused into one body, the Tarnholt report becomes that body's 'after', a functional basing relation replaces the earlier one, a move nobody reported is drawn, the pair leaves the analyst's queue because it now looks settled, and the honest gap that recorded the unresolved identity is deleted as stale. Every step follows mechanically from the first, and each step individually looks like progress.

### Documents

**`survey-VV`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-07-11

```
AERIAL SURVEY EXTRACT - REDLOW PUMPING STATION
Collected 11 July 2025, single pass, 0.5 m

Six TL-40 skids are visible on the north apron in a fan arrangement, within the Northern Grid Works station boundary.

No markings, signage, section titles or vehicle numbers are legible at this ground sample distance.
```

**`survey-WW`** - aerial survey extract, source grade **B**, a second, unrelated commercial survey vendor, dated 2025-07-14

```
AERIAL SURVEY EXTRACT - REDLOW PUMPING STATION, EAST APRON
Collected 14 July 2025, own pass, 0.4 m

Four TL-40 skids are visible on prepared pads on the east apron, some 900 m from the north apron across the station perimeter road, within the Northern Grid Works station boundary.

No markings or section titles are legible. This pass did not cover the north apron.
```

**`survey-XX`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-08-02

```
AERIAL SURVEY EXTRACT - TARNHOLT FORWARD STANDING
Collected 02 August 2025, single pass, 0.5 m

Five TL-40 skids are visible on the standing, within the Northern Grid Works perimeter.

No markings, signage or section titles are legible.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (survey-VV) | Six TL-40 skids (north apron) | `presence` |  |
| `m4` (survey-WW) | Four TL-40 skids (east apron) | `presence` |  |
| `m7` (survey-XX) | Five TL-40 skids (Tarnholt) | `presence` |  |
| `m8` (survey-XX) | Tarnholt forward standing | `place` |  |
| `m9` (survey-XX) | Northern Grid Works | `operator_org` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED and IDENTICAL across all three |
| geography | STATED - two aprons at one station, plus a second, different site |
| designation | ABSENT in all three, and stated absent in all three |
| time | STATED exactly (2025-07-11, 2025-07-14, 2025-08-02) - successive, which is what makes a move readable |

### Required outcome (prose - choose your own mechanism and values)

Four things must be true of the output and all four are absences. No body-level identity is confirmed anywhere in the set. Both Redlow groups and the Tarnholt group survive as distinct nodes - the count is preserved. No move edge is drawn between Redlow and Tarnholt: successive dates plus an identical design and operator are not evidence that one body moved, and no source describes a move. And the gap that records the body identity as unresolved survives the arrival of the third report intact - it is neither deleted nor quietly reclassified from 'we do not have the evidence' to 'the evidence has gone stale', because nothing about it has been answered. A move here would also fail on its own terms: no single source co-refers its own mentions across the two sites, so no source licenses one.

### Tempting but wrong

- Fuse the two Redlow groups (F5a's error) and then let the Tarnholt report become the fused body's after-state, which draws a relocation no one reported.
- Draw the move but keep it unconfirmed, on the grounds that an unconfirmed edge is harmless. It removes the pair from the queue and answers the analyst's question for them.
- Delete the retired basing rather than retiring it with its date, so the graph loses the record that the body was ever assessed to be at Redlow.
- Retire the unresolved-identity gap as stale when the newer report lands, converting an honest 'insufficient evidence' into an answered question.
- Read five skids at Tarnholt as the six-minus-one from Redlow, and narrate an arithmetic of movement across three independent passes.

### Negative gold - spans that must produce NO claim

- 'within the Northern Grid Works perimeter' states custody of the site, not of the plant.
- Three passes by two vendors are three looks; they are not three bodies and not one body's itinerary.

**Corpus:** NOT EXERCISABLE end to end, which is why the harm chain went unnoticed for so long. Every ingredient is in the corpus separately - two sites, one design, no titles, a relocation beat, and a supersede floor built against a weak-tier spoof - but with no two co-located same-kind bodies to over-merge, the chain from identity error to drawn relocation to deleted gap cannot be demonstrated on the frozen data. The gate is fixture-only.

# Shape 6 - The composite identifier - a designation alone identifies nothing

## `F6a-shared-designation-different-operators`

**Scope:** 6 (the discriminator ladder: a shared designation is NOT a unique identifier)  
**Refs:** D-13.20 (the unique-identifier list is composite AND-keys; a bare designation is not an identifier); designations are reused across armies and across time; the bill-of-lading asymmetry: differing identifiers veto, shared ones do not confirm

**Purpose.** One body title, two operators, two sites, two good-grade sources - each publishing about its own establishment. Nothing links them but the string.

**Why it is hard.** Two independent good sources appear to agree, which is the textbook shape of a corroborated fact - and what they agree on is a numbering convention, not a body. Numbering series restart in every organisation, so the agreement carries no information about identity at all. Worse, if the pair fuses, the two sites then look like one body's before and after, so a name collision turns into a movement claim.

### Documents

**`bulletin-YY`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-20

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07/2025
Dated: 20 April 2025

2 Transfer Section (Northern Grid Works) is established at Redlow pumping station with effect from 20 April 2025.
```

**`bulletin-ZZ`** - operator establishment bulletin, source grade **B**, a different operator's own establishment bulletin, dated 2025-05-06

```
WATER AUTHORITY - ESTABLISHMENT NOTICE 04/2025
Dated: 06 May 2025

2 Transfer Section, Water Authority, is established at Ashgate transfer yard with effect from 06 May 2025.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-YY) | 2 Transfer Section | `formation` | operator stated in the same clause: Northern Grid Works |
| `m2` (bulletin-YY) | Redlow pumping station | `place` |  |
| `m3` (bulletin-ZZ) | 2 Transfer Section | `formation` | operator stated in the same clause: Water Authority |
| `m4` (bulletin-ZZ) | Ashgate transfer yard | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both, and they DIFFER |
| geography | STATED on both, and they differ |
| designation | STATED on both, and IDENTICAL - the whole temptation |
| time | STATED as effective dates two weeks apart (2025-04-20, 2025-05-06) |

### Required outcome (prose - choose your own mechanism and values)

No merge and no confirmation. A designation shared between two operators' establishments is not an identifier; what identifies a body is the pairing of the operator with the title, and here that pairing differs. The two bodies stand apart, and the identical title may be recorded as what it is - a name collision between two organisations' numbering - without lifting the pair toward a merge. Nothing in the output may suggest a body moved from one site to the other. The asymmetry to preserve: a differing identifier is strong enough to veto, while a shared one is never strong enough to confirm - the two directions are deliberately unequal.

### Tempting but wrong

- Fuse on the shared designation, treating a title as a hard identifier - and then inherit a cross-operator body, the most damaging over-merge class on an operator-scoped map.
- Confirm the body because two independent good-grade sources agree. They agree on a string; corroboration requires two looks at the same thing.
- Treat the differing operators as a weak score contributor that a perfect title match can outvote.
- Draw a move between the two sites once the pair is fused, so a naming coincidence becomes a reported relocation.

### Negative gold - spans that must produce NO claim

- Each bulletin is its own operator's publication; neither is evidence about the other's establishment.

**Corpus:** EXERCISABLE at design level, and richly - one designation string is attached to five different national contexts, another is fielded by three operators with three different contract values attached to what the sources all call 'the deal', and two design families each appear as a perfect two-operator/two-name square stated in a single line. At BODY level it is not exercisable: one numbered body in 52 documents, and it is a planted designator collision belonging to a foreign army.

## `F6b-composite-stated-on-both-sides-confirms`

**Scope:** 6 (the discriminator ladder: the composite key lifts the caps)  
**Refs:** D-13.20 (the composite AND-key IS an identifier; it lifts the caps); two independent sources are what confirm; S3's invariant: fragmentation must resolve by EARNED merges

**Purpose.** The mirror of F6a and the earned mirror of the co-location trap: the operator-plus-title pairing is stated on both sides, by two sources with genuinely independent looks.

**Why it is hard.** It is the fixture that catches the opposite failure from everything else in this file. A system tuned only to refuse will refuse here too - and permanent fragmentation is not caution, it is the same insufficient-evidence claim made falsely. The stage's whole purpose is that identity becomes earnable, so there has to be a case that earns it, and it has to be earned on the composite rather than on either half.

### Documents

**`bulletin-YY`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-20

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07/2025
Dated: 20 April 2025

2 Transfer Section (Northern Grid Works) is established at Redlow pumping station with effect from 20 April 2025.
```

**`register-AC`** - curated establishment register, source grade **B**, regional regulator's compiled register; this entry from its own site visit, dated 2025-06-12

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 24/2025
Compiled 12 June 2025

Redlow pumping station: establishment 2 Transfer Section, Northern Grid Works.
Compiled from a site visit on 10 June 2025; the section title was read from the works notice board.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-YY) | 2 Transfer Section | `formation` | operator stated: Northern Grid Works |
| `m2` (bulletin-YY) | Redlow pumping station | `place` |  |
| `m3` (register-AC) | 2 Transfer Section | `formation` | operator stated: Northern Grid Works; read from the works notice board on the register's own site visit |
| `m4` (register-AC) | Redlow pumping station | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both, and IDENTICAL |
| geography | STATED on both, and the same station |
| designation | STATED on both, and IDENTICAL |
| time | STATED (effective 2025-04-20; independently observed 2025-06-10) - consistent, not conflicting |

### Required outcome (prose - choose your own mechanism and values)

The merge proceeds and may reach confirmed: the pairing of operator and title is stated on both sides, the two looks are genuinely independent - one is the operator's own notice, the other a regulator's site visit reading a notice board - and nothing conflicts. What earns it is the composite, not either half: the same title with a different operator (F6a) earns nothing, and the same operator with a different title (F6c) is a veto. This is what an earned merge looks like, and it is the only kind of merge that may reduce fragmentation.

### Tempting but wrong

- Refuse because 'shared designations never confirm'. That rule is about a BARE designation; over-applying it means nothing can ever confirm, and permanent fragmentation gets reported as genuine uncertainty.
- Confirm on the title alone, by the same code path that would then also confirm F6a.
- Count the register entry as a second look without checking whether it is a reprint of the bulletin. Here it is not, and the document says why - but the check is the thing being tested, not the outcome.
- Lower a floor to get this merge. It must be earned by the evidence being better, not by the bar being lower.

### Negative gold - spans that must produce NO claim

- 'the section title was read from the works notice board' is what makes this an independent look - it is provenance, not a second establishment.

**Corpus:** NOT EXERCISABLE. The composite needs an operator-plus-title pairing stated on both sides; the corpus states no body title for the subject at all, so the top two rungs of the discriminator ladder have zero data. Every basing in the answer key is annotated derived, and one carries a note saying no document states a named body at a named site.

## `F6c-differing-designation-vetoes`

**Scope:** 6 (the ladder's top rung: a differing designation vetoes)  
**Refs:** D-13.20 (differing designation = veto, the top rung); the asymmetry: differing vetoes, shared does not confirm

**Purpose.** Two differently titled bodies of one operator, at one station, over overlapping dates - everything agrees except the one thing that individuates them.

**Why it is hard.** Three of the four discriminators agree and the two titles are lexically almost identical, so a scoring approach adds up a great deal of agreement against one small difference. But the small difference is the only individuating fact present, and it is stated by the operator itself. This is also the co-location shape with the discriminator supplied - which is exactly why the veto has to outrank the agreement.

### Documents

**`bulletin-YY`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-20

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07/2025
Dated: 20 April 2025

2 Transfer Section (Northern Grid Works) is established at Redlow pumping station with effect from 20 April 2025.
```

**`bulletin-AB`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-28

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 08/2025
Dated: 28 April 2025

5 Transfer Section, Northern Grid Works, is established at Redlow pumping station with effect from 28 April 2025.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-YY) | 2 Transfer Section | `formation` |  |
| `m2` (bulletin-AB) | 5 Transfer Section | `formation` |  |
| `m3` (bulletin-AB) | Redlow pumping station | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both, and IDENTICAL |
| geography | STATED on both, and the SAME station |
| designation | STATED on both, and DIFFERENT - the veto |
| time | STATED as effective dates eight days apart, both open-ended (overlapping) |

### Required outcome (prose - choose your own mechanism and values)

The merge is vetoed on the differing titles, however much else agrees - and the veto must be visible, with the two titles shown, rather than expressed as a score that a strong name or relational signal could outweigh. Both bodies survive, and the station now honestly holds two establishments of one operator, which is the order-of-battle fact the co-location cap exists to protect. Note the direction: this difference is decisive, while the agreement in F6a was not - a differing identifier vetoes, a shared one does not confirm.

### Tempting but wrong

- Fuse because the operator, the site and the design all agree and the titles are 90% similar as strings.
- Treat the differing titles as a mere score penalty, so a strong enough name or co-location signal outvotes the one individuating fact in the set.
- Read the second establishment as a re-titling of the first and draw a succession, so two bodies become one with a history.
- Apply the veto silently, leaving an analyst unable to see that two candidate bodies were considered and separated.

### Negative gold - spans that must produce NO claim

- Two bulletins from one operator eight days apart are not two independent looks at one body.

**Corpus:** NOT EXERCISABLE - it needs two differently-titled bodies of one operator, and the corpus has no two titled bodies of any operator.

## `F6d-title-reissued-after-a-stated-disestablishment`

**Scope:** 6 (the ladder: temporally-witnessed continuity outranks a shared designation)  
**Refs:** D-13.20 (designations are reused across TIME as well as across armies; temporally-witnessed continuity sits above shared designation); C2 / G16 (no drawn relocation)

**Purpose.** The same operator, the same title, six years apart, with an explicit disestablishment in between - and the later source says in its own words that the title was re-raised.

**Why it is hard.** The composite key matches perfectly, so the rule that earns identity in F6b fires here and gets it wrong. The only thing separating the two bodies is a stated discontinuity in time, which no attribute comparison will surface - and if the two are fused, the two stations six years apart become one body's before and after, producing a relocation across a gap in which the body did not exist.

### Documents

**`bulletin-AD`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2019-03-11

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 03/2019
Dated: 11 March 2019

2 Transfer Section, Northern Grid Works, is established at Calder pumping station.
```

**`bulletin-AE`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2021-06-02

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 11/2021
Dated: 02 June 2021

2 Transfer Section is disestablished with effect from 30 June 2021. Its plant passes to the Calder depot party.
```

**`bulletin-AF`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-04-20

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 07A/2025
Dated: 20 April 2025

2 Transfer Section, Northern Grid Works, is established at Redlow pumping station with effect from 20 April 2025.
The title is re-raised; the previous holder of the title was disestablished in 2021.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AD) | 2 Transfer Section | `formation` | 2019, at Calder pumping station |
| `m2` (bulletin-AE) | 2 Transfer Section | `formation` | 2021, disestablished with effect from 30 June 2021 |
| `m3` (bulletin-AF) | 2 Transfer Section | `formation` | 2025, at Redlow pumping station; the bulletin states the title is re-raised |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on all three, and IDENTICAL |
| geography | STATED - Calder in 2019, Redlow in 2025 |
| designation | STATED on all three, and IDENTICAL |
| time | STATED, and DISCONTINUOUS - a disestablishment in 2021 and a re-raising in 2025, both stated |

### Required outcome (prose - choose your own mechanism and values)

No single confirmed body may span the stated disestablishment. Either two bodies that share a title, or one identity held unresolved with the discontinuity named - both are defensible; a confirmed merge is not, and neither is a move from Calder to Redlow across a period in which the operator says the title did not exist. The reason the composite key does not settle it: continuity witnessed in time outranks a shared title, and here the witness says the continuity was broken. Neither the 2019 record nor the disestablishment may be dropped as superseded - both are what makes the later record legible.

### Tempting but wrong

- Confirm on the composite key, because operator plus title matches exactly - the rule that is right in F6b and wrong here.
- Draw a relocation from Calder to Redlow spanning six years and a disestablishment.
- Discard the 2019 body as a stale duplicate of the 2025 one, deleting the evidence that the title has two occupants.
- Treat the disestablishment as a mere status attribute on a single continuing body, so a body that ceased to exist keeps its history and its plant.

### Negative gold - spans that must produce NO claim

- 'Its plant passes to the Calder depot party' is a custody transfer, not a renaming of the section.
- 'The title is re-raised' is an explicit statement of discontinuity - the strongest evidence in the set.

**Corpus:** PARTIALLY EXERCISABLE - corrected. The corpus does contain a stated chain of amalgamations and redesignations of one body across decades, with the document itself saying the chain is not consistently recorded and that accounts differ on the final date. That is an unbounded alias sink: a transitive closure over 'was redesignated as' has no floor there, which is the same hazard this fixture guards from the other side. What is missing is the clean version - a stated disestablishment followed by a re-raising of the same title - and the body in question is the off-subject decoy, so nothing about the subject can be tested this way.

# Shape 7 - The unnormalizable critical value - no wall AND no fusion, plus a named gap

## `F7a-operator-stated-on-both-sides-and-uncomparable`

**Scope:** 6 / C7 (normalization is a prerequisite for walling on any slot)  
**Refs:** C7 (an unnormalizable stated critical value yields a third state: no wall AND no fusion, plus a named gap - and the gap must BIND the fusion path, not merely annotate it); normalization must run before conflict detection and before the operator namespace is derived

**Purpose.** One site, one design, one period - and the operator stated on both sides in two house styles that no normalizer can reconcile: a directorate title with a regional qualifier, and an initialism with a branch qualifier.

**Why it is hard.** There are three states here, not two, and only two are usually implemented. The values are not equal and not known to be different: the comparison simply cannot be made. Both confident answers fabricate - declaring a conflict invents a distinction, and treating the untestable value as absent converts 'we cannot check' into 'nothing is in the way' and merges on the remaining agreement. And the pressure to expand the initialism from elsewhere in the graph is strong, because a name that fits is sitting right there.

### Documents

**`bulletin-AG`** - operator establishment bulletin, source grade **B**, operator-side bulletin, house style A, dated 2025-05-05

```
WORKS DIRECTORATE (NORTHERN REGION) - PLANT NOTICE 06/2025
Dated: 05 May 2025

Transfer plant at Tarnholt forward standing is held by the Works Directorate (Northern Region).
Six skids of the TL-40 type are on charge.
```

**`register-AH`** - curated establishment register, source grade **B**, regional regulator's compiled register, house style B, dated 2025-05-19

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 20/2025
Compiled 19 May 2025

Tarnholt forward standing: transfer plant held by N.G.W. (Regional Works Branch).
Six skids of the TL-40 type recorded.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AG) | the Works Directorate (Northern Region) | `operator_org` |  |
| `m2` (bulletin-AG) | Tarnholt forward standing | `place` |  |
| `m3` (register-AH) | N.G.W. (Regional Works Branch) | `operator_org` |  |
| `m4` (register-AH) | Tarnholt forward standing | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both sides - and the two forms cannot be reconciled by any general rule |
| geography | STATED, and the SAME site |
| designation | ABSENT on both |
| time | STATED two weeks apart (2025-05-05, 2025-05-19), overlapping period |

### Required outcome (prose - choose your own mechanism and values)

Neither a wall nor a fusion. The operator is stated on both sides, so it is not absent and cannot be treated as unknown; but the two forms are not comparable, so the system does not know whether they agree or conflict. The pair therefore may not merge on the strength of the site and design agreeing, and may not be vetoed either - and a named gap must record which comparison could not be made and what would settle it (a source stating the relation between the two organisational names). Crucially the gap has to bind the merge: while it stands the pair cannot fuse, because a gap that merely annotates a merged node is decoration.

### Tempting but wrong

- Treat the two strings as different and veto - inventing a distinction between two organisations that may well be one.
- Expand the initialism using an operator that exists elsewhere in the graph. If a document stated that expansion this would be an equivalence case with a quote; absent that, it is an equivalence the system invented.
- Treat an unnormalizable value as an absent one, so 'untestable' becomes 'no obstacle' and the pair merges on the agreeing signals - the precise inversion this rule forbids.
- Merge and hang the gap on the merged node as a footnote, which reports the doubt while acting on the certainty.
- Derive the operator namespace from the raw strings before normalizing, so the two forms land in two different operator worlds and can never be compared at all.

### Negative gold - spans that must produce NO claim

- The same figure of six skids appears in both documents - one figure twice, not a corroborated total of twelve.

**Corpus:** EXERCISABLE, on both sides of one candidate merge - a direct correction to what I first wrote. Two corpus documents place the SAME subject under two service commands whose names differ by one word, where one name is a substring of the other, both strings are registered aliases of a single entity in the shipped registry, and the answer key says only one of the two services is right. The same pair of documents disagrees on five other facts about that one designation with no cross-reference between them. The corpus adds three more hard-failure abbreviations: two that are never expanded anywhere in 52 documents, and one that is a single edit away from a different country's acronym, so a normalizer that 'corrects' it moves the entity to the wrong nation. The shipped config has already conceded the shape by declaring the discriminator soft - which is the wrong one of the three states.

## `F7b-normalization-reconciles-and-the-merge-proceeds`

**Scope:** 6 / C7 (normalization as a prerequisite)  
**Refs:** C7 (normalization is the prerequisite; where it succeeds, the comparison is testable); the normalization vocabulary must be inspectable, extensible data rather than literals in code

**Purpose.** The mirror of F7a: the same two-house-style shape, but the difference is case, punctuation and a legal suffix - reconcilable by a declared general rule.

**Why it is hard.** Easy to get right and easy to get wrong in both directions. Refuse it and every publisher's house style becomes a wall, which is how a system tuned by F7a's caution ends up unable to merge anything. Reconcile it by containment instead of by a declared rule and F7c breaks. The fixture also states the boundary: the reconciliation must be visible and editable, because the vocabulary of house styles is open-ended and every new publisher adds to it.

### Documents

**`bulletin-AJ`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-05-05

```
NORTHERN GRID WORKS LTD - PLANT NOTICE 08/2025
Dated: 05 May 2025

Transfer plant at Ashgate transfer yard is held by NORTHERN GRID WORKS LTD.
Six skids of the TL-40 type are on charge.
```

**`register-AK`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-05-19

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 20A/2025
Compiled 19 May 2025

Ashgate transfer yard: transfer plant held by Northern Grid Works.
Six skids of the TL-40 type recorded on a visit of 16 May 2025.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AJ) | NORTHERN GRID WORKS LTD | `operator_org` |  |
| `m2` (bulletin-AJ) | Ashgate transfer yard | `place` |  |
| `m3` (register-AK) | Northern Grid Works | `operator_org` |  |
| `m4` (register-AK) | Ashgate transfer yard | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both sides, and reconcilable (case, punctuation, a legal suffix) |
| geography | STATED, and the SAME site |
| designation | ABSENT on both |
| time | STATED (2025-05-05; observed 2025-05-16) - consistent |

### Required outcome (prose - choose your own mechanism and values)

The two operator values reconcile under a declared, general normalization, so the comparison becomes testable, the operator agreement counts as agreement, and the pair is judged on its merits with nothing untestable in the way. The normalization that did it must be inspectable and extensible data an analyst can read and add to - not a literal buried in code - because the next publisher will spell it a third way. Two independent looks at one site with an agreeing operator is exactly the shape that is allowed to strengthen a presence.

### Tempting but wrong

- Refuse because the strings differ, making house style a wall and guaranteeing permanent fragmentation across publishers.
- Reconcile by substring containment rather than by declared rules, which passes here and then wrongly matches F7c.
- Hard-code this particular pair of spellings, so the fixture passes and the next spelling fails silently.
- Read the two documents' identical figure as two corroborating counts totalling twelve.

### Negative gold - spans that must produce NO claim

- 'recorded on a visit of 16 May 2025' dates the observation; the compilation date does not.

**Corpus:** EXERCISABLE. The corpus carries case and punctuation drift on organisation and country names across documents - one country appears in two spellings, and one document drifts internally - which is exactly the reconcilable half. The config also already records that a naive comparison on one of these would false-wall a real pair.

## `F7c-containment-is-not-agreement`

**Scope:** 6 / C7 (normalization as a prerequisite)  
**Refs:** C7 (the third state); the containment doctrine (an extra qualifier can change what a name denotes)

**Purpose.** An operator name that literally contains another: a joint directorate of two operators, against one of its parents. Containment says match; the world says a third organisation.

**Why it is hard.** This is the trap that catches the cheapest possible normalization. Every string operation says these agree, and the qualifier that makes them different is the only part that carries the meaning. It also has a genuine third answer: a joint body is neither of its parents, so the honest output is neither a match nor a conflict but an unresolved question about whose plant it is.

### Documents

**`bulletin-AL`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-06-09

```
NORTHERN GRID WORKS - PLANT NOTICE 12/2025
Dated: 09 June 2025

Tarnholt forward standing: plant held by Northern Grid Works.
```

**`register-AM`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-06-23

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 25/2025
Compiled 23 June 2025

Tarnholt forward standing: plant held by the Northern Grid Works / Water Authority joint directorate.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AL) | Northern Grid Works | `operator_org` |  |
| `m2` (bulletin-AL) | Tarnholt forward standing | `place` |  |
| `m3` (register-AM) | the Northern Grid Works / Water Authority joint directorate | `operator_org` |  |
| `m4` (register-AM) | Tarnholt forward standing | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both sides; one string contains the other, and they denote different bodies |
| geography | STATED, and the SAME site |
| designation | ABSENT on both |
| time | STATED two weeks apart (2025-06-09, 2025-06-23), overlapping period |

### Required outcome (prose - choose your own mechanism and values)

Not a match and not a conflict: a joint directorate of two operators is a third organisation, not either parent, so the pair may neither fuse nor wall - and a gap must name the open question, which is whose plant this is: one operator's, or the joint body's. Nothing in the output may quietly take the first-named parent as the operator. This is the same third state as F7a arrived at from the opposite direction: there, two names that could not be compared; here, two names that compare too easily.

### Tempting but wrong

- Count containment as an operator match and merge, which silently assigns a joint body's plant to one parent.
- Declare a conflict and veto, inventing a distinction between an operator and a body it is part of.
- Take the first-listed parent as the operator, or split the plant between the two parents - both are figures no source states.
- Normalize the joint name by stripping everything after the separator, so the whole distinction disappears in preprocessing.

### Negative gold - spans that must produce NO claim

- 'joint directorate' names an organisational arrangement; it does not state a share of the plant.

**Corpus:** EXERCISABLE. Joint-use compounds naming two services in one string occur in the corpus (primary side only - zero in the chaff half), so the containment trap has real material. And the operator collision in F7a is a second, sharper instance of the same shape: one command name literally contains the other while denoting a different service.

# Shape 8 - Geography plays three different parts - and that is what lets anything confirm

## `F8a-place-is-perishable-for-a-body`

**Scope:** 6 / C6 (the time role of an attribute is declared per kind of thing)  
**Refs:** C6 (for a formation, geography is perishable: it expires, so it can neither veto nor confirm on its own); D-13.9 (perishable-only evidence cannot confirm)

**Purpose.** One body, one operator, one title, two stations seven months apart - with the later source stating the move in its own words.

**Why it is hard.** For a body, where it is is the most-reported and least-identifying fact available. Treat a differing place as a conflict and every real relocation becomes invisible, which is how a system stops being able to monitor anything. Treat an agreeing place as confirmation and co-located strangers become one body. The same attribute has to be prevented from doing either job, while still being the thing the analyst most wants to see.

### Documents

**`bulletin-AN`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-02-10

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 02/2025
Dated: 10 February 2025

2 Transfer Section, Northern Grid Works, is established at Calder pumping station.
```

**`bulletin-AP`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-09-15

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 23/2025
Dated: 15 September 2025

2 Transfer Section, Northern Grid Works, is established at Redlow pumping station with effect from 15 September 2025.
The section vacates Calder pumping station on the same date.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AN) | 2 Transfer Section | `formation` | at Calder pumping station, February 2025 |
| `m2` (bulletin-AP) | 2 Transfer Section | `formation` | at Redlow pumping station from 15 September 2025; the bulletin states the section vacates Calder the same day |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both, and IDENTICAL |
| geography | STATED on both, and DIFFERENT - and the change is stated, not inferred |
| designation | STATED on both, and IDENTICAL |
| time | STATED, SUCCESSIVE and non-overlapping (2025-02-10; effective 2025-09-15) |

### Required outcome (prose - choose your own mechanism and values)

The differing stations must not veto the identity - a body's location is expected to change, and here a source states the change explicitly - and an agreeing station would not have confirmed it either. The two records are one body at two times: the earlier basing retires with its own date and keeps whatever gap it carried, rather than being deleted, and the move is drawn because a source describes it, not because two records exist. What makes this legitimate where F5b's was fabrication is not the strength of the later report - it is that the identity was earned on the operator-plus-title pairing and the move is stated.

### Tempting but wrong

- Veto the identity because the stations differ, which makes every genuine relocation unrepresentable and reports it as two bodies.
- Confirm the identity because the operator and title agree AND the place is 'consistent with' a move - the place must contribute nothing to the confirmation either way.
- Delete the Calder basing instead of retiring it with its date, losing the record of where the body was.
- Draw the move from the mere existence of two dated records, which is the same edge for a different and unfounded reason.

### Negative gold - spans that must produce NO claim

- 'with effect from' is an administrative date; it is not an observation of the section at Redlow.

**Corpus:** PARTIALLY EXERCISABLE. The corpus has a two-ended relocation beat with dated basings at both ends, so the perishable half of the geography question is live. It has no title at either end, so the fixture's actual subject - one TITLED body that moves - cannot be built from it; the corpus relocation is earned on geography and imagery alone.

## `F8b-place-is-constitutive-for-a-presence`

**Scope:** 6 / C6 (constitutive: the place is part of what a presence IS)  
**Refs:** C6 (constitutive is what lets a presence confirm at all; a difference in a constitutive attribute is a distinctness signal, not staleness)

**Purpose.** Three sightings, identical in design, operator and figure: two at different places, and two at the same place by two unrelated vendors.

**Why it is hard.** The three reports are word-for-word interchangeable except for the place, so a system that treats place the way F8a requires - as an expiring attribute - fuses the first two into one travelling presence and has to explain how six skids were in two places. The pair that should confirm and the pair that must never merge differ only in that one field, which is why one setting cannot serve both kinds of thing.

### Documents

**`survey-AQ`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-06-04

```
AERIAL SURVEY EXTRACT - REDLOW PUMPING STATION
Collected 04 June 2025, single pass, 0.5 m

Six TL-40 skids on the north apron, within the Northern Grid Works station boundary.
No markings legible.
```

**`survey-AR`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-06-06

```
AERIAL SURVEY EXTRACT - TARNHOLT FORWARD STANDING
Collected 06 June 2025, single pass, 0.5 m

Six TL-40 skids on the standing, within the Northern Grid Works perimeter.
No markings legible.
```

**`survey-AS`** - aerial survey extract, source grade **C**, a second, unrelated survey vendor; its own pass, not a reprint, dated 2025-06-09

```
SECOND-VENDOR SURVEY EXTRACT - REDLOW PUMPING STATION
Collected 09 June 2025 on this vendor's own pass, 0.6 m

Six skids of the TL-40 type on the north apron, Northern Grid Works.
No markings legible.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (survey-AQ) | Six TL-40 skids, Redlow north apron | `presence` |  |
| `m2` (survey-AR) | Six TL-40 skids, Tarnholt standing | `presence` |  |
| `m3` (survey-AS) | Six TL-40 skids, Redlow north apron | `presence` | a second vendor's own pass over the same apron |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED and IDENTICAL in all three |
| geography | STATED in all three - two of them share a place, one does not |
| designation | ABSENT in all three |
| time | STATED exactly (2025-06-04, 2025-06-06, 2025-06-09), days apart |

### Required outcome (prose - choose your own mechanism and values)

For equipment at a place, the place is part of what the thing is - so the Redlow sighting and the Tarnholt sighting can never be one presence however identical everything else is, and their difference is evidence that these are two things rather than evidence that one of them is out of date. The two Redlow sightings, sharing the constitutive fields, can be one presence, and two unrelated vendors looking at it is what allows it to confirm - this is the rung without which a presence could never confirm at all. The matching figures are not evidence of movement, and the two Redlow figures are one figure seen twice, not twelve skids.

### Tempting but wrong

- Treat place as perishable for a presence too, fusing the Redlow and Tarnholt sightings into one presence that moved - and then either doubling or halving the count to make it consistent.
- Read the identical figures across two sites as a signal that the same six skids relocated in two days.
- Count the second vendor's pass as a reprint of the first because the wording is nearly identical, so the presence never confirms.
- Add the two Redlow figures into twelve skids on one apron.
- Treat the Tarnholt sighting as superseding the Redlow one because it is later.

### Negative gold - spans that must produce NO claim

- 'No markings legible' is a stated absence of identifiers in all three - it is not a discriminator, and repeating it three times does not corroborate anything about identity.
- 'on this vendor's own pass' is the provenance that makes the third report an independent look.

**Corpus:** EXERCISABLE, and the corpus's strongest suit: equipment-at-a-site sightings are its dominant shape, including one site reported twice with different figures and the same design reported at more than one site. The one thing to check when using real data here is source independence between the two same-site reports, which the corpus makes genuinely non-trivial.

## `F8c-coordinates-identify-a-place`

**Scope:** 6 / C6 (identifying: coordinates identify a place), 11 (place resolution must inform what sits above it)  
**Refs:** C6 (identifying satisfies the requirement for a confirm - the missing rung without which the clean-anchor lever cannot exist); the ordering requirement: a place merge that lands too late to inform the instances above it did not happen for any downstream purpose

**Purpose.** Two differently named place mentions whose stated coordinates are the same point, given in two different formats and at two different stated precisions.

**Why it is hard.** The names share one token and differ in every other respect, so a name-based route is unreliable in both directions - and the decisive evidence is in two notations that have to be converted before they can be compared at all. There is a second, subtler requirement: a place identity that is settled after the things at that place have been judged is worthless, because the whole value of a resolved place is that everything sitting on it can use it as an anchor.

### Documents

**`register-AT`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-03-02

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 09/2025
Compiled 02 March 2025

Redlow pumping station (52.114 N, 1.028 W) - transfer plant recorded. Coordinates given to station precision.
```

**`survey-AU`** - aerial survey extract, source grade **B**, commercial survey vendor, dated 2025-03-20

```
AERIAL SURVEY EXTRACT - REDLOW NORTH TRANSFER SITE
Collected 20 March 2025, single pass, 0.5 m

Redlow North transfer site, 52 06 50 N 001 01 41 W - six TL-40 skids on a north apron. Position given to apron precision.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-AT) | Redlow pumping station | `place` | coordinates stated in decimal degrees, to station precision |
| `m2` (survey-AU) | Redlow North transfer site | `place` | position stated in degrees-minutes-seconds, to apron precision - the same point |

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT in both |
| geography | STATED as COORDINATES in both, in different notations, resolving to one point |
| designation | ABSENT |
| time | STATED (2025-03-02 compiled; 2025-03-20 collected) |

### Required outcome (prose - choose your own mechanism and values)

One place. Coordinates identify a place, so two mentions whose stated positions resolve to the same point - at the coarser of the two stated precisions - are the same place, and the differing names do not weigh against it. The two notations must be reconciled before they are compared, and a format difference must never be read as a value difference. And the place identity must be settled early enough to inform what sits on it: the sightings, holdings and basings that reference either name must all see one anchor, because a merge that lands after those judgements have been made has no downstream effect at all.

### Tempting but wrong

- Compare the coordinate strings and find them different, so a place is duplicated on a notation difference.
- Merge on the shared token 'Redlow' and get the right answer for the wrong reason - the same reasoning wrongly merges F8d.
- Compare positions without regard to the precision each source states, so a station-level position and an apron-level position read as a mismatch.
- Resolve places after the instances above them have already been scored, so the merge is real in the graph and invisible to everything that needed it.

### Negative gold - spans that must produce NO claim

- 'Coordinates given to station precision' and 'Position given to apron precision' are statements about precision - they must be read, not discarded as prose.

**Corpus:** EXERCISABLE - upgraded. The primary half of the corpus carries resolved coordinates on a double-digit number of claims across five different notations, which is precisely the reconcile-the-notation-before-comparing requirement. The chaff half carries no coordinates for any military object at all - every chaff site is a bare toponym - so geometric place resolution has no fallback there, and one chaff post says why that hurts ('which village exactly, it is a big district').

## `F8d-one-name-two-points-and-one-with-no-point`

**Scope:** 6 / C6 (identifying), 7 (under-determined + named gap)  
**Refs:** C6 (identifying attributes are strong identity evidence - in both directions); D-13.8 (an absent discriminator leaves a thing under-individuated, never back-filled)

**Purpose.** The mirror of F8c: one station name attached to two positions tens of kilometres apart, plus a third mention of the same name with no position at all.

**Why it is hard.** The name is identical, which is the strongest cheap signal available, and the coordinates are the only thing that says these are two places. If the name wins, the graph gets one station at two locations and every basing under it is wrong somewhere. The third mention then has nowhere honest to go: it looks like both, and being the only remaining candidate for either is not evidence.

### Documents

**`register-AT`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-03-02

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 09/2025
Compiled 02 March 2025

Redlow pumping station (52.114 N, 1.028 W) - transfer plant recorded. Coordinates given to station precision.
```

**`press-AV`** - trade press item, source grade **C**, trade press, recycles operator briefings, dated 2025-04-02

```
CALDONIA PLANT MONTHLY - 02 April 2025

Redlow pumping station (52.63 N, 1.11 W) is being re-cabinetted this quarter.
```

**`register-AW`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-04-10

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 16/2025
Compiled 10 April 2025

Redlow transfer site - no coordinates recorded - transfer plant recorded.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-AT) | Redlow pumping station | `place` | 52.114 N, 1.028 W |
| `m2` (press-AV) | Redlow pumping station | `place` | 52.63 N, 1.11 W - the same name, some 58 km north of m1 |
| `m3` (register-AW) | Redlow transfer site | `place` | no coordinates recorded |

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT in all three |
| geography | STATED as coordinates in two, and they DIFFER materially; ABSENT in the third |
| designation | ABSENT |
| time | STATED (2025-03-02, 2025-04-02, 2025-04-10) |

### Required outcome (prose - choose your own mechanism and values)

The two positioned mentions are two places, and the identical name may not override the coordinates - either the name is reused or one source is wrong, and both readings leave two places plus a recorded discrepancy for an analyst. The unpositioned mention may not be confirmed as either of them on its name alone: it is held, under-determined, with a gap naming what is missing and what would settle it. No position may be back-filled onto it from the better-attested twin, and it must not be silently attached to whichever place has more evidence.

### Tempting but wrong

- Fuse the two positioned mentions on the identical name, so the graph holds one station at two locations and quietly averages or picks between them.
- Discard the trade-press position as the weaker source and merge anyway - grade decides how much to believe a claim, not whether two different points are one place.
- Back-fill coordinates onto the unpositioned mention from its better-attested namesake, manufacturing a position no source gave it.
- Attach the unpositioned mention to whichever place already carries more plant, which is the rich-get-richer error at place level.

### Negative gold - spans that must produce NO claim

- 'no coordinates recorded' is a stated absence in the register - keep it as an absence, not as a licence to infer one.

**Corpus:** EXERCISABLE IN KIND, with a caveat I checked myself. The frozen data does contain one aerodrome identifier filed at two positions in two documents roughly 1,100 km apart - and the wrong one lands in the other of the two cities this subject's relocation question turns on. But the second document is tagged in the answer key with a code-string-noise corruption class, is marked off-subject, and is expected to yield no claim at all, so it is unclear whether the mismatch is the intended noise or an unnoticed error, and either way it cannot reach the graph through claims while that expectation holds. So: the shape is real in the source text, it is not usable as a clean test, and the residual risk belongs to any pass that reads chaff navigation-warning position fixes as place evidence. The unpositioned-namesake half is common - places with no coordinates are frequent throughout.

# Shape 9 - The same-document contrast - and the mirror where there is none

## `F9a-enumeration-with-a-stated-count`

**Scope:** 4 (same-doc contrast: a contrastive channel of its own, a ceiling not a veto)  
**Refs:** D-13.19 (a same-doc stated contrast can never auto-merge; the value is a band name, not a coefficient, because a coefficient drops a pair two bands and out of the queue); the contrast must be its own lane, never the hard, transitive stated-distinction rail - every establishment list contains an enumeration; D-13.13 (a source saying 'two sections' is stating the order-of-battle figure; capture it as a sourced count, never as reports-merged)

**Purpose.** One document, one operator, one design, two bodies named only by their stations - and the source enumerates them as two and gives each its own figure.

**Why it is hard.** Every cheap signal wants these fused: same operator, same design, same scheme, same sentence, near-identical names, one publisher. The only counter-evidence is syntax - and syntax is exactly what survives least well through extraction, which is why it has to be carried explicitly as its own channel rather than re-derived later. The mechanism also has to be chosen carefully: a penalty large enough to stop the merge is large enough to drop the pair out of the review queue, and a prohibition strong enough to be safe here is strong enough to shatter legitimate clusters elsewhere.

### Documents

**`bulletin-AX`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-07-22

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 19/2025
Dated: 22 July 2025

Two transfer sections are established in the northern scheme: the Redlow section and the separate Tarnholt section.
Each holds Vanguard-pattern plant of the TL-40 type.
The Redlow section holds six skids; the Tarnholt section holds four.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AX) | the Redlow section | `formation` |  |
| `m2` (bulletin-AX) | the separate Tarnholt section | `formation` |  |
| `m3` (bulletin-AX) | TL-40 | `design` |  |

### Hand-authored coreference clusters

**`ax-1`** (bulletin-AX) - category **`CONTRAST`**, anchor `m1`, members `m2`, bind truth **`correct`**

> Two transfer sections are established in the northern scheme: the Redlow section and the separate Tarnholt section.

A contrastive annotation, not an identity one: the extractor is reporting that this document syntactically distinguishes the two mentions. Note the stated figure in the same span.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity, and the same for both |
| geography | STATED, and different for each |
| designation | ABSENT - both bodies are named only by their station |
| time | STATED as the bulletin's date (2025-07-22) |

### Required outcome (prose - choose your own mechanism and values)

The pair can never merge automatically, and both bodies survive as two. The contrast reaches an analyst with its quote, so the reason is legible. Two further requirements make this fixture non-trivial: the stated figure - two sections in the northern scheme - is a sourced order-of-battle count and must be captured as one, never derived by counting the nodes that happened to survive resolution; and the contrast is local to this document, so it may not become a hard, transitive prohibition that splits other clusters elsewhere which merely mention a Redlow section. Withholding an automatic merge must also keep the pair visible: 'not automatically' is not 'not at all'.

### Tempting but wrong

- Fuse on the agreement of operator, design and scheme, and then report one section holding ten skids.
- Route the contrast through the hard, transitive stated-distinction channel, so one bulletin's enumeration shatters well-corroborated identities everywhere the same words appear.
- Apply a numeric penalty instead of a ceiling. At any plausible threshold it drops the pair two bands, out of the analyst's queue, and the withheld merge becomes an invisible one.
- Derive 'two sections' by counting surviving nodes, so the order-of-battle figure silently reports our own resolution behaviour back to the analyst.
- Treat the two figures as two looks at one holding and reconcile them.

### Negative gold - spans that must produce NO claim

- 'Each holds Vanguard-pattern plant of the TL-40 type' is a design fact about both, and evidence for neither identity.
- 'in the northern scheme' is an area of responsibility, not a site.

**Corpus:** PARTIALLY EXERCISABLE, and the sourced-count half is richer than the S2 pass found: the corpus states order-of-battle figures repeatedly, including one document stating two incompatible figures for one force in four lines (a per-battery TEL count and a per-battalion range, with the two echelon words never equated), one stating a count with the unit type left as a slash-pair, one stating '3 (or possibly 4, sources vary)', and one stating a figure with two competing organising words for what the figure counts. The destination now exists too - the shipped ontology declares the count attribute sourced-only and never derived from reports merged. What is absent is the enumeration of two INDIVIDUATED bodies in one document, so the contrast channel itself has no corpus input.

## `F9b-no-contrast-is-neutral`

**Scope:** 4 (absence of contrast is neutral)  
**Refs:** D-13.19 (absence of contrast is neutral - never a prior FOR merging either); D-13.8 (absence is unknown, not agreement and not conflict)

**Purpose.** The same two bodies in one document with no enumeration, no 'separate', and no stated total - two mentions and nothing syntactic to read either way.

**Why it is hard.** Absence is the field this whole design keeps having to defend, and it gets misread in both directions here. 'The document does not distinguish them' is very easily heard as 'the document treats them as one', which turns a silence into a merge licence; the opposite reading turns it into a wall. And because both surface forms contain the same common word, there is a third temptation that has nothing to do with contrast at all.

### Documents

**`bulletin-AY`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-07-29

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 20/2025
Dated: 29 July 2025

The Redlow section holds six skids of the TL-40 type at Redlow pumping station.
Elsewhere in the northern scheme, the transfer section at Tarnholt forward standing holds four skids of the same type.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AY) | The Redlow section | `formation` |  |
| `m2` (bulletin-AY) | the transfer section at Tarnholt forward standing | `formation` |  |
| `m3` (bulletin-AY) | TL-40 | `design` |  |

### Coreference

No contrast annotation and no identity annotation: the document supplies neither, and that is the point.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED by the publisher's identity, and the same for both |
| geography | STATED, and different for each |
| designation | ABSENT for both |
| time | STATED as the bulletin's date (2025-07-29) |

### Required outcome (prose - choose your own mechanism and values)

The absence of a contrast changes nothing in either direction: it is not evidence that these are two bodies and not a licence to treat them as one. The pair is judged on its discriminators alone - same operator, same design, two different places, no titles at either end - which is the co-location shape, and it must end the same way: no confirmed body identity, both surviving, the body count unresolved and reported as such. No stated total exists here, so no order-of-battle figure may be reported for the scheme at all.

### Tempting but wrong

- Read 'no contrast stated' as the document treating the two as one, and merge.
- Read it as an implied contrast and wall them apart, which manufactures a stated distinction out of silence.
- Bind the second mention to the first as an anaphor because both contain the word 'section' - a name signal wearing the anaphor route's clothes, and the second mention is a named-by-place body, not a pronoun.
- Report two sections in the scheme because two survived resolution - here, unlike F9a, no source states the figure.

### Negative gold - spans that must produce NO claim

- 'Elsewhere in the northern scheme' locates the second body vaguely; it is not a second site name.
- 'four skids of the same type' inherits the design from the previous sentence and states no new design fact.

**Corpus:** PARTIALLY EXERCISABLE. Same-document pairs with no contrast are abundant - one site name appears three times as three separate mentions in a single document (verified in the S2 pass) - but not as two candidate BODIES, which is the pair this fixture judges.

# Shape 10 - Cross-operator and cross-kind pairs that must not fuse - including through an alias

## `F10a-same-title-two-operators-must-not-fuse`

**Scope:** 9 (G19: cross-namespace non-fusion, in BOTH phases)  
**Refs:** G19 (two instances in incompatible operator worlds cannot fuse - not in the fuzzy pass and not in the bootstrap); spine/13 sec.3 (collapse happens within a layer and never across operators in the instance layer); the widest merge path is a name verdict that reaches no cap at all

**Purpose.** An identical body title published by two different operators about their own establishments, at two different sites. The most dangerous over-merge class on an operator-scoped map, in its simplest form.

**Why it is hard.** An exact name match is the widest and cheapest path in any resolution system, and it is the one most likely to run before the more careful machinery does - so the operator check has to hold on the earliest path as well as the careful one. A gate that only guards the fuzzy comparison passes its own test while the exact path stays open, which is the shape of a gate that cannot fail.

### Documents

**`bulletin-AZ`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-03-05

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 04/2025
Dated: 05 March 2025

Transfer Section 3, Northern Grid Works, is established at Redlow pumping station.
```

**`bulletin-BA`** - operator establishment bulletin, source grade **B**, a different operator's own establishment bulletin, dated 2025-03-11

```
WATER AUTHORITY - ESTABLISHMENT NOTICE 02/2025
Dated: 11 March 2025

Transfer Section 3, Water Authority, is established at Marrow Bank pumping station.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AZ) | Transfer Section 3 | `formation` | operator stated: Northern Grid Works |
| `m2` (bulletin-AZ) | Redlow pumping station | `place` |  |
| `m3` (bulletin-BA) | Transfer Section 3 | `formation` | operator stated: Water Authority |
| `m4` (bulletin-BA) | Marrow Bank pumping station | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED on both, and DIFFERENT |
| geography | STATED on both, and different |
| designation | STATED on both, and IDENTICAL |
| time | STATED six days apart (2025-03-05, 2025-03-11) |

### Required outcome (prose - choose your own mechanism and values)

No fusion by any route - not on the exact name, not on the design, not through any similarity or relational path, and not on the grounds that each is the only body of that title in its own publisher's records. Two bodies survive in two operator worlds. And because they never merge, the two sites never become one body's history, so no move is drawn either. The protection has to sit on every path that can reach a merge, including whichever path runs first and cheapest.

### Tempting but wrong

- Fuse on the exact normalized title, on the earliest and widest path, where none of the later caps or bands applies.
- Treat the operator as one score contributor among several, so a perfect title match outweighs it.
- Guard only the careful comparison and leave the cheap exact-name path ungated, so the test passes while the hole stays open.
- Fuse and then read the two different stations as a relocation.

### Negative gold - spans that must produce NO claim

- Two operators' own bulletins are not two independent looks at one body.

**Corpus:** EXERCISABLE IN KIND, and deliberately planted - one designator-string collision decoy, a foreign body whose title collides with subject-side strings, with the answer key stating the document must not be read as being about the subject. Every discriminating signal sits outside the numeral. Being off-subject limits what it demonstrates, but it is the one place in the corpus where this gate can bite on real data.

## `F10b-one-name-three-kinds-of-thing`

**Scope:** 9 (G19: cross-type non-fusion)  
**Refs:** G19 (cross-type fusion is reachable through the same hole as cross-operator fusion); the area-versus-site distinction (an area is where something might be; a site is where it is)

**Purpose.** One distinctive name doing three jobs in one document: a station, the company that runs it, and the district it stands in.

**Why it is hard.** This is the ordinary way places are named, so it is common rather than exotic - and each pair fails for a different reason, which is why one gate has to cover all three. The district is the subtlest: fusing it with the station does not look like an identity error at all, it looks like knowing where the station is, and it silently attaches district-sized geography to a station-precision fact.

### Documents

**`register-BB`** - curated establishment register, source grade **B**, regional regulator's compiled register, dated 2025-03-18

```
CALDONIA REGIONAL PLANT REGISTER - EXTRACT 12/2025
Compiled 18 March 2025

Marrow Bank pumping station is operated by Marrow Bank Water Ltd under contract to the Water Authority.
The station's transfer plant is of the TL-40 type.
Marrow Bank is also the name of the district in which the station lies.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (register-BB) | Marrow Bank pumping station | `place` |  |
| `m2` (register-BB) | Marrow Bank Water Ltd | `operator_org` |  |
| `m3` (register-BB) | Marrow Bank | `area` | the district, stated by the document to be a different thing from the station |
| `m4` (register-BB) | the Water Authority | `operator_org` |  |
| `m5` (register-BB) | TL-40 | `design` |  |

### Hand-authored coreference clusters

**`bb-1`** (register-BB) - category **`NAME_VARIANT`**, anchor `m1`, members `m2`, `m3`, bind truth **`over_bound`**

> Marrow Bank pumping station is operated by Marrow Bank Water Ltd under contract to the Water Authority.

Three kinds of thing bound on one shared token, and the document explicitly says the district is also called Marrow Bank - i.e. it states the collision rather than an identity.

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED twice, in two different roles |
| geography | STATED as a station and, separately, as a district |
| designation | ABSENT |
| time | STATED as the compilation date (2025-03-18) |

### Required outcome (prose - choose your own mechanism and values)

Three nodes, no fusion between any pair, by any route including an alias route: a site, an organisation and an area are three kinds of thing. The area in particular must not be treated as a site - it is a coarser thing entirely, and using it as the station's location silently degrades every fact hung on the station's position. The document's real content - which body operates the station, and under whose contract - should survive, and where there is no lane for it the absence is reported rather than flattened into an identity.

### Tempting but wrong

- Fuse the station with the district, which reads as helpfully locating the station and in fact attaches district-sized geography to a site-precision fact.
- Fuse the station with the company that runs it.
- Fuse the contractor with the principal because both are organisations named in one clause.
- Drop the district mention entirely because it is 'not a site', losing the fact that the name is ambiguous - which is the very thing the next reader needs to know.

### Negative gold - spans that must produce NO claim

- 'Marrow Bank is also the name of the district' is the document stating a name collision - the strongest evidence in the fixture, and evidence against identity, not for it.

**Corpus:** EXERCISABLE - corrected and stronger than I first wrote. The corpus carries two legal entities of one shipping group on a single line (a national agent and a European carrier) which must not merge; a research institute named two different ways in one parenthesis, colliding by naming pattern with a different organisation's institutes that the answer key says must stay distinct; and - the sharpest cross-boundary case in the corpus - one bare locative phrase used for sites in two different countries, in both halves of the corpus, one of them a missile-launch rumour and the other the subject's own site.

## `F10c-the-alias-route-must-be-gated-too`

**Scope:** 9 (G19: covering the alias branch)  
**Refs:** G19 (an alias equivalence must be a real link between two different names, not a name equal to itself; and the alias branch must be gated by kind and by operator); an alias table is a name-normalization aid: it carries no source, no date and no assertion

**Purpose.** F10a's two same-titled bodies plus an alias table - including one entry whose two sides are the same string, and a third document using a short form with no operator attached.

**Why it is hard.** A self-referential alias entry makes every name its own alias, so a comparison that consults the alias table gets a hit for free and never reaches the checks that live on the direct-name path. The route is invisible: the operator and kind gates are all present and correct, and none of them is on the path that fires. The short-form mention then shows what an alias table can and cannot settle - it resolves a string, never a body.

### Documents

**`bulletin-AZ`** - operator establishment bulletin, source grade **B**, operator of the asset (interested party), dated 2025-03-05

```
NORTHERN GRID WORKS - ESTABLISHMENT BULLETIN 04/2025
Dated: 05 March 2025

Transfer Section 3, Northern Grid Works, is established at Redlow pumping station.
```

**`bulletin-BA`** - operator establishment bulletin, source grade **B**, a different operator's own establishment bulletin, dated 2025-03-11

```
WATER AUTHORITY - ESTABLISHMENT NOTICE 02/2025
Dated: 11 March 2025

Transfer Section 3, Water Authority, is established at Marrow Bank pumping station.
```

**`press-BC`** - trade press item, source grade **C**, trade press, recycles operator briefings, dated 2025-03-25

```
CALDONIA PLANT MONTHLY - 25 March 2025

TS3 has taken over the Ashgate transfer yard this month.
```

### Supplied alias data (editable data, not a source)

| Entry | Note |
|---|---|
| `'Transfer Section 3' -> 'Transfer Section 3'` | a self-entry: the same string on both sides. It asserts nothing, and it makes the name its own alias. |
| `'TS3' -> 'Transfer Section 3'` | a genuine short-form alias, and it says nothing about WHOSE Transfer Section 3. |

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (bulletin-AZ) | Transfer Section 3 | `formation` | operator stated: Northern Grid Works |
| `m3` (bulletin-BA) | Transfer Section 3 | `formation` | operator stated: Water Authority |
| `m5` (press-BC) | TS3 | `formation` | no operator stated anywhere in the item |
| `m6` (press-BC) | the Ashgate transfer yard | `place` |  |

### Discriminators

| Discriminator | State |
|---|---|
| operator | STATED and DIFFERENT on the first two; ABSENT on the third |
| geography | STATED on all three, all different |
| designation | STATED on all three, and equal after the alias table is applied |
| time | STATED (2025-03-05, 2025-03-11, 2025-03-25) |

### Required outcome (prose - choose your own mechanism and values)

Three things. First, an alias entry whose two sides are the same string is not an alias link and must license nothing - otherwise every name is its own alias and every same-named pair is reachable by a route that consults neither kind nor operator. Second, the alias route must be gated exactly as the direct-name route is: the two same-titled bodies under different operators must not fuse through the alias table either. Third, the short-form mention resolves to a title, not to a body: with no operator stated it may not be attached to either candidate, and it is held with a gap naming the missing discriminator. An alias table normalizes names; it is not a source-stated equivalence, and it carries neither provenance nor a date.

### Tempting but wrong

- Gate the direct-name comparison and leave the alias route open, so every gate passes and the widest path stays open.
- Treat an alias hit as an identity assertion, giving an editable convenience file the authority of a sourced claim.
- Attach the short form to whichever candidate has more evidence, or to the one whose site is nearest to the yard.
- Delete the self-referential entry and consider the matter closed, without gating the route it exposed - the next such entry re-opens it.

### Negative gold - spans that must produce NO claim

- 'has taken over the Ashgate transfer yard' is a stated change of custody with no operator attached - keep it, unattributed.

**Corpus:** NOT EXERCISABLE as authored, and I checked: the seed place gazetteer holds 74 alias entries and NONE has the same string on both sides, so the self-referential entry in this fixture is invented to make the route testable. What the corpus does supply is what an ungated transitive alias route would eat: a redesignation chain the document itself says is not consistently recorded, a person-name chain of five spellings that would join a civilian import, a second civilian import and a defence consignment, and two truncated telephone numbers sharing a prefix - a false edge built from a redaction artefact.

# Shape 11 - The thin mention - under-determined, never attributed and never collapsed

## `F11a-thin-mention-must-stay-under-determined`

**Scope:** 7 (thin context degrades to under-determined plus a named gap)  
**Refs:** the highest-risk piece of the design: how a thin-context bind degrades to under-determined plus a gap instead of fabricating or collapsing; D-13.8 (an absent discriminator leaves a thing under-individuated and flagged, never back-filled); D-13.13 (never reify what no source names)

**Purpose.** A single sentence naming a design and nothing else - no place, no holder, no date - arriving into a graph that holds exactly one well-evidenced instance of that design.

**Why it is hard.** The pull is almost irresistible and it is a coverage artefact: there is one candidate, so the mention looks unambiguous. It is the same fallacy as the anaphor gate's failure case moved to a bigger scope - uniqueness in our own data says nothing about uniqueness in the world, and a graph that grows by attaching thin mentions to its best-attested nodes concentrates evidence exactly where it is least warranted. The opposite error is equally available: throw away a sourced fact because its subject is unclear.

**Graph context.** Elsewhere in the sandbox the graph holds one well-evidenced instance of this design: six skids at Redlow, held by Northern Grid Works, seen by two vendors. It is the only candidate - and being the only candidate is a fact about our collection, not about the world.

### Documents

**`press-BD`** - trade press item, source grade **C**, trade press, no stake, dated 2025-08-12

```
CALDONIA PLANT MONTHLY - 12 August 2025

A TL-40 set has been re-cabinetted this quarter. No location, holder or date of works is given.
```

### Mention inventory (what the extractor emitted)

| Mention | Surface form | Declared kind | Note |
|---|---|---|---|
| `m1` (press-BD) | A TL-40 set | `unknown` | a design is named; whether this is an instance, a holding or a class statement is not stated |

### Discriminators

| Discriminator | State |
|---|---|
| operator | ABSENT, and STATED ABSENT ('no holder is given') |
| geography | ABSENT, and STATED ABSENT ('no location is given') |
| designation | ABSENT |
| time | ABSENT beyond 'this quarter'; the item's date is 2025-08-12 |

### Required outcome (prose - choose your own mechanism and values)

What the item supports is a design-level fact - a set of this design was re-cabinetted in that quarter, on one middling source - and nothing more. It must not be attached to the one instance of that design the graph happens to hold, and it must not be dropped: it is a sourced statement whose subject is under-determined, so it is recorded as such, with a gap naming exactly what is missing (which set, held by whom, where) and what would settle it. No placeholder instance may be minted with an unknown place and an unknown holder - that is a sighting no one reported, at no place, on no date. The item's own statement that the holder and location are not given is itself worth keeping: a stated absence tells an analyst where the coverage stops.

### Tempting but wrong

- Attribute the works to the only instance of that design in the graph - the anaphor fallacy at collection scale, and it grows more confident the sparser the coverage gets.
- Drop the fact for want of a subject, losing a sourced statement and leaving no record that it was seen.
- Mint a placeholder instance with unknown place and unknown holder, so the graph gains an individual no source describes.
- Read 'no location, holder or date of works is given' as an absence of information rather than as the information it is.

### Negative gold - spans that must produce NO claim

- 'this quarter' is not a date.
- 'No location, holder or date of works is given' is the source stating its own limits - keep it as a gap.

**Corpus:** EXERCISABLE, strongly - upgraded. The corpus's thinnest document types its object only as 'some kind of solid-fuel job', flips its identity twice in one sentence, gives its location as two nameless definite descriptions, dates it from a recycled older image, and flips its whole class in the final line. Elsewhere the corpus has a post stating 'no date given in that post btw, no location either, just \"a designated site\"', a document with no date at all, and a commissioning event with a precise date and an undisclosed garrison. The one condition the corpus cannot supply is the fixture's sharpest edge - a thin mention arriving where exactly ONE candidate instance exists - because the corpus holds several presences of the subject design.
