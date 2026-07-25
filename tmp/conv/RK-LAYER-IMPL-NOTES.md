# RK-LAYER (S2) — implementer notes (corpus-blind hand)

Branch `s2/rk-impl`, based on `design/resolution-redesign` @ `a3d68b4`. Four commits, each verified
flag-off before the next. **The implementer hand never read `corpus/**`, `answer_key.json`,
`SCENARIO_MANIFEST.json` or `tmp/spike-rk/gold/**`.** Every threshold and vocabulary below was chosen on
general principle and is stated as such; the two site-class values I know about (an airfield, a
"revetment complex" string) reached me from the orchestrator's rulings, not from the corpus.

---

## 1. The flag — name and where it lives

**`layer_routing.enabled`, a top-level block in `config/ontology.yaml`** (bottom of the file). It ships
**`false`**. *(Confirmed for the test hand — this is the name to align on. `LayerRouting.from_ontology`
compiles it; an absent block reads disabled.)*

Why there: the block declares what layer routing *is*, and the ontology already carries a non-type-list
top-level knob block (`materiality:`), so this needs no schema change — `OntologyConfig` is
`extra="allow"`. Compiled by `chanakya.ontology.LayerRouting.from_ontology`; an absent block reads
disabled, so every consumer degrades to the pre-S2 path.

**One flag for all six mechanisms**, deliberately: the straddle split, endpoint materialization, the
derived basing edge, the `site_type` bucket, `requires_stated_endpoints`, and the earned-identity gate on
supersede promotion. They are one change to *what a node is*, and half of it is incoherent — a
materialized presence with no `instance-of` link is an orphan; a `site_type` bucket with no derived basing
to key is inert; an earned-identity gate with no notion of a provisional instance can only ever fire on
half its cases.

`credibility.yaml` carries two related config additions, both inert without the flag:
`supersede_floor.require_earned_identity` (a boolean — no number to tune) and
`basing_proposer.occupied_tokens`. `basing_proposer` is otherwise **unchanged**: those knobs describe the
derivation, and the derivation did not change — only *where and when* it runs.

---

## 2. Flag-off proof

Verified on **both** valid surfaces after every commit (the booted app withholds the flagship relocation
pair, so it is blind to items 5–7; the full scenario is the gate):

| surface | measurement | hash |
|---|---|---|
| booted app | 160 nodes / 73 edges / 18 gaps / 450 claims | `22d668a348430df091b71aa0ff53650f8b1be0ba9d95ab88b9034368d6dac3a9` |
| full scenario (harness) | 169 nodes / 80 edges / 71 events / 20 gaps / 492 claims | `bd24eefc16c990eb6630147a231c778ff9bfa3df41dce990defde42454ed275f` |
| golden fixture | md5 `bb6f16a516c31eb0846494b62271a601` | unchanged |
| suite | **1102 passed, 7 skipped, 2 xfailed** | — |

The count moved from 1094 to 1102 net of **−16** (`tests/ingest/test_basing.py`, deleted with the module
it tested) and **+24** new gate/fixture tests. Two rebuilds of the full scenario are byte-identical
(G1/G2) in **both** flag states.

The golden fixture carries its own minimal `config/ontology.yaml` with no `layer_routing` block, so it is
protected by construction rather than by luck.

---

## 3. Flag-on diff, delta by delta (full-scenario surface)

**169 → 183 nodes · 80 → 95 edges · 20 → 27 gaps · 71 events unchanged.** Hash
`9fb23acb89bd8c062cf23190d0f338dccb6270072056ccaba717f1180582f7b2`; two rebuilds identical.

Predicted before measuring; every line below was the prediction.

