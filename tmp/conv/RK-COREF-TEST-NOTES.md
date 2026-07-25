# RK-COREF (S3) — independent test-author notes

Branch `s3/rk-test`, based on `design/resolution-redesign`. **Written from the specification only** — the
implementation branch (`s3/rk-impl`), its worktree, `RK-COREF-IMPL-NOTES.md` and the data hand's branch were
never read.

## What is here

| File | Tests | Covers |
|---|---|---|
| `backend/tests/_rk_coref.py` | — | the toolkit: abstract fixtures + **config discovery** |
| `backend/tests/resolve/test_rk_coref_autobind.py` | 34 | D-13.17 · C5 · C9 · C10 · **M1** · **M2** · the anaphor gate |
| `backend/tests/resolve/test_rk_coref_decline.py` | 7 | D-13.18 · **C3** (attribute *and* relationship) |
| `backend/tests/resolve/test_rk_coref_ladder.py` | 21 | D-13.10 · D-13.20 · C7 · the Phase-1 name verdict |
| `backend/tests/resolve/test_rk_coref_time_role.py` | 10 | **C6** (four values) · **M3** · the `places.augment` ordering |
| `backend/tests/resolve/test_rk_coref_plumbing.py` | 13 | both switches · the referent mint · the quote · the contrast lane · earned merges |
| `backend/tests/gates/test_g16_colocation_cap.py` | 9 | **G16** — C2's three absences |
| `backend/tests/gates/test_g18_relationship_wall.py` | 13 | **G18** — C1 amended, the channel, C11 |
| `backend/tests/gates/test_g19_cross_namespace_non_fusion.py` | 11 | **G19** — both phases + the alias-reflexivity hole |

