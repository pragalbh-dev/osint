# RK-COREF (S3) — implementer notes (corpus-blind hand, `s3/rk-impl`)

Eight commits on `s3/rk-impl` off `design/resolution-redesign` @ `cebf5d3`. **1220 passed / 7 skipped / 2
xfailed** (baseline 1184 + 36 new), ruff clean.

Every threshold, cap, floor, ceiling, category list and vocabulary this stage adds is **config**. I introduced
**no** numeric literal into `resolve/` or `ingest/`, and ruling M1's fourth conjunct deliberately reuses the
shipped `containment_min_descriptor_len` rather than declaring a second threshold for the same idea (G6).

---

## 1. The flag, and where it lives

**`earned_identity.enabled` in `config/resolution.yaml`, shipping `false`.** One flag, mirroring S2's
`layer_routing.enabled`, read through exactly one accessor (`ResolveConfig.earned_identity_on`) so the
boundary is testable in one place. Compiled by `EarnedIdentity.from_resolution` (`resolve/rconfig.py`).

The flag gates **both** of coreference's off-switches, which is what makes "two switches, one deliberate
motion" real rather than nominal:

* the **producer** (`config/credibility.yaml → coreference`) is now declared and populated — it was commented
  out on the stated condition *"turn it on together with that honor policy, not before"*, and S3 **is** that
  policy — but `coref._coref_cfg` returns `{}` unless the stage flag is on;
* the **consumer** — `coref_authoritative_evidence` stays shipped-empty as the legacy operator opt-in, and
  S3's policy (`earned_identity.authoritative_categories`) is read only while the flag is on.

**Why the producer is subordinate to the flag rather than standing alone.** Turning it on bare costs a
*second extraction call per document*, which broke **32 scripted-client tests** in files this stage does not
own. That is not a test-fixture inconvenience — it is proof the change is behavioural on the **ingest** path,
and the flag boundary has to cover ingest too or a flag-off re-extract stops reproducing the frozen bundles
and the dual-run baseline evaporates.

### Flag-off proof, both surfaces

| surface | measured | baseline | verdict |
|---|---|---|---|
| golden fixture md5 | `bb6f16a516c31eb0846494b62271a601` | same | unchanged, never edited |
| booted app | `160` nodes / `73` edges / `18` gaps, view sha `7af5307a0ce6` | `160/73/18 @22d668a3…` | unchanged |
| full scenario (`eval.harness`) | `169 / 80 / 71 / 20`, view sha `5e7e535ccca8` | `169/80/71/20` | unchanged |
| suite | 1220 / 7 / 2 | 1184 / 7 / 2 + 36 new | no pre-existing test moved |

Measured after **every** commit, not only at the end.

**Flag-on determinism (G2), checked too:** two consecutive rebuilds are byte-identical, and the view hash
`6b5400afbff6` is unchanged under `PYTHONHASHSEED` 1 / 7 / 99. The fixpoint's monotone-termination argument is
untouched — none of the new mechanisms feeds a score back into the loop; the caps only ever *withhold*.

**mypy:** 6 pre-existing errors on the base tree (`view/basing.py`, `ontology.py`, `view/pipeline.py`'s
`_seen_gaps` comprehension); I introduced one and fixed it. No new type errors.

---

## 2. Flag-on delta, item by item — predicted, then verified

Full-scenario surface, flag on: **183 nodes / 100 edges / 71 events / 22 gaps**, view sha `6b5400afbff6`.
Partition: `same_as` **66 → 52**, `candidates` **19 → 43**, `possible` 355 → 355, `distinct_from` 57 → 57.

**Fragmentation went UP by 14 nodes. That is the honest result and I did not loosen anything to change it.**
Read §3 before reading it as a failure.

