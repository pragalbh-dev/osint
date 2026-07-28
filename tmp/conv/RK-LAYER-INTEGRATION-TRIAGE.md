# RK-LAYER (S2) — integration triage: 7 failures, 3 causes

Independently-authored tests (`s2/rk-test`, never saw the impl) against the independently-built implementation
(`s2/rk-impl`, corpus-blind): **1166 passed, 7 failed**. All 7 are in the **test hand's** files, so the
implementation misses the independent spec in 7 places. Triaged by the orchestrator with the facts verified.

Plus one **merge conflict** worth recording: both hands wrote `tests/gates/test_g15_presence_not_fused.py`
(add/add). **Resolved by keeping both** — the implementer's at the canonical name, the test hand's at
`…_spec.py`. Two independent takes on one gate are an asset; picking one would discard half the coverage. (S1
avoided this only because the two hands happened to choose different filenames.)

---

## Cause 1 — MY spec error: the session file states counts my own later rulings invalidated (2 failures)

`test_the_shipped_ontology_still_declares_the_stated_type_and_attribute_counts` ·
`test_every_attribute_entry_declares_a_layer`

**The implementation is correct.** Measured: **15 node types, 90 attribute entries, every one tagged**, using
three values (`design` / `instance` / `meta`) exactly as **L3** required.

**The test is faithfully asserting my session file**, which says "81 attribute entries, 13 node types". Those
numbers went stale the moment I ruled **L2** (add an instance-layer *presence* type) and **L4** (declare a
numeric equipment-count attribute) — i.e. my own rulings told the implementer to add precisely the types and
attributes the session file then said should not exist. The test hand had no way to know; it was given a count
and told the config was the source of truth.

**Ruling: the session file is wrong, not the code.** Fix the stated counts, and **stop stating a frozen count
for a surface this stage is meant to grow**. The durable assertion is *"every node type and every attribute
entry is classified with a legal value, and no entry claims two layers"* — which is count-independent and
survives S3/S4. A frozen count on a growing surface is a tripwire pointed at ourselves.

---

## Cause 2 — a genuine design disagreement, and both sides are right (1 failure)

`test_the_basing_derived_bundle_suffix_is_gone`

- **Test hand:** with the offline pass deleted, the seed loader must stop globbing `__basing.json`, or a frozen
  bundle replays an inference the rebuild now derives — **the same attribution arrives twice**, and the frozen
  copy never ages or re-derives.
- **Implementer:** removing the glob unconditionally **is itself the flag-off byte-identity break**, so it must
  die with RK-DATA's bundle removal, not here.

Both are correct about their own concern, and the spec never reconciled them.

**Ruling: gate the glob on the flag.** Flag **off** ⇒ the glob stays (byte-identity preserved, S2's safety
property). Flag **on** ⇒ the glob is skipped (no double attribution, and the derived edge is the single source).
The bundles themselves still die with RK-DATA. This satisfies both requirements with no trade — the
disagreement existed only because the flag boundary had not been applied to this particular coupling.

---

## Cause 3 — a REAL implementation defect: R1.4's guard is too broad (4 failures)

`…_is_still_promoted` · `…_is_not_machine_adjudicated_over_a_sub_confirmed_identity` ·
`…_raises_a_real_known_gap_when_nothing_is_retired` · `…_still_reads_stale`

**This is the mirror tests doing exactly what they were built for.** The test hand wrote them so that
*disabling* supersession fails as loudly as *over-promoting* it — and the implementation over-corrected in two
distinct directions:

1. **It blocks the *earned* relocation too.** *"the earned relocation was not promoted — the supersede beat must
   survive R1.4's guard."* R1.4 restrains machine promotion over an **unearned** identity; it must not disable
   promotion generally. The legitimate flagship beat has to keep working.
2. **It protects every retirement, not only an honest `insufficient`.** *"an assessable retired position reads
   'probable' — R1.4(b) protects an honest `insufficient`, it does not disable retirement."* The requirement is
   narrow: do not delete a Known Gap and do not flip `insufficient` → `stale`. A well-evidenced retirement must
   still read `stale`.
