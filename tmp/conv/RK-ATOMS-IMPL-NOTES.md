# RK-ATOMS (S1) — implementer notes (corpus-blind hand)

Branch `s1/rk-impl`, worktree `wt-RK-ATOMS-impl`, based on `design/resolution-redesign` @ 47af1e4.
Five commits, one per verifiable increment; the full suite + the golden md5 were run after **each**.

**Corpus-blindness held.** Nothing under `corpus/**`, `answer_key.json`, `SCENARIO_MANIFEST.json` or
`tmp/spike-rk/gold/**` was opened. Neither was `s1/rk-test` or any `backend/tests/**` file except the existing
`tests/gates/_srcscan.py` (read-only, for `PKG_ROOT`) and the one gate file this stage owns. Every threshold-ish
choice below is argued from a principle, not tuned — and there is exactly one number in the whole stage
(none: no threshold was introduced at all).

---

## 1. What was built

### Increment 1 — the claim atom named; the referent atom added, dormant (`4a38c37`)

* **`schemas/ids.py`** — rewritten module docstring stating the two atom levels and which one mints. The
  **claim atom is the canonical post-dedup `claim_id`**; the id present at `ClaimRecord` construction is
  explicitly documented as *provisional*. **No new id is minted.**
* `make_referent_id` / `is_referent_id` added beside the claim pair. `make_referent_id` **builds its stem with
  `make_claim_id`**, so the two schemes share one normalisation rule and cannot drift, under a `ref:` prefix.
  **Not invoked anywhere** (grep-verified) — referents are minted in S3.
* **`schemas/claim.py`** — `ClaimRecord.referent_id: str | None = None`.

**Why a prefixed namespace rather than an opaque UUID.** spine/13 §8 calls the referent "opaque", but the repo's
standing convention is human-readable ids (hallucination reduction in tool-calling + the one-click provenance
label). A `ref:` prefix keeps the house style *and* buys a real safety property: `is_claim_id(referent) is False`
and vice versa, because a claim id may not contain `:`. Two consequences fall out for free — a referent can never
be silently accepted where a claim atom is expected, and **a claim-id remap map can never rewrite a referent by
accident** (a claim map holds no `ref:` keys). Same reasoning that already prefixes `ent:` / `event:`.

**Grain of the field — a spec gap I had to close (see §4.1).** A1 says "on `ClaimRecord`/payloads". I put it on
`ClaimRecord` only: an entity-form claim bears the referent of the mention it names; a relationship/event claim
names two or more mentions and therefore has no single referent, so it stays `None` and its endpoints' referents
are reached through the existing tier-3 mention refs (`_subject_mention` / `_object_mention`, which already name
the endpoint *claims*). Two homes for one fact would be worse than one documented restriction.

### Increment 2 — dedup made atom-aware (`38eed12`), refined by the ruling (`9933944`)

* **`_claim_signature`** — the referent joins the signature, so a **differing referent blocks the fold**.
* **`dedup_within_doc`** — the group's single shared referent is carried onto the representative
  **explicitly** via `_folded_referent`, which **raises** if it ever sees a disagreement.
* **`remap_claim_refs`** — an explicit, opt-in `referents=` map. `assign_claim_ids` deliberately passes none.
* **`namespace_chunk_ids`** — new: one definition of the per-extraction-call namespacing that
  `lane._extract_doc_claims` and `seed._merge_chunks` previously spelled out in two near-identical loops.
* Docstring over-claim corrected; two residual defects recorded in-code (§3).

### Increment 3 — A7 structured discriminators, both sides of the seam (`1fe25bd`)

* **`ingest/extract.py`** — `MentionContext` (`operator` / `geography` / `designation` / `time`), added as an
  optional `context` block on the **seven entity-yielding** mention schemas: `OrgMention`, `UnitMention`,
  `VariantMention`, `ComponentMention`, `SiteMention`, `StockpileMention`, `TechDataMention`.
