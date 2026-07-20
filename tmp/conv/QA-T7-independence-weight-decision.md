# Decision needed: the independence weight is applied twice (D-P4.14 / residual #11)

**Raised by:** QA-T7, 2026-07-20. **Deliberately NOT fixed.** This is a credibility retune; the register
marks it RAISED-NOT-RATIFIED and says it must not be folded into another change. Confirmed accurate on
inspection, and now quantified so the call can be made on numbers rather than on principle alone.

---

## What the code does

An independence group carries a `weight`: two genuinely cross-discipline looks weigh 1.0 each, a
same-class-but-passing pair weighs 0.5. That weight is consumed in **two** places:

1. **Magnitude** — `group_confidence()` returns `strongest_claim_credibility × group.weight`, and those
   values feed the noisy-OR that produces `assertion_confidence`. A half-weight group therefore
   contributes half as much *confidence*.
2. **Count** — `_effective_looks()` sums the same weights and the result is compared against
   `min_independent_groups` (currently **2**). A half-weight group therefore also counts as half a
   *look*.

So a same-class pair is discounted twice: once in how much it raises confidence, once in whether it
clears the "≥2 independent looks" structural gate.

## What the design says

`spine/04` defines `c_g` as **the max `claim_credibility` in group g** — no weight factor — and defines
the CONFIRMED gate as **≥2 independent origin groups**. The weight is introduced once, in the *grouping*
rule ("same-class-but-passing = 0.5 weight"). Read literally, the weight belongs in exactly one of the
two places, and the code puts it in both. The implementation is therefore **stricter than the ratified
design**, not looser — it under-claims rather than over-claims, which is why it is safe to leave.

## Blast radius, measured on the full corpus (withhold disabled)

- 334 independence groups exist: **248 at weight 1.0, 86 at weight 0.5.**
- 29 elements (nodes + edges) carry more than one group; **26 of those are weighted down.**
- **26 of 294 assessed elements** would move their `assertion_confidence` if the weight were removed from
  the magnitude and left only in the count. Some of those sit near the 0.80 confirmed cut, so status
  flips are possible — this is not a cosmetic change.
- Current status distribution: 13 confirmed · 157 probable · 58 possible · 12 insufficient · 1 stale.
- **The flagship demo path is not affected either way.** The Rahwali basing edge's two groups both weigh
  1.0 (`assertion_confidence` 0.7905, effective looks 2.0), so no option below moves it.

## The options

**(A) Leave it as-is** *(recommended for the deadline)*. The double discount only ever makes the system
*less* willing to say "confirmed", which is the safe direction for the non-negotiable. Cost: the code
does not match `spine/04` as written, and a sharp reviewer reading both could call it out. Mitigation:
state it in the design note as a deliberate conservatism, not a bug.

**(B) Weight the count only** — drop `× group.weight` from `group_confidence()`. Restores `c_g` = max
credibility exactly as spine/04 defines it, and keeps the structural gate strict (two same-class looks
still total 1.0 and cannot reach the ≥2 threshold). Moves 26 elements' confidence upward; needs a re-read
of every flex expectation and a `make beat` re-check.

**(C) Weight the magnitude only** — count *groups*, not weighted looks, in the CONFIRMED gate. This is the
looser direction: two same-class looks would satisfy "≥2 independent groups". **Not recommended** — it
weakens precisely the gate that makes the aligned-interest and echo-burst flexes work.

**(D) Make it configurable** — a `independence_weight_applies_to: [magnitude, count]` knob in
`credibility.yaml`, defaulting to today's behaviour. Fits the config-driven principle and defers the
judgement, but adds a knob nobody will turn before the call.

## Recommendation

**(A) for now, (B) after the deadline**, and disclose (A) in the design note. Whichever is chosen, it must
land as its own change with its own before/after status table — not folded into another fix.
