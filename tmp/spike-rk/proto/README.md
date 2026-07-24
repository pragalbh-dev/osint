# RK-SPIKE — `characterize-and-cluster` prototype

Throwaway prototype for spine/13 §13's **highest-risk piece**: how a provisional
instance is described richly enough to cluster cross-document, in what
discriminator priority, and how a thin-context bind degrades to *"under-determined
+ named gap"* rather than fabricating a unit or collapsing two.

Implements the four closed decisions — **D-13.17** (Tier-0 auto-bind by coref
category, behind a deterministic gate *and* a source-grade floor), **D-13.18** (the
referent atom as a grouping the rebuild may **decline**), **D-13.19** (same-document
stated contrast ⇒ a band ceiling at *probable*), **D-13.20** (the discriminator
ladder, composite AND-key identifiers, and the name/discriminator split).

Nothing outside this directory is touched. No production code is written.

---

## Run it

```
python3 tmp/spike-rk/proto/run.py --cases <input.json> --out <output.json>
```

Optional: `--config <path>` to point at a different config; `--expect <file>` to
diff the produced output against a frozen one and exit non-zero on any mismatch.

Pure standard library. Verified to run under `python3 -S -E` (no `site-packages`,
no environment): no API key, no network, no app boot, **no embeddings** (locked
project decision — the only signals used are alias/rarity, string similarity,
BM25-style term weighting, and relational/discriminator evidence).

The self-cases pass:

```
$ python3 tmp/spike-rk/proto/run.py --cases tmp/spike-rk/proto/self-cases.json \
      --out /tmp/out.json --expect tmp/spike-rk/proto/self-expected.json
OK: 14 case(s) match tmp/spike-rk/proto/self-expected.json
```

`self-cases.json` and `self-expected.json` are **authored by the implementer hand**
and are development shapes, not acceptance cases — entities are invented in a
neutral survey/hydrography domain. A separate test hand is independently authoring
acceptance cases from the same spec; this prototype has never seen them, and the
implementer has read no corpus, answer key, or gold data.

### Determinism

Verified: three runs under randomized `PYTHONHASHSEED` produce byte-identical
output (`md5sum` equal). No clock, no RNG; every list is sorted with a natural-sort
key (so `i2` precedes `i10`), floats are rounded to a configured precision before
emission, and the fixpoint iterates in sorted order.

### The self-checks that make the guarantees testable

Five sabotage tests, all caught (run in development, reproducible by editing the
config or monkey-patching the guard):

| Sabotage | Caught by |
|---|---|
| set the name weight above the probable floor | `scoring.invariants.name_alone_below_probable` at config load |
| make the stated-contrast ceiling liftable | load-time invariant |
| allow a name-derived confirm trigger | load-time invariant |
| write a cap as a float instead of a band name | load-time invariant |
| delete a rationale comment above any config leaf | the G6 rationale gate at config load |
| force `_drawable()` to always return True | `run.py::_assert_postconditions` → `AssertionError: D1 VIOLATION: relocation drawn for 'i1 + i3' whose identity is not confirmed` |

---

## The discriminator bag

Six slots, declared in `proto-config.yaml → discriminators.bag`, in D-13.20 ladder
order. Each is populated from a **configured list** of attribute names (the ontology's
own declared vocabularies) and/or from a **configured list of predicates**, never
from a hard-coded field.

