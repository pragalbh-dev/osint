# RK-LAYER (S2) — independent test hand: what was asserted, what fails today, where the spec is silent

**Authored from the spec alone** (`plan/01` §4 A2/A3/A4 + §5/§5a/§5a-bis + §7 RK-LAYER ·
`plan/sessions/RK-LAYER.md` · `spine/13` §3a/§5 + D-13.3/5/6/13/14 · `tmp/conv/rk-spike-verified-defects.md`
D1/D2/D12 · `tmp/conv/rk-spike-DECISIONS.md` C1/C2 · `tmp/conv/RK-LAYER-RULINGS.md` L1–L4).
The implementation branch (`s2/rk-impl`), the impl worktree, `RK-LAYER-IMPL-NOTES.md` and the data branch
(`s2/rk-data`) were **not** read. Base: `design/resolution-redesign` @ `a3d68b4`.

**Suite state.** Baseline before these tests: `1094 passed, 7 skipped, 2 xfailed`.
After: **`39 failed, 1126 passed, 7 skipped, 2 xfailed`** — 32 new passing (regression guards + mirrors +
negative controls), **39 new failing** (the S2 behaviour that does not exist yet). No pre-existing test
changed or broke. `ruff check` clean.

**Four coordinator rulings folded in (2026-07-25), after the first pass:**

1. **The baseline discrepancy is resolved — two valid surfaces exist and neither number was wrong.** The
   **booted app** (160 / 73 / 18 gaps / 450 claims, hash `22d668a3…dac3a9`) deliberately withholds
   `d18_rahwali_pass1` + `d19_rahwali_confirm` from the boot seed; the **full-scenario harness** (169 / 80 /
   71 / 20) sees everything. This suite pins the harness surface **because those two withheld documents are
   exactly the flagship relocation pair** — the booted surface is structurally blind to the supersede path S2
   changes most (items 5–7). The constant block in `test_s2_flag_off_equivalence.py` now says that, replacing
   the earlier (and wrong) "these do not reproduce here", which would have taught readers to distrust a
   working baseline — the same failure mode as the two docstrings already corrected this session.
2. **"Sub-confirmed identity" = an open `candidate` merge** — carrier confirmed. Node `status` is expressly
   *not* it (the legitimate flagship subject sits at `probable`, so gating there would delete the beat). Now
   recorded in the test's own docstring so nobody re-derives the trap.
3. **Absent and unmappable `site_type` are one condition** — both land in L1's third state. The absent-value
   test was strengthened from "no de-confliction" alone to the full third state (no de-confliction · no fusion
   · a named gap) and consequently **now fails today**, where before it passed.
4. **The flagship consequence is intended, and is now pinned** — new
   `test_the_flagship_relocation_is_held_while_its_site_classes_are_unknown`, on the real corpus with the flag
   on, labelled INTENDED so nobody later "fixes" it by loosening the vocabulary.

**Files added** (tests only; nothing under `chanakya/`, `config/`, `corpus/`, or existing fixtures touched):

