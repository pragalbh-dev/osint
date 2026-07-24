# RK-SPIKE acceptance cases — rationale

One entry per case: the **shape**, **what it tests**, the **tempting-but-wrong** outcome, the
**correct** outcome, and the **spec line** that makes it correct. A case with no citation would be
opinion, not a test. Sources: `tmp/conv/rk-spike-DECISIONS.md` (D-13.17…D-13.20),
`tmp/conv/rk-spike-verified-defects.md` (D1…D10, R*), `artifacts/spine/13-…-replumb.md` (§3a, §4, §5,
§6, §7, §11), `artifacts/plan/01-replumb-implementation-plan.md` §5 (G15/G16/G18), `CLAUDE.md`,
`artifacts/spine/04-credibility.md`, `artifacts/working-principles.md`.

All entities are invented (Zarrin / Marnian services, TL-7B Sarband, Meridian Precision Works, sites
Kotra East / Barha / Sarband Garrison). Nothing under `corpus/**` or `answer_key.json` was read or
touched; the cases are self-contained.

The open questions — every place the spec is **silent, ambiguous or self-contradictory** — are at the
end (O1–O12) and are referenced from the cases that hit them.

---

## D-13.17 — Tier-0 auto-bind, graded by coref category

### rk-01 · alias from a low-grade source must NOT bind
**Shape.** One grade-**E** document; two `unit` mentions with different names, same service branch,
no other structured facts; an `EXPLICIT_EQUIVALENCE` cluster whose quote contains **both** surfaces
inside a parenthetical.

**Tempting-but-wrong.** Honour it: the extractor labelled it an explicit equivalence, the quote checks
out verbatim, so bind. That is the adversary's cheapest attack — a planted alias fuses two formations
into one and, because the bind is uncapped, nothing downstream can question it.

**Correct.** Not authoritative; one referent atom per member; the pair is raised, never fused.
The **grade** gate is what fails — the structural gate passes, so the case isolates it.

> "It must *also* clear a **source-grade floor**, because a coref bind currently acts **harder than the
> assertion it most resembles**… The weaker-evidenced channel acting harder is an inversion, and
> spine/13 §5's doctrine is explicit: **stated ≠ trusted.**" (D-13.17)
> "an authoritative coref bind must clear a source-grade floor set **strictly above** the
> stated-`same-as` floor" (R10.1)

Deliberately no structured discriminator on either side: whether the two are "really" one formation is
unknowable from the document, and that is the point — a grade-E equivalence buys a *question*, not a
fusion. Grades E and B (never C/D) keep the case independent of the configured floor value (O9).

### rk-02 · the same sentence at grade B must bind
**Shape.** `rk-01`'s document byte-for-byte, at grade **B**. One variable changed.

**Tempting-but-wrong.** Refuse it too, because two differently-named batteries "look like" two things.
That forfeits the biggest fragmentation lever and re-labels our own grain choice as a collection gap.

**Correct.** One shared referent atom over both members; authoritative; not declined; fused.

> "Only an **authoritative** cluster mints **one shared referent atom**." (D-13.17)
> "Tier 0 … kills intra-document fragmentation… **Biggest lever**." (spine/13 §6)

Without this case, `rk-01` is passed by an implementation that binds nothing.

### rk-03 · a category mislabel must fail the structural gate
**Shape.** Grade **A**; category `EXPLICIT_EQUIVALENCE`; the quote occurs verbatim and has a
parenthetical — but it contains only the **first** member's surface.

**Tempting-but-wrong.** Trust the label: the category is authoritative and the quote is real.

**Correct.** Structural gate **fail**, grade gate **pass** (so the refusal is attributable), not
authoritative, not fused.

> "quote contains **both** members' surface forms · quote contains a **configured equivalence
> marker**" (D-13.17 policy table)
> "A model's self-report is not evidence; a model's self-report plus a structural check any reader can
> re-derive is." (D-13.17)

### rk-04 · `NAME_VARIANT` is raise-only, permanently
**Shape.** Grade **A**; two near-identical `manufacturer` names; category `NAME_VARIANT`; the quote
names both surfaces. Every check a naive reader would run passes.

**Tempting-but-wrong.** Bind it — the names are obviously variants and the source says so. This is the
single most seductive case in the suite, and it is exactly the deleted lane wearing a new predicate.

**Correct.** Raise-only: one atom per member, not fused, and the pair's only support is the name, so it
carries a ceiling at *possible*.

