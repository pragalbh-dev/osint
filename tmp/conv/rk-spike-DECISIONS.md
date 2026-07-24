# RK-SPIKE — the three micro-decisions, CLOSED

**Status: decided (2026-07-24).** Synthesized by the orchestrator from two independently-framed opus analyses
(`rk-spike-analyst-A.md` mechanism-first, `rk-spike-analyst-B.md` failure-first), the verified code baseline
(`rk-spike-code-facts.md`), the orchestrator's own pre-synthesis position
(`rk-spike-orchestrator-position.md`), and the verified defect register (`rk-spike-verified-defects.md`).
Where the two analysts disagreed, the disagreement and its resolution are recorded — that is the point of
running two framings.

**Decided on general principle, per working-principles #1.** Nothing about the current corpus, the present
graph, the keyless boot, an existing demo beat, or the cost of re-extraction was allowed as an input. Two
places where the shipped config or a design doc *did* rest on one of those are called out and overruled.

---

## The single mechanical fact that decides most of (a)

**An "authoritative" coref pair is a Phase-1 bootstrap trigger: it merges at hardcoded confidence `1.0` and
bypasses banding entirely** (`resolve/cluster.py:462-465`, `merge(a, b, 1.0, bd)`; the bootstrap disjunction at
`:404-415`). It is therefore restrained by **no cap** — not the name cap, not the perishable cap, not a band
ceiling. Everything downstream in the design that says "capped at *possible*" or "capped at *probable*" is
simply inapplicable to an authoritative bind.

Consequences, and they are the spine of decision (a):
1. Authorizing a category is authorizing an **uncapped, unbanded fusion** on a *model-chosen label* — so a
   category may only be authoritative behind a **deterministic, code-verified precondition**. A model's
   self-report is not evidence; a model's self-report plus a structural check any reader can re-derive is.
2. It must *also* clear a **source-grade floor**, because a coref bind currently acts **harder than the
   assertion it most resembles**: a source-stated `same-as` is grade-floored *and* structurally raise-only
   (`_deterministic_total` excludes it, `cluster.py:78`), while a coref bind fuses at 1.0 with **no grade check
   anywhere** (neither `ingest/coref.py` nor `_coref_pairs`, `resolve/__init__.py:614-661`). The weaker-
   evidenced channel acting harder is an inversion, and spine/13 §5's doctrine is explicit: **stated ≠
   trusted.**

So the deterministic gate and the credibility gate are **both required, not alternatives** — analyst A supplied
the first, analyst B the second, and neither is sufficient alone.

---

## (a) Tier-0 auto-bind, graded by coref category — DECIDED

### The policy