| file | what it covers |
|---|---|
| `backend/tests/_rk_layer.py` | discovery helpers + the abstract fixture builder (mirrors S1's `_rk_atoms.py`) |
| `backend/tests/config/test_rk_layer_a2_layer_tags.py` | A2 layer tags on the **real shipped config**, D-13.3, the ontology additions S2 owns, L1/L2/L4 |
| `backend/tests/view/test_rk_layer_routing.py` | A4 split → materialize, A3's two citizens, count-as-sourced, stated-vs-derived basing |
| `backend/tests/view/test_rk_layer_derived_basing.py` | D-13.6 rebuild-derived `based-at`, premise citation, "deleted not relocated" |
| `backend/tests/view/test_rk_layer_supersede_identity.py` | R1.4 / the D1 tail, C1+L1 `site_type`, the `co_instances` carry-forward |
| `backend/tests/gates/test_g15_presence_not_fused.py` | G15 both clauses (regression + the D2 no-silent-pick clause) |
| `backend/tests/gates/test_g17_no_mint_under_rebuild.py` | G17 extended: no mint / no `store.append` under `rebuild()`, non-vacuous |
| `backend/tests/gates/test_s2_flag_off_equivalence.py` | flag-OFF equivalence (golden **and** real corpus). Flag-ON byte-identity deliberately **not** asserted |

---

## 1. How the suite handles the identifiers the spec does not fix

Same shape as S1's `_rk_atoms.py`: the spec fixes *concepts*, never *names*. Four names are discovered, and
every discovery miss fails loudly quoting the spec line rather than passing:

| discovered | how | if it cannot be found |
|---|---|---|
| the `layer` tag's key | any key on a type/attr entry containing `layer` (`AttrDef` is `extra="allow"`, so an extra key is legal) | fails: "declares no layer tag (plan §4 A2 …)" |
| the layer **accessor** | any public callable in `chanakya.ontology` (module- or class-level) whose name contains `layer`; the accessor's answers are then diffed against the file's own declaration | fails, listing `NodeTypeIndex`'s current public methods |
| a materialized node's layer | a `NodeView` field, else `attrs` — `NodeView` is `extra="forbid"` and `schemas/view.py` is **not** in S2's owned paths, so `attrs` is a legitimate home; the type's declared layer also satisfies it | not required on its own |
| the **S2 feature flag** | any boolean config key (incl. one nesting level) carrying `layer`/`straddle`/`presence`/`materiali`/`instance_routing`/`two_layer`/`rk_layer`/`rk2`/`s2`/`citizen`/`split_straddl` | the bundle is left untouched and every behavioural failure appends `flag_report()` naming what was searched |

**This is the one contract the implementer must honour for the suite to grade S2 fairly:** if the stage's
flag is a boolean config key whose name carries one of those tokens, the behavioural tests turn it on
themselves. If it is named something else (or lives in an env var), the behavioural tests will run against
the flag-**off** graph and fail with the `flag_report()` text explaining exactly that. Either widen the token
list in `_rk_layer.FLAG_TOKENS` or name the flag accordingly — do **not** weaken the assertions.

The behavioural fixtures load the **shipped `config/ontology.yaml`** (credibility/sources/resolution stay
synthetic, per the `tests/credibility/builders` idiom) because the layer tags *are* the thing under test: a
fixture declaring its own tags would test the fixture. The `basing_proposer` knobs are copied verbatim from
the shipped `credibility.yaml` so no fixture can pass or fail on a mis-guessed knob name.

---

## 2. Per test: what it asserts · the spec line · does it fail today

### `tests/config/test_rk_layer_a2_layer_tags.py`

| test | asserts | spec | today |
|---|---|---|---|
| `test_the_shipped_ontology_still_declares_the_stated_type_and_attribute_counts` | 13 node types, 81 attribute entries — the denominators A2 is measured against, read from the YAML | session item 1: "(81 attribute entries, 13 node types) … this **adds one key per entry**, nothing is restructured" | **PASSES** (a deliberate denominator guard: dropping an entry to shrink the tagging job must fail) |
| `test_every_node_type_is_classified` | every type carries a tag; a third value is allowed but only **one**; an untagged type is allowed only for L3's meta kinds | A2 + **L3** "give `layer` a third value (or an explicit exemption) … **State the third value in config**" | **FAILS**: `node type(s) carry no layer tag and are not one of L3's meta kinds: ['basing_site', 'component', 'contract_import_event', 'interceptor_stockpile', 'manufacturer', 'trading_org', 'unit', 'variant']` |
| `test_the_meta_kinds_are_not_forced_into_design_or_instance` | `source`/`indicator`/`known_gap` are **not** design or instance | **L3** "Forcing a meta type into `design` or `instance` would corrupt the straddle-split trigger … a mis-tagged meta type would generate phantom splits" | **PASSES vacuously today** (nothing is tagged) — it is the clause that bites if a migration tags all 13 `design`; guarded by the row above failing |
| `test_the_types_whose_layer_the_design_fixes_are_tagged_accordingly` | variant/component/manufacturer ⇒ design; `unit` ⇒ instance | spine/13 §3 "Type / design layer — variant, component, radar, manufacturer"; **L2** "`unit` is the **formation** citizen" | **FAILS**: `layer tags contradict the design: {'variant': None, 'component': None, 'manufacturer': None, 'unit': None}` |
| `test_both_layers_are_actually_used` | ≥1 type in each of design and instance | spine/13 §3 names populations for both | **FAILS**: `no node type is tagged 'design'` |
| `test_every_attribute_entry_declares_a_layer` | all 81 file-declared entries carry a layer in {design, instance} | A2 "**and** every `attribute_type` … gains a `layer` tag" | **FAILS**: `81 of 81 attribute entries carry no layer tag: ['manufacturer.role', …]` |
| `test_no_attribute_entry_claims_both_layers` | no entry's layer is a list / `both` / `either` / `contextual` / comma-joined | **D-13.3** "a genuinely dual attribute is **split into two attribute-types** … not made contextual" | **PASSES vacuously today**; becomes live the moment tags exist |
| `test_the_split_trigger_is_reachable_in_the_shipped_schema` | some **design**-layer node type declares an **instance**-layer attribute — else A4's trigger is dead code | §7 RK-LAYER 2 "The split trigger is an *instance-layer attribute on a design-layer node*" | **FAILS**: `the shipped ontology declares no design-layer node type carrying an instance-layer attribute, so A4's split trigger … is unreachable in production` |
| `test_a_layer_accessor_exists_in_the_ontology_module` | a public `layer`-named callable in `chanakya.ontology` | §7 RK-LAYER 1 "Add the layer accessor in `ontology.py` beside `refines`/`identity`" | **FAILS**: `… Public methods on NodeTypeIndex today: ['identifier', 'refine', 'relational_identity']` |
| `test_the_layer_accessor_reads_what_the_file_declares` | the accessor's answer == the file's declaration for all 13 types (a reader, not a second hardcoded copy) | A2 + G6 | **FAILS**: `no layer accessor on NodeTypeIndex (found elsewhere: [])` |
| `test_operated_by_exists_as_a_declared_predicate` | `operated-by` exists **and** declares from/to | §7 RK-LAYER 5 / **D7** "the predicate does not exist. Add it here, or G18 silently tests half of itself" | **FAILS**: `config/ontology.yaml declares no 'operated-by' edge … Declared edges: [...]` |
| `test_the_customs_event_to_trading_org_relation_is_expressible` | some edge connects `contract_import_event` ↔ `trading_org` | **D12** "the sourced relation inexpressible while making the unsourced thing easy is an anti-fabrication hazard" | **FAILS**: `no edge type connects 'contract_import_event' to 'trading_org' …` |
| `test_trading_org_is_reachable_by_some_edge` | ≥1 edge names `trading_org` at either end | **L4** "`trading_org` is named by NO edge type at all, so a correctly-typed consignee can only be an orphan" | **FAILS**: `no edge type names 'trading_org' in its from/to …` |
| `test_the_new_predicates_do_not_collide_on_endpoint_types` | `EdgeLaneIndex.collisions == {}` after S2's additions | `chanakya/ontology.py` / D-A: every extractor edge uniquely determined by `(from → to)` | **PASSES** (regression guard). The live trap: `operated-by` declared `variant → unit` + `extractor: true` collides with `inducted-into` and would start mis-laning inductions |
| `test_new_decaying_edges_keep_a_reachable_half_life` | `unreachable_half_lives == {}` | SC-2: a perishable edge with no reachable half-life scores as eternal | **PASSES** (regression guard) |
| `test_based_at_supersede_key_is_tagged_by_site_type` | `based-at`'s declaration names `site_type` in a **machine-readable** field (never a comment) | §7 RK-LAYER 5 / R1.3 / C1 | **FAILS**: `'based-at's declaration carries no machine-readable 'site_type' … (declared: {… 'instance_key': ['from']})` |
| `test_site_type_is_declared_on_the_type_that_carries_it` | `site_type` is still a declared attribute of some type | C7 prerequisite | **PASSES** |
| `test_a_closed_site_type_vocabulary_is_declared_in_config` | a list-of-≥2-strings under a `site_type`-named key, anywhere in the nine surfaces | **L1 rule 1** "S2 declares a closed `site_type` vocabulary in config (the *kind of place* axis only)" | **FAILS**: `config declares no closed 'site_type' vocabulary …` |
| `test_a_numeric_equipment_count_attribute_is_declared` | a count/quantity attribute exists **and** sits on an instance-layer type | **L4** "No numeric equipment-count attribute anywhere … S2 declares it"; spine/13 §3a puts count on the presence | **FAILS**: `the count attribute(s) {'contract_import_event': ['quantity']} sit on no instance-layer type …` |
| `test_an_instance_layer_presence_node_type_exists` | an instance-layer type that is neither `unit` nor a refinement of it | **L2** "add a new instance-layer node type for the presence citizen" | **FAILS**: `no node type is tagged instance-layer at all …` |
| `test_the_presence_type_is_not_a_refinement_of_the_formation` | nothing declares `refines: unit` | **L2** "A presence is **not a kind of unit** … Refinement models *narrower*, not *weaker*" | **PASSES vacuously today**; live once the type lands |

### `tests/view/test_rk_layer_routing.py` (A4 / A3)

| test | asserts | spec | today |
|---|---|---|---|
| `test_a_sighting_materializes_a_provisional_presence_not_the_shared_design_node` | the `observed-at` subject endpoint is **not** the design node, and reads as instance-layer | spine/13 §5.3 "the build does **not** point it at the shared design node — it materializes a provisional **presence** P" | **FAILS**: `the observed-at sighting still binds to the shared design node 'hq9p' (subjects: ['hq9p'])` |
| `test_the_materialized_presence_is_not_the_formation_citizen` | the presence's type ∉ `{unit}` **and** is a declared presence type | **L2**; G15's whole purpose | **FAILS**: `no presence was materialized for the sighting …` |
| `test_the_presence_stays_linked_to_the_shared_design_node` | an edge exists between presence and design node | spine/13 §5.3 "P `instance-of`/`fields` HQ-9/P(design)" | **FAILS**: `no presence was materialized, so there is no link to assert` |
| `test_the_shared_design_node_survives_the_split` | the design node is not consumed by materialization | spine/13 §3/§5.2 | **PASSES** (regression guard) |
| `test_a_bare_sighting_never_forces_a_formation` | no `based-at`, no `unit` node from a bare sighting | **D-13.13** "reifying an organizational individual we cannot source would violate the non-negotiable" | **PASSES** (the G15 regression clause — current behaviour, kept deliberately) |
| `test_an_edge_with_no_instance_endpoint_mints_nothing` | a design-only lane mints nothing and is not re-pointed | **A4** "a cross-layer holding edge does not [materialize]" | **PASSES** (regression guard; **the negative is as load-bearing as the positive**) |
| `test_a_straddling_mention_splits_into_two_linked_nodes` | one mention carrying a design-layer **and** an instance-layer attribute ⇒ ≥2 nodes, one per layer, linked | **D-13.5** "a straddling mention is split into linked design + instance nodes" | **FAILS** (via the discovery helper): `the shipped ontology declares no design-layer node type carrying an instance-layer attribute …` |
| `test_the_design_half_of_a_split_keeps_only_the_design_fact` | the instance-layer attribute is **absent** from the design node; the design-layer one is present | spine/13 §5.2 "Design-level facts attach to the (shared) design node; instance-level facts attach to an instance node" | **FAILS** (same discovery failure) |
| `test_three_reports_of_one_sighting_do_not_become_three_launchers` | no count attribute equals 3 or the supporting-claim count | **A3** "`count` … **never** `= how many reports merged`" | **FAILS**: `no presence was materialized, so the count rule cannot be exercised …` |
| `test_a_stated_count_is_carried_as_a_sourced_attribute_of_the_presence` | a stated figure of 6 is reachable from the presence | spine/13 §3a "an attribute of the presence with its own sourced evidence" | **FAILS**: `no presence was materialized, so a count cannot be an attribute *of the presence*` |
| `test_an_unstated_count_defaults_to_unknown_rather_than_a_number` | no numeric count appears that no source stated | **D-13.8 / L4** "default `unknown`, never fabricated" | **PASSES** (regression guard — a default of `1` would be a fabricated OOB figure) |
| `test_a_stated_based_at_binds_the_formation_directly` | a stated `based-at` binds unit→site and is not relabelled derived | **D-13.13** the stated path "is the stronger path" | **PASSES** (regression guard) |
| `test_a_low_grade_stated_basing_still_runs_through_source_grade` | a weak-source stated basing is not `confirmed` and scores strictly lower than a strong one | spine/13 §5.3 "**stated ≠ trusted**" | **PASSES** (regression guard) |

### `tests/view/test_rk_layer_derived_basing.py` (D-13.6) — **all 7 fail today**

`test_rebuild_materializes_the_derived_basing_edge` · `…_cites_both_premise_claim_atoms` ·
`…_is_weaker_than_a_stated_one` · `test_the_derivation_appends_nothing_to_the_evidence_log` ·
`test_two_rebuilds_of_the_derived_basing_are_byte_identical` · `test_the_offline_minting_pass_no_longer_mints`
· `test_the_basing_derived_bundle_suffix_is_gone`.

Verbatim signatures (representative):
- `rebuild() materialized no 'based-at' edge from the derivation triangle … Edges built: [('inducted-into', 'hq9p', 'unit_8ad'), ('observed-at', 'hq9p', 'site_rahwali')]`
- `ingest/basing.py still mints claim atoms at ['ingest/basing.py:358'] — §7 RK-LAYER 4 deletes the minting pass`
- `the seed loader still globs derived basing bundles ['__basing.json']`

Every one of them names the derived edge's provenance requirement — "**citing its two premise claim-atoms**
… with **NO** `make_claim_id`/`ClaimRecord` mint and **NO** `store.append` inside rebuild" (§7 RK-LAYER 4).
`…appends_nothing_to_the_evidence_log` and `…byte_identical` both assert the derived edge *exists* first, so
they cannot pass vacuously once the derivation lands.

### `tests/view/test_rk_layer_supersede_identity.py` (R1.4 / the D1 tail / C1+L1)

| test | asserts | spec | today |
|---|---|---|---|
| `test_a_relocation_over_an_unquestioned_identity_is_still_promoted` | **the mirror**: an earned relocation still promotes and still draws its edge | R1.4 "Machine promotion is only legitimate over an identity the system actually earned" — it forbids *unearned* promotion, not promotion | **PASSES** (this is what stops the refusals below being satisfied by disabling supersession) |
| `test_the_rival_mention_really_is_an_unadjudicated_identity_question` | fixture premise: the rival pair is a `candidate` (`merge_band == "candidate"`), **not** fused | **D8** "`candidates`→probable … only `same_as` fuses" | **PASSES** (premise guard, asserted separately so the next test cannot pass for the wrong reason) |
| `test_a_relocation_is_not_machine_adjudicated_over_a_sub_confirmed_identity` | no drawn `supersedes`; nothing retired; gate ≠ `promoted`; both edges keep `candidate_supersede` | **R1.4** | **FAILS**: `a node→node relocation was DRAWN while the subject's own identity was still an open question for the analyst (['same-as:unit_1|unit_2'])` |
| `test_the_gap_fixture_raises_a_real_known_gap_when_nothing_is_retired` | non-vacuity control: with no floor, exactly one Known Gap on the older basing and status `insufficient` | — | **PASSES** |
| `test_a_retired_edges_known_gap_is_not_deleted` | the retired edge's Known Gap survives promotion | §7 RK-LAYER 7 / **C2** "no Known-Gap deletion" | **FAILS**: `the retired edge's Known Gap was deleted by the promotion (gaps left: [])` |
| `test_an_honest_insufficient_is_not_flipped_to_stale` | the older edge's status is not `stale` when its own assessment was `insufficient` | **C2** "no `insufficient → stale` on the retired edge" | **FAILS**: `the older basing's honest 'insufficient' became 'stale'` |
| `test_a_well_evidenced_retired_position_still_reads_stale` | **the mirror**: an *assessable* retired position still reads `stale` and raises no gap | `credibility/supersession.py` "→ *stale*, not *insufficient* — it is history, not a gap" | **PASSES** (this is what stops the two rows above being satisfied by disabling retirement) |
| `test_two_concurrent_basings_at_different_site_classes_are_not_a_relocation` | differing declared **classes** ⇒ no drawn relocation, nothing retired, no contradiction, **different** instance keys | **C1 / R1.3** "two concurrent valid basings, not a relocation" | **FAILS**: `config declares no closed 'site_type' vocabulary, so C1's de-confliction has no classes to key on (ruling L1 rule 1)` |
| `test_an_unmappable_site_type_lands_in_the_third_state` | unmappable strings ⇒ **same** instance key (no de-confliction) **and** no promotion/draw **and** a named gap | **L1 rule 3** "no de-confliction, no fusion, and a **named gap** … must never silently de-conflict … must never silently kill a supersede" | **FAILS**: `a relocation was drawn from two site_type values the config cannot classify — L1's third state is 'no de-confliction, no fusion'` |
| `test_an_absent_site_type_lands_in_the_same_third_state_as_an_unmappable_one` | absent `site_type` ⇒ one instance bucket **and** no fusion **and** a named gap | §7 RK-LAYER 5's fail-safe reconciled into **L1 rule 3** by the ruling of 2026-07-25: absence and unmappability are the same condition | **FAILS**: `a relocation was drawn between two sites whose class is unknown (no site_type stated at all)` |
| `test_the_flagship_relocation_is_held_while_its_site_classes_are_unknown` | on the **real corpus with the flag on**: if the two flagship sites' classes are unknown or differ ⇒ no drawn relocation + the pair held; if both resolve to the **same** class ⇒ the relocation must still be drawn | ruled 2026-07-25: "**that consequence is correct and intended** … a held relocation with a named gap is the system saying 'I cannot classify these sites yet' — precisely the non-negotiable behaving"; L1 rule 4 "Until [the mapping] lands, the third state is the correct, honest behaviour" | **FAILS**: `a relocation was drawn between the flagship sites while their classes are {'site_rahwali': None, 'site_rawalpindi': None} (stated: {'site_rahwali': 'airfield', 'site_rawalpindi': 'prepared revetment complex / airfield site'})` |
| `test_the_two_ends_of_a_relocation_never_become_merge_candidates[True/False]` | the origin and destination of one unit's relocation never fuse and are never offered as duplicate candidates — parametrized over **same** and **differing** site classes | §7 RK-LAYER 5 "A naive `site_type` re-key … would **silently drop** this mitigation, so a confirmed relocation would manufacture relational evidence that origin ≡ destination. **Gate-fixture it.**" | **PASSES both** (regression guard; the differing-class arm is precisely the one a naive re-key breaks, because splitting the instance stops `co_instances` from excluding the shared unit) |

### `tests/gates/test_g15_presence_not_fused.py`

| test | asserts | spec | today |
|---|---|---|---|
| `test_a_sighting_without_organizational_evidence_never_becomes_a_basing` | the original G15 clause | plan §5 G15 | **PASSES** — and §5a says so out loud ("As written it **passes vacuously**"). Kept as the regression guard the amendment asks for |
| `test_a_sighting_plus_an_induction_does_derive_one_attribution` | the differential's control arm derives exactly one attribution | §7 RK-LAYER 4 | **FAILS**: `one candidate formation derived []` |
| `test_two_candidate_formations_are_never_silently_truncated` | **the D2 clause**, differentially: the 2-candidate rebuild must show ≥2 attributions **or** a gap the 1-candidate rebuild did not have | §5a G15 "*Two candidate formations ⇒ two attributions, or one plus an explicit named gap. Never a silent pick.*" | **FAILS**: `the single-candidate control derived nothing, so the differential below is vacuous` |
| `test_a_truncated_attribution_names_which_candidate_it_dropped` | if truncated, the dropped unit is named in a gap or on the derived edge | §5a "an **explicitly named** gap"; D-13.14 "the residual is a first-class coverage item" | **FAILS**: `the attribution was truncated to [] and nothing names the dropped candidate(s) ['unit_12ad', 'unit_8ad']` |
| `test_the_undercount_is_visible_without_any_merge_being_involved` | the two candidate formations stay **unmerged**, so this gate measures D2 and not S3's G16 | **D2** "an OOB undercount with **no merge involved**" | **PASSES** (scope guard: if the fixture ever fuses, the file is silently testing the co-location cap instead) |

### `tests/gates/test_g17_no_mint_under_rebuild.py`

| test | asserts | spec | today |
|---|---|---|---|
| `test_the_derived_basing_branch_executes_under_rebuild` | the premise pair actually derives — the non-vacuity precondition for everything else in the file | §5 G17 "*Fixture must be non-vacuous:* include an `observed-at`+`inducted-into` premise pair so the derived-basing branch actually executes" | **FAILS**: `the premise pair derived no 'based-at' edge, so the no-mint clauses below are vacuous` |
| `test_rebuild_completes_with_the_evidence_log_write_path_disabled` | `EvidenceLog.append`/`append_many` patched to raise; rebuild still produces the identical view | G17 "no code path under `rebuild()` calls … `store.append`" | **PASSES** (a negative invariant; it binds from S2 and fails the moment the derivation writes) |
| `test_rebuild_completes_with_the_claim_mint_disabled` | `make_claim_id` patched to raise on both import surfaces | G17 "no code path under `rebuild()` calls `make_claim_id`" | **PASSES** (same) |
| `test_no_mint_or_evidence_append_in_any_rebuild_reachable_module` | static call-graph scan of the 38 modules reachable from `view/pipeline.py`, exempting only `schemas/ids.py` | G17's second accepted form: "an input-independent static call-graph scan of rebuild-reachable modules" | **PASSES** (only hit today is the constructor-composing-a-constructor at `schemas/ids.py:83`, which S1's gate already ruled exempt and *proved* incapable of appending) |
| `test_the_reachability_walk_sees_the_real_rebuild_path` | `view/pipeline.py`, `view/supersede.py`, `resolve/__init__.py`, `credibility/supersession.py` are all in the scan surface | — | **PASSES** (scan-surface self-check) |
| `test_the_write_scanner_flags_a_planted_violation` | the scanner catches a planted mint **and** a planted `evidence_log.append_many`, follows a **relative** import, and does **not** flag `plain.append` | §5a "a gate that cannot fail is a gate that lies" | **PASSES** (negative control). Note: `tests/gates/_srcscan.imported_modules` reads `node.module` only, so it is blind to `from .supersede import …`; a reachability walk built on it would have scanned ~11 modules instead of 38. `_rk_layer._imports_of` resolves relative imports |