| Slot | Populated from | Perishable | Multi-valued | Walls on conflict | Why it is in the bag |
|---|---|---|---|---|---|
| `unique_id` | the canonical values of **every** component of a configured composite AND-key, and only when all are present (default key: `(operator, designation)`) | no | no | yes | D-13.20's load-bearing call: a bare designator is not an identifier; `(operator, designation)` is. This is the only slot whose *match* lifts caps. |
| `designation` | `designator`, `unit_designator`, `base_designator`, `export_designator` | no | no | **yes — top rung** | The non-perishable formation discriminator; a designation persists through moves, which is what makes a formation a formation. |
| `operator` | `service_branch`, `operator_branch`, `operator`, `country`, `origin_country` | no | no | yes, **only post-normalization** | Namespace-level: necessary for identity, never sufficient. The most dangerous over-merge class for an operator-scoped OOB map (D4). |
| `geography` | the object of a placement predicate (`based-at`, `observed-at`, `deployed-at`, `located-at`, `garrisoned-at`), or `coordinates` / `home_garrison` / `location` / `site` | **yes** | **yes** | yes, **only at overlapping times**, and **pairwise never transitive** | spine/13 §7: a discriminator is attributes + relationships + derived geo. Agreement here is evidence about a moment, not about a referent. |
| `time` | the placement edge's `event_time` | yes | yes | **no** | Two different dates are a sequence, not a contradiction. It is the axis continuity is measured on. |
| `echelon` | `echelon`, `formation_level` | no | no | **no** | Discriminates weakly, and sources routinely describe one referent at different granularity ("battery" inside "brigade"), so walling here would shatter merges on a reporting-style difference. |

**`name` is deliberately NOT a bag member.** D-13.20's enabling change is splitting
`name` *out* of the discriminator channel (production fuses them at one `max`,
`resolve/scoring.py:437`); putting it back in the bag would undo the thing being
demonstrated. It is a third, separately-weighted signal.

### When the source is silent

An absent attribute stays absent through the whole pipeline. It renders as the
literal string `"unknown"` in the emitted bag and is **never** invented, defaulted
or `None`-filled. In addition, for the three slots listed in
`discriminators.gap_on_unknown_slots` (`designation`, `operator`, `time`), an
instance-layer citizen with the slot unset produces a named
`discriminator-unstated` gap carrying a literal analyst-facing sentence. Those three
were chosen because they are exactly the slots whose absence *structurally blocks a
confirm* — so naming them tells the analyst what collection would unblock the
assessment, which is the "insufficient evidence" contract rather than a shrug.

### Display vs comparison

The emitted bag shows the **stated** source value(s); every comparison runs on the
**normalized** form (transliteration → casefold → punctuation collapse → per-slot
equivalence class or ordinal folding). Provenance discipline: the analyst must see
what the source said, not what the normalizer made of it. Multiple stated values on
one slot are joined with a configured separator.

### Output conventions worth knowing

* **`referent_atoms` holds the atoms the rebuild actually used, plus one extra
  record per *declined* grouping.** So a declined 3-member cluster emits four rows:
  the declined grouping (with its reason) and the three claim-atom-granularity atoms
  it de-grouped to. A grouping held *loose* emits only the per-member atoms — it was
  never authoritative, so there was no grouping to decline; the `gate_results` on
  each member records which gate failed.
* **`authoritative` = the proposal cleared both Tier-0 gates. `declined` = the
  rebuild refused the grouping anyway.** An atom binds as one shared referent iff
  authoritative **and not** declined. Both flags are reported so "cleared its gates
  and was still declined" — the entire D-13.18 story — stays readable.
* **`ceiling` is non-null whenever a cap is in force**, even if the score landed
  below it anyway. The alternative reading ("only when it actually clamped") would
  make G16's own co-location cap invisible in exactly the weak-evidence cases it
  exists for. See FINDINGS B-note on the two readings.
* **A cross-type pair is emitted with a `type-incompatible` wall**, not skipped.
  Production treats it as a silent skip; every other rejection path in this design is
  required to be visible, and defect D2 is precisely a silent skip.
* `confirmed` means **the pair fused**. Everything else means it did not. Clusters
  are the transitive closure of `confirmed` pairs.

---

## The D1 guard — which line enforces it, and why it cannot be bypassed

Defect D1 is a verified chain from one identity over-merge to a **drawn,
positively-asserted relocation with the analyst removed from the loop**. Three
properties make it unreachable here:

