# DEFAULT-ON — calibration ledger (integration of `defaulton/rk-test2`)

Companion to `DEFAULTON-calibration-and-data-refresh.md` (the implementer's ledger, which owns the
SINO-GALAXY alias item). This file records the expectations left **red-but-declared** after merging the
surface-anchored spec, and why each one is xfail(strict) rather than fixed or edited away.

Suite at time of writing: **1518 passed / 7 skipped / 13 xfailed**, working tree clean.
Both graded surfaces are **byte-identical** to the pre-integration tree (digests below), so nothing here is
a data-staleness artefact — every item is a live design statement.

| surface | nodes | edges | events | gaps | claims | digest |
|---|---|---|---|---|---|---|
| booted (declared holdback) | 183 | 111 | 66 | 37 | 449 | `79db6401bd35…` |
| full scenario (withhold nothing) | 196 | 123 | 71 | 45 | 489 | `7c3d9096d46e…` |

Determinism: identical digests across `PYTHONHASHSEED=1 / 97 / 12345` in three separate processes.

---

## Item 1 — the `possible` watch-list reaches no surface (5 xfail(strict) entries, one root cause)

**Tests**
- `test_defaulton_refusal_on_the_analyst_surface_spec.py::test_a_withheld_merge_appears_on_the_rendered_view[name-alone]`
- `…::test_the_rendered_reason_names_the_ground_that_actually_caused_this_refusal[name-alone]`
- `…::test_no_two_refusal_grounds_render_the_same_words`
- `…::test_an_open_identity_question_is_actionable_through_the_hitl_merge_endpoint[name-alone]`
- (the fifth is Item 2 below — a different ground, deliberately given its own reason string)

**The property is correct and is NOT satisfied today.** A name-capped pair is retained on the `possible`
watch-list *with its reason* and nothing about it is rendered on any surface: no `same-as` edge, no wall, no
Known Gap. `Partition.candidate_reasons` holds 349 entries the analyst cannot reach. The register's rule — *a
cap may withhold ATTENTION, not the RECORD* — is therefore only half-honoured.

**Why it is held open rather than closed.** Both directions were measured on the real booted corpus:

- Closing it the way the spec asks (an element per pair) puts **331 of the 355** retained pairs onto the
  wire, and all 331 render the **same single sentence** — roughly 660 identically-worded Known Gaps spread
  over 183 nodes, against the 14 candidate proposals and 34 walls that are real findings. That is this same
  file's mirror test (`test_an_earned_merge_carries_no_refusal_record_on_the_rendered_view`) failing in
  spirit: a reason on every pair is as useless as a reason on none.
- Leaving it silent also has a **measured, non-hypothetical** cost. Two `component` mentions with
  near-identical names agreeing on `component_class` + `radar_band` score 0.45, correctly decline to fuse
  (`discriminator` 0.0 — the taxonomic fix working exactly as intended), and then reach the analyst with no
  edge, no gap and no reason. A pair a human would plainly want to see is invisible.

**The honest close is neither.** It is to expose the watch-list as **its own channel** — a list the analyst
can open, off the graph — so the record exists without 331 edges competing with the findings. That is a new
surface, deliberately not started at this stage of the project, so it is filed rather than faked.

**What must not happen:** editing the spec to assert less. The property it states is the right one, which is
why the marker is `strict=True` — the day the channel lands these turn green and the marker must be removed.

## Item 2 — a pair capped at `possible` is visible but not adjudicable inline

**Test:** `…::test_an_open_identity_question_is_actionable_through_the_hitl_merge_endpoint[co-location-capped-at-possible]`

Ceiling `possible` withholds the **queue place** by its own definition, and `POST /hitl/merge` resolves its
subject only through a drawn candidate `same-as` edge — i.e. through a queue item. Demanding a merge handle
for a pair an operator explicitly capped at `possible` asks the system to contradict the dial just set.

The **visibility** half of this ground is now genuinely closed by this integration: the co-location rail was
added to `CEILINGS_THAT_MUST_ESCALATE`, so the pair escalates as a named per-endpoint Known Gap carrying the
cap's own words. That is the half the register requires. Adjudicability deliberately is not closed. Kept as a
standing xfail(strict) rather than deleted because "an open question the analyst can see but cannot act on"
is a real limit that deserves to stay visible; closing it means letting an analyst adjudicate an *arbitrary*
pair, not drawing a queue item the ceiling refused.

---

## Not calibration — five defects fixed in this integration (recorded so the numbers are attributable)

1. **`POST /hitl/merge` reject → 500.** `aliases.py` stored a learned do-not-merge as `frozenset((normA,
   normB))`; when two mentions normalise to one name that is a **one-element** set, and
   `cluster.learned_distinct_eid_pairs` unpacked it into two targets → `ValueError`. Its guard
   (`len(names) != len({*names})`) could never fire because `sorted()` of a set is already de-duplicated. So
   the only verdict the system accepted on two identically-named co-located batteries was the one that
   **fuses** them. Fixed by recording same-name rejections against **entity ids** (`AliasIndex.distinct_eids`)
   — the only key that distinguishes the two mentions — and by taking arity from the unpack. Verified
   end-to-end: reject → 200, pair does not fuse on replay, wall drawn on `GET /view`, ground truthfully reads
   "an ANALYST adjudicated these apart".
2. **`colocation_ceiling` did not escalate.** Added to `CEILINGS_THAT_MUST_ESCALATE`, with the rail threaded
   through `fusion_blocked` as data rather than sniffed out of its own prose. Inert on the shipped config
   (`colocation_ceiling: probable`).
3. **The provenance drawer cited nothing on a coref-licensed proposal.** `identity_claim_ids` deliberately
   excludes coreference to keep the `source_asserted` bar honest, and its only consumer is the edge's
   `claim_ids` — a **citation** channel, not a score. A raise-only `NAME_VARIANT` proposal, whose entire
   product is the referral, therefore reached the analyst with an empty drawer. Split into
   `licensing_claim_ids` (citation, includes coref) vs `identity_claim_ids` (unchanged, mirrors the score).
4. **The SPA read the rationale nowhere.** `attrs.reason` was rendered into `GET /view` and no non-test
   source read it; the merge card was built from `merge_confidence` + the signal breakdown, which say how
   *strong* the resemblance is and never *why the system refused it*. Added `identityReason()` and a "Why
   this is still a question" block on the merge card.
5. **G6 regression introduced and closed in-session:** the arity literal `2` tripped the no-magic-numbers
   gate; replaced with the file's own `try: a, b = … / except ValueError` idiom.

All five are byte-inert on both graded surfaces: they require a decision-log entry, a non-shipped config
value, a coref-licensed candidate, or the SPA, none of which the frozen keyless boot exercises.
