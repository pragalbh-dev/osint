# RK-SPIKE — Design Analyst B (failure-first)

Read-only analysis, 2026-07-24, against `design/resolution-redesign` @ c2a2b68. Premises: `tmp/conv/rk-spike-code-facts.md`
(treated as ground truth; every additional behavioural claim below is independently verified with a `file:line`),
`CLAUDE.md`'s non-negotiable, `artifacts/spine/13-*.md` §§3a/6/7/8/11/13, `artifacts/plan/01-*.md` §5/§7,
`artifacts/working-principles.md`. Corpus-blind: no `corpus/**`, no `answer_key.json`, no `SCENARIO_MANIFEST.json`
was opened. Method: start from the harm, derive the policy, then check buildability.

---

## Verdict summary

1. **(a)** Auto-bind **`EXPLICIT_EQUIVALENCE` only**, and only when a *deterministic structural test* corroborates the
   model's label (the licensing quote must contain **both** members' surface forms **and** a configured equivalence
   marker) **and** the asserting source clears a grade floor strictly above the stated-`same-as` floor.
2. **(a)** `NAME_VARIANT` → **raise-only permanently** (it is the name-verdict rule D-13.1 abolishes, wearing a category
   label). `UNAMBIGUOUS_ANAPHOR` → **raise-only permanently** (its licensing condition is un-re-derivable downstream).
3. **(a)** "Held looser" is only honest if the **referent atom is evidence *about* a grouping, not the address of the
   provisional instance** — claim atoms stay the split unit. Coref already emits a *claim*, never an entity id
   (`coref.py:385-392`); keep that and D-13.11 is satisfiable. Bind-as-address + "atoms never split" = irreversible
   over-bind = disqualifying.
4. **(b)** The contrastive prior is **not one thing**. Enumeration-with-distinct-fillers → a **credibility-gated,
   pairwise, non-transitive, always-reported wall**. "another/a second" → a **band demotion** (`auto → hitl`), not a
   coefficient. "Distinct designations" → **not a contrast at all**; route to the discriminator rail.
5. **(b)** Carriers: doc-sameness from `DocRef.file` via a rebuild-time atom→doc index (**never** `Entity.source_ids` —
   that is the publisher, not the document); contrast from a **new optional extractor field**, deliberately *not* the
   `distinct-from` channel, whose ungraded-transitive treatment is exactly the shatter vector we are refusing.
6. **(c)** Ladder by damage × exploitability: **differing-designation veto > temporally-witnessed continuity > shared
   designation (non-perishable discriminator, corroboration-gated — *not* a fast path to confirmed) > operator (only
   after value normalization) > geography (perishable; separator, never unifier) > relational > name (recall + capped
   contributor)**.
7. **(c)** Co-location cap **confirmed and sharpened**: there is no "probable merge" in this codebase, so the cap means
   *do not fuse; emit a candidate pair + a named coverage gap*. Presence-merge fine only if `count` is a sourced
   attribute — otherwise the presence merge silently answers "how many?" with 1.
8. **(c)** Of the two D-13.9 guards, the perishable cap **exists but is laundered by name-sameness**
   (`cluster.py:399-415`); source-independence is **not implemented in the merge path at all**. Fix the first, scope or
   disclose the second.
9. **(c)** F9 → **accept the gap and disclose it**: its error direction is under-merge (safe), and it accidentally blocks
   transitive fusion through a wrong anchor — protective in exactly our harmful direction.
10. **Most worried about:** a formation over-merge does not merely undercount — because `based-at` is **functional and
    unit-keyed** (`config/ontology.yaml:146`, `instance_key: [from]`), fusing two co-located batteries makes their two
    sites read as one unit's before/after, and the supersede path (`view/pipeline.py:795`) can promote that into a
    **drawn relocation**. An identity bug becomes a *fabricated movement assessment* — the non-negotiable breached
    structurally, and precisely what one planted parenthetical buys an adversary. **No gate currently checks this.**

---

## Decision (a) — Tier-0 auto-bind, graded by coref category

### Failure modes, ranked by damage × exploitability

**A1 — Planted in-document equivalence between two real formations. (Damage: catastrophic. Exploitability: maximal.
Recoverability: nil.)**
One sentence — *"the 8th AD Battalion (also known as the 12th AD Battalion)"* — is textbook `EXPLICIT_EQUIVALENCE`.
Damage chain: two real formations fuse → OOB undercount (the harmful direction per D-13.14) → and then, because
`based-at` is functional keyed on the unit, the two formations' two sites become one unit's before/after, the supersede
ordering runs (`view/supersede.py` via `view/pipeline.py:795 promote_supersessions`) and a **relocation is drawn**. The
system does not merely under-report strength; it *asserts an event that never happened*.
Exploitability is maximal because today the coref lane has **no source-grade gate whatsoever**: `_coref_pairs` gates on
`veto` membership, equal `etype`, `namespace_compatible` and `has_hard_conflict` — and nothing else
(`resolve/__init__.py:616-661`). Compare the structurally analogous lane: a source-stated `same-as` **is** grade-floored
and can only *raise*, never merge (`resolve/__init__.py:578-600`, `_best_identity_weight` at `:603-613`). So an opted-in
coref bind would be **less gated than the assertion it most resembles**, and would land at hardcoded identity confidence
**1.0** in the Phase-1 bootstrap (`cluster.py:465`) — the same confidence as a shared unique identifier.
Recoverability inside one document is **nil**: there is no independent second source inside one source, so
cross-corroboration cannot correct it, and if the bind mints the provisional instance's address, D-13.11's
"atoms never split" makes it permanent.

**A2 — Category mislabel (a pronoun chain reported as `EXPLICIT_EQUIVALENCE`). (Damage: as A1. Frequency: higher.)**
The category is a **model self-report with no structural test behind it**. Validation is set-membership
(`coref.py:303-305`) plus "the quote occurs in the document" (`_quote_supported`, `coref.py:253-260`, applied at
`:306-308`). Nothing checks that the quote **contains the member names**, and nothing checks that the quote's *form*
matches the claimed category. So a model can quote any real sentence and label it `EXPLICIT_EQUIVALENCE`.
**Which categories are robust to a mislabel?** As written, none. But they are not equally *testable*:
- `EXPLICIT_EQUIVALENCE`'s licensing patterns are **lexical** — parenthetical, apposition, acronym expansion, "also
  known as", "formerly", "Full Name (SHORT)" (`coref.py:124-130`). A deterministic re-derivation exists.
