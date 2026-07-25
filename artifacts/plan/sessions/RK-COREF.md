# Session RK-COREF (S3) — coref-cluster minting, per-layer policy, co-location cap, relationship wall

**Wave 3 · depends on RK-LAYER (S2, integrated at 0cfc069) · offline.**
Thin by design. Spec: `../01-replumb-implementation-plan.md` **§7 RK-COREF** (incl. **item 7**, the closures) ·
contracts **A7** (coref half) · gates **G16 / G18 / G19** (§5, §5a) · **§5b** the closure table.
The *why*: `../../spine/13-*.md` §6 (two-tier resolution + the three levers), §7 (what earns identity; the
co-location cap; the two guards), **D-13.8/13.9/13.10/13.14/13.17/13.18/13.19/13.20**.

**Read the prior stages first — all load-bearing:**
`../../../tmp/conv/rk-spike-code-facts.md` (verified baseline — **overrides any doc**) ·
`../../../tmp/conv/rk-spike-DECISIONS.md` (D-13.17…20, C1–C4) ·
`../../../tmp/conv/rk-spike-REVIEW-VERDICT.md` (**C5–C11**, and §4's two findings the spike missed) ·
`../../../tmp/conv/rk-spike-verified-defects.md` (**D3, D4, D6** are this stage's business) ·
`../../../tmp/conv/RK-LAYER-RULINGS.md` + `RK-LAYER-INTEGRATION-TRIAGE.md` ·
`PROGRESS.md`'s **S1 and S2 handoffs** (nine follow-ups between them; five are yours).

## This is the stage the whole re-plumb exists for

S1 gave claims a stable address. S2 split design from instance. **S3 makes identity *earned*** — the doc-local
coreference cluster becomes the mint grain, and the judge finally gets the pairs it was built for.

**The invariant, third time it changes:** S1 = nothing changes · S2 = flag-off identical / flag-on changes ·
**S3 = fragmentation metrics become meaningful for the first time.** Per **F8** S2 deliberately fragments
per-mention; that was transient and expected. **S3 is where it must resolve — and it must resolve by earning
merges, never by loosening a threshold.** If you are tempted to lower a floor to reduce fragmentation, that is
the trap the whole design exists to prevent (it is the name-collapse bug wearing a different hat). Report it.

## Scope

1. **Promote Tier-0 coref to a required tier.** `ingest/coref.py` from optional to required; the doc-local
   cluster **groups the per-mention claim atoms** and is **where the referent atom is minted** (`make_referent_id`,
   dormant since S1, invoked here). **Two independent gates must both flip** — the producer
   (`config/credibility.yaml` `coreference`, currently commented out) *and* the consumer
   (`config/resolution.yaml` `coref_authoritative_evidence`, currently `[]`).
2. **D-13.17's auto-bind policy.** `EXPLICIT_EQUIVALENCE` and `UNAMBIGUOUS_ANAPHOR` authoritative, each behind
   **both** a deterministic gate **and** a source-grade floor; `NAME_VARIANT` **raise-only permanently**.
   **Why the grade floor is not optional:** an authoritative pair is a **Phase-1 bootstrap trigger** — it merges
   at hardcoded `1.0` and **bypasses banding entirely**, so no cap restrains it, and today a coref bind reads
   **no grade at all** while a source-stated `same-as` is grade-floored *and* raise-only. That inversion is the
   sharpest gap in the substrate.
   - **C5**: the gate is per **link** (anchor→member); a cluster binds only over passing links, each failing
     link becoming an injected Tier-1 candidate pair. A **partial** bind, not all-or-nothing.
   - **The anaphor gate must be POSITIVE** — a named, declared, ontology-typed antecedent, exactly one
     type-compatible mention, `unknown`-typed endpoints **counting as compatible**. An *absence* test fails
     open under extractor under-reach. **If the positive gate is not built, `UNAMBIGUOUS_ANAPHOR` reverts to
     raise-only.**
   - **C9**: an authoritative bind may instantiate **only over entity ids attested in the contributing
     document** — it shares (b)'s `Entity.doc_ids` carrier and must not ship without it.
3. **D-13.18 — the rebuild may DECLINE a grouping.** The referent atom is **evidence about a grouping, never
   the address**. An intra-referent critical-discriminator conflict de-groups to claim-atom granularity and
   raises. **The check must read `attr_history`, not `attrs`** — first-claim-wins scalar storage makes the
   conflict invisible otherwise. **C3**: the decline fires on **relationship** conflicts too, using the same
   overlapping-time predicate as G18 under C1's rule.
4. **Tier-1 cross-doc + same-doc (F5/D-13.19).** Cluster *provisional instances*, not bare mentions. **Tier 1
   already compares same-doc pairs — there is no document filter anywhere in `resolve/**`, so that half needs
   no code.** Add `Entity.doc_ids` (populated where the doc ref is currently dropped; **not** by parsing a
   claim-id, **not** `source_ids` which is the *publisher*), and a **contrastive channel** on coref
   (`coref-distinct-from`, its own lane — **never** the stated `distinct-from` rail, which is hard, transitive
   and ungraded: every ORBAT list contains an enumeration). Same-doc stated contrast ⇒ **band ceiling at
   `probable`**, ungraded, **a band name not a float**. Absence of contrast is **neutral**.
5. **Per-layer identity policy (D-13.10)** — one judge, a permissive per-layer *profile*, never a second code
   path. **Requires splitting `attribute_score` into two signals (`name` / `discriminator`)** — they are already
   computed independently and fused at one `max`, and **without the split D-13.10 cannot function at all**.
   Name caps at *possible* for **every** layer.
6. **The discriminator ladder (D-13.20)** — differing designation (veto) > composite unique id >
   temporally-witnessed continuity > shared designation > operator (post-normalization) > geography (perishable)
   > relational > name. **A shared designation is NOT a unique identifier**: `hard_id_fields.unique` is a list of
   **composite AND-keys** (`(service_branch, designator)`), because designations are reused across armies and
   across time. Preserve the bill-of-lading asymmetry: **differing identifiers veto, shared ones do not confirm.**
   - **C7**: normalization is a prerequisite for walling on **any** slot; an unnormalizable stated critical value
     ⇒ **no wall AND no fusion** + a named gap. **A gap must bind the fusion path, not merely annotate it.**
   - **C6 (re-specified — read the closure)**: `perishable` becomes a four-value **`time_role`**
     (`durable | perishable | constitutive | identifying`). A boolean cannot carry three states. `constitutive`
     is what lets a **presence** confirm; `identifying` what lets a **place** confirm — the missing rung without
     which lever 2 cannot exist. **No back-compat**: a bare `perishable:` key is a loud error.
7. **The co-location cap (D-13.14 / G16)** — shared design+site+operator ⇒ presence-merge fine, **formation
   merge not fused**; confirming a formation needs a unit-level discriminator. **This is anti-fabrication
   machinery, not OOB hygiene:** because `based-at` is functional and unit-keyed, a formation over-merge makes
   two sites one unit's before/after and the supersede path then draws a relocation, removes the analyst, and
   deletes the retired edge's Known Gap. **G16 asserts all three absences (C2).**
8. **The relationship-conflict wall (D-13.8/G18)** — a **stated** `based-at`/`operated-by` conflict at
   overlapping times **within one `site_type`** hard-walls a merge. **C1 as amended by S2: the rule is per
   `(subject, predicate)` over every basing of that subject, applied as a post-pass after derivation — never a
   key input.** A per-edge tag silently killed the flagship relocation: **separation *is* de-confliction, so a
   partial tag is worse than none.** **G18 must name the wall channel and assert an analyst-visible reason** —
   built the geo-veto way it would be non-transitive *and* invisible while the gate passed.
   **C11: `operated-by` needs a producer** — add it to the extractor contract (one field in the A7 schema you
   already amend), or the gate must declare the arm fixture-only and it goes in the disclosures.
9. **G19 — cross-namespace and cross-type non-fusion.** Close **D4**: `namespace_compatible` never guards the
   Phase-2 fuzzy fixpoint, and relational blocking emits pairs with **no namespace key**. **And the review found
   worse (§4): alias self-equivalence is reflexive where its docstring promises a real alias link**, so the
   namespace-gated exact-name branch is never reached — making cross-operator *and cross-type* fusion reachable
   in **Phase 1**. Fix both: make equivalence non-reflexive, and type/namespace-gate the alias branch.
10. **Bind the caps to the Phase-1 bootstrap.** §4: **name is a verdict in Phase 1 at every type**, and the caps
    exist only in Phase 2 — the widest name-only fusion path bypasses the bands entirely and never reaches
    `confirm_is_durable`. R1.2/R3.1/R3.2 must bind the **bootstrap disjunction**, not just the collection loop.
11. **Fix the `places.augment` ordering** — it runs *after* `resolve_entities`, so place merges are invisible to
    `relational_score`. Together with **F9** this makes lever 2 weaker than §6 claims in *two* ways.

## Explicitly NOT in scope
**C8 / D6 source-independence** — user ruling: the rule (two independent sources ⇒ confirmed) stands; re-keying
*detection* onto evidential lineage is **roadmap**, disclosed, not built. · Cutting the name-key (**S4**) ·
the corpus regen (**RK-DATA**) · **F9**'s graded sub-confirmed relational weight (accepted + disclosed).

## Gates
**G16** (three-part per C2) · **G18** (channel named, analyst-visible reason, C1's per-subject rule) ·
**G19** (both phases, incl. the alias branch) · plus existing **G7**. **All fixtures must be abstract** — the
corpus holds essentially one numbered formation, one stated basing and zero serials, so it cannot exercise them.

> **Count corrected (2026-07-25):** the corpus holds **five `based-at` claims over three subjects**, not "one
> stated basing". The numbered-formation and zero-serials halves stand, and the requirement (abstract fixtures,
> because the corpus cannot exercise these gates) is unchanged — the sole multi-basing subject carries a dated
> succession, not the conflict G18 needs. This sentence is quoted verbatim in `tests/_rk_coref.py` and
> `tests/gates/test_g16_colocation_cap_spec.py`, both of which now carry the same correction.

## Owned paths
`ingest/coref.py` · `resolve/{__init__,cluster,rconfig,aliases,scoring,entities}.py` · **`config/resolution.yaml`** ·
`config/credibility.yaml` (coref producer block) · A7 mention schemas (`ingest/extract.py`) ·
`tests/resolve/**` · `tests/gates/test_g16_*`, `test_g18_*`, `test_g19_*`.

## Acceptance
- [ ] Coref required; referent atoms minted at ingest; **both** gates flipped.
- [ ] Authoritative binds pass a deterministic gate **and** a grade floor; `NAME_VARIANT` raise-only; the
      anaphor gate is **positive** (or the category reverts to raise-only).
- [ ] A conflicting cluster **declines** (from `attr_history`), on attribute **and** relationship conflicts.
- [ ] `name` and `discriminator` are separate signals; name caps at *possible* at every layer **and cannot fuse
      in Phase 1**.
- [ ] Co-location never confirms a formation **and draws no relocation**; G16's three absences hold.
- [ ] A stated conflict at overlapping times within one `site_type` hard-walls, with an analyst-visible reason.
- [ ] Cross-namespace/cross-type pairs cannot fuse in **either** phase.
- [ ] **Fragmentation resolves by earned merges, with no threshold loosened.** Report before/after counts and
      justify each merge class as earned — predict-then-verify (#4).
- [ ] Residual fragmentation reports as a `/coverage` gap.