1. **Fusion is structural, not scored.** `judge.Judge.band_from_score` returns
   `probable` at most, by construction. A pair reaches `confirmed` **only** if it
   holds a durable confirm trigger (`confirm.triggers`: composite-AND-key match,
   temporally-witnessed continuity, or corroborated designation) with source
   independence satisfied, no wall, and no ceiling below `confirmed`. Co-location,
   name similarity and relational overlap — the exact signals in D1's chain — produce
   no trigger, so no score can fuse them. `confirm.name_derived_triggers_allowed` is
   pinned `false` by a load-time invariant (R3.2).

2. **`drawn` is assigned in exactly one place.** `derive.relocation_edge()` computes
   it on its first line from `derive._drawable(status, cfg)`, which is the single
   expression `status == cfg["relocation"]["drawn_requires_identity_status"]` — a
   comparison against a config **status name**, not a number. There is no override
   argument, no second assignment to `drawn`, and no other function constructs a
   relocation edge. The withheld branch builds the edge **and** appends its gap in
   the same statement, so a withheld relocation cannot exist without a named,
   analyst-facing gap.

3. **The finished document is re-checked.** `run.py::_assert_postconditions` walks
   the emitted output and raises if (a) any drawn relocation's subject is not a
   confirmed identity, (b) any withheld relocation lacks a reason, or (c) any
   withheld relocation lacks a matching gap. A violating output cannot be written
   even if the derivation logic were changed. Verified by monkey-patching
   `_drawable` to always return True: the assertion fires.

Worked contrast in the self-cases: case **10-relocation-withheld** (two co-located
formation reports, no designation ⇒ no trigger ⇒ `possible`) emits
`drawn: false, withheld_reason: "identity sub-confirmed"` plus a
`relocation-unconfirmed` gap. Case **11-relocation-earned** (the same shape, but both
sources state the designation, so the composite key matches ⇒ `confirmed`) emits
`drawn: true`.

---

## Reuse vs new — what each prototype function would do to production

Anchors are `file:line` in `backend/chanakya/`, verified against the current code on
`design/resolution-redesign`.