**108 new tests: 74 fail against current code, 34 pass.** Suite total `1219 passed, 74 failed, 6 skipped,
2 xfailed` — the pre-existing suite is untouched (baseline in this worktree measured **1185 passed, 6 skipped,
2 xfailed**; note the brief's 1184/7 differs by one skip↔pass, before any of my files existed).

Run: `cd backend && CHANAKYA_ROOT=<worktree> .venv/bin/python -m pytest tests/resolve/test_rk_coref_*.py
tests/gates/test_g1[689]*.py`. `ruff check tests/` is clean.

## Method (three rules, each from a past failure)

1. **Read config, never hand-copy it.** `_rk_coref.bundle()` builds every fixture over the **shipped
   `resolution` block wholesale** (plus the shipped ontology and gazetteer), and the supersede floor comes
   from `rk.SUPERSEDE_FLOOR`, which reads `credibility.yaml`. Where the spec does not fix a name,
   `keys_matching()` / `accessors_matching()` / `time_role_of()` **search** for it and the failure message
   prints what was searched. Nothing in these files re-types a knob.
2. **Every prohibition has a mirror.** All 34 currently-passing tests are mirrors, non-vacuity controls or
   regression guards; several fixtures assert their own premise first (e.g. the decline fixture proves the
   conflict really is hidden from `attrs`, the G16 control proves a relocation *is* drawable).
3. **A three-way mechanism states its discriminating input in the fixture.** `_stated_conflict(iso_b=…,
   classes=…)`, `_branch_pair(value_b)`, `_grouping(second_designator)`, `_relocation`-style parameters — no
   default silently routes a mirror into the wrong branch.

---

## Per test: what it asserts, the spec line, and whether it fails now

`✗` = fails against current code (the proof of work). `✓` = passes now: a mirror, a control, or a regression
guard — each one names, in its own failure message, the over-correction it exists to catch.

### `test_rk_coref_autobind.py` — D-13.17 · C5 · C9 · C10 · M1 · M2 · the anaphor gate

| | test | asserts | spec line |
|---|---|---|---|
|✗|`a_low_grade_in_document_alias_does_not_bind`|a grade-E in-document alias must not fuse|"each behind **both** a deterministic gate **and** a source-grade floor … it merges at hardcoded `1.0` and **bypasses banding entirely**, so no cap restrains it"|
|✓|`a_low_grade_bind_still_reaches_the_analyst`|the below-floor bind is queued, not deleted|"Demotion, not silent deletion, is the point — the evidence still reaches a human"|
|✓|`the_same_sentence_from_a_good_source_does_bind`|a grade-A parenthetical *does* fuse|"`EXPLICIT_EQUIVALENCE` \| **authoritative**"; "D-13.9 says the opposite in terms: confirmed identity is reached by a **graded** path"|
|✗|`a_quote_..._without_an_equivalence_marker_does_not_bind`|co-occurrence is not equivalence|"quote contains a **configured equivalence marker** (a parenthetical wrapping one form, or a term from a config list)"|
|✗|`a_quote_that_does_not_name_the_member_does_not_bind`|the span must name both members|"quote contains **both** members' surface forms"|
|✓|`the_fixture_reads_the_shipped_mark_vs_word_threshold`|the M1 fixture is derived from `containment_min_descriptor_len`|M1: "Reuse the shipped knob; do **not** introduce a second threshold for the same idea (G6)"|
|✗|`a_mark_only_difference_is_not_a_licensed_equivalence`|`TX-5` vs `TX-5/B` must go raise-only although the sentence reads like an alias|M1: "if the longer surface form differs from the shorter only by a **mark** … the equivalence is **not licensed**, regardless of how the sentence is phrased"|
|✓|`a_word_extension_still_licenses_the_equivalence`|`RX-9` vs `RX-9 engagement radar` still binds|M1's mirror: "a longer form that adds a real **word** … *is* the same thing described more fully and must still license"|
|✓|`two_spans_from_one_document_license_the_bind`|a two-field equivalence licenses|M2: "licensing evidence is a set of verbatim spans from the same document"|
|✗|`spans_from_two_different_documents_do_not_license`|spans must share a document (both entities *are* attested in d1, so C9 cannot be what refuses it)|M2: "from the **same** document"|
|✗|`multiple_spans_do_not_relax_the_grade_floor`|span count is not evidence quality|M2: "**What does not change:** the grade floor … Multiple spans make the evidence *findable*, not *stronger*"|
|✗|`multiple_spans_do_not_relax_the_mark_test`|M1 and M2 compose|M2: "the mark-vs-word conjunct (M1) … still appl[ies]"|
|✗|`every_span_in_the_set_must_occur_verbatim`|producer-level differential: all-verbatim accepted, a fabricated span rejected|M2: "Each span must still occur verbatim … **any reader can re-derive the bind**"|
|✗|`a_cluster_binds_over_its_passing_link_and_not_its_failing_one`|partial bind: good link fuses, bad link becomes a candidate|C5: "the cluster binds only over links that pass; failing links become injected Tier-1 candidate pairs"|
|✗|`name_variant_never_binds_even_when_configured`|the prohibition binds the code, not the config|"`NAME_VARIANT` is **raise-only, permanently**" — "'authoritative NAME_VARIANT' *is* the exact-normalized-name auto-merge lane that D-13.1 exists to delete"|
|✓|`the_shipped_config_never_opts_name_variant_in`|the same at the config surface|as above|
|✗|`a_second_type_compatible_mention_fails_the_anaphor_gate`|two declared antecedents ⇒ no bind|"require a named, declared, ontology-typed antecedent, **exactly one type-compatible mention**"|
|✗|`an_unknown_typed_second_mention_also_fails_the_gate`|an under-declared second endpoint also fails it|"`unknown`-typed endpoints **COUNT as compatible** (so any second undeclared endpoint fails the gate)" — "under-extraction makes the gate PASS … *anti-correlated with safety*"|
|✗|`an_anaphor_with_no_named_antecedent_never_binds`|two elliptical references are not one entity|"require a **named, declared, ontology-typed** antecedent"|
|✓|`the_anaphor_category_and_the_shipped_config_agree`|config ⇔ behaviour, both directions|"**If the positive gate is not built, `UNAMBIGUOUS_ANAPHOR` reverts to raise-only.**" / "the gate *is* the decision"|
|✗|`a_bind_never_instantiates_over_another_documents_homonym`|no global name expansion|C9: "may only instantiate over entity ids **attested in the contributing document**"|
|✗|`the_doc_id_carrier_exists`|`Entity` carries the contributing documents, populated from `doc_refs()`|C9/(b): "`Entity.doc_ids: frozenset[str]` … (a) must not ship without it"; **not** `source_ids` ("the *publisher*"), **not** a parsed claim id|
|✗|`a_bare_single_member_instance_does_not_license_a_relocation`|one low-grade doc's unco-referenced mentions must not fuse|C10: "a bare single-member instance never licenses one"|
|✗/✓|`a_relocation_needs_an_authoritative_co_reference_that_clears_the_floor[lo/hi]`|the same co-referring document binds only above the floor (`lo` ✗, `hi` ✓)|C10: "only when that source authoritatively co-refers its own mentions **and** clears the authoritative-bind grade floor"|

### `test_rk_coref_decline.py` — D-13.18 / C3

| | test | asserts | spec line |
|---|---|---|---|
|✓|`the_fixture_hides_its_conflict_from_the_scalar_attrs`|non-vacuity: `attrs` shows `8`, `attr_history` holds `12`|"**The check must read `attr_history`, not `attrs`** — first-claim-wins scalar storage makes the conflict invisible otherwise"|
|✗|`a_conflicting_grouping_declines`|the bind does not stand|"An intra-referent critical-discriminator conflict makes the rebuild **decline** the grouping — de-grouping to claim-atom granularity"|
|✗|`a_declined_grouping_is_raised_not_dropped`|not fused **and** surfaced|"…and raising for an analyst"|
|✓|`a_consistent_grouping_still_binds`|a restated value is corroboration, not conflict|the same mechanism, negated input — a decline must not fire on "any member with more than one claim"|
|✗|`a_grouping_whose_relationships_conflict_declines`|relationship conflicts decline too|C3: "the same overlapping-time conflict test G18 uses, under C1's `site_type` rule"|
|✓✓|`a_non_conflicting_relationship_pair_still_binds[…]`|later time, and differing class, still bind|C1: "A differing `site_type` is NOT a conflict"|

### `test_rk_coref_ladder.py` — D-13.10 · D-13.20 · C7

| | test | asserts | spec line |
|---|---|---|---|
|✗ ×4|`an_identical_name_alone_never_fuses_at_any_type[variant/unit/basing_site/manufacturer]`|the cap binds the **bootstrap**|"**name is a verdict in Phase 1 at every type**, and the caps exist only in Phase 2. R1.2/R3.1/R3.2 must bind the **bootstrap disjunction**"|
|✗ ×4|`a_name_alone_pair_still_reaches_the_watch_list[…]`|capped ⇒ `possible`, not dropped|D-13.10: "capped at *possible*"|
|✓|`a_design_pair_collapses_on_the_name_plus_one_more_signal`|design collapses readily|"design collapses readily but *never on name alone*"; rk-17: "designs never collapse"|
|✗|`an_instance_pair_is_not_confirmed_by_the_name_plus_one_more_signal`|instance fully earned|"instance fully earned"; D-13.14: "confirming a formation needs a unit-level discriminator"|
|✗|`the_merge_breakdown_reports_name_and_discriminator_separately`|two signals, not one fused `max`|"**Without it, D-13.10 cannot function at all**"|
|✗|`the_two_signals_are_weighted_in_config_not_in_code`|declared weights|G6: "any discriminator-priority weights live in `config/`, never as code literals"|
|✓|`a_shared_bare_designation_never_confirms`|one designator string never confirms|"**A shared designation is NOT a unique identifier**"|
|✗|`the_composite_key_declaration_exists_and_is_composite`|`hard_id_fields.unique` exists and holds AND-keys incl. `(service_branch, designator)`|M3: "**The composite identifier has no declaration site in config at all**"|
|✗|`a_shared_composite_key_does_confirm`|the composite is **consumed** (no shared neighbours, dissimilar names)|"composite unique id … lifts all caps"; M3: "exist **and are consumed**"|
|✗|`a_differing_designation_is_a_hard_and_visible_veto`|the 8th ≠ the 12th, visibly|"differing designation (veto)"|
|✓|`the_existing_bill_of_lading_veto_still_fires`|regression|"**Preserve that asymmetry; do not 'fix' it.**"|
|✗|`the_operator_slot_is_declared_critical`|`unit.service_branch` promoted|"**S3 owns** the per-instance-type critical-discriminator declaration (operator/branch critical)"|
|✗|`a_genuinely_different_branch_walls`|PAF ≠ Pakistan Army|D-13.20: "operator / branch … conflict ⇒ hard veto, **gated on normalization**"|
|✓|`a_normalizable_branch_variant_does_not_wall`|PAF ≡ Pakistan Air Force still fuses|"a critical veto compares values **exactly** … so walling them SHATTERS legitimate merges" — **also pins the ordering**: normalization before namespace derivation|
|✗|`an_unnormalizable_critical_value_neither_walls_nor_fuses`|third state + named gap|C7: "**no wall AND no fusion** + a named gap. **A gap must bind the fusion path, not merely annotate it**"|

### `test_rk_coref_time_role.py` — C6 · M3 · lever 2

| | test | asserts | spec line |
|---|---|---|---|
|✗|`every_attribute_role_declares_a_legal_time_role`|four-value vocabulary|"replace the boolean with a declared `time_role`, four values"|
|✗|`the_legacy_perishable_key_is_gone_from_the_shipped_config`|migrated|"**No backward compatibility** … no migration shim outlives its stage"|
|✗|`a_bare_perishable_declaration_fails_loudly`|a legacy key raises|"a bare `perishable:` key becomes a **loud validation error**"|
|✗|`the_two_new_roles_are_actually_used`|`constitutive` and `identifying` appear|"the missing rung C6 was created to supply"|
|✗|`the_two_new_roles_are_declared_on_the_types_that_need_them`|on the presence type and the place types specifically|M3: "no declaration site **for the types that need them**"|
|✗|`geography_is_declared_per_type_not_once`|one attribute, different roles per citizen|C6: "declared **per (type, attribute)**"|
|✗|`two_co_located_presences_of_one_design_confirm`|`constitutive` lets a presence confirm|"`constitutive` is what lets a **presence** confirm at all"|
|✓|`two_mentions_of_one_place_confirm_on_their_coordinate`|`identifying` lets a place confirm|"`identifying` … **satisfies the non-perishable requirement for a confirm**"|
|✓|`perishable_only_agreement_still_cannot_confirm`|the D-13.9(a) cap survives the rename|"**perishable-only evidence cannot confirm**" — fails exactly if `time_role` is declared but the consumer still reads `perishable`|
|✗|`a_place_merge_is_visible_to_the_relational_signal`|two units at one resolved place share a neighbour key|"`places.augment` runs **after** `resolve_entities` … **mechanically they are not one**"|

### `test_rk_coref_plumbing.py` — the switches, the mint, the quote, the contrast lane, earned merges

| | test | asserts | spec line |
|---|---|---|---|
|✗|`the_coreference_producer_is_configured`|`credibility.coreference` present and emits `EXPLICIT_EQUIVALENCE`|"**Two independent gates must both flip**"|
|✗|`the_consumer_switch_is_flipped_and_only_for_licensed_categories`|`coref_authoritative_evidence` non-empty, no unknown categories|"With it empty, `_coref_pairs` routes **every** pair to `raise_only`"|
|✗|`the_demo_beat_is_not_a_reason_to_keep_the_switch_off`|the overruled justification|"demo preservation, forbidden as a design input … **Overruled.**"|
|✗|`make_referent_id_is_invoked_at_ingest`|a call site under `ingest/`|"`make_referent_id`, dormant since S1, invoked here"|
|✗|`emitted_coref_claims_carry_the_referent_atom`|one cluster ⇒ one referent on its claims|"the doc-local cluster … is **where the referent atom is minted**"; "the forbidden shape is minting one referent atom per *proposal*"|
|✗|`a_raise_only_bind_hands_the_analyst_its_licensing_quote`|the quote is reachable from the candidate|"**Wire it, or the mitigation that makes raise-only acceptable is fictional**"; M2: "the raise-only queue's usability … is on S3's critical path"|
|✗|`the_contrast_lane_is_declared_and_is_not_the_stated_distinct_from_rail`|`coref-distinct-from` declared|"its own `coref-distinct-from` lane — **never** the stated `distinct-from` rail"|
|✗|`a_same_document_stated_contrast_caps_the_pair_at_probable`|control fuses, contrast ⇒ `probable`, never walled|"band ceiling at `probable`, ungraded"; "a **band ceiling cannot shatter anything**"|
|✗|`the_contrast_ceiling_is_configured_as_a_band_name`|not a float|"**a band name not a float**" (a ×0.5 penalty moves 0.85 → 0.425, below `hitl_low`)|
|✓|`absence_of_contrast_is_neutral`|silence is not a prior either way|"Absence of contrast is **neutral**"|
|✓|`a_contrast_never_leaks_onto_a_cross_document_pair`|doc-scoped|"scopes the contrast channel so a doc-local contrast cannot leak onto cross-doc pairs"|
|✗|`every_fused_pair_names_a_signal_other_than_the_name`|**invariant, not a count**|"**Fragmentation resolves by earned merges, with no threshold loosened**" — a count target is what pressures a floor down|
|✓|`residual_fragmentation_is_reported_rather_than_hidden`|the coverage summary reports the tail|"Residual fragmentation reports as a `/coverage` gap"|

### `test_g16_colocation_cap.py` — C2's three absences

| | test | asserts | spec line |
|---|---|---|---|
|✗|`co_location_never_confirms_a_formation_merge`|(i) no confirmed formation merge|"Two instances sharing only design+site+operator cannot reach `confirmed` formation-merge without a unit-level discriminator"|
|✗|`co_location_still_reaches_the_analyst`|sub-confirmed, not dropped|D8: "**not fused; queued and reported**"|
|✓|`a_unit_level_discriminator_still_confirms`|the cap is a cap, not a ban|"confirming a formation needs a unit-level discriminator"|
|✗|`a_presence_level_merge_in_the_same_case_is_expected`|the presence pair *does* merge|C2: "A presence-level merge in the same case is *expected* and must not fail the gate"|
|✗|`both_formation_nodes_survive_the_rebuild`|(ii) node count preserved|C2 (ii)|
|✓|`the_control_fixture_draws_no_relocation_and_raises_a_real_gap`|non-vacuity for all three absences|— |
|✗|`a_co_location_over_merge_draws_no_relocation`|(iii) no drawn relocation|"a **fabricated movement assessment with the human removed** — the non-negotiable breached structurally"|
|✓|`the_retired_edges_known_gap_is_not_deleted`|no Known-Gap deletion (guards S2's ruling)|C2: "**no Known-Gap deletion**"|
|✓|`an_honest_insufficient_is_not_flipped_to_stale`|no `insufficient → stale`|"An assertion that was never established cannot go stale; there is nothing to age"|

### `test_g18_relationship_wall.py` — C1 amended · the channel · C11

| | test | asserts | spec line |
|---|---|---|---|
|✗|`a_stated_conflict_at_overlapping_times_walls_the_merge`|the wall fires|"two units at different sites at overlapping times are different units"|
|✗|`the_wall_is_the_transitive_visible_channel_not_a_pairwise_consultation`|analyst-visible reason|"**G18 must name the wall channel and assert an analyst-visible reason**"|
|✗|`the_wall_holds_transitively_through_a_bridge_mention`|transitivity|"built the geo-veto way it would be non-transitive *and* invisible while the gate passed"|
|✗|`no_relational_score_can_out_weigh_the_wall`|hard, not a penalty|"never overridable by a relational score"|
|✓|`a_later_placement_is_a_relocation_not_a_conflict`|non-overlapping ⇒ no wall|C1; and a wall here would delete the flagship|
|✓|`a_differing_site_class_is_not_a_conflict`|garrison + forward site|C1: "A differing `site_type` is NOT a conflict"|
|✗|`an_unmappable_site_class_neither_walls_nor_fuses`|third state + named reason|L1 rule 3: "no de-confliction, no fusion, and a **named gap**"|
|✗|`a_partial_classification_does_not_silently_de_conflict_the_subject`|per-`(subject, predicate)`|"**separation *is* de-confliction, so a partial tag is worse than none**"|
|✗|`operated_by_is_extractor_emittable`|C11's producer|"a declared predicate with no producer makes the gate lie"|
|✗|`a_stated_operator_conflict_walls_the_merge`|the operator arm|"a **stated** `based-at`/`operated-by` conflict"|
|✓/✗|`both_arms_of_the_gate_are_exercised_on_stated_evidence[based-at/operated-by]`|the gate admits which arm is fixture-only|§5a: "a gate that cannot fail is a gate that lies"|

### `test_g19_cross_namespace_non_fusion.py` — both phases

| | test | asserts | spec line |
|---|---|---|---|
|✗|`alias_equivalence_is_not_reflexive`|`equivalent(x, x)` is False for a tabled name|§4: "reflexive where its own docstring promises a real alias link, so the namespace-gated exact-name branch is never reached"|
|✓|`a_real_alias_link_is_still_equivalent`|FD-2000 ≡ HQ-9/P survives|the mirror of the fix|
|✗|`the_alias_branch_cannot_fuse_across_namespaces_in_phase_one`|Phase-1 cross-operator|"never across operators within the instance layer"|
|✗|`the_alias_branch_cannot_fuse_across_types_in_phase_one`|Phase-1 cross-**type**|§4: "making cross-operator **and cross-type** fusion reachable in **Phase 1**"|
|✓|`an_exact_name_match_inside_one_namespace_still_bootstraps`|the ordinary bootstrap survives|the mirror|
|✗|`the_phase_two_fixpoint_cannot_fuse_across_namespaces`|Phase-2 fixpoint, **design-layer** pair (M15)|D4: "**never the Phase-2 fuzzy fixpoint** … relational blocking emits pairs with **no namespace key**"|
|✓|`an_unstated_namespace_is_a_wildcard_not_a_conflict`|absence ≠ disagreement (design-layer control)|"an unstated namespace is a **wildcard**, not a conflict"|
|✓|`a_shared_namespace_still_fuses_in_the_fixpoint`|not a blanket wall (design-layer control)|the mirror|
|✗|`the_instance_layer_cannot_fuse_across_namespaces_either`|the instance-layer clause, over a pair G16 **permits** (shared composite id)|spine/13 §3: "never across operators **within the instance layer**"; M15: "a unit-level discriminator and therefore *legitimately* confirms under G16"|
|✓✓|`the_namespace_guard_reads_a_normalized_value[PAKISTAN/pakistan]`|normalized namespace (design-layer control)|"normalizing only at conflict time would leave namespaces split"|

---

## Spec silences — everywhere the spec did not determine an outcome

Each is a place I had to choose. Where a *name* was unfixed I searched for it and the test prints what it
searched; where an *outcome* was unfixed I chose the reading and say so here, so the implementer can dispute
the test rather than guess at it.

1. **The coref grade floor has no config key.** D-13.17 requires "a source-grade floor" and never names the
   knob. Searched: every shipped `resolution` key and every `ResolveConfig` accessor for `coref`+`grade`,
   `coref`+`floor`, `coref`+`min` — only `coref_authoritative_evidence` exists. So the floor is asserted
   **behaviourally across the grade extremes** (a grade-A source binds, a grade-E source does not), which
   pins the floor without asserting where it lives. Any floor between A and E passes.
2. **The equivalence-marker vocabulary key.** C5 says "declare the seed equivalence-marker vocabulary in
   config, verb forms included" without naming it; the tests assert behaviour (parenthetical present vs a
   bare co-occurrence sentence), never the key. **A "verb form" case is deliberately not asserted** — the
   vocabulary's contents are the implementer's to seed.
3. **M2's carrier shape for a span *set* is unspecified.** The fixture supplies the spans (a) as a list under
   the shipped `source_quote` attribute, (b) under a plural sibling `source_quotes`, and (c) as one `DocRef`
   per span on the claim; the producer-level test additionally puts them under both `licensing_quote` (list)
   and `licensing_quotes` on the raw tool payload. If the implementation picks another carrier, **this is the
   one place to reconcile** — the assertions are on outcomes, only the input shape is a guess.
4. **Whether C5's per-link gate lives producer-side or consumer-side** is not fixed. Every C5 assertion is on
   the outcome (which links fuse, which become candidates), so either placement passes.
5. **The name / discriminator signal names.** D-13.20 requires the split but not the keys; the tests accept
   any breakdown key containing `name` / `discrimin`, and require config-declared weights for both.
6. **Where C7's / L1's "named gap" lives** — a `known_gap` node, a `candidate_reason`, or `distinct_from`
   membership — is unfixed. `visible_rationale()` accepts a reason **or** a surfaced wall; the resolve-level
   tests therefore do not demand a view-level gap node. If the implementation raises a real `KnownGap`
   instead, add it to that helper.
7. **`time_role`'s key spelling** is unfixed (`time_role` / `temporal_role` / a value-only declaration);
   `time_role_of()` searches by key token first, then by any value drawn from the four-value vocabulary.
8. **The contrast ceiling knob name** is unfixed; the test searches every resolution key for `contrast` and
   only asserts that whatever it finds is **not numeric**.
9. **The value-normalization surface** (equivalence classes for `PAF` ≡ `Pakistan Air Force`) has no declared
   key. Rather than guess one, the C7 tests run on the **shipped resolution block wholesale** and assert
   behaviour, so any normalization S3 declares in that file is picked up automatically.
10. **Which attribute name carries "geography" per type** (`coordinates`? `location`?) is unfixed; the C6
    per-type test discovers it by token (`coord` / `geo`).
11. **G16's presence clause**: C2 says a presence merge "is *expected*", which I read as **must fuse**, not
    merely "is permitted". If the implementer reads it as permission only, that test is the disagreement.
12. **D-13.20's "shared designation satisfies the perishable cap"** rung is *not* asserted — it needs a
    fixture that simultaneously exercises the perishable cap and the designation rung, and the spec does not
    say which wins when they disagree. Flagged rather than guessed.
13. **C11's fallback is not asserted as an alternative.** The test asserts `operated-by` becomes
    extractor-emittable (the ruling's primary instruction) and its docstring records the declared fallback
    ("G18 must then declare in the gate itself that its `operated-by` arm is fixture-only"); the parametrised
    `both_arms_…` test is where that admission would go.
14. **"Rarity-graded name" is not asserted at all.** DECISIONS says it "has no implementation anywhere … yet
    D-13.2 and D-13.10 both rest on it. Either S3 builds it or the design stops claiming it" — but no
    observable contract is given (what does a rare name do that a common one does not?), so I could not write
    a falsifiable test. **This is the one spec item I have left uncovered**; it needs a ruling.
15. **No fragmentation count is asserted anywhere**, deliberately: the acceptance line is honoured as an
    invariant ("no fused pair rests on the name signal alone") plus the coverage-reporting test. A count
    target is the pressure that lowers a floor.
16. **C8 / D6 source-independence, the S4 name-key cut, corpus regen and F9's graded sub-confirmed relational
    weight are not asserted** — out of scope per the brief.
17. **The anaphor three-way fork** (authoritative-with-a-positive-gate vs raise-only) is resolved by a
    **config-coherence** test rather than by picking a branch: whatever the shipped config declares, the
    behaviour must match it. The three prohibition tests hold under either branch.
18. **M4 is honoured, not asserted**: G16/G18/G19 carry a docstring note that they are fixture-only on this
    corpus by measurement, so nobody later "fixes" them with a corpus-dependent assertion.

## Standing rule for S4 (ruling M15) — a control must not be restrained by another gate

**What happened here.** G19's must-fuse controls were built from `shared_neighbours` over two `unit`s — which
my own toolkit docstring calls "the co-location evidence class and nothing else". That is precisely what G16
forbids from confirming a formation merge, so **the two gates contended**: G19's control could not pass while
G16's cap held. The implementer kept the cap and escalated rather than weakening it, which was right —
"weakening G16 to make G19's control go green is the F8 trap wearing G16's clothing."

**Fixed by changing the fixture, never a cap.** The Phase-2 controls are now a **design-layer** pair (two
`variant`s sharing a manufacturer and a component): G16 governs the *instance* layer, so co-location has no
claim on them, and the design layer is also the permissive profile — which makes it the sharper place to
assert the boundary ("even where fusion is easy, it must not cross an operator"). The instance-layer clause
keeps its own case, built on M15's second option: a pair sharing a composite `(service_branch, designator)`
identifier, which G16 *legitimately* confirms, so the namespace boundary is the only thing left that can
refuse it. It asserts its own premise (`hard_id_fields.unique` declared) first, so it cannot pass vacuously
while the composite key is still missing.

**The rule to carry into S4:** *a gate's control must be built from an evidence class no **other** gate
restrains.* Otherwise two gates contend and the pressure lands on whichever cap is easier to loosen — which is
how a safety property gets traded away to make a suite green. Before writing a must-fuse mirror, ask which
other gate governs the evidence class it is built from; if any does, pick another class. Checked here against
G16 (instance-layer co-location), G18 (stated placement/operator conflicts), D-13.10's name cap, C7's critical
walls, the geo veto and the shipped `distinct_from` traps.

**This is the second time an input choice routed a mirror into the wrong branch** — S2's unstated site classes
was the first — so it belongs in the method, not in a changelog.

## Two interlocks worth knowing before you start

* **Fixing G19 without C7's normalization breaks a mirror.** `a_normalizable_branch_variant_does_not_wall`
  passes today only because the namespace gate is broken in Phase 2. Once cross-namespace fusion is blocked,
  `PAF` and `Pakistan Air Force` become two namespaces unless normalization runs **before namespace
  derivation** — which is exactly what DECISIONS requires and what that mirror pins.
* **Renaming `perishable` → `time_role` without rewiring the consumer breaks another.**
  `perishable_only_agreement_still_cannot_confirm` passes today via the boolean; it fails the moment the
  declaration moves and `attribute_perishable` still reads the old key. That is the S2 hand-copied-knob
  failure, reproduced as a tripwire.

## Verbatim failure signatures (74), current code

```
  tests/resolve/test_rk_coref_autobind.py:65: AssertionError: a grade-E source's in-document alias FUSED two manufacturers at confidence 1.0. An authoritative bind bypasses banding, so the grade floor is the only thing restraining it — and a stated `same-as` from the same source would be grade-floored AND raise-only. That inversion is what D-13.17's grade gate closes. Partition: same_as=[('m2', 'm1')]
  tests/resolve/test_rk_coref_autobind.py:126: AssertionError: a bind fused on 'Alpha Precision Machinery and APM both shipped in March' — a sentence that merely mentions both names, with no parenthetical and no equivalence marker. Co-occurrence is not a stated equivalence, and this is the lane an extractor mislabel walks straight through (D-13.17 gate clause 3).
  tests/resolve/test_rk_coref_autobind.py:144: AssertionError: 'Beta Metalworks' was fused into 'Alpha Precision Machinery' on the quote 'Alpha Precision Machinery (APM)', which names neither of its surface forms. The licensing span is the whole basis of the category; a span that does not mention the member licenses nothing.
  tests/resolve/test_rk_coref_autobind.py:190: AssertionError: 'TX-5' and 'TX-5/B' were fused at confidence 1.0 on a parenthetical. The longer form adds only the mark 'B' (below containment_min_descriptor_len=3), so the sentence distinguishes two variants of one design rather than declaring an alias — and neither the grade floor (a good source can write it) nor the D-13.18 decline (two marks often conflict on nothing) catches it. same_as=[('v_short', 'v_long')]
  tests/resolve/test_rk_coref_autobind.py:273: AssertionError: a bind was licensed by one span from d1 and one from d2. No single document stated this equivalence; assembling it across documents is a cross-document identity decision, which belongs to Tier 1 and the analyst, not to the extractor's reading of one document. same_as=[('m2', 'm1')]
  tests/resolve/test_rk_coref_autobind.py:292: AssertionError: two spans from a grade-E document bound where one span would not have. Span count is not evidence quality. same_as=[('m2', 'm1')]
  tests/resolve/test_rk_coref_autobind.py:312: AssertionError: a two-span set bound 'TX-5' to 'TX-5/B', which differ only by the mark 'B'. More spans make an equivalence easier to find, not truer. same_as=[('v_short', 'v_long')]
  tests/resolve/test_rk_coref_autobind.py:341: AssertionError: a span set whose every member occurs verbatim in the document was rejected, so the M2 form is not accepted at all and the negative below is vacuous
  tests/resolve/test_rk_coref_autobind.py:371: AssertionError: the failing link bound anyway: one member's licensing span was reused to fuse a mention it never names. That is the 'one bad link licenses the rest' half of C5.
  tests/resolve/test_rk_coref_autobind.py:401: AssertionError: NAME_VARIANT bound because the config listed it. That rebuilds the exact-normalized-name auto-merge lane on the coref predicate, immune to D-13.10's name cap — 'the one call all three positions converged on'. same_as=[('n2', 'n1')]
  tests/resolve/test_rk_coref_autobind.py:453: AssertionError: 'the export agency' was bound to one of TWO declared manufacturers in the same document. The category's own licensing condition is that there is no second mention of that type it could mean. same_as=[('m1', 'ent:manufacturer:the export agency')]
  tests/resolve/test_rk_coref_autobind.py:473: AssertionError: a second undeclared endpoint ('the supplier') did not fail the gate, so an extractor that under-declares its mentions *widens* the strongest fusion path in the system. This is the fails-open direction the positive reformulation exists to close. same_as=[('m1', 'ent:manufacturer:the export agency')]
  tests/resolve/test_rk_coref_autobind.py:495: AssertionError: two undeclared, untyped descriptions were fused into one entity by an anaphor bind. The positive gate requires a named, declared, ontology-typed antecedent — there is none here.
  tests/resolve/test_rk_coref_autobind.py:547: AssertionError: a second document's homonymous 'APM' was swept into the bind through global name expansion. C9: a document's authority extends to its own referents only — d1 said nothing whatever about d2's company. same_as=[('m2', 'm1'), ('m_other', 'm1')]
  tests/resolve/test_rk_coref_autobind.py:565: AssertionError: resolve.entities.Entity declares no document field. There is no document dimension anywhere downstream (code facts D6), so C9's scoping and (b)'s same-doc contrast have no carrier. Declared fields: ['attr_history', 'attrs', 'claim_ids', 'eid', 'etype', 'name', 'registry', 'source_ids']
  tests/resolve/test_rk_coref_autobind.py:605: AssertionError: one grade-E document's two unco-referenced mentions were fused, which makes their two sites one unit's before/after and licenses a relocation nobody stated. C10 requires the source to *authoritatively co-refer its own mentions* and clear the grade floor. same_as=[('u2', 'u1')]
  tests/resolve/test_rk_coref_autobind.py:631: AssertionError: a grade-E document that authoritatively co-refers its own two mentions bound anyway. C10 grants a source authority over its own referent — spine/13 §5 — but only above the authoritative-bind grade floor: 'a bare single-member instance never licenses one'. same_as=[('u2', 'u1')]
  tests/resolve/test_rk_coref_decline.py:82: AssertionError: the grouping stood even though one of the claim atoms it groups asserts a different designation. The referent atom is 'evidence about a grouping, never the address' — if a conflicting grouping cannot decline, S3 makes intra-document over-merge permanent, which the decision calls disqualifying. same_as=[('e2', 'e1')]
  tests/resolve/test_rk_coref_decline.py:94: AssertionError: the declined grouping left no trace: no candidate link and no analyst-visible reason. A decline is a referral, not a deletion. candidates=[] possible=[] reasons={}
  tests/resolve/test_rk_coref_decline.py:144: AssertionError: an authoritative bind fused two mentions the document's own *relationships* place at two same-class sites at the same time. The decline and the wall must share one predicate rather than drifting apart. same_as=[('e2', 'e1')]
  tests/resolve/test_rk_coref_ladder.py:57: AssertionError: two variant mentions sharing nothing but an identical name FUSED at confidence 1.0 through the Phase-1 bootstrap, bypassing the bands and the name cap entirely. That is the widest over-merge path in the substrate. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 0.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.45}
  tests/resolve/test_rk_coref_ladder.py:57: AssertionError: two unit mentions sharing nothing but an identical name FUSED at confidence 1.0 through the Phase-1 bootstrap, bypassing the bands and the name cap entirely. That is the widest over-merge path in the substrate. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 0.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.45}
  tests/resolve/test_rk_coref_ladder.py:57: AssertionError: two basing_site mentions sharing nothing but an identical name FUSED at confidence 1.0 through the Phase-1 bootstrap, bypassing the bands and the name cap entirely. That is the widest over-merge path in the substrate. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 0.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.45}
  tests/resolve/test_rk_coref_ladder.py:57: AssertionError: two manufacturer mentions sharing nothing but an identical name FUSED at confidence 1.0 through the Phase-1 bootstrap, bypassing the bands and the name cap entirely. That is the widest over-merge path in the substrate. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 0.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.45}
  tests/resolve/test_rk_coref_ladder.py:72: AssertionError: a name-alone variant pair reads 'confirmed'. D-13.10 caps name at *possible* — the watch-list link the analyst can see but is not pestered by — it does not delete the pair.
  tests/resolve/test_rk_coref_ladder.py:72: AssertionError: a name-alone unit pair reads 'confirmed'. D-13.10 caps name at *possible* — the watch-list link the analyst can see but is not pestered by — it does not delete the pair.
  tests/resolve/test_rk_coref_ladder.py:72: AssertionError: a name-alone basing_site pair reads 'confirmed'. D-13.10 caps name at *possible* — the watch-list link the analyst can see but is not pestered by — it does not delete the pair.
  tests/resolve/test_rk_coref_ladder.py:72: AssertionError: a name-alone manufacturer pair reads 'confirmed'. D-13.10 caps name at *possible* — the watch-list link the analyst can see but is not pestered by — it does not delete the pair.
  tests/resolve/test_rk_coref_ladder.py:110: AssertionError: two formation mentions were confirmed as one unit on a shared descriptor name plus a shared operator/design — every battery in the order of battle shares those. Confirming a formation needs a unit-level discriminator. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 1.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.8500000000000001}
  tests/resolve/test_rk_coref_ladder.py:138: AssertionError: the merge breakdown carries no separate name / discriminator signals — it reports ['attribute', 'relational', 'source_asserted', 'temporal_consistency', 'total']. While both live in one fused `attribute` number, 'name caps at possible' and 'one more signal clears it' cannot be expressed, so D-13.10 has nothing to act on.
  tests/resolve/test_rk_coref_ladder.py:153: AssertionError: config/resolution.yaml merge_weights declares ['attribute', 'relational', 'source_asserted', 'temporal_consistency'] — no separate name/discriminator weights. Splitting the signal in code while leaving one weight in config buries the new number in the source (gate G6).
  tests/resolve/test_rk_coref_ladder.py:192: AssertionError: config/resolution.yaml declares no `hard_id_fields.unique`, so `_shared_unique_id` is always False and the strongest rung of the ladder is unwired (code facts B6: 'the "shared unique identifier ⇒ fast path to confirmed" mechanism is not wired').
  tests/resolve/test_rk_coref_ladder.py:231: AssertionError: two mentions stating the SAME (service_branch, designator) composite were not fused, and nothing else in this fixture could have earned it. That rung 'lifts all caps' — an unconsumed declaration leaves the fast path unreachable exactly as the spike measured. status=None breakdown={}
  tests/resolve/test_rk_coref_ladder.py:255: AssertionError: the 8th and the 12th battalion were fused into one unit. A stated differing designation is the strongest wall on the ladder. same_as=[('b', 'a')]
  tests/resolve/test_rk_coref_ladder.py:311: AssertionError: unit.service_branch is declared {'role': 'supporting', 'perishable': False}. Once normalization exists, a different service branch is a different entity — that promotion is the whole reason C7 makes normalization a prerequisite.
  tests/resolve/test_rk_coref_ladder.py:323: AssertionError: a PAF unit and a Pakistan Army unit sharing designator '8' were fused — the reuse of designations across armies is precisely why the composite key exists. same_as=[('b', 'a')]
  tests/resolve/test_rk_coref_ladder.py:369: AssertionError: the pair FUSED while its critical discriminator 'P.A.F. (Northern)' could not be normalized — the gap annotated the answer instead of binding it. This is the rk-14-probe critical bug verbatim: name the gap, then assert the assessment anyway. same_as=[('b', 'a')]
  tests/resolve/test_rk_coref_plumbing.py:40: AssertionError: config/credibility.yaml declares no `coreference` block, so ingest/coref.py returns [] and Tier 0 produces nothing. Scope 1 promotes the pass from optional to REQUIRED — that is this switch.
  tests/resolve/test_rk_coref_plumbing.py:56: AssertionError: config/resolution.yaml still ships `coref_authoritative_evidence: []`, so every cluster is raise-only and D-13.17's policy is inert. 'Two independent gates must both flip.'
  tests/resolve/test_rk_coref_plumbing.py:77: AssertionError: the switch is still off and the comment still justifies it with the d10 'HT-233 (H-200)' demo beat. The policy is decided on general principle; 'the data pass owes a re-carried beat'.
  tests/resolve/test_rk_coref_plumbing.py:91: AssertionError: make_referent_id has no call site under ingest/ (all call sites: []). The referent atom is still dormant, so the doc-local cluster is not the mint grain and nothing groups the per-mention claim atoms.
  tests/resolve/test_rk_coref_plumbing.py:115: AssertionError: the emitted coref claims carry no referent atom ({None}). S1 added the field dormant precisely so S3 could mint against the cluster; without it the grouping has no address to be evidence *about*.
  tests/resolve/test_rk_coref_plumbing.py:151: AssertionError: the raise-only pair is 'confirmed' rather than a candidate — raise-only means 'a probable HITL candidate with the merge one click away'.
  tests/resolve/test_rk_coref_plumbing.py:175: AssertionError: the ontology declares no 'coref-distinct-from' edge (['based-at', 'component-of', 'contradicts', 'coref-same-as', 'corroborates', 'customs-party', 'derived-from', 'design-authority-for', 'distinct-from', 'equips', 'evidenced-by', 'exported-by', 'imported-by', 'inducted-into', 'instance-of', 'manufactures', 'observed-at', 'operated-by', 'replenishes', 'same-as', 'substitutable-by', 'supersedes', 'supplies-component', 'sustained-by']). Coref's mention shape has no spans and pass 1 collapses one name to one claim per document, so nothing downstream can re-read the syntax: the contrast is 'not derivable downstream' and needs its own lane.
  tests/resolve/test_rk_coref_plumbing.py:208: AssertionError: a document that syntactically distinguishes its two mentions still auto-merged them. same_as=[('u2', 'u1')]
  tests/resolve/test_rk_coref_plumbing.py:228: AssertionError: config/resolution.yaml declares no contrast knob (searched every resolution key for 'contrast'; keys are ['acronym_min_len', 'alias_table', 'attribute_roles', 'auto_merge_by_type', 'bands', 'blocking_keys', 'containment_min_descriptor_len', 'containment_min_short_tokens', 'coref_authoritative_evidence', 'coverage_gap_ratio', 'critical_veto_min_grade', 'distinct_from', 'entity_geo_conflict_max_km', 'high_alias_risk_types', 'identity_raise_min_weight', 'identity_source_weight_default', 'llm_candidate_gen', 'merge_weights', 'name_alone_caps_at_possible', 'orphan_block_threshold_k', 'place_allowed_precision_classes', 'place_bind_on_curated_toponym', 'place_entity_types', 'place_identity_precision_classes', 'place_min_geocode_confidence', 'place_proximity_hitl_multiplier', 'place_proximity_radius_m', 'relational_support_k', 'toponym_descriptive_markers', 'transliteration'])
  tests/resolve/test_rk_coref_plumbing.py:300: AssertionError: no stored breakdown names a `name` signal, so 'this merge rests on the name alone' is not even expressible and this invariant cannot be checked. Signals seen: ['attribute', 'relational', 'source_asserted', 'temporal_consistency', 'total']
  tests/resolve/test_rk_coref_time_role.py:41: AssertionError: these attribute_roles entries declare no legal time_role: {'component.component_class': None, 'component.radar_band': None, 'manufacturer.tier': None, 'trading_org.origin_country': None, 'unit.alert_posture': None, 'unit.service_branch': None, 'variant.family': None, 'variant.operator_branch': None, 'variant.range_class': None}. C6's four values are ('durable', 'perishable', 'constitutive', 'identifying'); a boolean cannot carry three states, which is why the closure was re-specified.
  tests/resolve/test_rk_coref_time_role.py:53: AssertionError: these entries still carry a bare `perishable:` key: ['component.component_class', 'component.radar_band', 'manufacturer.tier', 'trading_org.origin_country', 'unit.alert_posture', 'unit.service_branch', 'variant.family', 'variant.range_class']. The standing directive is that no migration shim outlives the stage that introduces it — 'a dual-form loader biases every later implementer toward the old shape'.
  tests/resolve/test_rk_coref_time_role.py:78: AssertionError: a config declaring the old boolean `perishable:` was accepted in silence. It then behaves as an *undeclared* time role — i.e. as `durable` — so a perishable attribute silently becomes durable identity support and the D-13.9(a) cap evaporates. That is worse than a crash.
  tests/resolve/test_rk_coref_time_role.py:94: AssertionError: no shipped declaration uses ['constitutive', 'identifying'] (roles in use: []). Renaming `perishable: true|false` to `time_role: perishable|durable` carries two of the four states and leaves the anchor/design layer unable to confirm anything — rk-20 and rk-17 both.
  tests/resolve/test_rk_coref_time_role.py:122: AssertionError: no attribute of the presence citizen ['contract_import_event', 'presence', 'interceptor_stockpile'] is declared `constitutive` (attribute_roles covers ['component', 'manufacturer', 'trading_org', 'unit', 'variant']). A presence *is* operator+design+site+window, so without this the presence layer can never confirm and every report of one battery becomes another presence.
  tests/resolve/test_rk_coref_time_role.py:146: AssertionError: no geography attribute is declared in attribute_roles at all, so geography has no time role on any citizen. Declared attributes: ['alert_posture', 'component_class', 'family', 'operator_branch', 'origin_country', 'radar_band', 'range_class', 'service_branch', 'tier']
  tests/resolve/test_rk_coref_time_role.py:194: AssertionError: two presences of the same design, at the same coordinate, under the same operator, in the same window did not collapse (status=probable, breakdown={'attribute': 0.6853193773483629, 'relational': 1.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.7241277509393452}). Constitutive geography is what lets a presence confirm at all; without it the presence layer fragments per report and the OOB count inflates.
  tests/resolve/test_rk_coref_time_role.py:286: AssertionError: the units' relational signal is 0.0 even though both are based at what the resolver itself decided is ONE place. The place merge lands after the entity fixpoint, so the shared anchor is invisible exactly where lever 2 claims to work.
  tests/gates/test_g16_colocation_cap.py:129: AssertionError: two formation mentions sharing a base, a design and an operator — and nothing unit-level — were CONFIRMED as one unit. That is an order-of-battle undercount by construction: every battery at a base shares exactly this evidence. same_as=[('unit_b', 'unit_a')] breakdown={'attribute': 1.0, 'relational': 1.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.8500000000000001}
  tests/gates/test_g16_colocation_cap.py:143: AssertionError: the co-located pair reads 'confirmed': it was either fused or dropped entirely, and the analyst is never asked whether these two mentions are one battery. 'Residual surfaced as a coverage item' requires the link to exist and stay sub-confirmed. candidates=[] possible=[]
  tests/gates/test_g16_colocation_cap.py:195: AssertionError: the presence-level pair did not merge on identical site + design + operator + window. C6 makes that geography *constitutive* for a presence, and C2 says the presence merge is expected — so a cap that swallowed it has over-corrected. status=probable
  tests/gates/test_g16_colocation_cap.py:212: AssertionError: the view holds ['unit_a'] — the two co-located batteries collapsed into one formation node. This is the OOB undercount G16 names, and it is invisible to every other gate.
  tests/gates/test_g16_colocation_cap.py:253: AssertionError: a relocation was drawn: ['e:site_new:supersedes:site_old', 'e:unit_a:based-at:site_old->e:unit_a:based-at:site_new']. Nobody stated that anything moved — two documents described two batteries, and the identity error turned that into a movement. `based-at` is functional and unit-keyed, so the fusion alone is enough to manufacture the before/after.
  tests/gates/test_g18_relationship_wall.py:107: AssertionError: two formation mentions stated at two different same-class sites at the same time were FUSED. The conflict is stated, not inferred, so this is not a low score to be out-weighed — D-13.8 makes it a hard wall. same_as=[('unit_b', 'unit_a')] breakdown={'attribute': 1.0, 'relational': 0.5, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.65}
  tests/gates/test_g18_relationship_wall.py:124: AssertionError: the pair was held apart with nothing an analyst can read: it is absent from `distinct_from` and carries no candidate reason. A wall consulted only inside `vetoed()` is invisible to `finalise`, to the D9 bridge alarm and to the surfaced distinct-from edge. reasons={} distinct_from=[]
  tests/gates/test_g18_relationship_wall.py:144: AssertionError: a third look-alike mention bridged the wall: unit_a and unit_b ended in one cluster via unit_c. A cannot-link that only holds pairwise is not a wall. cluster=['unit_a', 'unit_b', 'unit_c']
  tests/gates/test_g18_relationship_wall.py:162: AssertionError: a maximal shared neighbourhood carried the pair over a stated placement conflict. 'A hard wall no similarity score may cross' is the whole distinction between a wall and a penalty. breakdown={'attribute': 1.0, 'relational': 0.6, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.6900000000000001}
  tests/gates/test_g18_relationship_wall.py:208: AssertionError: the pair fused while one end's stated site class could not be mapped to the declared vocabulary. Unknown must fail safe: 'we do not know whether these are the same kind of place' is not 'they are different kinds of place, so no conflict'. same_as=[('unit_b', 'unit_a')]
  tests/gates/test_g18_relationship_wall.py:234: AssertionError: the subject's own second, unclassifiable basing made the stated conflict invisible and the pair fused. Per-edge tagging is worse than none: 'separation IS de-confliction, so a partial tag is worse than none'. same_as=[('unit_b', 'unit_a')]
  tests/gates/test_g18_relationship_wall.py:260: AssertionError: `operated-by` is declared {'name': 'operated-by', 'from': ['unit', 'presence'], 'to': 'operator', 'freshness_class': 'semi-durable'} — non-extractor, so no source can ever state one and G18's operator arm is fixture-only forever. If that is the accepted outcome it must be stated in the gate and disclosed, never discovered later.
  tests/gates/test_g18_relationship_wall.py:273: AssertionError: two mentions stated under two different operators at the same time were fused. Operator is the namespace of an order-of-battle map: 'never across operators within the instance layer'. same_as=[('unit_b', 'unit_a')]
  tests/gates/test_g18_relationship_wall.py:292: AssertionError: 'operated-by' is not extractor-emittable, so this arm of G18 can only ever fire on hand-written fixtures. That is C11's 'the gate half-lies' condition; declare it and disclose it.
  tests/gates/test_g19_cross_namespace_non_fusion.py:100: AssertionError: AliasIndex.equivalent('hq 9 p', 'hq 9 p') is True: any name inside an alias class is alias-equivalent to ITSELF, so two identically-named entities take the alias branch and never reach the exact-name branch that checks type and namespace. That is a Phase-1 bootstrap merge at confidence 1.0 across an operator boundary.
  tests/gates/test_g19_cross_namespace_non_fusion.py:134: AssertionError: two 'HQ-9/P' mentions in DIFFERENT stated namespaces (China / Pakistan) fused in the Phase-1 bootstrap. The exact-name branch is namespace-gated; the alias branch is not, and a name inside the alias table reaches the alias branch first. same_as=[('b', 'a')]
  tests/gates/test_g19_cross_namespace_non_fusion.py:147: AssertionError: a `variant` and a `unit` both named 'HQ-9/P' were fused into one node. A weapon design and a military formation are not the same entity under any evidence — T3b-A's own words: asking whether an air-defence sector is an air-defence centre 'is not triage, it is noise'. same_as=[('b', 'a')]
  tests/gates/test_g19_cross_namespace_non_fusion.py:194: AssertionError: a PLA-side and a Pakistan-side design were auto-merged by the fuzzy fixpoint on a shared manufacturer and component. This is 'the single most dangerous over-merge class for an operator-scoped OOB map' — spine/13 §3: identity is never resolved across operators. same_as=[('b', 'a')] breakdown={'attribute': 1.0, 'relational': 1.0, 'temporal_consistency': 1.0, 'source_asserted': 0.0, 'total': 0.8500000000000001}
  tests/gates/test_g19_cross_namespace_non_fusion.py:241: AssertionError: `hard_id_fields.unique` is undeclared, so the composite identifier cannot fire and this pair has no legitimate route to fusion — the assertion below would pass for the wrong reason (see the ladder suite's composite-declaration test)
```
