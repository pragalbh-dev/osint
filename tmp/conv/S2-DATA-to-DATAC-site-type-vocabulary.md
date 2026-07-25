# S2 DATA → DATA-C / RK-DATA — `site_type` is free text used for four different kinds of thing

**From:** the independent DATA hand for RK-LAYER (S2), branch `s2/rk-data`, 2026-07-25.
**Nothing was changed.** `corpus/**`, `config/**`, `answer_key.json`, `SCENARIO_MANIFEST.json` untouched.
**No fix is requested.** This is a heads-up with one coordination ask for the RK-DATA coverage additions.

## What I found

S2 is required to tag the `based-at` supersede instance key by **site kind** (R1.3 / C1), so that one body at
its garrison *and* concurrently at a forward site is two valid basings rather than a relocation. The
discriminator that rule turns on is the `site_type` attribute on `basing_site`.

In the frozen corpus `site_type` is **free text with no enumeration anywhere** — not in `config/ontology.yaml`
(a bare attribute entry), not in `config/resolution.yaml`, not in code. Its actual values conflate at least
four different kinds of thing:

| What the value denotes | Frozen-corpus examples |
|---|---|
| a kind of **place** (what the key needs) | `garrison`, `airfield`, `centre`, `dispersal site`, `deployment site` |
| **how we learned about it** | `observed-imagery-site` (the single most common value; stamped by the imagery ingest path), `stated_destination` |
| the **equipment** at it | `HQ-9/P site`, `long-range SAM battery position`, `air defense node` |
| an **area class** | `candidate coverage area`, `air defence belt` |
| a free **descriptive phrase** | `prepared revetment complex / airfield site`, `Pakistan Army/PAF joint-use facility` |

## Why it matters, concretely

Three consequences, all verified against the frozen claims:

1. **The two ends of the flagship relocation are in different buckets.** The origin carries
   `prepared revetment complex / airfield site`; the destination carries `airfield` in one document and
   `Pakistan Army/PAF joint-use facility` in another. A supersede key tagged on the **raw stated string**
   therefore gives the before-edge and the after-edge different keys — so the relocation is never seen as one
   instance and **never fires**. Silent, and it looks like correct de-confliction.
2. **One site is two buckets.** The destination alone carries two different `site_type` strings from two
   documents, so the same site does not key stably even without a relocation.
3. **Present-and-absent inside one document.** One site name appears three times in a single document as three
   separate `basing_site` entity claims, with `site_type` present on one and absent on two. With
   first-claim-wins attribute collection, **whether the key is defined at all depends on claim ordering.**

## What this is not

Not a data error, and **not** an argument against the site-kind key — R1.3's reasoning stands, and this drift
is realistic (different publishers describe the same place differently; that is exactly the value-normalization
case `config/resolution.yaml` already warns about for country names). It is a design input for S2, which owns
`config/ontology.yaml` and will decide whether the key normalizes to a class, where the mapping lives, and
what an absent or unmappable value does. Those are S2's calls, not yours, and not mine.

## The one ask, for RK-DATA's coverage additions

The corpus has **no** one-body-two-sites-concurrently pair, so the C1 rule has nothing to exercise today (the
existing `test_supersede` xfail says as much). If RK-DATA authors the §B6 ORBAT addition:

- **please state the site kind in a small, repeated vocabulary** rather than in fresh descriptive prose per
  document — one document calling a place a "depot" and another calling the same place a "logistics and
  storage establishment" adds coverage and **no testability**;
- and if a simultaneous garrison-plus-forward-site pair is authored for the C1 rule, **state the kind on both
  ends and state the concurrency in the source's own voice**, otherwise the fixture cannot distinguish "two
  valid basings" from "a relocation whose end date is unstated".

Nothing here anticipates or requests the corpus regeneration decision; per plan §10 that needs a
user-approved, EVAL-coordinated `DECISIONS.md` entry with the old oracle archived first.

## Where the detail lives

`tmp/spike-rk/s2-fixtures/S2-DATA-FINDINGS.md` §2 (this item, with the checks) and §3 (five further ontology
expressiveness gaps of D12's kind, including that `trading_org` is named by no edge type at all, and that all
492 frozen claims are `polarity: positive` so no refutation was ever recorded). The abstract fixtures that
carry these shapes are `tmp/spike-rk/s2-fixtures/s2-shapes.{json,md}` — `F6a` / `F6b` / `F6c` for this one.
