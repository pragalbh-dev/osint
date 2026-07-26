# DEFAULT-ON — calibration ledger (integration of `defaulton/rk-test2`)

Companion to `DEFAULTON-calibration-and-data-refresh.md` (the implementer's ledger, which owns the
SINO-GALAXY alias item). This file records the expectations left **red-but-declared** after merging the
surface-anchored spec, and why each one is xfail(strict) rather than fixed or edited away.

Suite at time of writing (2026-07-24): **1518 passed / 7 skipped / 13 xfailed**, working tree clean.
Both graded surfaces are **byte-identical** to the pre-integration tree (digests below), so nothing here is
a data-staleness artefact — every item is a live design statement.

**Updated 2026-07-26** by the write-path pass (blockers A–J). Item 1's original text was FALSE and is
corrected in place below; items 5 and 6 are new declared-red entries. See the header of item 1 first.

| surface | nodes | edges | events | gaps | claims | digest |
|---|---|---|---|---|---|---|
| booted (declared holdback) | 183 | 111 | 66 | 37 | 449 | `79db6401bd35…` |
| full scenario (withhold nothing) | 196 | 123 | 71 | 45 | 489 | `7c3d9096d46e…` |

Determinism: identical digests across `PYTHONHASHSEED=1 / 97 / 12345` in three separate processes.

---

## Item 1 — ~~the `possible` watch-list reaches no surface~~ **CORRECTED 2026-07-26 — the old text was FALSE**

> **This entry as originally written was measurably wrong, and that is the most serious thing in this
> file.** It asserted that the `possible` watch-list "reaches no surface" and that
> `Partition.candidate_reasons` "holds 349 entries the analyst cannot reach". `GET /coverage` shipped at the
> time and returned `withheld[]` with **331 of the 355** retained pairs, each carrying both endpoints, the
> identity confidence and the full reason text. A false claim inside a green artifact is this project's
> worst failure mode: it switches off the next reader's scepticism, which is the one thing a calibration
> ledger exists to keep switched on. The corrected statement follows; the original is struck rather than
> deleted so the correction is auditable.

**What was actually true, and what is true now.** The channel existed and was incomplete. `withheld` was
built only for pairs carrying a *recorded* reason, and a reason is recorded when some mechanism withheld the
pair — a cap, a wall, a raise. A pair that simply scored into `[possible_floor, hitl_low)` on its own
evidence had nothing to record, so **24 of 355 reached no surface anywhere**. That filter is closed: such a
pair now carries a ground derived from its own confidence against the configured bar ("reached the review
band on its own evidence and stopped short of the bar: identity confidence 0.28 of the 0.45 needed…"), and
a pair *below* the retention floor — retained because something withheld it and recorded nothing — says
exactly that instead. `GET /coverage` now returns **355 of 355**, none with an empty reason.

**The residual gap, stated honestly.** Two things, both real:

1. the watch-list does not reach `GET /view`. That is deliberate and is the trade the rest of this item
   describes: an element per pair puts 355 near-identical sentences on the wire against 14 candidate
   proposals and 34 walls that are real findings.
2. **the SPA never calls `/coverage`.** Nothing under `frontend/src` fetches it, so the channel is on the
   wire and reaches no human inside the app. Closing that means a watch-list panel — a new surface,
   deliberately not started at this stage.

The xfail reasons in `test_defaulton_refusal_on_the_analyst_surface_spec.py` have been rewritten to say
this. They remain `strict=True`: the day the panel lands they turn green and the markers must be removed.

### The original entry (struck, kept for audit)

## Item 1 (original text) — the `possible` watch-list reaches no surface (5 xfail(strict) entries, one root cause)

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

## Item 5 — `expected_view.json` predates `coverage_statement` / `also_raised_as` (2 xfail(strict))

**Tests:** `tests/gates/test_g2_determinism.py::test_matches_committed_golden_file` ·
`tests/view/test_rebuild.py::test_golden_view_matches_expected_file`

Every Known Gap now carries a derived `coverage_statement` (and, where several raw pairs restated one
finding about one node, an `also_raised_as` list of the collapsed ids). The committed golden differs from
the rebuilt view by exactly those two fields and by nothing else. Regenerating a golden so it matches new
code is how a determinism gate stops being one, so the fixture stands and the two comparisons are declared
red. G2's actual property is untouched and still enforced by its two siblings: two in-process rebuilds are
byte-identical, and the output is identical across three `PYTHONHASHSEED` values in separate processes.

## Item 6 — a supersede fixture with no evidential weight (1 xfail(strict))

**Test:** `tests/view/test_layer_instance_key.py::test_a_well_evidenced_retirement_still_reads_stale`

F5 tightened `stale`. "We knew this and the world has moved on" is a claim about the **past**, so the label
is now conditioned on the assertion having reached the **confirmed magnitude**; a mid-band assertion that
was only ever an open question is not history, and relabelling it `stale` on supersession told an analyst it
had been established when it never was.

This fixture's older basing carries `assertion_confidence` **0.0** (no source registry, so per-claim
credibility is 0) under a config whose `probable` floor is **0.0** — "assessable" in the sufficiency sense
the test checks, and carrying no evidential weight whatever. It is the purest instance of what F5 forbids,
so it now reads `probable` with `superseded-never-established` in its gate vector. The retirement is still
visible to the analyst — through `superseded_by` and the `superseded` integrity flag, which are on the view
schema and read by the SPA — it is simply no longer called history. (The gate-vector marker itself reaches
no surface; see item 7.) The property the test *means* is enforced on fixtures that
carry real credibility (`test_defaulton_fabrication_path_spec.py`, `test_supersede.py`), which stay green.
Giving this fixture weight is a data change, so it is declared rather than made.

