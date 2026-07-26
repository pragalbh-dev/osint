# DEFAULT-ON — calibration / data-refresh ledger

**For: the DATA agent (and whoever re-records the frozen bundles + answer key).**
**From: DEFAULTON-impl (branch `defaulton/rk-impl`).**

The identity re-key is now unconditional (both stage flags deleted — see `DECISIONS.md` → "DEFAULT-ON").
Nothing in the corpus, the frozen bundles, `answer_key.json` or any golden fixture was edited. Where the
target behaviour invalidated a corpus expectation, the test is marked `xfail(strict=True)` with the
regeneration named in the marker's `reason`, per working principle #3.

Five tests are expected-red. There are exactly **two** underlying data items.

---

## Item 1 — `layer_routing.site_type_aliases` is empty, so the flagship relocation is HELD

**Owner: DATA.** Ruling L1 step 4 assigns this mapping to the data pass, and it is a domain judgement about
the *kind-of-place* axis — not a threshold an implementer may guess, which is why it is filed here instead of
being authored from a test failure.

`unit_hq9b` carries **four** rebuild-derived `based-at` edges. Their stated `site_type` values are:

| site | stated `site_type` | normalises? |
|---|---|---|
| `ent:basing_site:Army Air Defence Centre, Karachi` | `centre` | no |
| `ent:basing_site:Sargodha` | `deployment site` | no |
| `site_rahwali` | `airfield` | **yes** |
| `site_rawalpindi` | `prepared revetment complex / airfield site` | no |

The closed vocabulary is `config/ontology.yaml → layer_routing.site_type_vocabulary`; `site_type_aliases` is
`{}`. Because the rule is **per subject** (a partial tag is worse than none — separation *is*
de-confliction), one unreadable class collapses the whole subject to one bucket and takes C7/L1's third
state: **no de-confliction**, **no fusion** (every supersede nomination on `unit_hq9b` is withdrawn and marked
`supersede_suppressed: instance-key-tag-unmappable`), and **a named gap**
(`gap:edge:unit_hq9b:based-at:site_type`).

Consequence: no `supersedes` edge is drawn, the origin basing reads `possible`/`insufficient` rather than
`stale`, and the relocation observable fires no alert.

**This is the target behaviour**, and the system's own corpus gate asserts it:
`tests/view/test_rk_layer_supersede_identity.py::test_the_flagship_relocation_is_held_while_its_site_classes_are_unknown`
passes. It was invisible before only because the layer-routing flag shipped off.

**Expected-red (all `xfail(strict)`):**

- `tests/acceptance/test_relocation_beat.py::test_relocation_alert_fires_once_with_before_after_and_provenance`
  — `len(alerts) == 1` observed `0`.
- `tests/acceptance/test_relocation_beat.py::test_the_only_alert_is_the_watched_unit`
  — `{a.subject for a in alerts}` observed `set()`, expected `{'unit_hq9b'}`.
- `tests/api/test_withheld_seed.py::test_ingesting_the_withheld_documents_relocates_the_unit_and_fires_one_alert`
  — origin `status` observed `'possible'`, expected `'stale'`.
- `tests/api/test_withheld_seed.py::test_env_override_can_seed_the_full_corpus`
  — same signature (`'possible'` vs `'stale'`).

Everything else in both modules still passes, including `test_staged_ingest_adds_the_relocation_evidence`,
`test_staged_ingest_is_deterministic` and `test_spoof_ingest_fires_nothing`.

**TO CLOSE:** author `layer_routing.site_type_aliases` mapping each stated string onto the closed vocabulary
— i.e. decide, as a domain question, whether *centre*, *deployment site* and *prepared revetment complex /
airfield site* denote the same kind of place as one of the declared classes, or whether the vocabulary itself
needs a new class. Then re-record and delete the four markers. **Do not** close it by weakening the third
state: a change of site whose kind-of-place cannot be read may not be asserted as a movement.

---

## Item 2 — the corpus types the string `HT-233` two different ways

**Owner: DATA (or ONTOLOGY).**

One document states `HT-233` as a `component`, another as a `variant`. The cross-type fusion wall is
unconditional now, so the view holds two nodes — `comp_ht233` and `ent:variant:HT-233` — where the frozen
expectation is one.