> "**`NAME_VARIANT` is raise-only for a mechanical reason, not out of caution.** Because an
> authoritative pair bypasses banding and fuses at 1.0, 'authoritative `NAME_VARIANT`' *is* the
> exact-normalized-name auto-merge lane that D-13.1 exists to delete — rebuilt on a different
> predicate, and immune to the very cap (name-alone ⇒ *possible*) that D-13.10 introduces to replace
> it." (D-13.17)

### rk-05 · an anaphor with a type-unique antecedent must bind
**Shape.** Grade B; one `unit` mention, one anaphoric `unit` mention, **plus** a `basing_site` and a
`variant` mention. The anaphor's `based-at` edge carries the document's location fact.

**Tempting-but-wrong (two ways).** (a) Refuse all anaphora as untestable — which manufactures nameless
orphans. (b) Run the uniqueness check over *all* other mentions rather than *compatible-type* ones, and
refuse because the site and the variant are "other candidates".

**Correct.** Authoritative; the anaphor joins its antecedent; the merged instance carries both the
designation and the location.

> "**type-unique antecedent** — the document contains no second mention of a compatible entity type
> that the anaphor could mean (checkable against coref's own mention inventory)" (D-13.17)
> "Raise-only for anaphora forfeits **lever 1**… and manufactures a fragmentation class of **nameless
> orphans**… reporting our own grain choice as a collection gap **mis-tasks the analyst**." (D-13.17)

### rk-06 · an anaphor with two same-type antecedents must NOT bind
**Shape.** Grade B; two `unit` mentions with differing designators, then an anaphor.

**Tempting-but-wrong.** Pick the nearest or the first antecedent. A silent pick is the same failure
class as D2 and cannot be corrected by cross-source corroboration, because the error is intra-document.

**Correct.** Structural gate fail; the anaphor fuses with **neither**; the two named units stay
separate (differing designations).

> "**Conditional:** if the type-unique gate is not built, this decision flips to raise-only. The gate
> *is* the decision." (D-13.17)

---

## D-13.18 — the rebuild may DECLINE a grouping

### rk-07 · an authoritative cluster with a conflicting critical discriminator must be declined
**Shape.** Grade **A**; a three-member `EXPLICIT_EQUIVALENCE` cluster whose quote names all three
surfaces (so **both gates pass** — the bind is licensed). Designators across the members are
`{5th, absent, 9th}`, in that order.

**Tempting-but-wrong (and this is the trap).** Read the cluster's discriminators as a collapsed
scalar. First-wins gives `designator = "5th"`, the absent one contributes nothing, and the conflicting
`"9th"` is **invisible** — so no conflict is detected and the over-bind becomes permanent, which is
disqualifying.

**Correct.** The grouping is **declined**: the referent atom is emitted with `declined: true` and a
reason, membership de-groups to claim-atom granularity, the conflicting members do not fuse, and **no
atom is lost**.

> "An intra-referent critical-discriminator conflict makes the rebuild **decline** the grouping —
> de-grouping to claim-atom granularity and raising for an analyst. **No atom splits; the grouping
> declines.**" (D-13.18)
> "**New code required, and it is not obvious:** an intra-referent conflict is currently **invisible**,
> because `Entity.attrs` is first-claim-wins scalar… The decline check must read **history**, not
> `attrs`." (D-13.18)

Full de-grouping to three instances is asserted **advisory** — see **O3**.

### rk-08 · an absent attribute is not a conflict, so the grouping must NOT decline
**Shape.** Grade A; two members; one states `designator: 5th`, the other states nothing.

**Tempting-but-wrong.** Decline on any asymmetry in the member values. That turns the decline
mechanism into a general de-binder and reverses lever 1.

**Correct.** Authoritative, **not** declined, fused, and the stated designation carries onto the
merged instance.

> "**critical-if-present**: absent → `unknown` (under-individuated + named gap), never fabricated,
> never rejected, **never a wall**." (D-13.8)

---

## D-13.19 — same-document contrast ⇒ a band ceiling at *probable*

### rk-09 · an enumeration must not fuse, and the stated figure is data
**Shape.** One grade-B document enumerating two sibling batteries — **identical surfaces**, identical
service branch, same `contrast_group`, same date, one at each of two sites.

**Tempting-but-wrong.** Fuse them: names identical, operator identical, same document, non-relocation
temporal score, high relational overlap. Then, because `based-at` is functional and keyed on the unit
alone, their two site edges become one unit's before/after and a relocation gets drawn — the D1 chain,
entered without a single planted lie.

**Correct.** Both survive; not fused; no drawn relocation; and the enumerated figure ("two") is
captured as data rather than merely used as an anti-merge hint.

> "A same-doc pair carries a prior *against* merging **only** when the source syntactically contrasts
> them (an enumeration, 'another battery', distinct designations)." (spine/13 §6)
> "A source that says *'two batteries'* is **stating the order-of-battle figure**. Capture it as a
> **sourced `count` attribute**… far more valuable as data than as an anti-merge hint." (D-13.19)

The *mechanism* is asserted with `any_of` (contrast ceiling **or** the G18 relationship wall): at two
sites at one date, either is target-correct and over-pinning one would fail a correct implementation.
The count assert is advisory — see **O1**, **O6**.

### rk-10 · the same shape with no contrast must fuse (presence)
**Shape.** One grade-B document; two `observed-at` sightings of the same design by the same operator
at the **same** site, three days apart; **no** contrast group.

**Tempting-but-wrong.** Treat two same-doc mentions as presumptively two things (over-correcting from
`rk-09`), or attribute the sighting to a formation.

**Correct.** One presence, fused; citizen is `presence`; **no** formation is minted and no `based-at`
is drawn — there is no organizational evidence.

> "Two co-located reports of HQ-9/P at Rahwali by the same operator collapse into one **presence** —
> safe, because a presence asserts only presence, which co-location evidence genuinely supports."
> (spine/13 §6)
> "Absence of contrast is **neutral** — never a prior *for* merging either." (D-13.19)
> G15: "An `observed-at` equipment sighting never becomes a `based-at` formation basing without
> organizational evidence."

### rk-11 · the same document plus a contrast must be capped
**Shape.** `rk-10` byte-for-byte **plus** a shared `contrast_group`. One variable.

**Tempting-but-wrong.** Fuse, because on merits they would (`rk-10` proves it) and the contrast is
"just a syntactic hint". Or shatter them with a veto — which is what makes an ORBAT list unusable,
since every ORBAT list contains an enumeration.

**Correct.** Not fused; `ceiling == "probable"` with a reason. Same site and same operator means no
wall is available, so the ceiling is the only mechanism that can hold this pair — which is what makes
`rk-10`/`rk-11`/`rk-12` an isolating series.

> "A same-doc **stated-contrast** pair is **capped at `probable`**: it reaches the analyst with its
> licensing quote and can **never auto-merge**." (D-13.19)
> "A band ceiling is threshold-independent… and states the intent directly: **contrast means 'not
> automatically', never 'not at all.'**" (D-13.19)

### rk-12 · the ceiling is ungraded — a grade-E contrast still applies
**Shape.** `rk-11` at grade **E**. This is the contested call and is pinned deliberately.

**Tempting-but-wrong.** Grade-gate it (analyst B's position), so a low-grade enumeration is ignored and
the pair fuses.

**Correct.** Still capped at *probable*, still reported.

> "**Decided: band ceiling at *probable*, ungraded** — the ceiling cannot shatter, which removes the
> harm the grade gate defended." (three-way disagreement table)
> "a **band ceiling cannot shatter anything** — it withholds a *new* fusion for one pair; it cannot
> retract an existing merge… so the gate would be a knob buying no risk reduction." (D-13.19)

### rk-13 · a ceiling cannot shatter a corroborated cluster, and cannot leak cross-document
**Shape.** Three documents. d01 (A) and d02 (B) report one formation with different surfaces and the
same `(service_branch, designator)`; d03 (C) enumerates "the 5th … and the 9th" as a contrast group.

**Tempting-but-wrong.** Let the enumeration act on the cluster: either retract the existing d01↔d02
merge, or block d03's "5th" from joining it. That is precisely the planted-document attack analyst B
raised, and it is why the veto rail was rejected.

**Correct.** d01↔d02 confirmed; d03's "5th" joins them; d03's two siblings stay separate; the doc-local
contrast never appears on a cross-document pair.

> "a **band ceiling cannot shatter anything**… it cannot retract an existing merge, and a cluster can
> still form transitively through its other pairs." (D-13.19)
> "it scopes the contrast channel so a doc-local contrast cannot leak onto cross-doc pairs" (D-13.19,
> on the `Entity.doc_ids` carrier)

---

## D-13.20 — the discriminator ladder

### rk-14 · a shared designation with differing operators must not confirm
**Shape.** Two documents; **identical** unit names; identical `designator: 3rd`; different service
branches (Zarrin vs Marnian).

**Tempting-but-wrong.** Confirm — the designation matches and the names are byte-identical. Note the
names being identical is deliberate: it is also the D3(b) laundering path, where name-sameness counts
as durable identity support and short-circuits the caps.

**Correct.** Not fused, and the refusal is a reported **wall**, not a quiet low score.

> "Designations are **reused across armies and across time**. One shared designation string may
> **never** confirm a formation merge." (D-13.20)
> "a **discriminator conflict** (different operator, incompatible geo at overlapping times) → **hard
> wall**." (spine/13 §7); "never across operators within the instance layer" (§3)
> D7: an unreported wall is "non-transitive *and unreported* while G18 passes. **The gate must name the
> channel and assert an analyst-visible reason.**"

### rk-15 · the composite `(operator, designation)` key must confirm
**Shape.** Two independent documents, different surfaces ("3rd Air Defence Battalion" / "3 ADB"),
different dates, same branch **and** same designator, same site.

**Tempting-but-wrong.** Withhold, because there is no serial number.

**Correct.** Confirmed, caps lifted. This is the instance layer's must-succeed case; without it,
`rk-14` and every cap case are passed by an implementation that confirms nothing.

> "**`hard_id_fields.unique` is a list of composite AND-keys** — `(service_branch, designator)` is an
> identifier; a bare `designator` is not." (D-13.20)
> "composite unique id … **lifts all caps**" (D-13.20 rung table)
> "**Confirmed identity does not require a unique id**… corroborated discriminator + relational
> agreement can reach confirmed" (spine/13 §7)

### rk-16 · a name-only pair must not fuse at any floor
**Shape.** Two documents, each with a `manufacturer` mention and a `unit` mention. Both pairs share
**only** the name — no attributes, no edges, nothing. The `manufacturer` pair is the type whose
per-type floor was lowered (0.37) and is where D3's hole is arithmetically reachable.

**Tempting-but-wrong.** Fuse the manufacturer pair, because at the lowered floor a token-sorted
similarity of 0.80 clears it, and the name cap is only consulted in the post-fixpoint collection loop
— i.e. it demotes pairs that were only ever going to be queued and cannot stop a fusion.

**Correct.** Neither pair fuses; both carry `ceiling: possible`.

> "**R3.1** D-13.10's invariant — *name is a contributor, never a verdict, at every layer* — must bind
> **the fusion path**, not only the queue band." (defect D3)
> "**Gate clause (new, or a G16 clause):** assert that a name-only pair does not **fuse**, at *every*
> configured floor including per-type overrides." (defect D3)

The `manufacturer` half depends on design-layer nodes being observable — see **O2**.

### rk-17 · name plus one more signal must confirm (design layer)
**Shape.** Two documents; the same design name; both stating the same origin country and design bureau.

**Tempting-but-wrong.** Keep it at *possible* because "name never confirms". That reads the cap as a
prohibition on name-driven merges and re-introduces design-layer fragmentation the use case cannot
absorb.

**Correct.** Confirmed; the ceiling does not stay latched once a non-name signal agrees.

> "a name match reaches at most a *possible* merge, and one more trivially-available signal (shared
> manufacturer / component / co-citation) clears it, **so designs still collapse into one node in
> practice**" (D-13.10)

There is deliberately **no instance-layer counterpart** to this case: at the instance layer "a name is
**never** sufficient; identity is fully earned" (spine/13 §7), and `rk-15` is that layer's
must-succeed mirror instead. The spec does not enumerate exhaustively what counts as "one more
signal"; an agreeing declared discriminator is the ladder's own next rung up from name, and
country-of-origin is named as a design-layer discriminator in §7 ("A manufacturer or country-of-origin
conflict still **walls** the merge").

### rk-18 · an unnormalized operator value must not false-wall a legitimate merge
**Shape.** Three documents reporting one formation; `service_branch` is given as `ZAF` (initialism),
`Zarrin Air Force` (expansion), and `"  zarrin  air  force "` (case + whitespace).

**Tempting-but-wrong.** Compare raw values with `==`, find "conflicts", and wall — shattering a
formation that three sources agree on. This is D5's live failure, and it is why the shipped config
keeps `service_branch` at `supporting` (i.e. inert) instead of `critical`.

**Correct.** No wall on either pair; both merges hold; one formation.

> G18: "**value normalization (PAF ≡ 'Pakistan Air Force') fires before the wall is tested**"
> "**R5.2** Value normalization is a **prerequisite**… and must apply before conflict detection **and**
> before namespace derivation… normalizing only at conflict time would leave namespaces split."
> The shipped config states the consequence itself: an exact-match critical wall "SHATTERS legitimate
> merges". (D5)

An initialism/expansion pair was chosen precisely because a generic normalizer can resolve it without
a hand-authored equivalence entry — the case format has no config channel (**O9**).

---

## The non-negotiable

### rk-19 · thin context must degrade to under-determined plus a named gap
**Shape.** d01 (grade C): equipment observed at a site, no organizational evidence. d02 (grade C): a
named formation with no site of its own — the look-alike.

**Tempting-but-wrong.** Two fabrications, both one step away. (a) Attribute the sighting to the
neighbouring formation, producing "the 5th Air Defence Regiment is based at Kotra East" — an assessment
no source made. (b) Collapse the presence into the look-alike, or copy its designation onto the
presence's discriminators.

**Correct.** A `presence` only; designation `unknown`; nothing fused; **no** `based-at` drawn; and an
explicit gap with a non-empty `missing` list and a literal analyst-facing sentence.

> "where evidence is **absent, ambiguous, or contradictory**, the system returns an explicit
> **'insufficient evidence to assess'** — naming what is missing and when next coverage is due.
> **Fabricated or hallucinated assessments in evidence-sparse cases are disqualifying.**" (CLAUDE.md)
> "We do **not** force a formation node: reifying an organizational individual we cannot source would
> violate the non-negotiable." (spine/13 §3a)
> "Because the template is explicit, the **gap statement is generated, not hand-written.**"
> (spine/04)

The "when next coverage is due" half is advisory only — nothing in the input contract carries a
freshness window or collection schedule (**O12**).

---

## The verified defects

### rk-20 · co-location must not manufacture a relocation (defect D1)
**Shape.** Three grade-B documents, same design and operator throughout, **no designations anywhere**.
d01 and d02 put equipment and an unnamed battery at Kotra East two days apart; d03 puts them at Barha
five months later.

**Tempting-but-wrong.** The path of least resistance, every link of which is verified in the current
substrate: co-located same-named batteries fuse into one unit → `based-at` is functional and keyed on
the unit → their two site edges become one unit's before/after → the supersede promoter clears the
credibility floor, marks the pair machine-adjudicated, **pops it out of the analyst's queue**, and —
because the targets differ — **draws a relocation edge**. One identity error, one fabricated movement
assessment, no analyst.

**Correct.** The safe half happens (the two Kotra East presences fuse); the formations do **not** fuse;
the presence at Barha is a different presence; **no relocation is drawn**; and the residual is reported
as a formation-count gap with a sentence.

> "**Gate clause (G16, amended):** G16 must assert **the absence of a derived `supersedes` / drawn
> relocation edge**, not merely the absence of a confirmed merge. As written it goes green while the
> harm it exists to prevent is realized one stage downstream." (defect D1)
> "**R1.2** A formation merge that rests on co-location must never fuse, therefore never create a
> shared supersede instance key."
> "Merging co-located reports into one *presence* is safe…; merging them into one *formation* on
> co-location alone would **undercount the adversary's order of battle**." (spine/13 §7)
> "The residual is a **first-class coverage item**: *'HQ-9/P presence at Rahwali confirmed;
> formation/unit count unresolved (1–2 candidates); designation coverage needed'*." (spine/13 §7)

The absence of the drawn relocation is the suite's single most important assertion — it is the clause
G16 does not currently contain, and the harm is realized one stage *after* the merge decision the gate
inspects. Note the dates: two days apart for the co-located pair, five months for the distant one, so
no configured overlap window changes the answer (**O9**).

### rk-21 · an earned relocation must be drawn (mirror of rk-20)
**Shape.** Two independent documents, same `(branch, designator)`, two field sites of the same
`site_type`, five months apart.

**Tempting-but-wrong.** Withhold everything after being burned by `rk-20`. A system that can never
state a movement is not honest, it is useless — and R1.4 conditions the withholding on the identity
being sub-confirmed, not on the edge being a relocation.

**Correct.** Identity confirmed on designation continuity; the relocation is drawn, oriented
earlier-site → later-site.

> "*confirmed relocation* → **+** designation continuity or an explicit transition claim
> (credibility-gated)." (spine/13 §6 ladder)
> "**R1.4** … Machine promotion is only legitimate over an identity the system actually earned."

### rk-22 · a garrison plus a forward site is not a relocation (requirement R1.3)
**Shape.** One formation (identical composite key) reported at a `garrison` and at a `field site` four
days apart.

**Tempting-but-wrong.** Read the two basings as a movement and draw a relocation, because `based-at`'s
supersede key is the unit alone and the targets differ.

**Correct.** No relocation drawn. **The identity question is left advisory** because the spec
contradicts itself here — see **O5**.

> "**R1.3** `based-at`'s supersede instance key must be tagged by **site_type**… so a unit legitimately
> at a garrison *and* a forward site is two valid instances rather than a relocation."
> "**The sub-scope limitation must be closed in the design, not deferred to a Tier-4 refinement.**"
> (defect D1)

### rk-23 · two candidate formations, never a silent pick (defect D2)
**Shape.** One document; one sighting at a site; `inducted-into` links from that equipment to **two**
differently-designated formations.

**Tempting-but-wrong.** Take the best-evidenced candidate and drop the other — with no skip record, no
coverage item, no gap. The order of battle is undercounted **with no merge involved**, so neither G15
nor G16 can see it, and the truncation is the only rejection path in the pass that logs nothing.

**Correct.** Two attributions, or one plus an explicitly named gap; either way the second candidate is
visible somewhere an analyst reads.

> "**R2.1** two candidate formations ⇒ **two attributions, or one attribution plus an explicitly named
> gap. Never a silent pick.**" (defect D2)
> "**Gate clause (G15, amended):** G15 as written passes *vacuously*… add the clause that actually
> bites: *a truncated/ambiguous formation attribution must produce a named gap.*" (defect D2)

### rk-24 · a reprint is not independent corroboration
**Shape.** Two grade-B documents carrying **one** underlying observation: identical surfaces, identical
attributes, identical date. The composite key matches, so `rk-15`'s reasoning would confirm.

**Tempting-but-wrong.** Confirm on "two sources agree" — the cleanest-looking evidence in the suite,
and manufactured.

**Correct.** Not confirmed; withheld, queued and reported.

> "**Independence.** 'Enough independent corroboration' explicitly inherits the corroboration ledger's
> source-independence / too-clean machinery (`spine/04`): two derivative reprints of one almanac must
> not confirm an instance merge." (spine/13 §7; D-13.9(b))
> "**Two reprints of one almanac must not confirm an identity merge.**" (defect D6)

Expressible only as verbatim duplication, because the input contract carries no source identity —
**O8**. This is the case I have least confidence any implementation can pass *as specified*, and the
contract gap is the reason.

---

# Open questions — where the specification is silent, ambiguous, or self-contradictory

These are findings for the orchestrator, not complaints. Each one is a place where I could not derive
the expectation from the spec and had to either weaken an assert to advisory or leave a shape untested.

**O1 — No slot for a sourced `count`.** D-13.19 adopts "capture the stated OOB figure as a sourced
`count` attribute" as a first-class outcome, but the output contract has nowhere to put it
(`discriminators` is for identity discriminators). The *input* also carries no document text, so the
only recoverable form of "two batteries" is the **size of the `contrast_group`**. Asserted advisory in
`rk-09`. If the count matters, both ends of the contract need a field.

**O2 — No slot for design-layer nodes.** `instances[].citizen` follows §3a's two citizens
(presence/formation), so a `manufacturer` or `variant` node has no handle. Yet D-13.10 binds the name
cap "for *every* layer, including design", and D3's arithmetic hole is reachable **only** at the
design-layer per-type floors (`manufacturer`/`trading_org` 0.37). So the most reachable instance of the
most important cap is the least observable. `rk-16`/`rk-17` assert through `pair_verdicts` and mark the
membership asserts advisory.

**O3 — After a decline, may a conflict-free sub-pair re-bind?** D-13.18 says "de-grouping to claim-atom
granularity and raising for an analyst" — it does not say whether the de-grouped atoms remain eligible
for Tier-1 comparison. F5 ("Tier 1 compares *all* provisional-instance pairs, including same-document
ones") argues yes; "raising for an analyst" argues the whole grouping becomes one analyst question.
`rk-07` therefore pins only that the *conflicting* members stay apart, with full 3-way de-grouping
advisory.

**O4 — Does a *relationship* conflict trigger the decline?** D-13.8 defines discriminators as
"attributes + relationships + derived geo", but D-13.18's mechanics are framed entirely on attributes
("`Entity.attrs` is first-claim-wins scalar… must read history"). An authoritative coref cluster whose
members are stated at two different sites at overlapping times is the cheapest attack on the bind,
because the bind bypasses banding and every cap. **No case covers this**: I kept the shape out of
`rk-01`/`rk-02` so the grade-gate mirror stays uncofounded. It should get a case once the spec answers.

**O5 — R1.3 contradicts G18.** R1.3 requires that a unit at a garrison *and* a forward site be two
valid basing instances rather than a relocation — which presumes the unit **merged**. G18 requires that
"a **stated** `based-at`/`operated-by` conflict at overlapping times **hard-walls** a merge". Nothing
says differing `site_type` makes two basings non-conflicting, so as written R1.3's scenario can never
arise: the wall fires first and there is no unit to hold two instances. `rk-22` pins only the
no-relocation half and records which reading the implementation took. **This needs closing before S3
writes G18.**

**O6 — Presence or formation for a stated count?** D-13.19 says put the OOB figure "on the presence
(D-13.13)"; §3a says "formation counts come from OOB/white-paper/logistics sources". An enumeration of
*formations* (`rk-09`) should carry a formation count, but the decision names the presence.

**O7 — Is `instances` the provisional set or the post-resolution set?** The contract's single example
(one referent, one claim atom) cannot disambiguate, and `verdict == "confirmed"` = "the pair FUSED"
implies pair endpoints are pre-fusion provisional instances. My selectors are deliberately agnostic
(see README), but this matters beyond the spike: **G16 is phrased in terms of a pair verdict**
("cannot reach `confirmed` formation-merge") while **D-13.14's actual claim is about node counts** (the
order of battle is not undercounted). Those are the same assertion only once this is settled.

**O8 — No source identity or derivation channel.** A document carries only `source_grade`. The
independence guard (D-13.9(b), D6) cannot be expressed: `rk-24` resorts to verbatim duplication as a
"too-clean" proxy. Add `source_id` and/or `derived_from` to the input contract, or the guard is
untestable and D6 stays unverified.

**O9 — No config channel.** G6 requires the coref grade floor, the relationship wall's overlap window,
the normalization equivalence classes, the per-type merge floors and the co-location threshold to live
in config — but a case cannot supply any of them. Every case in this suite therefore keeps a wide
margin (grades E vs B only, never C/D; two days vs five months; an initialism a generic normalizer can
resolve). A per-case `config` block would make the graded gates directly testable instead of
approximately testable.

**O10 — Where does the licensing quote surface?** D-13.17 is emphatic that the raise-only mitigation is
fictional unless the analyst is handed the exact sentence, but the output's only prose slots are
`pair_verdicts.reason`, `ceiling_reason`, `withheld_reason`, `gaps.sentence`. Asserted advisory on
`reason` in `rk-01`/`rk-04`.

**O11 — Does a `coref: null` mention mint a singleton referent atom?** The spec covers authoritative
clusters (one shared atom) and loose clusters (one per member) but not mentions in no cluster at all.
I avoided asserting total referent-atom counts in any case containing coref-null mentions.

**O12 — "When next coverage is due" is not derivable.** The non-negotiable's sentence template requires
it (CLAUDE.md; spine/04's "next coverage due DATE"), but no input field carries a freshness window,
half-life or collection schedule. `rk-19` asserts the *named-missing* half hard and leaves the
*coverage-due* half unasserted.

**One further note, not an ambiguity.** F9 (only completed merges contribute relational weight) is
deliberately **not** pinned. A case asserting "a pair whose only support is a sub-confirmed anchor does
not confirm" cannot fail in the useful direction — an implementation with no relational signal at all
passes it — so it would be a gate that lies. The honest place for F9 is the disclosure the decision
already requires: *"relational scaffolding only helps where the anchor actually merges; a merely
`probable` anchor lends no support at all — it is a step function, not a graceful degradation."*
