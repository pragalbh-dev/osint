# RK-SPIKE — what building it taught me

Written by the corpus-blind implementer hand after building the
`characterize-and-cluster` prototype against `tmp/conv/rk-spike-DECISIONS.md`,
`rk-spike-code-facts.md` and `rk-spike-verified-defects.md`.

**Headline: the design holds up when built.** The four decisions compose into a
working pipeline, and the load-bearing claim — that a thin-context bind can degrade
to *under-determined + a named gap* rather than fabricating or collapsing — is real
and mechanisable. One architectural move made everything else fall out: **fusion is
licensed by a structural trigger, never by a score.** Once the score cannot fuse a
pair, defect D1 stops being a thing you defend against and becomes a thing that
cannot be expressed.

Six findings are load-bearing enough to change what S3 builds: B1, B2, B3, B5, C2, C4.

---

## A. Harder to implement than the decision text implies

### A1. "Authoritative" is a per-**cluster** label, but its gate evidence is per-**link**

D-13.18 correctly records that option (iii) — a per-link authoritative closure — is
not implementable, because the coref category is stamped per cluster
(`ingest/coref.py:375-379`). But the D-13.17 *gate* is inherently per-link: the
licensing quote must contain "**both** members' surface forms", and in a three-member
cluster there is no single "both". The implementer must invent a quantifier the
decision does not state.

I chose the **conjunction**: the cluster is authoritative only if *every*
anchor->member link passes its own gate. That is the safe direction, but it has a real
cost the decision never weighs — one bad link demotes an otherwise-good cluster to
*n* singletons, which can be *worse* recall than the per-link closure the decision
ruled out as unimplementable. This choice needs to be written into the spec, whichever
way it goes.

### A2. The gate needs an "anchor", and "anchor" is undefined at the point the gate runs

Production picks "the first claim-bearing member else `members[0]`"
(`ingest/coref.py:330`), but at gate time in the replumb the mention shape has no
claim id. I used "the first member carrying stated attributes, else the first by id".
Whichever S3 picks decides *which quote is tested against which surface form*, hence
which clusters bind at all. It is a load-bearing detail sitting in a footnote.

### A3. The caps turn out to be **reporting** mechanisms, not blocking mechanisms

D8 rightly renames "capped at probable" to "not fused; queued and reported". But once
fusion requires a durable structural trigger — which is what D-13.20 demands — the
caps become almost entirely redundant *for preventing fusion*: co-location, name-only
and perishable-only evidence produce no trigger anyway, so the merge was never
reachable. What the caps still do is **label the pair and raise the gap**.

That is a good outcome, but it inverts the emphasis. G16's real content is *"the pair
is reported with a named gap naming the missing unit-level discriminator"*, not *"the
merge is blocked"*. The gate should assert the reporting, because the blocking is
structural and would otherwise pass vacuously — the same failure mode the defect
register already found in G15.

### A4. The `ceiling` field has two incompatible readings and the contract admits both

"The band a cap clamped the pair to" and "null if uncapped" are different rules
whenever the score already sits below the ceiling. I chose **non-null whenever a cap
is in force**, because the alternative makes G16's own co-location cap invisible in
exactly the weak-evidence cases it exists for. Someone has to decide this before the
gate fixture is written, or the gate and the implementation will disagree silently.

---

## B. Underspecified or mutually inconsistent

### B1. Rung 2 and rungs 4+5 are the same test — and rung 2 bypasses R5.1