- `NAME_VARIANT` is testable, but the test is *string similarity* — i.e. it **is** the name-verdict rule D-13.1/D-13.10
  demote to recall. Making it authoritative re-imports lane 2 of the substrate bug through the ingest door.
- `UNAMBIGUOUS_ANAPHOR`'s licensing condition ("there is no second mention of that type it could mean") is a claim about
  the whole document that **no downstream code can re-derive** — the mention shape carries no spans and no offsets
  (`coref.py:156-163`), so proximity, ordering and scope are all unavailable. Its failure is silent by construction.

**A3 — Under-bind (Tier 0 misses a co-reference). (Damage: moderate, reportable. Recoverable.)**
Cost: thinner provisional instances → weaker cross-doc signal → larger honest residual. Recoverable **iff** Tier 1 sees
the pair, which is decision (b). The codebase already prices this asymmetry correctly: overlapping proposals resolve
first-wins with the comment *"under-merge is cheap"* (`coref.py:321-322`).

**A4 — The "held looser" trap. (Damage: disqualifying if built.)**
If a *loose* category still mints one shared referent atom, "looser" is a lie: atoms never split, so no later evidence
can undo it and spine/13 §4's promise that coref remains "a challengeable proposal" is false.

### The policy

**(i) Authoritative set = `[EXPLICIT_EQUIVALENCE]`, gated twice.** Two new preconditions, both deterministic:

- **Structural corroborator.** The licensing quote must (1) occur in the document (already enforced), (2) contain **both**
  members' surface forms, and (3) contain a configured equivalence marker (a parenthetical wrapping one form, or a term
  from a config list). All three ⇒ eligible to auto-bind; any miss ⇒ raise-only with the quote. This converts a model
  self-report into a fact any reader can re-derive, and it kills A2 for the only category we are trusting. ~20 lines of
  pure string work beside `_quote_supported`; markers in config (G6).
- **Source grade.** An eligible bind must clear a `coref_authoritative_min_grade` floor, set **strictly above** the
  stated-`same-as` floor `identity_raise_min_weight` — because the coref bind *merges at 1.0* whereas the stated
  `same-as` only *raises*. Note `identity_raise_min_weight: 0.0` today (`config/resolution.yaml:140`): the same-as floor
  is structurally present but dialled off; **do not inherit that value**. Justification on principle, not data: an
  in-document equivalence is a *single-source, uncorroborable* assertion, and spine/13 §5 states the doctrine outright —
  **stated ≠ trusted**; a grade-E source stating something still runs through source grade. The right sibling
  precedent is `_critical_attribute_walls`, which is credibility-gated at `critical_veto_min_grade: C`
  (`resolve/__init__.py:490-529`, `config/resolution.yaml:370`) and *raises* rather than acting when below floor
  (`__init__.py:499-501`) — mirror exactly that discipline.

**Answer to "does source grade gate a coref bind at all today?" — No.** `coref.py` never reads a grade, and
`_coref_pairs` (`resolve/__init__.py:616-661`) reads none. That is the single sharpest gap in decision (a).

**(ii) `NAME_VARIANT` and `UNAMBIGUOUS_ANAPHOR` are raise-only permanently** — not "for now". `NAME_VARIANT` because
authoritative name-equality is the abolished lane; `UNAMBIGUOUS_ANAPHOR` because it is untestable and fails silently. Both
still earn their keep: they arrive as Tier-1 candidate pairs **with their licensing quote**, which is strictly better than
today's queue item, because the analyst is handed the exact sentence.

**(iii) What "held looser" means mechanically — and how a wrong bind is undone.** The load-bearing constraint is that
**claim atoms remain the split unit and the referent atom is evidence about a grouping, not the address of the provisional
instance.** The current code already has the right shape and it must be preserved: coref emits a real `ClaimRecord` on a
dedicated `coref-same-as` predicate and mints a **claim** id, *never* an entity id (`coref.py:385-392`, verified; facts
§A2). Under that shape:
- rebuild **groups claim atoms**; the referent atom is a strong (or authoritative) grouping signal the grouping step
  consults — exactly as a coref claim is consulted today;
- a *loose* bind = an injected Tier-1 candidate pair (the mechanism already exists: `_candidate_pairs` accepts injected
  pairs, `cluster.py:203`; `_coref_pairs` already routes non-authoritative pairs to `raise_only`,
  `resolve/__init__.py:657-660`). Undoing it = rejecting a candidate;
- a *tight* bind that turns out wrong = an analyst split that **re-partitions the claim atoms** — which is precisely
  D-13.11's own mechanic ("a split is just atoms landing in two buckets"). No atom splits; the derived node id changes and
  the redirect map carries display continuity.
The forbidden shape is minting **one referent atom per *proposal* and using it as the instance address**: then an
over-bind is irreversible, and I reject that reading. D-13.7 and plan/01 RK-COREF item 1 ("the doc-local coref cluster
**GROUPS** the per-mention claim atoms and is where the referent atom is minted") can be read either way — it must be
written down the safe way before S3 starts.

**(iv) Resolving the principle collision.** `config/resolution.yaml:170-179` gives two reasons for the empty list. Reason 1
(the producer and consumer switches must be flipped in one deliberate motion) is **sound and should survive as a comment**.
Reason 2 — preserving the d10 "HT-233 (H-200)" orphan-alias beat an analyst is meant to earn — is a demo-preservation
argument, and working-principles #1 forbids it as a design input. **Target-correct policy is as above.** If a grade-B/C
parenthetical now auto-binds, the beat is lost, and **the data pass owes a re-carried beat** on evidence the target system
genuinely cannot auto-bind. Two clean shapes, either of which is a *better* demo:
- state the alias in a **low-grade** document (D/E) ⇒ the grade gate raises it, and the analyst earns it *with the reason
  visible* ("stated, but by a grade-E source");
- **split the alias across two documents** (doc A says HT-233, doc B says H-200, neither states the equivalence) ⇒ it
  becomes a Tier-1 *earned* identity problem rather than a reading problem, which is the capability actually being graded.

**Buildability:** all three parts are small and land inside S3's declared scope (`ingest/coref.py` +
`resolve/{__init__,rconfig}.py`). No new abstraction, no new store, no model call.