**What F5 deliberately did NOT close, and why it is stated rather than silent.** An assertion that reached
the confirmed *magnitude* on a **single** independent look still reads `stale` when superseded. Tightening
to the full confirmed bar (magnitude **and** `min_independent_groups`) would strip `stale` from exactly the
shape of this project's flagship relocation beat — whose whole point is that a retired position reads as
history rather than as an open question — across eight behavioural specs including the one named "the
flagship shape". Rather than flip that quietly, the shortfall is **recorded**: such an assertion carries
`superseded-single-look` in its gate vector, so it is on the record that the retirement rests on one source
and that a second independent look is the next collection move. A stated partial close — and see item 7 for
the second, sharper half of what it does not close.

## Item 7 — `gate_vector` is computed and reaches NO analyst surface (not a new defect; a corrected claim)

**Found by the verifier of the DEFAULT-ON pass, confirmed independently at final triage.** `gate_vector` is
produced in `backend/chanakya/credibility/status.py`, declared on `StatusOut` in `backend/chanakya/schemas/
stage_io.py`, and consumed by **exactly one** thing in the repository: a unit test reading the stage output
directly (`backend/tests/credibility/test_freshness_class_defaults.py:90`). It is **not** on `NodeView` or
`EdgeView`, not in `GraphView`, not on any API response, and nothing under `frontend/src` mentions it.

**Why it is in the calibration ledger.** Item 6 above and three strings in the tree — `status.py`'s module
docstring (twice, including "for the provenance drawer"), the inline note beside the `established` test, and
the `xfail(strict)` reason on `test_a_well_evidenced_retirement_still_reads_stale` — asserted that
`superseded-single-look` / `superseded-never-established` let *an analyst see* how thinly a retirement is
evidenced. **They cannot.** All four strings are corrected in place at final triage; no behaviour changed.

**This is PRE-EXISTING and NOT a regression.** Every older marker (`capped-at-probable`,
`single-independent-look`, `below-probable-floor`, `aging-not-fresh`) is equally invisible, and has been for
as long as the field has existed. It is also **moot on both graded surfaces today**: zero elements on the
keyless boot (183/111) and zero on the full-corpus boot (196/123) exercise the supersede path at all.

**What IS visible, verified:** a retired edge carries `superseded_by` (`schemas/view.py:149`) and
`integrity_flags: ['superseded']` (`schemas/view.py:52`), and the SPA reads both (`api/types.ts`,
`components/stage/MapView.tsx`). So *that* an assertion was retired reaches the analyst; *how thinly the
retirement is evidenced* does not.

**Not closed, deliberately.** Putting the gate vector on the view schema is a new analyst-facing surface, and
the endgame rule is "don't start new capability" — so it is filed here rather than started. It is worth
noticing that this is the **same failure shape** as the blockers this pass just fixed (a computed judgement
that never reaches the human), which is precisely why it is written down rather than left in a docstring.

**Numbering note.** This ledger runs 1, 2, 5, 6, 7 — items **3 and 4 do not exist**. Two candidate entries
were drafted during the pass and resolved as real fixes rather than calibration items before the file was
written, and the numbers were not reused so that nothing already cited by a marker string would shift. A
reader counting entries against the 16 `xfail(strict)` markers should not go looking for the missing two.

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