D-13.20 declares `(service_branch, designator)` a **composite unique identifier**
whose match "lifts all caps" (rung 2). Separately it says a **shared designation**
"never confirms alone" and requires "namespace compatibility **and** independent
corroboration" (rung 4, and R5.1 in the defect register). With `(operator,
designation)` as the declared composite key those are the *identical predicate* — so
rung 2 silently grants the fast path to exactly the evidence rung 4 was written to
restrain, and R5.1's independence requirement is bypassed.

My resolution: keep both as separate confirm triggers, and require independence
(>=2 distinct documents) on `corroborated_designation` while allowing
`composite_unique_id_match` on one document. That is a **choice, not a reading** — the
decision text supports either, and the difference is observable (a same-document pair
with a matching designation and operator either fuses or does not).

Confirming corollary from the run: the `designation-conflict` and
`identifier-conflict` walls **always co-fire**, because the composite key conflicts
whenever its designation component does. Two rungs, one veto.

### B2. The ladder's top rung is a hard veto on an **unnormalized** value

R5.2 makes value normalization a prerequisite for walling on *operator*, and gives the
exact reason — exact-match walling "SHATTERS legitimate merges". Designations have the
identical problem: `3rd` / `3` / `III` / `3 Svy`. Yet D-13.20 makes a **differing
designation the strongest wall in the ladder** with no normalization requirement at
all, and `unit.designator` is not even declared in `attribute_roles` today (defect D5).

Self-case `13-designation-spelling-veto` shows the consequence: `"3rd"` versus
`"III"`, same operator, hard-vetoed and permanently unmergeable. I added ordinal
folding, which handles the easy half of the problem; a designation **alias table** on
the same footing as the operator equivalence classes is required and is not in the
decision. **I believe this is an outright hole in D-13.20**, and it is the mirror image
of the hole R5.2 closes for operators.

### B3. No confirm trigger exists that a **place** or a **design** could satisfy — so lever 2 cannot exist

Under D-13.10 (a name match caps at *possible*, at **every** layer) plus D-13.20
(fusion needs a durable non-perishable trigger), the anchor and design layers have no
rung to climb: a place has no designation and no operator, so no composite AND-key, no
corroborated designation and no temporal continuity. In self-cases 10, 11 and 12, two
mentions of the *same depot name* sit at `possible` and never fuse. Designs are in the
same position unless a designator happens to be stated on both sides.

That collapses **spine/13 section 6 lever 2** ("clean anchor layers as relational
scaffolding"). The decisions doc already notes lever 2 is weaker than claimed for two
other reasons — F9, and `places.augment` running after `resolve_entities`. This is a
third and more fundamental one: it is not an ordering bug, it is that the ladder has no
rung for an anchor. And since the relational signal counts only *completed* merges
(F9), an anchor layer that cannot merge contributes exactly zero relational support —
the two weaknesses multiply rather than add.

Section 7's "per-layer policy profile" is the intended answer, but nothing states what
the anchor profile's trigger **is**. The concrete fix is small and worth stating: for a
place, **coordinates are a non-perishable identifier**, even though for a unit
geography is the perishable rung. So `perishable` must be declared per
*(type, attribute)* — which `config/resolution.yaml` already supports and the decision
does not use — and the anchor profile's composite key is `(coordinates)`.

### B4. D-13.19's contrast ceiling is inert in exactly the case it was designed for

Self-cases 07 and 08 differ *only* by the presence of a shared `contrast_group` and
produce identical verdicts (`probable`) and identical ceilings (`probable`) — only the
prose differs. The reason is A3: the co-location cap already holds the pair, so the
contrast ceiling adds nothing to an ORBAT enumeration of co-located siblings, which is
the motivating example.

The contrast channel changes an outcome **only** on a pair that would otherwise
*confirm*. That requires the source to both enumerate the pair as siblings *and* give
them the same composite identifier — i.e. to contradict itself (self-case 09, which
lands `probable` plus a `contrast-vs-identifier` gap instead of fusing). The channel is
worth having for that guard, but the decision oversells its reach: it buys a new coref
output lane and a new extractor field, and its non-redundant effect is one
self-contradiction check. That trade should be made with eyes open.

### B5. A **confirmed relocation manufactures relational evidence that origin == destination**

Discovered by running self-case 11, before I fixed it. Once the two unit instances
fuse, both site instances hold an identical `based-at -> <that unit>` neighbour key, so
"Depot Kestrel == Depot Larch" scored `relational: 1.0` and reached `probable` — two
demonstrably different depots pushed into the analyst's merge queue by the very
relocation that proves they are different.

Production has a mitigation for exactly this (the co-instance relocation exclusion,
`resolve/scoring.py:337-350`, which zeroes temporal and drops the shared neighbour), so
the hazard is known to the codebase — but **D-13.20's ladder text mentions neither the
hazard nor the mitigation**, and the re-key changes the shape of the relational key,
which is precisely when an unstated mitigation gets dropped. I fixed it by putting the
stated event time into the neighbour key for placement predicates (one config line,
`relational.time_scoped_predicates`), which states the same fix positively: *a dated
relationship to the same neighbour at two different times is not the same
relationship.* **This must be carried into S3 explicitly.**

### B6. The decline check's scope is unstated

D-13.18 says "a conflicting critical discriminator". Is a **perishable** conflict — two
places at overlapping times, *inside one coref cluster* — a decline? I said no: a
pairwise wall, not grounds to overrule a source's reading of its own text. But the
decision does not say, and the two answers differ observably on a document that reports
detachments.

---

## C. Where I think a decision is wrong

### C1. `stated_same_as_min_grade` is the wrong reference point for the coref floor

D-13.17/R10.1 sets the authoritative-bind floor "strictly above the stated-`same-as`
floor", and points at `critical_veto_min_grade: C`. But that is a floor on a **wall**,
not on a **bind**. Anchoring a fusion floor to a veto floor makes them move together
for no reason: if an analyst later loosens the veto floor to catch *more* conflicts,
the coref bind floor loosens with it — in the wrong direction, and silently. The floor
should be stated absolutely, or relative to the auto-merge channel it actually
resembles. I implemented it as specified (grade `B`, derived from `C`) and flag it.

### C2. The name-alone cap should not be a cap

Once fusion requires a durable structural trigger, "name alone reaches at most
*possible*" follows **arithmetically** from `name_weight < probable_floor`, which is
checkable at config-load time — my `scoring.invariants` does exactly that, and refuses
to load a config that breaks it. Keeping the cap *as well* creates a second place the
same policy lives, and defect D3(a) is precisely the failure mode of a policy dial that
does not cover every code path (`name_alone_caps_at_possible` is consulted only in the
post-fixpoint collection loop, `cluster.py:558-568`). One machine-checked invariant
beats two mechanisms that can drift apart. I implemented both as belt-and-braces, but I
would ship the invariant and delete the cap.

### C3. `UNAMBIGUOUS_ANAPHOR` being authoritative buys less than the decision claims

The decision's strongest argument is that raise-only "manufactures a fragmentation
class of nameless orphans" and forfeits the biggest fragmentation lever. But the
type-unique gate **only passes when the document contains exactly one compatible-type
mention** — which is exactly the document where Tier 1 could recover the antecedent
anyway, because there is nothing else for the anaphor to be pulled toward. Where the
gate *fails*, the orphan is created regardless. Self-cases 03 (gate passes, binds) and
04 (gate fails, orphan created with every discriminator `unknown`) are that pair.

So the benefit is real but narrow, and the "biggest lever" framing overstates it. I
would still ship it — the cost is one structural check — but the design note should not
lean on it, and the *measured* claim ("Tier-0 coref is the biggest fragmentation
lever") should be checked against the anaphor gate's actual pass rate before it is
repeated.

### C4. A single-source stated relocation is an unnamed fork in the D1 guard

The D1 guard says a relocation may be drawn only over an identity the system earned.
But a single grade-B source that authoritatively co-refers its own mentions and dates
two placements is asserting a movement about **its own referent** — no cross-source
identity was inferred, and refusing to draw it would suppress the honest, common case
(section 4: the source is authority on what its own "it" refers to; section 5: the
stated basing path is the *stronger* provenance path).

I made it drawable behind an explicit switch
(`relocation.allow_single_source_authoritative_identity`) so the concession is
auditable rather than buried. But **nothing in D1, R1.4 or spine/13 section 5 decides
it**, and it is the one place the guard admits a non-corroborated identity. It needs a
ruling before S3, because it is the difference between the relocation beat working from
one document and requiring two.

---

## D. Things the decisions got right that were not obvious until built

* **The band-name-not-a-float call (D-13.19) is worth more than its rationale says.**
  Because caps compose (a pair can fire three at once) the implementation needs a
  *lattice*, and band names give one for free — `min` over an ordered vocabulary.
  Coefficients would have needed a composition rule nobody has specified.
* **"Decline the grouping, never split the atom" (D-13.18) is genuinely cheap.** About
  fifteen lines, and it fell out of keeping the **full set** of member values per slot
  rather than a scalar — which is the same change the discriminator bag needs anyway.
  The two requirements pay for each other. The warning that the check must read history
  rather than `attrs` is exactly right: with a first-claim-wins scalar the conflict is
  invisible.
* **Splitting `name` from `discriminator` is as small as claimed**, and it immediately
  makes three separate policies expressible (the name ceiling, the name-impermeability
  of caps, and rarity grading) that cannot be stated at all while the two live in one
  `max`.
* **The `unnormalized` third state is the right shape for R5.2.** "Cannot test => do
  not wall, raise a gap" degrades safely with an *empty* normalization table: zero
  false walls, only gaps. That property means the table can be filled incrementally by
  an analyst without a flag day, which is worth stating in the design note.
