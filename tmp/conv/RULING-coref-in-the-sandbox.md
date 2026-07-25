# Ruling — bake coreference into the synthetic sandbox? Yes, with one boundary that must not blur

**Question (user, 2026-07-25):** we curate a synthetic sandboxed gold set anyway — can't we bake coreference
into it for testing, or is that a bad idea?

**Answer: yes, do it — and it is the only practical way to test S3 at all. But it tests the *consumer*, never
the *producer*, and conflating those two would make the system look better than it is.**

## Why it is necessary

Coreference is off today (two independent gates), so **the frozen bundles contain no coref annotations at all**.
Testing Tier-0/Tier-1 on real data would otherwise require a **keyed re-extract** with coref enabled — which is
costly, confirmed **non-deterministic**, and has broken the hero query before. A sandbox with coref baked in
removes that dependency entirely and lets S3 be developed and tested offline, keyless, deterministically. The
sandbox path is already gitignored, so it cannot contaminate the frozen corpus.

It is also **already precedented in this project**: the spike's data hand built abstracted shape fixtures
carrying exactly this — coref clusters, their licensing category, and the verbatim licensing quote — so the
corpus-blind implementer could work the hard shapes without seeing real content. This proposal is that pattern,
scaled up.

## The boundary that must not blur

There are **two different things** that both get called "testing coref", and a baked sandbox only covers one:

| | What it asks | What tests it | Baked sandbox? |
|---|---|---|---|
| **Consumer side** (resolution) | *Given* coref handles, do Tier-0/Tier-1, the per-layer policy, the caps and the walls behave correctly? | a sandbox with coref baked in | **Yes — this is exactly right** |
| **Producer side** (extraction) | Does the extractor *actually emit* correct coref handles on real prose — how often does it over-bind or under-bind? | the hand-labelled **claim-gold slice** + the bake-off's coref-binding accuracy metric | **No — a baked set cannot answer this** |

**Why the distinction is load-bearing rather than pedantic.** The spike's own finding (**F6**, spine/13 §10/§13)
is that the replumb *moves* the load-bearing extraction burden **onto** coref and discriminator capture — the
risk "concentrates in extraction quality, not just resolution." If we bake coref by hand and then test against
it, we are testing the resolver against **our own idea of what the extractor would produce**. Every hand-authored
cluster is implicitly a *correct* cluster, so the resolver never meets the failure mode that actually matters:
a **wrongly bound** cluster from a real model on real prose. The suite would go green while the dominant risk
sits untested — the same shape as a gate that cannot fail.

**So the rule:** a baked sandbox is a legitimate, deterministic **fixture for the resolution machinery**. It is
**not** evidence that coref works, and it must never be cited as such. Producer quality is measured exactly where
the plan already puts it — **§8's coref-binding accuracy against the claim-gold slice, post-S3**, which is
hand-labelled from real documents by a hand that authored no code.

## Practical requirements if we build it

1. **Bake in the failure modes, not just the successes.** Include deliberately **over-bound** and **under-bound**
   clusters, and clusters whose licensing quote does *not* support the bind. A sandbox of only-correct coref
   tests optimism. The gates that matter (the decline path of **D-13.18**, the co-location cap, the walls) can
   only fire on bad input.
2. **Cover all three real categories** — `EXPLICIT_EQUIVALENCE`, `NAME_VARIANT`, `UNAMBIGUOUS_ANAPHOR` — plus the
   cases that must fail each category's deterministic gate (a quote missing one surface form; a mark-vs-name
   collision; two candidate antecedents of the same type). Those are D-13.17's gates; without negative cases the
   gates pass vacuously.
3. **Carry the licensing quote verbatim**, because D-13.17 makes it load-bearing — and note the audit finding
   that the quote is currently *written but read nowhere*, so the sandbox is also how that wiring gets tested.
4. **Label it unmistakably as synthetic** and keep it out of the frozen corpus and out of any recall metric
   scored against the answer key. It is a fixture, not evidence.
5. **State it in the design-note disclosures**: the resolution machinery is validated on synthetic coreference;
   real-world coref binding accuracy is measured separately, on hand-labelled documents.

## Verdict

Build it, as an **S3 fixture** (owner: the data hand, independently of whoever implements S3). It removes a keyed,
non-deterministic dependency from the critical path — a clear win. Just never let "the sandbox passes" stand in
for "the extractor binds correctly": those are two claims, and only one of them is what the mission rests on.
