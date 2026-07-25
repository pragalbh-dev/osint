# RK-ATOMS (S1) — independently-authored test suite: what it asserts, and what currently fails

**Author:** the independent test hand. Branch `s1/rk-test`, worktree `wt-RK-ATOMS-test`, based on
`design/resolution-redesign`.
**Written from the spec alone.** The implementation branch (`s1/rk-impl`), its worktree and its
`RK-ATOMS-IMPL-NOTES.md` were never read. Every assertion below is derived from
`artifacts/plan/01-replumb-implementation-plan.md` (§4 **A1**/**A7**, §5 **G17**, §7 **RK-ATOMS**),
`artifacts/plan/sessions/RK-ATOMS.md`, `artifacts/spine/13-*.md` §8/§10 + **D-13.7/D-13.11/D-13.18**,
`tmp/conv/rk-spike-{code-facts,DECISIONS,REVIEW-VERDICT}.md`, and `CLAUDE.md`'s non-negotiable.

## Files

| File | Covers |
|---|---|
| `backend/tests/_rk_atoms.py` | shared **discovery** helpers (not tests) — see "naming silence" below |
| `backend/tests/ingest/test_claim_atom.py` | scope item **1** — the claim atom is the post-dedup `claim_id` |
| `backend/tests/ingest/test_dedup_referent.py` | scope items **2 + 3** — dormant referent field, atom-aware dedup |
| `backend/tests/schemas/test_a7_discriminators.py` | scope item **4** — A7 discriminators + structured `TypeDef.attrs` |
| `backend/tests/gates/test_g17_atom_mint.py` | **G17**, S1's half only (+ `seed.py`-as-bundle-reader) |
| `backend/tests/gates/test_s1_zero_behavioural_change.py` | scope item **5** — the golden view md5 pin |

## Measured result against the CURRENT, UNMODIFIED code

Command (this worktree has no `backend/.venv`; `python3` is the pyenv 3.12 interpreter that carries the deps):

```
cd backend && python3 -m pytest
```

**Whole suite: `25 failed, 1063 passed, 7 skipped, 2 xfailed in 30.68s`.**

Reconciliation against the recorded baseline (`1026 passed, 7 skipped, 1 xfailed`): 63 tests added
(1097 − 1034), of which **25 fail** (the specified behaviour does not exist yet), **1 is a new documented
xfail**, and **37 pass** as regression guards. `1063 − 37 = 1026` — **no pre-existing test was disturbed.**
`ruff check` is clean on all six files.

---

## Amendment, 2026-07-25 — the "no backward compatibility" ruling

Rebased onto `design/resolution-redesign` @ `d7e443c` (my suite merged at `9f070a6`, the implementation at
`114a0f6`, plus `ab1b705` which amended my G17 file to exempt the id-defining module from the mint-site
rule). **Against that merged base my whole suite passed — including the two tests that accepted the
bare-string `attrs` form.** That is what the ruling withdraws: the shipped S1 loader is a **dual-form**
loader, exactly the "temporary tolerance" the ruling forbids.

**Revised state after the ruling: `3 failed, 1091 passed, 7 skipped, 2 xfailed in 31.40s`.** The three
failures are precisely the inverted/new assertions, and no other test in the suite moved.

### What changed in the suite

| Test | Change | Now |
|---|---|---|
| `test_typedef_still_accepts_the_old_bare_string_attrs_form` | **inverted and renamed** → `test_a_bare_string_attr_entry_is_rejected` — a bare string must **raise** | **FAILS-NOW** |
| `test_mixed_bare_and_structured_entries_in_one_type_still_read` | **inverted and renamed** → `test_a_mixed_bare_and_structured_attrs_list_is_rejected` — a half-migrated type must **raise** | **FAILS-NOW** |
| `test_attribute_names_read_the_same_from_either_form` | **deleted** — there is only one form now; the surviving `test_typedef_accepts_structured_attr_entries` covers it | — |
| `test_a_structured_attr_entry_tolerates_an_unfamiliar_key` | **deleted** — it asserted tolerance *via* `layer`, and the ruling forbids asserting anything about `layer` at S1 (see silence **S-6**) | — |
| `test_the_repo_ontology_config_still_loads_after_the_restructure` | **replaced** by the three migration-net tests below | — |
| `test_the_repo_ontology_config_loads_under_the_structured_only_schema` | **new** — no bare string may survive in the shipped `config/ontology.yaml` | **FAILS-NOW** |
| `test_the_loader_round_trips_the_shipped_attribute_names_name_for_name` | **new** — loaded model == what the file declares, per type, in order (catches a loader that drops/reorders/renames on parse) | GUARD |
| `test_the_structured_migration_loses_no_declared_attribute` | **new** — the frozen pre-migration vocabulary must survive in full (catches a *botched migration*: a dropped or renamed attribute) | GUARD |

`tests/_rk_atoms.py` gains `raw_attr_name()` (reads a **raw YAML** entry, tolerant of either shape, for the
round-trip test) and its `attr_names()` docstring now states that the bare-string branch is a legacy-input
name extractor and **never** the form validator — otherwise the round-trip test would fail for the wrong
reason. No other test of mine leaned on the bare form (verified by grep across all six files).

### Verbatim signatures after the ruling

```
tests/schemas/test_a7_discriminators.py:167: in test_a_bare_string_attr_entry_is_rejected
    with pytest.raises(ValueError):
E   Failed: DID NOT RAISE <class 'ValueError'>

tests/schemas/test_a7_discriminators.py:177: in test_a_mixed_bare_and_structured_attrs_list_is_rejected
    with pytest.raises(ValueError):
E   Failed: DID NOT RAISE <class 'ValueError'>

tests/schemas/test_a7_discriminators.py:255: AssertionError: config/ontology.yaml still declares 81
bare-string attrs entries (first few: ['manufacturer.role', 'manufacturer.tier',
'manufacturer.foreign_control', 'manufacturer.named_examples', 'manufacturer.production_rate']) — the bare
form is removed, not tolerated (ruling 2026-07-25)
```

`DID NOT RAISE` is the proof asked for: the two inverted tests are being run **against a loader that still
coerces bare strings**, so they are genuinely testing the removal, not describing it.

### Facts the implementer of the removal needs

* **The migration is confined to one file.** `config/ontology.yaml` — **13 types, 81 bare-string entries**
  (`manufacturer` 7, `trading_org` 4, `component` 7, `variant` 9, `contract_import_event` 6, `unit` 7,
  `basing_site` 6, `area_of_operations` 4, `interceptor_stockpile` 7, `techdata_authority` 2, `source` 8,
  `indicator` 10, `known_gap` 4). The other two configs that grep for `attrs:` — `subjects.yaml`
  (`materiality_attrs`) and `credibility.yaml` (`gated_attrs`, `fingerprint_attrs`) — are **unrelated keys
  in other sections**, not `TypeDef.attrs`.
* **Nothing else constructs a `TypeDef`.** The only `TypeDef(` in `chanakya/**` is the class definition, and
  no test or fixture builds one with bare attrs (verified by grep over `tests/**`).
* **The golden view is safe.** `backend/tests/fixtures/golden/config/ontology.yaml` declares **no `attrs` at
  all** (`- {name: unit, freshness_class: durable}`), so the structured-only migration cannot move the
  golden view — S1's byte-identical invariant and the md5 pin are unaffected.
* The frozen pre-migration vocabulary now lives as `PRE_MIGRATION_ATTRS` in
  `tests/schemas/test_a7_discriminators.py`, captured from `d7e443c`. It is a **subset** check, so DATA-C
  may add attributes freely; only a loss or a rename fails.

---

## Per test

Legend: **FAILS-NOW** = the spec's behaviour is absent from the current code, so the test proves it can
fail. **GUARD** = passes now on purpose; it protects a property S1 must not break (a test that only fails
now would let S1 silently regress the things it is supposed to preserve).

### `tests/ingest/test_claim_atom.py` — scope item 1 (7 pass + 1 xfail)

Spec line that makes these correct (plan §4 A1):

> "**Claim atom** = the per-mention bedrock = the **post-dedup `claim_id`** (canonicalised in
> `dedup.assign_claim_ids`, not at construction). S1 formalizes it as the stable addressing bedrock; no new
> id is minted — this names and freezes what already exists."

| Test | Asserts | Now |
|---|---|---|
| `test_construction_time_claim_id_is_provisional_not_the_atom` | the atom is minted in `assign_claim_ids`, not at construction; the input is not mutated | GUARD |
| `test_the_atom_is_minted_from_the_folded_claim_not_per_restatement` | one assertion restated twice ⇒ **one** atom, two spans (the atom's grain is the mention-fold) | GUARD |
| `test_atoms_are_byte_identical_across_input_order` | the atom is content-derived, never arrival-order-derived | GUARD |
| `test_atoms_are_byte_identical_across_reruns` | pure recompute (G2 hygiene at the mint) | GUARD |
| `test_no_reference_survives_pointing_at_a_provisional_id` | the **closure** property: after the reshape every cross-claim reference names an atom; ids never in the input are left alone | GUARD |
| `test_tier3_mention_refs_follow_the_atom` | `_subject_mention`/`_object_mention` are claim ids too, so they follow the remap | GUARD |
| `test_retraction_target_points_at_an_atom` | `targets` follows the remap | GUARD |
| `test_fold_does_not_orphan_a_reference_to_the_folded_mention` | a premise pointing at a **folded-away** mention must not dangle | **xfail (non-strict)** — see silence **S-4** |

Verbatim signature of the xfail (run with `--runxfail`):

```
E       AssertionError: premise ['folded'] points at a mention the fold discarded — an orphaned atom reference
E       assert {'folded'} <= {'d01-l1', 'd01-l4'}
```

### `tests/ingest/test_dedup_referent.py` — scope items 2 + 3 (16 FAILS-NOW)

Spec lines (plan §7 RK-ATOMS items 2 and 3):

> 2. "Add an optional referent id (**default `None`**) to `ClaimRecord`/payloads (`schemas/claim.py`); add
>    `make_referent_id` beside `make_claim_id` (`schemas/ids.py`) **but do not invoke it** — referents are
>    minted in S3. … Optional-default keeps `extra="forbid"` fixtures loading and S1 non-breaking."
> 3. "Extend `remap_claim_refs` **and** `dedup_within_doc` (`ingest/dedup.py`) to carry/reconcile the
>    referent field, so a value populated later (S3) is **never silently orphaned or collapsed** … **This is
>    the real risk the old plan missed.**"

| Test | Asserts | Now |
|---|---|---|
| `test_claim_record_declares_an_optional_referent_defaulting_to_none` | the field exists and defaults `None` | FAILS-NOW |
| `test_the_referent_field_is_not_required_by_the_schema` | it is absent from the JSON-schema `required` list (non-breaking; no forced fabrication) | FAILS-NOW |
| `test_a_record_that_omits_the_referent_still_validates` | "tolerated-absent on pre-baked fixtures" | FAILS-NOW |
| `test_a_referent_value_round_trips_through_json` | it survives the on-disk evidence-log form | FAILS-NOW |
| `test_the_ingest_reshape_never_populates_a_referent` | **negative direction** — S1 is dormant; S3 mints | FAILS-NOW |
| `test_reading_a_bundle_without_a_referent_leaves_it_none` | the keyless boot path invents nothing for the frozen corpus | FAILS-NOW |
| `test_referent_survives_dedup_within_doc_untouched` | item 3, `dedup_within_doc`, single claim | FAILS-NOW |
| `test_referent_survives_a_fold_of_two_mentions_sharing_one_referent` | item 3, the ordinary S3 shape (a restatement inside one cluster) | FAILS-NOW |
| `test_a_shared_referent_never_widens_the_fold_across_documents` | the referent is **document-local** (A1) and must never become a cross-doc merge signal at ingest | FAILS-NOW |
| `test_referent_survives_the_canonical_id_remap` | item 3, `assign_claim_ids` — the `claim_id` changes, the referent does not | FAILS-NOW |
| `test_remap_claim_refs_does_not_clear_the_referent` | item 3, the `remap_claim_refs` update dict must not blank it | FAILS-NOW |
| `test_a_referent_is_never_rewritten_into_a_claim_id` | **negative direction** — a hostile remap whose keys include the referent's own value must not re-point it at a claim atom | FAILS-NOW |
| `test_fold_of_conflicting_referents_is_deterministic` | the **fold case**: order-independent outcome | FAILS-NOW |
| `test_fold_of_conflicting_referents_never_fabricates_a_third_value` | the **fold case**: the survivor ∈ {left, right} | FAILS-NOW |
| `test_fold_of_conflicting_referents_loses_nothing_silently` | the **fold case**: no value vanishes without a trace | FAILS-NOW — see silence **S-2** |
| `test_carrying_the_referent_does_not_change_the_fold_of_referentless_claims` | zero behavioural change at the dedup boundary | FAILS-NOW (discovery only) |

Verbatim signature (all sixteen fail at the same discovery point):

```
tests/_rk_atoms.py:48: AssertionError: ClaimRecord declares no referent field (plan §4 A1: 'The field is
added to ClaimRecord in S1 as optional, default None (so extra="forbid" fixtures still load and S1 stays
non-breaking)'). Declared fields: ['asserts', 'attributes', 'claim_id', 'doc_ref', 'event_time',
'extraction', 'ingest_time', 'kind', 'payload', 'polarity', 'premises', 'report_time', 'resolved_ref',
'source_id', 'targets']
```

**Why `test_fold_of_conflicting_referents_is_deterministic` is the sharpest test in the suite.** The fold's
survivor is `min(members, key=_earliest_docref_key)` (`ingest/dedup.py:224`) — and with equal sort keys
`min` returns the **first in input order**. Verified empirically on the current code with `attributes`
standing in for the referent (a field the signature also excludes):

```
forward : [('a', {'x': 'LEFT'})]
reversed: [('b', {'x': 'RIGHT'})]
```

So an implementation that simply inherits the representative's referent — the obvious one-line fix — is
**arrival-order dependent**, and `lane.py` phase 1 is a *concurrent* extraction fan-out. This is a
pre-existing latent nondeterminism in `dedup_within_doc` for every field outside the signature
(`claim_id`, `attributes`, `resolved_ref`, `extraction`, `report_time`, `ingest_time`); today it is
harmless because `assign_claim_ids` overwrites `claim_id` deterministically afterwards. The referent would
inherit it. **Flagged for the orchestrator.**

### `tests/schemas/test_a7_discriminators.py` — scope item 4

> **Superseded in part by the 2026-07-25 ruling** — read the "Amendment" section above for the current
> table of this file's `attrs` tests. The discriminator half (below) is unchanged; the `TypeDef.attrs`
> rows marked with the old "accepts both forms" framing are the ones the ruling inverted.

Spec lines (plan §4 A7 / spine/13 §10 / session file item 4):

> "**Structured discriminators** (operator, geography, unit designation, time) are emitted as **structured
> claim context**, not buried in the untyped `attrs` bag. This needs new fields on the `extract.py` mention
> schemas plus the `config_models.py` structured-attrs representation they are declared against …
> All fields **optional** — absence is `unknown`, never fabricated."
> "**Optional**, never required: a required field would force the extractor to fabricate a value the source
> didn't state (violating the non-negotiable) or drop the claim."
> "`TypeDef.attrs` moves from a bare `list[str]` to structured entries." / "Design the entry so **S2 adds a
> field** and nothing else is reshaped."

| Test | Asserts | Now |
|---|---|---|
| `test_the_instance_mention_declares_all_four_discriminator_dimensions` | `UnitMention` carries operator + geography + designation + time as structured fields | **FAILS-NOW** (`['designation', 'time']` absent) |
| `test_every_discriminator_dimension_is_reachable_from_the_extraction_surface` (×4) | each dimension is declared *somewhere* the extractor can fill it | GUARD |
| `test_extraction_tool_schema_declares_no_required_field` (×6) | **the required-field regression** — no `required`, no `additionalProperties` in the emitted tool schema | GUARD |
| `test_no_extraction_field_carries_a_fabricated_default` (×6) | no field is required, and none defaults to a stated-looking value (`"unknown"`, `0`, a country) | GUARD |
| `test_an_empty_mention_carries_no_discriminator_value` (×6) | behavioural half of "absence is `unknown`" — an empty mention fills nothing in | GUARD |
| `test_typedef_still_accepts_the_old_bare_string_attrs_form` | **no config file must change in S1** | GUARD |
| `test_typedef_accepts_structured_attr_entries` | the structured form loads | FAILS-NOW |
| `test_attribute_names_read_the_same_from_either_form` | one vocabulary, two spellings | FAILS-NOW |
| `test_a_structured_attr_entry_tolerates_an_unfamiliar_key` | the S1→S2 seam: S2's `layer` must land as an added field, not a validation error | FAILS-NOW |
| `test_mixed_bare_and_structured_entries_in_one_type_still_read` | a partially-migrated config keeps its whole vocabulary | FAILS-NOW |
| `test_a_structured_entry_with_no_name_is_rejected_or_unreadable` | **negative direction** — an entry naming no attribute must not yield a silently empty vocabulary | GUARD |
| `test_the_repo_ontology_config_still_loads_after_the_restructure` | the real `config/ontology.yaml` still validates, and no attribute name is lost | GUARD |

Verbatim signatures:

```
tests/schemas/test_a7_discriminators.py:60: AssertionError: UnitMention declares no structured field for
['designation', 'time'] — A7 requires all four of operator/geography/designation/time as structured claim
context. Declared: ['UnitMention.alert_posture', 'UnitMention.echelon', 'UnitMention.home_garrison',
'UnitMention.name', 'UnitMention.service_branch', 'UnitMention.source_quote'].

tests/schemas/test_a7_discriminators.py:146: pydantic_core._pydantic_core.ValidationError: 2 validation errors for TypeDef
  attrs.0  Input should be a valid string [type=string_type, input_value={'name': 'designator'}, ...]
tests/schemas/test_a7_discriminators.py:157: ValidationError: 1 validation error for TypeDef
tests/schemas/test_a7_discriminators.py:168: ValidationError: 1 validation error for TypeDef
tests/schemas/test_a7_discriminators.py:189: ValidationError: 1 validation error for TypeDef
```

### `tests/gates/test_g17_atom_mint.py` — G17, S1's clause only (4 FAILS-NOW + 4 guards)

Spec lines (plan §5 G17 + §7 RK-ATOMS "Gates" + §7 item 5):

> "Atoms are minted only at ingest and never inside `rebuild()`" · "RK-ATOMS authors the *atoms-minted-only-
> at-ingest* portion; **the no-mint/no-append-under-`rebuild()` clause is RK-LAYER's** and the id-from-atoms
> clause is **S4's**." · "`seed.py`-as-bundle-reader must **not** mint — it reads frozen bundles, and minting
> there would overwrite a frozen referent [and break KEYLESS≡LIVE]."
> "*Fixture must be non-vacuous* … a gate that cannot fail is a gate that lies." (§5a)

**Scope discipline:** this file deliberately asserts *neither* the no-mint-under-`rebuild()` clause (S2's)
*nor* the id-from-atoms/determinism clause (S4's). Failing S1 for work it does not own would be a false
signal.

| Test | Asserts | Now |
|---|---|---|
| `test_make_referent_id_exists_beside_make_claim_id` | the constructor exists **and** is defined in `chanakya.schemas.ids` | FAILS-NOW |
| `test_the_referent_mint_is_deterministic` | identical input ⇒ identical id (an RNG/clock atom breaks pure recompute). Explicitly asserts the constructor exists first, so the discovery fallback cannot make it vacuous | FAILS-NOW |
| `test_the_referent_mint_is_dormant_in_s1` | **negative direction** — AST scan: zero call sites anywhere in `chanakya/**` | FAILS-NOW |
| `test_the_bundle_reader_replays_a_frozen_atom_verbatim` | behavioural: a frozen `claim_id` the deterministic pass would never mint, plus a frozen referent, both survive `ingest_bundle` | FAILS-NOW |
| `test_the_id_constructors_are_rng_and_clock_free` | `schemas/ids.py` imports no `random`/`uuid`/`secrets`/`time`/`datetime` | GUARD |
| `test_the_claim_atom_mint_is_called_only_from_the_ingest_package` | every `make_claim_id` call site is under `chanakya/ingest/`; **also asserts the scan found ≥1 site**, so a broken scanner cannot pass vacuously | GUARD |
| `test_the_mint_scanner_flags_a_planted_violation` | the **negative control**: on a synthetic `tmp_path` tree the scanner catches a bare call *and* an attribute call, and does **not** fire on a docstring mention | GUARD |
| `test_the_bundle_reader_does_not_mint` | AST: neither `seed.ingest_bundle` nor `seed.seed_store_from_bundles` calls a mint or a dedup pass | GUARD |

Verbatim signature:

```
tests/_rk_atoms.py:81: AssertionError: chanakya.schemas.ids declares no make_referent_id — plan §4 A1:
'make_referent_id lives beside make_claim_id in schemas/ids.py'. Public names found: ['annotations',
'is_claim_id', 'make_claim_id', 're']
```

**Why the scan is AST-based and not a grep:** `make_claim_id` appears in eight docstrings across
`ingest/**`. A text scan would either count those (permanent false positives) or need an exclusion list.
The AST walker counts `ast.Call` nodes only, which the negative control proves.

### `tests/gates/test_s1_zero_behavioural_change.py` — scope item 5 (1 guard)

> "The derived graph must be **byte-identical** after S1." · "**The golden view is byte-identical to
> pre-S1** (the stage's headline invariant)."

`test_golden_view_fixture_is_byte_identical_to_pre_s1` pins
md5 `bb6f16a516c31eb0846494b62271a601` on `backend/tests/fixtures/golden/expected_view.json`. GUARD.

**Why the md5 is not redundant.** `tests/gates/test_g2_determinism.py` and `tests/view/test_rebuild.py`
already compare `view_to_json(rebuild)` to the committed fixture — but both compare *output* to *fixture*,
so both stay green if the **fixture is regenerated** to match changed behaviour. The md5 is the one
assertion that fails on a re-record. It is expected to be updated, with a ledger entry, by **RK-NAMECUT
(S4)**, which regenerates the golden by design; the failure message says so.

I deliberately did **not** pin the `1026 passed / 7 skipped / 1 xfailed` counts: this suite itself changes
them, so such a test would be self-defeating.

---

## Spec silences

Places where the spec did not determine an outcome and I asserted properties instead of inventing an
answer. **S-1 and S-2 want an orchestrator ruling; S-3 to S-6 are reported for the record.**

**S-1 — no identifier is fixed anywhere (the pervasive one).** The spec names the referent *field*, the
`make_referent_id` *constructor*, the four discriminator *dimensions* and the structured-attrs *entry*, but
never their spellings, and never `make_referent_id`'s signature. Writing tests from the spec alone
therefore cannot hard-code a name without testing my guess instead of the requirement. Handled by
`backend/tests/_rk_atoms.py`, which discovers:
* the referent field — any single `ClaimRecord` field whose name contains `referent` (preferring
  `referent_id` / `referent` / `referent_atom` / `referent_atom_id` if several match);
* the constructor — `chanakya.schemas.ids.make_referent_id`, called with signature-derived string
  arguments; on an unguessable signature it falls back to an opaque literal so the dedup tests still test
  dedup. `test_the_referent_mint_is_deterministic` asserts the constructor exists *first* so the fallback
  cannot make it vacuous;
* the four dimensions — generous per-dimension token sets in `DISCRIMINATOR_DIMENSIONS`, matched
  recursively through nested models (a discriminator on a nested structured-context model counts exactly as
  much as a flat one);
* the attrs entry's name — an accessor (`attr_names` / `attribute_names` / …) if the implementation exposes
  one, else the entry's `name` key/attribute.
**Residual risk:** an implementation using a name outside a token set fails a test that is actually
correct. Every such failure prints the tokens it looked for and the fields it found. If the implementer
picked, say, `unit_serial` for designation, widen the token set — do not weaken the assertion.

**S-2 — the dedup fold with two *different* referents (the one the brief already named).** §7 item 3 says
the referent must be "never silently orphaned or collapsed", but never says what the fold must **produce**.
I asserted only what holds under any correct choice — deterministic · no fabricated third value · nothing
lost without a trace — and `test_fold_of_conflicting_referents_loses_nothing_silently` explicitly accepts
**all** of: (a) the two mentions do not fold at all (a differing referent is differing content);
(b) the survivor retains both values in a collection; (c) one wins and the other is kept as a traceable
breadcrumb (e.g. in tier-3 `attributes`). It rejects only (d) one is kept and the other vanishes without
trace. **This is the single place I may be reading the spec more strictly than the implementer will**: (d)
is the obvious one-line implementation, and someone could argue a deterministic pick is not "silent".
My reading rests on the literal words "never silently … collapsed" plus the non-negotiable's traceability
corollary — a grouping signal that disappears with no record cannot be audited. **Orchestrator call.**

**S-3 — which mention schemas must carry which discriminator.** A7 says the four dimensions are "structured
claim **context**"; it does not say on which of the ~25 mention schemas. I made the hard assertion on
`UnitMention` only, on the reading that the discriminators exist to individuate the *instance-layer
citizen* (spine/13 §3a; D-13.20's ladder is about telling two co-located units apart), and left a softer
surface-wide coverage test for the rest. If the implementation puts the structured context on a shared
nested model referenced from the relation/event lanes but *not* from `UnitMention`, that test fails on a
placement the spec never forbade. Also note three of the four dimensions already exist today in flat form
(`service_branch`, `home_garrison`, `date_text`, `designators`), so the surface-wide test alone would be
near-vacuous — which is exactly why the `UnitMention` test is the one that bites.

**S-4 — whether the *claim-id* reference must survive the fold.** `dedup_within_doc` discards the
non-representative members and publishes **no** old→new map, so a premise pointing at a folded-away mention
dangles today (verified, signature above). Item 3's principle — "never silently orphaned" — is written about
the *referent* field; the spec never says the same must hold for a claim-id reference across the fold, and
fixing it would be a behavioural change in a stage whose headline invariant is *zero* behavioural change.
Recorded as a **non-strict xfail**, not an S1 requirement, so it stays visible without failing the stage.
This is a genuine latent hole in the substrate; suggest it goes to the roadmap or to S2/S3 explicitly.

**S-5 — "reconcile" is undefined for the remap.** §7 item 3 says dedup must "**carry/reconcile**" the
referent. "Carry" is clear; "reconcile" is not. I asserted the two unambiguous halves — the claim-id remap
must not blank the referent, and it must not rewrite the referent into a **claim** id even when the remap's
keys happen to include the referent's own value (namespaces must not cross). Any richer reconciliation the
implementation adds is compatible with both.

**S-6 — the structured-attrs entry shape is under-specified beyond the name.** *(Rewritten after the
2026-07-25 ruling — the compatibility half of this silence is now closed.)* **Closed:** the bare-string form
is illegal, so "must a bare string keep working?" is answered — no. **Still open:** whether the entry is a
model or a mapping, and whether the name key is spelled `name`. Handled by discovery (`attr_names`'s
accessor-then-`name` ladder). I assert **only** the attribute name — no other field — so S2 stays free.

**Withdrawn by the ruling, with one residual risk to note.** My `..._tolerates_an_unfamiliar_key` test is
deleted because the ruling forbids asserting anything about `layer` at S1. It had a second purpose the
deletion loses: it protected the S1→S2 seam ("design the entry so **S2 adds a field** and nothing else is
reshaped"). I judged the risk small — adding a field to a pydantic model *is* "S2 adds a field", and a
strict entry that rejects unknown keys is now the more consistent design under "one form only, loud errors"
— but it is no longer covered by a test, so **S2 owns it**. Flagged rather than smuggled back in.

**Not a silence, but worth stating:** `TypeDef.attrs` has **no code consumer today** — nothing in
`chanakya/**` reads it (verified; the only `TypeDef(` is the class definition). It is declarative only. So
the restructure cannot be validated through behaviour; the loader-level and file-level assertions above are
the whole of what is checkable at S1 — which is exactly why the migration net (round-trip + no-loss) is the
part that earns its keep.