| Prototype | Production counterpart | Verdict |
|---|---|---|
| `strings.normalize` / `tokens` / `sorted_form` / `name_similarity` | `resolve/normalize.py:30` / `:36` / `:42` / `:46` | **reuse as-is** — re-implemented here only to drop the `rapidfuzz` import at `resolve/normalize.py:13` so the prototype needs nothing installed. Semantics match. |
| `strings.jaro_winkler` / `_jaro` | `rapidfuzz.distance.JaroWinkler`, called at `resolve/normalize.py:57` | **reuse as-is** (the reference algorithm) |
| `strings.Rarity` (IDF + rarity-weighted Dice) | **nothing** — no `idf`/`rarity`/`tf-idf`/token-frequency code anywhere in `backend/chanakya`; blocking treats every name token as an equal key (`cluster.py:170-171`) | **new code** — D-13.2 and D-13.10 both rest on a "rarity-graded name" that does not exist |
| `characterize.Normalizer.canonical` (value equivalence classes + ordinal folding) | **nothing** — `normalize`/`transliterate`/`AliasIndex` apply only to `Entity.name`; conflict detection is bare `==` on raw attrs (`scoring.py:99-106`) | **new code** — the R5.2 prerequisite, and it must run before *both* conflict detection and namespace/key derivation (`entities.py:114-120` reads raw attrs) |
| `characterize.Mention` | `ingest/coref.py:157` `Mention{local_id, name, entity_type, claim_id}` | **extend** — add `attrs` and `contrast_group`; coref's mention shape carries neither |
| `characterize.Tier0.equivalence_gate` | `ingest/coref.py:258` `_quote_supported` (verbatim-in-document only) | **extend** — adds "quote contains both surface forms" + "quote contains a configured equivalence marker" |
| `characterize.Tier0.anaphor_gate` (type-unique antecedent) | **nothing** — categories are model-chosen and validated by set membership only (`coref.py:303-305`) | **new code** — this gate *is* the D-13.17 decision for `UNAMBIGUOUS_ANAPHOR`; without it the decision flips to raise-only |
| `characterize.Tier0.grade_ok` | the discipline exists at `resolve/__init__.py:490-529` (`_critical_attribute_walls`) + `scoring.py:134` (`_value_meets_grade_floor`) | **new code on the coref lane** — neither `ingest/coref.py` nor `_coref_pairs` (`resolve/__init__.py:614-661`) reads a source grade at all (defect D10) |
| `characterize.Builder.referent_atoms` | `ingest/coref.py:279` `valid_clusters` + `:342` `coref_claims` + `resolve/__init__.py:616` `_coref_pairs` | **extend** — the authoritative/raise-only routing exists; the *atom record*, the gate results and the injected-pair-with-quote are new |
| `characterize.Builder._decline_reason` | **nothing** — `Entity.attrs` is first-claim-wins (`entities.py:189` `setdefault`), so an intra-referent conflict is invisible; only `attr_history` (`entities.py:192-200`) retains the losing value | **new code** — D-13.18, and it must read the history, not the collapsed scalar |
| `characterize.Builder.instances` (the whole bag) | **nothing** — the judge's comparison surface is `Entity{eid, etype, name, attrs, claim_ids, source_ids, registry, attr_history}` (`entities.py:97-112`) with `attrs` a flat first-wins scalar bag | **new code** — this is the "characterize" half of the spike |
| `characterize.time_window` / `windows_overlap` | times exist on `AttrClaim` (`entities.py:73-81`) and feed succession (`scoring.py:104`), but there is no window/overlap test | **new code** — G18's "at overlapping times" needs it |
| `judge.Judge.slot_state` | `resolve/scoring.py:81` `attribute_is_conflict` (bare `==` at `:99-106`) | **extend** — adds the normalization gate and the third outcome `unnormalized` (untestable ⇒ no wall, raise a gap) |
| `judge.Judge.composite_state` | `resolve/scoring.py:207` `_shared_unique_id` (single attribute, and always `False` today because `hard_id_fields` is dead config) | **extend** — single attribute → composite AND-key, plus the conflict direction (cf. `_identifier_veto`, `resolve/__init__.py:460-485`) |
| `judge.Judge.geo_wall` | `resolve/scoring.py:49` `geo_conflict_km`, consulted at `cluster.py:360` | **extend** — adds the overlapping-time condition; keeps it pairwise/non-transitive, matching how it is actually wired |
| `judge.Judge.name_signal` | the name half of `attribute_score` (`scoring.py:395-399`) | **extend** — split out of `attribute_score`, plus rarity |
| `judge.Judge.discriminator_signal` | the attribute half of `attribute_score` (`scoring.py:414-437`), fused at the `max` on `:437` | **extend** — split out, and normalized by *total configured slot weight* rather than `agreeing/present`, so agreeing on one cheap slot no longer scores 1.0 |
| `judge.Judge.relational_signal` | `resolve/scoring.py:494` `relational_score`, keys at `:353` / `:371-373` | **extend** — adds the stated time to the neighbour key for placement predicates (see FINDINGS B5); F9 behaviour (only fused links carry weight) is retained deliberately |
| `judge.Judge.confirm_triggers` | `resolve/cluster.py:399` `has_durable_trigger` / `:418` `confirm_is_durable` | **replace** — those count exact-normalized-name as durable support (`cluster.py:418-428`), which is defect D3(b): name launders the perishable and co-location caps |
| `judge.Judge.band_from_score` | `resolve/cluster.py:81` `_band` + `:68` `_deterministic_total` | **extend** — the score must top out *below* fusion; production's `auto` band **is** the fusion |
| `judge.UnionFind` | `resolve/cluster.py:31` `_UnionFind` | **reuse as-is** |
| `judge.run_fixpoint` | the Phase-2 loop `resolve/cluster.py:467-496` | **extend** — same monotone-termination argument (`cluster.py:6-9`); the merge test becomes trigger-based instead of band-based |
| the ceiling machinery (`caps`, `protoconfig.lower_band`, `band_at_most`) | the two proven cap shapes: `perishable_capped` (`cluster.py:443`, `:478-496`, `:574-576`) and `name_alone` (`cluster.py:140`, `:558-568`) | **extend** — same shapes, but they must bind the **fusion** path, not only the queue band (defect D3(a)), and the config value becomes a band name |
| `derive.relocation_edge` / `_drawable` | `credibility/supersession.py:165-209` `promote_supersessions`, called at `view/pipeline.py:795` | **replace** — that path pops the pair out of the analyst queue and draws the edge whenever the targets differ, with no check on the underlying identity (defect D1, requirement R1.4) |
| `derive.gap` + `gaps.sentences` | `resolve/cluster.py:122` `_perishable_confirm_reason`, `:104` `_bridge_reason`, `resolve/__init__.py:532` `_critical_raise_reason` | **extend** — same prose-only, threshold-free idiom (G6-clean); new kinds plus a machine-readable `missing` list |
| `derive.derive`'s per-site formation count | `ingest/basing.py:301` truncation under `max_units_per_site: 1`, which appends no `SkipRecord` | **replace** — requirement R2.1: two candidates ⇒ two attributions or one plus a named gap, never a silent pick |
| `protoconfig` rationale + invariant gate | nothing — G6 is a test, not a loader check | **new code, prototype-only** — a device to prove the numbers were chosen by principle, not a production proposal |
| `run.py::_read_case` | `ingest/extract.py` pass 1 + `dedup.dedup_within_doc` (`dedup.py:201-228`) | **out of scope** — the prototype takes mentions as given |