**This is the ruled behaviour** (see `DECISIONS.md` → the Part-3 fork): a type disagreement between two
sources is an *evidentiary contradiction*, and the system surfaces it rather than resolving it silently in
either direction. Fusing would assert a type neither source states; dropping the resemblance would hide the
disagreement. So the refusal is **not** a quiet drop — the pair reaches the analyst as a candidate carrying
`not fusable: cross-type (component vs variant)`, and each endpoint carries a Known Gap
(`gap:identity:comp_ht233|ent:variant:HT-233:<endpoint>`) naming the adjudication needed.

**Expected-red (`xfail(strict)`):**

- `tests/acceptance/test_t3b_fragmentation_corpus.py::test_the_identical_string_ht233_fragment_is_gone`
  — observed `['comp_ht233', 'ent:variant:HT-233']`, expected `['comp_ht233']`.

**TO CLOSE:** either harmonise the stated type of `HT-233` across the corpus documents, or declare a
`component` ↔ `variant` refinement in `config/ontology.yaml` so the two mentions arrive as one type. Then
re-extract, re-record the bundles + answer key, and delete the marker. **Do not** close it by weakening the
wall.

---

## Also worth a look (not expected-red, no action required)

Two cross-type candidates other than HT-233 now reach the analyst's queue, because a source asserted the
identity and such an assertion is no longer silently dropped:

- `('ent:component:Type 305B', 'ent:variant:HT-233')` — the same typing contradiction as item 2.
- `('comp_tel_chassis', 'ent:known_gap:transporter-erector-launchers (TELs)')` — a `component` asserted
  same-as a **`known_gap`** node. That looks like an extraction artefact (a gap placeholder being treated as
  an entity) and is exactly the kind of thing the queue exists to put in front of a human, but it may be
  cheaper to fix upstream in extraction than to adjudicate.

Both are candidates, not merges: both endpoints remain separate nodes and each edge carries the reason.

## Not stale, worth knowing

`unit_hq9b`'s four derived basings include two whose premises are `d23-cpmiec-false-attribution` and
`d10-sat-cloud-gap` — i.e. the graph is attributing basings to that unit off a document the corpus plants as
a **false attribution**. That is a separate question from this change (the derivation is unchanged), but it is
what makes the site-class spread as wide as it is.

---

# Integration pass (2026-07-26) — what the 53 reds actually were

**From: DEFAULTON-integration.** Suite after integration: **1467 passed, 7 skipped, 7 xfailed, 0 failed.**
No fixture edited, no golden regenerated, **no new xfail added** — the five items above are still the whole
expected-red set, and they are still the whole data-refresh backlog.

## The headline: 44 of the 53 were BINDING ARTEFACTS, not implementation defects

The red count did not move under the implementer's 16-file change because most of the tests never reached
the implementation. Two mechanisms, both in the fixture helpers:

1. **`earned_identity.enabled` (37 reds).** The spec helpers pinned the stage with `{"enabled": True}`, which
   `validate_stage_block` now rejects at construction. Every one of those tests died inside
   `ResolveConfig.from_bundle` while its failure message named the escalation path, the co-location cap or
   the country wall. Nothing was measured.
2. **`raises_loudly` masking the same error (9 more reds, plus 9 FALSE GREENS).**
   `test_a_legal_ceiling_value_is_never_rejected` catches load exceptions, so it reported
   "`name_ceiling='probable'` … was rejected at load" when the ceiling validator was perfect and the raise
   came from `enabled`. Its mirror, `test_a_ceiling_value_the_code_cannot_honour_is_rejected`, was *green for
   the same wrong reason* — passing on `StageBlockError`, never on `CeilingValueError`.

Also found: `rc.bundle(flag_on=…)` had stopped binding to anything. `CredibilityConfig` is `extra="allow"`,
so the dead kwarg was filed as a credibility field nobody reads — a fixture that believed it had pinned a
stage. Both fixture builders now refuse the retired names by name (`_rk_layer.DEAD_STAGE_KWARGS`).

**No assertion was weakened to make anything pass.** Two rulings changed a *probe*; both are recorded in the
test docstrings and summarised below.