| # | item | predicted | verified |
|---|---|---|---|
| 1 | coref promoted to a required tier, referent minted | **no effect on this corpus** — the bundles predate the producer | ✔ measured: **0 `coref-same-as` claims, 0 referent ids** in all 492 frozen claims |
| 2 | D-13.17 auto-bind policy + gates + grade floor | no effect (no coref input) | ✔ zero binds; proven on 14 fixtures |
| 3 | D-13.18 decline | no effect (no groupings) | ✔ zero declines; proven on 3 fixtures |
| 4 | Tier-1 same-doc + contrast lane | no effect (no contrast claims) | ✔ zero; proven on 2 fixtures |
| 5 | name/discriminator split | **no score moves** (`max` of a decomposition) | ✔ view sha identical before/after that commit alone |
| 6 | discriminator ladder + composite AND-key | no effect — the corpus states no `designator`+`service_branch` pair | ✔ 0 `unique_id_keys` matches |
| 7 | co-location cap (G16) | **fires**: the corpus has co-located formations sharing an induction | ✔ **4 pairs capped** (`inducted-into` ×2 pairs, `based-at` ×1, +1 across passes); `unit` merges 9 → 7 |
| 8 | relationship wall (G18) | **no effect** — one stated basing, no `operated-by` data | ✔ 0 walls, 0 third-state raises |
| 9 | G19 cross-ns / cross-type non-fusion | **fires**: the alias-reflexivity hole was live | ✔ **2 cross-type merges closed** (`known_gap`↔`component`, `variant`↔`component`) |
| 10 | caps bound to the Phase-1 bootstrap | **fires**: name is a verdict in Phase 1 at every type | ✔ **15 bootstrap triggers refused** (8 containment, 7 exact-name) |
| 11 | `places.augment` ordering | no new merges; scaffolding now live | ✔ node count unchanged, view sha changed — the relational term now sees place merges |
| 12 | residual fragmentation as a `/coverage` gap | already reported via `coverage_gap_ratio` | ✔ 7 types flagged; the report now also names the three ceilings |

---

## 3. Fragmentation: before/after, and every merge class justified as earned

**`same_as` 66 → 52. All 14 accounted for, by type-pair, and no threshold was loosened — not one. I did not
change a single band, floor, weight or ratio anywhere in this stage.** (`auto_merge` 0.85, `hitl_low` 0.45,
`possible_floor` 0.25, `auto_merge_by_type` 0.37, `relational_support_k` 2, `critical_veto_min_grade` C are
all byte-identical to the values S2 shipped.) Every number I added is a *new* knob with a *new* name.

| lost | type-pair | mechanism | why it is EARNED |
|---|---|---|---|
| 1 | `known_gap` ↔ `component` | G19 cross-type | a **system/meta** node was fused with a design node. There is no reading on which a Known Gap is a piece of equipment |
| 1 | `variant` ↔ `component` | G19 cross-type | exactly the review's finding: one designator declared a `component` by one document and a `variant` by another, fused in **Phase 1** at 1.0 through the reflexive alias branch, past every band |
| 2 | `source` ↔ `source` | name cap on the fusion path | the shipped config states the intent outright: `source` is *deliberately excluded* from `auto_merge_by_type` because cross-account persona links "sit right among the genuine ones, so that stays a HITL call". They were auto-merging anyway. The policy the config already declared now actually binds |
| 5 | `area_of_operations` ×5 | name cap on the fusion path | the ontology declares `identity.relational: false` for areas, so an area pair is name-only *by construction*, and T3b's own note says the resolver was wrongly treating "an AD Centre, a sector and a coastal belt" as duplicates. It was **merging** them, which is worse than queueing them. See the objection in §5.1 — this is the one I want a second opinion on |
| 1 | `basing_site` ↔ `basing_site` | name cap | two site mentions with a similar name, no shared neighbour, no agreeing attribute. A map that fuses two places on a name coincidence is the T2 bug class |
| 1 | `component` ↔ `component` | name cap | ditto, on parts |
| 1 | `trading_org` ↔ `trading_org` | name cap | ditto. Note **`manufacturer` merges are 16 → 16** — every one of the four evidence-checked spelling-variant merges the per-type floor was tuned for survives, because they carry relational or discriminator support. The cap is a cap, not a ban |
| 2 | `unit` ↔ `unit` | co-location cap (G16) | the anti-fabrication case. `based-at` is functional and unit-keyed, so fusing two co-located batteries makes their two sites *one unit's before-and-after*; the supersede path then draws a relocation nobody reported, pops the pair out of the analyst's queue as machine-adjudicated, and deletes the retired edge's Known Gap |

**And the compensating direction:** `candidates` 19 → 43. Twenty-four pairs that previously either merged
silently or dropped silently now reach the analyst **with a reason**. That is the recall-biased-triage
direction, and it is where the withheld merges went — not into a void.

### Why fragmentation does not RESOLVE here, and why that is not a threshold problem

The session file is explicit that S3 is where per-mention fragmentation must resolve. It does not, on this
corpus, and the cause is measurable rather than arguable: **there are zero coreference annotations and zero
referent ids in all 492 frozen claims.** The mechanism that resolves fragmentation is coreference binding, and
it has no input. Ruling M4 predicted exactly this ("three fixture families are untestable *in principle*").

The two levers that could have resolved fragmentation *without* coref are both measured weak on this data:

* **lever 2 (place anchors)** — the ordering bug is fixed and the scaffolding is live, but it rescued **zero**
  name-capped pairs here: no capped pair had a gazetteer-resolvable site pair to gain a neighbour from;