* **`schemas/config_models.py`** — `TypeDef.attrs` moves from `list[str]` to `list[AttrDef]`; `AttrDef` carries
  `name` + optional `discriminator`. `TypeDef.attr_names()` gives the old view.
  *(As first built, this also accepted the bare-string form and serialised a name-only entry back to a bare
  string, leaving `config/ontology.yaml` untouched. **A follow-up user directive removed that compatibility
  outright** — see §7, which supersedes both properties.)*

**Why one uniform shared block rather than ~15 new per-type fields.** The discriminators exist so the identity
judge can read them *structurally*. Scattering them as per-type fields (`service_branch` here,
`location_text` there, nothing on a component) would force S3 to carry a per-node-type field-name mapping — the
untyped-bag problem in new clothes, which is precisely what A7 is written against. One lane, one shape, one thing
for S3 to read. The overlap with existing type attributes is deliberate and harmless: `context` is the
*identity* restatement; the ontology attributes stay what they are.

**Why entity-yielding mentions only.** A discriminator's job is to tell two candidate **nodes** apart. A
relationship/event mention names two or more things (so a single context block would be ambiguous) and already
carries its own `date_text` / `location_text`. `SourceMention` is excluded because a source's identity is its
registry `source_id`, never a discriminated name. Stated in-code so the exclusions are auditable, not accidental.

**Why `discriminator` belongs in the ontology and not `resolution.yaml`.** The seam the session file draws is
*ontological* vs *identity semantics*. "This attribute states who operates the thing" is a fact about the
attribute's **nature** — the same kind of fact as S2's `layer` (design vs instance). "This attribute is
`critical` / `identifying`, and is `perishable` for *this* type" is a fact about how much identity weight it
carries — that stays in `attribute_roles` (per (type, attribute), per C6). Putting `discriminator` in
`resolution.yaml` would make the resolver config restate the ontology.

**~~Why the entry serialises back to a bare string.~~ SUPERSEDED by §7.** The original argument was that
`GET /config/ontology` returns `value.model_dump(mode="json")` straight onto the wire, so restructuring would
change an observable API response inside the stage whose invariant is that nothing changes. That is still true
as a *fact* — the GET response for the ontology section now carries structured entries — but the user directive
correctly ranks a one-time, single-form migration above wire-shape continuity on a config endpoint with no
consumer. No frontend consumer of ontology `attrs` exists (checked `frontend/src/**`), so nothing reads the
changed shape.

### Increment 4 — gate G17, atoms-minted-only-at-ingest (`7d36185`)

`backend/tests/gates/test_g17_atoms_minted_at_ingest.py`, five tests:

| Test | Asserts |
|---|---|
| `test_every_mint_call_site_is_under_ingest` | whole-package AST scan: only `chanakya/ingest/**` *calls* a mint fn |
| `test_no_rebuild_reachable_module_mints_an_atom` | the transitive intra-package import closure of `chanakya.view.pipeline` (34 modules) contains no mint call |
| `test_the_frozen_bundle_reader_does_not_mint` | function-level: `seed.ingest_bundle` / `seed.seed_store_from_bundles` mint nothing |
| `test_the_scanner_detects_a_violation` | **non-vacuity**: the detector fires on source that *does* mint, in both call forms; a `def`/`import` is not a mint; the one exemption is correctly scoped |
| `test_the_reachable_closure_is_not_trivially_small` | **non-vacuity**: the closure walk still reaches `resolve.cluster` / `credibility.status` / `schemas.ids` |

**Non-vacuity, done two ways.** The plan flags that a fixture-driven G17 passes vacuously whenever the fixture
happens not to reach the offending branch, so the scan is **static and input-independent** — an unexercised path
cannot dodge it. That inverts the vacuity risk (a *broken scanner* would now pass silently), which the last two
tests close. Beyond the tests, I verified it out-of-band by injecting `make_claim_id('d99','derived')` into
`chanakya/resolve/cluster.py`: **both** clauses failed, and both passed again on revert.