| # | delta | why it is target-correct |
|---|---|---|
| 1 | **+14 `presence` nodes** — one per resolved `observed-at` edge instance | A4/D-13.13, the worked example of spine/13 §5.3. A sighting states equipment at a place; pointing it at the shared design node would assert the *design* is at a place and pool every operator's sightings onto one node. Each carries `provisional: true` and `instance_of_design`. |
| 2 | **+14 `observed-at` / −14 `observed-at`** (same count, re-pointed) | The sighting's subject moves from the design node to the presence. Not new facts — the same claims, bound to the endpoint the edge actually needs. |
| 3 | **+14 `instance-of` edges** | The presence is not an orphan: it links back to the shared design, citing the same observation claim. This is the "one mention → two linked nodes" half of the split. |
| 4 | **+2 derived `based-at` edges** | Two more sites now clear the `observed-at` + `inducted-into` triangle than the frozen bundles had recorded (the bundles were frozen against a sparser earlier view). Each cites **its two premise claim-atoms** — no minted claim. |
| 5 | **The two `unit_hq9b` basings become rebuild-derived** and drop their frozen `*__basing.json` inference claims | The offline pass is deleted; the same edges are now recomputed each rebuild from the same premises, so a conclusion can no longer outlive its premises. |
| 6 | **−1 `supersedes` edge**; the retired basing goes `stale` → `possible` | The flagship relocation lands in the **third state**: one shared untagged instance (no de-confliction), nomination withdrawn (no fusion), and a named gap. One end's class maps and the other's does not, so we cannot yet say whether this is one kind of place. **Intended and ruled correct** — the mapping is DATA's to supply. **The one-line handoff:** one `site_type_aliases` entry mapping the older site's stated class onto `airfield` makes both ends map, and the relocation is nominated and drawn again with no code change. The gap text quotes the stated string verbatim, so the entry to write is readable straight off the surface. |
| 7 | **+7 gaps** | 2 × unmappable-`site_type` (the third state's third part) · 4 × truncated formation attribution, each **naming the discarded candidate** (R2.1/G15 — this fires on the real corpus, so the clause is not vacuous) · 1 × an ordinary sufficiency gap on a newly-appearing derived edge. |
| 8 | **10 `basing_site` nodes gain `layer_straddle_unrouted`** | Their `occupancy_state` is an instance-layer fact on a design-layer node — a genuine straddler with no declared citizen, because the citizen of a site's occupancy is the presence its sighting already materialized. Recorded on the node rather than given an invented structure. |
| 9 | **6 design nodes change** (`var_hq9p`, `var_hq9be`, `comp_ht233`, 3 components) | They regain the sighting claim whose edge was re-pointed away (`apply_design_citations`). Two also move `possible → probable` and one keeps a decay it would otherwise have lost. Before routing, a dangling endpoint's provenance was "the claims of whichever edge mentioned it first" — order-dependent; re-pointing changed the winner. Citing the claim that *named the design* is the honest read, and it is what the node had before. |
| 10 | **1 stated basing's `edge_instance` gains `:airfield`** | Its subject has exactly one basing and its class is known, so the tag applies. Visible in the identifier, no behavioural consequence with one target. |

**No node is removed and no claim's provenance is lost.** Every added element cites at least one claim
(G4).

### Flag-on suite

8 failures with the flag on, characterised (none blocks; the flag ships off):

* **2 real** — `tests/api/test_withheld_seed.py` (the relocation alert). Delta 6 above: intended, and
  clears when DATA supplies the `site_type` mapping. Verified flag-conditional (both pass with routing off
  under the identical root).
* **1 by design** — my own `test_layer_routing_is_off_by_default_in_the_shipped_ontology`, which asserts
  the shipped config.
* **5 not flag-related** — `test_quotes.py` (×4) and `test_answer_key_separation.py` fail identically with
  the flag **off** under the synthetic config root I used for the dual-run; they read repo-relative paths.

---

## 4. Reuse vs new

| existing code | what I did |
|---|---|
| `chanakya/ontology.py:64` `build_edge_instance_key` | **extend** — one optional `tag` argument; `None` (always, flag-off) reproduces the old string byte-for-byte |
| `chanakya/ontology.py:115` `EdgeLaneIndex` | **extend** — `instance_key_tag` / `materializes` / `requires_stated_endpoints` / `endpoint_layers`; all read plain YAML through `extra="allow"`, no schema change |
| `chanakya/ontology.py:316` `NodeTypeIndex` | **extend** — `node_layer` / `attr_layer` / `straddling_attrs` / `instance_split`, beside `refine` / `identifier` as the session file asked |
| `chanakya/ontology.py` (end) | **new** — `LayerRouting`, the compiled flag + knobs |
| `chanakya/schemas/config_models.py` `AttrDef` / `TypeDef` | **extend** — one `layer` field each (S1 had already restructured `attrs`, so this is one added key per entry) |
| `chanakya/view/supersede.py:100` `build_instance_edges` | **refactor, no behaviour change** — the ordering half factored out as `order_instance_edges` so the derived layer runs the *identical* rule; a second copy would have been free to drift |
| `chanakya/view/pipeline.py` `_assemble` | **extend** — relationship claims are now buffered before keying (needed: a node attribute has to exist before its edge can be keyed). Signature kept a **3-tuple** with the routing report as an out-parameter, so every existing caller and any independently-authored test binds unchanged |
| `chanakya/view/pipeline.py` `rebuild` | **extend** — three new steps (2b derive, 2c retag, and the routing gaps), all inside `if routing.enabled` |
| `chanakya/credibility/supersession.py:165` `promote_supersessions` | **extend** — two optional args, both default `None`; the earned-identity gate |
| `chanakya/credibility/status.py:51` `_CAP_FLAGS` | **extend** — one string (`derived-inference`) |
| `chanakya/ingest/basing.py` | **DELETED** (see §5) |
| `chanakya/view/layers.py` | **new** — layer routing |
| `chanakya/view/basing.py` | **new** — the rebuild-time derived basing edge; the pure premise-selection helpers are carried over from the deleted module |
| `config/ontology.yaml` | **extend** — `layer` on 15 node types + 90 attribute entries; 2 new node types, 3 new edge types, 4 new per-edge keys, the `layer_routing` block |
| `config/credibility.yaml` | **extend** — `require_earned_identity`, `occupied_tokens`; `max_claims_per_pass` removed (see §5) |

---

## 5. Deleted, and what rode on it

**`chanakya/ingest/basing.py` — deleted, not relocated.** It minted a `kind="inference"` `ClaimRecord`
and appended it to the evidence log. That is derived output frozen into an append-only record: the
conclusion outlives its premises across a re-record, and provenance depends on when the pass last ran.
`tests/gates/test_g17_no_evidence_write_under_rebuild.py::test_the_deleted_offline_basing_pass_is_gone`
pins the deletion, because "moved it into the view" and "deleted it and derived the edge instead" look
identical in a diff summary and are architecturally opposite.

Traced and dropped with it:

* `tests/ingest/test_basing.py` (16 tests).
* the `basing` subcommand in `chanakya/ingest/__main__.py`, its parser, and its docstring entry (the
  now-unused `Triple` import went too).
* `freeze_bundles` — nothing writes `*__basing.json` any more.
* `basing_proposer.max_claims_per_pass` — a budget cap on an *offline* pass; meaningless in a pure fold,
  where the work is bounded by the graph. Its `over-budget` skip record went with it.

Traced and deliberately **kept**:

* **`ingest/seed.py`'s `_DERIVED_BUNDLE_SUFFIXES` still contains `__basing.json`.** The plan says to drop
  it "with the pass". Dropping it **unconditionally is the byte-identity break** — the frozen bundles are
  still on disk and still load, and flag-off must keep loading them. So the glob entry stays and the
  *rebuild* declines those claims when routing is on (`_drop_superseded_derivations`, driven by
  `layer_routing.superseded_derived_layers`). The entry becomes dead the moment RK-DATA removes the
  bundles. **This is a spec correction, not a deviation of convenience** — see §7.
* `api/routes/pending.py` and `eval/harness.py` mention `__basing.json` only in prose; the mechanism they
  rely on is the generic `<doc>__` prefix rule in `bundle_belongs_to_doc`, which is untouched.

---

## 6. Design decisions worth a reviewer's eye

**The `materializes` declaration is explicit, not derived.** A2 says endpoint layers fall out of the
declared endpoint types. True, and **not sufficient**: `observed-at`'s declared domain is
`variant`/`component` — design types, because that is what an extractor may legitimately emit — while its
semantics require an instance subject. Nothing in the endpoint types can express that gap, so the intent
is declared per edge. Opt-in is also the fail-safe direction: an edge that declares nothing materializes
nothing, so no edge type can silently start minting instances. `inducted-into` declares nothing and
therefore mints nothing, which is spine/13 §5.3's contrast case.

**Presence grain: one per (design endpoint, site endpoint)** — i.e. per resolved `observed-at` edge
instance, *not* per mention. Coarser than S3's coref grain will be, and safe in exactly the way D-13.14
states: "merging co-located reports into one **presence** is safe; merging them into one **formation** on
co-location alone would undercount the order of battle." **S3 must not read this as already-correct
grain.** I did not touch fragmentation (F8) and no threshold was moved.

**The `site_type` decision is per subject, not per edge.** This is the sharpest thing in the stage and the
one place a naive reading of C1 is actively harmful — see §7 item 1.

**The derived basing edge is capped explicitly.** It cites its premises *directly*, which is the point
(one click to the sighting and the induction). But two independent premise sources would then pool into
two independent looks and the inference would read as better corroborated than the sighting under it. The
minted form got its ceiling for free by sharing an independence group with its premises; citing them
directly needs it said, so the edge carries a `derived-inference` gate flag that caps it at *probable*.

**Provisional instances live in their own id namespace** (`presence:<design>@<site>`), never `ent:`. G13
binds after S4 and scans for `ent:` construction; this stage adds no new offender for S4 to unwind.

**`meta` as the third layer value** (ruling L3) is doing real work, not tidying: the split trigger fires
on a layer *mismatch*, so a source or a known-gap mislabelled `design` would generate a phantom split the
moment any of its attributes were tagged `instance`.

---

## 7. What I think the spec gets wrong or leaves underspecified

This is the highest-value section: I am the first to build this.

1. **C1 as written de-conflicts *silently*, and a per-edge reading of it kills the flagship relocation.**
   Ruling L1 caught the diagnosis; the *fix* it implies is stronger than "collapse an unmappable value to
   a shared bucket", and I only found that by measuring. If one of a subject's basings has a known class
   and another does not, tagging the known one **separates** the unknown one from it — and separation *is*
   de-confliction. On the real corpus that put the relocation's two ends in different buckets, the
   supersede simply never fired, and **nothing anywhere said so**: no gap, no flag, and the code still
   looked deterministic. The correct rule is per `(subject, predicate)` over **every** basing of that
   subject: all classes known ⇒ de-conflict; any class unknown ⇒ one untagged instance, nomination
   withdrawn, named gap. Because "every basing" includes the rebuild-derived ones, the tag **cannot** be
   applied during keying at all — it has to be a post-pass after the derivation. The plan implies the
   opposite (an `instance_key` is a keying-time concern). **S3 must inherit the per-subject rule when it
   writes G18's wall**, or the wall will fire on the same false distinction.

2. **G18 needs a *stated* `operated-by` and S2 cannot supply a producer.** I declared the predicate and an
   `operator` node type, so the gate can test itself on a fixture. But nothing *emits* an operator mention
   — the extraction schema carries the operator as a discriminator **attribute** — so a stated
   `operated-by` has no production path. I left it `extractor: false` rather than widening the extraction
   enum, because that would change live extraction behaviour outside the flag with no seeded data behind
   it. **Someone must own the A7 extraction-schema extension**, or G18's `operated-by` half is fixture-only
   forever. (Contrast `customs-party`, which I *did* make extractor-emittable: D12's harm is specifically
   extraction-side fabrication pressure, and its endpoints are both existing types, so no new mention type
   is needed.)

3. **C6's `perishable` needs three values and the field is a boolean.** C6 says geography is *perishable*
   for a formation, **constitutive** for a presence, **identifying** for a place. The shape already exists
   per `(type, attribute)` (`config/resolution.yaml → attribute_roles.<type>.<attr>.perishable`, read by
   `rconfig.attribute_perishable`) — but it is `bool | None`, which cannot express three states.
   `constitutive` and `identifying` are not "not perishable"; they are different claims about what the
   attribute *does* to identity. S3 owns that file and C6, so I did not change it — but the closure as
   written cannot be implemented against the current field.

4. **D12's uniqueness constraint forbids one edge per customs role.** `canonical_edge` keys on the
   `(from → to)` type pair, so two extractor edges between `contract_import_event` and `trading_org`
   collide. Splitting them by *direction* instead would make the model's chosen direction authoritative —
   a flipped write would silently turn a shipper into a consignee, which is the same class of fabrication
   the edge exists to remove. So the role has to be an edge **attribute** (`party_role`). The spec asks for
   "the event ↔ trading_org edge" as though the shape were free; it is not.

5. **A2's "endpoint layers fall out of the endpoint types" cannot express the worked example** (§6 above).
   The spec states it as sufficient; it is necessary and not sufficient.

6. **The straddle split needs a per-type (citizen, link) declaration, and the design supplies only one.**
   Design → presence via `instance-of` works. A site's instance-layer *occupancy* has no distinct citizen —
   its citizen is the presence the sighting already materialized — so splitting it would double-count one
   fact. I record the unrouted straddle on the node instead of inventing structure. The spec's "a
   straddling mention splits into two linked nodes" is written as universal; it is not.

7. **A genuine defect in the derivation, pre-existing and masked by the frozen data.** The derived basing
   inherited *the later of its two premises'* valid times. But the same `inducted-into` claim backs every
   attribution for a unit, and the derivation always picks that edge's newest backing claim — so **every
   basing of that unit inherited one identical induction date**, and two basings with identical dates are
   unorderable, i.e. read as "the unit is in two places at once" rather than as a relocation. Measured: a
   2021 sighting inherited a 2025 induction date. Fixed to the observation's own time, which is what the
   module's docstring always said it did ("inherited from the grounding observation … which is why the
   observation had to be dated first"). The frozen bundles hid it because they were recorded against a
   sparser earlier view — **a general warning: anything the offline passes froze is evidence about an older
   graph, not about this one.**

8. **A provenance hazard the spec does not mention: re-pointing an edge can silently strip a node's
   provenance.** A dangling endpoint's claim_ids are "the claims of whichever edge mentioned it first" —
   order-dependent. Re-pointing `observed-at` off the design node changed the winner, and one design node
   lost the dated look it was decaying against (its freshness went from a 0.011 decay factor to 1.0 — it
   read *fresher* after the change). Fixed by having the design node keep citing the claim that named it.
   **Any later stage that re-points an edge inherits this hazard**, and the underlying first-wins
   dangling-endpoint rule is worth revisiting on its own merits.

9. **The occupancy vocabulary is duplicated across the ingest and view layers.** `view/basing.py` must not
   import `ingest.imagery`, because `imagery` imports `make_claim_id` and that would drag a mint into the
   rebuild-reachable call graph and trip G17's own static scan. I moved the vocabulary into config
   (`basing_proposer.occupied_tokens`) with the duplication stated in a comment. Properly unifying it means
   `ingest/imagery` reading the same config key — a small follow-up nobody owns.

10. **Smaller notes.** `mfr_23rd_ri` appears as the subject of a `based-at` edge, whose declared domain is
    `unit` — a pre-existing extraction/data artefact the view does not police (nothing validates view
    endpoint types against the ontology). And the acceptance line "`layer` populated on all 13 node types +
    81 attribute entries" is now **15 and 90**: A3 and G18 required two new node types, which carry nine
    attributes between them.

---

## 8. Three-hands separation, as evidenced

The implementer hand read `artifacts/**`, `tmp/conv/rk-spike-*`, `backend/chanakya/**`,
`backend/tests/**` (existing tests, to keep them green) and `config/**`. It read **no** corpus document,
**no** answer key, **no** scenario manifest and **no** spike gold. It never opened `s2/rk-test` or
`s2/rk-data`. Every measurement above is an aggregate of the frozen claims as the pipeline sees them —
node and edge counts, hashes, and the identifiers the graph itself prints — which is what a dual-run
requires and is not the same as reading the corpus.

The four thresholds/vocabularies I introduced, and the principle behind each:

| value | principle |
|---|---|
| `site_type_vocabulary` (8 values) | a single axis — *kind of place* — chosen because the three other axes the stated values conflate (how we learned of a site, what is parked there, area-vs-point) each already have a proper home. Not tuned to any observed value; the mapping is DATA's. |
| `absent_bucket: unknown` | one shared bucket, because the evasion direction is over-merge and a bucket of its own would let an unstated class buy a second concurrent basing for free |
| `count_attrs` | the attributes a *source* can state about a presence. Never a count derived from claim arithmetic. |
| `require_earned_identity: true` | a boolean, not a threshold — there was no number to tune once "sub-confirmed" was ruled to mean an open `candidate` merge |

---

## 9. Integration round 2 — what changed after the independent suite ran

The independently-authored suite found **7 failures**. Two were the session file's stale counts (my surface
is right: 15 types / 90 entries, all tagged); five were mine or a reconciled disagreement.