| Category | Verdict | Deterministic gate (all must pass) | Grade gate |
|---|---|---|---|
| `EXPLICIT_EQUIVALENCE` | **authoritative** | quote occurs verbatim in the document (**already enforced**, `coref.py:253-260`) · quote contains **both** members' surface forms · quote contains a **configured equivalence marker** (a parenthetical wrapping one form, or a term from a config list) | ✔ |
| `UNAMBIGUOUS_ANAPHOR` | **authoritative** | **type-unique antecedent** — the document contains no second mention of a compatible entity type that the anaphor could mean (checkable against coref's own mention inventory) | ✔ |
| `NAME_VARIANT` | **raise-only, permanently** | — | — |

**`NAME_VARIANT` is raise-only for a mechanical reason, not out of caution.** Because an authoritative pair
bypasses banding and fuses at 1.0, "authoritative `NAME_VARIANT`" *is* the exact-normalized-name auto-merge
lane that D-13.1 exists to delete — rebuilt on a different predicate, and immune to the very cap
(name-alone ⇒ *possible*) that D-13.10 introduces to replace it. Both analysts reached this independently; it
is the one call all three positions converged on. My own pre-synthesis view (authoritative behind a
normalized-equality check) was **wrong**, and wrong in an instructive way: a normalized-equality check is not a
*corroborator*, it is the name verdict itself, restated.

**`UNAMBIGUOUS_ANAPHOR` is authoritative — this is where the two analysts split, and it flips the shipped
config comment.** Analyst B argued raise-only (untestable, fails silently, and an intra-document over-bind
cannot be corrected by cross-source corroboration). Analyst A argued authoritative behind a structural gate.
**A wins, for three reasons:**
1. The gate is real, not hypothetical: the category's own licensing condition — *no second mention of that
   type it could mean* — is **structurally checkable** against the existing mention inventory. Where the check
   passes there is, by construction, no ambiguity to resolve.
2. Raise-only for anaphora forfeits **lever 1**, which spine/13 §6 calls the *biggest* fragmentation lever, and
   manufactures a fragmentation class of **nameless orphans**: an anaphor carries no independent name, so an
   unbound one becomes a node whose only content is the facts hung on it. That is self-inflicted sparsity, and
   §6's defence of residual fragmentation ("it reflects genuine evidential uncertainty") does not cover it —
   reporting our own grain choice as a collection gap **mis-tasks the analyst**.
3. B's strongest objection — that a mislabel *fails silently* — is answered by the gate plus the decline
   mechanism below, not by refusing the category.
**Conditional:** if the type-unique gate is not built, this decision flips to raise-only. The gate *is* the
decision.

### What "held looser" means mechanically — option (i)

Only an **authoritative** cluster mints **one shared referent atom**. A looser cluster mints **one referent
atom per member**, plus an **injected Tier-1 candidate pair** per link, carrying its licensing quote
(`_candidate_pairs` already accepts injected pairs, `cluster.py:203`; `_coref_pairs` already routes
non-authoritative pairs to `raise_only`, `resolve/__init__.py:657-660`).

Option (iii) — "transitive closure over authoritative links only" — **is not implementable**: the coref
category is per-**cluster**, not per-link (`coref.py:375-379`, `_coref_evidence` stamped on the cluster), so it
collapses into option (i). Recording this so S3 does not re-derive it.

### Reversibility — the rebuild may DECLINE a grouping (the disqualifying gap, closed)

**As spine/13 and plan/01 are written, S3 would make intra-document over-merge permanent.** §4 promises a coref
cluster stays "a challengeable proposal"; D-13.11 says atoms never split; and neither doc states the mechanism
by which a wrong grouping is undone. Both analysts independently flagged this as the highest-risk ambiguity.
The resolution:

> **The referent atom is *evidence about a grouping*, never the address of the provisional instance.** Rebuild
> groups **claim atoms**; the referent atom is a strong (or authoritative) grouping *signal* the grouping step
> consults. An intra-referent critical-discriminator conflict makes the rebuild **decline** the grouping —
> de-grouping to claim-atom granularity and raising for an analyst. **No atom splits; the grouping declines.**

This is already the shape the code emits: `coref.py:385-392` mints a **claim** id on a `coref-same-as`
predicate, **never an entity id**. The forbidden shape is minting one referent atom per *proposal* and using it
as the instance address.

**New code required, and it is not obvious:** an intra-referent conflict is currently **invisible**, because
`Entity.attrs` is first-claim-wins scalar (`resolve/entities.py:189` `setdefault`) and the losing value only
reaches `attr_history`. The decline check must read **history**, not `attrs`.

**Action:** write this into **D-13.7 / D-13.11 and plan §7 RK-COREF item 1** — all three read either way today,
and the unsafe reading is disqualifying.

### A required build item both analysts leaned on, which does not exist

**The raise-only licensing quote is written but read nowhere.** Both analyses justify raise-only by "the
analyst is handed the exact sentence" — the shipped config comment says so too
(`config/resolution.yaml:175-177`). It is stamped onto the claim (`coref.py:375-379`, `source_quote`) and
never surfaced. **Wire it, or the mitigation that makes raise-only acceptable is fictional.**

### The principle collision — overruled

`config/resolution.yaml:170-179` gives two justifications for `coref_authoritative_evidence: []`.
- *Justification 1* — the producer and consumer switches must be flipped in one deliberate motion — is
  **sound and survives as a comment**.
- *Justification 2* — preserving the d10 "HT-233 (H-200)" orphan-alias beat an analyst is meant to earn — is
  **demo preservation, forbidden as a design input** (working-principles #1). **Overruled.**

The target-correct policy binds `EXPLICIT_EQUIVALENCE`, so a grade-passing parenthetical will auto-bind and the
beat is lost as currently carried. **The data pass owes a re-carried beat**, and the better shape is to
**split the two designations across two documents** (doc A says HT-233, doc B says H-200, neither states the
equivalence): it converts a *reading* demo into an **earned cross-document identity** demo, which is the
capability actually being graded. (A low-grade statement of the alias also works — the grade gate raises it and
the analyst earns it *with the reason visible*.)

---

## (b) Tier-1 same-document comparison + the contrastive prior — DECIDED

### A finding that removes half the work

**Tier 1 already compares same-document pairs. There is nothing to build.** Candidate generation is five
sources of blocks over the whole entity inventory (`cluster._candidate_pairs:151-203`) with **no document
dimension anywhere** — zero hits for `doc_ref`/`doc_id`/`document` across all of `resolve/**`. F5's "so Tier-0
under-binding can rejoin" is satisfied by the **absence of a filter**, not by new code. **The plan should stop
budgeting for it.**

### Carriers

- **Doc-sameness — `Entity.doc_ids: frozenset[str]`**, populated at the single boundary where the reference is
  currently dropped (`resolve/entities.py:188-213`, from `c.doc_refs()`). One field, one population site.
  **Rejected: deriving doc-sameness by parsing the claim-atom id prefix.** `make_claim_id` does encode the
  document (`schemas/ids.py:19-30`), and my pre-synthesis position proposed parsing it — but that makes a
  load-bearing identity decision depend on an id *format*, which is precisely the coupling the re-key exists to
  remove. Analyst A is right. Also note referent equality is **not** a doc-sameness test: two instances from
  one document have *different* referent atoms.
  **Also rejected: `Entity.source_ids`** — `source_id` is the *publisher*, so two documents from one outlet
  would read as same-doc, which is exactly the input that triggers the too-strong failure mode.
  Load-bearing beyond this decision: it scopes the contrast channel so a doc-local contrast cannot leak onto
  cross-doc pairs through `_matching_eids`' global name expansion (`resolve/__init__.py:232-241`); plan §8's
  bake-off **cannot measure coref over/under-binding without a doc axis**; and D-13.12's coverage surface must
  report the intra-doc fragmentation tail.
- **Contrast — a new contrastive output channel on coref**, its own `coref-distinct-from` lane. **Not**
  derivable downstream: coref's mention shape has no spans (`coref.py:156-163`) and pass 1 collapses one name
  to one claim per document (`extract.py:839`), so nothing can re-read the syntax. Optional field, absence ⇒
  `unknown` (D-13.8) — a required field would push the extractor to invent one.
  **Deliberately not the existing stated-`distinct-from` rail**: that channel is semantically narrow (the
  extraction slot is explicitly *"explicit 'no interoperability' / 'not related'"*) and lands as a **hard,
  transitive, ungraded** veto (`resolve/__init__.py:567-575`). Widening an ungraded transitive veto to "any
  enumeration" is the single worst thing this spike could have recommended — **every ORBAT list contains one** —
  and it is rejected.

### Strength: a band ceiling at `probable` — and the config value is a band name, not a float

A same-doc **stated-contrast** pair is **capped at `probable`**: it reaches the analyst with its licensing
quote and can **never auto-merge**. Absence of contrast is **neutral** — never a prior *for* merging either
(the same "absence ≠ evidence" doctrine the conflict machinery already follows, `scoring.py:99-101`).

**Why a ceiling, not a score penalty.** Analyst B computed the arithmetic: with `auto_merge: 0.85` /
`hitl_low: 0.45`, a ×0.5 penalty moves a 0.85 pair to 0.425 — **below `hitl_low`, i.e. two bands**, silently
dropping the pair out of the analyst queue entirely. Any coefficient carries this hazard and its safe value
depends on thresholds that will move. A band ceiling is threshold-independent, matches the existing
`perishable_capped` / `raise_walls` idiom, and states the intent directly: **contrast means "not
automatically", never "not at all."**

**Why no grade gate — where I depart from analyst B.** B recommended grade-gating the enumeration case, on the
strength of a real adversarial scenario: a planted document enumerating *"the 8th AD Bn and the separate 12th
AD Bn"* shattering a well-corroborated cluster. That risk is **specific to a veto**, and it is why B was right
to reject the veto rail. But a **band ceiling cannot shatter anything** — it withholds a *new* fusion for one
pair; it cannot retract an existing merge, and a cluster can still form transitively through its other pairs.
Choosing the non-shattering mechanism removes the harm the grade gate was defending against, so the gate would
be a knob buying no risk reduction. (Contrast with (a), where the grade gate **is** required precisely because
an authoritative bind fuses uncapped.)

### Adopted from analyst B, independent of the merge question

A source that says *"two batteries"* is **stating the order-of-battle figure**. Capture it as a **sourced
`count` attribute on the presence** (D-13.13) — far more valuable as data than as an anti-merge hint, and it
directly serves the OOB mission.

### Folded out of (b)

**"Distinct designations" is not a syntactic contrast at all.** It is a discriminator conflict; it belongs on
(c)'s rail, it must hold **across** documents (not be scoped to one), and routing it through a doc-local
contrast prior would both double-count it and wrongly narrow it. Both analysts agree. **Removed from (b).**

---

## (c) Discriminator priority — DECIDED

### The ladder

**differing designation (veto) > composite unique identifier > temporally-witnessed continuity > shared
designation > operator (post-normalization) > geography (perishable) > relational (F9-limited) > name
(ceiling at *possible*)**

Priority manifests in **three shapes, not one dial**, and each rung uses a different pair:

| Rung | Blocking | Score | Cap behaviour | Wall |
|---|---|---|---|---|
| composite unique id | ✔ | — | lifts all caps | conflict ⇒ hard veto (**built**) |
| shared designation | ✔ | ✔ | **satisfies the perishable cap; never confirms alone** | conflict ⇒ hard veto (**undeclared today**) |
| operator / branch | namespace key | ✔ | — | conflict ⇒ hard veto, **gated on normalization** |
| geography | — | ✔ | **perishable ⇒ cannot confirm alone** | conflict ⇒ veto (built; not transitive) |
| relational | ✔ | ✔ | feeds the co-location cap | — |
| name | ✔ | ✔ | **ceiling at *possible*, every layer** | — |

### The load-bearing call: a shared designation is NOT a unique identifier

Designations are **reused across armies and across time**. One shared designation string may **never** confirm
a formation merge. The mechanism, and it is elegant: **`hard_id_fields.unique` is a list of composite AND-keys**
— `(service_branch, designator)` is an identifier; a bare `designator` is not.

This is stronger than declaring the designator a "non-perishable discriminator" (my pre-synthesis position),
because it makes the operator requirement **structural in the identifier declaration** rather than depending on
a separate namespace check — and per the defect register **D4 that namespace check is broken in the Phase-2
fixpoint**. The codebase already embodies exactly this asymmetry for bills of lading: differing identifiers
veto, shared ones do not confirm (`identity.identifier_patterns`, `_identifier_veto`). **Preserve that
asymmetry; do not "fix" it.**

### The two code changes that carry most of (c)

1. **Split `attribute_score` into two signals (`name` / `discriminator`).** They are already computed
   independently and fused at a single `max` (`scoring.py:425-437`), with exactly one production caller — so
   this is a small, contained change. **Without it, D-13.10 cannot function at all**: "a name match reaches at
   most *possible*, and one more trivially-available signal clears it" is unexpressible while the two live in
   one number.
2. **Make the caps bind the fusion path, and make them name-impermeable** (defect register D3). Today
   `name_alone_caps_at_possible` is consulted only in the post-fixpoint collection loop
   (`cluster.py:558-568`) and the Phase-2 fixpoint that actually unions never sees it — reachable at the
   lowered per-type floor (`attr ≥ 0.80` at `auto_merge_by_type: 0.37`; unreachable at the global `0.85`).
   And `confirm_is_durable` short-circuits on `has_durable_trigger`, which counts exact-normalized-name as
   durable support (`cluster.py:418-428`) — so name-sameness launders a perishable-only confirm **and** the
   co-location cap.

### What already exists (so S3 configures rather than builds)

Both cap **shapes** are built and proven: *cap at probable* = withhold the merge, force into `candidates` with
a reason (the `perishable_capped` shape, `cluster.py:443, 478-496, 574-576`); *cap at possible* = withhold from
`candidates`, land in `possible` (the `name_alone` shape). **The co-location cap (G16) is a third instance of
the `perishable_capped` shape, not new machinery**, and its analyst-facing reason belongs beside
`_perishable_confirm_reason` (prose-only, no thresholds — G6-clean). Per-attribute `perishable` is already
declared and explicitly "read but NOT yet consumed" (`config/resolution.yaml:309-311`) — **S3 consumes it; that
is the D-13.9(a) guard.**

### Value normalization

A **prerequisite** to promoting any operator/branch attribute to `critical`. Must apply **before conflict
detection *and* before namespace derivation** (`resolve/entities.py:114-120` reads raw attrs; normalizing only
at conflict time would leave namespaces split). The shipped config already asks for this by name
(`resolution.yaml:317-324`) and explains why exact-match walling "SHATTERS legitimate merges". Config-driven
equivalence classes, analyst-editable, hot-config.

### Terminology correction (defect register D8)

spine/13 §6/§7/§13 say "capped at *probable*" as if a probable **merge** existed. It does not — three bands,
no `reject` verdict, and confirmed/probable/possible are a derived read of set membership where **only
`same_as` fuses**. **Rewrite as "not fused; queued and reported"** — stronger, and testable.

### F9 — accept the gap, disclose it, roadmap the fix

Both analysts independently recommend accept-and-disclose; A adds that the naive fix is **unreachable code**.
Accepted. The fix would give sub-confirmed links graded weight, reintroducing a feedback loop that threatens
the monotone-termination argument the fixpoint rests on (`cluster.py:6-9`) and therefore G2 determinism — a bad
trade in the stage whose whole purpose is making formation merges *harder*, and its absence errs toward honest
fragmentation, which §6 declares the goal.

**What must be said out loud:** *relational scaffolding only helps where the anchor actually merges; a merely
`probable` anchor lends no support at all — it is a step function, not a graceful degradation.* Without that
disclosure a reader would wrongly believe lever 2 degrades smoothly.

### And lever 2 is weaker still — places are not the clean anchor the design claims

`places.augment` runs **after** `resolve_entities` (`resolve/__init__.py:181` vs `:177`), so place merges are
**invisible to `relational_score`**: two units based at differently-named-but-identical sites do not share a
neighbour key. spine/13 §6 lever 2 names places as a clean anchor the instance layer crystallizes onto —
**mechanically they are not one.** Combined with F9, lever 2 is weaker than the design assumes in **two
independent ways**. The ordering fix is cheap and belongs in S3.

### Also unbuilt, and depended upon

**"Rarity-graded name" has no implementation anywhere** — yet D-13.2 and D-13.10 both rest on it ("name
contributes a *rarity-graded* score"). Either S3 builds it or the design must stop claiming it.

---

## Summary of the three-way disagreements and how they resolved

| Question | Analyst A | Analyst B | Orchestrator (pre) | **Decided** |
|---|---|---|---|---|
| `NAME_VARIANT` | raise-only | raise-only | authoritative + normalized-equality | **raise-only** — an authoritative bind bypasses banding, so this *is* the name-verdict lane |
| `UNAMBIGUOUS_ANAPHOR` | authoritative + structural gate | raise-only | authoritative + type-unique gate | **authoritative + type-unique gate** — the gate is checkable; raise-only forfeits lever 1 and manufactures nameless orphans |
| Grade gate on a bind | not raised | required | mirror the critical wall | **required** — a bind acts harder than a stated `same-as`, which is an inversion |
| Contrast strength | band ceiling at *probable* | grade-gated pairwise wall + band demotion | raise-wall | **band ceiling at *probable*, ungraded** — the ceiling cannot shatter, which removes the harm the grade gate defended |
| Doc-sameness carrier | `Entity.doc_ids` | atom→doc index | parse the claim-id prefix | **`Entity.doc_ids`** — no id-format coupling |
| Designation | composite AND-key identifier | non-perishable discriminator | non-perishable discriminator | **composite AND-key** — makes the operator requirement structural, not dependent on the broken namespace check |
| F9 | accept + disclose | accept + disclose | accept + disclose | **accept + disclose** |
