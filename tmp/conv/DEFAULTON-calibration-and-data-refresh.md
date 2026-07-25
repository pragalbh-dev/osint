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