### The glob is now flag-gated (the disagreement, resolved with no trade)

Both sides were right: removing `__basing.json` from the seed glob unconditionally **is** the flag-off
byte-identity break, *and* leaving it unconditional means a frozen bundle replays an inference the rebuild
now derives — the same attribution twice, once frozen and never ageing. Flag-gating it costs neither.

Declared as `layer_routing.superseded_derived_bundle_suffixes` beside the existing
`superseded_derived_layers`, and read through `LayerRouting.retired_bundle_suffixes()` so the flag boundary
lives in **one** place rather than at every seed call site. `seed_store_from_bundles` gained a dumb
`skip_suffixes` argument (it stays config-free); `api/state.py` and `eval/harness.py` supply it from config.

**Both halves are kept, and they are not redundant.** The file-level skip stops the double attribution
entering the store at boot — measured: the full-scenario claim count drops 492 → 489 with the flag on. The
`derived_layer` filter inside `rebuild()` is the **backstop** for a store that already holds such claims,
where the file-level skip never ran: a live `POST /ingest` of a legacy bundle, or any caller that seeds
without config in hand.

### R1.4 was too broad — re-scoped to exactly two narrow prohibitions

I had it return a **hold**, which disabled promotion generally. That is the over-correction the mirror
caught, and the pattern is worth recording rather than filed as a slip: *an implementer closing an
over-promotion hole reaches for the broadest guard, because every test it can see rewards caution.* Only a
mirror that asserts the thing which must still work can catch it. Timidity is a failure mode here.