---

## Decision (b) — Tier-1 same-document comparison and the strength of the contrastive prior

### Failure modes at three strengths

**Too weak. (Damage: the dominant harm. Exploitability: high — needs no planted lie at all.)**
*"Two HQ-9/P batteries, at Rahwali and Nur Khan respectively"* — Tier 0 correctly leaves two provisional instances;
Tier 1 then fuses them, because *every* signal in the current scorer points the same way: near-identical names (so
`attribute_score` is high — `scoring.py:425-437` takes `max(name_sim, agreeing/present)`), a shared design and site
neighbourhood (relational), and `temporal_score` is **binary 1.0** on any non-relocation pair (`scoring.py:545-547`).
Result: OOB undercount **plus** the fabricated-relocation chain from the verdict summary. An adversary does not even need
to plant a false equivalence for this; they need only publish two real units described similarly.

**Too strong. (Damage: fragmentation we manufacture ourselves, which is worse than sparsity.)**
A document says *"the HQ-9/P battery at Rahwali… the unit… its HT-233…"*; Tier 0 under-binds two of those mentions. If
contrast is inferred loosely — different surface strings read as "the source distinguishes them" — and treated as hard,
they can **never** rejoin. That fragmentation class is created by our own grain choice, and it is *not* honestly
reportable: §6's whole defence of residual fragmentation is that it "reflects genuine evidential uncertainty". Reporting
a self-inflicted split as a collection gap **mis-tasks the analyst**, which is the operational face of the thing the
non-negotiable forbids.
Worse, if the prior is implemented as membership in `veto`, it is **transitive** (`violates_veto_transitively`,
`cluster.py:363-370`, re-applied in `finalise`, `:638-648`) — so one bad contrast in one document can shatter a cluster
assembled from five other documents.

**Right.** Contrast reduces confidence and blocks *fusion* for exactly the pair the source contrasted, is gated on the
contrasting source's grade, does not propagate, and is always visible to the analyst as the reason.

### Is syntactic contrast *stated anti-identity evidence* or a *graded prior*?