### `tests/gates/test_s2_flag_off_equivalence.py` — all pass (the safety property)

- `test_flag_off_rebuild_of_the_golden_logs_still_matches_the_recorded_view` — the golden fixture carries its
  own tiny ontology, so it is **blind to the shipped file S2 edits**; it catches a `view/pipeline.py` change.
- `test_flag_off_leaves_the_real_corpus_graph_unchanged[node_count|edge_count|event_count|known_gap_count]` —
  the **only** assertion that can see a config-only regression (layer tags, new predicates, the `site_type`
  re-key). Parametrized per metric so a failure names *what* moved.
- `test_the_shipped_config_still_loads_and_rebuilds_after_the_ontology_edits` — arrival guard: the loader
  rejects malformed shapes, and that loudness must not become a boot break.
- **Flag-ON byte-identity is deliberately NOT asserted** (§5a-bis: "for those stages an unchanged view means
  the stage did nothing"; "Never gate, default-away, or curb a target-correct capability to keep a fixture
  green").

---

## 3. Spec silences — everywhere the spec did not determine an outcome

Ordered by how likely each is to cause an implementer/test disagreement.

1. ~~**The stated flag-off baseline does not reproduce.**~~ **RULED 2026-07-25 — closed, and no longer a
   silence.** Two valid surfaces exist and both reproduce: the **booted app** (160 / 73, hash
   `22d668a3…dac3a9`) withholds the two flagship-relocation documents from the boot seed; the **full-scenario
   harness** (169 / 80 / 71 / 20, md5 `14ccc45c9f702763a1e27b9900bb56db`) sees everything. The harness surface
   is the gate, precisely because the booted one cannot see the relocation/supersede path S2 changes most. The
   test's constant block now states both surfaces and why one was chosen.
2. **The flag has no name.** "Behind a flag, dual-run only" is all the spec says. See §1 for the discovery
   contract; this is now the single highest-risk coupling between the two hands. **Still open.**
3. ~~**"Sub-confirmed identity" (R1.4) names no carrier.**~~ **RULED — my reading confirmed.** It is the
   merge-band vocabulary: an **open `candidate`** merge is sub-confirmed (D8: `candidates` → probable), and
   node `status` is expressly *not* the carrier, because the legitimate flagship subject sits at `probable` and
   gating there would delete the beat. The fixture builds an open `candidate` same-as touching the relocation's
   subject and asserts its own premise (`merge_band == "candidate"`, both units still separate).
4. ~~**Absent vs unmappable `site_type` diverge between two authorities.**~~ **RULED — both land in the same
   third state.** §7 RK-LAYER 5's weaker absent-value fail-safe ("same bucket … or raise") predates L1 and is
   superseded: absence and unmappability are the same condition for keying purposes — *we do not know the
   class* — so both yield no de-confliction, no fusion, and a named gap. The absent-value test now asserts the
   full third state and fails today.
5. ~~**The third-state consequence for the flagship is not stated.**~~ **RULED — correct and intended, and now
   pinned.** With the flag on and no `site_type` mapping, the flagship relocation is **held, gap-named, and not
   drawn**; that is the honest outcome, not a regression, and the test says so in capitals so nobody loosens
   the vocabulary to make the edge come back. Measured detail worth knowing: the two flagship sites' *node*
   attrs carry `airfield` and `prepared revetment complex / airfield site` — L1's **over-merge** direction (two
   strings for arguably one kind of place), not the `observed-imagery-site` / `stated_destination` pair L1
   quotes, which lives elsewhere in the claim set. The test reads the classes rather than assuming them, so it
   self-adjusts to whatever DATA maps — and if a mapping sends both to one class it must then produce the drawn
   edge it claims.