R1.4 now changes **how** a promotion happens, never **whether**:

* **(a) no machine adjudication over an unearned identity.** The pair is promoted, retired and drawn as
  normal — but it **keeps `candidate_supersede`** and records why, so the analyst still decides. Promotion
  is not withheld; *adjudication* is. (`identity_is_unearned`, and the `supersede_adjudication_held` attr.)
* **(b) no honest `insufficient` overwritten with `stale`, and no Known Gap deleted** —
  `protects_an_honest_refusal`.

**And (b) is conditioned on (a)'s trigger, which I got wrong first and which the real corpus caught.** My
first cut made (b) unconditional, and it **broke flag-off byte-identity and the flagship relocation
together**: that retirement is itself under-evidenced, so protecting it stopped it ever reading `stale`.
D-13.14 settles it — it names the gap deletion as one of *three consequences of the over-merge* ("draws a
relocation, removes the pair from the analyst's queue, and deletes the retired edge's Known Gap"). The harm
is an identity error laundering itself into a movement assessment, **not** that retiring an under-evidenced
position is wrong in general. So both prohibitions share one trigger. An earned retirement — assessable or
not — restates to `stale` and drops its gap exactly as before.

Config simplified with it: `require_earned_identity` is a boolean and there is no threshold at all.

### Duplicate gaps — a real one, fixed at source and again at the end

`withheld` collected one entry **per withheld claim**, so several claims asserting one unsourced relation
each earned their own copy of the same gap. Now recorded once per `(predicate, endpoint, end)`. And
`rebuild()` deduplicates `known_gaps` by id as a backstop, first-occurrence-wins and deterministic —
several mechanisms can independently notice one absence, and a register that lists a finding twice reads as
two findings, which is how an analyst learns to skim it. Verified: no repeated gap id in either flag state.

### The mirror tests I should have written first

Six added to `tests/view/test_layer_instance_key.py`, each prohibition paired with the thing that must
still work: an earned relocation is promoted, retired, drawn **and** popped from the queue · a
well-evidenced retirement still reads `stale` · an unearned identity is promoted but **stays** in the queue
(both shapes: a provisional subject and an open candidate merge) · an under-evidenced retirement over an
*earned* identity is retired normally · a same-target refresh is never treated as unearned · the switch is
real and the gap register never repeats itself.

### Verification after the round

| | flag off | flag on |
|---|---|---|
| booted | 160 / 73 / 18, `22d668a3…` | — |
| full scenario | 169 / 80 / 71 / 20, `bd24eefc…`, 492 claims | **183 / 95 / 71 / 27**, 489 claims, two rebuilds identical |
| golden | md5 `bb6f16a5` | — |
| suite | **1109 passed**, 7 skipped, 2 xfailed | — |

The flag-on node/edge/gap deltas are **unchanged** from §3 — the loader gate closes the double-attribution
channel at source (3 fewer claims) without moving the graph, because the rebuild backstop was already
declining those claims.

**And the beat is proven curable, not broken.** With three `site_type_aliases` entries standing in for
DATA's mapping, flag-on promotes the flagship fully: Rawalpindi `stale`, Rahwali `probable`, the
`supersedes` edge drawn, `supersede_gate: promoted`, and the pair correctly *popped* from the analyst's
queue because that identity is earned. In the same run `unit_paad`'s two basings de-conflict into
`command_centre` and `emplacement` — two concurrently valid basings, correctly **not** a relocation, which
is R1.3/C1's whole purpose. So the third state is a refusal on a specific, curable ground, and the
per-subject rule buys the precision it was meant to.