## Rulings (two hands genuinely disagreed; recorded, not split)

- **Declaring the dead flag is an ERROR, not a no-op.** The specs expected `enabled` to be ignored; the
  implementation rejects it in both directions. The implementation is right — an operator who writes
  `enabled: false` and is silently overridden is the fabrication path — and it is the spec author's own
  `perishable:` doctrine, stated in the sibling `declared_values` file. The off-spellings are now asserted as
  *unreachable* (`test_every_off_spelling_of_the_flag_is_refused_at_load`), which is strictly stronger than
  "loads and behaves the same".
- **A hard-walled pair does not get an `identity_status`.** `test_the_pair_is_never_silently_dropped…`
  demanded membership in `candidates`/`possible`. Refused: `probable` would draw a candidate `same-as`, i.e.
  an accept-this-merge button for the costliest over-merge in an operator-scoped ORBAT; and `finalise`
  structurally filters both tiers by `not in distinct`. The property was kept and the probe widened to every
  analyst-facing channel **plus a new requirement that the refusal carry its grounds** — bare membership no
  longer passes.
- **An absent stage block leaves the co-location cap inert, and that is correct.** G6, and the
  `declared_values` file defends it explicitly. The guard moved to the config surface, where
  `test_neither_stage_block_declares_an_enablement_switch` already fails if a shipped block drops its
  ceilings — asserted directly, so moving it cannot lose it.

## Real implementation defects fixed (all on the escalate half)

1. **The hard critical-attribute wall threw its reason away.** `critical_conflict_disposition` computes which
   attributes credibly disagree and the *raise* branch kept them while the *wall* branch dropped them — so
   the hardest refusal in the system reached the analyst as `view/pipeline`'s fallback string "explicit
   do-not-merge (hard veto)". This is the rail that walls two same-named trading orgs stating China and
   Pakistan. Now 25 of the 30 drawn do-not-merge edges carry a ground-naming reason (the other 5 are curated
   /claim-asserted, which need none by design).
2. **A source-asserted identity a wall overrode vanished.** Both `_coref_pairs` and `_identity_pairs` did
   `if pair in veto: continue`. The verdict is right; the silence was not — no bind, no queue item, no gap,
   both halves orphaned. Now routed to `identity_refusals` ⇒ one named Known Gap per endpoint, carrying the
   document's licensing quote where it supplied one.
3. **`_colocation_cap_reason` hard-coded `'probable'`.** An operator setting `colocation_ceiling: possible`
   got a watch-list pair whose rationale said it was in the review queue — and the two bands produced the
   identical reason. The ceiling is now threaded in, like its sibling `_name_cap_reason` always did.
4. **`contrast_ceiling: possible` behaved exactly like `probable`.** The raise-wall channel was band-blind, so
   the one rail on it whose ceiling is a config value could not honour it. `raise_ceilings` now carries the
   declared band. Byte-unchanged on the shipped `probable`.
5. **Two validated no-ops wired (P7).** `earned_identity.presence_types` granted its documented exemption
   implicitly via *another* key's contents; now stated explicitly in `colocation_only`.
   `layer_routing.presence_type` was one of FOUR declarations of the value `presence` and the only one with
   no consumer — the copy an operator would edit was the copy that did not run. It is now the single source;
   the three `node_type: presence` duplicates are removed from `config/ontology.yaml`.

## Measured corpus impact — direction is UNDER-merge (the recoverable error)

| surface | nodes | edges | events | gaps | claims |
|---|---|---|---|---|---|
| pre-change booted | 160 | 73 | 66 | 18 | 450 |
| **booted, now** | **186** | **112** | **66** | **33** | **449** |
| pre-change full scenario | 169 | 80 | 71 | 20 | — |
| **full scenario, now** | **198** | **120** | **71** | **38** | — |

More surviving nodes ⇒ fewer merges ⇒ under-merge. Events are **unchanged** on both surfaces (66 / 71), so
nothing in the event lane moved. Gaps up 18→33 and 20→38 is the escalate half becoming visible. Digests
`6bffe7df968a0ec97607b3716e4fa2a1` (booted) / `0bee71ad3de7a905e894961e219d3a2b` (full), identical across
five separate processes including `PYTHONHASHSEED=random`. The golden fixture md5 is still
`bb6f16a516c31eb0846494b62271a601` — untouched.