* **the discriminator ladder** — the composite AND-key is declared and wired, and matches **nothing**,
  because the corpus states essentially one numbered formation and zero serials.

**The one thing I will not do is lower a floor to make the number go down.** Every refusal above is a refusal
on *stated grounds* with an analyst-visible reason. Fragmentation resolving requires a corpus with coreference
in it (RK-DATA's re-record), not a looser judge — and the second I traded a threshold for a node count I would
be shipping the name-collapse bug with a different label on it.

---

## 4. Reuse vs. new

| `file:line` | what | verdict |
|---|---|---|
| `resolve/cluster.py:443-497` `perishable_capped` | block-merge-and-review shape | **reuse** — the co-location cap, the name cap and the two third states are the 3rd–6th instances of one proven shape, not new machinery |
| `resolve/__init__.py:_critical_attribute_walls` | walls/raises split | **extend** — C7's third state and C6's constitutive difference join the existing `raises` channel |
| `resolve/cluster.py:_band` / `_name_alone` | banding | **extend** — `_name_alone` reads the sub-signals when present, the fused term otherwise |
| `resolve/scoring.py:attribute_score` | fused attribute term | **extend** → `attribute_signals()`; `attribute_score` is now `max()` of it, byte-identical |
| `resolve/aliases.py:AliasIndex.equivalent` | alias class test | **extend** — `require_distinct_forms` |
| `ontology.py:LayerRouting.normalise_tag` | site-class vocabulary | **reuse** — C1 is "one declaration, two consumers"; a second vocabulary would drift from the supersede key's |
| `resolution.yaml:185` `containment_min_descriptor_len` | mark-vs-word | **reuse** — ruling M1's conjunct, one threshold for one idea |
| `resolve/places.py:augment` | place merges | **extend** → `place_merge_pairs()`; `augment` consumes it unchanged |
| `credibility` grade floor / `grade_meets_floor` | STANAG floor | **reuse** — the coref bind floor is the same letter as `critical_veto_min_grade`, deliberately |
| `resolve/__init__.py:_relationship_walls` | G18 | **NEW** — the judge had no relationship rail at all |
| `resolve/__init__.py:_referent_conflict` / `_history_conflict` | D-13.18 decline | **NEW** |
| `ingest/coref.py` gates (`explicit_equivalence_gate`, `unambiguous_anaphor_gate`, `differs_only_by_a_mark`) | D-13.17 / M1 / M2 | **NEW** — `coref.py` was a prompt, not a matcher; there was no structural detector to lean on |
| `ingest/coref.py:stamp_referents` / `contrast_claims` | A1 mint, D-13.19 lane | **NEW** |
| `entities.py` `Entity.doc_ids` / `Edge.doc_ids` / `earliest_iso` / `kind` | carriers | **NEW**, pure data |
| `rconfig.py:unique_id_keys` | composite AND-key | **NEW** (ruling M3 — `hard_id_fields` had no declaration site) |

---

## 5. Spec objections — what I think the spec got wrong

### 5.1 The name cap and `identity.relational: false` collide, and nothing in the spec notices *(HIGH)*

D-13.10 says name caps at *possible* **at every layer**. T3b-A declares `identity.relational: false` for
`area_of_operations`, and its own comment says *"an area can still merge or queue on name/alias evidence,
which is the only honest identity signal it has."* Put together: for a type whose relational term is forced
to zero, "name alone" is not a *choice the evidence made* — it is the **only channel that exists**, so the
universal name cap makes such a type **permanently unmergeable** except through a curated alias.

I implemented the cap as specified (it costs 5 area merges) and I think that is right *here*, because the
merges it removed were bad ones. But the general rule is wrong as stated: a cap that says "earn one more
signal" is incoherent against a type the ontology forbids from ever having one. Either the cap needs a
declared exemption for relational-blind types, or those types need a second honest signal. **Flagging rather
than deciding: it is a design call, and it changes which types can ever confirm.**

### 5.2 `auto_merge_by_type` is now largely redundant, and nobody has said so *(MEDIUM)*

The per-type floor of 0.37 exists to admit spelling-variant merges "with margin above every same-type trap".
Its whole reachable band was **name-only** pairs — that is what a spelling variant *is*. With the cap bound to
the fusion path, a name-only pair cannot fuse at any floor, and a name + one-more-signal pair generally clears
the global 0.85 anyway. So the knob still loads and still lowers a floor that almost nothing can now cross.
It is not harmful, but a reader will assume it does work it no longer does. **S4 should either delete it or
document it as vestigial.**

### 5.3 C1's "unknown fails safe" is under-specified in a way that silently disables the wall *(HIGH — I hit it)*

C1 says an unknown `site_type` must "fail safe (same bucket / raise, never de-conflicted)". My first
implementation collapsed each *subject* with an unreadable class to one bucket — faithful to S2's amendment —
and the wall then **silently stopped firing**, because subject A's bucket was `garrison` and subject B's
collapsed bucket was `""`, so they *differed* and de-conflicted. That is precisely the failure S2 measured
across **edges**, reproduced across **subjects**, and the amended C1 does not mention it.

The correct rule, which I implemented and which C1 should state: **the buckets are compared only when both are
readable.** If either is unknown, do not compare them at all — fall through to the conflict test and raise. An
independently-authored fixture caught this; nothing in the spec would have.

### 5.4 "Fragmentation must resolve at S3" cannot be satisfied by S3 *(HIGH, and it is a sequencing error)*

The stage is defined as the one where fragmentation resolves, and its resolving mechanism is coreference
binding. There are **zero coreference annotations in the corpus**, and producing them needs a keyed re-extract
that is RK-DATA's job. So the acceptance criterion "fragmentation resolves by earned merges" is **unsatisfiable
in this stage's inputs**, by construction — S3 can only be measured as *raising* fragmentation, because it
ships the guards before the corpus can ship the earning material. Ruling M4 records the symptom; the plan
should record the **ordering consequence**: the fragmentation metric becomes meaningful at RK-DATA, not at S3.

### 5.5 The gate verdicts the resolver cannot re-derive *(MEDIUM — a stated limitation, not a defect)*

D-13.17 insists a bind stand behind "a structural check any reader can re-derive". Two of the four conjuncts
genuinely can be re-derived downstream (both surface forms in the spans; a marker in the spans) because the
verbatim spans ride the claim. Two **cannot**: "the span occurs in the document" needs the document, and the
positive anaphor gate needs the whole mention inventory. Both are evaluated at ingest by *code* over the
model's output — which satisfies the real distinction D-13.17 rests on (a code check is not a model
self-report) — and the verdict plus its reasoning is stamped for audit. But a reader auditing the graph alone
cannot re-run them, and the spec implies they can. **A link with no stamped verdict fails closed.**