**The one exemption, and why it is safe.** `make_referent_id` calls `make_claim_id` to build its stem. A
constructor composing a constructor is not a mint — nobody gets an atom out of it — and the alternative
(duplicating the normalisation) is exactly the drift the shared stem prevents. The exemption is scoped to
`schemas/ids.py` **and** to calls lexically inside a mint constructor's own body, and the scoping itself is
asserted: a mint smuggled into any other function in that file still fails.

**Deliberately not built:** G17's no-`store.append`-under-`rebuild()` clause (S2) and its
ids-derive-from-atom-membership clause (S4). Worth recording for S2: `chanakya.store` is **not** in the
rebuild-reachable import closure today, so S2's clause starts from a clean base.

---

## 2. The dedup fold decision

**Decision: a differing referent BLOCKS the fold — the referent is part of `_claim_signature`.** The
conflicting-fold case is therefore *dissolved*, not adjudicated. (Independently reached and committed in
`38eed12`; the orchestrator's ruling arrived mid-stage and matched, so `9933944` only made the signature key
unconditional and recorded the residuals.)

**Reasoning.**

1. **It is a grouping decision, and grouping belongs to the rebuild.** A referent is the source's own stated
   grouping of its own mentions. Two claims with the same stated content but different referents means coref read
   them as two different things; folding them and keeping one referent *asserts that those two referents are one*.
   D-13.18 puts that decision at rebuild, never at ingest. Dedup's job is mechanical de-duplication of identical
   mentions — it has no business deciding identity.
2. **The two errors are not symmetric.** The evidence log is append-only and a claim atom never splits, so an
   over-fold destroys a distinction the source made **permanently**, with no analyst in the loop. An under-fold is
   fully recoverable: the rebuild can still group two claim atoms into one node, and being a *derived* grouping it
   can be challenged and undone. When one direction is irreversible, err the other way — the same asymmetry
   behind "the rebuild may decline a grouping".
3. **Picking a winner would be input-order dependent.** `min(members, key=_earliest_docref_key)` returns the
   *first* minimal element and phase 1 of the live lane is a concurrent fan-out, so "one wins" would inherit
   nondeterminism into the identity substrate — against G2 and pure recompute.
4. **It matches the direction this pass already errs in.** The signature is deliberately a *superset* of the
   minimal key so it keeps claims apart rather than silently dropping a distinct assertion.

**Alternatives rejected:** *first-wins* (silent evidence drop + nondeterministic — this is the exact orphaning the
stage exists to prevent); *fold and blank the referent* (silently discards coref's work, and the loss is
unrecoverable because atoms never split); *keep a set of referents on one claim* (makes the per-mention grain
ambiguous precisely where S4 keys identity off it).

**Made explicit in code, not incidental.** `_folded_referent(members)` is called and its result passed in the
`model_copy` update, even though the representative already holds the right value. And its disagreement branch
**raises** rather than blanking or picking: unreachable while the signature includes the referent, so if a future
change drops it the failure is loud instead of a silent identity fusion.

**Inertness at S1 was verified, not assumed.** The ruling says a uniform `None` "adds nothing to the signature".
Grouping-wise that is trivially true (a constant key preserves equality classes), but the signature string is
also a **sort tiebreak** in both `dedup_within_doc` and `assign_claim_ids`, and the golden path never runs dedup
at all (`ingest_bundle` reads frozen bundles via `model_validate`) — so a byte-identical golden view is
corroboration, not proof. Argument: inserting the same key/value at the same `sort_keys` position in two dicts
leaves the first point of divergence between their JSON exactly where it was. Checked with a randomised sweep:
**zero order flips over 20 000 random signature-shaped pairs.** Behaviour spot-checked directly: same referent →
folds (1 claim, 2 spans); different referents → 2 claims; `None` vs set → 2 claims; both `None` → folds exactly
as pre-S1.

---

## 3. Residual defects recorded (pre-existing; NOT fixed here)

Both are written into `dedup_within_doc`'s docstring for whichever stage next owns the module, and the
docstring's over-claim that "the pass is itself order-independent" is corrected to name what actually is
(the output ordering and the `doc_ref` union) and what is not.