## Honestly byte-inert on this corpus (principle #5), and why

Defect (2)'s fix fires **zero** times on the real corpus: the booted evidence log contains **0
`coref-same-as` claims**, and no source-asserted `same-as` collides with a hard veto. The mechanism is at
full strength — the corpus-independent gate fixture produces exactly that collision and yields two named
Known Gaps carrying the document's sentence verbatim. This is "inert because the data is sparse", not
"hidden to protect a fixture". **It closes on the same DATA action as item 2 above** (a re-extraction that
emits coreference annotations will start exercising it).

## Residue reported, deliberately NOT changed (out of the DEFAULT-ON mandate)

- `next_coverage_due` is populated on only **3 of 33** Known Gaps. The non-negotiable asks a refusal to name
  what is missing *and when next coverage is due*; the first half holds everywhere (33/33), the second is
  mostly empty. Needs a per-source collection-cadence model — a DATA/design question, not a fix to make from
  a test failure.
- `credibility.entailment_judge_enabled: false` is a default-off boolean, but it is an ASK feature and an
  *additional* belt over always-on deterministic citation validation; ON by default would also break the
  keyless boot (it needs a live client). Compliant, and scoped out by the specs by name.
- `mypy` reports 5 errors in `view/basing.py` and `view/pipeline.py` — both files untouched by this pass, so
  pre-existing. Every file this pass edited is ruff- and mypy-clean.

---

## Item 3 — SINO-GALAXY splits 2-1 once a CLASS attribute may no longer stand in for identity

**Owner: DATA (one alias-table row).** Not a threshold and not a code fix.

Closing the class-attribute loophole (BLOCKER 1: an agreeing `family` / `origin_country` / `service_branch`
was lifting the name cap, the only remaining guard on the widest fusion lane) removed the signal that carried
the third SINO-GALAXY spelling into its cluster.

Measured on the booted `hq9p_primary` corpus:

| pair | before | after |
|---|---|---|
| `SINO-GALAXY IMPEX CO, LTD` ≡ `SINO-GALAXY IMP/EXP CO. LTD` | merged @0.504 | merged @0.504 (unchanged — they share a neighbour) |
| `SINO GALAXY IMP. & EXP. CO.` ≡ that cluster | merged | **watch-list @0.438, with the name-cap reason** |

So the consignor is two nodes, not one. The pair is *retained and readable*, never dropped: its reason names
the ground ("name-only identity, capped at 'possible' — … no neighbour, no stated discriminator, no source
assertion"). What used to fuse it was the two sides' agreeing `origin_country`, and a shared country is a
class every Chinese exporter is in — not evidence that two companies are one company.

**Expected-red (`xfail(strict)`):**
`tests/acceptance/test_per_type_automerge_corpus.py::test_sino_galaxy_spelling_variants_collapse_to_one_trading_org`.
Everything else in that module still passes, including the two same-type traps (CASIC ≠ its own institutes,
ORIENT ≠ SINO-GALAXY) and the CPMIEC / Taian merges — the per-type auto floor is NOT inert.

**TO CLOSE:** add `SINO GALAXY IMP. & EXP. CO.` to `config/resolution.yaml → alias_table` under the
SINO-GALAXY canonical. An alias LINK is a curated statement of equivalence, it is an EARNED trigger, and the
name cap does not touch it — that is the honest way to assert this merge. (The competing spec is a *property*,
not a corpus outcome: `test_an_identical_name_alone_never_fuses_at_any_type` is parametrized over
`manufacturer` too, so "a name alone never fuses" already covers organisations.)

### Also in this change (not a data item)
`config/resolution.yaml → attribute_roles` gains a third axis, `taxonomic: true`, plus two new
identity-bearing rows (`variant.export_designator`, `component.model_designation`) so the design layer keeps a
rung that can legitimately clear the name cap. Two property specs that had used `family` as their "one more
trivially-available signal" now use `export_designator`: the swap makes the spec *stricter*, since a family is
shared by every member of the family.
