# Session RK-SPIKE (S0) — close the design opens; prototype the concentrated risk

**Wave 0 · depends on nothing · throwaway branches, no production code.**
This file is thin by design (plan §6 step 2). The spec is `../01-replumb-implementation-plan.md`
**§7 RK-SPIKE**; the *why* is `../../spine/13-type-instance-and-identity-replumb.md` §§6/7/8/10/13; the
reasoning trail is `../../../tmp/conv/replumb-13-design-review.md`. **The verified current-code baseline is
`../../../tmp/conv/rk-spike-code-facts.md` — it overrides any contrary statement in the design docs**
(working-principles #6).

## Goal (plan §7 RK-SPIKE)

Retire the three open micro-decisions and de-risk the one concentrated design unknown **before** any
production code, so the S1→S4 chain does not build on guesses.

## Scope

1. **Close the three micro-decisions** (plan §11 · spine/13 §13):
   (a) Tier-0 auto-bind graded by coref category · (b) Tier-1 same-document comparison + the strength of the
   contrastive anti-merge prior (F5) · (c) discriminator priority for cross-doc clustering.
2. **Prototype characterize-and-cluster** (spine/13 §13 "highest-risk piece") on representative shapes:
   how a provisional instance is described richly enough to cluster cross-document, in what discriminator
   priority, and how a thin-context bind **degrades to "under-determined + named gap"** rather than
   fabricating a unit or collapsing two.
3. **Build the claim-gold slice + per-slice sub-oracle** the bake-off needs (plan §8 items 1–2), authored by
   the data hand so it is independent of both code and model.

## Constraints

- **No runtime embeddings** (DECISIONS lock :116). Only alias/rarity + BM25 + fuzzy + relational/discriminator.
  Guard this in the prototype so an implementer is not tempted to reach for sentence-transformer similarity.
- **G6 no-magic-numbers.** Every threshold, cap, weight and category list this session decides must land in
  `config/`, never a code literal — name the file and key.
- **Target-first (working-principles #1).** Decide on general principle. Nothing about the current corpus,
  the keyless boot, an existing demo beat, or the already-extracted claims may gate the policy. Where a
  target-correct policy costs a demo beat, the *data pass* re-carries the beat — the policy does not bend.
- **The non-negotiable.** Absent / ambiguous / contradictory evidence ⇒ an explicit "insufficient evidence",
  naming what is missing. An under-individuated instance must *say so*, not fall silent.
- **No production code this session.** Output is `tmp/` prototypes + doc updates + the gold slice.

## Three hands (plan §6 step 4 — structural, not by discipline)

| Hand | Worktree / branch | Sees | Never sees |
|---|---|---|---|
| **Implementer** (prototype) | `wt-RK-SPIKE-impl` / `spike/rk-impl` | this spec + the code facts + its own invented shapes | `corpus/**`, `answer_key.json`, the test hand's cases |
| **Test author** (cases) | `wt-RK-SPIKE-test` / `spike/rk-test` | this spec only | the prototype branch |
| **Data hand** (gold) | `wt-RK-SPIKE-data` / `spike/rk-data` | the corpus (read-only) | both other branches |

The data hand additionally authors **abstracted** shape fixtures (real structural difficulty, invented
entities) so the implementer gets the hard shapes while staying corpus-blind.

## Gates touched

None ship this session. RK-SPIKE **specifies** what G16 (co-location cap), G18 (relationship-conflict wall)
and the Tier-0/Tier-1 policy must assert, so RK-COREF's gate fixtures are non-vacuous — a gate that cannot
fail is a gate that lies.

## Acceptance (plan §7 RK-SPIKE)

- [ ] Each micro-decision has a **decision + rationale + named mechanism** (config file · key · value shape ·
      function touched · exists-or-new), moved from "open" to "decided" in `spine/13` §13.
- [ ] The prototype demonstrates the **degrade-to-gap** path on at least one thin-context case, using **no
      embeddings**.
- [ ] The claim-gold slice + per-slice sub-oracle exist and are independent of the answer key (disagreements
      recorded, not silently adopted).
- [ ] Independently-authored cases run against independently-authored prototype code on independently-authored
      shapes; every unexplained divergence is a regression until proven otherwise (working-principles #4).
- [ ] `PROGRESS.md` row + `DECISIONS.md` entries + the five-beat handoff, noting **how the three-hands
      separation was evidenced**.

## Out of scope

Production code (S1 owns the first line of it) · minting referent atoms (S3) · the name-key cut (S4) · the
bake-off's scoring harness (RK-BAKEOFF; this session only supplies its gold slice).