1. **The representative choice leaks input order.** `min()` returns the first minimal element, so on a
   `_earliest_docref_key` tie every field the signature deliberately excludes (`claim_id`, `resolved_ref`,
   `extraction`, `report_time`/`ingest_time`) is decided by arrival order — and phase 1 is a concurrent fan-out.
   Harmless today (those fields are per-document constants and `assign_claim_ids` restamps `claim_id` right
   after), but it is real nondeterminism under the identity substrate. Fix = make the choice **total** with a
   deterministic final key (e.g. the pre-dedup construction id), not lean on `min`'s tie behaviour. Not
   attemptable in a stage whose invariant is a byte-identical view.
2. **A fold can orphan an inbound claim-id reference.** Folding b into a drops b's id, but `assign_claim_ids`
   runs *after* and builds its remap only from survivors, so another claim's `premises` / `targets` / endpoint
   mention ref pointing at b dangles instead of redirecting to a. The fold needs to contribute a b→a entry.

---

## 4. What I believe the spec got wrong or under-specified

### 4.1 A1's "`ClaimRecord`/payloads" has no answer for a relationship claim (closed as above)

A referent is per *mention*. A `Triple` names two mentions, so a record-level scalar cannot address both. The
plan never says which. Resolved by restricting the field's meaning to entity-form claims and routing endpoint
referents through the existing mention refs — documented at the field. **If S3 needs a referent per endpoint on
the relationship claim itself, this is the decision it must revisit**; it is a one-field change, not a reshape.

### 4.2 A7's "structured claim context, not buried in the untyped `attrs` bag" has **no carrier on the claim**

This is the sharpest gap. S1's scope adds discriminator fields to the *extractor's mention schemas* and the
*ontology's attribute declarations* — but `ClaimRecord` has only `payload.attrs` (tier-2) and `attributes`
(tier-3), both untyped bags. So as scoped, a discriminator the model fills has **nowhere typed to land**: it
either dies at the transform boundary (what happens today — nothing reads `context`) or gets written into the
very bag A7 says not to use.

The reading that makes S1 coherent is that the *structured `TypeDef.attrs` entry* is the typing: an attr named in
the ontology with `discriminator: operator` is no longer untyped, it is *declared*, so `EntityDescriptor.attrs`
becomes a declared surface rather than a free-for-all. I built to that reading and it is defensible — but it is
an interpretation, not what the plan says, and **S3 must decide explicitly** whether the discriminators travel
as declared ontology attrs or need a typed claim-side field. Flagging rather than pre-empting: adding a claim
field nobody reads would be the new abstraction layer this stage was told not to build.

### 4.3 `TypeDef.attrs` has **no production consumer at all** today