3. **The queue-pop is still happening** on the sub-confirmed path (*"the pair was popped out of the analyst's
   queue"*) — the half of R1.4 that most matters is not yet done: with the identity unearned, the analyst is
   exactly who should decide.
4. One fixture-shape mismatch (two gaps raised where the control expects one) — resolve on the merits; it may be
   the impl raising a duplicate.

**This is the most valuable thing S2's separation has produced**, and it is worth stating why: an implementer
fixing an over-promotion bug will naturally reach for the broadest possible guard, because every test it can see
rewards caution. Only an independently-authored *mirror* — which asserts the thing that must still work — can
catch the over-correction. Timidity is a failure mode, not a safe default.

---

## Also from the implementer, and load-bearing beyond S2

- **C1 must be per-`(subject, predicate)`, not per-edge — and it cannot be applied at keying time at all.**
  A per-edge `site_type` tag **killed the flagship relocation silently**: the two ends are described on
  different axes, one class mapped and one did not, they landed in different buckets, and the supersede simply
  never fired — no gap, no flag, code still deterministic. **Separation *is* de-confliction**, so a partial tag
  is worse than none. The correct rule: over **every** basing of that subject, all classes known ⇒ de-conflict;
  **any** unknown ⇒ one untagged instance, nomination withdrawn, **named gap**. And because "every basing"
  includes the rebuild-derived ones, the tag must be a **post-pass after derivation**, not a key input.
  **S3 must inherit the per-subject rule when it writes G18's wall** — this amends C1.
- **A pre-existing defect the frozen data was hiding.** A derived basing inherited the *later* of its two
  premises' dates. Since one `inducted-into` claim backs every attribution for a unit, **every basing of that
  unit inherited one identical induction date** — unorderable, so read as "in two places at once" rather than a
  relocation, and a 2021 sighting inherited a 2025 date. Fixed to the observation's own time, which the module
  always documented. **The general warning is the valuable part: anything the offline passes froze is evidence
  about an older graph.**
- **G18's `operated-by` half has no producer.** The predicate is now declared but **non-extractor**, so nothing
  can emit a *stated* `operated-by`. Either someone owns the A7 extraction extension or **that half of G18 is
  fixture-only forever** — which must be stated, not discovered later.
- **C6 is unimplementable as written:** it needs three values but `perishable` is a **boolean**, and S3 owns
  that file. Needs re-specifying before S3.
- **A2's "endpoint layers fall out of endpoint types" cannot express the worked example**, so `materializes`
  became an explicit per-edge declaration. Accepted — but it means A2's derivation claim is wrong and should be
  corrected rather than left as a contradiction.
- **D12's `(from→to)` uniqueness rule forbids one edge per customs role**, so `party_role` is an edge attribute.
  Accepted, and the reasoning is right: splitting by direction would let a flipped write turn a shipper into a
  consignee — the same fabrication class the edge exists to remove.

---

## Round 2 — 4 failures left, and one is a real design fork I have now settled

After both hands' fixes: **1179 passed, 4 failed**. The two that matter are R1.4(b)'s prohibitions, and the
hands genuinely disagree:

- **Implementer:** (b) rides (a)'s trigger — the prohibitions apply only over an **unearned** identity, because
  D-13.14 names the gap deletion as a consequence *of the over-merge*. Its unconditional first cut "broke
  flag-off byte-identity *and* the flagship together", since the flagship's own retirement is under-evidenced.
- **Test hand:** the prohibitions are **unconditional** — §7 item 7 / C2 say "no Known-Gap deletion and no
  `insufficient → stale` on the retired edge", full stop.

### The fact that settles it — `stale` is not a free label, it has a defined meaning

`credibility/status.py:49`: `_STALE = "stale"  # the freshest supporting look older than 1 half-life →
**demote confirmed→stale**`.

So in this system's own vocabulary **`stale` means "this WAS confirmed and has since aged out."** Overwriting
`insufficient` with `stale` therefore does not merely look untidy — it **asserts something false in the
system's own terms**: it claims the assertion was once established and has merely gone out of date. *An
assertion that was never established cannot go stale; there is nothing to age.* That is an over-claim about
provenance, which is the disqualifying class.

Measured on the real corpus (flag off, booted): `e:unit_hq9b:based-at:site_rawalpindi` is **`insufficient`**,
carrying a Known Gap (`what_missing='imagery_confirmation'`, ceiling `confirmable`). So the flagship's older
position is exactly the case in question — we never established the unit was at Rawalpindi.

### Ruling

1. **Both prohibitions hold unconditionally**, *not* conditioned on identity earned-ness. The test hand is
   right, and the reason is the vocabulary above rather than a preference. Note the two prohibitions guard
   **different** things and are therefore independent: (a) guards *identity* — is this one unit? (b) guards the
   **origin's evidential status** — did we ever establish it was there? An earned identity with an
   unestablished origin is still a relocation whose premise was never confirmed.
2. **The implementer's objection is answered, not overruled.** Retirement is expressed by **`superseded_by`**
   (`schemas/view.py:149`), which is independent of the status label — so the beat does not need
   `insufficient → stale` to read correctly. Rawalpindi is retired because it is superseded; it is
   *not confirmed* because nobody confirmed it. Both facts survive, which is the honest outcome.
3. **Both live behind the flag**, like everything else in S2. Flag **off** ⇒ existing behaviour, so flag-off
   byte-identity is preserved (this was the implementer's real constraint, and it is satisfied by the flag
   boundary rather than by narrowing the rule). Flag **on** ⇒ both prohibitions apply.

**Why this was worth the round trip.** The implementer's narrowing was a reasonable reading of D-13.14 and it
was driven by real corpus evidence, not laziness. What broke the tie was neither doc nor intuition but the
*shipped definition of the label* — which is why "explore the code, not the docs" is a working principle. The
remaining two failures (the flag-gated glob, and the queue-pop on the sub-confirmed path) are ordinary
follow-through on rulings already made.
