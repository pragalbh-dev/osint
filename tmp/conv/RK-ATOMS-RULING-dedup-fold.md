# RK-ATOMS ruling — the conflicting-referent fold, and a pre-existing nondeterminism it exposed

**Orchestrator ruling, 2026-07-25.** The independent test hand identified that the spec does not say what
`dedup_within_doc` must do when two folded mentions carry **different** referent values, and demonstrated that
the obvious implementation is **input-order dependent**. Verified independently before ruling.

## The verified mechanism

`ingest/dedup.py:224` — `representative = min(members, key=_earliest_docref_key)`. Python's `min` returns the
**first** minimal element, so when two members tie on `_earliest_docref_key` the survivor is whichever arrived
**first in input order**. The docstring's claim that *"the pass is itself order-independent"* holds for the
**output ordering** and for the `doc_ref` union (both explicitly sorted) — but **not** for the choice of
representative. Any field that differs between tied members and is **not** part of `_claim_signature` is
therefore order-dependent. The test hand proved this empirically using `attributes` as a stand-in: forward
input yields one survivor, reversed input yields the other.

## The ruling: a differing referent BLOCKS the fold — the referent joins the dedup signature

**Rejected: "one referent wins, the other vanishes."** Two independent reasons, either sufficient:
1. **It is nondeterministic** (the mechanism above) and would inherit that nondeterminism into the identity
   substrate — directly against G2 and the pure-recompute guarantee. `lane.py` phase 1 is a concurrent fan-out,
   so input order is not even stable in principle.
2. **It is a silent drop of evidence** — the one thing this project's append-only doctrine forbids.

**Rejected: "keep both referents on one claim."** A claim atom is *per-mention bedrock*; giving it a set of
referents makes the grain ambiguous exactly where S4 will key identity off it.

**The ruling — and the reason it is the right shape:** a referent is the *source's own stated grouping* of its
mentions. Two claims with the **same stated content** but **different referents** means coref read them as
different referents. Folding them and picking one would assert that those two referents are **one** — and that
is a **grouping decision**, which **D-13.18 places at rebuild, never at ingest**. Dedup's job is mechanical
de-duplication of identical mentions; it has no business deciding identity.

So: **add the referent to `_claim_signature`.** Then claims that differ in referent simply do not group, and
the conflicting-fold case **cannot arise** — the problem is dissolved rather than adjudicated.

**Why this is safe and, in S1, free:**
- **Deterministic** — no choice between conflicting referents is ever made, so no tie-break is consulted.
- **Nothing dropped** — both claims survive as what they honestly are: two referents each asserting the same
  fact, which Tier-1 may later merge *or decline to* (the honest-fragmentation outcome the design wants).
- **Byte-identical at S1** — every referent is `None` in S1, so a uniform `None` adds nothing to the signature
  and changes no grouping. It is inert now and correct from S3. That is the whole point of a dormant field.
- **Right division of labour** — identity stays *earned* at rebuild, which is the re-key's entire thesis.

## Separate finding, recorded, NOT S1's to fix

The representative tie-break is **pre-existing latent nondeterminism** independent of the referent: any
non-signature field differing between tied members leaks input order into the output. Adding the referent to
the signature removes the *referent* instance of this, but not the general case.

**Do not fix it in S1** (out of scope, and the stage's invariant is zero behavioural change — a tie-break change
could move the golden). **Record it as a defect** for whichever stage next owns `dedup.py`, and **correct the
docstring's over-claim** — a comment asserting order-independence that is only partly true is worse than no
comment, because it stops the next reader from checking. Candidate real fix later: make the representative
choice total by adding a deterministic final key (e.g. the pre-dedup construction id), not by relying on `min`'s
tie behaviour.

**Also noted from the test hand, and accepted as *not* an S1 requirement:** claim-id references orphaned by a
fold are a real hole, correctly filed as a non-strict `xfail` rather than smuggled into this stage.