**Neither, uniformly — and treating the three cases as one strength is the mistake.** The existing stated-`distinct_from`
treatment is *hard, transitive and deliberately ungraded* (`resolve/__init__.py:567-575`: "Deliberately *not* graded or
type-gated"), and that doctrine is defensible **only because a stated `distinct-from` is a rare, deliberate, quotable
act** — a source going out of its way to say "this is not that". Syntactic contrast is neither rare nor deliberate:
**every ORBAT list contains one.** Widening an ungraded transitive veto to "any enumeration" is the single worst thing
this spike could recommend, and I reject it.

1. **Enumeration with distinct fillers** — *"two batteries, one at A and one at B"*, *"the 8th and 12th Bns"*. This
   genuinely **is** the source asserting distinctness, and it is the strongest of the three. Make it a **wall, but a
   different kind of wall than `distinct_from`**: credibility-gated, pairwise, non-transitive, and *always reported*.
   Build it beside `_critical_attribute_walls`, not inside `veto`.
   - *grade-gated* ⇒ a grade-E planted list **raises** instead of walling (the existing below-floor discipline);
   - *non-transitive* ⇒ a bad contrast cannot reach a distant cluster;
   - *pairwise* ⇒ blast radius = exactly the pair the source contrasted.
   **The price of non-transitivity must be paid explicitly.** The geo veto is already pairwise-non-transitive and absent
   from `veto` (`cluster.py:357-361`), and the code facts flag that as a *defect* (§D3) because `finalise`, the D9 bridge
   alarm and `res.distinct_from` all ignore it. So the contrast wall must be registered in the **same channel as
   `raise_walls`** so it always produces an analyst-visible candidate reason (`cluster.py:531-544`). A non-transitive wall
   that is also invisible is the worst of both worlds.
2. **"another battery" / "a second unit"** — weaker, and *categorically different*: it asserts a **count** (there are ≥2),
   not *which* pair is non-identical. It must therefore reduce confidence, never adjudicate a pair. Expressed as a **band
   demotion**, `contrast ⇒ band = min(band, "hitl")` — the same treatment `perishable_capped` and `raise_walls` already
   get. (This *also* means the count claim should be captured where it belongs: as a sourced `count` attribute on the
   presence, per D-13.13 — a source that says "two batteries" is *stating the OOB figure*, which is far more valuable than
   its use as an anti-merge hint.)
3. **Distinct designations** — **not a syntactic contrast at all.** It is a discriminator conflict, it belongs on the
   discriminator rail (decision (c)), and it already has the right machinery: `_identifier_veto` walls two same-type
   entities that state *different* hard identifiers (`resolve/__init__.py:460-485`). Routing it through the contrast prior
   would double-count it *and* wrongly scope it to one document, when a designation conflict must hold across documents.
   **Fold it out of micro-decision (b).**

**Adversary view.** The exploitable direction depends entirely on the strength choice. A hard transitive contrast wall is
exploitable by *any* source, because it is ungraded — a planted document enumerating *"the 8th AD Bn and the separate 12th
AD Bn"*, naming two mentions that a well-corroborated cluster already unites, would **shatter a confirmed assessment**.
That is more valuable to an adversary than an over-merge: it destroys an existing finding rather than adding a false one.
Hence: **yes, source grade must gate the prior** — asymmetrically, in the same shape as the critical-attribute wall
(above floor ⇒ act; below floor ⇒ raise, never silently do nothing).

### Carriers — neither exists today

- **Doc-sameness: derivable, cheaply and honestly.** Every claim carries `DocRef.file` (`schemas/claim.py:35-49`, field at
  `:117`), and a referent atom is doc-local *by construction* (D-13.7) — so an **atom→doc index built once per rebuild**
  answers "same document?" for every provisional instance, including instances with no referent (a claim atom also has
  exactly one document). Checked as instructed: doc-sameness **is** derivable from referent-atom membership, and the
  claim-atom fallback covers the singleton case.
  **Two traps.** (1) Do **not** use `Entity.source_ids` (`resolve/entities.py:97-112`): `source_id` is the *publisher*, so
  two documents from one outlet would read as same-doc — the precise input that triggers the too-strong failure mode.
  (2) The judge cannot see either today: `EntityGraph` is `entities + edges` only (`resolve/entities.py:159-161`) and
  `build()` consumes claims and discards them (`:167`), so the index must be threaded into `merge_score` explicitly.
- **Contrast: not derivable — must be an extractor output.** Coref's mention shape has no spans or offsets
  (`coref.py:156-163`), and pass 1 already collapses one name to one claim per document
  (`extract.py:839 _entity_claim_ids.setdefault(name, cid)`; plus `dedup.dedup_within_doc`), so **nothing downstream can
  re-read the syntax** (facts §D6). The home is a new **optional** `contrast_group` on A7's structured-discriminator
  schema (plan/01 RK-ATOMS §7.4): the extractor tags mentions it read as enumerated siblings with a shared group id plus
  the licensing quote. Optional, absence ⇒ `unknown` (D-13.8) — a required field would push the extractor to invent one.
  **Deliberately not the existing `distinct-from` channel**, even though coref already reads stated distinctions as input
  (`coref.py:218-226`, prompt at `:246-249`): that channel is semantically narrow — the extraction slot is explicitly
  *"explicit 'no interoperability' / 'not related'"* (`extract.py:366, 506`) — and it lands as an ungraded transitive
  veto. Widening it would inherit exactly the treatment rejected above.

### Strength in config terms (G6), and why the values are defensible on principle

- `same_doc.contrast_wall_min_grade: C` — reuse the *value already ratified for the critical-attribute wall*
  (`critical_veto_min_grade: C`, `config/resolution.yaml:370`) and justify it identically: a wall a single low-grade
  source can fire is a shatter vector. Defensible because it is the same principle already decided, not a number tuned
  to a corpus.
- `same_doc.contrast_demotes_band: true` — **not a penalty coefficient.** I checked the arithmetic: with
  `auto_merge: 0.85` / `hitl_low: 0.45` (`config/resolution.yaml:26-27`), a ×0.5 penalty moves a 0.85 pair to 0.425 —
  *below* `hitl_low`, i.e. **two bands**, silently dropping the pair out of the analyst queue. Any coefficient has this
  hazard and its safe value depends on thresholds that will move. A band demotion is threshold-independent, matches the
  existing `perishable_capped`/`raise_walls` idiom, and states the intent directly: *contrast means "not automatically",
  never "not at all"*.
- `same_doc.neutral_when_no_contrast: true` — the F5 default; absence of contrast is never a prior *for* merging either
  (the same "absence ≠ evidence" doctrine the conflict machinery already follows, `scoring.py:99-101`).

**Buildability:** the wall + demotion are localised to `resolve/{__init__,cluster}.py`, both S3-owned. The two carriers
are the real cost: an atom→doc index threaded into `merge_score` (small) and one optional extractor field (already
budgeted as A7 in RK-ATOMS). Nothing here needs embeddings.

---

## Decision (c) — Discriminator priority for cross-doc clustering

### The ladder, derived from harm

For each rung: *if this signal is wrong or planted, what breaks, and is it recoverable?*

**0. Differing designation ⇒ hard wall.** Cheap to plant, but the error direction is *fragmentation*, which is
reportable and analyst-fixable. Keep hard — this is the shape `_identifier_veto` already implements
(`resolve/__init__.py:460-485`). Caveat before extending it to `unit.designator`: it compares extracted identifier
strings **exactly**, so "8th AD Battalion" vs "8 AD Bn" would false-wall. Same normalization prerequisite as rung 3.

**1. Temporally-witnessed continuity** (a dated sequence: present at A → absent → present at B; or a designation
re-appearing at a new site). Highest *positive* rung, because it is the only non-perishable positive signal that is
**expensive to plant** — an adversary must fabricate a dated *sequence*, ideally across independence groups, not a
sentence. If wrong, the damage is a false relocation, which is serious but **visible and citable** — it is the assessment
being made, not a silent structural change.

**2. Shared designation — interrogated, as asked.** **A shared designation is NOT a unique identifier and must NOT be a
fast path to confirmed.** Three reasons: designations are **reused across armies** ("8th AD Battalion" exists in many
orders of battle); **reused across time** (re-raised after disbandment); and a single document can state one wrongly or
plant one. And a fourth, decisive for this codebase: a designation arrives as a **name string**, so a designation "match"
*is* a string match — the exact thing D-13.1/D-13.10 demote to recall.
**Verdict: a shared designation is a *non-perishable discriminator*.** It **satisfies** the perishable cap (D-13.9(a)) —
i.e. it is *eligible* to carry a confirm — but it still requires independent corroboration (D-13.9(b)) to actually
confirm. Concretely: designation **+ one independently-sourced agreeing discriminator ⇒ confirmed**; designation **alone
⇒ probable**. **One shared string may never confirm a formation merge.**
The code already embodies exactly this asymmetry for bills of lading and it should be preserved rather than "fixed":
*differing* identifiers veto (`_identifier_veto`), while *shared* identifiers do **not** confirm — `_shared_unique_id` is
always False because `hard_id_fields` is absent (`scoring.py:215-219`; facts §B6). Wire the positive fast path **only**
for genuinely unique strings (a serial, a bill of lading, a registration), never for a designation.

**3. Operator (branch / service).** Most decision-relevant discriminator for an OOB map — operator boundary is what makes
the map *about one adversary* (spine/13 §3: "never across operators within the instance layer"). Today it **cannot fire
in either direction**: `unit.service_branch` is demoted to `supporting` precisely because sources state it unnormalised
('Air Force' / 'PAF' / 'Pakistan Air Force'), and a critical veto compares exactly, so walling it "SHATTERS legitimate
merges" (`config/resolution.yaml:315-334`) — *and* `supporting` is inert because `conflict_penalty` is unconfigured
(`scoring.py:445-447`). Harm of promoting to critical *before* normalization: shattered legitimate merges (the config
names the SINO-GALAXY case). Harm of leaving it: the most decision-relevant discriminator contributes exactly zero.
**Recommend: normalization first, then critical.** Normalization must be a config alias map over **attribute values**,
mirroring the name `AliasIndex` — note `normalize`/`AliasIndex` today apply **only** to `Entity.name`
(`resolve/normalize.py:30-33`, `scoring.py:395-399`) and conflict detection is bare `==` on raw attrs
(`scoring.py:99-101`).

**4. Geography — perishable; separator, never unifier.** Two roles, kept apart. As a **wall** it is good and already
built (`geo_conflict_km`, `scoring.py:60-79`; tolerances `config/resolution.yaml:238-240`) and correctly narrow (only
*stated* coordinates count; absence is unknown). As a **unifier** it must never confirm a formation — this is the
co-location cap.

**5. Relational.** Sub-confirmed-blind (F9 — `uf.union` only inside `merge()`, `cluster.py:378-384`; `pair_confidence`
reads `merge_edges`, filled only by `merge()`). See below.

**6. Name.** Blocking/recall key plus a capped contributor. See below.

### The co-location cap (D-13.14 / G16) — confirmed, and sharpened twice

**Confirmed.** Shared design + site + operator ⇒ **presence**-merge fine, **formation**-merge must not confirm. It is
right on the presence/formation split (§3a): a *presence* asserts only "this operator's equipment was at this site in this
window", which co-location evidence genuinely supports; a *formation* asserts an organizational individual that persists
through moves, which co-location does not evidence at all. A garrison hosts many units.

**Sharpening 1 — say what "capped at probable" *means*, or the implementer will look for a band that does not exist.**
There is **no probable *merge*** in this system. `_band` yields exactly three outcomes — `auto` / `hitl` / `separate`
(`cluster.py:96-101`) — and the verdict names `confirmed`/`probable`/`possible` are a **derived read of set membership**
(`schemas/stage_io.py:112-118`: `same_as`→confirmed, `candidates`→probable, `possible`→possible). Only `same_as` fuses
nodes. Therefore the cap means, mechanically: **do not fuse; emit a candidate pair; emit a named coverage item.** That is
*stronger* than the doc's wording and *crisply testable*, which is what G16 needs.

**Sharpening 2 — the presence merge is only safe if `count` is sourced.** G15 (presence-not-fused) says nothing about
counts. If two co-located presences merge and `count` defaults to 1 or is derived from anything other than a sourced
figure, the presence merge **silently answers "how many?" with 1** — the same OOB undercount arriving through the
"safe" door. D-13.13 already requires `count` to be a sourced attribute defaulting to `unknown`, *never* `= reports
merged`; that requirement must be **asserted by a gate**, not just stated.

**What must a *unit-level discriminator* be to lift the cap?** A signal that individuates the **organization**, not its
location or its kit: (1) a designation — non-perishable, but corroboration-gated per rung 2; (2) a genuine unique id
(serial / registration); (3) temporally-witnessed continuity; (4) an analyst decision.
**Does temporally-witnessed continuity qualify without a designation? Yes — but only in its exclusivity form, and only to
*probable* on a single source's sequence.** Continuity earns identity when the evidence **excludes the alternative**:
presence at A ends, presence at B begins, and the operator's inventory does not support two. Absent an inventory bound —
which is exactly what open sources do not give (spine/13 §9: the sustainment tier carries zero instances) — continuity
cannot exclude *rotation of two units through one base*. So: continuity qualifies as a unit-level discriminator **iff the
sequence spans ≥2 independence groups**, reusing spine/04's ledger rather than inventing a count. One source's sequence
supports, it does not confirm.

### The two guards (D-13.9)

**(i) Geography is perishable ⇒ perishable-only evidence ≤ probable.** *Failure if missing:* a co-located pair
**confirms on geography** — the OOB undercount — and it confirms **silently**, because an auto-merge produces no queue
item at all. *Enforced today?* **Partly, with a real hole.** The mechanism exists and works: `perishable_capped` blocks a
would-be auto-merge that reaches the band only on the perishable succession bonus and forces it to the queue with a
reason (`cluster.py:437-467`, reason text at `:128-138`). But `confirm_is_durable` **short-circuits on
`has_durable_trigger`** (`cluster.py:417-433`), and `has_durable_trigger` counts **exact-normalized-name + namespace** as
durable identity support (`cluster.py:399-415`). So a co-located, same-named pair **bypasses the perishable cap entirely
via name-sameness** — name laundering a perishable-only confirm. That directly undercuts guard (i) and the co-location
cap, and it is named in neither spine/13 nor plan/01.

**(ii) Source-independence ⇒ two reprints of one almanac cannot confirm.** *Failure if missing:* two derivative copies of
one underlying observation read as corroboration — and for this corpus that is not hypothetical, since the recycled-image
trap is *precisely* one observation appearing twice. *Enforced today?* **No — not anywhere in the merge path.**
`source_asserted_score` is a **max over source grades** (`scoring.py:550-566`), not an independence count, and it is
**excluded from the auto band** anyway (`_deterministic_total` = `merge_score` minus `source_asserted`, `cluster.py:78`).
Nothing counts independence groups when deciding a merge. **Recommendation:** the *confirm* path (not the raise path) must
require ≥2 independence groups among the claims carrying the **non-name** signals, reusing spine/04's existing grouping.
If that is too large for S3, **disclose it verbatim**: *"identity confirmation counts corroborating claims, not
independent sources."*

### F9 — accept the gap explicitly

**Recommendation: accept and disclose. Do not fix in this chain.**
*What class of correct merge is unreachable:* two provisional instances whose only tie to a shared anchor is *itself* a
probable/possible anchor merge — the fuzzy-instance-hanging-off-a-fuzzy-anchor case. On a real corpus with messy place
names that is a meaningful class, and it is the class spine/13 §6 lever 2 leans on.
*What incorrect merge it accidentally prevents:* transitive fusion **through a wrong anchor merge** — two batteries both
linked to the same over-merged site node, chaining into one formation. That is the OOB harm, so the accident is protective
in exactly our harmful direction. Fixing F9 means giving weight to *unmerged* pairs, which reintroduces a cascade
(a probable link lending weight that promotes another pair to auto, which lends more weight) at the precise moment we are
trying to make formation merges harder. The asymmetry is the argument: F9's error direction is under-merge, which §6
already declares the goal.
**What must be disclosed out loud (design-note disclosures):** *"Relational support flows only through anchors that
actually merged; a probable or possible anchor merge contributes zero relational weight. The anchor-scaffolding lever is
therefore real only for cleanly-resolved anchors, and instance-layer recall is understated wherever places or designs
remain unresolved."*
**What a user would wrongly believe without it:** that the residual instance tail on the coverage surface reflects
**genuine evidential sparsity** — i.e. an adversary collection gap — when part of it is our own scoring conservatism.
They would task collection that cannot close the gap. An undisclosed system-caused gap is a **mis-tasking**, and
mis-tasking is the operational face of the thing the non-negotiable forbids.

### The name rung — three harms, and the invariant

- **Fusion into `attribute_score`.** `attribute_score` returns `max(name_similarity, agreeing/present) × penalty`
  (`scoring.py:425-437`, `:463`). So a strong name match *sets the floor* of the 0.40-weighted attribute term, and
  attribute agreement can never distinguish "agrees on three discriminators" from "spelled almost the same". Concretely: a
  pair agreeing on nothing but its spelling is indistinguishable, in the number the judge reads, from a pair with real
  discriminator agreement — and the soft penalty that would push back is dead (`conflict_penalty` unconfigured, facts §B6).
- **Exact-normalized-name auto-merge at 1.0** (`cluster.py:457-465`) — lane 2 of D-13.1, and it also feeds the
  perishable-cap bypass above.
- **A third the code facts do not name: the advertised cap has a hole at the lowered per-type floor.**
  `name_alone_caps_at_possible` is applied **only** in the candidate-collection loop, and **only** to `band == "hitl"`
  (`cluster.py:558-568`). The Phase-2 auto-merge fixpoint (`cluster.py:479-491`) never consults it. With
  `auto_merge_by_type: {manufacturer: 0.37, trading_org: 0.37}` (`config/resolution.yaml:64-66`), a pair whose *only*
  nonzero signal is name similarity ≈0.8 reaches `_deterministic_total` = 0.8×0.40 + 1.0×0.05 = **0.37 ≥ 0.37 ⇒ auto**,
  and `confirm_is_durable` waves it through — its docstring says so in as many words: *"A name-driven … confirm still
  autos here"* (`cluster.py:417-433`). So the dial the config presents as the D4 correction (*"a bare name match is
  `possible`, never `probable`"*, `config/resolution.yaml:150-154`) does not bind the path that actually fuses nodes.

**The invariant the cap mechanism must guarantee** (not how to code it):
> **No code path may fuse two nodes when every non-name identity signal is zero — at any floor, in any phase, for any
> type.**
Two corollaries: the cap is a property of the **merge decision**, not of the candidate-collection band; and name
similarity must enter the score on its **own axis**, separable from attribute agreement, so "name-alone" is a *fact about
the breakdown* rather than a heuristic over a fused number.

### The absent discriminator (D-13.8) — what must be true of the *output*

This is the clause the project is graded on, so concretely. For an under-individuated instance, five things must hold:

1. **It exists and is drawn**, carrying its evidence. Never dropped, never merged away, never given an invented
   discriminator. Absence must never wall: the "absence ≠ conflict" doctrine already enforced by `attribute_is_conflict`
   (`scoring.py:99-101`) and by the geo veto (`scoring.py:71-78`) must be reused verbatim for the new discriminators.
2. **It carries a first-class `KnownGap`.** The carrier already exists — `KnownGap{what_missing, missing_slots,
   observability_ceiling, next_coverage_due, related_ref}` (`schemas/view.py:171-183`) — and is already generated from a
   *failed evidence template* (`view/pipeline.py:777-787`). So the mechanism is **a new `assertion_type: formation-identity`
   row in `config/templates.yaml`** with a `refusal_template`: no new prose code, and the file's own discipline is
   preserved (*"a deterministic fill-in-the-blank string, never regenerated prose"*, `config/templates.yaml:7`).
3. **Its label shows the under-individuation.** The display label is derived from name + discriminators (spine/13 §8);
   when the individuating discriminator is absent the label must *say so* ("HQ-9/P presence — Rahwali · formation
   unattributed"), not render as a confident singular.
4. **It names a candidate count and a next-coverage date.** The count ("1–2 candidate formations") is the OOB answer;
   the date comes from a source's cadence or from the explicit `unscheduled_coverage_phrase`
   (`config/templates.yaml:15`) — **never invented**.
5. **It appears in the coverage surface at instance granularity.** Today `identity_coverage` reports gaps only at
   **entity-type** granularity — it appends a bare `etype` string (`view/coverage.py:147-153`). A type-level "unit" gap is
   **not** an instance-level named gap, so this is a genuine addition, not a wiring job.

**How that differs from silence.** Silence is: one node labelled "8th AD Bn", status *probable*, a confidence number, and
nothing else — an analyst reads a single unit and a soft score. The honest output is the same node **plus** a named
missing slot, **plus** a candidate count, **plus** a next-coverage date or the explicit statement that nothing is tasked,
**plus** an explicit refusal when asked the question the evidence cannot answer. The difference is not tone; it is that
**a gap is addressable and a low confidence number is not** — the first tasks collection, the second invites a guess.

---

## The adversarial test set — shapes a test author must include

| # | Input shape | Tempting-but-wrong outcome | Correct outcome |
|---|---|---|---|
| 1 | **Planted in-doc alias between two real formations**, grade-E source: *"the 8th AD Battalion (also known as the 12th AD Battalion)"* | `EXPLICIT_EQUIVALENCE` ⇒ auto-bind at 1.0 ⇒ one formation | Structural test passes, **grade floor fails** ⇒ raise-only with the quote; two formations preserved; HITL item created |
| 2 | **The same sentence in a grade-B source** | "coref is dangerous, never bind" ⇒ nothing happens | **Auto-binds.** The gate must be able to fail in *both* directions, or it only proves timidity |
| 3 | **Category mislabel**: two batteries, then *"it was relocated"*; model returns `EXPLICIT_EQUIVALENCE` with a real quote containing only one member's name | Category is allow-listed ⇒ bind | **Structural corroborator fails** (both surface forms absent from the quote) ⇒ raise-only |
| 4 | **Enumeration in one ORBAT paragraph**: *"two HQ-9/P batteries, at Rahwali and Nur Khan respectively"* | Tier 1 fuses on design + operator + co-citation (name high, temporal 1.0) | Contrast wall (grade ≥ floor) blocks fusion; both survive; **presence `count` = 2 from the stated figure**; **no `supersedes` / relocation edge drawn** |
| 5 | **The same enumeration in a grade-E document** | Below floor ⇒ silently ignored, pair merges | Below floor ⇒ the pair is **raised** with the contrast as its reason. A low-grade source can neither fuse nor shatter |
| 6 | **Fake contrast against a confirmed cluster**: a planted doc enumerates *"the 8th AD Bn and the separate 12th AD Bn"*, naming two mentions a 5-document cluster already unites | Routed through `distinct-from` ⇒ ungraded transitive veto ⇒ **the cluster shatters** | Pairwise, non-transitive, grade-gated ⇒ cluster intact; the contradiction surfaces for the analyst |
| 7 | **Co-location, two batteries, one garrison**: two independent imagery reports, same operator, same design, same site, same month, no designations | Fuse into one unit (every current signal points that way) | **One presence merge; no formation merge**; formation count reported unresolved (1–2); `KnownGap` naming "unit designation"; **no derived relocation** |
| 8 | **Thin context — must degrade** (required case): one line, *"a Pakistani SAM battery was seen near Rahwali"* — no designation, no branch, no count, district-level geography | Attach to the existing HQ-9/P-at-Rahwali unit (name + geo + operator all "agree") | Presence with `variant = unknown`, `formation = unattributed`, precision district-not-site; `KnownGap` with `missing_slots = [variant identification, unit designation]`; asked *"which unit?"* ⇒ **"insufficient evidence to attribute"**, naming both slots and the next coverage date (or the unscheduled phrase) |
| 9 | **Recycled image / two reprints of one almanac** — two documents carrying one underlying observation | Two "independent" corroborations ⇒ confirmed formation merge | One independence group ⇒ **cannot confirm**; stays probable with "corroboration is not independent" as the reason |
| 10 | **Designation collision across armies / across time** — two docs each naming an "8th AD Battalion", one PAF-side, one PLA-side | Shared designation ⇒ fast path to confirmed | Designation is a non-perishable discriminator, not a unique id; operator/namespace conflict walls it once normalization runs; with operator absent it sits at probable + a named gap. **This test fails today** and should: the Phase-2 fuzzy fixpoint never checks `namespace_compatible`, and relational blocking emits pairs with no namespace key (`cluster.py:182-187`, `:261`) |
| 11 | **Value-normalization false wall** — one unit, two claims: `service_branch: PAF` and `service_branch: Pakistan Air Force` | Promote operator to critical first ⇒ a hard wall **shatters a legitimate merge** | Normalization maps both to one value ⇒ no conflict ⇒ merge proceeds on its other merits. **This test must exist before operator is promoted to critical** |

---

## What the analyst sees — the literal sentences

**Co-location residual** (rendered from a `formation-identity` template row, per the mechanism above):

> **HQ-9/P presence at Rahwali airfield: confirmed** — 2 independent imagery reports (09 OCT 2021, 14 NOV 2021).
> **Formation attribution unresolved — 1–2 candidate formations.** The reports agree on design, site and operator, but no
> unit-level discriminator is stated, and a garrison can host two batteries of one system. **Missing:** a unit
> designation, or a dated presence sequence establishing continuity. **Next coverage due 12 FEB 2026** (Sentinel-2
> revisit, 30-day cadence).

**Under-individuated instance, absent discriminator:**

> **Provisional formation at PAF Base Nur Khan: under-individuated.** No designation, no service branch and no serial is
> stated by any source. Held as a distinct instance — **not** merged into 8th AD Battalion, and **not** asserted to be a
> new formation. **Missing:** unit designation. **Ceiling:** confirmable. **Next coverage:** unscheduled — no collection is
> tasked against this gap; it stands as an open collection requirement.

**And the two sentences the system must never emit:** *"1 HQ-9/P battery at Rahwali"* (a count derived from a merge), and
a merged node silently labelled *"8th AD Battalion"* when the designation came from only one of the merged sides.

---

## Drift, and gates that would pass while the harm happens

1. **`based-at` is functional and unit-keyed, so a formation over-merge manufactures a relocation.**
   `config/ontology.yaml:146` — `based-at`, `instance_key: [from]`, FUNCTIONAL, keyed on the unit *"so a relocation's
   before/after co-locate"*. Fuse two co-located batteries into one unit and their two sites become one unit's
   before/after; the supersede path runs (`view/pipeline.py:795 promote_supersessions`) and can **draw a relocation**.
   Neither spine/13 nor plan/01 names this consequence — §6 lever 3 treats relocation as an *inference* problem, never as
   a *side effect of an identity error*. The ontology already admits the sub-scope limitation and explicitly rests it on
   the corpus (`config/ontology.yaml:40-44`: *"correct while the corpus has no such simultaneous pair"*), which
   working-principles #1 forbids as a design input. **G16 must assert the absence of a derived `supersedes`/relocation
   edge, not only the absence of a confirmed merge** — otherwise the gate goes green while the harm it exists to prevent
   is realized one stage downstream.
2. **G15 passes vacuously today, and misses a second route to the same harm.** `basing.find_candidates` already requires a
   `formation_edge_types` link to a `unit`-typed node and skips otherwise (`ingest/basing.py:296-300`, reason
   `no-formation-reference`), so "an `observed-at` never becomes a `based-at` without organizational evidence" **is
   current behaviour**. Fine as a regression guard; but the conflation route that actually exists is
   `max_units_per_site: 1` (`config/credibility.yaml:172`): when two candidate formations are associated with the same
   observed equipment, the second is **silently dropped** — `formations[:max_units]` (`ingest/basing.py:301`) truncates,
   and `SkipRecord`s are appended only on clause failures, never on truncation. That is an OOB undercount produced
   **without any merge**, so G16 cannot see it either. G15 needs a clause: *two candidate formations ⇒ two attributions,
   or one attribution plus a named gap — never a silent pick.*
3. **G18's `operated-by` half has nothing to fire on.** There is **no `operated-by` predicate** anywhere — grep across
   `config/` and `backend/` returns nothing; `config/ontology.yaml:146-159` declares no such edge. Either S3 adds the
   predicate (then the stage scope must say so) or the gate silently tests half of itself and is marked green.
4. **G18 does not say *which* kind of wall, and the two available kinds are not equivalent.** "Hard wall" has two
   implementations here: membership in `veto` — hard **and** transitive, re-applied in `finalise`
   (`cluster.py:363-370`, `:638-648`) — and consultation inside `vetoed()` only, which is hard, pairwise, and **invisible**
   to `finalise`, the D9 bridge alarm and `res.distinct_from` (how the geo veto is wired, `cluster.py:357-361`; flagged as
   a defect in facts §D3). Build the relationship wall like the geo veto and it will be non-transitive **and unreported**,
   and G18 will still pass. The gate must name the channel and assert an analyst-visible reason.
5. **`name_alone_caps_at_possible` does not bind the path that fuses nodes.** Applied only to `band == "hitl"` in the
   collection loop (`cluster.py:558-568`); the Phase-2 auto-merge never consults it (`cluster.py:479-491`); at
   `auto_merge_by_type: 0.37` a name-only pair reaches `auto`. **G6 cannot catch this** — the numbers *are* in config; the
   defect is that a policy dial does not cover a code path. Needs its own gate clause, asserting the invariant in (c).
6. **`confirm_is_durable` launders a perishable-only confirm through name-sameness.** `has_durable_trigger` counts
   exact-normalized-name + namespace as durable identity support (`cluster.py:399-415`), so a co-located same-named pair
   short-circuits the perishable cap. This directly undercuts D-13.9 guard (a) and the co-location cap, and appears in
   neither spine/13 nor plan/01.
7. **D-13.9's independence guard is not implemented anywhere in the merge path**, but plan/01 §7 RK-COREF item 5 reads as
   if it were configuration ("corroboration inherits source-independence"). It is **new code**: `source_asserted_score` is
   a `max` over grades (`scoring.py:550-566`) and is excluded from the auto band entirely (`cluster.py:78`). Scope it or
   disclose it; do not let it be assumed.
8. **spine/13 §6/§7/§13 speak of "capped at *probable*" as if a probable merge existed.** It does not: three bands
   (`cluster.py:96-101`), no `reject` verdict, and the confirmed/probable/possible names are a derived read of set
   membership (`schemas/stage_io.py:112-118`) where only `same_as` fuses. Rewrite as *"not fused; queued + reported"* —
   stronger, and testable.
9. **spine/13 §4's "coref stays a challengeable proposal" is inconsistent with D-13.11 as written**, if the referent atom
   becomes the address of the provisional instance (atoms never split ⇒ a wrong cluster is permanent). Resolved by (a)(iii):
   the referent atom is *evidence about a grouping* — which is what `coref.py:385-392` already emits (a claim on
   `coref-same-as`, never an entity id) — with claim atoms as the split unit. Write this into D-13.7/D-13.11, because
   plan/01 RK-COREF item 1 can be read either way and the unsafe reading is disqualifying.
10. **`config/resolution.yaml:170-179`'s second justification is demo preservation** — forbidden as a design input by
    working-principles #1. Target policy per (a); the data pass owes a re-carried earned-alias beat (two shapes offered).
    The *first* justification (producer and consumer switches must flip in one deliberate motion) is sound and should
    survive as a comment.
11. **Namespace is not a wall in the fuzzy fixpoint — an unstaged, live OOB hazard.** Cross-namespace pairs (PLA vs PAF)
    can be scored and auto-merged: relational blocking emits pairs with **no namespace key** (`cluster.py:182-187`), and
    `namespace_compatible` gates only bootstrap-exact-name, `_name_containment` (`cluster.py:261`), `_identity_pairs`
    (`resolve/__init__.py:596`) and `_coref_pairs` (`:654`) — never the Phase-2 loop. For an operator-scoped OOB map this
    is the single most dangerous over-merge class, and it directly contradicts spine/13 §3's "never across operators
    within the instance layer". **No gate names it.** RK-COREF should own closing it, under a G16 clause or a new gate.

---

## Two places I am genuinely uncertain (with my call anyway)

- **Whether the enumeration wall should be grade-gated or ungraded.** The existing `distinct_from` doctrine
  (`resolve/__init__.py:567-575`) argues persuasively that honouring a wrong non-identity is cheap. **My call: grade-gate
  it** — because that argument holds for a *rare deliberate* statement and enumerations are neither, so the shatter
  surface is orders of magnitude larger. If a reviewer overrules this, the compensating requirement is that the wall stay
  non-transitive *and* always reported.
- **Whether F9 should be fixed in the same chain rather than disclosed.** A graded sub-confirmed relational term is what
  spine/13 §6 lever 2 actually promises. **My call: disclose, don't fix** — the fix adds cascade risk in the same stage
  that is trying to make formation merges harder, and its absence errs toward honest fragmentation, which §6 declares the
  goal.