Verified by grep across `chanakya/`, `tests/` and `eval/`: nothing reads it (`ontology.py` and `extract.py` read
only `TypeDef.name`; `resolve/` gets its attribute vocabularies from `resolution.yaml`'s `attribute_roles`). So
the restructure is currently pure declaration. That is fine for a schema stage, but the plan's framing implies
`attrs` is load-bearing, and it is not — **S2 will be the first consumer** (via `layer`). Worth knowing before
S2 assumes there is an existing accessor to extend.

### 4.4 The recorded baseline command does not print the number it promises

`cd backend && python3 -m pytest -q` yields **no summary line**: `pyproject.toml` `addopts` already contains
`-q`, so the CLI flag makes it `-qq` and pytest suppresses the count. The baseline figure is real (verified via
`python3 -m pytest`, and `--collect-only` reports 1034 = 1026 + 7 + 1), but the stated invocation cannot show it.
Later stages should record `python3 -m pytest` (addopts supplies `-q`).

### 4.5 A minor factual drift in the session file

Session `RK-ATOMS.md` §5 lists `ingest/seed.py` as a canonical-id **remap** site "(recorder)". `seed.py` does not
call `remap_claim_refs` for canonical minting — it namespaced provisional chunk ids (now via
`namespace_chunk_ids`) and delegates canonical minting to `dedup.assign_claim_ids`. The `grep 'ClaimRecord('`
expectation itself was exact: constructed in `extract/coref/basing/attribute/imagery` + the `schemas/claim.py`
definition (7 call sites), remapped in `dedup.py` / `lane.py` / `seed.py`, and `seed.py`-as-bundle-reader mints
nothing (now gate-asserted).

---

## 5. Reuse vs new

| Site | Verdict | Note |
|---|---|---|
| `schemas/ids.py:19` `make_claim_id` | **reuse as-is** | untouched logic; `make_referent_id` composes it for the shared stem |
| `schemas/ids.py:33` `is_claim_id` | **reuse as-is** | now also the disjointness witness against `is_referent_id` |
| `schemas/ids.py:1-31` module docstring | **extend** | names the two atom levels; no code change |
| `schemas/ids.py:37,40` `REFERENT_PREFIX`, `_REFERENT_ID_RE` | **new code** | mirrors `_CLAIM_ID_RE`'s shape |
| `schemas/ids.py:71` `make_referent_id` | **new code** | thin wrapper over `make_claim_id`; **uninvoked** |
| `schemas/ids.py:86` `is_referent_id` | **new code** | mirrors `is_claim_id` |
| `schemas/claim.py:138` `ClaimRecord.referent_id` | **new code** | one optional field; `claim_id` documented as the claim atom in place |
| `schemas/base.py` `Record` (`extra="forbid"`) | **reuse as-is** | optional default is what keeps frozen bundles loading |
| `ingest/dedup.py:143` `_claim_signature` | **extend** | one key added; conditional-vs-constant settled by the ruling |
| `ingest/dedup.py:182` `remap_claim_refs` | **extend** | one optional kwarg; existing three ref channels untouched |
| `ingest/dedup.py:223` `namespace_chunk_ids` | **new code** | but *replaces* two duplicated loops — net reuse |
| `ingest/dedup.py:254` `_folded_referent` | **new code** | the fold decision, made explicit + loud |
| `ingest/dedup.py:328` `dedup_within_doc` fold | **extend** | one key in the `model_copy` update |
| `ingest/dedup.py:281` `assign_claim_ids` | **reuse as-is** | docstring only — the referent is carried, never rewritten |
| `ingest/lane.py:208` `_extract_doc_claims` | **extend** | 6-line loop → one `namespace_chunk_ids` call |
| `ingest/seed.py:190` `_merge_chunks` | **extend** | same; the two paths now share one definition |
| `ingest/extract.py:129` `MentionContext` | **new code** | one shared submodel, not ~15 per-type fields |
| `ingest/extract.py` × 7 mention classes | **extend** | one optional `context` field each |
| `ingest/extract.py` transforms (read-by-key) | **reuse as-is** | why the addition is inert: nothing reads `context` |
| `schemas/config_models.py:38,41` `DiscriminatorClass`, `AttrDef` | **new code** | `AttrDef` extends `ConfigModel`, so `extra="allow"` still applies |
| `schemas/config_models.py:100,113` `TypeDef.attrs`, `attr_names` | **extend** | `attr_names()` mirrors the existing `from_types()`/`to_types()` |
| `config/ontology.yaml` | **migrated** (§7) | all 13 `attrs` lists → 81 `- {name: X}` entries; name-only, no `layer`/`discriminator` values |
| `tests/gates/_srcscan.py` | **reuse as-is** | imported `PKG_ROOT` only; not edited (avoids colliding with the test hand) |
| `tests/gates/test_g17_…py` | **new code** | AST scanning modelled on the existing G6/G9/G10/G11 gates |

---

## 6. Verification — verbatim (as of the original four increments; §7 carries the post-migration run)

`cd backend && python3 -m pytest -q` — note that `pyproject.toml` `addopts` already carries `-q`, so this is
effectively `-qq` and **pytest suppresses the summary line**; the summary-bearing run follows.

```
........................................................................ [  6%]
.................s..........s........................................... [ 13%]
........................................................................ [ 20%]
........................................................................ [ 27%]
........................................................................ [ 34%]
............................................................s........... [ 41%]
.................ss..................................................... [ 48%]
........................................................................ [ 55%]
......................................................ss................ [ 62%]
........................................................................ [ 69%]
........................................................................ [ 76%]
........................................................................ [ 83%]
........................................................................ [ 90%]
........................................................................ [ 97%]
....................x..........                                          [100%]
```

`cd backend && python3 -m pytest` (last line):

```
1031 passed, 7 skipped, 1 xfailed in 30.87s
```

**1031 = the recorded 1026 baseline + the 5 tests of the G17 gate this stage was asked to author.** Skips (7)
and xfails (1) are unchanged, and there are no new failures. Confirmed by scope:

```
$ python3 -m pytest --ignore=tests/gates/test_g17_atoms_minted_at_ingest.py
1026 passed, 7 skipped, 1 xfailed in 30.48s
```

`md5sum backend/tests/fixtures/golden/expected_view.json`:

```
bb6f16a516c31eb0846494b62271a601  backend/tests/fixtures/golden/expected_view.json
```

The golden file was never edited; `tests/view/test_rebuild.py` and `tests/gates/test_g2_determinism.py` assert
the rebuilt view byte-for-byte against it, so both invariants hold at full strength. `ruff check chanakya/
tests/gates/` reports only the 3 pre-existing findings (2 in `view/coverage.py`, 1 in `test_g2_determinism.py`)
— none in a file this stage touched.

---

## 7. Follow-up ruling — the bare-string `attrs` compatibility is GONE

**User directive, after the four increments above were merged (`114a0f6`).** Remove the legacy bare-string
`attrs` tolerance entirely — do not keep it, do not defer it to S2. Rationale, and I think it is the right
call: a dual-form loader biases every later implementer toward the old shape, and a "temporary" tolerance left
in place is exactly how `config/ontology.yaml` never migrates and the data never bends to the design
(working-principles #1). One form only. My original wire-shape-continuity argument (§1, struck through)
optimised the wrong thing — it protected a config endpoint with no consumer at the cost of leaving two shapes
alive in the substrate.

Branch rebased onto `design/resolution-redesign` first; the rebase **fast-forwarded**, because S1 had already
been merged at `114a0f6` — so `s1/rk-impl` and the design tip were identical going in, and this change sits on
top of the merged S1 plus the test hand's merged tests.

### What was migrated

* **`config/ontology.yaml` — all 13 `attrs:` lists → 81 `- {name: X}` entries**, one attribute per line.
  Name-only: **no `layer` values** (that is A2/RK-LAYER/S2's job) and no `discriminator` values (nothing has a
  live query behind it yet, and absence must keep reading `unknown`).
  * **Why one-per-line flow maps** (`- {name: designator}`) rather than a single long flow list: S2 adds
    `layer` as a *second key on each entry*, so `- {name: designator, layer: instance}` stays one readable line,
    whereas `attrs: [{name: a, layer: x}, {name: b, layer: y}, …]` on the 9-attribute `variant` type would be
    a 200-character line. Block form (`- name: X` / `  layer: Y`) would double to two lines per attribute.
  * Migration was mechanical and **checked, not eyeballed**: the per-type attribute-name lists are identical
    before and after; every non-`attrs` key in the file is unchanged; and all inline comments are preserved
    (diffed the sorted comment set — including `techdata_authority`'s `# holds ∈ TDP | …`, which moved onto the
    `attrs:` line).
* **`schemas/config_models.py` — deleted `_accept_bare_name` and `_dump_bare_name`**, plus the three now-unused
  pydantic imports. A bare string in `attrs` is now a loud `ValidationError`
  (`Input should be a valid dictionary or instance of AttrDef`), never a silent coercion. Docstrings on
  `AttrDef` and `TypeDef.attrs` rewritten to state that there is deliberately no compatibility and why.
* **`config/ontology.yaml` header** — a new block stating the one legal form, that the loader rejects the other,
  that `layer` is S2's second key on each entry, and that identity *semantics* stay in `resolution.yaml`. The
  seam is now documented where a config author will actually read it, not only in the schema.

### The sweep — what else depended on the bare form

Grepped every YAML/JSON in the repo for an `attrs` key, and all of `backend/`, `eval/` for anything
constructing or validating a `TypeDef` / `OntologyConfig`. Result: **nothing in production or in any fixture
relied on the bare form.** Specifically:

| Candidate | Verdict |
|---|---|
| `config/ontology.yaml` | the only real `TypeDef.attrs` data — **migrated** |
| `backend/tests/fixtures/golden/config/ontology.yaml` | declares **no** `attrs` at all — nothing to migrate |
| `config/subjects.yaml`, `config/credibility.yaml` (+ their golden-fixture copies) | different fields — `materiality_attrs`, `gated_attrs`, `fingerprint_attrs`. Unaffected |
| `corpus/**/claims/*.json`, `tests/fixtures/**`, `tmp/**` snapshots | `EntityDescriptor.attrs` / view-node `attrs` — a `dict`, an unrelated field. Unaffected |
| `config_models.py:265` `EntityEntry.attrs` (`entities.yaml`) | a `dict[str, Any]`. Unaffected |
| `tests/resolve/test_t3b_fragmentation.py` | constructs `TypeDef`s with **no** `attrs`. Unaffected |
| `tests/schemas/test_a7_discriminators.py`, `tests/_rk_atoms.py` | the **other hand's** files — see below |

### Ownership deviation — recorded, not silent

`config/ontology.yaml` is nominally **RK-LAYER/S2's single-owner file** (plan §3 item, "single-owner S2/RK-LAYER
— not contended"). Editing it from S1 is a **deliberate, user-directed exception**. S1→S2 is strictly serial, so
there is no concurrency risk and no one else is holding the file — but S2 must know that its file arrived
pre-migrated, and that its remaining job there is to add `layer` to each of the 81 entries, not to restructure
them. Logged here rather than assumed.

### Three failing tests, on the other hand's branch — deliberately untouched

The compatibility that was removed is asserted by three tests in `tests/schemas/test_a7_discriminators.py`
(the independent test hand's file, merged at `9f070a6`). The coordinator named one; there are in fact **three**,
all the same concern, all in that one file:

```
FAILED tests/schemas/test_a7_discriminators.py::test_typedef_still_accepts_the_old_bare_string_attrs_form
FAILED tests/schemas/test_a7_discriminators.py::test_attribute_names_read_the_same_from_either_form
FAILED tests/schemas/test_a7_discriminators.py::test_mixed_bare_and_structured_entries_in_one_type_still_read
```

Per instruction I did not touch them. Note also that the same file's
`test_the_real_config_ontology_yaml_still_loads` (~:195) is *documented* as "config/ontology.yaml is untouched in
S1" — it still **passes**, because the file still loads, but its stated premise is now false and its docstring
will mislead the next reader. Worth folding into whatever you do with the other three.

### Verification — verbatim

1. **Full suite** (`cd backend && python3 -m pytest` — not `-q`, per the pitfall in §4.4), last line:

```
3 failed, 1091 passed, 7 skipped, 2 xfailed in 31.79s
```

The 3 are exactly the bare-form assertions listed above; nothing else regressed. The golden-view and
determinism gates specifically:

```
$ python3 -m pytest tests/view/test_rebuild.py tests/gates/test_g2_determinism.py
8 passed in 0.97s
```

2. **Golden md5** — unchanged, file never edited:

```
bb6f16a516c31eb0846494b62271a601  backend/tests/fixtures/golden/expected_view.json
```

3. **Real-corpus view check** (the one that matters here) — identical to the pre-migration baseline I captured
before touching anything, so this was a pure shape change and not a change of meaning:

```
160 73 22d668a348430df091b71aa0ff53650f8b1be0ba9d95ab88b9034368d6dac3a9
```

`ruff check chanakya/` is back to the 2 pre-existing findings in `view/coverage.py`; `config_models.py` is clean.
Spot-checked directly that the real ontology still loads with all **81** attributes intact across the three type
families, that `unit.attr_names()` is unchanged, and that `TypeDef.model_validate({"attrs": ["echelon"]})` now
raises.