---

## What the prototype does NOT model

1. **The verbatim-quote-in-document check.** Production already enforces it
   (`ingest/coref.py:258`). The I/O contract carries no document text, so the
   EXPLICIT_EQUIVALENCE gate here checks only its other two clauses.
2. **Per-layer policy profiles** (spine/13 §7). One profile — the instance-layer one —
   is applied to every layer. This has a real consequence, visible in cases 10/11/12:
   two mentions of the same depot name sit at `possible` and never fuse, because no
   confirm trigger exists that a place could satisfy. See FINDINGS B3.
3. **Source independence beyond distinct `doc_id`s** (defect D6). Two derivative
   reprints of one almanac are two doc ids here, so spine/04's
   source-independence / too-clean machinery is not modelled.
4. **Transitive veto closure.** All walls are pairwise. Production draws some vetoes
   into a transitive set re-applied in `finalise` (`cluster.py:363-370`, `:638-648`)
   and leaves others pairwise. The prototype is uniformly pairwise — the weaker choice.
5. **HITL.** No decision log, no override propagation, no redirect map, none of
   D-13.11's split mechanics. Gaps are *raised*; nothing adjudicates them.
6. **Blocking as a cost device.** All type-compatible pairs are compared
   exhaustively, so the prototype says nothing about the recall or cost of
   `_candidate_pairs` (`cluster.py:151-203`).
7. **The `count` attribute on a presence** (D-13.13 — the "two batteries" OOB figure).
   The input contract has no slot for it.
8. **Rarity against a real corpus.** IDF is computed over the case's own surfaces, so
   weights are noisy on small cases and would differ against a corpus-wide table.
9. **`operated-by`** (defect D7). The operator discriminator is attribute-only; there
   is no operator *edge*, so the relationship-conflict wall is demonstrated on
   `based-at` only.
10. **Cross-document referent atoms.** An atom is doc-local by construction, and the
    prototype does not emit fused instances — `instances[].doc_ids` is always one doc,
    and cross-doc identity lives only in the union-find over `confirmed` pairs.
11. **The design/anchor layer's own work** — edge derivation, materiality,
    chokepoints, coverage surfaces, freshness — all out of scope.
12. **Extraction quality.** spine/13 §13 (F6) notes the risk concentrates in
    extraction; the prototype takes coref proposals and discriminators as given
    inputs and says nothing about whether a model produces them well.