### 5.6 Smaller ones

* **A "gap" has no first-class carrier in `resolve/`.** C7 demands "a named gap"; the only analyst-visible
  channel in the resolver is `candidate_reasons`, so every third state is a *reason on a queued pair* rather
  than a `known_gap` node. That satisfies "binds the fusion path" and "is visible", but it is not the same
  object the rest of the system calls a gap, and G18/C7 read as if it were.
* **C6's `identifying` and `constitutive` differ only on paper.** I implemented `constitutive` = a difference
  is distinctness, `identifying` = agreement can confirm — but nothing in the closure distinguishes their
  *positive* halves, so `identifying` currently behaves like `durable`. If that is all it is, it is a third
  name for one behaviour.
* **`Entity.attrs` first-claim-wins is load-bearing in a place nobody flagged.** The D-13.18 decline is only
  the *first* detector that must read history rather than the scalar; `critical_conflict_disposition`,
  `_identifier_veto` and the namespace derivation all still read the scalar and are all blind the same way.
  I fixed it where D-13.18 required it and left the rest. **S4 should decide whether the scalar is a bug.**
* **The plan assigns G16 "node count preserved" as an assertion, but the resolver has no node count.** I
  assert the observable equivalents (no cluster fusion, no site fusion, no canonical collapse). The node
  count lives in the view; a gate at the resolve layer cannot see it.

---

## 6. Handoff / follow-ups

1. **DATA owes a re-record with coreference in it.** Until then §3's numbers are the ceiling of what S3 can
   show, and the `site_type` alias mapping S2 asked for is still outstanding (it also feeds G18's scoping).
2. **32 scripted-client tests will need a second queued response** when the corpus is re-recorded with the
   flag on (`tests/ingest/**`, `ScriptedExtractionClient`). Not fixed here: they are not this stage's files
   and the flag currently keeps them green.
3. **`operated-by` now has a producer** (C11) but no data. The wall's operator arm is fixture-only until a
   document states one — state it in the disclosures.
4. **Disclosed limitations** for the design note: G16/G18/G19 are fixture-only on this corpus (M4); the
   resolution machinery is validated on synthetic/abstract coreference while real binding accuracy is
   measured separately (§8's bake-off); C8 source-independence is roadmap; F9's step-function relational
   weighting is accepted.
5. **Ownership deviations, recorded:** I edited `config/ontology.yaml` (S2's file) for C11's one field, and
   `tests/config/**`, `tests/ingest/**`, `tests/gates/test_g17_atom_mint.py` where a contract this stage
   changed made them assert something that is no longer true. Each is described in its commit.
