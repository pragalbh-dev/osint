# For the DATA hand — the sub-oracle must not confirm on a single source

**Status: user-ratified 2026-07-25.** Not a question; a fix. Recorded here per the frozen-data rule (the
orchestrator does not edit data artifacts unilaterally).

## The defect

`tmp/spike-rk/gold/sub-oracle.json` grades **twelve entries `confirmed` on a single source document each**.
That violates the system's own rule:

> `config/credibility.yaml:101` — `min_independent_groups: 2` — *"≥2 independent looks required to reach
> `confirmed`"*

One source cannot confirm. There is no interpretive question here.

Additionally: **one alias entry is graded `confirmed` on a single hedged grade-C source** while listing among
its supporting rows a row that, combined with another, implies the *opposite* equivalence. Two of its four
cited rows do not support what it claims.

## Why this matters more than an ordinary data nit

The sub-oracle is the **yardstick** — plan §8 item 2 exists precisely so slice recall is scored against it
rather than the full answer key. A yardstick that confirms on one source is **more confident than the system it
grades**, and biased in the direction that flatters us: it will score the system as under-confident exactly
where the system is being correctly cautious. That inverts the measurement.

## The fix

1. **Cap every single-source entry at `probable`.**
2. **If** you believe a specific case genuinely justifies a bypass — the strongest candidate is a **shared
   unique identifier inside one primary record** (a bill-of-lading reference appearing in one customs
   document), which is arguably one *look* but an unusually hard identifier — then do **not** leave it
   implicit. Record it as an explicit `DECISIONS.md` entry stating the rule, the rationale, and its scope, so a
   reviewer sees a decision rather than an inconsistency. Absent that entry, the cap applies.
3. **Fix the alias entry**: re-cite it on the row that actually supports it, drop the two rows that do not, and
   move the contradicting row into the tension list where it belongs (or state explicitly that it is
   counter-evidence being over-ridden, and why).

## What is NOT being asked of you

**Do not re-key how independence is detected.** That is a separate, deferred item (see
`rk-spike-verified-defects.md` **D11**): independence is currently keyed on publisher/source-type rather than
evidential lineage, so a source that reads another source's report still counts as a second look. The **rule**
(two independent sources ⇒ confirmed) is correct and stays; only the *detection* refinement is roadmap, because
the independence-group mechanism already exists and already applies the lineage idea to inferences
(`config/credibility.yaml:160`), making the extension cheap later. It is **disclosed** in the design note
meanwhile.

So: the flagship Rahwali confirm **stays `confirmed`** — mechanically it is two independent looks. Do not
demote it as part of this fix. The only open data question there is whether the corpus should eventually carry a
genuinely independent second look, which is a coverage item, not a correction.