6. **Where a materialized node records its layer is undefined.** `NodeView` is `extra="forbid"` and
   `schemas/view.py` is not in S2's owned paths, so the tag can only live in `attrs` (or be inferred from the
   node's type). Accepted either way.
7. **The design↔instance binding edge does not exist.** spine/13 §5.3 links the presence to the design with
   `instance-of`/`fields`; the shipped ontology declares **neither** (`fields` exists only in the golden test
   fixture), and §7 RK-LAYER 5's list of ontology additions does not name one. My test asserts only that
   *some* edge links the two, not its name. **Flagged to the implementer by the coordinator** — materializing a
   presence linked to its design node needs this edge, and no ontology-addition item currently covers it.
8. **A2 vs L2 pull in opposite directions on edge endpoint layers.** A2 says "Edge endpoint-layers derive from
   the already-declared `from`/`to`", while L2 says `observed-at` keeps its **design** endpoints and the
   presence is materialized in the derived layer. So "which edges materialize" cannot be derived from endpoint
   layers alone — some other signal is needed and the spec names none. I sidestepped it: A4's negative is
   asserted on a pure design-layer authorship lane (`manufactures`/`supplies-component`/`equips`, first
   available), with `observed-at`/`based-at` explicitly excluded from the pick.
9. **"Named gap" has no declared shape.** The D2 clause and L1 rule 3 both require one; nothing says whether
   it is a `KnownGap`, an attribute on the derived edge, or a coverage item. Asserted permissively
   (`KnownGap` **or** an attr naming the dropped candidate) and differentially against a control run.
10. **`site_type` normalization has no declared home.** L1 says keying is on the normalized class and "mapping
    the 15 existing values is DATA's job" — but not where the *map* lives, nor whether the class is stamped on
    the claim, the site node, or computed at key-build time. My tests state site_type on the site node's attrs
    (where the ontology declares it) and assert only outcomes.
11. **The dual-attribute split (D-13.3) is only half-testable.** "No entry claims both layers" is assertable;
    "this attribute *was* dual and *was* split into two types" is not, because nothing declares which
    attributes are dual. Asserted the shape rule only.
12. **A2's "81 attribute entries" counts node types only.** Edge and event types declare no `attrs` today, so
    "every `attribute_type`" is satisfied by the 81 node-type entries. If S2 adds attrs to an edge type, the
    count assertion will fail — correctly, but for a reason the session file does not anticipate.
13. **`operated-by`'s endpoints are unspecified.** spine/13 §3 lists it among the layer-*binding* relations,
    which suggests `variant → unit`; that exact declaration, marked `extractor: true`, collides with
    `inducted-into` and would mis-lane every induction. I assert only that the predicate exists, declares
    endpoints, and does not introduce a collision — the collision test is the one likely to catch a hurried
    addition.
14. **`imported-by → unit` was left alone.** §7 RK-LAYER 5 says "re-examine whether `imported-by → unit`
    should require a stated unit" — a *re-examination*, not a requirement, so nothing asserts it. If the
    implementer removes or constrains that lane, no test of mine objects.

## 4. Two mechanical notes for whoever integrates

- **`tests/view/test_supersede.py::test_garrison_and_field_are_not_a_false_supersede` is
  `xfail(strict=True)`** and its stated fix *is* S2's `site_type` re-key. Its fixture states **no**
  `site_type`, so under the absent-value fail-safe (no de-confliction) it should keep xfailing and the
  flag-off "2 xfailed" baseline holds. If the re-key ever splits on absence, that test XPASSes and — being
  strict — turns red. I did not touch it (not mine to edit); flagging it so nobody reads it as a new
  regression.
- **File ownership.** All new files are prefixed `test_rk_layer_*` / `test_g15_*` / `test_g17_*` /
  `test_s2_*` plus `tests/_rk_layer.py`, so the impl hand's own tests under `tests/view/**` cannot collide.
